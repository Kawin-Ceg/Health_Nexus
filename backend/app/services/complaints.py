"""Complaints backed by what the app itself recorded.

A worker can only complain that a citizen keeps missing visits when the record shows
it: at least MISSED_THRESHOLD visits marked "nobody there" in the last MISSED_WINDOW
that the citizen has not explained. A citizen's explanation takes that visit out of the count.
"""

import uuid
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HealthRecord, ScheduledVisit, User
from app.models.enums import ConcernCategory, UserRole, VisitStatus
from app.services.catchment import in_catchment
from app.services.visit_state import format_local, now_utc, overdue_before

MISSED_WINDOW = timedelta(days=90)
MISSED_THRESHOLD = 3

CITIZEN_CATEGORIES = {
    ConcernCategory.device_issue,
    ConcernCategory.worker_no_show,
    ConcernCategory.worker_conduct,
    ConcernCategory.incorrect_diagnosis_flag,
    ConcernCategory.data_misuse,
    ConcernCategory.access_request,
    ConcernCategory.app_problem,
    ConcernCategory.other,
}
WORKER_CATEGORIES = {
    ConcernCategory.citizen_missed_visits,
    ConcernCategory.citizen_conduct,
    ConcernCategory.app_problem,
    ConcernCategory.access_request,
    ConcernCategory.other,
}
ABOUT_A_CITIZEN = {ConcernCategory.citizen_missed_visits, ConcernCategory.citizen_conduct}


def _visit(v: ScheduledVisit, worker: str | None) -> dict[str, Any]:
    return {
        "when": format_local(v.scheduled_for),
        "at": v.scheduled_for.isoformat(),
        "location": v.location,
        "reason": v.reason,
        "worker": worker,
        "status": v.status.value,
        "explanation": v.missed_reason,
    }


async def missed_visits(db: AsyncSession, citizen_id: uuid.UUID, phc_id: uuid.UUID | None) -> dict[str, Any]:
    """The citizen's missed visits with this centre's workers in the window, and whether a complaint is allowed."""
    rows = (await db.execute(
        select(ScheduledVisit, User.name)
        .join(User, User.id == ScheduledVisit.worker_id)
        .where(
            ScheduledVisit.citizen_id == citizen_id,
            ScheduledVisit.status == VisitStatus.missed,
            ScheduledVisit.scheduled_for >= now_utc() - MISSED_WINDOW,
            User.phc_id == phc_id,
        )
        .order_by(ScheduledVisit.scheduled_for.desc())
    )).all()
    visits = [_visit(v, name) for v, name in rows]
    unexplained = sum(1 for v in visits if not v["explanation"])
    return {
        "kind": "missed_visits",
        "window_days": MISSED_WINDOW.days,
        "threshold": MISSED_THRESHOLD,
        "missed": len(visits),
        "unexplained": unexplained,
        "eligible": unexplained >= MISSED_THRESHOLD,
        "visits": visits,
    }


async def _overdue_visits(db: AsyncSession, citizen: User) -> dict[str, Any]:
    """Visits booked for the citizen whose time passed with no outcome recorded by the worker."""
    rows = (await db.execute(
        select(ScheduledVisit, User.name)
        .join(User, User.id == ScheduledVisit.worker_id)
        .where(
            ScheduledVisit.citizen_id == citizen.id,
            ScheduledVisit.status == VisitStatus.scheduled,
            ScheduledVisit.scheduled_for < overdue_before(now_utc()),
        )
        .order_by(ScheduledVisit.scheduled_for.desc())
        .limit(10)
    )).all()
    return {"kind": "worker_no_show", "visits": [_visit(v, name) for v, name in rows]}


async def _watch(db: AsyncSession, citizen: User) -> dict[str, Any]:
    since = now_utc() - timedelta(days=7)
    rows = (await db.execute(
        select(HealthRecord.source, func.count(), func.max(HealthRecord.timestamp))
        .where(HealthRecord.user_id == citizen.id, HealthRecord.timestamp >= since)
        .group_by(HealthRecord.source)
    )).all()
    last_sync = await db.scalar(select(func.max(HealthRecord.timestamp)).where(HealthRecord.user_id == citizen.id, HealthRecord.source == "watch"))
    return {
        "kind": "device",
        "last_sync": format_local(last_sync) if last_sync else None,
        "last_7_days": {source: count for source, count, _ in rows},
    }


async def _last_worker(db: AsyncSession, citizen: User) -> uuid.UUID | None:
    return await db.scalar(
        select(ScheduledVisit.worker_id).where(ScheduledVisit.citizen_id == citizen.id).order_by(ScheduledVisit.scheduled_for.desc()).limit(1)
    )


async def prepare(
    db: AsyncSession, user: User, category: ConcernCategory, subject_id: uuid.UUID | None
) -> tuple[uuid.UUID | None, dict[str, Any] | None]:
    """Check the complaint is allowed for this person, and gather (subject, evidence)."""
    allowed = WORKER_CATEGORIES if user.role == UserRole.phc_worker else CITIZEN_CATEGORIES
    if category not in allowed and category != ConcernCategory.harassment:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That kind of complaint is not available for your account.")

    if category in ABOUT_A_CITIZEN:
        citizen = await db.get(User, subject_id) if subject_id else None
        if citizen is None or not await in_catchment(db, user, citizen):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a citizen registered at your health centre.")
        evidence = await missed_visits(db, citizen.id, user.phc_id)
        if category == ConcernCategory.citizen_missed_visits and not evidence["eligible"]:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"{citizen.name} has {evidence['unexplained']} unexplained missed visit"
                f"{'' if evidence['unexplained'] == 1 else 's'} in the last {evidence['window_days']} days. "
                f"A complaint needs {MISSED_THRESHOLD}; visits they have explained do not count.",
            )
        return citizen.id, evidence

    if user.role == UserRole.user:
        if category == ConcernCategory.device_issue:
            return None, await _watch(db, user)
        if category in (ConcernCategory.worker_no_show, ConcernCategory.worker_conduct):
            evidence = await _overdue_visits(db, user) if category == ConcernCategory.worker_no_show else None
            return await _last_worker(db, user), evidence
    return None, None
