"""The admin console: PHC worker approvals, accounts, support concerns, the audit trail and the research export.

Every route needs an admin. Decisions on PHC applications are written to
phc_verification_audit_log; account changes go to audit_logs. An admin can never
act on their own account or on another admin from here.
"""

import csv
import hashlib
import io
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import and_, delete, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.dependencies import require_admin
from app.db.session import get_session
from app.models import (
    Advisory,
    Alert,
    AuditLog,
    ChatMessage,
    ChatSession,
    Concern,
    HealthRecord,
    PhcApplication,
    PhcVerificationAuditLog,
    ProcessedData,
    ScheduledVisit,
    User,
    UserProfile,
    ValidPhcFacility,
)
from app.models.base import utcnow
from app.models.enums import (
    AlertSeverity,
    AlertType,
    ApplicationStatus,
    ChatMessageRole,
    ConcernCategory,
    ConcernStatus,
    Designation,
    PhcVerificationAction,
    UserRole,
    VisitStatus,
)
from app.services import sessions

from .applications import DocumentOut, documents_of
from app.services.consent import in_research
from app.services.localities import MIN_CELL
from app.services.metrics import VITALS
from app.services.phc_registry import match_facility, normalise_facility_name
from app.services.visits import notify_changed

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

APPLICATION_NOT_FOUND = "Application not found."
USER_NOT_FOUND = "Account not found."
CONCERN_NOT_FOUND = "Concern not found."
FACILITY_NOT_FOUND = "That health centre is not in the registry, or is inactive."

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


def _ip(request: Request) -> str:
    return sessions.client_ip(request) or "unknown"


# --- Overview -------------------------------------------------------------------


class Overview(BaseModel):
    users_by_role: dict[str, int]
    inactive_accounts: int
    unverified_accounts: int
    pending_applications: int
    workers_without_facility: int
    open_concerns: int
    readings_last_7_days: int
    open_flags: int
    facilities_active: int
    assistant_questions_last_7_days: int
    area: str | None = None
    pending_today: int = 0
    pending_over_3_days: int = 0
    flags_daily: list[int] = []
    top_flag_centres: list[dict] = []
    oldest_applications: list[dict] = []
    open_concern_list: list[dict] = []
    oldest_pending_at: datetime | None = None
    concerns_in_review: int = 0
    open_flags_high: int = 0
    centres_without_workers: int = 0
    citizen_activity: dict[str, list[int]] = {}
    worker_activity: dict[str, list[int]] = {}


def area_of(admin: User) -> str | None:
    """A district admin sees their district only; an admin with no district sees the whole state."""
    return admin.district.strip() if admin.district else None


def in_area(column, area: str | None):
    return func.lower(column) == area.lower() if area else true()


