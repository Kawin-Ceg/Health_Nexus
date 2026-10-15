"""Outbreak signals from the latest clustering run (services/outbreaks.py)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin, require_any_verified
from app.db.session import get_session
from app.models import Advisory, AuditLog, CommunityData, User
from app.models.enums import UserRole
from app.services import outbreaks, sessions

router = APIRouter(prefix="/clusters", tags=["outbreaks"])

NOT_FOUND = "Cluster not found."


class ClusterOut(BaseModel):
    id: uuid.UUID
    syndrome: str
    region: str
    district: str | None
    cases: int
    expected: float
    p_value: float
    outbreak: bool
    prevalence: float
    symptoms: dict[str, int]
    localities: dict[str, int]
    centre_lat: float
    centre_lng: float
    radius_km: float
    first_onset: datetime
    last_onset: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    advisory_id: uuid.UUID | None
    yours: bool


class ClustersOut(BaseModel):
    items: list[ClusterOut]
    last_run_at: datetime | None
    window_days: int
    radius_km: float
    min_people: int


async def viewer(user: User = Depends(require_any_verified)) -> User:
    if user.role not in (UserRole.phc_worker, UserRole.admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Outbreak signals are for health workers and administrators.")
    return user


async def _out(db: AsyncSession, c: CommunityData, user: User) -> ClusterOut:
    who = await db.get(User, c.acknowledged_by) if c.acknowledged_by else None
    advisory = await db.scalar(select(Advisory.id).where(Advisory.cluster_id == c.id).limit(1))
    return ClusterOut(
        id=c.id, syndrome=c.syndrome, region=c.region, district=c.district, cases=c.cases, expected=c.expected,
        p_value=c.p_value, outbreak=c.outbreak_flag, prevalence=c.prevalence_score,
        symptoms=c.symptom_cluster.get("symptoms", {}), localities=c.symptom_cluster.get("localities", {}),
        centre_lat=c.centre_lat, centre_lng=c.centre_lng, radius_km=c.radius_km,
        first_onset=c.first_onset, last_onset=c.last_onset, acknowledged_at=c.acknowledged_at,
        acknowledged_by=who.name if who else None, advisory_id=advisory,
        yours=user.phc_id is not None and str(user.phc_id) in c.phc_ids,
    )


async def _listing(db: AsyncSession, user: User) -> ClustersOut:
    last = await outbreaks.last_run_at(db)
    items: list[ClusterOut] = []
    if last is not None:
        query = select(CommunityData).where(CommunityData.window_end == last)
        if user.role == UserRole.phc_worker:
            query = query.where(cast(CommunityData.phc_ids, JSONB).contains([str(user.phc_id)]))
        rows = await db.scalars(query.order_by(CommunityData.outbreak_flag.desc(), CommunityData.p_value))
        items = [await _out(db, c, user) for c in rows]
    return ClustersOut(
        items=items,
        last_run_at=last,
        window_days=outbreaks.WINDOW.days,
        radius_km=outbreaks.PARAMS.radius_km,
        min_people=outbreaks.PARAMS.min_people,
    )


@router.get("", response_model=ClustersOut)
async def current_clusters(user: User = Depends(viewer), db: AsyncSession = Depends(get_session)) -> ClustersOut:
    """Admins see every cluster; a health worker sees those that include their centre's citizens."""
    return await _listing(db, user)


@router.post("/run", response_model=ClustersOut)
async def run_now(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_session)) -> ClustersOut:
    await outbreaks.run(db)
    return await _listing(db, admin)


@router.post("/{cluster_id}/acknowledge", response_model=ClusterOut)
async def acknowledge(
    cluster_id: uuid.UUID, request: Request, user: User = Depends(viewer), db: AsyncSession = Depends(get_session)
) -> ClusterOut:
    cluster = await db.get(CommunityData, cluster_id, with_for_update=True)
    if cluster is None or (user.role == UserRole.phc_worker and str(user.phc_id) not in cluster.phc_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    if cluster.acknowledged_at is None:
        cluster.acknowledged_at = outbreaks.now_utc()
        cluster.acknowledged_by = user.id
        db.add(AuditLog(user_id=user.id, action="acknowledge_outbreak", entity="community_data", entity_id=cluster.id,
                        ip_address=sessions.client_ip(request) or "unknown"))
        await db.commit()
    return await _out(db, cluster, user)
