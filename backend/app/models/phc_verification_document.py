import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPk, utcnow
from .enums import PhcDocumentStatus, PhcDocumentType, pg_enum

if TYPE_CHECKING:
    from .phc_application import PhcApplication


class PhcVerificationDocument(UUIDPk, Base):
    __tablename__ = "phc_verification_documents"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("phc_applications.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    document_type: Mapped[PhcDocumentType] = mapped_column(pg_enum(PhcDocumentType, "phc_document_type"))
    storage_key: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    original_filename: Mapped[str | None] = mapped_column(String)
    status: Mapped[PhcDocumentStatus] = mapped_column(
        pg_enum(PhcDocumentStatus, "phc_document_status"),
        default=PhcDocumentStatus.pending,
        server_default=text("'pending'"),
    )
    ocr_text: Mapped[str | None] = mapped_column(Text)
    extracted_registration_no: Mapped[str | None] = mapped_column(String)
    tamper_score: Mapped[int | None]
    check_notes: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime | None]
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow)
    deleted_at: Mapped[datetime | None]

    application: Mapped["PhcApplication"] = relationship(back_populates="documents")
