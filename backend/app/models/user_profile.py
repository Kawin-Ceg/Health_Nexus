import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPk, utcnow
from .enums import BloodGroup, Gender, pg_enum

if TYPE_CHECKING:
    from .user import User


class UserProfile(UUIDPk, CreatedAt, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    age: Mapped[int]
    gender: Mapped[Gender] = mapped_column(pg_enum(Gender, "gender"))
    height_cm: Mapped[float]
    weight_kg: Mapped[float]
    blood_group: Mapped[BloodGroup | None] = mapped_column(pg_enum(BloodGroup, "blood_group"))
    existing_conditions: Mapped[list[str]] = mapped_column(JSON, default=list, server_default=text("'[]'"))
    current_medications: Mapped[list[str]] = mapped_column(JSON, default=list, server_default=text("'[]'"))
    emergency_contact_name: Mapped[str | None] = mapped_column(String)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String)
    has_smartwatch: Mapped[bool] = mapped_column(default=False, server_default=false())
    smartwatch_brand: Mapped[str | None] = mapped_column(String)
    permission_health_tracking: Mapped[bool]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="profile")
