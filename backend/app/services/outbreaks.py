"""Outbreak signals: space-time DBSCAN over symptomatic readings (model/healthnexus_ml/clustering.py).

A run looks at the last WINDOW of readings from citizens who allowed community
monitoring, per syndrome. Each cluster is compared with the same area's previous
BASELINE: if that many people would be unlikely by chance (Poisson, p < SIGNIFICANCE)
it is flagged as a possible outbreak. Every run is stored; the latest is what pages show.
"""

import asyncio
import logging
import uuid
from collections import Counter
from datetime import datetime, timedelta

from healthnexus_ml.clustering import Case, Params, find_clusters, haversine_km, poisson_tail
from healthnexus_ml.features import SYNDROMES, syndromes
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AuditLog, CommunityData, HealthRecord, User
from app.models.enums import UserRole

from .consent import counts_in_community
from .localities import locality_of
from .visit_state import now_utc

log = logging.getLogger(__name__)

WINDOW = timedelta(days=14)
BASELINE = timedelta(days=56)
SIGNIFICANCE = 0.01
EXPECTED_FLOOR = 0.5
KEEP_RUNS_FOR = timedelta(days=180)
RUN_EVERY = timedelta(hours=6)
PARAMS = Params()
RUN_ACTION = "outbreak_clustering_run"


def _case_symptoms(reported: list[str], vitals: dict[str, float], syndrome: str) -> tuple[str, ...]:
    signs = tuple(s.lower() for s in reported if s.lower() in SYNDROMES[syndrome])
    if not signs and syndrome == "febrile":
        return ("measured fever",)
    if not signs and syndrome == "respiratory":
        return ("low oxygen",)
    return signs


async def run(session: AsyncSession, now: datetime | None = None) -> list[CommunityData]:
    now = now or now_utc()
    start = now - WINDOW
    lat = func.coalesce(HealthRecord.geo_lat, User.geo_lat)
    lng = func.coalesce(HealthRecord.geo_lng, User.geo_lng)
    community = (User.role == UserRole.user, User.is_active.is_(True), counts_in_community(User.id))
    rows = await session.execute(
        select(HealthRecord.user_id, HealthRecord.timestamp, HealthRecord.symptoms, HealthRecord.vitals, lat, lng)
        .join(User, User.id == HealthRecord.user_id)
        .where(*community, lat.is_not(None), HealthRecord.timestamp >= start - BASELINE, HealthRecord.timestamp <= now)
    )
    current: dict[str, list[Case]] = {s: [] for s in SYNDROMES}
    earlier: dict[str, list[tuple[uuid.UUID, float, float]]] = {s: [] for s in SYNDROMES}
    for user_id, at, symptoms, vitals, y, x in rows.all():
        for syndrome in syndromes(symptoms or [], vitals or {}):
            if at >= start:
                day = (at - start).total_seconds() / 86400
                current[syndrome].append(Case(user_id, y, x, day, _case_symptoms(symptoms or [], vitals or {}, syndrome)))
            else:
                earlier[syndrome].append((user_id, y, x))

    people = {
        u.id: u
        for u in await session.scalars(select(User).where(*community, User.geo_lat.is_not(None)))
    }
    found: list[CommunityData] = []
    for syndrome, cases in current.items():
        for cluster in find_clusters(cases, PARAMS):
            reach = cluster.radius_km + PARAMS.radius_km
            centre = (cluster.centre_lat, cluster.centre_lng)
            before = {p for p, y, x in earlier[syndrome] if haversine_km(*centre, y, x) <= reach}
            expected = max(len(before) / (BASELINE / WINDOW), EXPECTED_FLOOR)
            p_value = poisson_tail(cluster.people, expected)
            living_near = sum(1 for u in people.values() if haversine_km(*centre, u.geo_lat, u.geo_lng) <= reach)
            members = [people[c.person] for c in cluster.cases if c.person in people]
            localities = Counter(locality_of(m.area) for m in members)
            districts = Counter(m.district for m in members if m.district)
            found.append(CommunityData(
                region=localities.most_common(1)[0][0] if localities else "Unspecified",
                syndrome=syndrome,
                cases=cluster.people,
                expected=round(expected, 2),
                p_value=p_value,
                symptom_cluster={"symptoms": cluster.symptoms, "localities": dict(localities)},
                prevalence_score=round(cluster.people / max(living_near, cluster.people), 3),
                outbreak_flag=p_value < SIGNIFICANCE,
                centre_lat=round(cluster.centre_lat, 3),
                centre_lng=round(cluster.centre_lng, 3),
                radius_km=round(cluster.radius_km, 2),
                district=districts.most_common(1)[0][0] if districts else None,
                phc_ids=sorted({str(m.phc_id) for m in members if m.phc_id}),
                first_onset=start + timedelta(days=cluster.first_day),
                last_onset=start + timedelta(days=cluster.last_day),
                window_start=start,
                window_end=now,
            ))
    await _carry_forward(session, found)
    session.add_all(found)
    session.add(AuditLog(user_id=None, action=RUN_ACTION, entity="community_data", entity_id=None, ip_address="system",
                         created_at=now))
    await session.execute(delete(CommunityData).where(CommunityData.window_end < now - KEEP_RUNS_FOR))
    await session.commit()
    return found


def same_cluster(a: CommunityData, b: CommunityData) -> bool:
    """The same group of cases seen by two runs: same syndrome, overlapping place, onsets within two days."""
    return (
        a.syndrome == b.syndrome
        and haversine_km(a.centre_lat, a.centre_lng, b.centre_lat, b.centre_lng) <= max(a.radius_km, b.radius_km) + PARAMS.radius_km
        and abs((a.first_onset - b.first_onset).total_seconds()) <= 2 * 86400
    )


async def _carry_forward(session: AsyncSession, found: list[CommunityData]) -> None:
    last = await last_run_at(session)
    if last is None:
        return
    earlier = (await session.scalars(select(CommunityData).where(CommunityData.window_end == last))).all()
    for new in found:
        old = next((o for o in earlier if same_cluster(new, o)), None)
        if old is None:
            continue
        new.acknowledged_at, new.acknowledged_by = old.acknowledged_at, old.acknowledged_by
        new.feedback, new.feedback_note, new.feedback_at, new.feedback_by = old.feedback, old.feedback_note, old.feedback_at, old.feedback_by


async def last_run_at(session: AsyncSession) -> datetime | None:
    return await session.scalar(select(func.max(AuditLog.created_at)).where(AuditLog.action == RUN_ACTION))


async def run_forever(maker: async_sessionmaker[AsyncSession]) -> None:
    while True:
        try:
            async with maker() as session:
                last = await last_run_at(session)
                if last is None or now_utc() - last >= RUN_EVERY:
                    clusters = await run(session)
                    log.info("Outbreak clustering: %d clusters, %d flagged", len(clusters), sum(c.outbreak_flag for c in clusters))
        except Exception:
            log.exception("Outbreak clustering failed")
        await asyncio.sleep(timedelta(minutes=30).total_seconds())
