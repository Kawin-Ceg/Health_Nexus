"""A citizen's own readings: smartwatch sync, list, summarise, delete."""

import uuid
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.views import alert_out, visit_for_citizen, vitals_result
from app.core.dependencies import require_onboarding_user
from app.db.session import get_session
from app.models import Alert, AuditLog, HealthRecord, ProcessedData, ScheduledVisit, User, UserProfile, ValidPhcFacility
from app.models.enums import VisitStatus
from app.schemas.health import (
    BaselineOut,
    BaselineStatusOut,
    VitalBaseline,
    PopulationOut,
    FacilitySummary,
    HistoryOut,
    LatestVital,
    MetricOut,
    MetricsOut,
    ReadingOut,
    SummaryOut,
    TrendPoint,
    VitalsResult,
)
from app.services import watch
from app.services.catchment import workers_serving
from app.services.metrics import COMMON_SYMPTOMS, VITALS, position
from app.services.readings import SCORING_HISTORY, baseline_of, earlier_vitals, submit_reading
from app.services.scoring import (
    BASELINE_WINDOW,
    FULL_BASELINE_READINGS,
    MIN_BASELINE_READINGS,
    MODEL_VERSION,
    baseline_weight,
    robust_baseline,
    stage_of,
)
from app.services.sessions import client_ip
from app.services.triage import describe_signal, severity_of, top_signal
from app.services.visit_state import now_utc

router = APIRouter(prefix="/health", tags=["health"])

READING_NOT_FOUND = "Reading not found."
TRACKING_OFF = "Health tracking is turned off for your account. Turn it on under Settings → Privacy to log readings."
BASELINE_WINDOW_DAYS = 90
TREND_WINDOW_DAYS = 30
SUMMARY_READINGS_CAP = 500


@router.get("/metrics", response_model=MetricsOut)
async def metrics() -> MetricsOut:
    """The vitals vocabulary, so the frontend never keeps its own copy of the ranges."""
    return MetricsOut(
        metrics=[
            MetricOut(
                key=s.key,
                label=s.label,
                unit=s.unit,
                group=s.group,
                normal=s.normal,
                plausible=s.plausible,
                decimals=s.decimals,
            )
            for s in VITALS.values()
        ],
        common_symptoms=list(COMMON_SYMPTOMS),
        min_baseline_readings=MIN_BASELINE_READINGS,
    )


class WatchSlotOut(BaseModel):
    key: str
    label: str
    hours: str
    reading_id: uuid.UUID | None
    measured_at: datetime | None
    vitals: dict[str, float] | None


class WatchOut(BaseModel):
    connected: bool
    brand: str | None
    current_slot: str
    day: date
    slots: list[WatchSlotOut]


class WatchConnect(BaseModel):
    brand: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]


class WatchSyncOut(BaseModel):
    reading: VitalsResult
    slot: str
    already_synced: bool


async def _profile(db: AsyncSession, user: User) -> UserProfile:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Finish setting up your profile first.")
    return profile


def _hours(s: watch.Slot) -> str:
    return f"{s.start:02d}:00–{s.end:02d}:00"


async def _watch_state(db: AsyncSession, user: User, profile: UserProfile) -> WatchOut:
    slot, day = watch.slot_at(now_utc())
    done = await watch.synced_today(db, user.id, day)
    return WatchOut(
        connected=profile.has_smartwatch,
        brand=profile.smartwatch_brand,
        current_slot=slot.key,
        day=day,
        slots=[
            WatchSlotOut(
                key=s.key, label=s.label, hours=_hours(s),
                reading_id=done[s.key].id if s.key in done else None,
                measured_at=done[s.key].timestamp if s.key in done else None,
                vitals=done[s.key].vitals if s.key in done else None,
            )
            for s in watch.SLOTS
        ],
    )


@router.get("/watch", response_model=WatchOut)
async def watch_status(user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)) -> WatchOut:
    return await _watch_state(db, user, await _profile(db, user))


@router.post("/watch/connect", response_model=WatchOut)
async def connect_watch(
    data: WatchConnect, user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)
) -> WatchOut:
    profile = await _profile(db, user)
    profile.has_smartwatch, profile.smartwatch_brand = True, data.brand
    await db.commit()
    return await _watch_state(db, user, profile)


@router.post("/watch/disconnect", response_model=WatchOut)
async def disconnect_watch(user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)) -> WatchOut:
    profile = await _profile(db, user)
    profile.has_smartwatch, profile.smartwatch_brand = False, None
    await db.commit()
    return await _watch_state(db, user, profile)


