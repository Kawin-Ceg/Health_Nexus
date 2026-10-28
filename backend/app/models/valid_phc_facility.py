from typing import TYPE_CHECKING

from sqlalchemy import String, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPk

if TYPE_CHECKING:
    from .user import User


class ValidPhcFacility(UUIDPk, CreatedAt, Base):
    """The health-centre registry. Users link to it via users.phc_id (the catchment)."""

    __tablename__ = "valid_phc_facilities"

    facility_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    normalised_name: Mapped[str] = mapped_column(String, index=True)
    district: Mapped[str] = mapped_column(String, index=True)
    state: Mapped[str] = mapped_column(String, index=True)
    block: Mapped[str | None] = mapped_column(String)
    official_email_domain: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    is_placeholder: Mapped[bool] = mapped_column(default=False, server_default=false())

    users: Mapped[list["User"]] = relationship(back_populates="facility")
