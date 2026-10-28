import pytest
from sqlalchemy import select, text

from app.models import ConsentRecord, User, UserProfile, ValidPhcFacility
from app.seeds.data import tamil_nadu
from tests.conftest import BASE, PASSWORD, register_and_login
from tests.test_auth import WORKER

STATE, DISTRICT = "Tamil Nadu", "Chennai"


async def facility_id(db, name: str) -> str:
    return str((await db.scalar(select(ValidPhcFacility).where(ValidPhcFacility.name == name))).id)


def payload(phc_id: str, **overrides):
    body = {
        "age": 34,
        "gender": "female",
        "height_cm": 160,
        "weight_kg": 58.5,
        "blood_group": "B+",
        "state": STATE,
        "district": DISTRICT,
        "phc_id": phc_id,
        "pincode": "600004",
        "area": "Mandaveli",
        "existing_conditions": ["asthma"],
        "current_medications": [],
        "has_smartwatch": True,
        "smartwatch_brand": "Noise",
        "emergency_contact_name": "Ravi",
        "emergency_contact_phone": "+91 98410 11223",
        "consents": {"health_tracking": True, "community_surveillance": False, "phc_worker_access": True},
    }
    return {**body, **overrides}


async def test_onboarding_needs_a_session(client):
    assert (await client.get(f"{BASE}/onboarding/districts", params={"state": STATE})).status_code == 401


async def test_onboarding_needs_a_verified_email(client, outbox):
    headers = await register_and_login(client, outbox, verify=False)
    r = await client.get(f"{BASE}/onboarding/districts", params={"state": STATE}, headers=headers)
    assert r.status_code == 403 and "verify" in r.json()["detail"].lower()


async def test_onboarding_is_closed_to_other_roles(client):
    await client.post(f"{BASE}/auth/register/phc-worker", json=WORKER)
    r = await client.post(f"{BASE}/auth/login", json={"email": WORKER["email"], "password": PASSWORD})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await client.get(f"{BASE}/onboarding/profile", headers=headers)).status_code == 403


async def test_dropdowns_load_from_the_registry(client, db, outbox):
    headers = await register_and_login(client, outbox)
    assert (await client.get(f"{BASE}/onboarding/states", headers=headers)).json() == [STATE]

    registry = tamil_nadu.facilities()

    districts = (await client.get(f"{BASE}/onboarding/districts", params={"state": "tamil nadu"}, headers=headers)).json()
    assert districts == sorted({r["district"] for r in registry})
    assert (await client.get(f"{BASE}/onboarding/districts", params={"state": "Kerala"}, headers=headers)).json() == []

    facilities = (await client.get(f"{BASE}/onboarding/facilities", params={"state": STATE, "district": DISTRICT}, headers=headers)).json()
    assert [f["name"] for f in facilities] == sorted(r["name"] for r in registry if r["district"] == DISTRICT)


async def test_inactive_facilities_are_hidden(client, db, outbox):
    headers = await register_and_login(client, outbox)
    await db.execute(text("UPDATE valid_phc_facilities SET is_active = false WHERE district = 'Kanchipuram'"))
    await db.commit()
    try:
        districts = (await client.get(f"{BASE}/onboarding/districts", params={"state": STATE}, headers=headers)).json()
        assert "Kanchipuram" not in districts
    finally:
        await db.execute(text("UPDATE valid_phc_facilities SET is_active = true"))
        await db.commit()


