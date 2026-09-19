import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPk, utcnow
from .enums import PhcVerificationAction, pg_enum

if TYPE_CHECKING:
    from .phc_application import PhcApplication


class PhcVerificationAuditLog(UUIDPk, Base):
    """Append-only record of every verification decision."""

    __tablename__ = "phc_verification_audit_log"

    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("phc_applications.id"), index=True)
    subject_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[PhcVerificationAction] = mapped_column(pg_enum(PhcVerificationAction, "phc_verification_action"))
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)
    auto_check_summary: Mapped[str | None] = mapped_column(Text)
    override_reason: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str] = mapped_column(String, default="unknown", server_default=text("'unknown'"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    application: Mapped["PhcApplication"] = relationship(back_populates="audit_entries")
