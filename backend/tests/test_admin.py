"""The admin console: approvals, accounts, concerns and the audit trail."""

from sqlalchemy import select

from app.models import PhcVerificationAuditLog, User
from app.models.enums import UserRole

from .conftest import BASE, PASSWORD, register_and_login
from .test_modules import facility, make_user

PHC_SIGNUP = {
    "name": "Meena S",
    "email": "meena@example.com",
    "password": PASSWORD,
    "employee_id": "TNPHC-CHN-2847",
    "designation": "staff_nurse",
    "phc_name": "Mylapore Primary Health Centre",
    "district": "Chennai",
    "state": "Tamil Nadu",
    "years_of_service": 4,
}


async def _applicant(client, outbox) -> dict:
    r = await client.post(f"{BASE}/auth/register/phc-worker", json=PHC_SIGNUP)
    assert r.status_code == 201, r.text
    token = outbox.verification[-1][1]
    assert (await client.post(f"{BASE}/auth/email/verify", json={"token": token})).status_code == 200
    r = await client.post(f"{BASE}/auth/login", json={"email": PHC_SIGNUP["email"], "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_only_admins_reach_the_console(client, outbox, db):
    citizen = await register_and_login(client, outbox)
    assert (await client.get(f"{BASE}/admin/overview", headers=citizen)).status_code == 403
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    r = await client.get(f"{BASE}/admin/overview", headers=ah)
    assert r.status_code == 200, r.text
    assert r.json()["users_by_role"]["admin"] == 1


async def test_approve_links_the_worker_to_the_facility(client, outbox, db):
    mylapore = await facility(db, "Mylapore PHC")
    admin, ah = await make_user(db, UserRole.admin, None, "Admin")
    wh = await _applicant(client, outbox)
    assert (await client.get(f"{BASE}/phc/dashboard", headers=wh)).status_code == 403

    listing = (await client.get(f"{BASE}/admin/applications?status=pending", headers=ah)).json()
    assert listing["counts"]["pending"] == 1
    app_id = listing["items"][0]["id"]
    detail = (await client.get(f"{BASE}/admin/applications/{app_id}", headers=ah)).json()
    assert detail["suggested_facility"]["id"] == str(mylapore.id)

    r = await client.post(f"{BASE}/admin/applications/{app_id}/approve", json={"facility_id": str(mylapore.id)}, headers=ah)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"
    assert r.json()["history"][0]["action"] == "application_approved"
    assert (await client.get(f"{BASE}/phc/dashboard", headers=wh)).status_code == 200
    again = await client.post(f"{BASE}/admin/applications/{app_id}/approve", json={"facility_id": str(mylapore.id)}, headers=ah)
    assert again.status_code == 409

    r = await client.post(f"{BASE}/admin/applications/{app_id}/revoke", json={"reason": "Left the service"}, headers=ah)
    assert r.status_code == 200, r.text
    worker = await db.scalar(select(User).where(User.email == PHC_SIGNUP["email"]).execution_options(populate_existing=True))
    assert worker.role == UserRole.pending_phc and worker.phc_id is None
    assert (await client.get(f"{BASE}/phc/dashboard", headers=wh)).status_code == 403
    logged = (await db.scalars(select(PhcVerificationAuditLog.action))).all()
    assert len(logged) == 2


async def test_reject_needs_a_reason_and_is_shown_to_the_applicant(client, outbox, db):
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    wh = await _applicant(client, outbox)
    app_id = (await client.get(f"{BASE}/admin/applications", headers=ah)).json()["items"][0]["id"]
    assert (await client.post(f"{BASE}/admin/applications/{app_id}/reject", json={"reason": ""}, headers=ah)).status_code == 422
    r = await client.post(f"{BASE}/admin/applications/{app_id}/reject", json={"reason": "Employee ID not found"}, headers=ah)
    assert r.status_code == 200, r.text
    me = (await client.get(f"{BASE}/auth/me", headers=wh)).json()
    assert me["application"]["status"] == "rejected"
    assert me["application"]["rejection_reason"] == "Employee ID not found"


async def test_deactivating_an_account_blocks_it_at_once(client, outbox, db):
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    citizen = await register_and_login(client, outbox)
    me = (await client.get(f"{BASE}/auth/me", headers=citizen)).json()
    r = await client.post(f"{BASE}/admin/users/{me['id']}/deactivate", json={"reason": "Spam account"}, headers=ah)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert (await client.get(f"{BASE}/auth/me", headers=citizen)).status_code == 401
    r = await client.post(f"{BASE}/admin/users/{me['id']}/reactivate", headers=ah)
    assert r.json()["is_active"] is True


async def test_admins_cannot_act_on_admins(client, db):
    admin, ah = await make_user(db, UserRole.admin, None, "Admin")
    other, _ = await make_user(db, UserRole.admin, None, "Other admin")
    for target in (admin, other):
        r = await client.post(f"{BASE}/admin/users/{target.id}/deactivate", json={"reason": "nope"}, headers=ah)
        assert r.status_code == 403


async def test_concern_closing_needs_a_note(client, outbox, db):
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    citizen = await register_and_login(client, outbox)
    r = await client.post(f"{BASE}/settings/concerns", json={"category": "other", "description": "My data looks wrong here."}, headers=citizen)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert (await client.patch(f"{BASE}/admin/concerns/{cid}", json={"status": "resolved"}, headers=ah)).status_code == 422
    r = await client.patch(f"{BASE}/admin/concerns/{cid}", json={"status": "resolved", "admin_note": "Fixed."}, headers=ah)
    assert r.status_code == 200 and r.json()["handled_by"] == "Admin"
    mine = (await client.get(f"{BASE}/settings/concerns/{cid}", headers=citizen)).json()
    assert mine["status"] == "resolved" and mine["admin_note"] == "Fixed."
    audit = (await client.get(f"{BASE}/admin/audit?source=account", headers=ah)).json()
    assert any(a["action"] == "concern_resolved" for a in audit)