@router.get("/overview", response_model=Overview)
async def overview(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_session)) -> Overview:
    area = area_of(admin)
    now = utcnow()
    week_ago = now - timedelta(days=7)
    people = select(User.id).where(in_area(User.district, area))
    centres = select(ValidPhcFacility.id).where(in_area(ValidPhcFacility.district, area))
    pending = (PhcApplication.status == ApplicationStatus.pending, in_area(PhcApplication.district, area))
    open_flag = (ProcessedData.is_anomaly.is_(True), ProcessedData.resolution.is_(None), ProcessedData.user_id.in_(people))
    by_role = dict(
        (await db.execute(select(User.role, func.count()).where(in_area(User.district, area)).group_by(User.role))).all()
    )

    async def count(query) -> int:
        return await db.scalar(query) or 0

    return Overview(
        area=area,
        users_by_role={r.value: by_role.get(r, 0) for r in UserRole},
        inactive_accounts=await count(select(func.count()).where(User.is_active.is_(False), in_area(User.district, area))),
        unverified_accounts=await count(select(func.count()).where(User.is_verified.is_(False), in_area(User.district, area))),
        pending_applications=await count(select(func.count()).where(*pending)),
        pending_today=await count(select(func.count()).where(*pending, PhcApplication.created_at >= now - timedelta(days=1))),
        pending_over_3_days=await count(select(func.count()).where(*pending, PhcApplication.created_at < now - timedelta(days=3))),
        workers_without_facility=await count(
            select(func.count()).where(User.role == UserRole.phc_worker, User.phc_id.is_(None), in_area(User.district, area))
        ),
        open_concerns=await count(
            select(func.count()).where(Concern.status.in_([ConcernStatus.open, ConcernStatus.in_review]), Concern.user_id.in_(people))
        ),
        concerns_in_review=await count(
            select(func.count()).where(Concern.status == ConcernStatus.in_review, Concern.user_id.in_(people))
        ),
        readings_last_7_days=await count(
            select(func.count()).where(HealthRecord.created_at >= week_ago, HealthRecord.user_id.in_(people))
        ),
        open_flags=await count(select(func.count()).where(*open_flag)),
        open_flags_high=await count(select(func.count()).where(*open_flag, ProcessedData.anomaly_score >= 0.5)),
        facilities_active=await count(
            select(func.count()).where(ValidPhcFacility.is_active.is_(True), in_area(ValidPhcFacility.district, area))
        ),
        centres_without_workers=await count(
            select(func.count()).select_from(ValidPhcFacility).where(
                ValidPhcFacility.is_active.is_(True),
                in_area(ValidPhcFacility.district, area),
                ~ValidPhcFacility.id.in_(select(User.phc_id).where(User.role == UserRole.phc_worker, User.phc_id.is_not(None))),
            )
        ),
        assistant_questions_last_7_days=await count(
            select(func.count()).where(
                ChatMessage.role == ChatMessageRole.user, ChatMessage.created_at >= week_ago, ChatMessage.user_id.in_(people)
            )
        ),
        oldest_pending_at=await db.scalar(select(func.min(PhcApplication.created_at)).where(*pending)),
        flags_daily=[
            await count(
                select(func.count()).where(
                    ProcessedData.is_anomaly.is_(True), ProcessedData.user_id.in_(people),
                    ProcessedData.processed_at >= now - timedelta(days=d + 1), ProcessedData.processed_at < now - timedelta(days=d),
                )
            )
            for d in range(6, -1, -1)
        ],
        top_flag_centres=[
            {"name": name, "count": n}
            for name, n in (
                await db.execute(
                    select(ValidPhcFacility.name, func.count())
                    .select_from(ProcessedData)
                    .join(User, User.id == ProcessedData.user_id)
                    .join(ValidPhcFacility, ValidPhcFacility.id == User.phc_id)
                    .where(*open_flag)
                    .group_by(ValidPhcFacility.name)
                    .order_by(func.count().desc())
                    .limit(3)
                )
            ).all()
        ],
        oldest_applications=[
            {"id": str(a.id), "name": u.name, "centre": a.phc_name, "created_at": a.created_at.isoformat()}
            for a, u in (
                await db.execute(
                    select(PhcApplication, User).join(User, User.id == PhcApplication.user_id)
                    .where(*pending).order_by(PhcApplication.created_at).limit(3)
                )
            ).all()
        ],
        open_concern_list=[
            {"id": str(c.id), "ref": c.ticket_ref, "category": c.category.value, "subject": c.description[:90],
             "status": c.status.value, "created_at": c.created_at.isoformat()}
            for c in (
                await db.scalars(
                    select(Concern).where(Concern.status.in_([ConcernStatus.open, ConcernStatus.in_review]), Concern.user_id.in_(people))
                    .order_by(Concern.created_at).limit(3)
                )
            ).all()
        ],
        citizen_activity=await _weekly(db, {
            "Watch readings": (
                select(func.count()).select_from(HealthRecord).where(HealthRecord.source == "watch", HealthRecord.user_id.in_(people)),
                HealthRecord.created_at,
            ),
            "Anomalies flagged": (
                select(func.count()).select_from(ProcessedData).where(ProcessedData.is_anomaly.is_(True), ProcessedData.user_id.in_(people)),
                ProcessedData.processed_at,
            ),
            "Assistant questions": (
                select(func.count()).select_from(ChatMessage).join(User, User.id == ChatMessage.user_id)
                .where(ChatMessage.role == ChatMessageRole.user, User.role == UserRole.user, in_area(User.district, area)),
                ChatMessage.created_at,
            ),
            "New citizens": (
                select(func.count()).select_from(User).where(User.role == UserRole.user, in_area(User.district, area)),
                User.created_at,
            ),
        }),
        worker_activity=await _weekly(db, {
            "Examinations recorded": (
                select(func.count()).select_from(HealthRecord).where(HealthRecord.source == "phc", HealthRecord.user_id.in_(people)),
                HealthRecord.created_at,
            ),
            "Flags reviewed": (
                select(func.count()).select_from(ProcessedData).where(ProcessedData.reviewed_at.is_not(None), ProcessedData.user_id.in_(people)),
                ProcessedData.reviewed_at,
            ),
            "Visits booked": (
                select(func.count()).select_from(ScheduledVisit).where(ScheduledVisit.citizen_id.in_(people)),
                ScheduledVisit.created_at,
            ),
            "Advisories published": (
                select(func.count()).select_from(Advisory).where(
                    (Advisory.phc_id.in_(centres)) | in_area(Advisory.district, area)
                ),
                Advisory.created_at,
            ),
        }),
    )


WEEKS = 8


