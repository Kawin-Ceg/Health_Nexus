"""Seed the PHC registry for Tamil Nadu.

    python -m app.seeds.seed_phc_facilities

Every district in the state, each with primary health centres named after real
towns and blocks. Rows are marked is_placeholder = True: the districts are real,
the centre list stands in for the official registry (see data/tamil_nadu.py).

Idempotent: rows are matched on facility_code and updated in place, so running
it again after editing the dataset refreshes names without creating duplicates.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValidPhcFacility
from app.services.phc_registry import normalise_facility_name

from ._common import run
from .data import tamil_nadu


async def seed(session: AsyncSession) -> None:
    rows = tamil_nadu.facilities()
    codes = [r["facility_code"] for r in rows]
    if len(set(codes)) != len(codes):
        raise SystemExit("facility codes are not unique; fix data/tamil_nadu.py")

    existing = {
        f.facility_code: f
        for f in await session.scalars(select(ValidPhcFacility).where(ValidPhcFacility.facility_code.in_(codes)))
    }
    created = updated = 0
    for row in rows:
        facility = existing.get(row["facility_code"])
        if facility is None:
            facility = ValidPhcFacility(facility_code=row["facility_code"])
            session.add(facility)
            created += 1
        else:
            updated += 1
        facility.name = row["name"]
        facility.normalised_name = normalise_facility_name(row["name"])
        facility.district = row["district"]
        facility.state = row["state"]
        facility.block = row["block"]
        facility.latitude = row["latitude"]
        facility.longitude = row["longitude"]
        facility.is_active = True
        facility.is_placeholder = True

    print(
        f"PHC registry: {created} created, {updated} updated "
        f"({len(rows)} centres across {len(tamil_nadu.DISTRICTS)} districts in {tamil_nadu.STATE})"
    )


if __name__ == "__main__":
    run(seed)
