import json
import statistics as st

from lib import ROOT, bullets, chain, chapter, files, flow, functions, h2, kpis, note, p, pre, qa, ref, table

BE, FE, AS = "backend/app/", "frontend/src/", "backend/app/services/assistant/"
M = json.loads((ROOT / "docs/rag_guide/measurements.json").read_text(encoding="utf-8"))


def _loc(path: str) -> int:
    return len((ROOT / path).read_text(encoding="utf-8").split("\n"))


def _tree() -> str:
    rows = [
        ("backend/app/services/assistant/", "", "THE PACKAGE: the whole RAG pipeline"),
        ("  __init__.py", _loc(AS + "__init__.py"), "the conductor: safety, plan, retrieve, generate, verify, store"),
        ("  router.py", _loc(AS + "router.py"), "safety rules and the keyword planner (fallback)"),
        ("  catalog.py", _loc(AS + "catalog.py"), "the 29 vetted SQL queries, parameters, role lists"),
        ("  llm.py", _loc(AS + "llm.py"), "Gemini: choose queries, word the answer, key fail-over"),
        ("  grounding.py", _loc(AS + "grounding.py"), "trims rows to the prompt; checks numbers"),
        ("  compose.py", _loc(AS + "compose.py"), "template answers when Gemini is off or rejected"),
        ("backend/app/api/routes/assistant.py", _loc(BE + "api/routes/assistant.py"), "HTTP: ask, chats, rename, delete, info"),
        ("backend/app/models/chat_session.py", _loc(BE + "models/chat_session.py"), "a conversation"),
        ("backend/app/models/chat_message.py", _loc(BE + "models/chat_message.py"), "a message + its SQL, sources, latency, tokens"),
        ("backend/alembic/versions/0006_chat.py", _loc("backend/alembic/versions/0006_chat.py"), "creates the chat tables"),
        ("backend/tests/test_assistant.py", _loc("backend/tests/test_assistant.py"), "tests: scope, read-only, refusals, rate limit"),
        ("frontend/src/pages/Assistant.tsx", _loc(FE + "pages/Assistant.tsx"), "the Nira screen"),
        ("frontend/src/services/assistant.ts", _loc(FE + "services/assistant.ts"), "the API calls"),
    ]
    width = max(len(a) for a, _, _ in rows) + 2
    return "\n".join(f"{name.ljust(width)}{str(n).rjust(5)}  {what}" for name, n, what in rows)


def _query_rows() -> list[list[str]]:
    rows = []
    for name, by_role in M["queries"].items():
        for role, v in by_role.items():
            rows.append([f"`{name}`", {"user": "Citizen", "phc_worker": "Worker", "admin": "Admin"}[role], f"{v['median_ms']}", f"{v['max_ms']}", str(v["rows"])])
    return rows


