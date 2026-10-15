"""Consents do what the privacy screen says: worker access, community monitoring and research use."""

import csv
import io
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import Alert, ScheduledVisit
from app.models.base import utcnow
from app.models.enums import ConsentType, UserRole, VisitStatus
from app.services import assistant
from app.services.assistant import llm
from app.services.consent import record_consents

from .conftest import BASE
from .test_modules import HIGH_BP, NORMAL, make_user, submit, world  # noqa: F401  (world is a fixture)


@pytest.fixture(autouse=True)
def rules_only(monkeypatch):
    monkeypatch.setattr(llm, "enabled", lambda: False)


async def set_consent(client, headers, consent_type: str, granted: bool):
    r = await client.patch(
        f"{BASE}/settings/consents", json={"consents": [{"consent_type": consent_type, "granted": granted}]}, headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()["consents"]


async def test_turning_off_worker_access_hides_the_citizen(client, db, world):
    priya, ph = world["priya"]
    worker, wh = world["worker"]
    await submit(client, ph, HIGH_BP)
    db.add(ScheduledVisit(worker_id=worker.id, citizen_id=priya.id, scheduled_for=utcnow() + timedelta(days=2)))
    await db.commit()

    await set_consent(client, ph, "phc_worker_access", False)

    assert (await client.get(f"{BASE}/phc/queue", headers=wh)).json()["items"] == []
    directory = (await client.get(f"{BASE}/phc/citizens", params={"q": "Priya"}, headers=wh)).json()
    assert directory["items"] == []
    assert (await client.get(f"{BASE}/phc/citizens/{priya.id}/record", headers=wh)).status_code == 404
    # The booked visit is cancelled, and both sides are told.
    visit = await db.scalar(select(ScheduledVisit).where(ScheduledVisit.citizen_id == priya.id))
    await db.refresh(visit)
    assert visit.status == VisitStatus.cancelled
    # A new flag says honestly that nobody at the centre will see it.
    flagged = (await submit(client, ph, HIGH_BP)).json()
    assert flagged["flagged"] and flagged["reviewed_by_someone"] is False
    newest = await db.scalar(select(Alert).where(Alert.user_id == priya.id).order_by(Alert.created_at.desc()))
    assert "turned off health worker access" in newest.message
    about = (await client.get(f"{BASE}/settings/about", headers=ph)).json()
    assert about["who_can_see"].startswith("Nobody at")

    # The assistant follows the same rule.
    out = await assistant_answer(client, wh, "Which citizens need attention?")
    assert "Priya B" not in out

    await set_consent(client, ph, "phc_worker_access", True)
    assert len((await client.get(f"{BASE}/phc/queue", headers=wh)).json()["items"]) == 2


async def assistant_answer(client, headers, content) -> str:
    r = await client.post(f"{BASE}/assistant/ask", json={"content": content}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["answer"]["content"]


async def test_never_answering_worker_access_keeps_the_centre_link(client, world):
    _, ph = world["priya"]
    _, wh = world["worker"]
    await submit(client, ph, HIGH_BP)
    assert [i["citizen"]["name"] for i in (await client.get(f"{BASE}/phc/queue", headers=wh)).json()["items"]] == ["Priya B"]


async def test_area_figures_count_only_community_consent(client, db, world):
    mylapore = world["mylapore"]
    _, wh = world["worker"]
    people = [await make_user(db, UserRole.user, mylapore, f"Luz {i}", area="Luz") for i in range(4)]
    for user, headers in people:
        await submit(client, headers, HIGH_BP)
    for user, _ in people[:3]:
        await record_consents(db, user.id, {ConsentType.community_surveillance: True}, source="test", ip_address=None)
    await db.commit()

    risk = (await client.get(f"{BASE}/phc/locality-risk", headers=wh)).json()["items"]
    luz = next(i for i in risk if i["locality"] == "Luz")
    assert (luz["citizens"], luz["flagged"]) == (3, 3)

    # One of the three withdraws: Luz drops below the minimum cell and is no longer shown.
    await set_consent(client, people[0][1], "community_surveillance", False)
    risk = (await client.get(f"{BASE}/phc/locality-risk", headers=wh)).json()["items"]
    assert all(i["locality"] != "Luz" for i in risk)
    reports = (await client.get(f"{BASE}/phc/reports", headers=wh)).json()
    assert all(i["locality"] != "Luz" for i in reports["localities"])


async def test_research_export_holds_only_consenting_people(client, db, world):
    priya, ph = world["priya"]
    _, rh = world["ravi"]
    admin, ah = await make_user(db, UserRole.admin, None, "Admin")
    await submit(client, ph, NORMAL)
    await submit(client, rh, HIGH_BP)
    await set_consent(client, ph, "research_analytics", True)

    r = await client.get(f"{BASE}/admin/research-export", headers=ah)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 1
    row = rows[0]
    assert float(row["systolic"]) == 112 and row["age_band"] == "40-49" and row["flagged"] == "0"
    # Below the minimum cell, the district is not given.
    assert row["district"] == "Other"
    assert "Priya" not in r.text and str(priya.id) not in r.text
    assert (await client.get(f"{BASE}/admin/research-export", headers=ph)).status_code == 403


async def test_marketing_consent_is_no_longer_asked(client, world):
    _, ph = world["priya"]
    consents = (await client.get(f"{BASE}/settings/consents", headers=ph)).json()["consents"]
    assert "marketing_updates" not in consents
    r = await client.patch(
        f"{BASE}/settings/consents", json={"consents": [{"consent_type": "marketing_updates", "granted": True}]}, headers=ph
    )
    assert r.status_code == 422


async def test_area_level_assistant_tools_skip_non_consenting(db, world):
    worker = world["worker"][0]
    tool = next(t for t in assistant.catalog.TOOLS if t.name == "locality_breakdown")
    assert await assistant.retrieve(tool, {}, worker, db.bind) == []
