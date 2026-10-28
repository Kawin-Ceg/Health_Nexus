import uuid
from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.models.enums import AdvisoryScope, AlertSeverity, AlertType, VisitStatus
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


class VitalCheck(BaseModel):
    """How one vital of a reading was judged (services/scoring.VitalDetail, plus its final contribution)."""

    key: str
    value: float
    stage: Literal["learning", "blending", "personal"]
    readings: int
    weight: float
    published: float
    safety: bool
    baseline: float | None = None
    spread: float | None = None
    z: float | None = None
    personal: float | None = None
    confirmed: bool = True
    contribution: float


class PopulationOut(BaseModel):
    """The trained population model's check (services/population.py). It informs; it never flags."""

    score: float
    percentile: float
    features: list[str]
    version: str
    unusual: bool
    note: str

    @classmethod
    def of(cls, stored: dict | None) -> "PopulationOut | None":
        if not stored:
            return None
        from app.services.population import describe

        return cls(
            score=stored["score"],
            percentile=stored["percentile"],
            features=list(stored["features"]),
            version=stored["version"],
            unusual=stored["score"] >= 0.5,
            note=describe(stored["score"], stored["percentile"], stored["features"]),
        )


class VitalsResult(BaseModel):
    id: uuid.UUID
    measured_at: datetime
    vitals: dict[str, float] = {}
    source: str = "watch"
    flagged: bool
    anomaly_score: float
    severity: Severity | None
    driver: str | None
    signal: str | None
    features: dict[str, float]
    basis: str
    earlier_readings: int
    basis_note: str
    reviewed_by_someone: bool
    model_version: str
    checks: list[VitalCheck]
    watch: list[str]
    population: PopulationOut | None = None


class ReadingOut(BaseModel):
    id: uuid.UUID
    measured_at: datetime
    vitals: dict[str, float]
    symptoms: list[str]
    flagged: bool
    severity: Severity | None
    signal: str | None
    reviewed: bool
    population: PopulationOut | None = None
    source: str = "self"
    watch_slot: str | None = None
    recorded_by: str | None = None
    location: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class ReviewerOption(BaseModel):
    id: uuid.UUID
    name: str


class HistoryOut(BaseModel):
    items: list[ReadingOut]
    total: int
    page: int
    page_size: int
    reviewers: list[ReviewerOption] = []


class BaselineOut(BaseModel):
    """The scorer's personal baseline: median and robust SD of the last readings (n of them)."""

    usual: float
    spread: float
    n: int


class LatestVital(BaseModel):
    key: str
    value: float
    measured_at: datetime
    position: str
    baseline: BaselineOut | None


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
    citizen: VisitPerson | None = None
    worker_name: str | None = None
    missed_reason: str | None = None
    visit_type: str = "home"
    duration_minutes: int = 30
    notes: str | None = None
    cancelled_by: str | None = None
    cancel_reason: str | None = None
    worker_phone: str | None = None
    booked_at: datetime | None = None
    cancelled_at: datetime | None = None
    missed_reason_at: datetime | None = None


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
    readings_until_baseline: int
    baseline_window_days: int
    latest: list[LatestVital]
    trend: list[TrendPoint]
    trend_window_days: int
    alerts: list[AlertOut]
    next_visit: VisitOut | None
    facility: FacilitySummary | None


class AdvisoryOut(BaseModel):
    id: uuid.UUID
    scope: AdvisoryScope
    audience: str
    title: str
    body: str
    severity: AlertSeverity
    author: str | None
    created_at: datetime
    expires_at: datetime
    withdrawn_at: datetime | None
    active: bool
    reach: int | None = None
    can_withdraw: bool = False
    area: str | None = None
    radius_km: float | None = None
    red_reason: str | None = None
    feedback: str | None = None
    feedback_note: str | None = None
    feedback_at: datetime | None = None


class AlertsOut(BaseModel):
    alerts: list[AlertOut]
    advisories: list[AdvisoryOut]
    unread: int


class UnreadCount(BaseModel):
    unread: int


class MarkRead(BaseModel):
    ids: Annotated[list[uuid.UUID], Field(max_length=200)] | None = None


class Updated(BaseModel):
    updated: int


class VitalBaseline(BaseModel):
    """Where one vital stands on the way from published ranges to a personal baseline."""

    key: str
    readings: int
    stage: Literal["learning", "blending", "personal"]
    weight: float
    baseline: float | None
    spread: float | None
    readings_to_start: int
    readings_to_full: int


class BaselineStatusOut(BaseModel):
    model_version: str
    min_readings: int
    full_readings: int
    window: int
    vitals: list[VitalBaseline]
