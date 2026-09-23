"""Visit notifications: booking tells both sides, and a missed visit tells both sides once.

Messages are worded for the person reading them. A citizen reads about "your
visit"; the worker reads the citizen's name.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, ScheduledVisit, User
from app.models.enums import AlertSeverity, AlertType, VisitStatus

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


def notify_changed(session: AsyncSession, visit: ScheduledVisit, citizen: User, worker: User, change: str) -> None:
    """change: 'cancelled' or 'moved'."""
    when = format_local(visit.scheduled_for)
    if change == "cancelled":
        to_citizen = f"Your health centre visit on {when} has been cancelled."
        to_worker = f"Visit for {citizen.name} on {when} cancelled."
    else:
        to_citizen = f"Your health centre visit has been moved to {when}."
        to_worker = f"Visit for {citizen.name} moved to {when}."
    session.add_all([_alert(citizen.id, to_citizen, AlertSeverity.medium), _alert(worker.id, to_worker)])


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
    await session.commit()
    return len(claimed)