async def test_completing_onboarding_writes_everything_in_one_go(client, db, outbox):
    headers = await register_and_login(client, outbox)
    phc = await facility_id(db, "Mylapore PHC")

    r = await client.post(f"{BASE}/onboarding/profile", json=payload(phc), headers=headers)
    assert r.status_code == 201, r.text
    assert r.json()["facility"]["name"] == "Mylapore PHC"
    assert r.json()["consents"] == {"health_tracking": True, "community_surveillance": False, "phc_worker_access": True}

    user = await db.scalar(select(User))
    assert user.profile_completed and str(user.phc_id) == phc and user.district == DISTRICT and user.state == STATE
    assert user.pincode == "600004" and user.area == "Mandaveli" and user.consent is True
    profile = await db.scalar(select(UserProfile))
    assert profile.age == 34 and profile.blood_group.value == "B+" and profile.permission_health_tracking is True
    assert profile.existing_conditions == ["asthma"] and profile.smartwatch_brand == "Noise"
    records = {(c.consent_type.value, c.granted, c.source) for c in await db.scalars(select(ConsentRecord))}
    assert records == {
        ("health_tracking", True, "onboarding"),
        ("community_surveillance", False, "onboarding"),
        ("phc_worker_access", True, "onboarding"),
    }

    me = await client.get(f"{BASE}/auth/me", headers=headers)
    assert me.json()["profile_completed"] is True
    saved = await client.get(f"{BASE}/onboarding/profile", headers=headers)
    assert saved.json()["pincode"] == "600004"


async def test_a_second_submission_is_a_conflict(client, db, outbox):
    headers = await register_and_login(client, outbox)
    phc = await facility_id(db, "Mylapore PHC")
    assert (await client.post(f"{BASE}/onboarding/profile", json=payload(phc), headers=headers)).status_code == 201
    assert (await client.post(f"{BASE}/onboarding/profile", json=payload(phc), headers=headers)).status_code == 409


async def test_get_profile_is_404_before_onboarding(client, outbox):
    headers = await register_and_login(client, outbox)
    assert (await client.get(f"{BASE}/onboarding/profile", headers=headers)).status_code == 404


async def test_a_facility_from_another_district_is_rejected(client, db, outbox):
    headers = await register_and_login(client, outbox)
    tambaram = await facility_id(db, "Tambaram PHC")
    r = await client.post(f"{BASE}/onboarding/profile", json=payload(tambaram), headers=headers)
    assert r.status_code == 422 and "does not serve" in r.json()["detail"]
    assert (await db.scalar(select(UserProfile))) is None
    assert (await db.scalar(select(User))).profile_completed is False


async def test_an_unknown_or_inactive_facility_is_rejected(client, db, outbox):
    headers = await register_and_login(client, outbox)
    unknown = "00000000-0000-0000-0000-000000000000"
    assert (await client.post(f"{BASE}/onboarding/profile", json=payload(unknown), headers=headers)).status_code == 422
    phc = await facility_id(db, "Adyar PHC")
    await db.execute(text("UPDATE valid_phc_facilities SET is_active = false WHERE name = 'Adyar PHC'"))
    await db.commit()
    try:
        assert (await client.post(f"{BASE}/onboarding/profile", json=payload(phc), headers=headers)).status_code == 422
    finally:
        await db.execute(text("UPDATE valid_phc_facilities SET is_active = true"))
        await db.commit()


@pytest.mark.parametrize(
    "override",
    [
        {"has_smartwatch": False, "smartwatch_brand": "Noise"},
        {"emergency_contact_phone": None},
        {"emergency_contact_name": None},
        {"age": 0},
        {"age": 121},
        {"height_cm": 49},
        {"height_cm": 301},
        {"weight_kg": 0},
        {"weight_kg": 301},
        {"pincode": "60000"},
        {"pincode": "6000a4"},
        {"gender": "robot"},
        {"blood_group": "Z+"},
        {"existing_conditions": [f"c{i}" for i in range(11)]},
        {"current_medications": [f"m{i}" for i in range(11)]},
        {"emergency_contact_phone": "abc"},
        {"consents": {"health_tracking": True}},
    ],
)
async def test_invalid_profiles_are_rejected(client, db, outbox, override):
    headers = await register_and_login(client, outbox)
    body = payload(await facility_id(db, "Mylapore PHC"), **override)
    assert (await client.post(f"{BASE}/onboarding/profile", json=body, headers=headers)).status_code == 422
    assert (await db.scalar(select(UserProfile))) is None


