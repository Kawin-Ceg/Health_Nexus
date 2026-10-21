"""Citizen and PHC worker modules, end to end through the API."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, text, update

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from app.api.views import vitals_result
from app.core.security import create_access_token, decode_access_token, hash_password
from app.db.session import get_session
from app.main import app
from app.schemas.health import VitalsIn
from app.services.readings import submit_reading
from app.models import Alert, ScheduledVisit, User, UserProfile, ValidPhcFacility
from app.models.base import utcnow
from app.models.enums import Gender, UserRole

from .conftest import BASE, PASSWORD

NORMAL = {"systolic": 112, "diastolic": 72, "heart_rate": 70, "temperature_c": 36.7, "spo2": 98}
HIGH_BP = {"systolic": 167, "diastolic": 103, "heart_rate": 88}


async def facility(db, name: str) -> ValidPhcFacility:
    found = await db.scalar(select(ValidPhcFacility).where(ValidPhcFacility.name == name))
    assert found is not None, f"seed_phc_facilities first: {name}"
    return found


async def make_user(db, role: UserRole, phc: ValidPhcFacility | None, name: str, area: str = "Luz") -> tuple[User, dict]:
    user = User(
        name=name,
        email=f"{uuid.uuid4().hex[:10]}@example.com",
        hashed_password=hash_password(PASSWORD),
        role=role,
        is_verified=True,
        profile_completed=True,
        consent=True,
        phone="+91 98400 00000",
        phc_id=phc.id if phc else None,
        district=phc.district if phc else "Chennai",
        state=phc.state if phc else "Tamil Nadu",
        area=area,
    )
    db.add(user)
    await db.flush()
    if role == UserRole.user:
        db.add(
            UserProfile(
                user_id=user.id, age=40, gender=Gender.female, height_cm=160, weight_kg=60, permission_health_tracking=True
            )
        )
    await db.commit()
    token = create_access_token(user.id, role.value, uuid.uuid4())
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def world(db):
    mylapore, adyar = await facility(db, "Mylapore PHC"), await facility(db, "Adyar PHC")
    worker, wh = await make_user(db, UserRole.phc_worker, mylapore, "Kavitha Raman")
    other_worker, owh = await make_user(db, UserRole.phc_worker, adyar, "Other Nurse")
    priya, ph = await make_user(db, UserRole.user, mylapore, "Priya B", area="Luz")
    ravi, rh = await make_user(db, UserRole.user, mylapore, "Ravi K", area="Mandaveli")
    foreign, fh = await make_user(db, UserRole.user, adyar, "Foreign Citizen")
    return {
        "mylapore": mylapore, "adyar": adyar,
        "worker": (worker, wh), "other_worker": (other_worker, owh),
        "priya": (priya, ph), "ravi": (ravi, rh), "foreign": (foreign, fh),
    }


class Stored:
    def __init__(self, status_code: int, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


async def submit(client, headers, vitals, symptoms=(), measured_at=None):
    """A reading arriving from the citizen's smartwatch, through the same service every reading uses."""
    try:
        data = VitalsIn(vitals=vitals, symptoms=list(symptoms), measured_at=measured_at)
    except ValidationError:
        return Stored(422)
    claims = decode_access_token(headers["Authorization"].removeprefix("Bearer "))
    async for session in app.dependency_overrides[get_session]():
        citizen = await session.get(User, uuid.UUID(claims["sub"]))
        if not citizen.consent:
            return Stored(403)
        recorded = await submit_reading(session, citizen, data.vitals, data.symptoms, data.measured_at or utcnow(), source="watch")
        return Stored(201, jsonable_encoder(vitals_result(recorded)))


# --- Phase 1 -------------------------------------------------------------------