@router.post("/watch/sync", response_model=WatchSyncOut)
async def sync_watch(
    response: Response, user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)
) -> WatchSyncOut:
    """Fetch the current slot's reading from the watch. Once per slot; a repeat returns the same reading."""
    if not user.consent:
        raise HTTPException(status.HTTP_403_FORBIDDEN, TRACKING_OFF)
    profile = await _profile(db, user)
    if not profile.has_smartwatch:
        raise HTTPException(status.HTTP_409_CONFLICT, "Connect your smartwatch first.")
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
    now = now_utc()
    slot, day = watch.slot_at(now)
    existing = (await watch.synced_today(db, user.id, day)).get(slot.key)
    if existing is not None:
        processed = await db.scalar(select(ProcessedData).where(ProcessedData.health_record_id == existing.id))
        response.status_code = status.HTTP_200_OK
        return WatchSyncOut(reading=_stored_result(existing, processed), slot=slot.key, already_synced=True)
    vitals = await watch.simulate(db, user.id, slot, day)
    recorded = await submit_reading(db, user, vitals, [], now, source="watch", watch_day=day, watch_slot=slot.key)
    response.status_code = status.HTTP_201_CREATED
    return WatchSyncOut(reading=vitals_result(recorded), slot=slot.key, already_synced=False)


def _stored_result(record: HealthRecord, processed: ProcessedData | None) -> VitalsResult:
    flagged = bool(processed and processed.is_anomaly)
    return VitalsResult(
        id=record.id,
        measured_at=record.timestamp,
        vitals=record.vitals,
        source=record.source,
        flagged=flagged,
        anomaly_score=processed.anomaly_score if processed else 0.0,
        severity=severity_of(processed.anomaly_score) if flagged and processed else None,
        driver=top_signal(processed.features) if flagged and processed else None,
        signal=describe_signal(processed.features, record.vitals) if flagged and processed else None,
        features=processed.features if processed else {},
        basis=(processed.basis if processed else None) or "published_ranges",
        earlier_readings=0,
        basis_note="Already synced in this part of the day.",
        reviewed_by_someone=False,
        model_version=(processed.model_version if processed else None) or MODEL_VERSION,
        checks=[],
        watch=[],
        population=PopulationOut.of(processed.population) if processed else None,
    )


def _reading_out(record: HealthRecord, processed: ProcessedData | None, recorders: dict) -> ReadingOut:
    flagged = bool(processed and processed.is_anomaly)
    recorder = recorders.get(record.recorded_by)
    return ReadingOut(
        source=record.source,
        watch_slot=record.watch_slot,
        recorded_by=f"{recorder[0]}, {recorder[1]}" if recorder and recorder[1] else (recorder[0] if recorder else None),
        location=record.location,
        id=record.id,
        measured_at=record.timestamp,
        vitals=record.vitals,
        symptoms=record.symptoms,
        flagged=flagged,
        severity=severity_of(processed.anomaly_score) if flagged and processed else None,
        signal=describe_signal(processed.features, record.vitals) if flagged and processed else None,
        reviewed=bool(processed and processed.resolution is not None),
        population=PopulationOut.of(processed.population) if processed else None,
    )


async def _recorders(db: AsyncSession, ids: set) -> dict:
    if not ids:
        return {}
    rows = await db.execute(
        select(User.id, User.name, ValidPhcFacility.name)
        .outerjoin(ValidPhcFacility, ValidPhcFacility.id == User.phc_id)
        .where(User.id.in_(ids))
    )
    return {uid: (name, facility) for uid, name, facility in rows.all()}


@router.get("/baseline", response_model=BaselineStatusOut)
async def baseline_status(
    user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)
) -> BaselineStatusOut:
    """Per vital: how many readings the model has, and how far it is from published ranges to personal."""
    history = await earlier_vitals(db, user.id, now_utc() + timedelta(minutes=1))
    vitals = []
    for key in VITALS:
        values = [float(h[key]) for h in history if h.get(key) is not None]
        if not values:
            continue
        median, spread = robust_baseline(key, values) if len(values) >= MIN_BASELINE_READINGS else (None, None)
        vitals.append(
            VitalBaseline(
                key=key,
                readings=len(values),
                stage=stage_of(len(values)),
                weight=round(baseline_weight(len(values)), 3),
                baseline=round(median, 2) if median is not None else None,
                spread=round(spread, 2) if spread is not None else None,
                readings_to_start=max(0, MIN_BASELINE_READINGS - len(values)),
                readings_to_full=max(0, FULL_BASELINE_READINGS - len(values)),
            )
        )
    return BaselineStatusOut(
        model_version=MODEL_VERSION,
        min_readings=MIN_BASELINE_READINGS,
        full_readings=FULL_BASELINE_READINGS,
        window=min(BASELINE_WINDOW, SCORING_HISTORY),
        vitals=vitals,
    )


