import uuid

import pytest
from sqlalchemy import delete, select

from app.models import AuditLog, ValidPhcFacility
from app.models.enums import UserRole

from .conftest import BASE
from .test_modules import make_user, world  # noqa: F401

NEW = {
    "facility_code": "tn-chn-test-01",
    "name": "Test Nagar Primary Health Centre",
    "district": "Chennai",
    "state": "Tamil Nadu",
    "block": "Test Nagar",
    "latitude": 13.05,
    "longitude": 80.25,
}


@pytest.fixture
async def clean_registry(db):
    yield
    await db.execute(delete(ValidPhcFacility).where(ValidPhcFacility.facility_code == "TN-CHN-TEST-01"))
    await db.commit()


async def test_admin_manages_the_registry(clean_registry, client, db, world):
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    r = await client.post(f"{BASE}/admin/registry", json=NEW, headers=ah)
    assert r.status_code == 201, r.text
    centre = r.json()
    assert centre["facility_code"] == "TN-CHN-TEST-01" and centre["is_active"] and not centre["is_placeholder"]
    assert (await client.post(f"{BASE}/admin/registry", json=NEW, headers=ah)).status_code == 409

    r = await client.patch(f"{BASE}/admin/registry/{centre['id']}", json={"name": "Test Nagar PHC", "block": None}, headers=ah)
    assert r.json()["name"] == "Test Nagar PHC" and r.json()["block"] is None
    assert (await client.patch(f"{BASE}/admin/registry/{centre['id']}", json={"latitude": None}, headers=ah)).status_code == 422

    listed = (await client.get(f"{BASE}/admin/registry", params={"q": "Test Nagar"}, headers=ah)).json()
    assert [c["id"] for c in listed["items"]] == [centre["id"]] and "Chennai" in listed["districts"]

    r = await client.post(f"{BASE}/admin/registry/{centre['id']}/deactivate", headers=ah)
    assert r.json()["is_active"] is False
    picker = (await client.get(f"{BASE}/admin/facilities", params={"q": "Test Nagar"}, headers=ah)).json()
    assert picker == []
    assert (await client.post(f"{BASE}/admin/registry/{centre['id']}/reactivate", headers=ah)).json()["is_active"]

    actions = set(await db.scalars(select(AuditLog.action).where(AuditLog.entity_id == uuid.UUID(centre["id"]))))
    assert actions == {"create_health_centre", "edit_health_centre", "deactivate_health_centre", "reactivate_health_centre"}


async def test_linked_people_are_counted(client, db, world):
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    mylapore = world["mylapore"]
    listed = (await client.get(f"{BASE}/admin/registry", params={"q": mylapore.name}, headers=ah)).json()
    row = next(c for c in listed["items"] if c["id"] == str(mylapore.id))
    assert (row["workers"], row["citizens"]) == (1, 2)


async def test_only_admins(client, world):
    _, wh = world["worker"]
    assert (await client.get(f"{BASE}/admin/registry", headers=wh)).status_code == 403
