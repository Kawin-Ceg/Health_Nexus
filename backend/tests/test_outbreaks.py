from app.models.enums import ConsentType, UserRole
from app.services import outbreaks
from app.services.consent import record_consents

from .conftest import BASE
from .test_modules import make_user, submit, world  # noqa: F401

FEVER = {"temperature_c": 38.6, "heart_rate": 96}


async def neighbours(db, world, n, *, consent=True, area="Mandaveli"):
    people = []
    for i in range(n):
        user, headers = await make_user(db, UserRole.user, world["mylapore"], f"{area} {i}", area=area)
        user.geo_lat, user.geo_lng = 13.029 + i * 0.001, 80.261 + i * 0.001
        if consent:
            await record_consents(db, user.id, {ConsentType.community_surveillance: True}, source="test", ip_address=None)
        people.append((user, headers))
    await db.commit()
    return people


async def test_a_fever_cluster_is_found_and_flagged(client, db, world):
    _, wh = world["worker"]
    _, owh = world["other_worker"]
    for _, headers in await neighbours(db, world, 4):
        await submit(client, headers, FEVER, symptoms=["fever"])
    for _, headers in await neighbours(db, world, 3, consent=False, area="Luz"):
        await submit(client, headers, FEVER, symptoms=["fever"])

    await outbreaks.run(db)
    out = (await client.get(f"{BASE}/clusters", headers=wh)).json()
    assert len(out["items"]) == 1
    c = out["items"][0]
    assert (c["syndrome"], c["cases"], c["region"]) == ("febrile", 4, "Mandaveli")
    assert c["outbreak"] and c["p_value"] < 0.01 and c["yours"]
    assert "Mandaveli 0" not in str(out)

    assert (await client.get(f"{BASE}/clusters", headers=owh)).json()["items"] == []
    assert (await client.post(f"{BASE}/clusters/{c['id']}/acknowledge", headers=owh)).status_code == 404
    acked = (await client.post(f"{BASE}/clusters/{c['id']}/acknowledge", headers=wh)).json()
    assert acked["acknowledged_by"] == "Kavitha Raman"

    notice = {"scope": "centre", "title": "Fever in Mandaveli", "body": "See a doctor if a fever lasts two days.", "cluster_id": c["id"]}
    assert (await client.post(f"{BASE}/advisories", json=notice, headers=wh)).status_code == 201
    assert (await client.get(f"{BASE}/clusters", headers=wh)).json()["items"][0]["advisory_id"]


async def test_two_people_are_not_a_cluster(client, db, world):
    _, wh = world["worker"]
    for _, headers in await neighbours(db, world, 2):
        await submit(client, headers, FEVER, symptoms=["fever"])
    await outbreaks.run(db)
    out = (await client.get(f"{BASE}/clusters", headers=wh)).json()
    assert out["items"] == [] and out["last_run_at"] is not None


async def test_citizens_and_workers_permissions(client, db, world):
    _, ph = world["priya"]
    _, wh = world["worker"]
    assert (await client.get(f"{BASE}/clusters", headers=ph)).status_code == 403
    assert (await client.post(f"{BASE}/clusters/run", headers=wh)).status_code == 403
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    assert (await client.post(f"{BASE}/clusters/run", headers=ah)).status_code == 200
