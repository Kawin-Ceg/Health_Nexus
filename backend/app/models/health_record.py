import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPk

if TYPE_CHECKING:
    from .processed_data import ProcessedData


class HealthRecord(UUIDPk, CreatedAt, Base):
    """One submitted reading. Vital keys, units and ranges: services/vitals.py."""

    __tablename__ = "health_records"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    vitals: Mapped[dict[str, Any]] = mapped_column(JSON)
    symptoms: Mapped[list[str]] = mapped_column(JSON)
    geo_lat: Mapped[float | None]
    geo_lng: Mapped[float | None]
    timestamp: Mapped[datetime]  # when it was measured; created_at is when it was stored
    # "watch": synced from the citizen's smartwatch; "phc": entered by a health worker at an
    # examination; "self": typed in by the citizen (before smartwatch sync replaced that).
    source: Mapped[str] = mapped_column(String(16), default="self", server_default="self")
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    location: Mapped[str | None] = mapped_column(String(160))
    watch_day: Mapped[date | None]
    watch_slot: Mapped[str | None] = mapped_column(String(16))

    processed: Mapped["ProcessedData | None"] = relationship(back_populates="health_record", uselist=False)