async def test_citizen_logs_normal_and_flagged_readings(client, world):
    _, ph = world["priya"]
    r = await submit(client, ph, NORMAL)
    assert r.status_code == 201, r.text
    assert r.json()["flagged"] is False
    assert "published normal ranges" in r.json()["basis_note"]  # cold start says so

    r = await submit(client, ph, HIGH_BP, symptoms=["Headache", "headache"])
    body = r.json()
    assert body["flagged"] is True and body["driver"] in ("systolic", "diastolic")
    assert body["signal"] == "Blood pressure 167/103 mmHg — well above the normal range"
    assert body["features"]["systolic"] > 0
    assert body["reviewed_by_someone"] is True

    history = (await client.get(f"{BASE}/health/history", headers=ph)).json()
    assert history["total"] == 2
    assert [i["flagged"] for i in history["items"]] == [True, False]  # newest first
    assert history["items"][0]["symptoms"] == ["headache"]

    summary = (await client.get(f"{BASE}/health/summary", headers=ph)).json()
    assert summary["readings_total"] == 2 and summary["open_flags"] == 1
    assert {v["key"] for v in summary["latest"]} >= {"systolic", "spo2"}
    assert all(v["baseline"] is None for v in summary["latest"])  # 2 readings: no baseline yet

    alerts = (await client.get(f"{BASE}/alerts", headers=ph)).json()
    assert alerts["unread"] == 1 and "flagged" in alerts["alerts"][0]["message"]


async def test_readings_are_validated(client, world):
    _, ph = world["priya"]
    assert (await submit(client, ph, {})).status_code == 422
    assert (await submit(client, ph, {"systolic": 1200})).status_code == 422
    assert (await submit(client, ph, {"systolic": 80, "diastolic": 90})).status_code == 422
    assert (await submit(client, ph, {"pulse": 80})).status_code == 422
    r = await client.get(f"{BASE}/health/history", params={"metric": "nope"}, headers=ph)
    assert r.status_code == 422


async def test_a_reading_can_only_be_deleted_by_its_owner(client, world):
    _, ph = world["priya"]
    _, rh = world["ravi"]
    reading = (await submit(client, ph, HIGH_BP)).json()["id"]
    assert (await client.delete(f"{BASE}/health/readings/{reading}", headers=rh)).status_code == 404
    assert (await client.delete(f"{BASE}/health/readings/{reading}", headers=ph)).status_code == 204
    assert (await client.get(f"{BASE}/health/history", headers=ph)).json()["total"] == 0


async def test_mark_read_touches_only_own_alerts(client, db, world):
    priya, ph = world["priya"]
    ravi, rh = world["ravi"]
    await submit(client, ph, HIGH_BP)
    await submit(client, rh, HIGH_BP)
    ravis = (await client.get(f"{BASE}/alerts", headers=rh)).json()["alerts"][0]["id"]
    r = await client.post(f"{BASE}/alerts/mark-read", json={"ids": [ravis]}, headers=ph)
    assert r.json()["updated"] == 0
    assert (await client.get(f"{BASE}/alerts/unread-count", headers=rh)).json()["unread"] == 1
    assert (await client.post(f"{BASE}/alerts/mark-read", json={}, headers=ph)).json()["updated"] == 1


async def test_citizen_without_a_worker_is_told_nobody_is_reviewing(client, db, world):
    # Adyar has a worker in this fixture; take them away.
    other, _ = world["other_worker"]
    await db.execute(update(User).where(User.id == other.id).values(is_active=False))
    await db.commit()
    _, fh = world["foreign"]
    r = await submit(client, fh, HIGH_BP)
    assert r.json()["reviewed_by_someone"] is False
    centre = (await client.get(f"{BASE}/settings/health-centre", headers=fh)).json()
    assert centre["current"]["workers_assigned"] == 0
    assert any(o["name"] == "Mylapore PHC" and o["workers_assigned"] == 1 for o in centre["options"])


# --- Phase 2 -------------------------------------------------------------------


async def test_worker_sees_only_their_catchment(client, world):
    _, ph = world["priya"]
    _, fh = world["foreign"]
    _, wh = world["worker"]
    await submit(client, ph, HIGH_BP)
    await submit(client, fh, HIGH_BP)

    queue = (await client.get(f"{BASE}/phc/queue", headers=wh)).json()
    assert [i["citizen"]["name"] for i in queue["items"]] == ["Priya B"]
    worklist = (await client.get(f"{BASE}/phc/worklist", headers=wh)).json()
    assert [i["citizen"]["name"] for i in worklist["items"]] == ["Priya B"]
    directory = (await client.get(f"{BASE}/phc/citizens", params={"q": "Foreign"}, headers=wh)).json()
    assert directory["items"] == []
    feed = (await client.get(f"{BASE}/phc/alerts", headers=wh)).json()
    assert {i["citizen"]["name"] for i in feed["items"]} == {"Priya B"}


