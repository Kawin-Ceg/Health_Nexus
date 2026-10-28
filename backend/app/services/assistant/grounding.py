"""Keeping generated answers tied to the retrieved rows.

trim():   fit rows into the prompt by dropping whole rows, never cutting one in half.
localize(): datetimes as India-time text, so the model quotes times as the user sees them.
unsupported(): numbers in an answer that appear nowhere in the rows, the question or
the parameters. Any hit means the model made something up, and the template answers instead.
"""

import json
import re
from datetime import date, datetime
from typing import Any

from app.services.visit_state import format_local

PROMPT_BUDGET = 12000

_NUMBER = re.compile(r"(?<![\w.\-])\d+(?:[.,]\d+)?(?![\w])")
_TIME = re.compile(r"\b\d{1,2}:\d{2}\b")


def localize(value: Any) -> Any:
    if isinstance(value, datetime):
        return format_local(value) + f" {value.year}"
    if isinstance(value, date):
        return f"{value.day} {value:%b %Y}"
    if isinstance(value, dict):
        return {k: localize(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [localize(v) for v in value]
    return value


def trim(rows: list[dict[str, Any]], budget: int) -> tuple[list[dict[str, Any]], bool]:
    """As many whole rows as fit in budget characters of JSON."""
    kept, used = [], 2
    for row in rows:
        size = len(json.dumps(row, default=str)) + 1
        if used + size > budget:
            return kept, True
        kept.append(row)
        used += size
    return kept, False


def _values(text: str) -> list[float]:
    found = []
    for match in _NUMBER.findall(text):
        try:
            found.append(float(match.replace(",", "")))
        except ValueError:
            pass
    return found


def unsupported(answer: str, evidence: list[str]) -> list[str]:
    """Numbers in the answer that no evidence text supports (allowing for rounding and 12-hour clocks)."""
    allowed: set[float] = {108.0}
    for text in evidence:
        for v in _values(text):
            allowed.update({v, round(v), round(v, 1), round(v, 2)})
            if v < 12:
                allowed.add(v + 12)
            if 12 < v < 24:
                allowed.add(v - 12)
    missing = []
    for token in _NUMBER.findall(_TIME.sub(lambda m: m.group(0).replace(":", " "), answer)):
        v = float(token.replace(",", ""))
        if v in allowed or any(abs(v - a) <= 0.05 * max(1.0, abs(a)) and abs(v - a) < 1 for a in allowed):
            continue
        missing.append(token)
    return missing
