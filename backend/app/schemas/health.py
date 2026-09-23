import uuid
from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.models.enums import AlertSeverity, AlertType, VisitStatus
from app.services.metrics import VITALS, ImplausibleVitalError, validate_vitals
from app.services.visit_state import VisitState, now_utc

MAX_SYMPTOMS = 12
BACKDATE_LIMIT = timedelta(days=30)

Symptom = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=2, max_length=40)]


class MetricOut(BaseModel):
    key: str
    label: str
    unit: str
    group: str
    normal: tuple[float, float] | None
    plausible: tuple[float, float]
    decimals: int


class MetricsOut(BaseModel):
    metrics: list[MetricOut]
    common_symptoms: list[str]
    min_baseline_readings: int


class VitalsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vitals: dict[str, float | None]
    symptoms: Annotated[list[Symptom], Field(max_length=MAX_SYMPTOMS)] = []
    # When it was measured, if not now. Must be aware, not in the future, at most 30 days back.
    measured_at: datetime | None = None

    @field_validator("vitals")
    @classmethod
    def _known_and_plausible(cls, value: dict[str, float | None]) -> dict[str, float]:
        unknown = sorted(set(value) - set(VITALS))
        if unknown:
            raise ValueError(f"Unknown measurement: {', '.join(unknown)}")
        try:
            clean = validate_vitals(value)
        except ImplausibleVitalError as exc:
            raise ValueError(str(exc)) from None
        if not clean:
            raise ValueError("Enter at least one measurement")
        return clean

    @field_validator("symptoms")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @field_validator("measured_at")
    @classmethod
    def _recent_past(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("measured_at needs a timezone")
        now = now_utc()
        if value > now + timedelta(minutes=5):
            raise ValueError("A reading cannot be in the future")
        if value < now - BACKDATE_LIMIT:
            raise ValueError("Readings older than 30 days cannot be added")
        return value

    @model_validator(mode="after")
    def _pressure_order(self) -> "VitalsIn":
        sys_, dia = self.vitals.get("systolic"), self.vitals.get("diastolic")
        if sys_ is not None and dia is not None and dia >= sys_:
            raise ValueError("Diastolic pressure must be lower than systolic. Check the two values are not swapped")
        return self


Severity = Literal["critical", "high", "moderate", "low"]


class VitalsResult(BaseModel):
    id: uuid.UUID
    measured_at: datetime
    flagged: bool
    anomaly_score: float
    severity: Severity | None
    driver: str | None  # the vital key that contributed most
    signal: str | None  # "Blood pressure 167/103 mmHg — well above the normal range"
    features: dict[str, float]
    basis: str
    earlier_readings: int
    basis_note: str
    reviewed_by_someone: bool


class ReadingOut(BaseModel):
    id: uuid.UUID
    measured_at: datetime
    vitals: dict[str, float]
    symptoms: list[str]
    flagged: bool
    severity: Severity | None
    signal: str | None
    reviewed: bool


class HistoryOut(BaseModel):
    items: list[ReadingOut]
    total: int
    page: int
    page_size: int


class BaselineOut(BaseModel):
    mean: float
    sd: float
    n: int


class LatestVital(BaseModel):
    key: str
    value: float
    measured_at: datetime
    position: str  # below / normal / above the published range
    baseline: BaselineOut | None  # None until there are enough earlier readings


class TrendPoint(BaseModel):
    measured_at: datetime
    vitals: dict[str, float]
    flagged: bool


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    is_read: bool
    created_at: datetime


class VisitPerson(BaseModel):
    id: uuid.UUID
    ref: str
    name: str
    phone: str | None = None
    area: str | None = None


class VisitOut(BaseModel):
    id: uuid.UUID
    scheduled_for: datetime
    reason: str | None
    location: str | None
    status: VisitStatus
    state: VisitState
    case_id: uuid.UUID | None
    citizen: VisitPerson | None = None  # set for the worker's view
    worker_name: str | None = None  # set for the citizen's view


class FacilitySummary(BaseModel):
    id: uuid.UUID
    name: str
    district: str
    workers_assigned: int


class SummaryOut(BaseModel):
    readings_total: int
    readings_last_7_days: int
    open_flags: int
    unread_alerts: int
    # Below MIN_BASELINE_READINGS there is no personal baseline; cards compare with published ranges.
    readings_until_baseline: int
    baseline_window_days: int
    latest: list[LatestVital]
    trend: list[TrendPoint]
    trend_window_days: int
    alerts: list[AlertOut]
    next_visit: VisitOut | None
    facility: FacilitySummary | None


class AlertsOut(BaseModel):
    alerts: list[AlertOut]
    advisories: list[AlertOut]
    unread: int


class UnreadCount(BaseModel):
    unread: int


class MarkRead(BaseModel):
    # Omit to mark everything read.
    ids: Annotated[list[uuid.UUID], Field(max_length=200)] | None = None


class Updated(BaseModel):
    updated: int
