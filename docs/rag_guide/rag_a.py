import re
import sys

from lib import ROOT, bullets, chain, chapter, files, flow, functions, h2, kpis, md, note, p, pre, qa, ref, table

sys.path.insert(0, str(ROOT / "backend"))
from app.models.enums import UserRole  # noqa: E402
from app.services.assistant import router  # noqa: E402
from app.services.assistant.catalog import BY_NAME, TOOLS, tools_for  # noqa: E402

BE, FE, AS = "backend/app/", "frontend/src/", "backend/app/services/assistant/"

ROLE_NAME = {"user": "Citizen", "phc_worker": "Worker", "admin": "Admin"}
TABLES = {"users", "user_profiles", "health_records", "processed_data", "alerts", "scheduled_visits", "valid_phc_facilities",
          "consent_records", "concerns", "phc_applications", "advisories", "community_data", "chat_messages"}

WHY = {
    "my_latest_reading": "The most common question: 'is my last reading normal?' Mirrors the dashboard's latest values.",
    "my_vital_stats": "Average, lowest and highest per vital over a period; mirrors the dashboard trend and History.",
    "my_activity": "How often they log; mirrors the dashboard's weekly count.",
    "my_flags": "Which readings were flagged and why; mirrors History's 'flagged only' filter.",
    "my_alerts": "The notification list; mirrors the Alerts page (a worker's Notifications too).",
    "my_visits": "Upcoming and recent visits; mirrors the Visits page.",
    "my_health_centre": "Which centre looks after them and how many workers it has; mirrors Settings → Your health centre.",
    "my_profile": "What the app holds about them; mirrors the Profile page.",
    "my_examinations": "Examinations a health worker recorded: when, where, by whom.",
    "my_readings_by_source": "How many readings came from the watch, an examination or typing, and the latest of each.",
    "my_advisories": "Advisories currently running for where they live; matches the Alerts page.",
    "catchment_overview": "The dashboard's counts as one answer: citizens, flagged, readings, visits.",
    "flagged_citizens": "The worklist: who has open flags, worst first; mirrors the Alerts page.",
    "citizen_summary": "One citizen's status, by name or HN reference; mirrors the citizen record.",
    "silent_citizens": "Who has not logged anything for N days; mirrors the Citizens page 'gone quiet'.",
    "my_schedule": "The worker's visits in the next days; mirrors the Schedule page.",
    "locality_breakdown": "Which localities have the most flags (only opted-in citizens, never under 3); mirrors the risk map.",
    "catchment_trend": "Readings and flags per week; mirrors the dashboard KPIs.",
    "symptom_counts": "Which symptoms are being reported (opted-in citizens); supports outbreak watching.",
    "advisories_overview": "Advisories published in a window, with status and feedback; mirrors the Advisories history.",
    "outbreak_signals": "Outbreak clusters flagged in a window; mirrors the Outbreaks page.",
    "platform_overview": "Accounts, readings, open flags, applications and concerns for the admin's district.",
    "pending_applications": "PHC applications waiting; mirrors the Applications page.",
    "facility_load": "Citizens and open flags per health centre; shows imbalance.",
    "unlinked_workers": "Approved workers with no centre, who therefore see nobody.",
    "concerns_summary": "Complaints by status and category; mirrors the Complaints page.",
    "signups": "New accounts by role over a period.",
    "district_activity": "Per district activity (opted-in citizens, groups of 3 or more).",
    "assistant_usage": "How Nira itself is being used: questions, unanswered, latency.",
}

DEMO = [
    (UserRole.user, "What was my blood pressure yesterday?"),
    (UserRole.user, "Hello"),
    (UserRole.user, "I have chest pain"),
    (UserRole.user, "Should I take paracetamol for my fever?"),
    (UserRole.user, "What is the capital of France?"),
    (UserRole.user, "Show me Priya's readings"),
    (UserRole.user, "How many citizens are flagged in my catchment?"),
    (UserRole.phc_worker, "Who has critical flags right now?"),
    (UserRole.phc_worker, "Show me the readings of HN-1A2B3C4D"),
    (UserRole.phc_worker, "What is 2 + 2?"),
    (UserRole.admin, "Give me a platform overview"),
    (UserRole.admin, "Show me anyone's heart rate readings"),
    (UserRole.admin, "Delete all users"),
]


