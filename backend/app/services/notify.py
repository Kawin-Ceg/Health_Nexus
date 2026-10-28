"""Email copies of in-app alerts, for people who asked for them in Settings > Preferences.

Every alert is always in the app; email is the extra. Emails are queued on the
database session and sent only once it commits, so a request that fails sends
nothing. Bodies carry no readings, names of other people or health details beyond
the severity: an inbox is less private than the app.
"""

import asyncio
import uuid

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import User
from app.models.enums import UserRole

from .mailer import send_email
from .preferences import emails_about, emails_flag
from .triage import Severity, citizen_ref
from .visit_state import format_local

OUTBOX = "hn_outbox"
_sending: set[asyncio.Task] = set()

FOOTER = "\n\nYou get this email because it is turned on in HealthNexus Settings > Preferences.\n"


def _link(path: str) -> str:
    return f"{get_settings().FRONTEND_URL.rstrip('/')}{path}"


def queue_email(session: AsyncSession, to: str, subject: str, body: str) -> None:
    session.info.setdefault(OUTBOX, []).append((to, subject, body + FOOTER))


async def _deliver(queued: list[tuple[str, str, str]]) -> None:
    for to, subject, body in queued:
        await send_email(to, subject, body)


@event.listens_for(Session, "after_commit")
def _send_after_commit(session: Session) -> None:
    queued = session.info.pop(OUTBOX, None)
    if not queued:
        return
    task = asyncio.get_running_loop().create_task(_deliver(queued))
    _sending.add(task)
    task.add_done_callback(_sending.discard)


@event.listens_for(Session, "after_soft_rollback")
def _drop_after_rollback(session: Session, previous_transaction: object) -> None:
    session.info.pop(OUTBOX, None)


async def drain() -> None:
    """Wait for queued emails to go out. For tests and shutdown."""
    while _sending:
        await asyncio.gather(*list(_sending), return_exceptions=True)


async def reading_flagged(
    session: AsyncSession, citizen: User, severity: Severity, signal: str | None, reviewed: bool
) -> None:
    """Email the citizen, and each worker at their centre who asked, about a new flag."""
    if emails_flag(citizen, severity):
        follow_up = (
            "Your health centre has been told and may contact you."
            if reviewed
            else "Nobody at a health centre is reviewing it, so if you feel unwell, see a doctor."
        )
        queue_email(
            session,
            citizen.email,
            "A HealthNexus reading was flagged",
            f"Hello {citizen.name},\n\n"
            f"A reading you logged was flagged ({severity}): {signal or 'one of your values is outside its usual range'}.\n"
            f"{follow_up}\n\nSee it here: {_link('/app/alerts')}\n\n"
            "A flag is a prompt to check, not a diagnosis. In an emergency call 108.",
        )
    if not reviewed or citizen.phc_id is None:
        return
    workers = await session.scalars(
        select(User).where(User.phc_id == citizen.phc_id, User.role == UserRole.phc_worker, User.is_active.is_(True))
    )
    for worker in workers:
        if emails_flag(worker, severity):
            queue_email(
                session,
                worker.email,
                f"New {severity} flag at your health centre",
                f"Hello {worker.name},\n\n"
                f"A reading from {citizen_ref(citizen.id)} was flagged as {severity}.\n"
                f"Open the queue to review it: {_link('/phc/alerts')}",
            )


def visit_email(session: AsyncSession, person: User, subject: str, line: str, path: str) -> None:
    if emails_about(person, "visits"):
        queue_email(session, person.email, subject, f"Hello {person.name},\n\n{line}\n\nDetails: {_link(path)}")


def visit_booked(session: AsyncSession, citizen: User, worker: User, when_utc) -> None:
    when = format_local(when_utc)
    visit_email(session, citizen, "A health centre visit is booked", f"{worker.name} from your health centre will visit you on {when}.", "/app/visits")
    visit_email(session, worker, "Visit booked", f"You booked a visit for {citizen_ref(citizen.id)} on {when}.", "/phc/schedule")


def visit_changed(session: AsyncSession, citizen: User, worker: User, when_utc, change: str) -> None:
    when = format_local(when_utc)
    if change == "cancelled":
        to_citizen, to_worker, subject = (
            f"Your health centre visit on {when} has been cancelled.",
            f"The visit for {citizen_ref(citizen.id)} on {when} was cancelled.",
            "A health centre visit was cancelled",
        )
    else:
        to_citizen, to_worker, subject = (
            f"Your health centre visit has been moved to {when}.",
            f"The visit for {citizen_ref(citizen.id)} was moved to {when}.",
            "A health centre visit was moved",
        )
    visit_email(session, citizen, subject, to_citizen, "/app/visits")
    visit_email(session, worker, subject, to_worker, "/phc/schedule")


async def visits_missed(session: AsyncSession, rows: list[tuple[uuid.UUID, uuid.UUID, object]]) -> None:
    """rows: (worker_id, citizen_id, scheduled_for) of visits that just passed with no outcome."""
    ids = {w for w, _, _ in rows} | {c for _, c, _ in rows}
    people = {u.id: u for u in await session.scalars(select(User).where(User.id.in_(ids)))}
    for worker_id, citizen_id, when_utc in rows:
        when = format_local(when_utc)
        if citizen := people.get(citizen_id):
            visit_email(
                session, citizen, "Your health centre visit has no outcome yet",
                f"Your visit on {when} has no outcome recorded. If nobody came, your health centre will rebook it.",
                "/app/visits",
            )
        if worker := people.get(worker_id):
            visit_email(
                session, worker, "A visit needs an outcome",
                f"The visit for {citizen_ref(citizen_id)} on {when} needs an outcome: done, nobody there, or cancelled.",
                "/phc/schedule",
            )
