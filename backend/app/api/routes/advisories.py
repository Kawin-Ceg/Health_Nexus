"""Community health advisories: PHC workers write to their centre's citizens, admins to a district or the state."""

import math
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import and_, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_any_verified
from app.db.session import get_session
from app.models import Advisory, Alert, AuditLog, CommunityData, User, ValidPhcFacility
from app.models.enums import AdvisoryScope, AlertSeverity, UserRole
from app.schemas.health import AdvisoryOut
from app.services import sessions
from app.services.visit_state import now_utc

router = APIRouter(prefix="/advisories", tags=["advisories"])

NOT_FOUND = "Advisory not found."


class AdvisoryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: AdvisoryScope
    district: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)] | None = None
    phc_id: uuid.UUID | None = None
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=120)]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]
    severity: AlertSeverity = AlertSeverity.medium
    days: Annotated[int, Field(ge=1, le=90)] = 14
    cluster_id: uuid.UUID | None = None
    area: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)] | None = None
    radius_km: Annotated[float, Field(ge=1, le=25)] | None = None
    red_reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: Literal["good", "poor"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class Check(BaseModel):
    label: str
    value: str
    met: bool


class RedCheckOut(BaseModel):
    allowed: bool
    message: str
    checks: list[Check]


class AdvisoriesOut(BaseModel):
    items: list[AdvisoryOut]


def _near(lat_a, lng_a, lat_b, lng_b, cos_lat: float):
    """Squared distance in km, flat-earth: fine for the few km an advisory reaches."""
    return ((lat_a - lat_b) * 111.0) * ((lat_a - lat_b) * 111.0) + ((lng_a - lng_b) * 111.0 * cos_lat) * ((lng_a - lng_b) * 111.0 * cos_lat)


def targeting(user: User):
    """Advisories addressed to this person: their centre (or living near one), their locality, district or state."""
    clauses = []
    if user.phc_id:
        clauses.append(and_(Advisory.scope == AdvisoryScope.centre, Advisory.phc_id == user.phc_id))
    if user.geo_lat is not None and user.geo_lng is not None:
        clauses.append(and_(
            Advisory.scope == AdvisoryScope.centre,
            Advisory.radius_km.is_not(None),
            _near(Advisory.centre_lat, Advisory.centre_lng, user.geo_lat, user.geo_lng, math.cos(math.radians(user.geo_lat)))
            <= Advisory.radius_km * Advisory.radius_km,
        ))
    if user.district and (user.area or user.pincode):
        places = [p.lower() for p in (user.area, user.pincode) if p]
        clauses.append(and_(
            Advisory.scope == AdvisoryScope.area,
            func.lower(Advisory.district) == user.district.lower(),
            func.lower(Advisory.area).in_(places),
        ))
    if user.district:
        clauses.append(and_(Advisory.scope == AdvisoryScope.district, func.lower(Advisory.district) == user.district.lower()))
    if user.state:
        clauses.append(and_(Advisory.scope == AdvisoryScope.state, func.lower(Advisory.state) == user.state.lower()))
    return or_(*clauses) if clauses else Advisory.id.is_(None)


def is_active(now: datetime):
    return and_(Advisory.withdrawn_at.is_(None), Advisory.expires_at > now)


def _audience_users(advisory: Advisory):
    base = select(func.count()).select_from(User).where(User.role == UserRole.user, User.is_active.is_(True))
    return base.where(audience_filter(advisory.scope, advisory.district, advisory.state, advisory.phc_id,
                                      advisory.area, advisory.radius_km, advisory.centre_lat, advisory.centre_lng))


def audience_filter(scope, district, state, phc_id, area, radius_km, lat, lng):
    if scope == AdvisoryScope.centre:
        mine = User.phc_id == phc_id
        if radius_km and lat is not None and lng is not None:
            return or_(mine, and_(User.geo_lat.is_not(None),
                                  _near(User.geo_lat, User.geo_lng, lat, lng, math.cos(math.radians(lat))) <= radius_km * radius_km))
        return mine
    if scope == AdvisoryScope.area:
        return and_(func.lower(User.district) == (district or "").lower(), or_(func.lower(User.area) == (area or "").lower(), User.pincode == area))
    if scope == AdvisoryScope.district:
        return func.lower(User.district) == (district or "").lower()
    return func.lower(User.state) == (state or "").lower()


async def advisory_out(db: AsyncSession, a: Advisory, viewer: User | None = None, *, with_reach: bool = False) -> AdvisoryOut:
    if a.scope == AdvisoryScope.centre:
        facility = await db.get(ValidPhcFacility, a.phc_id)
        audience = facility.name if facility else "A health centre"
        if a.radius_km:
            audience += f" + people within {a.radius_km:g} km"
    elif a.scope == AdvisoryScope.area:
        audience = f"{a.area}, {a.district}"
    elif a.scope == AdvisoryScope.district:
        audience = f"{a.district} district"
    else:
        audience = a.state
    author = await db.get(User, a.author_id) if a.author_id else None
    now = now_utc()
    return AdvisoryOut(
        id=a.id,
        scope=a.scope,
        audience=audience,
        title=a.title,
        body=a.body,
        severity=a.severity,
        author=(author.name if author else None),
        created_at=a.created_at,
        expires_at=a.expires_at,
        withdrawn_at=a.withdrawn_at,
        active=a.withdrawn_at is None and a.expires_at > now,
        reach=(await db.scalar(_audience_users(a)) or 0) if with_reach else None,
        can_withdraw=viewer is not None and _may_withdraw(viewer, a),
        area=a.area,
        radius_km=a.radius_km,
        red_reason=a.red_reason,
        feedback=a.feedback,
        feedback_note=a.feedback_note,
        feedback_at=a.feedback_at,
    )


RED_MIN_CASES = 10
RED_MIN_HIGH_ALERTS = 15
RED_MIN_SHARE = 0.05
RED_REASON_MIN = 30


async def red_check(db: AsyncSession, user: User, cluster_id: uuid.UUID | None) -> RedCheckOut:
    """Red reaches everyone with an emergency tone, so it needs evidence: a confirmed outbreak, or a surge of high alerts."""
    now = now_utc()
    district = user.district
    if user.role == UserRole.phc_worker and user.phc_id:
        facility = await db.get(ValidPhcFacility, user.phc_id)
        district = facility.district if facility else district
    in_area = (lambda col: func.lower(col) == district.lower()) if district else (lambda col: true())

    linked = await db.get(CommunityData, cluster_id) if cluster_id else None
    linked_ok = bool(linked and linked.outbreak_flag and linked.cases >= RED_MIN_CASES)
    outbreaks = (await db.scalars(
        select(CommunityData).where(
            CommunityData.outbreak_flag.is_(True),
            CommunityData.window_end >= now - timedelta(days=14),
            in_area(CommunityData.district),
        )
    )).all()
    biggest = max((c.cases for c in outbreaks), default=0)
    citizens = await db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.user, User.is_active.is_(True), in_area(User.district))
    ) or 0
    high = await db.scalar(
        select(func.count(func.distinct(Alert.user_id))).select_from(Alert).join(User, User.id == Alert.user_id).where(
            Alert.severity == AlertSeverity.high, Alert.created_at >= now - timedelta(days=7), in_area(User.district)
        )
    ) or 0
    share = high / citizens if citizens else 0
    running = await db.scalar(
        select(func.count()).select_from(Advisory).where(
            Advisory.severity == AlertSeverity.high, is_active(now), in_area(Advisory.district)
        )
    ) or 0

    outbreak_ok = linked_ok or biggest >= RED_MIN_CASES
    surge_ok = high >= RED_MIN_HIGH_ALERTS and share >= RED_MIN_SHARE
    checks = [
        Check(label="Confirmed outbreak in the last 14 days", value=f"{len(outbreaks)} flagged, largest {biggest} cases (needs {RED_MIN_CASES}+)", met=outbreak_ok),
        Check(
            label="Citizens with high-risk readings this week",
            value=f"{high} of {citizens} ({share:.0%}); needs {RED_MIN_HIGH_ALERTS}+ and {RED_MIN_SHARE:.0%}+",
            met=surge_ok,
        ),
        Check(label="No other red advisory running", value=f"{running} running", met=running == 0),
    ]
    allowed = (outbreak_ok or surge_ok) and running == 0
    if allowed:
        message = "The evidence supports a red advisory. Say why in the reason box; it is kept in the audit trail."
    elif running:
        message = "A red advisory is already running here. Update or withdraw it rather than adding another."
    else:
        message = "The situation does not look serious enough for red. Use yellow so people take care without panic."
    return RedCheckOut(allowed=allowed, message=message, checks=checks)


