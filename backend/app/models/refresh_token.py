import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPk, utcnow


class RefreshToken(UUIDPk, CreatedAt, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)  # SHA-256 hex, never raw
    expires_at: Mapped[datetime]
    revoked: Mapped[bool] = mapped_column(default=False, server_default=false())
    last_activity_at: Mapped[datetime] = mapped_column(default=utcnow)
    revoked_at: Mapped[datetime | None]
    revoked_reason: Mapped[str | None] = mapped_column(String)
    user_agent: Mapped[str | None] = mapped_column(String)
    ip_address: Mapped[str | None] = mapped_column(String)
    device_label: Mapped[str | None] = mapped_column(String)
    # Rotation chain: presenting a token that has already been rotated means reuse.
    rotated_from: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("refresh_tokens.id"))

    previous: Mapped["RefreshToken | None"] = relationship(remote_side="RefreshToken.id")
