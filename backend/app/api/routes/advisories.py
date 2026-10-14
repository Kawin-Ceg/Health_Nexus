"""Community health advisories: PHC workers write to their centre's citizens, admins to a district or the state."""

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_any_verified
from app.db.session import get_session
from app.models import Advisory, AuditLog, CommunityData, User, ValidPhcFacility
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


class AdvisoriesOut(BaseModel):
    items: list[AdvisoryOut]


def targeting(user: User):
    """Advisories addressed to this person: their centre, their district, or their state."""
    clauses = []
    if user.phc_id:
        clauses.append(and_(Advisory.scope == AdvisoryScope.centre, Advisory.phc_id == user.phc_id))
    if user.district:
        clauses.append(and_(Advisory.scope == AdvisoryScope.district, func.lower(Advisory.district) == user.district.lower()))
    if user.state:
        clauses.append(and_(Advisory.scope == AdvisoryScope.state, func.lower(Advisory.state) == user.state.lower()))
    return or_(*clauses) if clauses else Advisory.id.is_(None)


def is_active(now: datetime):
    return and_(Advisory.withdrawn_at.is_(None), Advisory.expires_at > now)


def _audience_users(advisory: Advisory):
    base = select(func.count()).select_from(User).where(User.role == UserRole.user, User.is_active.is_(True))
    if advisory.scope == AdvisoryScope.centre:
        return base.where(User.phc_id == advisory.phc_id)
    if advisory.scope == AdvisoryScope.district:
        return base.where(func.lower(User.district) == (advisory.district or "").lower())
    return base.where(func.lower(User.state) == advisory.state.lower())


async def advisory_out(db: AsyncSession, a: Advisory, viewer: User | None = None, *, with_reach: bool = False) -> AdvisoryOut:
    if a.scope == AdvisoryScope.centre:
        facility = await db.get(ValidPhcFacility, a.phc_id)
        audience = facility.name if facility else "A health centre"
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
    )


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
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(authors),
    db: AsyncSession = Depends(get_session),
) -> AdvisoriesOut:
    """Admins see every advisory; workers see the ones their citizens see, plus any they wrote."""
    query = select(Advisory)
    if user.role == UserRole.phc_worker:
        query = query.where(or_(targeting(user), Advisory.author_id == user.id))
    if not include_ended:
        query = query.where(is_active(now_utc()))
    rows = (await db.scalars(query.order_by(Advisory.created_at.desc()).limit(limit))).all()
    return AdvisoriesOut(items=[await advisory_out(db, a, user, with_reach=True) for a in rows])


@router.post("", response_model=AdvisoryOut, status_code=status.HTTP_201_CREATED)
async def create_advisory(
    data: AdvisoryIn, request: Request, user: User = Depends(authors), db: AsyncSession = Depends(get_session)
) -> AdvisoryOut:
    advisory = Advisory(
        author_id=user.id,
        scope=data.scope,
        title=data.title,
        body=data.body,
        severity=data.severity,
        expires_at=now_utc() + timedelta(days=data.days),
        state=user.state or "Tamil Nadu",
        cluster_id=data.cluster_id,
    )
    if data.cluster_id:
        cluster = await db.get(CommunityData, data.cluster_id)
        if cluster is None or (user.role == UserRole.phc_worker and str(user.phc_id) not in cluster.phc_ids):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cluster not found.")
    if user.role == UserRole.phc_worker:
        if data.scope != AdvisoryScope.centre:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Health workers write to their own centre's citizens.")
        if user.phc_id is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Your account is not linked to a health centre.")
        facility = await db.get(ValidPhcFacility, user.phc_id)
        advisory.phc_id, advisory.district, advisory.state = user.phc_id, facility.district, facility.state
    elif data.scope == AdvisoryScope.centre:
        facility = await db.get(ValidPhcFacility, data.phc_id) if data.phc_id else None
        if facility is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose the health centre.")
        advisory.phc_id, advisory.district, advisory.state = facility.id, facility.district, facility.state
    elif data.scope == AdvisoryScope.district:
        if not data.district:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose the district.")
        known = await db.scalar(
            select(ValidPhcFacility.district).where(func.lower(ValidPhcFacility.district) == data.district.lower()).limit(1)
        )
        if known is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No health centre is registered in that district.")
        advisory.district = known
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