async def test_ten_tags_is_the_limit_and_duplicates_collapse(client, db, outbox):
    headers = await register_and_login(client, outbox)
    phc = await facility_id(db, "Mylapore PHC")
    tags = [f"condition {i}" for i in range(8)] + ["Asthma", "asthma "]
    r = await client.post(f"{BASE}/onboarding/profile", json=payload(phc, existing_conditions=tags), headers=headers)
    assert r.status_code == 201 and len(r.json()["existing_conditions"]) == 9


async def test_a_failure_part_way_leaves_nothing_behind(client, db, outbox, monkeypatch):
    headers = await register_and_login(client, outbox)
    phc = await facility_id(db, "Mylapore PHC")

    async def explode(*args, **kwargs):
        raise RuntimeError("consent write failed")

    monkeypatch.setattr("app.api.routes.onboarding.record_consents", explode)
    with pytest.raises(RuntimeError):
        await client.post(f"{BASE}/onboarding/profile", json=payload(phc), headers=headers)
    assert (await db.scalar(select(UserProfile))) is None
    user = await db.scalar(select(User))
    assert user.profile_completed is False and user.phc_id is None


async def test_identity_and_role_cannot_be_smuggled_in_the_body(client, db, outbox):
    headers = await register_and_login(client, outbox)
    phc = await facility_id(db, "Mylapore PHC")
    r = await client.post(f"{BASE}/onboarding/profile", json=payload(phc, user_id="x", role="admin"), headers=headers)
    assert r.status_code == 201
    assert (await db.scalar(select(User))).role.value == "user"
    assert (await client.patch(f"{BASE}/onboarding/profile", json={"role": "admin"}, headers=headers)).status_code == 422


async def test_patch_updates_only_what_is_sent(client, db, outbox):
    headers = await register_and_login(client, outbox)
    phc = await facility_id(db, "Mylapore PHC")
    await client.post(f"{BASE}/onboarding/profile", json=payload(phc), headers=headers)

    r = await client.patch(f"{BASE}/onboarding/profile", json={"weight_kg": 60, "area": "Mylapore"}, headers=headers)
    assert r.status_code == 200 and r.json()["weight_kg"] == 60 and r.json()["area"] == "Mylapore"
    assert r.json()["age"] == 34 and r.json()["smartwatch_brand"] == "Noise"


async def test_patch_is_validated_against_the_saved_record(client, db, outbox):
    headers = await register_and_login(client, outbox)
    phc = await facility_id(db, "Mylapore PHC")
    await client.post(f"{BASE}/onboarding/profile", json=payload(phc, has_smartwatch=False, smartwatch_brand=None), headers=headers)

    assert (await client.patch(f"{BASE}/onboarding/profile", json={"smartwatch_brand": "Noise"}, headers=headers)).status_code == 422
    assert (await client.patch(f"{BASE}/onboarding/profile", json={"emergency_contact_phone": None}, headers=headers)).status_code == 422
    assert (await client.patch(f"{BASE}/onboarding/profile", json={"age": None}, headers=headers)).status_code == 422
    r = await client.patch(f"{BASE}/onboarding/profile", json={"has_smartwatch": True, "smartwatch_brand": "Fitbit"}, headers=headers)
    assert r.status_code == 200 and r.json()["smartwatch_brand"] == "Fitbit"
    r = await client.patch(f"{BASE}/onboarding/profile", json={"has_smartwatch": False}, headers=headers)
    assert r.status_code == 200 and r.json()["smartwatch_brand"] is None


async def test_patch_moving_district_needs_a_matching_centre(client, db, outbox):
    headers = await register_and_login(client, outbox)
    await client.post(f"{BASE}/onboarding/profile", json=payload(await facility_id(db, "Mylapore PHC")), headers=headers)

    assert (await client.patch(f"{BASE}/onboarding/profile", json={"district": "Chengalpattu"}, headers=headers)).status_code == 422
    tambaram = await facility_id(db, "Tambaram PHC")
    r = await client.patch(f"{BASE}/onboarding/profile", json={"district": "Chengalpattu", "phc_id": tambaram}, headers=headers)
    assert r.status_code == 200 and r.json()["facility"]["name"] == "Tambaram PHC"
    assert str((await db.scalar(select(User))).phc_id) == tambaram
