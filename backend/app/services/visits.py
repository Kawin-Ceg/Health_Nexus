"""Visit notifications: booking tells both sides, and a missed visit tells both sides once.

Messages are worded for the person reading them. A citizen reads about "your
visit"; the worker reads the citizen's name. Each in-app alert is also emailed
to people who asked for visit emails (services/notify.py).
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, ScheduledVisit, User
from app.models.enums import AlertSeverity, AlertType, VisitStatus

from . import notify
from .visit_state import format_local, now_utc, overdue_before


def _alert(user_id: uuid.UUID, message: str, severity: AlertSeverity = AlertSeverity.low) -> Alert:
    return Alert(user_id=user_id, alert_type=AlertType.personal, severity=severity, message=message)


def notify_booked(session: AsyncSession, visit: ScheduledVisit, citizen: User, worker: User) -> None:
    when = format_local(visit.scheduled_for)
    session.add_all(
        [
            _alert(
                citizen.id,
                f"{worker.name} from your health centre will visit you on {when}"
                + (f" ({visit.reason})." if visit.reason else "."),
                AlertSeverity.medium,
            ),
            _alert(worker.id, f"Visit booked for {citizen.name} on {when}."),
        ]
    )
    notify.visit_booked(session, citizen, worker, visit.scheduled_for)


def notify_changed(session: AsyncSession, visit: ScheduledVisit, citizen: User, worker: User, change: str) -> None:
    """change: 'cancelled' or 'moved'."""
    when = format_local(visit.scheduled_for)
    if change == "cancelled_by_citizen":
        to_citizen = f"You cancelled your visit on {when}."
        to_worker = f"{citizen.name} cancelled the visit on {when}: {visit.cancel_reason}"
    elif change == "cancelled":
        to_citizen = f"Your health centre visit on {when} has been cancelled" + (f": {visit.cancel_reason}" if visit.cancel_reason else ".")
        to_worker = f"Visit for {citizen.name} on {when} cancelled."
    else:
        to_citizen = f"Your health centre visit has been moved to {when}."
        to_worker = f"Visit for {citizen.name} moved to {when}."
    session.add_all([_alert(citizen.id, to_citizen, AlertSeverity.medium), _alert(worker.id, to_worker)])
    notify.visit_changed(session, citizen, worker, visit.scheduled_for, "cancelled" if change.startswith("cancelled") else change)


async def notify_missed(session: AsyncSession, *, worker_id: uuid.UUID | None = None, citizen_id: uuid.UUID | None = None) -> int:
    """Write the one-time 'missed' alerts for overdue visits of one worker or one citizen.

    The UPDATE ... WHERE missed_notified_at IS NULL claims each visit atomically,
    so two schedule loads racing each other cannot both send it. Commits.
    """
    now = now_utc()
    claim = (
        update(ScheduledVisit)
        .where(
            ScheduledVisit.status == VisitStatus.scheduled,
            ScheduledVisit.scheduled_for < overdue_before(now),
            ScheduledVisit.missed_notified_at.is_(None),
        )
        .values(missed_notified_at=now)
        .returning(ScheduledVisit.id, ScheduledVisit.worker_id, ScheduledVisit.citizen_id, ScheduledVisit.scheduled_for)
    )
    if worker_id is not None:
        claim = claim.where(ScheduledVisit.worker_id == worker_id)
    if citizen_id is not None:
        claim = claim.where(ScheduledVisit.citizen_id == citizen_id)
    claimed = (await session.execute(claim)).all()
    if not claimed:
        return 0

    names = dict(
        (await session.execute(select(User.id, User.name).where(User.id.in_({row.citizen_id for row in claimed})))).all()
    )
    for row in claimed:
        when = format_local(row.scheduled_for)
        session.add_all(
            [
                _alert(
                    row.citizen_id,
                    f"Your health centre visit on {when} has no outcome recorded. "
                    "If nobody came, your health centre will rebook it.",
                    AlertSeverity.medium,
                ),
                _alert(
                    row.worker_id,
                    f"Visit for {names.get(row.citizen_id, 'a citizen')} on {when} needs an outcome: "
                    "mark it done, nobody there, or cancelled.",
                    AlertSeverity.medium,
                ),
            ]
        )
    await notify.visits_missed(session, [(row.worker_id, row.citizen_id, row.scheduled_for) for row in claimed])
    await session.commit()
    return len(claimed)


async def cancel_open_visits(session: AsyncSession, citizen: User, *, unless_phc: uuid.UUID | None = None) -> int:
    """Cancel the citizen's booked visits and tell both sides. Visits by workers at `unless_phc` stay."""
    query = (
        select(ScheduledVisit, User)
        .join(User, User.id == ScheduledVisit.worker_id)
        .where(ScheduledVisit.citizen_id == citizen.id, ScheduledVisit.status == VisitStatus.scheduled)
    )
    if unless_phc is not None:
        query = query.where(User.phc_id != unless_phc)
    rows = (await session.execute(query)).all()
    for visit, worker in rows:
        visit.status = VisitStatus.cancelled
        notify_changed(session, visit, citizen, worker, "cancelled")
    return len(rows)