@router.get("/history", response_model=HistoryOut)
async def history(
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
    metric: str | None = Query(None, max_length=40),
    days: int | None = Query(None, ge=1, le=365),
    flagged_only: bool = False,
    user: User = Depends(require_onboarding_user),
    db: AsyncSession = Depends(get_session),
) -> HistoryOut:
    if metric is not None and metric not in VITALS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown metric: {metric}")
    query = (
        select(HealthRecord, ProcessedData)
        .outerjoin(ProcessedData, ProcessedData.health_record_id == HealthRecord.id)
        .where(HealthRecord.user_id == user.id)
    )
    if metric:
        query = query.where(HealthRecord.vitals[metric].as_string().is_not(None))
    if days:
        query = query.where(HealthRecord.timestamp >= now_utc() - timedelta(days=days))
    if flagged_only:
        query = query.where(ProcessedData.is_anomaly.is_(True))

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await db.execute(
        query.order_by(HealthRecord.timestamp.desc(), HealthRecord.id).offset((page - 1) * page_size).limit(page_size)
    )
    rows = rows.all()
    recorders = await _recorders(db, {r.recorded_by for r, _ in rows if r.recorded_by})
    return HistoryOut(
        items=[_reading_out(record, processed, recorders) for record, processed in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=SummaryOut)
async def summary(user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)) -> SummaryOut:
    now = now_utc()
    window_start = now - timedelta(days=BASELINE_WINDOW_DAYS)
    rows = (
        await db.execute(
            select(HealthRecord, ProcessedData)
            .outerjoin(ProcessedData, ProcessedData.health_record_id == HealthRecord.id)
            .where(HealthRecord.user_id == user.id, HealthRecord.timestamp >= window_start)
            .order_by(HealthRecord.timestamp.desc())
            .limit(SUMMARY_READINGS_CAP)
        )
    ).all()

    # Newest value of each vital, compared with that vital's earlier values in the window.
    latest: list[LatestVital] = []
    for key in VITALS:
        series = [(record, record.vitals[key]) for record, _ in rows if record.vitals.get(key) is not None]
        if not series:
            continue
        newest_record, value = series[0]
        base = baseline_of(key, [v for _, v in reversed(series[1:])])
        latest.append(
            LatestVital(
                key=key,
                value=value,
                measured_at=newest_record.timestamp,
                position=position(key, value),
                baseline=BaselineOut(usual=round(base.usual, 2), spread=round(base.spread, 2), n=base.n) if base else None,
            )
        )

    trend_start = now - timedelta(days=TREND_WINDOW_DAYS)
    trend = [
        TrendPoint(measured_at=record.timestamp, vitals=record.vitals, flagged=bool(processed and processed.is_anomaly))
        for record, processed in reversed(rows)
        if record.timestamp >= trend_start
    ]

    readings_total = await db.scalar(select(func.count()).where(HealthRecord.user_id == user.id)) or 0
    week = await db.scalar(
        select(func.count()).where(HealthRecord.user_id == user.id, HealthRecord.timestamp >= now - timedelta(days=7))
    ) or 0
    open_flags = await db.scalar(
        select(func.count()).where(
            ProcessedData.user_id == user.id, ProcessedData.is_anomaly.is_(True), ProcessedData.resolution.is_(None)
        )
    ) or 0
    unread = await db.scalar(select(func.count()).where(Alert.user_id == user.id, Alert.is_read.is_(False))) or 0
    alerts = (
        await db.scalars(
            select(Alert)
            .where(Alert.user_id == user.id, Alert.is_read.is_(False))
            .order_by(Alert.created_at.desc())
            .limit(5)
        )
    ).all()

    next_visit_row = (
        await db.execute(
            select(ScheduledVisit, User.name)
            .join(User, User.id == ScheduledVisit.worker_id)
            .where(ScheduledVisit.citizen_id == user.id, ScheduledVisit.status == VisitStatus.scheduled)
            .order_by(ScheduledVisit.scheduled_for)
            .limit(1)
        )
    ).first()

    facility = await db.get(ValidPhcFacility, user.phc_id) if user.phc_id else None
    return SummaryOut(
        readings_total=readings_total,
        readings_last_7_days=week,
        open_flags=open_flags,
        unread_alerts=unread,
        # The cards' baseline is the earlier readings in the window, so the newest one plus 7 before it.
        readings_until_baseline=max(0, MIN_BASELINE_READINGS + 1 - len(rows)),
        baseline_window_days=BASELINE_WINDOW_DAYS,
        latest=latest,
        trend=trend,
        trend_window_days=TREND_WINDOW_DAYS,
        alerts=[alert_out(a) for a in alerts],
        next_visit=visit_for_citizen(next_visit_row[0], next_visit_row[1], now) if next_visit_row else None,
        facility=FacilitySummary(
            id=facility.id,
            name=facility.name,
            district=facility.district,
            workers_assigned=await workers_serving(db, facility.id),
        )
        if facility
        else None,
    )


@router.delete("/readings/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading(
    reading_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_onboarding_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    # Scoped to the caller: someone else's reading is simply "not found".
    record = await db.scalar(
        select(HealthRecord).where(HealthRecord.id == reading_id, HealthRecord.user_id == user.id)
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, READING_NOT_FOUND)
    if record.source == "phc":
        raise HTTPException(status.HTTP_409_CONFLICT, "A reading recorded by your health worker can only be changed by your health centre.")
    # The score goes with it; a visit booked from it keeps going (case_id is SET NULL).
    await db.execute(delete(ProcessedData).where(ProcessedData.health_record_id == record.id))
    await db.delete(record)
    db.add(
        AuditLog(
            user_id=user.id,
            action="delete_reading",
            entity="health_records",
            entity_id=record.id,
            ip_address=client_ip(request) or "unknown",
        )
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
