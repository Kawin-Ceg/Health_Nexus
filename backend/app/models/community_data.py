import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPk


class CommunityData(UUIDPk, CreatedAt, Base):
    """One outbreak cluster from one clustering run (services/outbreaks.py). A run's rows share window_end."""

    __tablename__ = "community_data"

    region: Mapped[str] = mapped_column(String, index=True)
    syndrome: Mapped[str] = mapped_column(String(32))
    cases: Mapped[int]
    expected: Mapped[float]
    p_value: Mapped[float]
    symptom_cluster: Mapped[dict[str, Any]] = mapped_column(JSON)
    prevalence_score: Mapped[float]
    outbreak_flag: Mapped[bool] = mapped_column(default=False, server_default=false())
    centre_lat: Mapped[float]
    centre_lng: Mapped[float]
    radius_km: Mapped[float]
    district: Mapped[str | None] = mapped_column(String)
    phc_ids: Mapped[list[str]] = mapped_column(JSON)
    first_onset: Mapped[datetime]
    last_onset: Mapped[datetime]
    window_start: Mapped[datetime]
    window_end: Mapped[datetime] = mapped_column(index=True)
    acknowledged_at: Mapped[datetime | None]
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    feedback: Mapped[str | None] = mapped_column(String(16))
    feedback_note: Mapped[str | None] = mapped_column(Text)
    feedback_at: Mapped[datetime | None]
    feedback_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
