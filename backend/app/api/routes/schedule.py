"""Visits, as the citizen and the worker each see them, and recording an outcome."""

import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.views import visit_for_citizen, visit_for_worker
from app.core.dependencies import require_onboarding_user
from app.db.session import get_session
from app.models import ScheduledVisit, User
from app.models.enums import VisitStatus
from app.schemas.health import VisitOut
from app.services.catchment import catchment_ids, require_catchment_worker
from app.services.visit_state import PASSED, local_date, local_day_start, now_utc, overdue_before, visit_state
from app.services.visits import notify_changed, notify_missed

router = APIRouter(prefix="/schedule", tags=["schedule"])

VISIT_NOT_FOUND = "Visit not found."
BOOKING_HORIZON = timedelta(days=90)
GROUP_LIMIT = 100
CITIZEN_LIMIT = 100
RECENT_OUTCOMES = timedelta(days=14)
CITIZEN_PAST = timedelta(days=180)


class CitizenScheduleOut(BaseModel):
    visits: list[VisitOut]


@router.get("/mine", response_model=CitizenScheduleOut)
async def my_schedule(
    user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)
) -> CitizenScheduleOut:
    await notify_missed(db, citizen_id=user.id)
    now = now_utc()
    rows = await db.execute(
        select(ScheduledVisit, User.name)
        .join(User, User.id == ScheduledVisit.worker_id)
        .where(
            ScheduledVisit.citizen_id == user.id,
            or_(ScheduledVisit.status == VisitStatus.scheduled, ScheduledVisit.scheduled_for >= now - CITIZEN_PAST),
        )
        .order_by(ScheduledVisit.scheduled_for.desc())
        .limit(CITIZEN_LIMIT)
    )
    return CitizenScheduleOut(visits=[visit_for_citizen(v, name, now) for v, name in rows.all()])


class ScheduleCounts(BaseModel):
    needs_outcome: int
    happening_now: int
    today: int
    upcoming: int
    recent_outcomes: int


class WorkerScheduleOut(BaseModel):
    counts: ScheduleCounts
    needs_outcome: list[VisitOut]
    happening_now: list[VisitOut]
    today: list[VisitOut]
    upcoming: list[VisitOut]
    recent_outcomes: list[VisitOut]
    recent_window_days: int


def _mine(worker: User):
    """This worker's visits with citizens still in the catchment."""
    return (
        select(ScheduledVisit, User)
        .join(User, User.id == ScheduledVisit.citizen_id)
        .where(ScheduledVisit.worker_id == worker.id, ScheduledVisit.citizen_id.in_(catchment_ids(worker)))
    )


@router.get("", response_model=WorkerScheduleOut)
async def worker_schedule(
    worker: User = Depends(require_catchment_worker), db: AsyncSession = Depends(get_session)
) -> WorkerScheduleOut:
    await notify_missed(db, worker_id=worker.id)
    now = now_utc()
    tomorrow = local_day_start(local_date(now) + timedelta(days=1))
    scheduled = ScheduledVisit.status == VisitStatus.scheduled
    # Disjoint by construction; the same boundaries visit_state() uses.
    buckets = {
        "needs_outcome": (scheduled, ScheduledVisit.scheduled_for < overdue_before(now)),
        "happening_now": (
            scheduled,
            ScheduledVisit.scheduled_for >= overdue_before(now),
            ScheduledVisit.scheduled_for <= now,
        ),
        "today": (scheduled, ScheduledVisit.scheduled_for > now, ScheduledVisit.scheduled_for < tomorrow),
        "upcoming": (scheduled, ScheduledVisit.scheduled_for >= tomorrow),
        "recent_outcomes": (~scheduled, ScheduledVisit.scheduled_for >= now - RECENT_OUTCOMES),
    }
    lists: dict[str, list[VisitOut]] = {}
    counts: dict[str, int] = {}
    for name, conditions in buckets.items():
        query = _mine(worker).where(*conditions)
        counts[name] = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        order = ScheduledVisit.scheduled_for.desc() if name == "recent_outcomes" else ScheduledVisit.scheduled_for
        rows = await db.execute(query.order_by(order).limit(GROUP_LIMIT))
        lists[name] = [visit_for_worker(v, citizen, now) for v, citizen in rows.all()]
    return WorkerScheduleOut(
        counts=ScheduleCounts(**counts), recent_window_days=RECENT_OUTCOMES.days, **lists
    )


class VisitUpdate(BaseModel):
    action: Literal["complete", "cancel", "miss", "move"]
    scheduled_for: datetime | None = None  # required for "move"

    @field_validator("scheduled_for")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("scheduled_for needs a timezone")
        return value

    @model_validator(mode="after")
    def _move_needs_time(self) -> "VisitUpdate":
        if self.action == "move" and self.scheduled_for is None:
            raise ValueError("Moving a visit needs the new time")
        return self


def check_booking_time(moment: datetime) -> None:
    now = now_utc()
    if moment <= now:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a time in the future.")
    if moment > now + BOOKING_HORIZON:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Visits can be booked up to 90 days ahead.")


@router.patch("/{visit_id}", response_model=VisitOut)
async def update_visit(
    visit_id: uuid.UUID,
    data: VisitUpdate,
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> VisitOut:
    row = (await db.execute(_mine(worker).where(ScheduledVisit.id == visit_id).with_for_update(of=ScheduledVisit))).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, VISIT_NOT_FOUND)
    visit, citizen = row
    if visit.status != VisitStatus.scheduled:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This visit already has an outcome: {visit.status.value}.")

    now = now_utc()
    state = visit_state(visit.status, visit.scheduled_for, now)
    if data.action == "complete":
        if state == "upcoming":
            raise HTTPException(status.HTTP_409_CONFLICT, "This visit is on a later day. Move it if it happened early.")
        visit.status = VisitStatus.completed
    elif data.action == "miss":
        if state not in PASSED:
            raise HTTPException(status.HTTP_409_CONFLICT, "A visit can only be marked 'nobody there' once its time has passed.")
        visit.status = VisitStatus.missed
    elif data.action == "cancel":
        visit.status = VisitStatus.cancelled
        notify_changed(db, visit, citizen, worker, "cancelled")
    else:
        assert data.scheduled_for is not None
        check_booking_time(data.scheduled_for)
        visit.scheduled_for = data.scheduled_for
        visit.missed_notified_at = None  # a new time earns a new one-time reminder
        notify_changed(db, visit, citizen, worker, "moved")
    await db.commit()
    return visit_for_worker(visit, citizen, now_utc())
