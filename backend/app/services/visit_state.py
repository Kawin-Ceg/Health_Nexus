"""Display state of a scheduled visit. The single place "overdue" is defined.

scheduled_visits.status stores decisions only (scheduled, completed, cancelled,
missed). "Overdue" is derived here from status + clock and is never stored.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from app.models.enums import VisitStatus

OVERDUE_AFTER = timedelta(hours=4)

VisitState = Literal["scheduled", "overdue", "completed", "cancelled", "missed"]


def visit_state(status: VisitStatus, scheduled_for: datetime, now: datetime | None = None) -> VisitState:
    now = now or datetime.now(timezone.utc)
    if status == VisitStatus.scheduled and now - scheduled_for > OVERDUE_AFTER:
        return "overdue"
    return status.value
