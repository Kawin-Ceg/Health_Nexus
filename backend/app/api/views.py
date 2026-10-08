"""Row → response builders shared by several routers."""

from datetime import datetime

from app.models import Alert, ProcessedData, ScheduledVisit, User
from app.schemas.health import AlertOut, VitalCheck, VisitOut, VisitPerson
from app.services.triage import citizen_ref
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
    }


def visit_for_citizen(visit: ScheduledVisit, worker_name: str | None, now: datetime) -> VisitOut:
    return VisitOut(**_base(visit, now), worker_name=worker_name)


def visit_for_worker(visit: ScheduledVisit, citizen: User, now: datetime) -> VisitOut:
    return VisitOut(**_base(visit, now), citizen=person(citizen))


def checks_of(processed: ProcessedData | None) -> list[VitalCheck]:
    """The stored per-vital judgement of a score. Empty for rows scored before it was stored."""
    if processed is None or not processed.details:
        return []
    return [
        VitalCheck(**detail, key=key, contribution=processed.features.get(key, 0.0))
        for key, detail in processed.details.items()
    ]
