import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPk, utcnow
from .enums import FlagDismissReason, FlagResolution, pg_enum

if TYPE_CHECKING:
    from .health_record import HealthRecord


class ProcessedData(UUIDPk, Base):
    """The score for one reading.

    An open flag is `is_anomaly = true AND resolution IS NULL`.
    """

    __tablename__ = "processed_data"

    health_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("health_records.id"), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    # Per-vital contribution, e.g. {"systolic": 2.8}, so a flag can explain itself.
    features: Mapped[dict[str, float]] = mapped_column(JSON)
    anomaly_score: Mapped[float]
    is_anomaly: Mapped[bool]
    # How it was judged (services/scoring.py). NULL on rows scored before 0010.
    basis: Mapped[str | None] = mapped_column(String(32))
    model_version: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, dict] | None] = mapped_column(JSON)
    processed_at: Mapped[datetime] = mapped_column(default=utcnow)

    reviewed_at: Mapped[datetime | None]
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolution: Mapped[FlagResolution | None] = mapped_column(pg_enum(FlagResolution, "flag_resolution"))
    dismiss_reason: Mapped[FlagDismissReason | None] = mapped_column(
        pg_enum(FlagDismissReason, "flag_dismiss_reason")
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)

    health_record: Mapped["HealthRecord"] = relationship(back_populates="processed")
