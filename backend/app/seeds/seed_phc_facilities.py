"""Seed the PHC registry with placeholder (non-authoritative) facilities.

    python -m app.seeds.seed_phc_facilities

Idempotent: rows are matched on facility_code and updated in place.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValidPhcFacility
from app.services.phc_registry import normalise_facility_name

from ._common import run

# Placeholder rows for demos. Codes are invented; replace with the official
# registry before production (is_placeholder marks them as non-authoritative).
FACILITIES = [
    ("TN-CHN-PHC-001", "Mylapore PHC", "Chennai", "Mylapore", 13.0339, 80.2619),
    ("TN-CHN-PHC-002", "Adyar PHC", "Chennai", "Adyar", 13.0012, 80.2565),
    ("TN-CHN-PHC-003", "Ambattur PHC", "Chennai", "Ambattur", 13.1143, 80.1548),
    ("TN-CHN-PHC-004", "Perambur PHC", "Chennai", "Perambur", 13.1187, 80.2332),
    ("TN-CHN-PHC-005", "Velachery PHC", "Chennai", "Velachery", 12.9791, 80.2181),
    ("TN-CGL-PHC-001", "Tambaram PHC", "Chengalpattu", "Tambaram", 12.9249, 80.1000),
    ("TN-CGL-PHC-002", "Guduvancheri PHC", "Chengalpattu", "Kattankulathur", 12.8456, 80.0598),
    ("TN-TVL-PHC-001", "Poonamallee PHC", "Tiruvallur", "Poonamallee", 13.0473, 80.0945),
    ("TN-TVL-PHC-002", "Avadi PHC", "Tiruvallur", "Villivakkam", 13.1067, 80.1010),
    ("TN-KPM-PHC-001", "Sriperumbudur PHC", "Kanchipuram", "Sriperumbudur", 12.9675, 79.9419),
]


async def seed(session: AsyncSession) -> None:
    created = updated = 0
    for code, name, district, block, lat, lng in FACILITIES:
        facility = await session.scalar(select(ValidPhcFacility).where(ValidPhcFacility.facility_code == code))
        if facility is None:
            facility = ValidPhcFacility(facility_code=code)
            session.add(facility)
            created += 1
        else:
            updated += 1
        facility.name = name
        facility.normalised_name = normalise_facility_name(name)
        facility.district = district
        facility.state = "Tamil Nadu"
        facility.block = block
        facility.latitude = lat
        facility.longitude = lng
        facility.is_active = True
        facility.is_placeholder = True
    print(f"PHC facilities: {created} created, {updated} updated")


if __name__ == "__main__":
    run(seed)