async def test_a_foreign_id_is_indistinguishable_from_an_unknown_one(client, world):
    foreign, fh = world["foreign"]
    _, wh = world["worker"]
    await submit(client, fh, HIGH_BP)
    foreign_case = (await client.get(f"{BASE}/phc/queue", headers=world["other_worker"][1])).json()["items"][0]

    for path in ("/phc/citizens/{}/record",):
        a = await client.get(BASE + path.format(foreign.id), headers=wh)
        b = await client.get(BASE + path.format(uuid.uuid4()), headers=wh)
        assert a.status_code == b.status_code == 404 and a.json() == b.json()
    a = await client.post(f"{BASE}/phc/worklist/citizens/{foreign.id}/resolve", headers=wh)
    b = await client.post(f"{BASE}/phc/worklist/citizens/{uuid.uuid4()}/resolve", headers=wh)
    assert a.status_code == b.status_code == 404 and a.json() == b.json()
    a = await client.post(f"{BASE}/phc/queue/{foreign_case['processed_id']}/seen", headers=wh)
    b = await client.post(f"{BASE}/phc/queue/{uuid.uuid4()}/seen", headers=wh)
    assert a.status_code == b.status_code == 404 and a.json() == b.json()
    a = await client.post(
        f"{BASE}/phc/visits",
        json={"citizen_id": str(foreign.id), "scheduled_for": (utcnow() + timedelta(days=1)).isoformat()},
        headers=wh,
    )
    assert a.status_code == 404


async def test_a_worker_without_a_facility_gets_409(client, db):
    _, headers = await make_user(db, UserRole.phc_worker, None, "Unlinked")
    for path in ("/phc/dashboard", "/phc/queue", "/phc/citizens", "/schedule", "/phc-alerts/unread-count"):
        r = await client.get(BASE + path, headers=headers)
        assert r.status_code == 409, path
        assert isinstance(r.json()["detail"], str)


async def test_citizens_cannot_use_worker_routes(client, world):
    _, ph = world["priya"]
    assert (await client.get(f"{BASE}/phc/dashboard", headers=ph)).status_code == 403


async def test_clear_one_case_and_resolve_a_citizen(client, db, world):
    priya, ph = world["priya"]
    worker, wh = world["worker"]
    await submit(client, ph, HIGH_BP)
    await submit(client, ph, {"temperature_c": 39.2})
    await submit(client, ph, {"spo2": 90})
    queue = (await client.get(f"{BASE}/phc/queue", headers=wh)).json()
    assert queue["total"] == 3
    scores = [i["anomaly_score"] for i in queue["items"]]
    assert scores == sorted(scores, reverse=True)  # worst first

    first = queue["items"][0]["processed_id"]
    assert (await client.post(f"{BASE}/phc/queue/{first}/seen", headers=wh)).json()["cleared"] == 1
    assert (await client.post(f"{BASE}/phc/queue/{first}/seen", headers=wh)).status_code == 409
    reviewed_by = await db.scalar(text("SELECT reviewed_by FROM processed_data WHERE id = :i"), {"i": first})
    assert reviewed_by == worker.id

    r = await client.post(
        f"{BASE}/phc/worklist/citizens/{priya.id}/resolve",
        json={"resolution": "dismissed", "dismiss_reason": "contacted", "note": "Called, feeling fine"},
        headers=wh,
    )
    assert r.json()["cleared"] == 2
    assert (await client.get(f"{BASE}/phc/queue", headers=wh)).json()["total"] == 0


async def test_directory_counts_describe_the_whole_catchment(client, db, world):
    _, ph = world["priya"]
    ravi, _ = world["ravi"]
    _, wh = world["worker"]
    await submit(client, ph, HIGH_BP)

    full = (await client.get(f"{BASE}/phc/citizens", headers=wh)).json()
    assert full["counts"] == {"attention": 1, "never_logged": 1, "silent": 0, "ok": 0}
    assert [i["status"] for i in full["items"]] == ["attention", "never_logged"]

    filtered = (await client.get(f"{BASE}/phc/citizens", params={"status": "never_logged"}, headers=wh)).json()
    assert [i["citizen"]["name"] for i in filtered["items"]] == ["Ravi K"]
    assert filtered["counts"] == full["counts"] and filtered["total"] == 1
    by_ref = (await client.get(f"{BASE}/phc/citizens", params={"q": f"HN-{ravi.id.hex[:8]}"}, headers=wh)).json()
    assert [i["citizen"]["name"] for i in by_ref["items"]] == ["Ravi K"]