async def _weekly(db: AsyncSession, series: dict) -> dict[str, list[int]]:
    """Per series, counts for each of the last WEEKS weeks, oldest first."""
    now = utcnow()
    out: dict[str, list[int]] = {}
    for name, (query, column) in series.items():
        values = []
        for w in range(WEEKS, 0, -1):
            start, end = now - timedelta(days=7 * w), now - timedelta(days=7 * (w - 1))
            values.append(await db.scalar(query.where(column >= start, column < end)) or 0)
        out[name] = values
    return out


class PeriodTotals(BaseModel):
    scheduled: int
    done: int
    missed: int
    examinations: int
    advisories: int
    has_data: bool


class VisitWeek(BaseModel):
    start: datetime
    end: datetime
    scheduled: int
    done: int
    missed: int


class CentreActivity(BaseModel):
    facility_id: uuid.UUID
    name: str
    district: str
    workers: int
    citizens: int
    citizens_monitored: int
    flags_open: int
    flags_critical: int
    upcoming_visits: int
    range_start: datetime
    range_end: datetime
    current: PeriodTotals
    previous: PeriodTotals
    weeks: list[VisitWeek]


@router.get("/centre-activity", response_model=CentreActivity)
async def centre_activity(
    facility_id: uuid.UUID,
    days: int = Query(30, ge=7, le=365),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> CentreActivity:
    """Visits, examinations and advisories for one centre over `days`, against the `days` before."""
    facility = await db.get(ValidPhcFacility, facility_id)
    area = area_of(admin)
    if facility is None or (area and facility.district.lower() != area.lower()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, FACILITY_NOT_FOUND)
    now = utcnow()
    since = now - timedelta(days=days)
    citizens = select(User.id).where(User.phc_id == facility.id, User.role == UserRole.user)
    workers = select(User.id).where(User.phc_id == facility.id, User.role == UserRole.phc_worker)

    async def count(query) -> int:
        return await db.scalar(query) or 0

    def visits(start, end, *where):
        return select(func.count()).select_from(ScheduledVisit).where(
            ScheduledVisit.worker_id.in_(workers),
            ScheduledVisit.scheduled_for >= start,
            ScheduledVisit.scheduled_for < end,
            ScheduledVisit.status != VisitStatus.cancelled,
            *where,
        )

    async def totals(start, end) -> PeriodTotals:
        scheduled = await count(visits(start, end))
        done = await count(visits(start, end, ScheduledVisit.status == VisitStatus.completed))
        missed = await count(visits(start, end, ScheduledVisit.status == VisitStatus.missed))
        exams = await count(
            select(func.count()).select_from(HealthRecord).where(
                HealthRecord.recorded_by.in_(workers), HealthRecord.created_at >= start, HealthRecord.created_at < end
            )
        )
        advisories = await count(
            select(func.count()).select_from(Advisory).where(
                Advisory.phc_id == facility.id, Advisory.created_at >= start, Advisory.created_at < end
            )
        )
        return PeriodTotals(scheduled=scheduled, done=done, missed=missed, examinations=exams, advisories=advisories,
                            has_data=bool(scheduled or exams or advisories))

    weeks = []
    cursor = since
    while cursor < now:
        stop = min(cursor + timedelta(days=7), now)
        weeks.append(VisitWeek(
            start=cursor, end=stop,
            scheduled=await count(visits(cursor, stop)),
            done=await count(visits(cursor, stop, ScheduledVisit.status == VisitStatus.completed)),
            missed=await count(visits(cursor, stop, ScheduledVisit.status == VisitStatus.missed)),
        ))
        cursor = stop

    open_flags = (ProcessedData.user_id.in_(citizens), ProcessedData.is_anomaly.is_(True), ProcessedData.resolution.is_(None))
    return CentreActivity(
        facility_id=facility.id,
        name=facility.name,
        district=facility.district,
        workers=await count(select(func.count()).select_from(workers.subquery())),
        citizens=await count(select(func.count()).select_from(citizens.subquery())),
        citizens_monitored=await count(
            select(func.count(func.distinct(HealthRecord.user_id))).where(HealthRecord.user_id.in_(citizens), HealthRecord.timestamp >= since)
        ),
        flags_open=await count(select(func.count()).where(*open_flags)),
        flags_critical=await count(select(func.count()).where(*open_flags, ProcessedData.anomaly_score >= 0.75)),
        upcoming_visits=await count(visits(now, now + timedelta(days=365), ScheduledVisit.status == VisitStatus.scheduled)),
        range_start=since,
        range_end=now,
        current=await totals(since, now),
        previous=await totals(since - timedelta(days=days), since),
        weeks=weeks,
    )


# --- Health centre registry -------------------------------------------------------


class FacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    facility_code: str
    name: str
    district: str
    state: str
    block: str | None
    is_active: bool


@router.get("/facilities", response_model=list[FacilityOut])
async def facilities(
    q: str | None = Query(None, max_length=120),
    district: str | None = Query(None, max_length=120),
    state: str | None = Query(None, max_length=120),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
) -> list[ValidPhcFacility]:
    query = select(ValidPhcFacility).where(ValidPhcFacility.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            or_(
                ValidPhcFacility.name.ilike(like),
                ValidPhcFacility.normalised_name.ilike(f"%{normalise_facility_name(q)}%"),
                ValidPhcFacility.facility_code.ilike(like),
            )
        )
    if district:
        query = query.where(ValidPhcFacility.district.ilike(district.strip()))
    if state:
        query = query.where(ValidPhcFacility.state.ilike(state.strip()))
    return list((await db.scalars(query.order_by(ValidPhcFacility.name).limit(limit))).all())


# --- PHC worker applications --------------------------------------------------------


class Applicant(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_verified: bool
    is_active: bool
    phc_id: uuid.UUID | None


class ApplicationItem(BaseModel):
    id: uuid.UUID
    applicant: Applicant
    employee_id: str
    designation: Designation
    phc_name: str
    district: str
    state: str
    years_of_service: int
    status: ApplicationStatus
    rejection_reason: str | None
    facility: FacilityOut | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ApplicationsOut(BaseModel):
    items: list[ApplicationItem]
    total: int
    counts: dict[str, int]
    districts: list[str] = []


class HistoryItem(BaseModel):
    action: PhcVerificationAction
    from_status: str | None
    to_status: str
    reason: str | None
    actor: str | None
    created_at: datetime


class ApplicationDetail(ApplicationItem):
    # The registry's single exact match for what the applicant claimed, if any.
    suggested_facility: FacilityOut | None
    history: list[HistoryItem]
    documents: list[DocumentOut]


def _applicant(user: User) -> Applicant:
    return Applicant(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_verified=user.is_verified,
        is_active=user.is_active,
        phc_id=user.phc_id,
    )


def _item(app_: PhcApplication, user: User, facility: ValidPhcFacility | None, reviewer: str | None) -> dict:
    return dict(
        id=app_.id,
        applicant=_applicant(user),
        employee_id=app_.employee_id,
        designation=app_.designation,
        phc_name=app_.phc_name,
        district=app_.district,
        state=app_.state,
        years_of_service=app_.years_of_service,
        status=app_.status,
        rejection_reason=app_.rejection_reason,
        facility=FacilityOut.model_validate(facility) if facility else None,
        reviewed_by=reviewer,
        reviewed_at=app_.reviewed_at,
        created_at=app_.created_at,
    )


Reviewer = aliased(User)


def _applications_query():
    return (
        select(PhcApplication, User, ValidPhcFacility, Reviewer.name)
        .join(User, User.id == PhcApplication.user_id)
        .outerjoin(ValidPhcFacility, ValidPhcFacility.id == PhcApplication.facility_id)
        .outerjoin(Reviewer, Reviewer.id == PhcApplication.reviewed_by)
    )


@router.get("/applications", response_model=ApplicationsOut)
async def list_applications(
    status_: ApplicationStatus | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=120),
    district: str | None = Query(None, max_length=120),
    designation: Designation | None = None,
    days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> ApplicationsOut:
    filters = [in_area(PhcApplication.district, area_of(admin))]
    if district:
        filters.append(PhcApplication.district.ilike(district.strip()))
    if designation:
        filters.append(PhcApplication.designation == designation)
    if days:
        filters.append(PhcApplication.created_at >= utcnow() - timedelta(days=days))
    query = _applications_query().where(*filters)
    if status_:
        query = query.where(PhcApplication.status == status_)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            or_(User.name.ilike(like), User.email.ilike(like), PhcApplication.phc_name.ilike(like),
                PhcApplication.employee_id.ilike(like))
        )
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    # Oldest pending first: whoever has waited longest is reviewed first.
    rows = (await db.execute(query.order_by(PhcApplication.created_at).limit(limit).offset(offset))).all()
    counts = dict(
        (await db.execute(select(PhcApplication.status, func.count()).where(*filters).group_by(PhcApplication.status))).all()
    )
    districts = (
        await db.scalars(
            select(PhcApplication.district).where(in_area(PhcApplication.district, area_of(admin))).distinct().order_by(PhcApplication.district)
        )
    ).all()
    return ApplicationsOut(
        items=[ApplicationItem(**_item(a, u, f, r)) for a, u, f, r in rows],
        total=total,
        counts={s.value: counts.get(s, 0) for s in ApplicationStatus},
        districts=list(districts),
    )


async def _load_application(db: AsyncSession, application_id: uuid.UUID, lock: bool = False) -> PhcApplication:
    query = select(PhcApplication).where(PhcApplication.id == application_id)
    if lock:
        query = query.with_for_update()
    app_ = await db.scalar(query)
    if app_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, APPLICATION_NOT_FOUND)
    return app_


