"""The assistant: scoped SQL retrieval, refusals, sessions. Runs on the rule-based engine (no Gemini)."""

import pytest

from app.core.config import get_settings
from app.models.enums import UserRole
from app.services import assistant
from app.services.assistant import llm
from app.services.assistant.catalog import TOOLS, Tool

from .conftest import BASE
from .test_modules import HIGH_BP, NORMAL, make_user, submit, world  # noqa: F401  (world is a fixture)


@pytest.fixture(autouse=True)
def rules_only(monkeypatch):
    monkeypatch.setattr(llm, "enabled", lambda: False)


async def ask(client, headers, content, session_id=None):
    r = await client.post(f"{BASE}/assistant/ask", json={"content": content, "session_id": session_id}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_every_catalog_query_runs(world, db):
    """Each tool's SQL is valid against the migrated schema, with its default parameters."""
    users = {
        UserRole.user: world["priya"][0],
        UserRole.phc_worker: world["worker"][0],
        UserRole.admin: (await make_user(db, UserRole.admin, None, "Admin"))[0],
    }
    for tool in TOOLS:
        role = next(iter(tool.roles))
        args = {k: p.clean(None) for k, p in tool.params.items()}
        if tool.name == "citizen_summary":
            args["name"] = "Priya"
        await assistant.retrieve(tool, args, users[role], db.bind)


async def test_retrieval_is_read_only(world, db):
    sneaky = Tool(name="x", roles=frozenset({UserRole.user}), title="x", description="x", sql="UPDATE users SET name = 'x'")
    with pytest.raises(Exception, match="read-only"):
        await assistant.retrieve(sneaky, {}, world["priya"][0], db.bind)


async def test_citizen_answers_come_from_their_own_readings(client, world):
    _, ph = world["priya"]
    first = await ask(client, ph, "Is my latest blood pressure normal?")
    assert first["answer"]["was_refused"] and first["answer"]["refusal_reason"] == "insufficient_history"

    assert (await submit(client, ph, HIGH_BP)).status_code == 201
    out = await ask(client, ph, "Is my latest blood pressure normal?", first["session"]["id"])
    answer = out["answer"]
    assert not answer["was_refused"]
    assert "167/103" in answer["content"] and "above normal" in answer["content"]
    assert answer["retrieval"]["tool"] == "my_latest_reading"
    assert ":me" in answer["generated_sql"]
    assert out["session"]["title"].startswith("Is my latest blood pressure")

    flags = await ask(client, ph, "Were any of my readings flagged this month?")
    assert flags["answer"]["retrieval"]["tool"] == "my_flags"
    assert flags["answer"]["retrieval"]["row_count"] == 1


async def test_a_citizen_never_sees_another_citizens_data(client, world):
    _, ph = world["priya"]
    _, rh = world["ravi"]
    await submit(client, ph, HIGH_BP)
    out = await ask(client, rh, "Were any of my readings flagged?")
    assert out["answer"]["retrieval"]["row_count"] == 0
    assert "None of your readings" in out["answer"]["content"]


async def test_worker_sees_their_catchment_only(client, world):
    _, ph = world["priya"]
    _, fh = world["foreign"]
    await submit(client, ph, HIGH_BP)
    await submit(client, fh, HIGH_BP)

    _, wh = world["worker"]
    out = await ask(client, wh, "Which citizens need attention?")
    assert out["answer"]["retrieval"]["tool"] == "flagged_citizens"
    assert "Priya B" in out["answer"]["content"]
    assert "Foreign Citizen" not in out["answer"]["content"]

    lookup = await ask(client, wh, "How is Priya doing?")
    assert lookup["answer"]["retrieval"]["tool"] == "citizen_summary"
    assert "Priya B" in lookup["answer"]["content"]
    outside = await ask(client, wh, "Tell me about Foreign Citizen")
    assert outside["answer"]["refusal_reason"] == "no_matching_records"

    _, owh = world["other_worker"]
    theirs = await ask(client, owh, "Which citizens need attention?")
    assert "Priya B" not in theirs["answer"]["content"]
    assert "Foreign Citizen" in theirs["answer"]["content"]


async def test_admin_gets_aggregates_not_readings(client, world, db):
    _, ah = await make_user(db, UserRole.admin, None, "Admin")
    out = await ask(client, ah, "Give me a platform overview")
    assert out["answer"]["retrieval"]["tool"] == "platform_overview"
    assert "citizens" in out["answer"]["content"]
    # No admin tool reads health_records rows by person.
    readings = await ask(client, ah, "Show me Priya's latest blood pressure reading")
    assert readings["answer"]["retrieval"] is None or readings["answer"]["retrieval"]["tool"] != "my_latest_reading"


async def test_medical_advice_is_declined_and_emergencies_get_108(client, world):
    _, ph = world["priya"]
    advice = await ask(client, ph, "What medicine should I take for my blood pressure?")
    assert advice["answer"]["refusal_reason"] == "out_of_scope"
    urgent = await ask(client, ph, "I have chest pain and can't breathe")
    assert "108" in urgent["answer"]["content"]


async def test_follow_up_reuses_the_previous_question(client, world):
    _, ph = world["priya"]
    await submit(client, ph, NORMAL)
    first = await ask(client, ph, "What were my average vitals over the last 30 days?")
    assert first["answer"]["retrieval"]["args"]["days"] == 30
    again = await ask(client, ph, "and over the last 7 days?", first["session"]["id"])
    assert again["answer"]["retrieval"]["tool"] == "my_vital_stats"
    assert again["answer"]["retrieval"]["args"]["days"] == 7


async def test_sessions_are_private(client, world):
    _, ph = world["priya"]
    _, rh = world["ravi"]
    out = await ask(client, ph, "hello")
    sid = out["session"]["id"]
    assert (await client.get(f"{BASE}/assistant/sessions/{sid}", headers=rh)).status_code == 404
    assert (await client.post(f"{BASE}/assistant/ask", json={"content": "hi", "session_id": sid}, headers=rh)).status_code == 404
    detail = (await client.get(f"{BASE}/assistant/sessions/{sid}", headers=ph)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert (await client.delete(f"{BASE}/assistant/sessions/{sid}", headers=ph)).status_code == 204
    assert (await client.get(f"{BASE}/assistant/sessions", headers=ph)).json() == []


async def test_the_model_cannot_widen_its_scope(client, world, monkeypatch):
    """Whatever Gemini returns is checked: only the caller's role's tools, cleaned arguments, template on failure."""
    monkeypatch.setattr(llm, "enabled", lambda: True)
    picks = iter([("flagged_citizens", {}), ("my_vital_stats", {"days": 99999, "me": "someone-else"})])

    async def choose(role, question, tools, history, usage):
        return next(picks)

    async def write(*args, **kwargs):
        raise RuntimeError("quota")

    monkeypatch.setattr(llm, "choose_tool", choose)
    monkeypatch.setattr(llm, "write_answer", write)
    _, ph = world["priya"]
    await submit(client, ph, NORMAL)

    # A worker-only tool chosen for a citizen is ignored; the rules answer instead.
    first = await ask(client, ph, "Is my latest blood pressure normal?")
    assert first["answer"]["retrieval"]["tool"] == "my_latest_reading"
    # Out-of-range and undeclared arguments are dropped or clamped; the answer falls back to the template.
    second = await ask(client, ph, "What were my average vitals?")
    assert second["answer"]["retrieval"]["args"] == {"days": 365}
    assert second["answer"]["retrieval"]["engine"] == "gemini+template"
    assert "Over the last 365 days" in second["answer"]["content"]


async def test_questions_are_rate_limited(client, world, monkeypatch):
    monkeypatch.setattr(get_settings(), "ASSISTANT_QUESTIONS_PER_MINUTE", 2)
    _, ph = world["priya"]
    await ask(client, ph, "hi")
    await ask(client, ph, "hi")
    r = await client.post(f"{BASE}/assistant/ask", json={"content": "hi"}, headers=ph)
    assert r.status_code == 429