async def test_record_page_describes_one_window(client, db, world):
    priya, ph = world["priya"]
    _, wh = world["worker"]
    old = (utcnow() - timedelta(days=20)).isoformat()
    await submit(client, ph, HIGH_BP, measured_at=old)
    await submit(client, ph, NORMAL)
    r = await client.get(f"{BASE}/phc/citizens/{priya.id}/record", params={"days": 7}, headers=wh)
    body = r.json()
    assert body["identity"]["name"] == "Priya B" and body["identity"]["phone"]
    assert body["window"]["days"] == 7
    assert body["counts"]["readings"] == 1 and len(body["timeline"]) == 1
    assert body["counts"]["flags"] == 0
    assert body["unresolved_before_window"]["open_flags"] == 1  # reported beside the window, not in it
    assert (await client.get(f"{BASE}/phc/citizens/{priya.id}/record", params={"days": "abc"}, headers=wh)).status_code == 422


async def test_aggregate_pages_carry_no_names(client, world):
    _, ph = world["priya"]
    _, wh = world["worker"]
    await submit(client, ph, HIGH_BP)
    for path in ("/phc/reports", "/phc/map", "/phc/locality-risk", "/phc/overview"):
        r = await client.get(BASE + path, headers=wh)
        assert r.status_code == 200, (path, r.text)
        assert "Priya" not in r.text and "Ravi" not in r.text
    # Two citizens in two localities: both below the minimum cell size, so neither is shown on its own.
    risk = (await client.get(f"{BASE}/phc/locality-risk", headers=wh)).json()
    assert all(i["locality"] not in ("Luz", "Mandaveli") for i in risk["items"])
    overview = (await client.get(f"{BASE}/phc/overview", headers=wh)).json()
    assert len(overview["kpis"]) == 4 and all(len(k["weeks"]) == 8 for k in overview["kpis"])
    assert overview["kpis"][0]["weeks"][-1]["partial"] is True


# --- Phase 3 -------------------------------------------------------------------


async def test_the_scheduling_loop(client, db, world):
    priya, ph = world["priya"]
    worker, wh = world["worker"]
    case = (await submit(client, ph, HIGH_BP)).json()
    processed = (await client.get(f"{BASE}/phc/queue", headers=wh)).json()["items"][0]["processed_id"]

    when = utcnow() + timedelta(days=2)
    r = await client.post(
        f"{BASE}/phc/visits",
        json={"citizen_id": str(priya.id), "case_id": processed, "scheduled_for": when.isoformat(), "reason": "BP check"},
        headers=wh,
    )
    assert r.status_code == 201, r.text
    visit_id = r.json()["id"]
    assert r.json()["state"] == "upcoming"
    assert case["flagged"] and (await client.get(f"{BASE}/phc/queue", headers=wh)).json()["total"] == 0

    # Both sides told, each in their own words.
    citizen_msgs = [a.message for a in await db.scalars(select(Alert).where(Alert.user_id == priya.id))]
    worker_msgs = [a.message for a in await db.scalars(select(Alert).where(Alert.user_id == worker.id))]
    assert any("will visit you" in m for m in citizen_msgs)
    assert not any("Priya" in m for m in citizen_msgs)
    assert any(m.startswith("Visit booked for Priya B") for m in worker_msgs)

    mine = (await client.get(f"{BASE}/schedule/mine", headers=ph)).json()["visits"]
    assert [(v["state"], v["worker_name"]) for v in mine] == [("upcoming", "Kavitha Raman")]
    assert (await client.patch(f"{BASE}/schedule/{visit_id}", json={"action": "miss"}, headers=wh)).status_code == 409

    # Time passes beyond the grace window with no outcome.
    await db.execute(
        update(ScheduledVisit).where(ScheduledVisit.id == uuid.UUID(visit_id)).values(scheduled_for=utcnow() - timedelta(hours=5))
    )
    await db.commit()
    schedule = (await client.get(f"{BASE}/schedule", headers=wh)).json()
    assert schedule["counts"] == {"needs_outcome": 1, "happening_now": 0, "today": 0, "upcoming": 0, "recent_outcomes": 0}
    mine = (await client.get(f"{BASE}/schedule/mine", headers=ph)).json()["visits"]
    assert mine[0]["state"] == "overdue"

    async def missed_alerts(user_id):
        return [
            m for m in await db.scalars(select(Alert.message).where(Alert.user_id == user_id)) if "outcome" in m
        ]

    await client.get(f"{BASE}/schedule", headers=wh)  # loading again must not send it twice
    assert len(await missed_alerts(priya.id)) == 1 and len(await missed_alerts(worker.id)) == 1

    r = await client.patch(f"{BASE}/schedule/{visit_id}", json={"action": "complete"}, headers=wh)
    assert r.json()["status"] == "completed"
    assert (await client.get(f"{BASE}/schedule/mine", headers=ph)).json()["visits"][0]["state"] == "completed"
    assert (await client.get(f"{BASE}/schedule", headers=wh)).json()["counts"]["recent_outcomes"] == 1
    assert (await client.patch(f"{BASE}/schedule/{visit_id}", json={"action": "cancel"}, headers=wh)).status_code == 409