def build() -> list[str]:
    out = []
    g = M["gemini_samples"]
    plan = [s["plan_ms"] for s in g]
    write = [s["write_ms"] for s in g]
    retr = [s["retrieve_ms"] for s in g]
    totals = [a + b + c for a, b, c in zip(plan, retr, write, strict=True)]
    qm = [v["median_ms"] for by in M["queries"].values() for v in by.values()]
    rules = M["rules_summary"]

    out.append(chapter("6", "Folder structure: what each file does", "c6", "Everything about Nira lives in one package of six files. The rest is the route, two tables, the screen and the tests.", (
        h2("6.1 The files (line counts are real)")
        + pre(_tree())
        + h2("6.2 What each file does")
        + table(["File", "Lines", "Responsibility", "Key items"], [
            ["`__init__.py`", str(_loc(AS + "__init__.py")), "Runs the pipeline for one question", ref(AS + "__init__.py", "async def _answer") + " · " + ref(AS + "__init__.py", "async def retrieve") + " · " + ref(AS + "__init__.py", "async def ask")],
            ["`router.py`", str(_loc(AS + "router.py")), "Refuses or redirects before any model call; plans without a model", ref(AS + "router.py", "EMERGENCY = re.compile") + " · " + ref(AS + "router.py", "def plan")],
            ["`catalog.py`", str(_loc(AS + "catalog.py")), "The menu: query text, parameters, who may use it, keyword patterns", ref(AS + "catalog.py", "TOOLS: tuple") + " · " + ref(AS + "catalog.py", "class Param")],
            ["`llm.py`", str(_loc(AS + "llm.py")), "All Gemini calls: plan with function calling, word the answer, try each key", ref(AS + "llm.py", "async def choose_tools") + " · " + ref(AS + "llm.py", "async def write_answer")],
            ["`grounding.py`", str(_loc(AS + "grounding.py")), "Keeps the prompt to whole rows; finds numbers the data does not support", ref(AS + "grounding.py", "def trim") + " · " + ref(AS + "grounding.py", "def unsupported")],
            ["`compose.py`", str(_loc(AS + "compose.py")), "One template per query so there is always an answer", ref(AS + "compose.py", "def compose") + " · " + ref(AS + "compose.py", "_COMPOSERS = {")],
            ["`routes/assistant.py`", str(_loc(BE + "api/routes/assistant.py")), "HTTP layer: rate limit, chat ownership, rename, delete", ref(BE + "api/routes/assistant.py", "async def ask")],
            ["`models/chat_message.py`", str(_loc(BE + "models/chat_message.py")), "Stores `generated_sql`, `retrieval` (JSON), `latency_ms`, `tokens_used`, refusal reason", ref(BE + "models/chat_message.py", "class ChatMessage(")],
            ["`Assistant.tsx`", str(_loc(FE + "pages/Assistant.tsx")), "Chat list, greeting and starter cards, composer, answer bubbles, 'Based on' line", ref(FE + "pages/Assistant.tsx", "export function Assistant")],
        ])
        + h2("6.3 Configuration")
        + table(["Setting", "Default", "Meaning"], [
            ["`GEMINI_API_KEY`, `GEMINI_API_KEYS`", "empty", "One key or a comma-separated list; a key that fails hands over to the next. With none, the assistant runs on rules only"],
            ["`GEMINI_MODEL`", "gemini-2.5-flash", "The model used for planning and wording"],
            ["`ASSISTANT_QUESTIONS_PER_MINUTE`", "20", "Per-user rate limit"],
        ])
        + files([(BE + "core/config.py", "GEMINI_MODEL", "Where the three settings are read.")])
    )))

    out.append(chapter("7", "Tech stack and response time", "c7", "What Nira is built with, and how long each step takes, measured on this machine.", (
        table(["Layer", "Technology", "Used for"], [
            ["Language model", "Google Gemini 2.5 Flash through the `google-genai` SDK", "Choosing queries (function calling) and wording answers"],
            ["API", "FastAPI (async), Pydantic v2", "`/assistant/*` endpoints and validation"],
            ["Retrieval", "Raw parameterised SQL through SQLAlchemy (`text`) and asyncpg", "The 29 vetted queries"],
            ["Database", "PostgreSQL: read-only transaction, `statement_timeout`", "The data and the stored conversations (`JSONB` for sources)"],
            ["Verification", "Plain Python (`grounding.py`)", "Number check"],
            ["Fallback", "Regular expressions and templates", "Planning and answers when Gemini is unavailable"],
            ["Front end", "React 18, TypeScript, Tailwind v4", "The Nira screen"],
            ["Tests", "pytest with an async client", "Scope, read-only retrieval, refusals, rate limit"],
        ])
        + h2("7.1 Response time (measured)")
        + kpis([(f"{rules['median_ms']:g} ms", "answer without Gemini, median"), (f"{st.median(qm):g} ms", "a database query, median"), (f"{st.median(plan) / 1000:.1f} s", "Gemini picks the query, median"),
                (f"{st.median(write) / 1000:.1f} s", "Gemini words the answer, median"), (f"{st.median(totals) / 1000:.1f} s", "whole answer with Gemini, median")])
        + table(["Step", "Typical time", "What dominates"], [
            ["Safety rules", "under 1 ms", "Regular expressions"],
            ["Plan (Gemini function calling)", f"{min(plan) / 1000:.1f} to {max(plan) / 1000:.1f} s", "A network round trip to Gemini"],
            ["Retrieve (SQL)", f"{min(retr)} to {max(retr)} ms", "PostgreSQL (the first query after a cold start is the slowest)"],
            ["Generate (Gemini wording)", f"{min(write) / 1000:.1f} to {max(write) / 1000:.1f} s", "A second round trip to Gemini, proportional to the answer length"],
            ["Number check", "under 1 ms", "String and set operations"],
            ["Store", "a few ms", "One insert"],
            ["**Total with Gemini**", f"**{min(totals) / 1000:.1f} to {max(totals) / 1000:.1f} s**", "Almost all of it is the two Gemini calls"],
            ["**Total on the rule-based path**", f"**{rules['median_ms']} ms median, {rules['max_ms']} ms worst**", f"{rules['answered']} of {rules['questions']} sample questions matched a query"],
        ])
        + bullets([
            "**Gemini is about 97% of the time.** The database answers in milliseconds; the safety rules and the number check are negligible.",
            "Two Gemini calls per question: one to plan, one to word. That is what makes a question take about 5 to 6 s.",
            "Stored answers from earlier sessions showed 4.7 to 6.2 s end to end with about 1,600 tokens used per answer.",
            "**Free-tier limit:** Gemini's free tier allows 5 requests a minute, so about 2 questions a minute per key. Hitting it returns a 429, which falls over to the next key and then to the rule-based answer. During measurement this happened, which is why the Gemini timings above come from 3 complete runs and the rule-based path from 15.",
            M.get("gemini_note", ""),
        ])
        + h2("7.2 Time per query (rule-based path, 7 runs each)")
        + table(["Query", "Role", "Median (ms)", "Worst (ms)", "Rows"], _query_rows())
        + qa([
            ("Why does a question take 5 to 6 seconds?", "Two sequential calls to Gemini (choose the query, then word the answer), each 2 to 3 seconds. The database part is a few milliseconds."),
            ("How could it be faster?", "Cache the plan for repeated questions, skip the planning call for exact suggested questions, stream the answer to the screen, or use the template answer for simple lists. Streaming changes what the user feels, not the total."),
            ("What happens at the free-tier limit?", "A quota error on one key moves to the next key; with all exhausted the keyword planner and template answer respond in a few milliseconds, so the user still gets an answer."),
        ])
    )))

    out.append(chapter("8", "Defence Q&A and known limits", "c8", "Short answers to the likely questions, including the weaknesses worth admitting first.", (
        qa([
            ("What would you show first to prove it is RAG?", "A single answer's 'Based on' line expanded: the query that ran, its parameters and the rows. Then `catalog.py` (the menu) and `grounding.py` (the check)."),
            ("Why 29 queries, not hundreds?", "Each one is reviewed once for scope and privacy, and each mirrors something a screen already shows. A new question is one new query; the pipeline, safety and verification do not change."),
            ("Can the model be tricked into running something dangerous?", "No query writes data and the transaction is read-only. The model cannot add a query: it can only choose a name from the menu and fill declared parameters, which are cleaned."),
            ("Can a citizen get a worker's list by asking nicely?", "No. `flagged_citizens` is not in a citizen's menu. The role list is applied before Gemini sees the functions and again when its choice is accepted."),
            ("What does the assistant do with an emergency?", "'Chest pain', 'can't breathe', 'stroke' and similar words return 'call 108 now' straight away, before any query or model call."),
            ("What if Gemini returns a wrong number?", "The number check compares every number with the rows. A mismatch discards the answer and shows the template answer; the badge on the answer says 'Plain summary used'."),
            ("What are the limits?", "Only questions a query covers are answered. The keyword fallback can match a loose word and answer a nearby but different question (safely, within the user's own scope). The number check proves numbers, not every claim in a sentence. Answers take 5 to 6 s with Gemini. Free-tier quota is small."),
            ("Does it learn from users' questions?", "No. Nothing is trained. Questions and answers are stored per user for their own history, and an admin sees only usage totals (`assistant_usage`), never the text."),
            ("How would you add guideline search?", "Add one query-like tool whose retriever is a `pgvector` search; planning, scope, verification and storage are unchanged."),
            ("How is it tested?", "`backend/tests/test_assistant.py` checks every query runs, retrieval is read-only, a citizen never sees another's data, a worker sees only their catchment, an admin gets aggregates not readings, medical advice is declined and emergencies get 108, follow-ups, private sessions, scope that the model cannot widen, and the rate limit."),
        ])
    )))
    return out
