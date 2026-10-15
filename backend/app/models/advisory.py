import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPk
from .enums import AdvisoryScope, AlertSeverity, pg_enum


class Advisory(UUIDPk, CreatedAt, Base):
    """A community health notice. Who sees it follows from scope: one centre, one district, or a state."""

    __tablename__ = "advisories"

    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    scope: Mapped[AdvisoryScope] = mapped_column(pg_enum(AdvisoryScope, "advisory_scope"))
    phc_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("valid_phc_facilities.id"), index=True)
    district: Mapped[str | None] = mapped_column(String, index=True)
    state: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    severity: Mapped[AlertSeverity] = mapped_column(pg_enum(AlertSeverity, "alert_severity"))
    expires_at: Mapped[datetime] = mapped_column(index=True)
    withdrawn_at: Mapped[datetime | None]
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("community_data.id", ondelete="SET NULL"))