async def test_schedule_buckets_are_disjoint(client, db, world):
    priya, _ = world["priya"]
    worker, wh = world["worker"]
    db.add(ScheduledVisit(worker_id=worker.id, citizen_id=priya.id, scheduled_for=utcnow() - timedelta(hours=1)))
    await db.commit()
    counts = (await client.get(f"{BASE}/schedule", headers=wh)).json()["counts"]
    assert counts == {"needs_outcome": 0, "happening_now": 1, "today": 0, "upcoming": 0, "recent_outcomes": 0}


async def test_switching_centre_moves_the_citizen_out_of_the_old_catchment(client, db, world):
    priya, ph = world["priya"]
    _, wh = world["worker"]
    _, owh = world["other_worker"]
    await client.post(
        f"{BASE}/phc/visits",
        json={"citizen_id": str(priya.id), "scheduled_for": (utcnow() + timedelta(days=1)).isoformat()},
        headers=wh,
    )
    r = await client.patch(f"{BASE}/settings/health-centre", json={"phc_id": str(world["adyar"].id)}, headers=ph)
    assert r.status_code == 200 and r.json()["current"]["name"] == "Adyar PHC"
    assert (await client.get(f"{BASE}/phc/citizens/{priya.id}/record", headers=wh)).status_code == 404
    assert (await client.get(f"{BASE}/phc/citizens/{priya.id}/record", headers=owh)).status_code == 200
    assert (await client.get(f"{BASE}/schedule/mine", headers=ph)).json()["visits"][0]["state"] == "cancelled"
    tambaram = await facility(db, "Tambaram PHC")  # another district
    r = await client.patch(f"{BASE}/settings/health-centre", json={"phc_id": str(tambaram.id)}, headers=ph)
    assert r.status_code == 422


async def test_settings_and_support(client, world):
    _, ph = world["priya"]
    _, rh = world["ravi"]
    r = await client.patch(f"{BASE}/settings/preferences", json={"theme": "dark", "notifications": {"visits": {"email": False}}}, headers=ph)
    assert r.status_code == 200 and r.json()["theme"] == "dark" and r.json()["notifications"]["visits"]["email"] is False
    assert r.json()["notifications"]["alerts"]["email"] is True
    # Retired settings are refused rather than silently stored.
    r = await client.patch(f"{BASE}/settings/preferences", json={"notifications": {"alerts": {"sms": True}}}, headers=ph)
    assert r.status_code == 422
    assert (await client.patch(f"{BASE}/settings/preferences", json={"language": "ta"}, headers=ph)).json()["language"] == "ta"
    assert (await client.patch(f"{BASE}/settings/preferences", json={"language": "fr"}, headers=ph)).status_code == 422
    kept = (await client.get(f"{BASE}/settings/preferences", headers=ph)).json()
    assert kept["theme"] == "dark" and kept["notifications"]["visits"]["email"] is False  # earlier choices kept
    r = await client.patch(f"{BASE}/settings/preferences", json={"working_hours": {"start": "18:00", "end": "09:00"}}, headers=ph)
    assert r.status_code == 422

    r = await client.patch(
        f"{BASE}/settings/consents", json={"consents": [{"consent_type": "health_tracking", "granted": False}]}, headers=ph
    )
    assert r.json()["consents"]["health_tracking"] is False
    assert (await submit(client, ph, NORMAL)).status_code == 403  # tracking off: nothing is stored
    assert len((await client.get(f"{BASE}/settings/consents/history", headers=ph)).json()) == 1

    concern = (
        await client.post(
            f"{BASE}/settings/concerns", json={"category": "other", "description": "Please check my flag"}, headers=ph
        )
    ).json()
    assert (await client.get(f"{BASE}/settings/concerns/{concern['id']}", headers=ph)).status_code == 200
    assert (await client.get(f"{BASE}/settings/concerns/{concern['id']}", headers=rh)).status_code == 404

    export = await client.get(f"{BASE}/settings/export", headers=ph)
    assert "attachment" in export.headers["content-disposition"]
    assert "hashed_password" not in export.text


