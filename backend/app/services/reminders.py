"""Reading reminders: one nudge when a citizen has gone quiet, never a stream of them.

A citizen with reminders on (Settings > Preferences) and health tracking allowed
who has logged nothing for READING_REMINDER_AFTER gets one in-app alert, and an
email too. Then nothing more until they log a reading and go quiet again.
`users.reading_reminder_at` remembers the last one.

The API process runs `run_forever` in the background; `send_due` is the unit of work.
"""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Alert, HealthRecord, User
from app.models.enums import AlertSeverity, AlertType, UserRole

from .notify import queue_email
from .preferences import current_preferences
from .visit_state import LOCAL_TZ, now_utc

log = logging.getLogger(__name__)

READING_REMINDER_AFTER = timedelta(days=3)
CHECK_EVERY = timedelta(hours=1)
# Local hours a reminder may go out in: nobody wants one at 2 a.m.
SEND_FROM_HOUR, SEND_UNTIL_HOUR = 9, 20
MESSAGE = (
    "It has been a few days since your last reading. Logging regularly is what lets HealthNexus learn what is "
    "normal for you and spot a change early."
)


async def send_due(session: AsyncSession) -> int:
    """Remind everyone who is due. Commits. Returns how many were reminded."""
    now = now_utc()
    cutoff = now - READING_REMINDER_AFTER
    last_reading = (
        select(func.max(HealthRecord.timestamp)).where(HealthRecord.user_id == User.id).correlate(User).scalar_subquery()
    )
    # Quiet since: their last reading, or when they joined if they have none.
    quiet_since = func.coalesce(last_reading, User.created_at)
    due = await session.scalars(
        select(User).where(
            User.role == UserRole.user,
            User.is_active.is_(True),
            User.profile_completed.is_(True),
            User.consent.is_(True),
            quiet_since < cutoff,
            # One per quiet stretch: none sent since they last logged (or joined).
            or_(User.reading_reminder_at.is_(None), User.reading_reminder_at < quiet_since),
        )
        # Preferences may have changed since this session last loaded these people.
        .execution_options(populate_existing=True)
    )
    sent = 0
    for user in due:
        if not current_preferences(user).reading_reminders:
            continue
        session.add(Alert(user_id=user.id, alert_type=AlertType.personal, severity=AlertSeverity.low, message=MESSAGE))
        queue_email(session, user.email, "Time for a HealthNexus reading", f"Hello {user.name},\n\n{MESSAGE}")
        user.reading_reminder_at = now
        sent += 1
    await session.commit()
    return sent


async def run_forever(maker: async_sessionmaker[AsyncSession]) -> None:
    while True:
        hour = now_utc().astimezone(LOCAL_TZ).hour
        if SEND_FROM_HOUR <= hour < SEND_UNTIL_HOUR:
            try:
                async with maker() as session:
                    if sent := await send_due(session):
                        log.info("Sent %d reading reminders", sent)
            except Exception:  # noqa: BLE001 - a bad run must not stop the next one
                log.exception("Reading reminders failed")
        await asyncio.sleep(CHECK_EVERY.total_seconds())
