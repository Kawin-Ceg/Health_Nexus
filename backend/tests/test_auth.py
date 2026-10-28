import hashlib
from datetime import timedelta

from sqlalchemy import select, text

from app.models import PhcApplication, RefreshToken, User
from tests.conftest import BASE, PASSWORD, register_and_login

WORKER = {
    "name": "Kavitha",
    "email": "kavitha@example.com",
    "password": PASSWORD,
    "employee_id": "TNPHC-CHN-2847",
    "designation": "staff_nurse",
    "phc_name": "Mylapore PHC",
    "district": "Chennai",
    "state": "Tamil Nadu",
    "years_of_service": 6,
}


def sha(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def test_citizen_registration_stores_lowercase_email_and_a_hash(client, db, outbox):
    r = await client.post(f"{BASE}/auth/register/citizen", json={"name": "Asha", "email": " Asha@Example.COM ", "password": PASSWORD})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "asha@example.com" and body["role"] == "user" and body["is_verified"] is False
    assert "password" not in str(body).lower().replace("hashed", "")

    user = await db.scalar(select(User))
    assert user.hashed_password.startswith("$2") and PASSWORD not in user.hashed_password
    raw = outbox.verification[-1][1]
    assert user.verification_token_hash == sha(raw) != raw


async def test_duplicate_email_is_rejected_regardless_of_case(client, outbox):
    await register_and_login(client, outbox, "dup@example.com", verify=False)
    r = await client.post(f"{BASE}/auth/register/citizen", json={"name": "B", "email": "DUP@example.com", "password": PASSWORD})
    assert r.status_code == 409


async def test_short_password_is_a_422_with_a_readable_shape(client):
    r = await client.post(f"{BASE}/auth/register/citizen", json={"name": "A", "email": "a@example.com", "password": "short"})
    assert r.status_code == 422


async def test_phc_registration_creates_user_and_application_together(client, db, outbox):
    r = await client.post(f"{BASE}/auth/register/phc-worker", json=WORKER)
    assert r.status_code == 201 and r.json()["role"] == "pending_phc"
    app_row = await db.scalar(select(PhcApplication))
    assert app_row.status.value == "pending" and app_row.employee_id == "TNPHC-CHN-2847"
    assert app_row.user_id is not None and len(outbox.verification) == 1


async def test_phc_registration_rejects_a_bad_employee_id_and_creates_nothing(client, db):
    r = await client.post(f"{BASE}/auth/register/phc-worker", json={**WORKER, "employee_id": "tnphc-chn-2847"})
    assert r.status_code == 422
    assert await db.scalar(select(User)) is None


async def test_login_sets_an_httponly_scoped_cookie_and_stores_only_a_hash(client, db, outbox):
    await register_and_login(client, outbox)
    r = await client.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "hn_refresh=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert "path=/api/v1/auth" in cookie and "secure" not in cookie

    raw = client.cookies.get("hn_refresh", path="/api/v1/auth")
    rows = (await db.scalars(select(RefreshToken))).all()
    assert raw and all(row.token_hash != raw for row in rows)
    assert sha(raw) in {row.token_hash for row in rows}


async def test_login_failures_are_indistinguishable(client, outbox):
    await register_and_login(client, outbox)
    wrong = await client.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": "wrong-password"})
    unknown = await client.post(f"{BASE}/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_me_needs_a_token_and_pending_workers_see_their_application(client, outbox):
    assert (await client.get(f"{BASE}/auth/me")).status_code == 401
    assert (await client.get(f"{BASE}/auth/me", headers={"Authorization": "Bearer nonsense"})).status_code == 401

    await client.post(f"{BASE}/auth/register/phc-worker", json=WORKER)
    r = await client.post(f"{BASE}/auth/login", json={"email": WORKER["email"], "password": PASSWORD})
    me = await client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["application"]["employee_id"] == "TNPHC-CHN-2847"
    assert me.json()["application"]["status"] == "pending"


async def test_refresh_rotates_and_links_the_chain(client, db, outbox):
    await register_and_login(client, outbox)
    old_raw = client.cookies.get("hn_refresh", path="/api/v1/auth")

    r = await client.post(f"{BASE}/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"] and r.json()["user"]["email"] == "asha@example.com"
    new_raw = client.cookies.get("hn_refresh", path="/api/v1/auth")
    assert new_raw != old_raw

    old = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == sha(old_raw)))
    new = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == sha(new_raw)))
    assert old.revoked and old.revoked_reason == "rotated"
    assert new.rotated_from == old.id and not new.revoked


async def test_a_reused_refresh_token_is_rejected(client, anon, outbox):
    await register_and_login(client, outbox)
    old_raw = client.cookies.get("hn_refresh", path="/api/v1/auth")
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 200

    replay = await anon.post(f"{BASE}/auth/refresh", cookies={"hn_refresh": old_raw})
    assert replay.status_code == 401


