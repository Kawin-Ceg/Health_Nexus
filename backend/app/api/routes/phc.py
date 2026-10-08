"""The PHC worker's view of their catchment.

Every query here is scoped through services/catchment.py. A citizen outside the
catchment is indistinguishable from one that does not exist (404, same body),
and a worker with no facility gets 409 rather than an empty, quiet-looking page.
Every list has a server-side LIMIT.
"""

import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import String, and_, case, cast, func, outerjoin, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.routes.schedule import check_booking_time
from app.api.views import alert_out, checks_of, person, visit_for_worker
from app.db.session import get_session
from app.models import (
    Alert,
    AuditLog,
    HealthRecord,
    ProcessedData,
    ScheduledVisit,
    User,
    UserProfile,
    ValidPhcFacility,
)
from app.models.base import utcnow
from app.models.enums import FlagResolution, VisitStatus
from app.schemas.health import BaselineOut, VisitOut
from app.schemas.phc import (
    CaseOut,
    Cleared,
    DailyVolume,
    DashboardOut,
    DirectoryItem,
    DirectoryOut,
    Engagement,
    EngagementCounts,
    FacilityOut,
    FeedItem,
    FeedOut,
    FlagBrief,
    Kpi,
    LocalityCount,
    LocalityRisk,
    LocalityRiskOut,
    LocalityVolume,
    MapOut,
    OverviewOut,
    QueueOut,
    RecordCounts,
    RecordIdentity,
    RecordOut,
    RecordVital,
    RecordWindow,
    ReportsOut,
    Resolve,
    SeverityCounts,
    TimelineEntry,
    Unresolved,
    VisitCreate,
    VisitsOut,
    WeekValue,
    WorkItem,
    WorklistOut,
)
from app.services.catchment import (
    catchment_citizens,
    catchment_ids,
    get_catchment_citizen,
    require_catchment_worker,
)
from app.services.localities import MIN_CELL, locality_of, locality_risk, suppress
from app.services.metrics import VITALS, position
from app.services.readings import baseline_of
from app.services.scoring import MIN_BASELINE_READINGS
from app.services.sessions import client_ip
from app.services.triage import BANDS, Severity, band_bounds, describe_signal, severity_of
from app.services.visit_state import LOCAL_TZ, GRACE, local_date, local_day_start, now_utc, overdue_before
from app.services.visits import notify_booked

router = APIRouter(prefix="/phc", tags=["phc"], dependencies=[Depends(require_catchment_worker)])

CASE_NOT_FOUND = "Case not found."
SILENT_AFTER = timedelta(days=14)
TIMELINE_LIMIT = 200
RECORD_READINGS_CAP = 2000
FLAGS_PER_CITIZEN = 10
TZ_NAME = LOCAL_TZ.key


def _open_flag():
    return (ProcessedData.is_anomaly.is_(True), ProcessedData.resolution.is_(None))


def _severity_sql():
    """The triage bands as a SQL CASE, built from triage.BANDS so the two cannot drift."""
    return case(*[(ProcessedData.anomaly_score >= floor, name) for name, floor in BANDS[:-1]], else_=BANDS[-1][0])


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _search(q: str):
    """Name, or a citizen reference such as HN-1A2B3C4D."""
    term = q.strip()
    ref = term.upper().removeprefix("HN-")
    if term.upper().startswith("HN-") and ref and all(c in "0123456789ABCDEF" for c in ref):
        return cast(User.id, String).ilike(f"{ref.lower()[:8]}%")
    return User.name.ilike(_like(term), escape="\\")


def _locality_filter(locality: str):
    return func.lower(func.coalesce(func.trim(User.area), "")) == locality.strip().lower()


def _local_day(column):
    return func.date(func.timezone(TZ_NAME, column))


def _facility_out(facility: ValidPhcFacility) -> FacilityOut:
    return FacilityOut(id=facility.id, name=facility.name, district=facility.district, block=facility.block)


async def _count(db: AsyncSession, query) -> int:
    return await db.scalar(select(func.count()).select_from(query.subquery())) or 0


# --- Directory building blocks -------------------------------------------------