async def _detail(db: AsyncSession, application_id: uuid.UUID) -> ApplicationDetail:
    row = (await db.execute(_applications_query().where(PhcApplication.id == application_id))).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, APPLICATION_NOT_FOUND)
    app_, user, facility, reviewer = row
    suggested = await match_facility(db, app_.phc_name, app_.district, app_.state)
    Actor = aliased(User)
    history = (
        await db.execute(
            select(PhcVerificationAuditLog, Actor.name)
            .outerjoin(Actor, Actor.id == PhcVerificationAuditLog.actor_user_id)
            .where(PhcVerificationAuditLog.application_id == app_.id)
            .order_by(PhcVerificationAuditLog.created_at.desc())
        )
    ).all()
    return ApplicationDetail(
        **_item(app_, user, facility, reviewer),
        suggested_facility=FacilityOut.model_validate(suggested) if suggested else None,
        history=[
            HistoryItem(action=h.action, from_status=h.from_status, to_status=h.to_status, reason=h.reason,
                        actor=actor, created_at=h.created_at)
            for h, actor in history
        ],
        documents=await documents_of(db, app_.id),
    )


@router.get("/applications/{application_id}", response_model=ApplicationDetail)
async def get_application(application_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> ApplicationDetail:
    return await _detail(db, application_id)


class Approve(BaseModel):
    facility_id: uuid.UUID
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class Decision(BaseModel):
    reason: Reason


def _log(db: AsyncSession, app_: PhcApplication, admin: User, action: PhcVerificationAction, from_status: str,
         reason: str | None, request: Request) -> None:
    db.add(
        PhcVerificationAuditLog(
            application_id=app_.id,
            subject_user_id=app_.user_id,
            actor_user_id=admin.id,
            action=action,
            from_status=from_status,
            to_status=app_.status.value,
            reason=reason,
            ip_address=_ip(request),
        )
    )


@router.post("/applications/{application_id}/approve", response_model=ApplicationDetail)
async def approve(
    application_id: uuid.UUID,
    data: Approve,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> ApplicationDetail:
    app_ = await _load_application(db, application_id, lock=True)
    if app_.status == ApplicationStatus.approved:
        raise HTTPException(status.HTTP_409_CONFLICT, "This application is already approved.")
    user = await db.get(User, app_.user_id, with_for_update=True)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "The applicant's account is deactivated.")
    if not user.is_verified:
        raise HTTPException(status.HTTP_409_CONFLICT, "The applicant has not confirmed their email address yet.")
    facility = await db.get(ValidPhcFacility, data.facility_id)
    if facility is None or not facility.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, FACILITY_NOT_FOUND)

    now = utcnow()
    from_status = app_.status.value
    app_.status = ApplicationStatus.approved
    app_.rejection_reason = None
    app_.facility_id = facility.id
    app_.last_checked_at = now
    app_.reviewed_by = admin.id
    app_.reviewed_at = now
    # The catchment link: from here the worker sees citizens of this facility.
    user.role = UserRole.phc_worker
    user.phc_id = facility.id
    user.district = facility.district
    user.state = facility.state
    _log(db, app_, admin, PhcVerificationAction.application_approved, from_status, data.note, request)
    db.add(
        Alert(
            user_id=user.id,
            alert_type=AlertType.personal,
            severity=AlertSeverity.low,
            message=f"Your PHC worker account is approved. You are linked to {facility.name}.",
        )
    )
    await db.commit()
    return await _detail(db, app_.id)


