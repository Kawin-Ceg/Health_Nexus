"""The HealthNexus assistant: SQL-driven retrieval-augmented answers over the caller's own data.

One question goes through:

1. Safety: an emergency gets the emergency number at once; a request for a
   diagnosis or medicine advice is declined.
2. Plan: Gemini (if configured) or the rule-based router picks up to three tools
   from catalog.py (one per part of the question) and fills their parameters.
   A short follow-up ("and last month?") reuses the previous tool.
3. Retrieve: each tool's SQL runs in a READ ONLY transaction with a timeout,
   with the caller's scope (:me / :phc_id / :district) bound on the server.
4. Answer: Gemini words the answer from those rows only, or the template does.
5. Verify: every number in Gemini's answer must appear in the rows it was given
   (grounding.py); otherwise the template answer is used instead.
6. Record: the answer is stored with the SQL that ran, the rows it used and
   whether it passed the check, so every answer can show where it came from.
"""

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import ChatMessage, ChatSession, User
from app.models.base import utcnow
from app.models.enums import ChatMessageRole, ChatRefusalReason, UserRole
from app.services.catchment import NO_FACILITY
from app.services.visits import format_local

from . import grounding, llm, router
from .catalog import BY_NAME, Tool, tools_for
from .compose import compose

log = logging.getLogger(__name__)

MAX_ROWS = 200  # read from the database
KEPT_ROWS = 25  # stored with the message and shown as the source
STATEMENT_TIMEOUT_MS = 5000

SUGGESTIONS: dict[UserRole, list[str]] = {
    UserRole.user: [
        "Is my latest blood pressure normal?",
        "What were my average vitals over the last 30 days?",
        "Were any of my readings flagged this month?",
        "When is my next visit?",
        "How many readings have I logged this week?",
        "Which health centre looks after me?",
        "Any advisories for my area?",
        "My latest readings and my next visit",
    ],
    UserRole.phc_worker: [
        "Give me an overview of my catchment",
        "Who has critical flags right now?",
        "Who hasn't logged anything in 14 days?",
        "What symptoms are being reported this week?",
        "Which localities have the most flags?",
        "What visits do I have in the next 3 days?",
        "Any outbreak signals near my centre?",
    ],
    UserRole.admin: [
        "Give me a platform overview",
        "Which PHC applications are waiting?",
        "Which health centres have citizens but no worker?",
        "How many people signed up in the last 30 days?",
        "Summarise the open support concerns",
        "How is the assistant being used this week?",
        "Any outbreak signals in my district?",
    ],
}

# An empty result that is an answer in itself, not a failure to find anything.
EMPTY_ANSWERS: dict[str, str] = {
    "my_flags": "None of your readings in the last {days} days were flagged.",
    "my_alerts": "You have no notifications yet.",
    "my_visits": "No visits are booked for you, and none took place in the last 30 days.",
    "flagged_citizens": "No citizens in your catchment have open flags{severity_note}.",
    "silent_citizens": "Everyone in your catchment has logged a reading in the last {days} days.",
    "my_schedule": "You have no visits booked in the next {days} days.",
    "pending_applications": "No PHC worker applications are waiting.",
    "unlinked_workers": "Every approved PHC worker is linked to a health centre.",
    "concerns_summary": "Nobody has raised a support concern yet.",
    "symptom_counts": "No symptoms were reported with readings in the last {days} days.",
    "my_examinations": "No health worker has recorded an examination for you in the last {days} days.",
    "my_readings_by_source": "You have no readings in the last {days} days.",
    "my_advisories": "There are no advisories running for your area right now.",
    "advisories_overview": "No advisories were published in the last {days} days.",
    "outbreak_signals": "No outbreak signals were flagged in the last {days} days.",
}
INSUFFICIENT = {"my_latest_reading", "my_vital_stats"}


@dataclass
class Outcome:
    content: str
    tool: Tool | None = None
    args: dict[str, Any] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    engine: str = "rules"
    refusal: ChatRefusalReason | None = None
    sources: list["Source"] = field(default_factory=list)
    grounded: bool | None = None


Source = tuple[Tool, dict[str, Any], list[dict[str, Any]]]


def suggestions_for(role: UserRole) -> list[str]:
    return SUGGESTIONS.get(role, [])