def _directory(worker: User, now: datetime):
    """The catchment joined with each citizen's reading and open-flag aggregates, plus the engagement status."""
    members = catchment_ids(worker)
    readings = (
        select(
            HealthRecord.user_id.label("uid"),
            func.count().label("n"),
            func.max(HealthRecord.timestamp).label("last"),
        )
        .where(HealthRecord.user_id.in_(members))
        .group_by(HealthRecord.user_id)
        .subquery()
    )
    flags = (
        select(
            ProcessedData.user_id.label("uid"),
            func.count().label("n"),
            func.max(ProcessedData.anomaly_score).label("worst"),
        )
        .where(ProcessedData.user_id.in_(members), *_open_flag())
        .group_by(ProcessedData.user_id)
        .subquery()
    )
    status_expr = case(
        (func.coalesce(flags.c.n, 0) > 0, "attention"),
        (readings.c.last.is_(None), "never_logged"),
        (readings.c.last < now - SILENT_AFTER, "silent"),
        else_="ok",
    )
    source = (
        outerjoin(User, readings, readings.c.uid == User.id)
        .outerjoin(flags, flags.c.uid == User.id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
    )
    return source, User.id.in_(members), status_expr, readings, flags


async def _engagement_counts(db: AsyncSession, worker: User, now: datetime) -> EngagementCounts:
    source, members, status_expr, _, _ = _directory(worker, now)
    rows = await db.execute(select(status_expr, func.count()).select_from(source).where(members).group_by(status_expr))
    return EngagementCounts(**dict(rows.all()))


# --- Dashboard and overview ----------------------------------------------------


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(worker: User = Depends(require_catchment_worker), db: AsyncSession = Depends(get_session)) -> DashboardOut:
    now = now_utc()
    members = catchment_ids(worker)
    facility = await db.get(ValidPhcFacility, worker.phc_id)
    assert facility is not None

    severity = _severity_sql()
    by_severity = dict(
        (
            await db.execute(
                select(severity, func.count()).where(ProcessedData.user_id.in_(members), *_open_flag()).group_by(severity)
            )
        ).all()
    )
    flagged = await db.scalar(
        select(func.count(func.distinct(ProcessedData.user_id))).where(ProcessedData.user_id.in_(members), *_open_flag())
    )
    week = now - timedelta(days=7)
    readings_7d, submitting_7d = (
        await db.execute(
            select(func.count(), func.count(func.distinct(HealthRecord.user_id))).where(
                HealthRecord.user_id.in_(members), HealthRecord.timestamp >= week
            )
        )
    ).one()
    tomorrow = local_day_start(local_date(now) + timedelta(days=1))
    my_visits = select(ScheduledVisit.id).where(
        ScheduledVisit.worker_id == worker.id,
        ScheduledVisit.citizen_id.in_(members),
        ScheduledVisit.status == VisitStatus.scheduled,
    )
    return DashboardOut(
        facility=_facility_out(facility),
        citizens=await _count(db, catchment_citizens(worker)),
        citizens_flagged=flagged or 0,
        open_flags=sum(by_severity.values()),
        open_by_severity=SeverityCounts(**by_severity),
        readings_last_7_days=readings_7d,
        citizens_submitting_last_7_days=submitting_7d,
        engagement=await _engagement_counts(db, worker, now),
        silent_after_days=SILENT_AFTER.days,
        visits_needing_outcome=await _count(db, my_visits.where(ScheduledVisit.scheduled_for < overdue_before(now))),
        visits_today=await _count(
            db, my_visits.where(ScheduledVisit.scheduled_for > now, ScheduledVisit.scheduled_for < tomorrow)
        ),
    )


OVERVIEW_WEEKS = 8


@router.get("/overview", response_model=OverviewOut)
async def overview(worker: User = Depends(require_catchment_worker), db: AsyncSession = Depends(get_session)) -> OverviewOut:
    """Four KPIs, each per local calendar week (Monday start), the current week marked partial."""
    today = local_date(now_utc())
    this_monday = today - timedelta(days=today.weekday())
    weeks = [this_monday - timedelta(weeks=i) for i in range(OVERVIEW_WEEKS - 1, -1, -1)]
    start = local_day_start(weeks[0])
    members = catchment_ids(worker)

    def week_of(column):
        return func.date(func.date_trunc("week", func.timezone(TZ_NAME, column)))

    async def series(value, column, *conditions) -> dict[date, int]:
        bucket = week_of(column)
        rows = await db.execute(select(bucket, value).where(column >= start, *conditions).group_by(bucket))
        return {day: n for day, n in rows.all()}

    in_catchment_reading = HealthRecord.user_id.in_(members)
    in_catchment_flag = ProcessedData.user_id.in_(members)
    data = {
        ("readings", "Readings submitted"): await series(func.count(), HealthRecord.timestamp, in_catchment_reading),
        ("active_citizens", "Citizens who submitted"): await series(
            func.count(func.distinct(HealthRecord.user_id)), HealthRecord.timestamp, in_catchment_reading
        ),
        ("flags_raised", "Flags raised"): await series(
            func.count(), ProcessedData.processed_at, in_catchment_flag, ProcessedData.is_anomaly.is_(True)
        ),
        ("flags_cleared", "Flags cleared"): await series(
            func.count(), ProcessedData.reviewed_at, in_catchment_flag, ProcessedData.reviewed_at.is_not(None)
        ),
    }
    return OverviewOut(
        kpis=[
            Kpi(
                key=key,
                label=label,
                weeks=[WeekValue(week_start=w, value=values.get(w, 0), partial=w == this_monday) for w in weeks],
            )
            for (key, label), values in data.items()
        ],
        week_starts_on="monday",
        timezone=TZ_NAME,
    )


# --- The queue: one row per open flag -----------------------------------------


def _case_out(processed: ProcessedData, record: HealthRecord, citizen: User) -> CaseOut:
    return CaseOut(
        processed_id=processed.id,
        citizen=person(citizen),
        severity=severity_of(processed.anomaly_score),
        anomaly_score=processed.anomaly_score,
        signal=describe_signal(processed.features, record.vitals),
        features=processed.features,
        vitals=record.vitals,
        symptoms=record.symptoms,
        measured_at=record.timestamp,
        basis=processed.basis,
    )


@router.get("/queue", response_model=QueueOut)
async def queue(
    severity: Severity | None = None,
    locality: str | None = Query(None, max_length=120),
    q: str | None = Query(None, max_length=80),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=100_000),
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> QueueOut:
    query = (
        select(ProcessedData, HealthRecord, User)
        .join(HealthRecord, HealthRecord.id == ProcessedData.health_record_id)
        .join(User, User.id == ProcessedData.user_id)
        .where(ProcessedData.user_id.in_(catchment_ids(worker)), *_open_flag())
    )
    if severity:
        low, high = band_bounds(severity)
        query = query.where(ProcessedData.anomaly_score >= low)
        if high is not None:
            query = query.where(ProcessedData.anomaly_score < high)
    if locality:
        query = query.where(_locality_filter(locality))
    if q and q.strip():
        query = query.where(_search(q))
    total = await _count(db, query)
    rows = await db.execute(
        query.order_by(ProcessedData.anomaly_score.desc(), HealthRecord.timestamp.desc()).offset(offset).limit(limit)
    )
    return QueueOut(items=[_case_out(*row) for row in rows.all()], total=total, limit=limit, offset=offset)


def _apply(processed_query, worker: User, data: Resolve):
    return processed_query.values(
        reviewed_at=utcnow(),
        reviewed_by=worker.id,
        resolution=data.resolution,
        dismiss_reason=data.dismiss_reason,
        resolution_note=data.note,
    )


@router.post("/queue/{processed_id}/seen", response_model=Cleared)
async def mark_seen(
    processed_id: uuid.UUID,
    data: Resolve | None = None,
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> Cleared:
    data = data or Resolve()
    processed = await db.scalar(
        select(ProcessedData)
        .where(
            ProcessedData.id == processed_id,
            ProcessedData.is_anomaly.is_(True),
            ProcessedData.user_id.in_(catchment_ids(worker)),
        )
        .with_for_update()
    )
    if processed is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, CASE_NOT_FOUND)
    if processed.resolution is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This case has already been cleared.")
    await db.execute(_apply(update(ProcessedData).where(ProcessedData.id == processed.id), worker, data))
    await db.commit()
    return Cleared(cleared=1)


# --- The worklist: open flags grouped by citizen --------------------------------


@router.get("/worklist", response_model=WorklistOut)
async def worklist(
    locality: str | None = Query(None, max_length=120),
    q: str | None = Query(None, max_length=80),
    limit: int = Query(50, ge=1, le=100),
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> WorklistOut:
    now = now_utc()
    grouped = (
        select(
            ProcessedData.user_id,
            func.count().label("n"),
            func.max(ProcessedData.anomaly_score).label("worst"),
            func.min(ProcessedData.processed_at).label("first"),
            func.max(ProcessedData.processed_at).label("last"),
        )
        .join(User, User.id == ProcessedData.user_id)
        .where(ProcessedData.user_id.in_(catchment_ids(worker)), *_open_flag())
        .group_by(ProcessedData.user_id)
    )
    if locality:
        grouped = grouped.where(_locality_filter(locality))
    if q and q.strip():
        grouped = grouped.where(_search(q))
    total = await _count(db, grouped)
    groups = (
        await db.execute(grouped.order_by(func.max(ProcessedData.anomaly_score).desc(), func.max(ProcessedData.processed_at).desc()).limit(limit))
    ).all()
    ids = [g.user_id for g in groups]
    if not ids:
        return WorklistOut(items=[], total_citizens=total, limit=limit)

    citizens = {c.id: c for c in (await db.scalars(select(User).where(User.id.in_(ids)))).all()}
    flags: dict[uuid.UUID, list[tuple[ProcessedData, HealthRecord]]] = {i: [] for i in ids}
    rows = await db.execute(
        select(ProcessedData, HealthRecord)
        .join(HealthRecord, HealthRecord.id == ProcessedData.health_record_id)
        .where(ProcessedData.user_id.in_(ids), *_open_flag())
        .order_by(ProcessedData.anomaly_score.desc(), HealthRecord.timestamp.desc())
        .limit(len(ids) * FLAGS_PER_CITIZEN * 3)
    )
    for processed, record in rows.all():
        bucket = flags[processed.user_id]
        if len(bucket) < FLAGS_PER_CITIZEN:
            bucket.append((processed, record))

    visit_rows = await db.execute(
        select(ScheduledVisit)
        .where(
            ScheduledVisit.citizen_id.in_(ids),
            ScheduledVisit.worker_id == worker.id,
            ScheduledVisit.status == VisitStatus.scheduled,
        )
        .order_by(ScheduledVisit.scheduled_for)
    )
    next_visit: dict[uuid.UUID, ScheduledVisit] = {}
    for visit in visit_rows.scalars():
        next_visit.setdefault(visit.citizen_id, visit)

    items = []
    for g in groups:
        citizen = citizens[g.user_id]
        top = flags[g.user_id]
        worst = top[0] if top else None
        items.append(
            WorkItem(
                citizen=person(citizen),
                open_flags=g.n,
                worst_severity=severity_of(g.worst),
                worst_signal=describe_signal(worst[0].features, worst[1].vitals) if worst else None,
                first_flagged_at=g.first,
                last_flagged_at=g.last,
                flags=[
                    FlagBrief(
                        processed_id=p.id,
                        severity=severity_of(p.anomaly_score),
                        signal=describe_signal(p.features, r.vitals),
                        symptoms=r.symptoms,
                        measured_at=r.timestamp,
                        basis=p.basis,
                    )
                    for p, r in top
                ],
                flags_shown=len(top),
                next_visit=visit_for_worker(next_visit[g.user_id], citizen, now) if g.user_id in next_visit else None,
            )
        )
    return WorklistOut(items=items, total_citizens=total, limit=limit)


@router.post("/worklist/citizens/{user_id}/resolve", response_model=Cleared)
async def resolve_citizen(
    user_id: uuid.UUID,
    data: Resolve | None = None,
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> Cleared:
    citizen = await get_catchment_citizen(db, worker, user_id)
    result = await db.execute(
        _apply(update(ProcessedData).where(ProcessedData.user_id == citizen.id, *_open_flag()), worker, data or Resolve())
    )
    await db.commit()
    return Cleared(cleared=result.rowcount or 0)


# --- Directory and record ------------------------------------------------------


@router.get("/citizens", response_model=DirectoryOut)
async def citizens(
    q: str | None = Query(None, max_length=80),
    locality: str | None = Query(None, max_length=120),
    status_: Engagement | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100_000),
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> DirectoryOut:
    now = now_utc()
    source, members, status_expr, readings, flags = _directory(worker, now)
    query = select(
        User,
        status_expr.label("status"),
        func.coalesce(readings.c.n, 0),
        readings.c.last,
        func.coalesce(flags.c.n, 0),
        flags.c.worst,
        UserProfile.age,
        UserProfile.gender,
    ).select_from(source).where(members)
    if q and q.strip():
        query = query.where(_search(q))
    if locality:
        query = query.where(_locality_filter(locality))
    if status_:
        query = query.where(status_expr == status_)
    total = await _count(db, query)

    # What is worth opening first: open flags (worst first), never logged, then longest silent.
    rank = case((status_expr == "attention", 0), (status_expr == "never_logged", 1), (status_expr == "silent", 2), else_=3)
    rows = await db.execute(
        query.order_by(
            rank, flags.c.worst.desc().nulls_last(), readings.c.last.asc().nulls_first(), User.created_at, User.name
        )
        .offset(offset)
        .limit(limit)
    )
    items = [
        DirectoryItem(
            citizen=person(citizen),
            age=age,
            gender=gender,
            status=state,
            open_flags=open_n,
            worst_severity=severity_of(worst) if worst is not None else None,
            readings=n,
            last_reading_at=last,
            joined_at=citizen.created_at,
        )
        for citizen, state, n, last, open_n, worst, age, gender in rows.all()
    ]
    localities: dict[str, int] = {}
    for area, n in (await db.execute(select(User.area, func.count()).where(members).group_by(User.area))).all():
        name = locality_of(area)
        localities[name] = localities.get(name, 0) + n
    counts = await _engagement_counts(db, worker, now)
    return DirectoryOut(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        counts=counts,
        catchment_total=counts.attention + counts.never_logged + counts.silent + counts.ok,
        localities=[LocalityCount(locality=k, citizens=v) for k, v in sorted(localities.items())],
        silent_after_days=SILENT_AFTER.days,
    )


def _entry(record: HealthRecord, processed: ProcessedData | None) -> TimelineEntry:
    flagged = bool(processed and processed.is_anomaly)
    return TimelineEntry(
        reading_id=record.id,
        processed_id=processed.id if processed else None,
        measured_at=record.timestamp,
        vitals=record.vitals,
        symptoms=record.symptoms,
        flagged=flagged,
        severity=severity_of(processed.anomaly_score) if flagged and processed else None,
        signal=describe_signal(processed.features, record.vitals) if flagged and processed else None,
        resolution=processed.resolution if processed else None,
        reviewed_at=processed.reviewed_at if processed else None,
        basis=processed.basis if processed else None,
        checks=checks_of(processed),
    )


@router.get("/citizens/{user_id}/record", response_model=RecordOut)
async def citizen_record(
    user_id: uuid.UUID,
    request: Request,
    days: int = Query(90, ge=7, le=365),
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> RecordOut:
    citizen = await get_catchment_citizen(db, worker, user_id)
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == citizen.id))
    end = now_utc()
    start = end - timedelta(days=days)
    in_window = and_(HealthRecord.timestamp >= start, HealthRecord.timestamp <= end)

    readings_query = (
        select(HealthRecord, ProcessedData)
        .outerjoin(ProcessedData, ProcessedData.health_record_id == HealthRecord.id)
        .where(HealthRecord.user_id == citizen.id, in_window)
    )
    total_readings = await _count(db, readings_query)
    rows = (
        await db.execute(readings_query.order_by(HealthRecord.timestamp.desc()).limit(RECORD_READINGS_CAP))
    ).all()

    vitals: list[RecordVital] = []
    for key in VITALS:
        series = [(r.timestamp, r.vitals[key]) for r, _ in rows if r.vitals.get(key) is not None]
        if not series:
            continue
        latest_at, latest = series[0]
        base = baseline_of(key, [v for _, v in reversed(series[1:])])
        vitals.append(
            RecordVital(
                key=key,
                latest=latest,
                latest_at=latest_at,
                position=position(key, latest),
                readings=len(series),
                baseline=BaselineOut(usual=round(base.usual, 2), spread=round(base.spread, 2), n=base.n) if base else None,
                z_score=round((latest - base.usual) / base.spread, 2) if base else None,
            )
        )

    flags_in_window = sum(1 for _, p in rows if p and p.is_anomaly)
    open_in_window = sum(1 for _, p in rows if p and p.is_anomaly and p.resolution is None)

    alert_query = select(Alert).where(Alert.user_id == citizen.id, Alert.created_at >= start, Alert.created_at <= end)
    alerts = (await db.scalars(alert_query.order_by(Alert.created_at.desc()).limit(50))).all()

    worker_name = aliased(User)
    visit_query = (
        select(ScheduledVisit, worker_name.name)
        .join(worker_name, worker_name.id == ScheduledVisit.worker_id)
        .where(ScheduledVisit.citizen_id == citizen.id)
    )
    past_visits = (
        await db.execute(
            visit_query.where(ScheduledVisit.scheduled_for >= start, ScheduledVisit.scheduled_for <= end)
            .order_by(ScheduledVisit.scheduled_for.desc())
            .limit(50)
        )
    ).all()
    upcoming = (
        await db.execute(
            visit_query.where(ScheduledVisit.scheduled_for > end, ScheduledVisit.status == VisitStatus.scheduled)
            .order_by(ScheduledVisit.scheduled_for)
            .limit(20)
        )
    ).all()

    # Unresolved from before the window: reported beside it, never mixed into it.
    before_open, oldest = (
        await db.execute(
            select(func.count(), func.min(HealthRecord.timestamp))
            .select_from(ProcessedData)
            .join(HealthRecord, HealthRecord.id == ProcessedData.health_record_id)
            .where(ProcessedData.user_id == citizen.id, HealthRecord.timestamp < start, *_open_flag())
        )
    ).one()
    stale_visits = await _count(
        db,
        select(ScheduledVisit.id).where(
            ScheduledVisit.citizen_id == citizen.id,
            ScheduledVisit.status == VisitStatus.scheduled,
            ScheduledVisit.scheduled_for < start,
        ),
    )

    db.add(
        AuditLog(
            user_id=worker.id,
            action="view_citizen_record",
            entity="users",
            entity_id=citizen.id,
            ip_address=client_ip(request) or "unknown",
        )
    )
    await db.commit()

    def as_worker_view(visit: ScheduledVisit, name: str) -> VisitOut:
        out = visit_for_worker(visit, citizen, end)
        out.worker_name = name
        return out

    return RecordOut(
        identity=RecordIdentity(
            id=citizen.id,
            ref=person(citizen).ref,
            name=citizen.name,
            phone=citizen.phone,
            email=citizen.email,
            area=citizen.area,
            pincode=citizen.pincode,
            age=profile.age if profile else None,
            gender=profile.gender if profile else None,
            blood_group=profile.blood_group.value if profile and profile.blood_group else None,
            existing_conditions=profile.existing_conditions if profile else [],
            current_medications=profile.current_medications if profile else [],
            emergency_contact_name=profile.emergency_contact_name if profile else None,
            emergency_contact_phone=profile.emergency_contact_phone if profile else None,
            joined_at=citizen.created_at,
        ),
        window=RecordWindow(start=start, end=end, days=days),
        counts=RecordCounts(
            readings=total_readings,
            flags=flags_in_window,
            open_flags=open_in_window,
            alerts=await _count(db, alert_query),
            visits=len(past_visits),
        ),
        vitals=vitals,
        timeline=[_entry(r, p) for r, p in rows[:TIMELINE_LIMIT]],
        timeline_truncated=total_readings > TIMELINE_LIMIT,
        timeline_limit=TIMELINE_LIMIT,
        alerts=[alert_out(a) for a in alerts],
        visits=[as_worker_view(v, n) for v, n in past_visits],
        upcoming_visits=[as_worker_view(v, n) for v, n in upcoming],
        unresolved_before_window=Unresolved(
            open_flags=before_open, oldest_flag_at=oldest, visits_without_outcome=stale_visits
        ),
        min_baseline_readings=MIN_BASELINE_READINGS,
    )


# --- Feed, reports, map --------------------------------------------------------


@router.get("/alerts", response_model=FeedOut)
async def flag_feed(
    days: int = Query(14, ge=1, le=90),
    limit: int = Query(100, ge=1, le=200),
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> FeedOut:
    """Flags raised in the last `days`, newest first, open and cleared."""
    reviewer = aliased(User)
    rows = await db.execute(
        select(ProcessedData, HealthRecord, User, reviewer.name)
        .join(HealthRecord, HealthRecord.id == ProcessedData.health_record_id)
        .join(User, User.id == ProcessedData.user_id)
        .outerjoin(reviewer, reviewer.id == ProcessedData.reviewed_by)
        .where(
            ProcessedData.user_id.in_(catchment_ids(worker)),
            ProcessedData.is_anomaly.is_(True),
            HealthRecord.timestamp >= now_utc() - timedelta(days=days),
        )
        .order_by(HealthRecord.timestamp.desc())
        .limit(limit)
    )
    return FeedOut(
        items=[
            FeedItem(
                processed_id=p.id,
                citizen=person(c),
                severity=severity_of(p.anomaly_score),
                signal=describe_signal(p.features, r.vitals),
                measured_at=r.timestamp,
                status=p.resolution.value if p.resolution else "open",
                reviewed_by=reviewer_name,
                reviewed_at=p.reviewed_at,
            )
            for p, r, c, reviewer_name in rows.all()
        ],
        days=days,
        limit=limit,
    )


@router.get("/reports", response_model=ReportsOut)
async def reports(
    days: int = Query(30, ge=7, le=180),
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> ReportsOut:
    """Whole local days: 'last 30 days' is today and the 29 before it."""
    now = now_utc()
    first_day = local_date(now) - timedelta(days=days - 1)
    start = local_day_start(first_day)
    members = catchment_ids(worker)
    flagged = func.count().filter(ProcessedData.is_anomaly.is_(True))
    window_readings = (
        select(HealthRecord.user_id)
        .outerjoin(ProcessedData, ProcessedData.health_record_id == HealthRecord.id)
        .where(HealthRecord.user_id.in_(members), HealthRecord.timestamp >= start, HealthRecord.timestamp <= now)
    )

    day = _local_day(HealthRecord.timestamp)
    per_day = {
        d: (n, f)
        for d, n, f in (
            await db.execute(window_readings.with_only_columns(day, func.count(), flagged).group_by(day))
        ).all()
    }
    daily = [
        DailyVolume(date=d, readings=per_day.get(d, (0, 0))[0], flags=per_day.get(d, (0, 0))[1])
        for d in (first_day + timedelta(days=i) for i in range(days))
    ]

    readings, submitting, flags = (
        await db.execute(
            window_readings.with_only_columns(func.count(), func.count(func.distinct(HealthRecord.user_id)), flagged)
        )
    ).one()

    by_area: dict[str, dict[str, float]] = {}
    for area, n in (await db.execute(select(User.area, func.count()).where(User.id.in_(members)).group_by(User.area))).all():
        bucket = by_area.setdefault(locality_of(area), {"citizens": 0, "submitting": 0, "readings": 0, "flags": 0})
        bucket["citizens"] += n
    area_rows = await db.execute(
        window_readings.join(User, User.id == HealthRecord.user_id)
        .with_only_columns(User.area, func.count(func.distinct(HealthRecord.user_id)), func.count(), flagged)
        .group_by(User.area)
    )
    for area, s, n, f in area_rows.all():
        bucket = by_area[locality_of(area)]
        bucket["submitting"] += s
        bucket["readings"] += n
        bucket["flags"] += f

    localities = [
        LocalityVolume(locality=name, **{k: int(v) for k, v in values.items()})
        for name, values in sorted(suppress(by_area).items(), key=lambda kv: -kv[1]["readings"])
    ]
    return ReportsOut(
        window=RecordWindow(start=start, end=now, days=days),
        readings=readings,
        citizens_submitting=submitting,
        flags=flags,
        flag_rate=round(flags / readings, 3) if readings else None,
        catchment_now=await _count(db, catchment_citizens(worker)),
        daily=daily,
        localities=localities,
        min_cell=MIN_CELL,
    )


@router.get("/locality-risk", response_model=LocalityRiskOut)
async def locality_risk_ranked(
    worker: User = Depends(require_catchment_worker), db: AsyncSession = Depends(get_session)
) -> LocalityRiskOut:
    return LocalityRiskOut(items=[LocalityRisk(**i) for i in await locality_risk(db, worker)], min_cell=MIN_CELL)


@router.get("/map", response_model=MapOut)
async def risk_map(worker: User = Depends(require_catchment_worker), db: AsyncSession = Depends(get_session)) -> MapOut:
    facility = await db.get(ValidPhcFacility, worker.phc_id)
    assert facility is not None
    return MapOut(
        facility=_facility_out(facility),
        facility_lat=facility.latitude,
        facility_lng=facility.longitude,
        items=[LocalityRisk(**i) for i in await locality_risk(db, worker)],
        min_cell=MIN_CELL,
    )


# --- Visits --------------------------------------------------------------------


@router.post("/visits", response_model=VisitOut, status_code=status.HTTP_201_CREATED)
async def book_visit(
    data: VisitCreate, worker: User = Depends(require_catchment_worker), db: AsyncSession = Depends(get_session)
) -> VisitOut:
    citizen = await get_catchment_citizen(db, worker, data.citizen_id)
    check_booking_time(data.scheduled_for)

    case_row = None
    if data.case_id is not None:
        case_row = await db.scalar(
            select(ProcessedData)
            .where(ProcessedData.id == data.case_id, ProcessedData.user_id == citizen.id)
            .with_for_update()
        )
        if case_row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, CASE_NOT_FOUND)

    existing = await db.scalar(
        select(ScheduledVisit).where(
            ScheduledVisit.citizen_id == citizen.id,
            ScheduledVisit.status == VisitStatus.scheduled,
            ScheduledVisit.scheduled_for > now_utc() - GRACE,
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This citizen already has a visit booked. Move that visit instead of booking a second one.",
        )

    visit = ScheduledVisit(
        worker_id=worker.id,
        citizen_id=citizen.id,
        case_id=case_row.id if case_row else None,
        scheduled_for=data.scheduled_for,
        reason=data.reason or None,
        location=data.location or citizen.area,
    )
    db.add(visit)
    # Booking a follow-up is a review: the case leaves the queue.
    if case_row is not None and case_row.resolution is None:
        case_row.resolution = FlagResolution.reviewed
        case_row.reviewed_at = utcnow()
        case_row.reviewed_by = worker.id
        case_row.resolution_note = "Follow-up visit booked."
    await db.flush()
    notify_booked(db, visit, citizen, worker)
    await db.commit()
    return visit_for_worker(visit, citizen, now_utc())


@router.get("/visits", response_model=VisitsOut)
async def upcoming_visits(
    limit: int = Query(50, ge=1, le=100),
    worker: User = Depends(require_catchment_worker),
    db: AsyncSession = Depends(get_session),
) -> VisitsOut:
    """Visits that have not yet passed the grace window: due now, later today, or later."""
    now = now_utc()
    rows = await db.execute(
        select(ScheduledVisit, User)
        .join(User, User.id == ScheduledVisit.citizen_id)
        .where(
            ScheduledVisit.worker_id == worker.id,
            ScheduledVisit.citizen_id.in_(catchment_ids(worker)),
            ScheduledVisit.status == VisitStatus.scheduled,
            ScheduledVisit.scheduled_for >= overdue_before(now),
        )
        .order_by(ScheduledVisit.scheduled_for)
        .limit(limit)
    )
    return VisitsOut(items=[visit_for_worker(v, c, now) for v, c in rows.all()], limit=limit)

