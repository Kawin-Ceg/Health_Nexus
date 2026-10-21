"""Rule-based planning: which catalog tool answers a question, and with what parameters.

Used when no LLM is configured, and as the fallback when the LLM call fails.
"""

import re
from dataclasses import dataclass
from typing import Any

from app.models.enums import UserRole

from .catalog import Tool, tools_for

_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10, "fourteen": 14, "thirty": 30}
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}

GREETING = re.compile(r"^\s*(hi|hello|hey|namaste|vanakkam|good (morning|afternoon|evening))\b[\s!.?]*$", re.I)
HELP = re.compile(r"\b(help|what can you (do|answer)|what (should|can) i ask|how do(es)? (this|you) work)\b", re.I)
# Questions a records assistant must not answer: it reads data, it does not practise medicine.
MEDICAL_ADVICE = re.compile(
    r"\b(diagnos\w*|prescri\w*|what (medicine|medication|tablet|drug)s? should|should i (take|stop|start|increase|reduce)|"
    r"dos(e|age)|treat(ment)? for|cure|is it (cancer|covid|dengue|malaria|tb)|do i have)\b",
    re.I,
)
EMERGENCY = re.compile(
    r"\b(chest pain|can'?t breathe|cannot breathe|difficulty breathing|unconscious|fainted|stroke|heart attack|"
    r"severe bleeding|suicid\w*|kill myself|seizure)\b",
    re.I,
)


@dataclass
class Plan:
    tool: Tool
    args: dict[str, Any]
    score: float


def extract_days(text: str) -> int | None:
    t = text.lower()
    if re.search(r"\btoday\b", t):
        return 1
    if re.search(r"\byesterday\b", t):
        return 2
    m = re.search(r"\b(\d{1,3}|" + "|".join(_NUM_WORDS) + r")\s*(day|week|month|year)s?\b", t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else _NUM_WORDS[m.group(1)]
        return n * _UNIT_DAYS[m.group(2)]
    m = re.search(r"\b(this|last|past|previous)\s+(day|week|fortnight|month|quarter|year)\b", t)
    if m:
        return {"day": 1, "week": 7, "fortnight": 14, "month": 30, "quarter": 90, "year": 365}[m.group(2)]
    return None


def extract_limit(text: str) -> int | None:
    m = re.search(r"\b(?:top|first|last)\s+(\d{1,2})\b", text.lower())
    return int(m.group(1)) if m else None


def extract_severity(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bcritical\b", t):
        return "critical"
    if re.search(r"\b(high|serious|severe|urgent|high[- ]risk)\b", t):
        return "high"
    if re.search(r"\bmoderate\b", t):
        return "moderate"
    return None


_STOP = {"the", "my", "a", "an", "is", "doing", "now", "today", "this", "week", "month", "citizen", "patient", "please"}


def extract_name(text: str) -> str | None:
    ref = re.search(r"\bHN-[0-9A-F]{8}\b", text, re.I)
    if ref:
        return ref.group(0).upper()
    m = re.search(
        r"\b(?:about|is|for|on|of|named|called|lookup|look up|check)\s+([A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*)?)",
        text,
    )
    if not m:
        return None
    words = [w for w in m.group(1).split() if w.lower() not in _STOP]
    # Prefer capitalised words: "how is Priya doing" -> "Priya".
    caps = [w for w in words if w[0].isupper()]
    chosen = caps or words
    return " ".join(chosen[:2]) if chosen else None


def plan(role: UserRole, question: str) -> Plan | None:
    """The best-scoring tool for this role, or None if nothing matches."""
    best: Plan | None = None
    for tool in tools_for(role):
        score = sum(weight for pattern, weight in tool.patterns if re.search(pattern, question, re.I))
        if score <= 0:
            continue
        if best is None or score > best.score:
            best = Plan(tool=tool, args={}, score=score)
    if best is None:
        return None
    best.args = fill_args(best.tool, question)
    if best.tool.name == "citizen_summary" and not best.args.get("name"):
        return None  # a lookup with nobody named is not a lookup
    return best


def fill_args(tool: Tool, question: str) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    if "days" in tool.params:
        raw["days"] = extract_days(question)
    if "limit" in tool.params:
        raw["limit"] = extract_limit(question)
    if "severity" in tool.params:
        raw["severity"] = extract_severity(question)
    if "name" in tool.params:
        raw["name"] = extract_name(question)
    return {key: param.clean(raw.get(key)) for key, param in tool.params.items()}


def follow_up(tool: Tool, previous_args: dict[str, Any], question: str) -> dict[str, Any] | None:
    """'And over the last 90 days?' reuses the previous tool with the new window.

    Only when the new question changes a parameter that tool takes.
    """
    fresh = {
        "days": extract_days(question) if "days" in tool.params else None,
        "limit": extract_limit(question) if "limit" in tool.params else None,
        "severity": extract_severity(question) if "severity" in tool.params else None,
    }
    changed = {k: v for k, v in fresh.items() if v is not None}
    if not changed:
        return None
    merged = {**previous_args, **changed}
    return {key: param.clean(merged.get(key)) for key, param in tool.params.items()}
