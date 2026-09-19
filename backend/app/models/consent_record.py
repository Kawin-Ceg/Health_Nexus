import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPk, utcnow
from .enums import ConsentType, pg_enum


class ConsentRecord(UUIDPk, Base):
    """Append-only consent history. Current state = latest row per (user, type)."""

    __tablename__ = "consent_records"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    consent_type: Mapped[ConsentType] = mapped_column(pg_enum(ConsentType, "consent_type"))
    granted: Mapped[bool]
    source: Mapped[str] = mapped_column(String, default="settings", server_default=text("'settings'"))
    ip_address: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
