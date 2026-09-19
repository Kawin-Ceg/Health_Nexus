import secrets
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPk, utcnow
from .enums import ConcernCategory, ConcernStatus, pg_enum


def new_ticket_ref() -> str:
    return f"HN-{secrets.token_hex(3).upper()}"


class Concern(UUIDPk, CreatedAt, Base):
    """Support tickets raised by users."""

    __tablename__ = "concerns"

    ticket_ref: Mapped[str] = mapped_column(String(16), unique=True, default=new_ticket_ref)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[ConcernCategory] = mapped_column(pg_enum(ConcernCategory, "concern_category"))
    description: Mapped[str] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String)
    status: Mapped[ConcernStatus] = mapped_column(
        pg_enum(ConcernStatus, "concern_status"),
        default=ConcernStatus.open,
        server_default=text("'open'"),
        index=True,
    )
    admin_note: Mapped[str | None] = mapped_column(Text)  # shown back to the user
    handled_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    resolved_at: Mapped[datetime | None]