async def test_password_change_and_profile(client, world):
    _, ph = world["priya"]
    r = await client.post(f"{BASE}/settings/password", json={"current_password": "wrong", "new_password": "another good pass"}, headers=ph)
    assert r.status_code == 400
    r = await client.post(f"{BASE}/settings/password", json={"current_password": PASSWORD, "new_password": "another good pass 2"}, headers=ph)
    assert r.status_code == 200, r.text

    r = await client.patch(f"{BASE}/profile", json={"bio": "Teacher", "phone": "not a phone"}, headers=ph)
    assert r.status_code == 422
    r = await client.patch(f"{BASE}/profile", json={"bio": "Teacher"}, headers=ph)
    assert r.json()["bio"] == "Teacher"
    r = await client.post(f"{BASE}/profile/avatar", files={"file": ("a.png", b"not an image", "image/png")}, headers=ph)
    assert r.status_code == 415


# --- Anomaly model: score breakdown and baselines -------------------------------


async def test_scores_explain_themselves_and_baselines_build_up(client, world):
    priya, ph = world["priya"]
    _, wh = world["worker"]
    start = utcnow() - timedelta(days=20)
    for day in range(8):
        reading = {**NORMAL, "heart_rate": 68 + day % 3}
        r = await submit(client, ph, reading, measured_at=(start + timedelta(days=day)).isoformat())
        assert r.status_code == 201, r.text

    status = (await client.get(f"{BASE}/health/baseline", headers=ph)).json()
    heart = next(v for v in status["vitals"] if v["key"] == "heart_rate")
    assert heart["readings"] == 8 and heart["stage"] == "blending"
    assert heart["baseline"] is not None and heart["readings_to_full"] == status["full_readings"] - 8

    r = (await submit(client, ph, NORMAL)).json()
    assert r["flagged"] is False and r["basis"] == "personal_baseline"
    assert r["model_version"] and r["watch"] == []
    check = next(c for c in r["checks"] if c["key"] == "heart_rate")
    assert check["stage"] == "blending" and check["readings"] == 8 and check["contribution"] == 0

    flagged = (await submit(client, ph, HIGH_BP)).json()
    assert flagged["flagged"] is True
    assert any(c["safety"] for c in flagged["checks"] if c["key"] in ("systolic", "diastolic"))

    record = (await client.get(f"{BASE}/phc/citizens/{priya.id}/record", headers=wh)).json()
    newest = record["timeline"][0]
    assert newest["flagged"] and newest["basis"] == "personal_baseline" and newest["checks"]
    rhr = next(v for v in record["vitals"] if v["key"] == "heart_rate")
    assert rhr["baseline"]["usual"] > 0 and rhr["baseline"]["spread"] >= 4.0


async def test_each_reading_carries_the_population_check(client, world):
    _, ph = world["priya"]
    _, wh = world["worker"]
    result = (await submit(client, ph, {"heart_rate": 72, "respiratory_rate": 15, "systolic": 165, "diastolic": 101})).json()
    assert result["population"]["version"] == "population-iforest-v1"
    assert result["population"]["unusual"] is False and result["population"]["note"].startswith("Typical")
    history = (await client.get(f"{BASE}/health/history", headers=ph)).json()["items"]
    assert history[0]["population"] == result["population"]
    case = (await client.get(f"{BASE}/phc/queue", headers=wh)).json()["items"][0]
    assert case["population"]["score"] == result["population"]["score"]
    # A reading without heart rate or breathing rate has nothing for the model to look at.
    assert (await submit(client, ph, {"systolic": 118, "diastolic": 76})).json()["population"] is None
