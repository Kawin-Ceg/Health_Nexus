import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPk
from .enums import ApplicationStatus, Designation, pg_enum

if TYPE_CHECKING:
    from .phc_verification_audit_log import PhcVerificationAuditLog
    from .phc_verification_document import PhcVerificationDocument
    from .user import User


class PhcApplication(UUIDPk, CreatedAt, Base):
    """A worker's application. phc_name/district/state are what the applicant *claimed*;
    facility_id is the registry match, if one was found."""

    __tablename__ = "phc_applications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    employee_id: Mapped[str] = mapped_column(String)
    designation: Mapped[Designation] = mapped_column(pg_enum(Designation, "designation"))
    phc_name: Mapped[str] = mapped_column(String)
    district: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    years_of_service: Mapped[int]
    status: Mapped[ApplicationStatus] = mapped_column(
        pg_enum(ApplicationStatus, "application_status"),
        default=ApplicationStatus.pending,
        server_default=text("'pending'"),
    )
    rejection_reason: Mapped[str | None] = mapped_column(String)
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("valid_phc_facilities.id"))
    last_checked_at: Mapped[datetime | None]
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship(back_populates="phc_application", foreign_keys=[user_id])
    documents: Mapped[list["PhcVerificationDocument"]] = relationship(
        back_populates="application", cascade="all, delete-orphan", passive_deletes=True
    )
    audit_entries: Mapped[list["PhcVerificationAuditLog"]] = relationship(back_populates="application")
