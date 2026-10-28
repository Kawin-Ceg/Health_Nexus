import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPk
from .enums import VisitStatus, pg_enum


class ScheduledVisit(UUIDPk, CreatedAt, Base):
    """A PHC worker's visit to a citizen.

    `status` records decisions only. "Overdue" is derived at read time from
    status + clock by services/visit_state.py and is never stored.
    """

    __tablename__ = "scheduled_visits"
    __table_args__ = (Index("ix_scheduled_visits_worker_id_scheduled_for", "worker_id", "scheduled_for"),)

    worker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("processed_data.id", ondelete="SET NULL"))
    scheduled_for: Mapped[datetime]
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[VisitStatus] = mapped_column(
        pg_enum(VisitStatus, "visit_status"), default=VisitStatus.scheduled, server_default=text("'scheduled'")
    )
    location: Mapped[str | None] = mapped_column(String(160))
    missed_notified_at: Mapped[datetime | None]
    missed_reason: Mapped[str | None] = mapped_column(Text)
    missed_reason_at: Mapped[datetime | None]
    visit_type: Mapped[str] = mapped_column(String(24), default="home", server_default="home")
    duration_minutes: Mapped[int] = mapped_column(default=30, server_default="30")
    notes: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[str | None] = mapped_column(String(16))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None]