def _plain(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return value


def _binds(tool: Tool, args: dict[str, Any], user: User) -> dict[str, Any]:
    values = dict(args)
    if tool.derive:
        values.update(tool.derive(args))
    # Scope comes from the signed-in user, never from the question or the model.
    values["me"] = user.id
    values["phc_id"] = user.phc_id
    values["district"] = user.district if user.role == UserRole.admin else None
    return {k: v for k, v in values.items() if re.search(rf"(?<!:):{k}\b", tool.sql)}


async def retrieve(tool: Tool, args: dict[str, Any], user: User, engine: AsyncEngine) -> list[dict[str, Any]]:
    """Run one catalog query, read-only, on its own connection from engine."""
    async with engine.connect() as conn:
        async with conn.begin():
            await conn.execute(text("SET TRANSACTION READ ONLY"))
            await conn.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
            result = await conn.execute(text(tool.sql), _binds(tool, args, user))
            rows = [dict(r._mapping) for r in result.fetchmany(MAX_ROWS)]
    return tool.post(rows, args) if tool.post else rows


def _help(role: UserRole) -> str:
    examples = "\n".join(f"- {q}" for q in SUGGESTIONS.get(role, []))
    scope = {
        UserRole.user: "your own readings, flags, notifications, visits and health centre",
        UserRole.phc_worker: "the citizens in your catchment, their flags and readings, your visits, and locality trends",
        UserRole.admin: "accounts, worker applications, health centres, concerns and platform activity (totals only, never anyone's readings)",
    }.get(role, "your data")
    return f"I'm Nira. I answer questions from HealthNexus records: {scope}. Try asking:\n{examples}"


def _empty(tool: Tool, args: dict[str, Any]) -> Outcome:
    if tool.name in EMPTY_ANSWERS:
        severity = args.get("severity", "low")
        note = "" if severity in (None, "low") else " at critical" if severity == "critical" else f" at {severity} or above"
        return Outcome(EMPTY_ANSWERS[tool.name].format(days=args.get("days"), severity_note=note), tool, args)
    if tool.name in INSUFFICIENT:
        window = f" in the last {args['days']} days" if "days" in args else ""
        return Outcome(
            f"You have no readings{window} yet, so there is nothing to compare. Log your vitals and ask again.",
            tool, args, refusal=ChatRefusalReason.insufficient_history,
        )
    if tool.name == "citizen_summary":
        return Outcome(
            f"Nobody in your catchment matches \"{args.get('name')}\". Try part of the name or their HN- reference.",
            tool, args, refusal=ChatRefusalReason.no_matching_records,
        )
    return Outcome("I found no matching records for that.", tool, args, refusal=ChatRefusalReason.no_matching_records)


# The tool and arguments behind the last answer in this conversation, for follow-ups.
Previous = tuple[Tool, dict[str, Any]] | None


async def _plan(
    user: User, question: str, history: list[tuple[str, str]], previous: Previous, usage: llm.Usage
) -> tuple[list[tuple[Tool, dict[str, Any]]], str] | None:
    allowed = {t.name: t for t in tools_for(user.role)}
    if llm.enabled():
        try:
            picked = []
            for name, raw in await llm.choose_tools(user.role.value, question, list(allowed.values()), history, usage):
                tool = allowed.get(name)
                if tool is None or any(p[0] is tool for p in picked):
                    continue
                # The model's arguments get exactly the same cleaning as the router's.
                args = {k: p.clean(raw.get(k)) for k, p in tool.params.items()}
                if tool.name != "citizen_summary" or args.get("name"):
                    picked.append((tool, args))
            if picked:
                return picked, "gemini"
        except Exception:  # any SDK, network or quota failure: answer with the rules instead
            log.exception("Gemini planning failed; using the rule-based router")
    plan = router.plan(user.role, question)
    if plan:
        return [(plan.tool, plan.args)], "rules"
    if previous and previous[0].name in allowed:
        args = router.follow_up(previous[0], previous[1], question)
        if args is not None:
            return [(previous[0], args)], "rules"
    return None


def _template(sources: list[Source]) -> str:
    parts = [compose(tool.name, rows, args) if rows else _empty(tool, args).content for tool, args, rows in sources]
    return "\n\n".join(parts)


async def _answer(
    user: User, question: str, history: list[tuple[str, str]], previous: Previous, usage: llm.Usage, engine: AsyncEngine
) -> Outcome:
    if router.EMERGENCY.search(question):
        return Outcome(
            "This sounds like it could be an emergency. Call 108 for an ambulance now, or go to the nearest hospital. "
            "Do not wait for an answer here."
        )
    if router.GREETING.match(question) or router.HELP.search(question):
        return Outcome(_help(user.role))
    if user.role == UserRole.user and router.MEDICAL_ADVICE.search(question):
        return Outcome(
            "I can't diagnose or advise on medicines; I can only show what is in your records. "
            "Please speak to your health centre or a doctor about this. I can tell you your latest readings, "
            "averages, or any flagged readings if that helps.",
            refusal=ChatRefusalReason.out_of_scope,
        )

    planned = await _plan(user, question, history, previous, usage)
    if planned is None:
        return Outcome(
            "I can only answer questions about HealthNexus records, and I couldn't match that to one. " + _help(user.role),
            refusal=ChatRefusalReason.out_of_scope,
        )
    plan, engine_used = planned
    plan = [(tool, args) for tool, args in plan if not (tool.needs_facility and user.phc_id is None)]
    if not plan:
        first = planned[0][0]
        return Outcome(NO_FACILITY, first[0], first[1], refusal=ChatRefusalReason.error)

    sources: list[Source] = []
    for tool, args in plan:
        try:
            sources.append((tool, args, await retrieve(tool, args, user, engine)))
        except Exception:
            log.exception("Assistant retrieval failed for %s", tool.name)
            return Outcome("I couldn't read your records just now. Please try again in a moment.", tool, args,
                           refusal=ChatRefusalReason.error)
    tool, args, rows = sources[0]

    if len(sources) == 1:
        if not rows:
            outcome = _empty(tool, args)
            outcome.engine, outcome.sources = engine_used, sources
            return outcome
        if tool.name == "my_activity" and not rows[0]["readings_all_time"]:
            return Outcome(compose(tool.name, rows, args), tool, args, rows, engine_used,
                           refusal=ChatRefusalReason.insufficient_history, sources=sources)
    elif not any(r for _, _, r in sources):
        return Outcome(_template(sources), tool, args, rows, engine_used,
                       refusal=ChatRefusalReason.no_matching_records, sources=sources)

    content, grounded = None, None
    if llm.enabled():
        try:
            written, seen = await llm.write_answer(
                user.role.value, question, sources, history, format_local(utcnow()), usage
            )
            counts = " ".join(str(len(r)) for _, _, r in sources)
            missing = grounding.unsupported(written, [seen, question, counts, format_local(utcnow())])
            if missing:
                log.warning("Answer not grounded (%s): %s", ", ".join(missing[:5]), question)
                grounded, engine_used = False, "gemini, replaced by template"
            else:
                content, grounded, engine_used = written, True, "gemini"
        except Exception:
            log.exception("Gemini answer failed; using the template")
    if content is None:
        content = _template(sources)
        if engine_used == "gemini":
            engine_used = "gemini+template"
    return Outcome(content, tool, args, rows, engine_used, sources=sources, grounded=grounded)


async def ask(db: AsyncSession, user: User, session: ChatSession, question: str) -> tuple[ChatMessage, ChatMessage]:
    """Store the question, answer it, store the answer. Commits."""
    started = time.monotonic()
    earlier = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(6)
        )
    ).all()
    history = [(m.role.value, m.content) for m in reversed(earlier)]
    previous: Previous = None
    for m in earlier:
        if m.role == ChatMessageRole.assistant and m.retrieval and m.retrieval.get("tool") in BY_NAME:
            previous = (BY_NAME[m.retrieval["tool"]], m.retrieval.get("args") or {})
            break

    asked = ChatMessage(session_id=session.id, user_id=user.id, role=ChatMessageRole.user, content=question)
    db.add(asked)
    await db.flush()

    usage = llm.Usage()
    outcome = await _answer(user, question, history, previous, usage, db.bind)

    retrieval = None
    if outcome.tool is not None:
        kept = _plain(outcome.rows[:KEPT_ROWS])
        retrieval = {
            "tool": outcome.tool.name,
            "title": outcome.tool.title,
            "args": _plain(outcome.args),
            "engine": outcome.engine,
            "row_count": len(outcome.rows),
            "columns": list(kept[0].keys()) if kept else [],
            "rows": kept,
            "grounded": outcome.grounded,
            "sources": [
                {"tool": t.name, "title": t.title, "args": _plain(a), "row_count": len(r)}
                for t, a, r in (outcome.sources or [(outcome.tool, outcome.args, outcome.rows)])
            ],
        }
    answer = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        role=ChatMessageRole.assistant,
        content=outcome.content,
        generated_sql="\n;\n".join(t.sql.strip() for t, _, _ in outcome.sources) if outcome.sources
        else (outcome.tool.sql.strip() if outcome.tool else None),
        retrieval=retrieval,
        was_refused=outcome.refusal is not None,
        refusal_reason=outcome.refusal,
        latency_ms=int((time.monotonic() - started) * 1000),
        tokens_used=usage.tokens or None,
    )
    db.add(answer)
    if session.auto_titled and session.title == "New chat":
        session.title = question[:60].rstrip() + ("…" if len(question) > 60 else "")
    session.updated_at = utcnow()
    await db.commit()
    return asked, answer