async def test_late_reuse_revokes_the_whole_chain(client, anon, db, outbox):
    await register_and_login(client, outbox)
    stolen = client.cookies.get("hn_refresh", path="/api/v1/auth")
    await client.post(f"{BASE}/auth/refresh")
    await db.execute(text("UPDATE refresh_tokens SET revoked_at = now() - interval '1 minute' WHERE revoked_reason = 'rotated'"))
    await db.commit()

    replay = await anon.post(f"{BASE}/auth/refresh", cookies={"hn_refresh": stolen})
    assert replay.status_code == 401 and "reuse" in replay.json()["detail"].lower()
    live = (await db.scalars(select(RefreshToken).where(RefreshToken.revoked.is_(False)))).all()
    assert live == []
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 401


async def test_a_racing_second_refresh_is_rejected_without_killing_the_session(client, anon, outbox):
    await register_and_login(client, outbox)
    old_raw = client.cookies.get("hn_refresh", path="/api/v1/auth")
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 200

    racer = await anon.post(f"{BASE}/auth/refresh", cookies={"hn_refresh": old_raw})
    assert racer.status_code == 401
    assert "set-cookie" not in racer.headers
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 200


async def test_idle_refresh_token_is_rejected_and_says_inactivity(client, db, outbox):
    await register_and_login(client, outbox)
    await db.execute(text("UPDATE refresh_tokens SET last_activity_at = now() - interval '49 hours'"))
    await db.commit()

    r = await client.post(f"{BASE}/auth/refresh")
    assert r.status_code == 401 and "inactivity" in r.json()["detail"].lower()
    row = await db.scalar(select(RefreshToken))
    await db.refresh(row)
    assert row.revoked and row.revoked_reason == "inactivity"


async def test_just_inside_the_idle_window_still_refreshes(client, db, outbox):
    await register_and_login(client, outbox)
    await db.execute(text("UPDATE refresh_tokens SET last_activity_at = now() - interval '47 hours'"))
    await db.commit()
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 200


async def test_refresh_without_a_cookie_is_401(anon):
    assert (await anon.post(f"{BASE}/auth/refresh")).status_code == 401


async def test_logout_revokes_the_session_and_clears_the_cookie(client, db, outbox):
    await register_and_login(client, outbox)
    stale = client.cookies.get("hn_refresh", path="/api/v1/auth")
    r = await client.post(f"{BASE}/auth/logout")
    assert r.status_code == 200 and "hn_refresh=" in r.headers["set-cookie"]
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == sha(stale)))
    assert row.revoked and row.revoked_reason == "logout"
    assert (await client.post(f"{BASE}/auth/refresh", cookies={"hn_refresh": stale})).status_code == 401


async def test_sessions_list_flags_current_and_revoke_others_keeps_it(client, anon, outbox):
    headers = await register_and_login(client, outbox)
    other = await anon.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": PASSWORD}, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Firefox/120.0"})
    assert other.status_code == 200

    listing = (await client.get(f"{BASE}/auth/sessions", headers=headers)).json()
    assert len(listing) == 2 and sum(s["is_current"] for s in listing) == 1
    assert {"Firefox on macOS"} & {s["device_label"] for s in listing}

    r = await client.post(f"{BASE}/auth/sessions/revoke-others", headers=headers)
    assert r.status_code == 200
    after = (await client.get(f"{BASE}/auth/sessions", headers=headers)).json()
    assert len(after) == 1 and after[0]["is_current"]
    assert (await anon.post(f"{BASE}/auth/refresh")).status_code == 401
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 200


async def test_delete_one_session_and_never_someone_elses(client, anon, outbox):
    headers = await register_and_login(client, outbox)
    await anon.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": PASSWORD})
    listing = (await client.get(f"{BASE}/auth/sessions", headers=headers)).json()
    other = next(s for s in listing if not s["is_current"])

    assert (await client.delete(f"{BASE}/auth/sessions/{other['id']}", headers=headers)).status_code == 204
    assert (await client.delete(f"{BASE}/auth/sessions/{other['id']}", headers=headers)).status_code == 404

    intruder = await register_and_login(anon, outbox, "eve@example.com")
    mine = next(s for s in listing if s["is_current"])
    assert (await anon.delete(f"{BASE}/auth/sessions/{mine['id']}", headers=intruder)).status_code == 404


async def test_verification_link_works_on_a_device_with_no_session_and_only_once(client, anon, db, outbox):
    await register_and_login(client, outbox, verify=False)
    token = outbox.verification[-1][1]

    assert (await anon.post(f"{BASE}/auth/email/verify", json={"token": token})).status_code == 200
    user = await db.scalar(select(User))
    assert user.is_verified and user.verified_at and user.verification_token_hash is None
    assert (await anon.post(f"{BASE}/auth/email/verify", json={"token": token})).status_code == 400


async def test_verification_link_expires(client, db, outbox):
    await register_and_login(client, outbox, verify=False)
    await db.execute(text("UPDATE users SET verification_token_expires_at = now() - interval '1 second'"))
    await db.commit()
    assert (await client.post(f"{BASE}/auth/email/verify", json={"token": outbox.verification[-1][1]})).status_code == 400


