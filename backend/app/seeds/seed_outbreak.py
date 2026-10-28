"""A demo fever cluster in one locality, then a clustering run so the outbreak pages have something to show.

    python -m app.seeds.seed_outbreak [--area Mandaveli]

Run after seed_demo_catchment. Adds fever readings over the last four days for every
demo citizen in the area who allowed community monitoring. Idempotent: if the cluster
readings are already there (fever-only readings with just temperature and heart rate),
nothing is added again.
"""

import argparse
import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HealthRecord, User
from app.models.enums import UserRole
from app.services import outbreaks
from app.services.consent import counts_in_community

from ._common import add_scored_reading, run, utcnow

CLUSTER_KEYS = {"temperature_c", "heart_rate"}


async def seed_area(session: AsyncSession, area: str) -> int:
    """Add the cluster readings; returns how many readings were added (0 if already seeded)."""
    people = (
        await session.scalars(
            select(User).where(
                User.role == UserRole.user, User.area == area, User.geo_lat.is_not(None), counts_in_community(User.id)
            ).order_by(User.email)
        )
    ).all()
    if len(people) < 3:
        raise SystemExit(f"Need at least 3 consenting citizens with a location in {area}; found {len(people)}.")
    existing = await session.scalars(select(HealthRecord.vitals).where(HealthRecord.user_id.in_([p.id for p in people])))
    if any(set(v) == CLUSTER_KEYS for v in existing):
        print(f"Fever cluster in {area} already seeded, skipping.")
        return 0
    rng = random.Random(7)
    now = utcnow()
    added = 0
    for person in people:
        for day in rng.sample(range(4), 2):
            vitals = {"temperature_c": round(rng.uniform(38.1, 39.0), 1), "heart_rate": rng.randint(92, 108)}
            symptoms = rng.sample(["fever", "body ache", "headache", "fatigue"], 2)
            if "fever" not in symptoms:
                symptoms[0] = "fever"
            await add_scored_reading(session, person, vitals, now - timedelta(days=day, hours=rng.randint(1, 8)), symptoms)
            added += 1
    await session.commit()
    clusters = await outbreaks.run(session)
    print(f"Fever readings added for {len(people)} citizens in {area}.")
    for c in clusters:
        print(f"  {c.syndrome} in {c.region}: {c.cases} people, expected {c.expected}, p={c.p_value:.4f}, outbreak={c.outbreak_flag}")
    return added


def main(area: str):
    async def seed(session: AsyncSession) -> None:
        await seed_area(session, area)

    run(seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="Mandaveli")
    main(parser.parse_args().area)
