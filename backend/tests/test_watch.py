from datetime import datetime

from app.services.visit_state import LOCAL_TZ
from app.services.watch import slot_at

from .conftest import BASE
from .test_modules import NORMAL, world  # noqa: F401


def test_a_day_has_four_slots():
    at = lambda h: datetime(2026, 10, 16, h, 30, tzinfo=LOCAL_TZ)  # noqa: E731
    assert [slot_at(at(h))[0].key for h in (6, 13, 18, 22)] == ["morning", "afternoon", "evening", "night"]
    slot, day = slot_at(at(2))
    assert slot.key == "night" and day.isoformat() == "2026-10-15"


async def test_sync_once_per_slot(client, world):
    _, ph = world["priya"]
    assert (await client.post(f"{BASE}/health/watch/sync", headers=ph)).status_code == 409
    state = (await client.post(f"{BASE}/health/watch/connect", json={"brand": "Noise"}, headers=ph)).json()
    assert state["connected"] and state["brand"] == "Noise" and len(state["slots"]) == 4

    first = await client.post(f"{BASE}/health/watch/sync", headers=ph)
    assert first.status_code == 201, first.text
    body = first.json()
    assert not body["already_synced"] and body["reading"]["source"] == "watch"
    assert set(body["reading"]["vitals"]) == {"heart_rate", "spo2", "respiratory_rate", "temperature_c"}

    again = await client.post(f"{BASE}/health/watch/sync", headers=ph)
    assert again.status_code == 200 and again.json()["already_synced"]
    assert again.json()["reading"]["id"] == body["reading"]["id"]

    state = (await client.get(f"{BASE}/health/watch", headers=ph)).json()
    current = next(s for s in state["slots"] if s["key"] == state["current_slot"])
    assert current["reading_id"] == body["reading"]["id"]
    assert (await client.get(f"{BASE}/health/history", headers=ph)).json()["total"] == 1
    assert (await client.post(f"{BASE}/health/vitals", json={"vitals": NORMAL}, headers=ph)).status_code in (404, 405)


async def test_a_worker_records_an_examination(client, world):
    _, ph = world["priya"]
    priya, _ = world["priya"]
    _, wh = world["worker"]
    _, owh = world["other_worker"]
    body = {"vitals": {"systolic": 150, "diastolic": 96, "heart_rate": 88}, "symptoms": ["headache"], "location": "Priya's home, Luz"}
    r = await client.post(f"{BASE}/phc/citizens/{priya.id}/readings", json=body, headers=wh)
    assert r.status_code == 201, r.text
    assert r.json()["source"] == "phc"
    assert (await client.post(f"{BASE}/phc/citizens/{priya.id}/readings", json=body, headers=owh)).status_code == 404
    assert (await client.post(f"{BASE}/phc/citizens/{priya.id}/readings", json={**body, "location": ""}, headers=wh)).status_code == 422

    item = (await client.get(f"{BASE}/health/history", headers=ph)).json()["items"][0]
    assert item["source"] == "phc" and item["recorded_by"] == "Kavitha Raman, Mylapore PHC"
    assert item["location"] == "Priya's home, Luz"
    assert (await client.delete(f"{BASE}/health/readings/{item['id']}", headers=ph)).status_code == 409
