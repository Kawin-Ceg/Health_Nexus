"""Row → response builders shared by several routers."""

from datetime import datetime

from app.models import Alert, ProcessedData, ScheduledVisit, User
from app.schemas.health import AlertOut, PopulationOut, VitalCheck, VitalsResult, VisitOut, VisitPerson
from app.services.readings import Recorded
from app.services.scoring import MIN_BASELINE_READINGS, ScoreResult
from app.services.triage import citizen_ref, severity_of, top_signal
from app.services.visit_state import visit_state


def alert_out(alert: Alert) -> AlertOut:
    return AlertOut.model_validate(alert)


def person(citizen: User) -> VisitPerson:
    return VisitPerson(id=citizen.id, ref=citizen_ref(citizen.id), name=citizen.name, phone=citizen.phone, area=citizen.area)


def _base(visit: ScheduledVisit, now: datetime) -> dict:
    return {
        "id": visit.id,
        "scheduled_for": visit.scheduled_for,
        "reason": visit.reason,
        "location": visit.location,
        "status": visit.status,
        "state": visit_state(visit.status, visit.scheduled_for, now),
        "case_id": visit.case_id,
        "missed_reason": visit.missed_reason,
        "visit_type": visit.visit_type,
        "duration_minutes": visit.duration_minutes,
        "cancelled_by": visit.cancelled_by,
        "cancel_reason": visit.cancel_reason,
        "booked_at": visit.created_at,
        "cancelled_at": visit.cancelled_at,
        "missed_reason_at": visit.missed_reason_at,
    }


def visit_for_citizen(visit: ScheduledVisit, worker_name: str | None, now: datetime) -> VisitOut:
    return VisitOut(**_base(visit, now), worker_name=worker_name)


def visit_for_worker(visit: ScheduledVisit, citizen: User, now: datetime) -> VisitOut:
    return VisitOut(**_base(visit, now), citizen=person(citizen), notes=visit.notes)


def checks_of(processed: ProcessedData | None) -> list[VitalCheck]:
    """The stored per-vital judgement of a score. Empty for rows scored before it was stored."""
    if processed is None or not processed.details:
        return []
    return [
        VitalCheck(**detail, key=key, contribution=processed.features.get(key, 0.0))
        for key, detail in processed.details.items()
    ]


def _score_checks(score: ScoreResult) -> list[VitalCheck]:
    return [
        VitalCheck(**vars(detail), key=key, contribution=score.features.get(key, 0.0))
        for key, detail in score.details.items()
    ]


def basis_note(score: ScoreResult) -> str:
    """One sentence on what the reading was compared with, from the least-known vital up."""
    stages = {d.stage for d in score.details.values()}
    if not stages or stages == {"learning"}:
        fewest = min((d.readings for d in score.details.values()), default=0)
        remaining = MIN_BASELINE_READINGS - fewest
        return (
            f"Compared with published normal ranges. After {remaining} more "
            f"reading{'s' if remaining != 1 else ''} we start learning what is normal for you."
        )
    if stages == {"personal"}:
        return "Compared with your own usual readings."
    return "Compared partly with published normal ranges and partly with your own usual readings, which count for more as you log more."


def vitals_result(recorded: Recorded) -> VitalsResult:
    score = recorded.score
    record = recorded.record
    return VitalsResult(
        id=record.id,
        measured_at=record.timestamp,
        vitals=record.vitals,
        source=record.source,
        flagged=score.is_anomaly,
        anomaly_score=score.anomaly_score,
        severity=severity_of(score.anomaly_score) if score.is_anomaly else None,
        driver=top_signal(score.features) if score.is_anomaly else None,
        signal=recorded.signal,
        features=score.features,
        basis=score.basis,
        earlier_readings=recorded.earlier_readings,
        basis_note=basis_note(score),
        reviewed_by_someone=recorded.reviewed_by_someone,
        model_version=score.model_version,
        checks=_score_checks(score),
        watch=score.watch,
        population=PopulationOut.of(score.population_json()),
    )

