"""A demo fever cluster in one locality, then a clustering run so the outbreak pages have something to show.

    python -m app.seeds.seed_outbreak [--area Mandaveli]

Run after seed_demo_catchment. Adds fever readings over the last four days for every
demo citizen in the area who allowed community monitoring.
"""

import argparse
import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.enums import UserRole
from app.services import outbreaks
from app.services.consent import counts_in_community

from ._common import add_scored_reading, run, utcnow


def main(area: str):
    async def seed(session: AsyncSession) -> None:
        people = (
            await session.scalars(
                select(User).where(
                    User.role == UserRole.user, User.area == area, User.geo_lat.is_not(None), counts_in_community(User.id)
                )
            )
        ).all()
        if len(people) < 3:
            raise SystemExit(f"Need at least 3 consenting citizens with a location in {area}; found {len(people)}.")
        rng = random.Random(7)
        now = utcnow()
        for person in people:
            for day in rng.sample(range(4), 2):
                vitals = {"temperature_c": round(rng.uniform(38.1, 39.0), 1), "heart_rate": rng.randint(92, 108)}
                symptoms = rng.sample(["fever", "body ache", "headache", "fatigue"], 2)
                if "fever" not in symptoms:
                    symptoms[0] = "fever"
                await add_scored_reading(session, person, vitals, now - timedelta(days=day, hours=rng.randint(1, 8)), symptoms)
        await session.commit()
        clusters = await outbreaks.run(session)
        print(f"Fever readings added for {len(people)} citizens in {area}.")
        for c in clusters:
            print(f"  {c.syndrome} in {c.region}: {c.cases} people, expected {c.expected}, p={c.p_value:.4f}, outbreak={c.outbreak_flag}")

    run(seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", default="Mandaveli")
    main(parser.parse_args().area)
