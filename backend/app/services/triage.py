"""How a flag is ranked, described and referred to. Every page uses these three.

- `severity_of` turns an anomaly score into a band.
- `describe_signal` turns a flag's `features` into one clinician-readable line.
- `citizen_ref` is the short handle for a person, the same on every page.
"""

import uuid
from typing import Literal

from app.models.enums import AlertSeverity

from .metrics import VITALS, position

Severity = Literal["critical", "high", "moderate", "low"]

# Lower bound of each band, worst first. A flag always has score > 0.
BANDS: tuple[tuple[Severity, float], ...] = (("critical", 0.75), ("high", 0.5), ("moderate", 0.25), ("low", 0.0))
SEVERITY_RANK: dict[str, int] = {name: rank for rank, (name, _) in enumerate(BANDS)}


def severity_of(anomaly_score: float) -> Severity:
    for name, floor in BANDS:
        if anomaly_score >= floor:
            return name
    return "low"


def band_bounds(severity: Severity) -> tuple[float, float | None]:
    """[low, high) score range of a band, for filtering in SQL. None: no upper bound."""
    index = [name for name, _ in BANDS].index(severity)
    upper = BANDS[index - 1][1] if index > 0 else None
    return BANDS[index][1], upper


def alert_severity(severity: Severity) -> AlertSeverity:
    """alerts.severity has three levels; critical and high both map to high."""
    if severity in ("critical", "high"):
        return AlertSeverity.high
    return AlertSeverity.medium if severity == "moderate" else AlertSeverity.low


def citizen_ref(user_id: uuid.UUID) -> str:
    """HN-XXXXXXXX: derived from the id, so it never changes and never differs between pages."""
    return f"HN-{user_id.hex[:8].upper()}"


def _degree(contribution: float) -> str:
    if contribution >= 2:
        return "well "
    if contribution < 0.5:
        return "slightly "
    return ""


def _fmt(key: str, value: float) -> str:
    return f"{value:.{VITALS[key].decimals}f}"


def top_signal(features: dict[str, float]) -> str | None:
    """The vital that contributed most, or None when nothing was out of range."""
    key = max(features, key=features.__getitem__, default=None)
    return key if key is not None and features[key] > 0 else None


def describe_signal(features: dict[str, float], vitals: dict[str, float]) -> str | None:
    """'Blood pressure 167/103 mmHg — well above the normal range', from the strongest feature.

    Systolic and diastolic are reported together, as a clinician reads them.
    Returns None when no feature contributed.
    """
    key = top_signal(features)
    if key is None or key not in vitals:
        return None
    direction = position(key, vitals[key])
    if direction == "normal":  # a model may flag an in-range value against a personal baseline
        tail = "unusual for this person"
    else:
        tail = f"{_degree(features[key])}{direction} the normal range"

    if key in ("systolic", "diastolic") and "systolic" in vitals and "diastolic" in vitals:
        reading = f"Blood pressure {_fmt('systolic', vitals['systolic'])}/{_fmt('diastolic', vitals['diastolic'])} mmHg"
    else:
        spec = VITALS[key]
        gap = "" if spec.unit == "%" else " "
        reading = f"{spec.label} {_fmt(key, vitals[key])}{gap}{spec.unit}"
    return f"{reading} — {tail}"