@router.post("/applications/{application_id}/reject", response_model=ApplicationDetail)
async def reject(
    application_id: uuid.UUID,
    data: Decision,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> ApplicationDetail:
    app_ = await _load_application(db, application_id, lock=True)
    if app_.status != ApplicationStatus.pending:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only a pending application can be rejected. Revoke an approved one instead.",
        )
    now = utcnow()
    app_.status = ApplicationStatus.rejected
    app_.rejection_reason = data.reason
    app_.reviewed_by = admin.id
    app_.reviewed_at = now
    _log(db, app_, admin, PhcVerificationAction.application_rejected, ApplicationStatus.pending.value, data.reason,
         request)
    await db.commit()
    return await _detail(db, app_.id)


@router.post("/applications/{application_id}/revoke", response_model=ApplicationDetail)
async def revoke(
    application_id: uuid.UUID,
    data: Decision,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> ApplicationDetail:
    """Take worker access away. The account goes back to pending_phc with no catchment."""
    app_ = await _load_application(db, application_id, lock=True)
    if app_.status != ApplicationStatus.approved:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only an approved application can be revoked.")
    worker = await db.get(User, app_.user_id, with_for_update=True)
    now = utcnow()
    app_.status = ApplicationStatus.rejected
    app_.rejection_reason = data.reason
    app_.reviewed_by = admin.id
    app_.reviewed_at = now
    if worker is not None:
        worker.role = UserRole.pending_phc
        worker.phc_id = None
        # Citizens should not wait for a visit from someone who can no longer see them.
        visits = await db.execute(
            select(ScheduledVisit, User)
            .join(User, User.id == ScheduledVisit.citizen_id)
            .where(ScheduledVisit.worker_id == worker.id, ScheduledVisit.status == VisitStatus.scheduled)
        )
        for visit, citizen in visits.all():
            visit.status = VisitStatus.cancelled
            notify_changed(db, visit, citizen, worker, "cancelled")
        # Their assistant history quotes catchment records they may no longer see.
        await db.execute(delete(ChatSession).where(ChatSession.user_id == worker.id))
    _log(db, app_, admin, PhcVerificationAction.application_revoked, ApplicationStatus.approved.value, data.reason,
         request)
    await db.commit()
    return await _detail(db, app_.id)


# --- Accounts ---------------------------------------------------------------------


class AccountItem(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool
    profile_completed: bool
    facility: str | None
    district: str | None
    state: str | None
    created_at: datetime
    deactivated_at: datetime | None


class AccountsOut(BaseModel):
    items: list[AccountItem]
    total: int
    limit: int
    offset: int


@router.get("/users", response_model=AccountsOut)
async def list_users(
    role: UserRole | None = None,
    state_: Literal["active", "inactive", "unverified"] | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=120),
    sort: Literal["newest", "oldest", "name", "approved"] = "newest",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> AccountsOut:
    query = (
        select(User, ValidPhcFacility.name)
        .outerjoin(ValidPhcFacility, ValidPhcFacility.id == User.phc_id)
        .where(in_area(User.district, area_of(admin)))
    )
    if role:
        query = query.where(User.role == role)
    if state_ == "active":
        query = query.where(User.is_active.is_(True))
    elif state_ == "inactive":
        query = query.where(User.is_active.is_(False))
    elif state_ == "unverified":
        query = query.where(User.is_verified.is_(False))
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(User.name.ilike(like), User.email.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = {
        "newest": (User.created_at.desc(),),
        "oldest": (User.created_at.asc(),),
        "name": (func.lower(User.name).asc(),),
        "approved": (func.coalesce(PhcApplication.reviewed_at, User.verified_at).desc().nulls_last(), User.created_at.desc()),
    }[sort]
    if sort == "approved":
        query = query.outerjoin(PhcApplication, PhcApplication.user_id == User.id)
    rows = (await db.execute(query.order_by(*order).limit(limit).offset(offset))).all()
    return AccountsOut(
        items=[
            AccountItem(
                id=u.id, name=u.name, email=u.email, role=u.role, is_active=u.is_active, is_verified=u.is_verified,
                profile_completed=u.profile_completed, facility=facility, district=u.district, state=u.state,
                created_at=u.created_at, deactivated_at=u.deactivated_at,
            )
            for u, facility in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


async def _target(db: AsyncSession, admin: User, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id, with_for_update=True)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, USER_NOT_FOUND)
    if user.id == admin.id or user.role == UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator accounts cannot be changed here.")
    return user


@router.post("/users/{user_id}/deactivate", response_model=AccountItem)
async def deactivate_user(
    user_id: uuid.UUID,
    data: Decision,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> AccountItem:
    user = await _target(db, admin, user_id)
    if not user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account is already deactivated.")
    user.is_active = False
    user.deactivated_at = utcnow()
    # Signed out everywhere at once; get_current_user also re-reads is_active on every request.
    await sessions.revoke_all_for_user(db, user.id, "deactivated_by_admin")
    db.add(AuditLog(user_id=admin.id, action=f"admin_deactivate: {data.reason}", entity="users",
                    entity_id=user.id, ip_address=_ip(request)))
    await db.commit()
    return await _account(db, user)


@router.post("/users/{user_id}/reactivate", response_model=AccountItem)
async def reactivate_user(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> AccountItem:
    user = await _target(db, admin, user_id)
    if user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account is already active.")
    user.is_active = True
    user.deactivated_at = None
    db.add(AuditLog(user_id=admin.id, action="admin_reactivate", entity="users", entity_id=user.id,
                    ip_address=_ip(request)))
    await db.commit()
    return await _account(db, user)


async def _account(db: AsyncSession, u: User) -> AccountItem:
    facility = await db.scalar(select(ValidPhcFacility.name).where(ValidPhcFacility.id == u.phc_id)) if u.phc_id else None
    return AccountItem(
        id=u.id, name=u.name, email=u.email, role=u.role, is_active=u.is_active, is_verified=u.is_verified,
        profile_completed=u.profile_completed, facility=facility, district=u.district, state=u.state,
        created_at=u.created_at, deactivated_at=u.deactivated_at,
    )


# --- Support concerns ---------------------------------------------------------------


class ConcernItem(BaseModel):
    id: uuid.UUID
    ticket_ref: str
    category: ConcernCategory
    description: str
    status: ConcernStatus
    admin_note: str | None
    raised_by: str
    raised_by_email: str
    raised_by_role: UserRole
    raised_by_district: str | None
    subject: str | None
    subject_role: UserRole | None
    evidence: dict[str, Any] | None
    handled_by: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class ConcernsOut(BaseModel):
    items: list[ConcernItem]
    total: int
    counts: dict[str, int]


Raiser = aliased(User)
Handler = aliased(User)
Subject = aliased(User)

STAGES = {
    "not_reviewed": (ConcernStatus.open,),
    "in_progress": (ConcernStatus.in_review,),
    "action_taken": (ConcernStatus.resolved, ConcernStatus.rejected),
}


def _concerns_query():
    return (
        select(Concern, Raiser, Handler.name, Subject)
        .join(Raiser, Raiser.id == Concern.user_id)
        .outerjoin(Handler, Handler.id == Concern.handled_by)
        .outerjoin(Subject, Subject.id == Concern.subject_id)
    )


def _concern(c: Concern, raiser: User, handler: str | None, subject: User | None) -> ConcernItem:
    return ConcernItem(
        id=c.id, ticket_ref=c.ticket_ref, category=c.category, description=c.description, status=c.status,
        admin_note=c.admin_note, raised_by=raiser.name, raised_by_email=raiser.email, raised_by_role=raiser.role,
        raised_by_district=raiser.district, subject=subject.name if subject else None,
        subject_role=subject.role if subject else None, evidence=c.evidence,
        handled_by=handler, created_at=c.created_at, updated_at=c.updated_at, resolved_at=c.resolved_at,
    )


@router.get("/concerns", response_model=ConcernsOut)
async def list_concerns(
    status_: ConcernStatus | None = Query(None, alias="status"),
    category: ConcernCategory | None = None,
    raiser: Literal["user", "phc_worker"] | None = None,
    stage: Literal["not_reviewed", "in_progress", "action_taken"] | None = None,
    q: str | None = Query(None, max_length=120),
    days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> ConcernsOut:
    mine = in_area(Raiser.district, area_of(admin))
    if raiser:
        mine = and_(mine, Raiser.role == UserRole(raiser))
    if days:
        mine = and_(mine, Concern.created_at >= utcnow() - timedelta(days=days))
    if q and q.strip():
        like = f"%{q.strip()}%"
        mine = and_(mine, or_(Raiser.name.ilike(like), Raiser.email.ilike(like), Concern.ticket_ref.ilike(like),
                              Concern.description.ilike(like), Subject.name.ilike(like)))
    query = _concerns_query().where(mine)
    if status_:
        query = query.where(Concern.status == status_)
    if stage:
        query = query.where(Concern.status.in_(STAGES[stage]))
    if category:
        query = query.where(Concern.category == category)
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (await db.execute(query.order_by(Concern.created_at.desc()).limit(limit).offset(offset))).all()
    counts = dict(
        (
            await db.execute(
                select(Concern.status, func.count()).join(Raiser, Raiser.id == Concern.user_id)
                .outerjoin(Subject, Subject.id == Concern.subject_id).where(mine).group_by(Concern.status)
            )
        ).all()
    )
    return ConcernsOut(
        items=[_concern(*r) for r in rows],
        total=total,
        counts={**{s.value: counts.get(s, 0) for s in ConcernStatus},
                **{k: sum(counts.get(s, 0) for s in v) for k, v in STAGES.items()}},
    )


class ConcernUpdate(BaseModel):
    status: ConcernStatus
    admin_note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


@router.patch("/concerns/{concern_id}", response_model=ConcernItem)
async def update_concern(
    concern_id: uuid.UUID,
    data: ConcernUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> ConcernItem:
    concern = await db.get(Concern, concern_id, with_for_update=True)
    if concern is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, CONCERN_NOT_FOUND)
    closing = data.status in (ConcernStatus.resolved, ConcernStatus.rejected)
    if closing and not (data.admin_note or concern.admin_note):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Add a note for the person before closing this.")
    concern.status = data.status
    if data.admin_note is not None:
        concern.admin_note = data.admin_note or None
    concern.handled_by = admin.id
    concern.resolved_at = utcnow() if closing else None
    db.add(AuditLog(user_id=admin.id, action=f"concern_{data.status.value}", entity="concerns",
                    entity_id=concern.id, ip_address=_ip(request)))
    await db.commit()
    row = (await db.execute(_concerns_query().where(Concern.id == concern.id))).one()
    return _concern(*row)


# --- Audit trail --------------------------------------------------------------------


class AuditItem(BaseModel):
    source: Literal["account", "verification"]
    action: str
    actor: str | None
    entity: str
    entity_id: uuid.UUID | None
    detail: str | None
    ip_address: str
    created_at: datetime


@router.get("/audit", response_model=list[AuditItem])
async def audit(
    source: Literal["account", "verification"] | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
) -> list[AuditItem]:
    """Both trails, newest first. Each is append-only; this only reads them."""
    items: list[AuditItem] = []
    if source in (None, "account"):
        Actor = aliased(User)
        rows = await db.execute(
            select(AuditLog, Actor.name)
            .outerjoin(Actor, Actor.id == AuditLog.user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        items += [
            AuditItem(source="account", action=a.action, actor=name, entity=a.entity, entity_id=a.entity_id,
                      detail=None, ip_address=a.ip_address, created_at=a.created_at)
            for a, name in rows.all()
        ]
    if source in (None, "verification"):
        Actor = aliased(User)
        Subject = aliased(User)
        rows = await db.execute(
            select(PhcVerificationAuditLog, Actor.name, Subject.name)
            .outerjoin(Actor, Actor.id == PhcVerificationAuditLog.actor_user_id)
            .join(Subject, Subject.id == PhcVerificationAuditLog.subject_user_id)
            .order_by(PhcVerificationAuditLog.created_at.desc())
            .limit(limit)
        )
        items += [
            AuditItem(
                source="verification", action=v.action.value, actor=actor, entity="phc_applications",
                entity_id=v.application_id,
                detail=f"{subject}: {v.from_status or '-'} -> {v.to_status}" + (f" ({v.reason})" if v.reason else ""),
                ip_address=v.ip_address, created_at=v.created_at,
            )
            for v, actor, subject in rows.all()
        ]
    items.sort(key=lambda i: i.created_at, reverse=True)
    return items[:limit]


# --- Research export ----------------------------------------------------------------

RESEARCH_EXPORT_CAP = 50_000


def _age_band(age: int | None) -> str:
    if age is None:
        return ""
    low = age // 10 * 10
    return f"{low}-{low + 9}"


@router.get("/research-export")
async def research_export(
    request: Request,
    days: int = Query(365, ge=7, le=1825),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """De-identified readings, as CSV, from citizens who allowed research use only.

    No names, contact details, exact ages, areas or record ids. Each person gets a
    pseudonym that is random per export, so two exports cannot be joined. Readings
    carry their date, not the time. Districts with fewer than MIN_CELL consenting
    people are reported as "Other".
    """
    since = utcnow() - timedelta(days=days)
    consenting = select(User.id).where(User.role == UserRole.user, in_research(User.id))
    rows = (
        await db.execute(
            select(
                HealthRecord.user_id,
                HealthRecord.timestamp,
                HealthRecord.vitals,
                HealthRecord.symptoms,
                ProcessedData.anomaly_score,
                ProcessedData.is_anomaly,
                ProcessedData.model_version,
                User.district,
                UserProfile.age,
                UserProfile.gender,
            )
            .join(User, User.id == HealthRecord.user_id)
            .outerjoin(ProcessedData, ProcessedData.health_record_id == HealthRecord.id)
            .outerjoin(UserProfile, UserProfile.user_id == HealthRecord.user_id)
            .where(HealthRecord.user_id.in_(consenting), HealthRecord.timestamp >= since)
            .order_by(HealthRecord.timestamp)
            .limit(RESEARCH_EXPORT_CAP)
        )
    ).all()

    people_by_district: dict[str, set[uuid.UUID]] = {}
    for r in rows:
        people_by_district.setdefault(r.district or "", set()).add(r.user_id)
    small = {d for d, people in people_by_district.items() if len(people) < MIN_CELL}

    salt = secrets.token_bytes(16)
    vital_keys = list(VITALS)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["person", "date", "age_band", "gender", "district", *vital_keys, "symptoms", "anomaly_score", "flagged", "model_version"]
    )
    for r in rows:
        person = hashlib.sha256(salt + r.user_id.bytes).hexdigest()[:12]
        district = "Other" if (r.district or "") in small else r.district
        writer.writerow([
            person,
            r.timestamp.date().isoformat(),
            _age_band(r.age),
            r.gender.value if r.gender else "",
            district,
            *[r.vitals.get(k, "") for k in vital_keys],
            ";".join(r.symptoms or []),
            "" if r.anomaly_score is None else round(r.anomaly_score, 3),
            "" if r.is_anomaly is None else int(r.is_anomaly),
            r.model_version or "",
        ])

    db.add(AuditLog(user_id=admin.id, action="research_export", entity="health_records", entity_id=None, ip_address=_ip(request)))
    await db.commit()
    stamp = utcnow().strftime("%Y%m%d")
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="healthnexus-research-{stamp}.csv"',
            "X-Export-People": str(sum(len(p) for p in people_by_district.values())),
            "X-Export-Rows": str(len(rows)),
        },
    )