async def test_resend_is_rate_limited_and_replaces_the_old_link(client, db, outbox):
    headers = await register_and_login(client, outbox, verify=False)
    first = outbox.verification[-1][1]

    limited = await client.post(f"{BASE}/auth/email/send-verification", headers=headers)
    assert limited.status_code == 429 and int(limited.headers["retry-after"]) > 0

    await db.execute(text("UPDATE users SET verification_sent_at = now() - interval '61 seconds'"))
    await db.commit()
    assert (await client.post(f"{BASE}/auth/email/send-verification", headers=headers)).status_code == 200
    second = outbox.verification[-1][1]
    assert second != first
    assert (await client.post(f"{BASE}/auth/email/verify", json={"token": first})).status_code == 400
    assert (await client.post(f"{BASE}/auth/email/verify", json={"token": second})).status_code == 200


async def test_send_verification_requires_a_session(anon):
    assert (await anon.post(f"{BASE}/auth/email/send-verification")).status_code == 401


async def test_forgot_password_answers_identically_for_known_and_unknown(client, outbox):
    await register_and_login(client, outbox)
    known = await client.post(f"{BASE}/auth/password/forgot", json={"email": "asha@example.com"})
    unknown = await client.post(f"{BASE}/auth/password/forgot", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 200 and known.json() == unknown.json()
    assert [to for to, _ in outbox.reset] == ["asha@example.com"]


async def test_reset_sets_password_revokes_every_session_and_is_single_use(client, anon, db, outbox):
    await register_and_login(client, outbox)
    await anon.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": PASSWORD})
    await client.post(f"{BASE}/auth/password/forgot", json={"email": "asha@example.com"})
    token = outbox.reset[-1][1]
    assert (await db.scalar(select(User))).password_reset_token_hash == sha(token)

    r = await anon.post(f"{BASE}/auth/password/reset", json={"token": token, "new_password": "brand new secret"})
    assert r.status_code == 200
    live = (await db.scalars(select(RefreshToken).where(RefreshToken.revoked.is_(False)))).all()
    assert live == []
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 401

    assert (await client.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": PASSWORD})).status_code == 401
    assert (await client.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": "brand new secret"})).status_code == 200
    assert (await anon.post(f"{BASE}/auth/password/reset", json={"token": token, "new_password": "another secret 1"})).status_code == 400


async def test_a_reset_never_consumes_a_pending_verification(client, db, outbox):
    await register_and_login(client, outbox, verify=False)
    verification = outbox.verification[-1][1]
    await client.post(f"{BASE}/auth/password/forgot", json={"email": "asha@example.com"})
    await client.post(f"{BASE}/auth/password/reset", json={"token": outbox.reset[-1][1], "new_password": "brand new secret"})
    assert (await client.post(f"{BASE}/auth/email/verify", json={"token": verification})).status_code == 200


async def test_reset_link_expires(client, db, outbox):
    await register_and_login(client, outbox)
    await client.post(f"{BASE}/auth/password/forgot", json={"email": "asha@example.com"})
    await db.execute(text("UPDATE users SET password_reset_expires_at = now() - interval '1 second'"))
    await db.commit()
    r = await client.post(f"{BASE}/auth/password/reset", json={"token": outbox.reset[-1][1], "new_password": "brand new secret"})
    assert r.status_code == 400


async def test_consent_appends_only_when_the_answer_changes(client, db, outbox):
    headers = await register_and_login(client, outbox)
    body = {"consents": [{"consent_type": "research_analytics", "granted": True}]}
    assert (await client.patch(f"{BASE}/auth/consent", json=body, headers=headers)).json()["consents"] == {"research_analytics": True}
    await client.patch(f"{BASE}/auth/consent", json=body, headers=headers)
    body["consents"][0]["granted"] = False
    r = await client.patch(f"{BASE}/auth/consent", json=body, headers=headers)
    assert r.json()["consents"] == {"research_analytics": False}
    count = (await db.execute(text("SELECT count(*) FROM consent_records"))).scalar()
    assert count == 2


async def test_consent_is_for_citizens_only(client, outbox):
    await client.post(f"{BASE}/auth/register/phc-worker", json=WORKER)
    r = await client.post(f"{BASE}/auth/login", json={"email": WORKER["email"], "password": PASSWORD})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    body = {"consents": [{"consent_type": "research_analytics", "granted": True}]}
    assert (await client.patch(f"{BASE}/auth/consent", json=body, headers=headers)).status_code == 403


async def test_a_deactivated_account_loses_access_immediately(client, db, outbox):
    headers = await register_and_login(client, outbox)
    await db.execute(text("UPDATE users SET is_active = false"))
    await db.commit()
    assert (await client.get(f"{BASE}/auth/me", headers=headers)).status_code == 401
    assert (await client.post(f"{BASE}/auth/refresh")).status_code == 401
    assert (await client.post(f"{BASE}/auth/login", json={"email": "asha@example.com", "password": PASSWORD})).status_code == 401


async def test_an_expired_access_token_is_rejected(client, outbox, monkeypatch):
    from app.core import security

    monkeypatch.setattr(security, "ACCESS_TOKEN_TTL", timedelta(seconds=-1))
    headers = await register_and_login(client, outbox)
    assert (await client.get(f"{BASE}/auth/me", headers=headers)).status_code == 401
