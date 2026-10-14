from app.models.enums import UserRole

from .conftest import BASE
from .test_modules import make_user, world  # noqa: F401

NOTICE = {"title": "Dengue precautions", "body": "Empty standing water around your home every week.", "severity": "high"}


async def advisories(client, headers):
    return (await client.get(f"{BASE}/alerts", headers=headers)).json()["advisories"]


async def test_a_worker_writes_to_their_own_centre(client, world):
    _, wh = world["worker"]
    _, ph = world["priya"]
    _, fh = world["foreign"]
    r = await client.post(f"{BASE}/advisories", json={**NOTICE, "scope": "centre"}, headers=wh)
    assert r.status_code == 201, r.text
    made = r.json()
    assert made["audience"] == "Mylapore PHC" and made["reach"] == 2 and made["can_withdraw"]

    assert [a["title"] for a in await advisories(client, ph)] == ["Dengue precautions"]
    assert await advisories(client, fh) == []

    r = await client.post(f"{BASE}/advisories", json={**NOTICE, "scope": "district", "district": "Chennai"}, headers=wh)
    assert r.status_code == 403

    _, owh = world["other_worker"]
    assert (await client.post(f"{BASE}/advisories/{made['id']}/withdraw", headers=owh)).status_code == 404
    r = await client.post(f"{BASE}/advisories/{made['id']}/withdraw", headers=wh)
    assert r.json()["active"] is False
    assert await advisories(client, ph) == []


async def test_an_admin_writes_to_a_district(client, db, world):
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    _, ph = world["priya"]
    _, fh = world["foreign"]
    r = await client.post(f"{BASE}/advisories", json={**NOTICE, "scope": "district", "district": "chennai", "days": 3}, headers=ah)
    assert r.status_code == 201, r.text
    assert r.json()["audience"] == "Chennai district" and r.json()["reach"] == 3
    assert len(await advisories(client, ph)) == 1 and len(await advisories(client, fh)) == 1

    r = await client.post(f"{BASE}/advisories", json={**NOTICE, "scope": "district", "district": "Atlantis"}, headers=ah)
    assert r.status_code == 422
    listed = (await client.get(f"{BASE}/advisories", headers=ah)).json()["items"]
    assert len(listed) == 1


async def test_citizens_cannot_publish(client, world):
    _, ph = world["priya"]
    assert (await client.post(f"{BASE}/advisories", json={**NOTICE, "scope": "centre"}, headers=ph)).status_code == 403
