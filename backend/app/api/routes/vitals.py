"""A citizen's own readings: record, list, summarise, delete."""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.views import alert_out, visit_for_citizen
from app.core.dependencies import require_onboarding_user
from app.db.session import get_session
from app.models import Alert, AuditLog, HealthRecord, ProcessedData, ScheduledVisit, User, ValidPhcFacility
from app.models.enums import VisitStatus
from app.schemas.health import (
    BaselineOut,
    FacilitySummary,
    HistoryOut,
    LatestVital,
    MetricOut,
    MetricsOut,
    ReadingOut,
    SummaryOut,
    TrendPoint,
    VitalsIn,
    VitalsResult,
)
from app.services.catchment import workers_serving
from app.services.metrics import COMMON_SYMPTOMS, VITALS, position
from app.services.readings import baseline_of, record_reading
from app.services.scoring import MIN_BASELINE_READINGS
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


@router.post("/vitals", response_model=VitalsResult, status_code=status.HTTP_201_CREATED)
async def submit_vitals(
    data: VitalsIn, user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)
) -> VitalsResult:
    if not user.consent:
        raise HTTPException(status.HTTP_403_FORBIDDEN, TRACKING_OFF)
    measured_at = data.measured_at or now_utc()
    recorded = await record_reading(db, user, data.vitals, data.symptoms, measured_at)
    await db.commit()

    score = recorded.score
    if recorded.earlier_readings < MIN_BASELINE_READINGS:
        remaining = MIN_BASELINE_READINGS - recorded.earlier_readings
        note = (
            f"Compared with published normal ranges. You need {remaining} more "
            f"reading{'s' if remaining != 1 else ''} before we can learn what is normal for you."
        )
    elif score.basis == "personal_baseline":
        note = "Compared with your own usual readings."
    else:
        note = "Compared with published normal ranges."
    return VitalsResult(
        id=recorded.record.id,
        measured_at=measured_at,
        flagged=score.is_anomaly,
        anomaly_score=score.anomaly_score,
        severity=severity_of(score.anomaly_score) if score.is_anomaly else None,
        driver=top_signal(score.features) if score.is_anomaly else None,
        signal=recorded.signal,
        features=score.features,
        basis=score.basis,
        earlier_readings=recorded.earlier_readings,
        basis_note=note,
        reviewed_by_someone=recorded.reviewed_by_someone,
    )


def _reading_out(record: HealthRecord, processed: ProcessedData | None) -> ReadingOut:
    flagged = bool(processed and processed.is_anomaly)
    return ReadingOut(
        id=record.id,
        measured_at=record.timestamp,
        vitals=record.vitals,
        symptoms=record.symptoms,
        flagged=flagged,
        severity=severity_of(processed.anomaly_score) if flagged and processed else None,
        signal=describe_signal(processed.features, record.vitals) if flagged and processed else None,
        reviewed=bool(processed and processed.resolution is not None),
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
    return HistoryOut(
        items=[_reading_out(record, processed) for record, processed in rows.all()],
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
        base = baseline_of([v for _, v in series[1:]])
        latest.append(
            LatestVital(
                key=key,
                value=value,
                measured_at=newest_record.timestamp,
                position=position(key, value),
                baseline=BaselineOut(mean=round(base.mean, 2), sd=round(base.sd, 2), n=base.n) if base else None,
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