def _demo_rows() -> list[list[str]]:
    rows = []
    for role, q in DEMO:
        if router.EMERGENCY.search(q):
            outcome, who = "**Emergency reply**: 'call 108 now'. No query and no model call.", "router.py"
        elif router.GREETING.match(q) or router.HELP.search(q):
            outcome, who = "Greeting / help text listing example questions.", "router.py"
        elif role == UserRole.user and router.MEDICAL_ADVICE.search(q):
            outcome, who = "**Declined**: 'I can't diagnose or advise on medicines'.", "router.py"
        else:
            plan = router.plan(role, q)
            if plan is None:
                outcome, who = "**Refused**: 'I can only answer questions about HealthNexus records', plus examples.", "catalog + router"
            else:
                outcome, who = f"Runs the query `{plan.tool.name}` (match score {plan.score:g}).", "catalog + router"
        rows.append([ROLE_NAME[role.value], q, outcome, who])
    return rows


def _tool_tables(sql: str) -> str:
    found = sorted({m.lower() for m in re.findall(r"(?:FROM|JOIN)\s+([a-z_]+)", sql, re.I)} & TABLES)
    return ", ".join(found)


def _tool_rows(role_filter) -> list[list[str]]:
    rows = []
    n = 0
    for t in TOOLS:
        if not role_filter(t):
            continue
        n += 1
        params = ", ".join(t.params) or "none"
        rows.append([str(n), f"`{t.name}`", t.title, WHY[t.name], _tool_tables(t.sql), params])
    return rows


