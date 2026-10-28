import uuid

from sqlalchemy import ForeignKey, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPk
from .enums import AlertSeverity, AlertType, pg_enum


class Alert(UUIDPk, CreatedAt, Base):
    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    alert_type: Mapped[AlertType] = mapped_column(pg_enum(AlertType, "alert_type"))
    severity: Mapped[AlertSeverity] = mapped_column(pg_enum(AlertSeverity, "alert_severity"))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False, server_default=false())
