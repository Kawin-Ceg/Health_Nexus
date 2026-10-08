import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.models.enums import FlagDismissReason, FlagResolution, Gender
from app.schemas.health import AlertOut, BaselineOut, VitalCheck, VisitOut, VisitPerson

Severity = Literal["critical", "high", "moderate", "low"]
Engagement = Literal["attention", "never_logged", "silent", "ok"]


class FacilityOut(BaseModel):
    id: uuid.UUID
    name: str
    district: str
    block: str | None


class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    moderate: int = 0
    low: int = 0


class EngagementCounts(BaseModel):
    attention: int = 0
    never_logged: int = 0
    silent: int = 0
    ok: int = 0


class DashboardOut(BaseModel):
    facility: FacilityOut
    citizens: int
    citizens_flagged: int
    open_flags: int
    open_by_severity: SeverityCounts
    readings_last_7_days: int
    citizens_submitting_last_7_days: int
    engagement: EngagementCounts
    silent_after_days: int
    visits_needing_outcome: int
    visits_today: int


class WeekValue(BaseModel):
    week_start: date
    value: int
    partial: bool  # the current week, still in progress


class Kpi(BaseModel):
    key: str
    label: str
    weeks: list[WeekValue]


class OverviewOut(BaseModel):
    kpis: list[Kpi]
    week_starts_on: str
    timezone: str


class CaseOut(BaseModel):
    processed_id: uuid.UUID
    citizen: VisitPerson
    severity: Severity
    anomaly_score: float
    signal: str | None
    features: dict[str, float]
    vitals: dict[str, float]
    symptoms: list[str]
    measured_at: datetime
    basis: str | None  # NULL: scored before score details were stored


class QueueOut(BaseModel):
    items: list[CaseOut]
    total: int
    limit: int
    offset: int


class Resolve(BaseModel):
    resolution: FlagResolution = FlagResolution.reviewed
    dismiss_reason: FlagDismissReason | None = None
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None

    @model_validator(mode="after")
    def _reason_matches(self) -> "Resolve":
        if self.resolution == FlagResolution.dismissed and self.dismiss_reason is None:
            raise ValueError("Say why the flag is being dismissed")
        if self.resolution == FlagResolution.reviewed and self.dismiss_reason is not None:
            raise ValueError("A dismiss reason only applies when dismissing")
        return self


class Cleared(BaseModel):
    cleared: int


class FlagBrief(BaseModel):
    processed_id: uuid.UUID
    severity: Severity
    signal: str | None
    symptoms: list[str]
    measured_at: datetime
    basis: str | None


class WorkItem(BaseModel):
    citizen: VisitPerson
    open_flags: int
    worst_severity: Severity
    worst_signal: str | None
    first_flagged_at: datetime
    last_flagged_at: datetime
    flags: list[FlagBrief]  # worst first, capped
    flags_shown: int
    next_visit: VisitOut | None


class WorklistOut(BaseModel):
    items: list[WorkItem]
    total_citizens: int
    limit: int


class DirectoryItem(BaseModel):
    citizen: VisitPerson
    age: int | None
    gender: Gender | None
    status: Engagement
    open_flags: int
    worst_severity: Severity | None
    readings: int
    last_reading_at: datetime | None
    joined_at: datetime


class LocalityCount(BaseModel):
    locality: str
    citizens: int


class DirectoryOut(BaseModel):
    items: list[DirectoryItem]
    total: int  # matching the filters
    limit: int
    offset: int
    counts: EngagementCounts  # the whole catchment, never the filtered page
    catchment_total: int
    localities: list[LocalityCount]
    silent_after_days: int


class RecordIdentity(BaseModel):
    id: uuid.UUID
    ref: str
    name: str
    phone: str | None
    email: str
    area: str | None
    pincode: str | None
    age: int | None
    gender: Gender | None
    blood_group: str | None
    existing_conditions: list[str]
    current_medications: list[str]
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    joined_at: datetime


class RecordVital(BaseModel):
    key: str
    latest: float
    latest_at: datetime
    position: str
    readings: int
    # The scorer's baseline for this person, from the readings before the latest one.
    baseline: BaselineOut | None
    z_score: float | None


class TimelineEntry(BaseModel):
    reading_id: uuid.UUID
    processed_id: uuid.UUID | None
    measured_at: datetime
    vitals: dict[str, float]
    symptoms: list[str]
    flagged: bool
    severity: Severity | None
    signal: str | None
    resolution: FlagResolution | None
    reviewed_at: datetime | None
    basis: str | None
    checks: list[VitalCheck]  # empty for readings scored before score details were stored


class Unresolved(BaseModel):
    open_flags: int
    oldest_flag_at: datetime | None
    visits_without_outcome: int


class RecordWindow(BaseModel):
    start: datetime
    end: datetime
    days: int


class RecordCounts(BaseModel):
    readings: int
    flags: int
    open_flags: int
    alerts: int
    visits: int


class RecordOut(BaseModel):
    identity: RecordIdentity
    window: RecordWindow
    counts: RecordCounts
    vitals: list[RecordVital]
    timeline: list[TimelineEntry]
    timeline_truncated: bool
    timeline_limit: int
    alerts: list[AlertOut]
    visits: list[VisitOut]
    upcoming_visits: list[VisitOut]  # after the window's end, reported separately
    unresolved_before_window: Unresolved
    min_baseline_readings: int


class FeedItem(BaseModel):
    processed_id: uuid.UUID
    citizen: VisitPerson
    severity: Severity
    signal: str | None
    measured_at: datetime
    status: Literal["open", "reviewed", "dismissed"]
    reviewed_by: str | None
    reviewed_at: datetime | None


class FeedOut(BaseModel):
    items: list[FeedItem]
    days: int
    limit: int


class DailyVolume(BaseModel):
    date: date
    readings: int
    flags: int


class LocalityVolume(BaseModel):
    locality: str
    citizens: int
    submitting: int
    readings: int
    flags: int


class ReportsOut(BaseModel):
    window: RecordWindow
    readings: int
    citizens_submitting: int
    flags: int
    flag_rate: float | None
    catchment_now: int
    daily: list[DailyVolume]
    localities: list[LocalityVolume]
    min_cell: int


class LocalityRisk(BaseModel):
    locality: str
    citizens: int
    flagged: int
    share: float
    level: Literal["high", "elevated", "some", "none"]
    lat: float | None
    lng: float | None


class LocalityRiskOut(BaseModel):
    items: list[LocalityRisk]
    min_cell: int


class MapOut(LocalityRiskOut):
    facility: FacilityOut
    facility_lat: float | None
    facility_lng: float | None


class VisitCreate(BaseModel):
    citizen_id: uuid.UUID
    case_id: uuid.UUID | None = None
    scheduled_for: datetime
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    location: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None = None

    @field_validator("scheduled_for")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scheduled_for needs a timezone")
        return value


class VisitsOut(BaseModel):
    items: list[VisitOut]
    limit: int


Limit = Annotated[int, Field(ge=1, le=200)]
