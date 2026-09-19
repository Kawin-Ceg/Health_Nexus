from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, false
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPk


class CommunityData(UUIDPk, CreatedAt, Base):
    """Reserved for outbreak clustering output. Nothing writes to it yet."""

    __tablename__ = "community_data"

    region: Mapped[str] = mapped_column(String, index=True)
    symptom_cluster: Mapped[dict[str, Any]] = mapped_column(JSON)
    prevalence_score: Mapped[float]
    outbreak_flag: Mapped[bool] = mapped_column(default=False, server_default=false())
    window_start: Mapped[datetime]
    window_end: Mapped[datetime]
