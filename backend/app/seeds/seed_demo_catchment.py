"""Fill the demo worker's catchment: 27 citizens, 14 days of daily readings, some flagged.

    python -m app.seeds.seed_demo_catchment

Run after seed_phc_worker. Citizens join the worker's facility (same phc_id),
so they appear in that worker's catchment. Deterministic (fixed random seed)
and idempotent (existing demo emails are skipped).
"""

import random
import sys
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import User, UserProfile, ValidPhcFacility
from app.models.enums import BloodGroup, ConsentType, Gender, UserRole

from ._common import add_scored_reading, grant_consents, password_or_generated, run, user_by_email, utcnow

CITIZEN_COUNT = 27
DAYS = 14
EMAIL_TEMPLATE = "citizen{:02d}@example.com"

NAMES = [
    "Arun Kumar", "Priya Sundaram", "Meena Krishnan", "Suresh Babu", "Lakshmi Narayanan",
    "Karthik Rajan", "Divya Ramesh", "Vijay Anand", "Revathi Subramanian", "Ganesh Murugan",
    "Anitha Selvam", "Rajesh Pandian", "Kalpana Venkat", "Senthil Nathan", "Bhavani Shankar",
    "Mohan Das", "Saranya Gopal", "Prakash Iyer", "Deepa Mani", "Hari Prasad",
    "Janani Balaji", "Ramesh Chandran", "Uma Maheswari", "Dinesh Kannan", "Geetha Rani",
    "Naveen Sekar", "Shalini Arumugam",
]
AREAS = ["Mylapore", "Mandaveli", "Alwarpet", "Royapettah", "Santhome", "Luz"]

FLAGGED = {
    2: "fever",
    5: "hypertension",
    9: "low_spo2",
    13: "fever",
    17: "hypertension",
    21: "hyperglycaemia",
    24: "fever",
}


def baseline(rng: random.Random) -> dict[str, float]:
    return {
        "systolic": rng.uniform(104, 118),
        "diastolic": rng.uniform(66, 78),
        "heart_rate": rng.uniform(64, 84),
        "temperature_c": rng.uniform(36.4, 36.9),
        "spo2": rng.uniform(96.5, 99),
        "respiratory_rate": rng.uniform(13, 17),
        "glucose_mg_dl": rng.uniform(78, 96),
    }


def daily_reading(rng: random.Random, base: dict[str, float], episode: str | None) -> tuple[dict[str, float], list[str]]:
    v = {
        "systolic": base["systolic"] + rng.gauss(0, 3),
        "diastolic": base["diastolic"] + rng.gauss(0, 2),
        "heart_rate": base["heart_rate"] + rng.gauss(0, 3),
        "temperature_c": base["temperature_c"] + rng.gauss(0, 0.1),
        "spo2": min(100.0, base["spo2"] + rng.gauss(0, 0.4)),
        "respiratory_rate": base["respiratory_rate"] + rng.gauss(0, 0.8),
        "glucose_mg_dl": base["glucose_mg_dl"] + rng.gauss(0, 4),
    }
    symptoms: list[str] = []
    if episode == "fever":
        v["temperature_c"] = rng.uniform(38.6, 39.4)
        v["heart_rate"] += rng.uniform(18, 28)
        symptoms = ["fever", "body ache"]
    elif episode == "hypertension":
        v["systolic"] = rng.uniform(158, 176)
        v["diastolic"] = rng.uniform(96, 106)
        symptoms = ["headache"]
    elif episode == "low_spo2":
        v["spo2"] = rng.uniform(88, 91)
        v["respiratory_rate"] = rng.uniform(23, 27)
        symptoms = ["breathlessness"]
    elif episode == "hyperglycaemia":
        v["glucose_mg_dl"] = rng.uniform(190, 240)
        symptoms = ["thirst", "fatigue"]
    return {k: round(x, 1) for k, x in v.items()}, symptoms


async def seed(session: AsyncSession) -> None:
    settings = get_settings()
    worker = await user_by_email(session, settings.PHC_WORKER_EMAIL)
    if worker is None or worker.phc_id is None:
        sys.exit("Run seed_phc_worker first: the demo catchment hangs off that worker's facility.")
    facility = await session.get(ValidPhcFacility, worker.phc_id)
    assert facility is not None and facility.latitude is not None and facility.longitude is not None

    missing = [i for i in range(CITIZEN_COUNT) if not await user_by_email(session, EMAIL_TEMPLATE.format(i + 1))]
    if not missing:
        print(f"Demo catchment at {facility.name}: all {CITIZEN_COUNT} citizens already exist, skipping")
        return

    password = password_or_generated(settings.DEMO_CITIZEN_PASSWORD, "Demo citizens (shared)")
    hashed = hash_password(password)
    rng = random.Random(20260920)
    now = utcnow().replace(minute=0, second=0, microsecond=0)
    created = flagged_readings = 0

    for i in range(CITIZEN_COUNT):
        email = EMAIL_TEMPLATE.format(i + 1)
        if i not in missing:
            continue
        joined = now - timedelta(days=DAYS + rng.randint(5, 60))
        citizen = User(
            name=NAMES[i],
            email=email,
            hashed_password=hashed,
            role=UserRole.user,
            consent=True,
            profile_completed=True,
            is_verified=True,
            email_verified=True,
            verified_at=joined,
            phc_id=facility.id,
            district=facility.district,
            state=facility.state,
            phone=f"+91 94440 {10000 + i * 137:05d}",
            pincode="600004",
            area=AREAS[i % len(AREAS)],
            geo_lat=round(facility.latitude + rng.uniform(-0.012, 0.012), 6),
            geo_lng=round(facility.longitude + rng.uniform(-0.012, 0.012), 6),
            created_at=joined,
        )
        session.add(citizen)
        await session.flush()

        session.add(
            UserProfile(
                user_id=citizen.id,
                age=rng.randint(22, 74),
                gender=Gender.female if i % 2 else Gender.male,
                height_cm=round(rng.uniform(150, 182), 1),
                weight_kg=round(rng.uniform(48, 92), 1),
                blood_group=rng.choice(list(BloodGroup)),
                existing_conditions=["hypertension"] if FLAGGED.get(i) == "hypertension" else [],
                has_smartwatch=rng.random() < 0.4,
                permission_health_tracking=True,
                created_at=joined,
                updated_at=joined,
            )
        )
        await grant_consents(
            session,
            citizen,
            [ConsentType.health_tracking, ConsentType.community_surveillance, ConsentType.phc_worker_access],
            joined,
        )

        base = baseline(rng)
        episode = FLAGGED.get(i)
        for day in range(DAYS):
            measured_at = now - timedelta(days=DAYS - 1 - day, hours=rng.randint(1, 10))
            in_episode = episode if episode and day >= DAYS - 3 else None
            vitals, symptoms = daily_reading(rng, base, in_episode)
            processed = await add_scored_reading(session, citizen, vitals, measured_at, symptoms)
            flagged_readings += processed.is_anomaly
        created += 1

    print(
        f"Demo catchment at {facility.name}: {created} citizens created "
        f"({CITIZEN_COUNT - created} already existed), {flagged_readings} flagged readings"
    )


if __name__ == "__main__":
    run(seed)
