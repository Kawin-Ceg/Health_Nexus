"""The state of a scheduled visit. The single place it is defined.

The stored `status` records what somebody *decided* (scheduled, completed,
cancelled, missed). The *state* is that status combined with the clock:

    upcoming   scheduled, on a later local day
    today      scheduled, later today
    due_now    its time has passed, but within the grace window
    overdue    past the grace window, and nobody recorded an outcome

Each scheduled visit is in exactly one of those, so counts are disjoint: a visit
earlier today that has passed is `due_now` or `overdue`, never also `today`.
Day boundaries are local (Asia/Kolkata), not UTC.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from app.models.enums import VisitStatus

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
GRACE = timedelta(hours=4)

VisitState = Literal["upcoming", "today", "due_now", "overdue", "completed", "cancelled", "missed"]
# The visit time has passed: "nobody there" may be recorded.
PASSED: frozenset[str] = frozenset({"due_now", "overdue"})


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def local_date(moment: datetime) -> date:
    return moment.astimezone(LOCAL_TZ).date()


def local_day_start(day: date) -> datetime:
    """Local midnight at the start of `day`, as an aware datetime."""
    return datetime.combine(day, time.min, tzinfo=LOCAL_TZ)


def visit_state(status: VisitStatus, scheduled_for: datetime, now: datetime | None = None) -> VisitState:
    now = now or now_utc()
    if status != VisitStatus.scheduled:
        return status.value  # type: ignore[return-value]
    if scheduled_for > now:
        return "today" if local_date(scheduled_for) == local_date(now) else "upcoming"
    if now - scheduled_for <= GRACE:
        return "due_now"
    return "overdue"


def overdue_before(now: datetime | None = None) -> datetime:
    """A scheduled visit before this instant is overdue. For SQL filters."""
    return (now or now_utc()) - GRACE


def format_local(moment: datetime) -> str:
    """'Tue 24 Sep, 10:30 AM' in local time, for alert text."""
    local = moment.astimezone(LOCAL_TZ)
    return f"{local:%a} {local.day} {local:%b}, {local.hour % 12 or 12}:{local:%M %p}"