def _may_withdraw(user: User, a: Advisory) -> bool:
    if user.role == UserRole.admin:
        return True
    return user.role == UserRole.phc_worker and a.scope == AdvisoryScope.centre and a.phc_id == user.phc_id


async def authors(user: User = Depends(require_any_verified)) -> User:
    if user.role not in (UserRole.phc_worker, UserRole.admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only health workers and administrators publish advisories.")
    return user


@router.get("", response_model=AdvisoriesOut)
async def list_advisories(
    include_ended: bool = False,
    limit: int = Query(200, ge=1, le=500),
    user: User = Depends(authors),
    db: AsyncSession = Depends(get_session),
) -> AdvisoriesOut:
    """Admins see every advisory; workers see the ones their citizens see, plus any they wrote."""
    query = select(Advisory)
    if user.role == UserRole.admin and user.district:
        query = query.where(func.lower(Advisory.district) == user.district.lower())
    if user.role == UserRole.phc_worker:
        query = query.where(or_(targeting(user), Advisory.author_id == user.id))
    if not include_ended:
        query = query.where(is_active(now_utc()))
    rows = (await db.scalars(query.order_by(Advisory.created_at.desc()).limit(limit))).all()
    return AdvisoriesOut(items=[await advisory_out(db, a, user, with_reach=True) for a in rows])


class TargetIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scope: AdvisoryScope
    district: str | None = None
    phc_id: uuid.UUID | None = None
    area: str | None = None
    radius_km: Annotated[float, Field(ge=1, le=25)] | None = None


async def resolve_target(db: AsyncSession, user: User, data: TargetIn | AdvisoryIn) -> dict:
    """Who an advisory reaches. Admins stay inside their district; workers inside their centre."""
    state = user.state or "Tamil Nadu"
    if user.role == UserRole.phc_worker:
        if data.scope != AdvisoryScope.centre:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Health workers write to their own centre's citizens.")
        if user.phc_id is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Your account is not linked to a health centre.")
        phc_id = user.phc_id
    else:
        phc_id = data.phc_id
    district = user.district or data.district
    if data.scope == AdvisoryScope.centre:
        facility = await db.get(ValidPhcFacility, phc_id) if phc_id else None
        if facility is None or (district and facility.district.lower() != district.lower()):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a health centre in your district.")
        radius = data.radius_km
        if radius and facility.latitude is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "This centre has no location yet, so nearby residents cannot be found.")
        return dict(scope=AdvisoryScope.centre, phc_id=facility.id, district=facility.district, state=facility.state,
                    radius_km=radius, centre_lat=facility.latitude if radius else None, centre_lng=facility.longitude if radius else None)
    if data.scope == AdvisoryScope.state:
        if user.district:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"You publish for {user.district} district only.")
        return dict(scope=AdvisoryScope.state, state=state)
    if not district:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose the district.")
    known = await db.scalar(select(ValidPhcFacility.district).where(func.lower(ValidPhcFacility.district) == district.lower()).limit(1))
    if known is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No health centre is registered in that district.")
    if data.scope == AdvisoryScope.area:
        if not data.area:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose the locality.")
        return dict(scope=AdvisoryScope.area, district=known, state=state, area=data.area.strip())
    return dict(scope=AdvisoryScope.district, district=known, state=state)


