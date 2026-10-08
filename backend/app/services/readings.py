"""Recording a reading: store it, score it through the ML seam, tell the citizen.

Used by POST /health/vitals and by the seed scripts, so demo data is scored
exactly the way real data is.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, HealthRecord, ProcessedData, User
from app.models.enums import AlertType

from .catchment import workers_serving
from .scoring import BASELINE_WINDOW, MIN_BASELINE_READINGS, ScoreResult, robust_baseline, score_reading
from .triage import alert_severity, describe_signal, severity_of
from .visit_state import format_local

# How many earlier readings the scorer sees.
SCORING_HISTORY = 120


@dataclass(frozen=True)
class Recorded:
    record: HealthRecord
    processed: ProcessedData
    score: ScoreResult
    earlier_readings: int
    signal: str | None
    reviewed_by_someone: bool


@dataclass(frozen=True)
class Baseline:
    usual: float  # the model's personal median
    spread: float  # its robust SD
    n: int


def baseline_of(key: str, values: list[float]) -> Baseline | None:
    """The scorer's own baseline for display, or None below MIN_BASELINE_READINGS:
    no baseline is better than a fake one. `values` oldest first."""
    if len(values) < MIN_BASELINE_READINGS:
        return None
    usual, spread = robust_baseline(key, values)
    return Baseline(usual=usual, spread=spread, n=min(len(values), BASELINE_WINDOW))


async def earlier_vitals(session: AsyncSession, user_id: uuid.UUID, before: datetime) -> list[dict[str, float]]:
    """Up to SCORING_HISTORY readings measured before `before`, oldest first."""
    rows = await session.scalars(
        select(HealthRecord.vitals)
        .where(HealthRecord.user_id == user_id, HealthRecord.timestamp < before)
        .order_by(HealthRecord.timestamp.desc())
        .limit(SCORING_HISTORY)
    )
    return list(reversed(rows.all()))


def _citizen_message(signal: str, measured_at: datetime, reviewed: bool) -> str:
    follow_up = (
        "Your health centre has been notified and may contact you."
        if reviewed
        else "No health worker is assigned to your centre yet, so nobody is reviewing this. "
        "If you feel unwell, see a doctor."
    )
    return f"Your reading from {format_local(measured_at)} was flagged: {signal}. {follow_up}"


async def record_reading(
    session: AsyncSession,
    citizen: User,
    vitals: dict[str, float],
    symptoms: list[str],
    measured_at: datetime,
    *,
    stored_at: datetime | None = None,
) -> Recorded:
    """Store and score one already-validated reading. Flushes; the caller commits."""
    history = await earlier_vitals(session, citizen.id, measured_at)
    record = HealthRecord(
        user_id=citizen.id,
        vitals=vitals,
        symptoms=symptoms,
        geo_lat=citizen.geo_lat,
        geo_lng=citizen.geo_lng,
        timestamp=measured_at,
    )
    if stored_at is not None:
        record.created_at = stored_at
    session.add(record)
    await session.flush()

    score = score_reading(citizen.id, vitals, history)
    processed = ProcessedData(
        health_record_id=record.id,
        user_id=citizen.id,
        features=score.features,
        anomaly_score=score.anomaly_score,
        is_anomaly=score.is_anomaly,
        basis=score.basis,
        model_version=score.model_version,
        details=score.details_json(),
    )
    if stored_at is not None:
        processed.processed_at = stored_at
    session.add(processed)

    signal = describe_signal(score.features, vitals) if score.is_anomaly else None
    reviewed = await workers_serving(session, citizen.phc_id) > 0
    if score.is_anomaly:
        alert = Alert(
            user_id=citizen.id,
            alert_type=AlertType.personal,
            severity=alert_severity(severity_of(score.anomaly_score)),
            message=_citizen_message(signal or "one of your values is outside its usual range", measured_at, reviewed),
        )
        if stored_at is not None:
            alert.created_at = stored_at
        session.add(alert)
    await session.flush()
    return Recorded(record, processed, score, len(history), signal, reviewed)
