"""Alerts: a person's own notifications plus community advisories, and the PHC badge."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.views import alert_out
from app.core.dependencies import require_any_verified
from app.db.session import get_session
from app.models import Advisory, Alert, ProcessedData, User
from app.schemas.health import AlertsOut, MarkRead, UnreadCount, Updated
from app.services.catchment import catchment_ids, require_catchment_worker
from app.services.visit_state import now_utc

from .advisories import advisory_out, is_active, targeting

router = APIRouter(prefix="/alerts", tags=["alerts"])
phc_router = APIRouter(prefix="/phc-alerts", tags=["phc"])

ADVISORY_LIMIT = 20


async def _unread(db: AsyncSession, user: User) -> int:
    return await db.scalar(select(func.count()).where(Alert.user_id == user.id, Alert.is_read.is_(False))) or 0


@router.get("", response_model=AlertsOut)
async def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = False,
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> AlertsOut:
    own = select(Alert).where(Alert.user_id == user.id)
    if unread_only:
        own = own.where(Alert.is_read.is_(False))
    alerts = (await db.scalars(own.order_by(Alert.created_at.desc()).limit(limit))).all()
    advisories = (
        await db.scalars(
            select(Advisory)
            .where(targeting(user), Advisory.created_at >= now_utc() - timedelta(days=365))
            .order_by(is_active(now_utc()).desc())
            .order_by(Advisory.created_at.desc())
            .limit(ADVISORY_LIMIT)
        )
    ).all()
    return AlertsOut(
        alerts=[alert_out(a) for a in alerts],
        advisories=[await advisory_out(db, a) for a in advisories],
        unread=await _unread(db, user),
    )


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)) -> UnreadCount:
    return UnreadCount(unread=await _unread(db, user))


@router.post("/mark-read", response_model=Updated)
async def mark_read(
    data: MarkRead, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> Updated:
    query = update(Alert).where(Alert.user_id == user.id, Alert.is_read.is_(False)).values(is_read=True)
    if data.ids is not None:
        query = query.where(Alert.id.in_(data.ids))
    result = await db.execute(query)
    await db.commit()
    return Updated(updated=result.rowcount or 0)


class PhcBadge(UnreadCount):
    citizens_flagged: int


@phc_router.get("/unread-count", response_model=PhcBadge)
async def phc_unread_count(
    worker: User = Depends(require_catchment_worker), db: AsyncSession = Depends(get_session)
) -> PhcBadge:
    flagged = await db.scalar(
        select(func.count(func.distinct(ProcessedData.user_id))).where(
            ProcessedData.user_id.in_(catchment_ids(worker)),
            ProcessedData.is_anomaly.is_(True),
            ProcessedData.resolution.is_(None),
        )
    )
    return PhcBadge(unread=await _unread(db, worker), citizens_flagged=flagged or 0)