class Place(BaseModel):
    name: str
    citizens: int


class CentreOption(BaseModel):
    id: uuid.UUID
    name: str
    block: str | None
    located: bool
    citizens: int


class TargetsOut(BaseModel):
    district: str | None
    centres: list[CentreOption]
    localities: list[Place]
    pincodes: list[Place]


@router.get("/targets", response_model=TargetsOut)
async def targets(user: User = Depends(authors), db: AsyncSession = Depends(get_session)) -> TargetsOut:
    """The centres and localities an author can address."""
    citizen = and_(User.role == UserRole.user, User.is_active.is_(True))
    centres = select(ValidPhcFacility).where(ValidPhcFacility.is_active.is_(True))
    people = select(User).where(citizen)
    if user.role == UserRole.phc_worker:
        centres = centres.where(ValidPhcFacility.id == user.phc_id)
    if user.district:
        centres = centres.where(func.lower(ValidPhcFacility.district) == user.district.lower())
        people = people.where(func.lower(User.district) == user.district.lower())
    counts = dict((await db.execute(select(User.phc_id, func.count()).where(citizen).group_by(User.phc_id))).all())
    sub = people.subquery()
    localities = (await db.execute(
        select(sub.c.area, func.count()).where(sub.c.area.is_not(None)).group_by(sub.c.area).order_by(sub.c.area)
    )).all()
    pincodes = (await db.execute(
        select(sub.c.pincode, func.count()).where(sub.c.pincode.is_not(None)).group_by(sub.c.pincode).order_by(sub.c.pincode)
    )).all()
    return TargetsOut(
        district=user.district,
        centres=[
            CentreOption(id=c.id, name=c.name, block=c.block, located=c.latitude is not None, citizens=counts.get(c.id, 0))
            for c in (await db.scalars(centres.order_by(ValidPhcFacility.name))).all()
        ],
        localities=[Place(name=n, citizens=k) for n, k in localities],
        pincodes=[Place(name=n, citizens=k) for n, k in pincodes],
    )


