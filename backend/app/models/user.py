import copy
import json
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, ForeignKey, String, false, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPk
from .enums import UserRole, pg_enum

if TYPE_CHECKING:
    from .phc_application import PhcApplication
    from .user_profile import UserProfile
    from .valid_phc_facility import ValidPhcFacility

DEFAULT_PREFERENCES: dict[str, Any] = {
    "theme": "light",
    "language": "en",
    "notifications": {
        "alerts": {"email": True},
        "visits": {"email": True},
    },
    "alert_email_min_severity": "low",
    "working_hours": {"start": "09:00", "end": "17:00"},
    "reading_reminders": True,
}


def default_preferences() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_PREFERENCES)


class User(UUIDPk, CreatedAt, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"), default=UserRole.user, server_default=text("'user'")
    )
    consent: Mapped[bool] = mapped_column(default=False, server_default=false())
    profile_completed: Mapped[bool] = mapped_column(default=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    avatar_url: Mapped[str | None] = mapped_column(String)
    cover_url: Mapped[str | None] = mapped_column(String)
    bio: Mapped[str | None] = mapped_column(String(280))
    phone: Mapped[str | None] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String)
    department: Mapped[str | None] = mapped_column(String)
    date_of_birth: Mapped[date | None] = mapped_column(Date)

    phc_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("valid_phc_facilities.id"), index=True)
    district: Mapped[str | None] = mapped_column(String, index=True)
    state: Mapped[str | None] = mapped_column(String, index=True)
    pincode: Mapped[str | None] = mapped_column(String(6), index=True)
    area: Mapped[str | None] = mapped_column(String(120))
    geo_lat: Mapped[float | None]
    geo_lng: Mapped[float | None]

    is_verified: Mapped[bool] = mapped_column(default=False, server_default=false())
    verified_at: Mapped[datetime | None]
    verification_token_hash: Mapped[str | None] = mapped_column(String, index=True)
    verification_token_expires_at: Mapped[datetime | None]
    verification_sent_at: Mapped[datetime | None]
    verification_deadline: Mapped[datetime | None]

    password_reset_token_hash: Mapped[str | None] = mapped_column(String, index=True)
    password_reset_expires_at: Mapped[datetime | None]
    password_reset_sent_at: Mapped[datetime | None]

    email_verified: Mapped[bool] = mapped_column(default=False, server_default=false())
    pending_email: Mapped[str | None] = mapped_column(String)
    email_token_hash: Mapped[str | None] = mapped_column(String)
    email_token_expires_at: Mapped[datetime | None]

    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=default_preferences, server_default=text(f"'{json.dumps(DEFAULT_PREFERENCES)}'")
    )
    deactivated_at: Mapped[datetime | None]
    reading_reminder_at: Mapped[datetime | None]

    facility: Mapped["ValidPhcFacility | None"] = relationship(back_populates="users")
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)
    phc_application: Mapped["PhcApplication | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="PhcApplication.user_id"
    )