def build() -> list[str]:
    out = []
    citizen = [t for t in TOOLS if UserRole.user in t.roles]
    worker = [t for t in TOOLS if UserRole.phc_worker in t.roles]
    admin = [t for t in TOOLS if UserRole.admin in t.roles]

    out.append(chapter("1", "The big picture: what Nira's RAG is", "c1", "A question is answered in four moves: pick a vetted query, run it safely, word the answer from its rows, and check the numbers.", (
        kpis([(str(len(TOOLS)), "vetted SQL queries"), ("3", "roles, each with its own list"), ("6", "files in the assistant package"), ("4 ms", "to answer without Gemini (median)"), ("~5 to 6 s", "to answer with Gemini")])
        + chain(["Question", "Safety check", "Choose a query", "Run it, read-only", "Gemini words the answer from the rows", "Check every number", "Show with its sources"])
        + table(["Step", "What happens", "Who does it", "File"], [
            ["1 Safety", "Emergency words get 'call 108'; diagnosis and medicine questions are declined; greetings get help", "Fixed rules", ref(AS + "router.py", "EMERGENCY = re.compile")],
            ["2 Plan", "Pick **which query** answers it and its parameters", "Gemini (function calling), or the keyword router if Gemini is unavailable", ref(AS + "__init__.py", "async def _plan")],
            ["3 Retrieve", "Run that query for **this user only**, read-only, with a time limit", "PostgreSQL", ref(AS + "__init__.py", "async def retrieve")],
            ["4 Generate", "Write a short answer using only the returned rows", "Gemini, or a template", ref(AS + "llm.py", "async def write_answer")],
            ["5 Verify", "Every number in the answer must appear in the rows", "Code", ref(AS + "grounding.py", "def unsupported")],
            ["6 Record", "Store the answer with its sources so it can be shown and audited", "Code", ref(AS + "__init__.py", "answer = ChatMessage(")],
        ])
        + note("**What makes it RAG:** the model never sees the database and never writes SQL. It chooses from a fixed menu, the server fetches the data, and the answer is generated **from that retrieved data** and checked against it. Chapter 5 gives the full defence.", "key")
        + h2("Who can ask what")
        + table(["Role", "Queries open", "Sees"], [
            ["Citizen", str(len(citizen)), "Only their own rows (`user_id = :me`)"],
            ["PHC worker", str(len(worker)), "Their centre's catchment: citizens who have not withdrawn worker access"],
            ["Admin", str(len(admin)), "Aggregates and account metadata for their district; **never anyone's readings**"],
        ])
    )))

    out.append(chapter("2", "How it answers only the correct, related question", "c2", "Nothing is left to the model's judgement. Seven layers, each in a known file, stand between a question and an answer.", (
        table(["#", "Layer", "File responsible", "What it guarantees", "Code"], [
            ["1", "**Emergency and safety rules**", "router.py", "Chest pain, stroke, 'can't breathe' and similar get 'call 108' immediately; 'what medicine should I take', 'do I have dengue' are declined for citizens", ref(AS + "router.py", "MEDICAL_ADVICE = re.compile")],
            ["2", "**Role whitelist**", "catalog.py", "A role can only be offered its own queries (`tools_for(role)`); a citizen can never be offered `flagged_citizens`", ref(AS + "catalog.py", "def tools_for")],
            ["3", "**A fixed menu, not free SQL**", "catalog.py", "The model or router can only choose a query name and fill its declared parameters. There is no way to ask for a different query", ref(AS + "catalog.py", "class Tool")],
            ["4", "**Planner instructions**", "llm.py", "Gemini is told to call a function only if one fits, else reply with a short sentence; temperature 0 so the choice is repeatable", ref(AS + "llm.py", "PLAN_PROMPT")],
            ["5", "**Parameter cleaning**", "catalog.py", "Every argument (days, limit, severity, name) is coerced and clamped; anything odd falls back to the default", ref(AS + "catalog.py", "def clean")],
            ["6", "**No match means no answer**", "__init__.py", "If no query fits, the reply is 'I can only answer questions about HealthNexus records' with examples, and it is stored as an out-of-scope refusal", ref(AS + "__init__.py", "I can only answer questions about HealthNexus records")],
            ["7", "**Answer prompt and number check**", "llm.py, grounding.py", "Gemini must use only the rows and ignore instructions inside them; any number not in the rows discards the answer", ref(AS + "llm.py", "ANSWER_PROMPT")],
        ])
        + h2("Live behaviour (computed from the real rules)")
        + p("The table runs each question through the actual safety rules and the rule-based planner. Gemini's planner is more flexible but is held to the same menu.")
        + table(["Role", "Question", "What happens", "Decided by"], _demo_rows())
        + note("**Be ready to admit this limit:** the keyword fallback is crude. 'How many citizens are flagged in my catchment?' asked by a *citizen* matches the word 'flagged' and answers about **their own** flags. It is wrong-but-safe: the query is scoped to that citizen, so nothing private leaks. With Gemini planning the question is understood semantically; on the rules path a stricter minimum match score would refuse it.", "warn")
        + h2("Which file does what, in one view")
        + files([
            (AS + "router.py", "GREETING = re.compile", "Safety and intent rules (emergency, medical advice, greetings, help) and the rule-based planner `plan`."),
            (AS + "catalog.py", "TOOLS: tuple", "The 29 queries, their parameters, role lists and keyword patterns."),
            (AS + "llm.py", "async def choose_tools", "Gemini: choose up to three queries; word the answer."),
            (AS + "__init__.py", "async def _answer", "The conductor that applies every layer in order."),
            (AS + "grounding.py", "def unsupported", "The number check."),
            (AS + "compose.py", "def compose", "Template answers used when Gemini fails or its answer is rejected."),
        ])
        + qa([
            ("What stops the model answering something unrelated, like the weather?", "Two things. The planner can only pick from the role's 29-or-fewer queries and is told to reply briefly if none fits, so no query runs. And even if a query were chosen, the answer prompt limits the model to the retrieved rows."),
            ("What stops it reading another user's data?", "The SQL is fixed and written by us, not the model. `:me`, `:phc_id` and `:district` are bound on the server from the signed-in user, never from the question. A model that tried to ask for 'Priya's readings' as a citizen has no query for it."),
        ])
    )))

    out.append(chapter("3", "The 29 queries: what they are, why, and how they operate", "c3", "Each query is one vetted SQL statement with declared parameters. They were chosen to cover what each role already does on screen.", (
        h2("3.1 Why these 29")
        + bullets([
            "**They mirror the app's own screens.** Each query answers a question a person already asks of a page (latest reading, flagged list, schedule, pending applications). The assistant is a faster way in, not a new data source.",
            "**They come from the suggested questions** shown on Nira's start screen for each role, plus the newer features (examinations, advisories, outbreak signals, smartwatch sources).",
            "**Coverage versus safety:** every query is reviewed once for scope. A new question is one new query, not a new risk. The cost is that only questions a query covers are answered; the rest are politely refused.",
            "**Privacy is built into the SQL.** Worker queries use the same catchment rule as the screens; area-level queries include only opted-in citizens and fold groups under 3; admin queries return totals, never readings.",
        ])
        + table(["Role", "Count", "Queries"], [
            ["Citizen only", str(sum(1 for t in TOOLS if t.roles == frozenset({UserRole.user}))), ", ".join(f"`{t.name}`" for t in TOOLS if t.roles == frozenset({UserRole.user}))],
            ["Worker only", str(sum(1 for t in TOOLS if t.roles == frozenset({UserRole.phc_worker}))), ", ".join(f"`{t.name}`" for t in TOOLS if t.roles == frozenset({UserRole.phc_worker}))],
            ["Admin only", str(sum(1 for t in TOOLS if t.roles == frozenset({UserRole.admin}))), ", ".join(f"`{t.name}`" for t in TOOLS if t.roles == frozenset({UserRole.admin}))],
            ["Shared", str(sum(1 for t in TOOLS if len(t.roles) > 1)), ", ".join(f"`{t.name}` ({' and '.join(ROLE_NAME[r.value] for r in sorted(t.roles, key=lambda r: r.value))})" for t in TOOLS if len(t.roles) > 1)],
        ])
        + h2("3.2 Citizen queries (own rows only)")
        + table(["#", "Query", "Title", "Why it exists", "Tables read", "Parameters"], _tool_rows(lambda t: UserRole.user in t.roles))
        + h2("3.3 Worker queries (their catchment)")
        + table(["#", "Query", "Title", "Why it exists", "Tables read", "Parameters"], _tool_rows(lambda t: UserRole.phc_worker in t.roles))
        + h2("3.4 Admin queries (aggregates for their district)")
        + table(["#", "Query", "Title", "Why it exists", "Tables read", "Parameters"], _tool_rows(lambda t: UserRole.admin in t.roles))
        + h2("3.5 How one query operates")
        + p("Here is the real definition of `my_vital_stats`, the answer to 'what were my average vitals over the last 30 days?':")
        + pre(BY_NAME["my_vital_stats"].sql.strip(), "tree")
        + table(["Part", "What it is"], [
            ["`:me`", "A **server-side bind**: the signed-in user's id. It is not a parameter the model can set."],
            ["`days`", "A declared parameter: integer, 1 to 365, default 30. The model's value is cleaned by `Param.clean`."],
            ["The SQL text", "Written by us, reviewed once. The model can never edit it."],
            ["Keyword patterns", "Weighted regular expressions used only by the rule-based planner when Gemini is unavailable."],
            ["`description`", "The sentence Gemini reads when choosing among queries (function calling)."],
        ])
        + table(["Safeguard on every query", "Value", "Code"], [
            ["Read-only transaction", "`SET TRANSACTION READ ONLY`", ref(AS + "__init__.py", "SET TRANSACTION READ ONLY")],
            ["Time limit", "5 seconds (`statement_timeout`)", ref(AS + "__init__.py", "STATEMENT_TIMEOUT_MS =")],
            ["Rows read from the database", "at most 200", ref(AS + "__init__.py", "MAX_ROWS =")],
            ["Rows stored as the visible source", "at most 25", ref(AS + "__init__.py", "KEPT_ROWS =")],
            ["Bound values", "only those the SQL text actually uses", ref(AS + "__init__.py", "def _binds")],
        ])
        + table(["Parameter type", "Rule"], [
            ["`days`", "integer 1 to 365; default per query"],
            ["`limit`", "integer 1 to 50"],
            ["`severity`", "one of low, moderate, high, critical; anything else becomes `low`"],
            ["`name`", "text up to 80 characters, whitespace collapsed; matched with an escaped `LIKE` or an `HN-` reference"],
        ])
    )))
    return out