class ReachOut(BaseModel):
    citizens: int
    registered: int


@router.post("/reach", response_model=ReachOut)
async def reach(data: TargetIn, user: User = Depends(authors), db: AsyncSession = Depends(get_session)) -> ReachOut:
    """How many citizens a target would reach, and how many of them are registered at a centre."""
    t = await resolve_target(db, user, data)
    where = and_(User.role == UserRole.user, User.is_active.is_(True), audience_filter(
        t["scope"], t.get("district"), t.get("state"), t.get("phc_id"), t.get("area"), t.get("radius_km"), t.get("centre_lat"), t.get("centre_lng")))
    total = await db.scalar(select(func.count()).select_from(User).where(where)) or 0
    linked = User.phc_id == t["phc_id"] if t["scope"] == AdvisoryScope.centre else User.phc_id.is_not(None)
    registered = await db.scalar(select(func.count()).select_from(User).where(where, linked)) or 0
    return ReachOut(citizens=total, registered=registered)


@router.get("/red-check", response_model=RedCheckOut)
async def check_red(
    cluster_id: uuid.UUID | None = None, user: User = Depends(authors), db: AsyncSession = Depends(get_session)
) -> RedCheckOut:
    return await red_check(db, user, cluster_id)


@router.post("", response_model=AdvisoryOut, status_code=status.HTTP_201_CREATED)
async def create_advisory(
    data: AdvisoryIn, request: Request, user: User = Depends(authors), db: AsyncSession = Depends(get_session)
) -> AdvisoryOut:
    if data.severity == AlertSeverity.high:
        verdict = await red_check(db, user, data.cluster_id)
        if not verdict.allowed:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, verdict.message)
        if len(data.red_reason or "") < RED_REASON_MIN:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Explain in at least {RED_REASON_MIN} characters why this needs red.")
    if data.cluster_id:
        cluster = await db.get(CommunityData, data.cluster_id)
        if cluster is None or (user.role == UserRole.phc_worker and str(user.phc_id) not in cluster.phc_ids):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cluster not found.")
    target = await resolve_target(db, user, data)
    advisory = Advisory(
        author_id=user.id,
        red_reason=data.red_reason if data.severity == AlertSeverity.high else None,
        title=data.title,
        body=data.body,
        severity=data.severity,
        expires_at=now_utc() + timedelta(days=data.days),
        cluster_id=data.cluster_id,
        **target,
    )
    db.add(advisory)
    await db.flush()
    db.add(AuditLog(user_id=user.id, action="publish_advisory", entity="advisories", entity_id=advisory.id,
                    ip_address=sessions.client_ip(request) or "unknown"))
    await db.commit()
    return await advisory_out(db, advisory, user, with_reach=True)


@router.post("/{advisory_id}/withdraw", response_model=AdvisoryOut)
async def withdraw_advisory(
    advisory_id: uuid.UUID, request: Request, user: User = Depends(authors), db: AsyncSession = Depends(get_session)
) -> AdvisoryOut:
    advisory = await db.get(Advisory, advisory_id, with_for_update=True)
    if advisory is None or not _may_withdraw(user, advisory):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    if advisory.withdrawn_at is None:
        advisory.withdrawn_at = now_utc()
        db.add(AuditLog(user_id=user.id, action="withdraw_advisory", entity="advisories", entity_id=advisory.id,
                        ip_address=sessions.client_ip(request) or "unknown"))
        await db.commit()
    return await advisory_out(db, advisory, user, with_reach=True)


@router.post("/{advisory_id}/feedback", response_model=AdvisoryOut)
async def review_advisory(
    advisory_id: uuid.UUID,
    data: FeedbackIn,
    request: Request,
    user: User = Depends(authors),
    db: AsyncSession = Depends(get_session),
) -> AdvisoryOut:
    """Mark whether an advisory helped, so future ones learn from it."""
    advisory = await db.get(Advisory, advisory_id)
    if advisory is None or not _may_withdraw(user, advisory):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    advisory.feedback, advisory.feedback_note, advisory.feedback_at = data.rating, data.note or None, now_utc()
    db.add(AuditLog(user_id=user.id, action="review_advisory", entity="advisories", entity_id=advisory.id,
                    ip_address=sessions.client_ip(request) or "unknown"))
    await db.commit()
    return await advisory_out(db, advisory, user, with_reach=True)
