"""Add the population check to readings scored before it existed (migration 0012).

    python -m app.seeds.backfill_population

Only fills processed_data.population where it is NULL; the flag and score are not
touched. Safe to run again.
"""

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HealthRecord, ProcessedData
from app.services import population

from ._common import run


async def seed(session: AsyncSession) -> None:
    if population.model_info() is None:
        raise SystemExit("The population model did not load; see the log above.")
    rows = await session.execute(
        select(ProcessedData, HealthRecord.vitals)
        .join(HealthRecord, HealthRecord.id == ProcessedData.health_record_id)
        .where(ProcessedData.population.is_(None))
    )
    filled = skipped = 0
    for processed, vitals in rows.all():
        check = population.check(vitals)
        if check is None:
            skipped += 1
            continue
        processed.population = asdict(check)
        filled += 1
    print(f"Population check added to {filled} readings; {skipped} have no heart rate or breathing rate.")


if __name__ == "__main__":
    run(seed)
