"""Outbreak signals from the latest clustering run (services/outbreaks.py)."""

import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import cast, func, select
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
    current: bool
    seen_at: datetime
    reasons: list[str]
    feedback: str | None
    feedback_note: str | None
    feedback_at: datetime | None
    feedback_by: str | None


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["confirmed", "false_alarm", "unsure"]
    note: str | None = Field(default=None, max_length=1000)


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


NAMES = {"febrile": "fever", "respiratory": "breathing", "gastrointestinal": "stomach and gut"}


def reasons(c: CommunityData) -> list[str]:
    """Why the clustering flagged this, in plain words with the real numbers."""
    p, w, base = outbreaks.PARAMS, outbreaks.WINDOW.days, outbreaks.BASELINE.days
    days = max(1, round((c.last_onset - c.first_onset).total_seconds() / 86400) + 1)
    before = round(c.expected * (base / w)) if c.expected > outbreaks.EXPECTED_FLOOR else 0
    nearby = round(c.cases / c.prevalence_score) if c.prevalence_score else None
    symptoms = ", ".join(f"{s} {n}" for s, n in list(c.symptom_cluster.get("symptoms", {}).items())[:5])
    verdict = (
        f"p = {c.p_value:.4f} is below the {outbreaks.SIGNIFICANCE} threshold, so this is flagged as a possible outbreak."
        if c.outbreak_flag
        else f"p = {c.p_value:.4f} is above the {outbreaks.SIGNIFICANCE} threshold, so it is only on watch."
    )
    out = [
        f"{c.cases} different people reported {NAMES.get(c.syndrome, c.syndrome)} symptoms within {c.radius_km:.1f} km of each other "
        f"over {days} day{'s' if days != 1 else ''}. A cluster needs at least {p.min_people} people within {p.radius_km} km, "
        f"where each day apart counts as {p.km_per_day} km.",
        f"In the {base} days before, {before} {'person' if before == 1 else 'people'} had the same symptoms around here, "
        f"so about {c.expected:.1f} would be expected in {w} days"
        + (" (the minimum assumed when there is no history)." if before == 0 else "."),
        f"Seeing {c.cases} or more when about {c.expected:.1f} are expected: {verdict}",
    ]
    if symptoms:
        out.append(f"Symptoms reported: {symptoms}.")
    if nearby:
        out.append(f"That is {round(c.prevalence_score * 100)}% of the {nearby} consenting residents living within reach.")
    return out


async def _out(db: AsyncSession, c: CommunityData, user: User, current: bool = True) -> ClusterOut:
    who = await db.get(User, c.acknowledged_by) if c.acknowledged_by else None
    reviewer = await db.get(User, c.feedback_by) if c.feedback_by else None
    advisory = await db.scalar(select(Advisory.id).where(Advisory.cluster_id == c.id).limit(1))
    return ClusterOut(
        id=c.id, syndrome=c.syndrome, region=c.region, district=c.district, cases=c.cases, expected=c.expected,
        p_value=c.p_value, outbreak=c.outbreak_flag, prevalence=c.prevalence_score,
        symptoms=c.symptom_cluster.get("symptoms", {}), localities=c.symptom_cluster.get("localities", {}),
        centre_lat=c.centre_lat, centre_lng=c.centre_lng, radius_km=c.radius_km,
        first_onset=c.first_onset, last_onset=c.last_onset, acknowledged_at=c.acknowledged_at,
        acknowledged_by=who.name if who else None, advisory_id=advisory,
        yours=user.phc_id is not None and str(user.phc_id) in c.phc_ids,
        current=current, seen_at=c.window_end, reasons=reasons(c),
        feedback=c.feedback, feedback_note=c.feedback_note, feedback_at=c.feedback_at,
        feedback_by=reviewer.name if reviewer else None,
    )


def _scoped(query, user: User):
    if user.role == UserRole.phc_worker:
        return query.where(cast(CommunityData.phc_ids, JSONB).contains([str(user.phc_id)]))
    if user.district:
        return query.where(func.lower(CommunityData.district) == user.district.lower())
    return query


async def _listing(db: AsyncSession, user: User, days: int = 0) -> ClustersOut:
    """days=0: the latest run. Otherwise every cluster seen in that many days, each once (its latest sighting)."""
    last = await outbreaks.last_run_at(db)
    items: list[ClusterOut] = []
    if last is not None:
        query = _scoped(select(CommunityData), user)
        query = query.where(CommunityData.window_end == last) if not days else query.where(CommunityData.window_end >= last - timedelta(days=days))
        rows = (await db.scalars(query.order_by(CommunityData.window_end.desc(), CommunityData.p_value))).all()
        kept: list[CommunityData] = []
        for c in rows:
            if not any(outbreaks.same_cluster(c, k) for k in kept):
                kept.append(c)
        kept.sort(key=lambda c: (c.window_end != last, not c.outbreak_flag, c.p_value))
        items = [await _out(db, c, user, current=c.window_end == last) for c in kept]
    return ClustersOut(
        items=items,
        last_run_at=last,
        window_days=outbreaks.WINDOW.days,
        radius_km=outbreaks.PARAMS.radius_km,
        min_people=outbreaks.PARAMS.min_people,
    )


@router.get("", response_model=ClustersOut)
async def current_clusters(
    days: int = Query(0, ge=0, le=180), user: User = Depends(viewer), db: AsyncSession = Depends(get_session)
) -> ClustersOut:
    """Admins see their district's clusters; a health worker sees those that include their centre's citizens."""
    return await _listing(db, user, days)


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
    return await _out(db, cluster, user, current=cluster.window_end == await outbreaks.last_run_at(db))


@router.post("/{cluster_id}/feedback", response_model=ClusterOut)
async def review(
    cluster_id: uuid.UUID, data: FeedbackIn, request: Request, user: User = Depends(viewer), db: AsyncSession = Depends(get_session)
) -> ClusterOut:
    """Was the signal a real outbreak? Kept to track how often the clustering is right."""
    cluster = await db.get(CommunityData, cluster_id, with_for_update=True)
    if cluster is None or (user.role == UserRole.phc_worker and str(user.phc_id) not in cluster.phc_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    cluster.feedback, cluster.feedback_note = data.verdict, (data.note or "").strip() or None
    cluster.feedback_at, cluster.feedback_by = outbreaks.now_utc(), user.id
    db.add(AuditLog(user_id=user.id, action="review_outbreak", entity="community_data", entity_id=cluster.id,
                    ip_address=sessions.client_ip(request) or "unknown"))
    await db.commit()
    last = await outbreaks.last_run_at(db)
    return await _out(db, cluster, user, current=cluster.window_end == last)
