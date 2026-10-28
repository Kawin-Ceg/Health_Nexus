"""One command for a complete, reproducible demo database.

    python -m app.seeds.seed_demo

Run from backend/ after `alembic upgrade head`. Needs DEMO_MODE=true and DEMO_PASSWORD
in backend/.env (see .env.example); it refuses to run otherwise, so demo accounts never
appear in a database by accident.

Every account the demo owns gets DEMO_PASSWORD, so every teammate who runs this gets the
same logins. Each step is idempotent: accounts are matched on fixed emails, and existing
records are left alone, so running it again creates nothing new. Records that are not
part of the demo are never touched. All people and readings are synthetic.

Dates are relative to the day you run it (readings cover the days before the run).
"""

import asyncio
import os
import random
import sys
from collections.abc import Awaitable, Callable
from datetime import timedelta

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import (
    Advisory,
    Alert,
    ChatSession,
    Concern,
    HealthRecord,
    PhcApplication,
    ProcessedData,
    ScheduledVisit,
    User,
    UserProfile,
    ValidPhcFacility,
)
from app.models.enums import (
    AlertSeverity,
    AlertType,
    BloodGroup,
    ConsentType,
    FlagResolution,
    Gender,
    UserRole,
    VisitStatus,
)
from app.services.reminders import MESSAGE as REMINDER_MESSAGE

from . import (
    seed_admin,
    seed_admin_workflow,
    seed_citizen,
    seed_complaints,
    seed_demo_catchment,
    seed_directory,
    seed_outbreak,
    seed_phc_facilities,
    seed_phc_worker,
)
from ._common import add_scored_reading, grant_consents, user_by_email, utcnow

ADMIN_EMAIL = "admin.demo@example.com"
WORKER_EMAIL = "phc.worker@example.com"
SECOND_WORKER_EMAIL = "tn-chn-phc-002@phc.example.com"
SECOND_FACILITY_CODE = "TN-CHN-PHC-002"

ADYAR = [
    ("adyar.stable@example.com", "Selvi Murugan", "stable", 34, Gender.female, "Besant Nagar"),
    ("adyar.bp@example.com", "Murali Krishnan", "bp", 58, Gender.male, "Kasturba Nagar"),
    ("adyar.glucose@example.com", "Balaji Natarajan", "glucose", 49, Gender.male, "Gandhi Nagar"),
    ("adyar.heartrate@example.com", "Kavya Srinivasan", "heartrate", 41, Gender.female, "Besant Nagar"),
    ("adyar.new@example.com", "Farhan Ali", "new", 27, Gender.male, "Kasturba Nagar"),
]

OWNED_EMAILS = [
    ADMIN_EMAIL,
    WORKER_EMAIL,
    seed_citizen.EMAIL,
    *[seed_demo_catchment.EMAIL_TEMPLATE.format(i + 1) for i in range(seed_demo_catchment.CITIZEN_COUNT)],
    *[a[1] for a in seed_admin_workflow.APPLICANTS],
    *[a[0] for a in ADYAR],
]
OWNED_DOMAINS = ("@phc.example.com", "@admin.example.com")


def fail(message: str) -> None:
    print(f"\nDemo seed stopped: {message}", file=sys.stderr)
    sys.exit(1)


def check_config() -> str:
    settings = get_settings()
    if not settings.DEMO_MODE:
        fail("DEMO_MODE is not true. Demo accounts are off by default; set DEMO_MODE=true in backend/.env "
             "for a local demo database only, never in production.")
    password = settings.DEMO_PASSWORD or ""
    if len(password) < 10:
        fail("set DEMO_PASSWORD in backend/.env (at least 10 characters). Use the value from .env.example "
             "so every teammate gets the same logins.")
    settings.ADMIN_EMAIL = ADMIN_EMAIL
    settings.ADMIN_NAME = "Demo Admin"
    settings.ADMIN_PASSWORD = password
    settings.PHC_WORKER_EMAIL = WORKER_EMAIL
    settings.PHC_WORKER_PASSWORD = password
    settings.DEMO_CITIZEN_PASSWORD = password
    os.environ["SEED_DEMO_PASSWORD"] = password
    return password


async def check_schema() -> None:
    head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    try:
        async with engine.connect() as conn:
            current = (await conn.execute(text("select version_num from alembic_version"))).scalar()
    except OperationalError as e:
        fail(f"cannot reach the database in DATABASE_URL ({e.orig.__class__.__name__}). Is PostgreSQL running, and does the database exist?")
    except Exception:
        fail("the database has no schema yet. Run `alembic upgrade head` first.")
    if current != head:
        fail(f"the database is at migration {current}, but the code expects {head}. Run `alembic upgrade head` first.")
    print(f"Schema is at the latest migration ({head}).")


TABLES: list[tuple[str, Callable]] = [
    ("Health centres", lambda: select(func.count()).select_from(ValidPhcFacility)),
    ("Admins", lambda: select(func.count()).select_from(User).where(User.role == UserRole.admin)),
    ("PHC workers", lambda: select(func.count()).select_from(User).where(User.role == UserRole.phc_worker)),
    ("Pending worker applicants", lambda: select(func.count()).select_from(User).where(User.role == UserRole.pending_phc)),
    ("Citizens", lambda: select(func.count()).select_from(User).where(User.role == UserRole.user)),
    ("Readings", lambda: select(func.count()).select_from(HealthRecord)),
    ("Flagged readings", lambda: select(func.count()).select_from(ProcessedData).where(ProcessedData.is_anomaly.is_(True))),
    ("Visits", lambda: select(func.count()).select_from(ScheduledVisit)),
    ("Alerts and notifications", lambda: select(func.count()).select_from(Alert)),
    ("Concerns and complaints", lambda: select(func.count()).select_from(Concern)),
    ("Advisories", lambda: select(func.count()).select_from(Advisory)),
    ("Assistant chats", lambda: select(func.count()).select_from(ChatSession)),
    ("Worker applications", lambda: select(func.count()).select_from(PhcApplication)),
]


async def counts() -> dict[str, int]:
    async with SessionLocal() as s:
        return {name: (await s.execute(q())).scalar_one() for name, q in TABLES}


async def step(name: str, fn: Callable[[AsyncSession], Awaitable[object]]) -> None:
    print(f"\n== {name}")
    async with SessionLocal() as session:
        try:
            await fn(session)
            await session.commit()
        except BaseException:
            await session.rollback()
            print(f"   {name} failed; its changes were rolled back.", file=sys.stderr)
            raise


def adyar_reading(rng: random.Random, kind: str, day: int, days: int) -> tuple[dict[str, float], list[str]]:
    late = day >= days - 3
    v = {
        "systolic": rng.gauss(116, 3),
        "diastolic": rng.gauss(76, 2),
        "heart_rate": rng.gauss(72, 2.5),
        "temperature_c": rng.gauss(36.7, 0.1),
        "spo2": min(100.0, rng.gauss(97.8, 0.4)),
        "respiratory_rate": rng.gauss(15, 0.8),
        "glucose_mg_dl": rng.gauss(92, 4),
        "weight_kg": rng.gauss(64, 0.2),
    }
    symptoms: list[str] = []
    if kind == "bp":
        v["systolic"], v["diastolic"] = rng.gauss(128, 3), rng.gauss(82, 2)
        if late:
            v["systolic"], v["diastolic"] = rng.uniform(160, 172), rng.uniform(98, 106)
            symptoms = ["headache", "dizziness"]
    elif kind == "glucose":
        v["glucose_mg_dl"] = 104 + day * 1.4 + rng.gauss(0, 5)
        if late:
            v["glucose_mg_dl"] = rng.uniform(205, 235)
            symptoms = ["thirst"]
    elif kind == "heartrate":
        v["heart_rate"] = rng.gauss(68, 2) + max(0, day - (days - 8)) * 4.5
        if late:
            symptoms = ["palpitations"]
    return {k: round(x, 1) for k, x in v.items()}, symptoms


async def seed_second_catchment(session: AsyncSession) -> None:
    """Five scenario citizens at a second health centre, looked after by a second worker."""
    worker = await user_by_email(session, SECOND_WORKER_EMAIL)
    facility = await session.scalar(select(ValidPhcFacility).where(ValidPhcFacility.facility_code == SECOND_FACILITY_CODE))
    if worker is None or facility is None or worker.phc_id != facility.id:
        fail(f"{SECOND_WORKER_EMAIL} should be linked to {SECOND_FACILITY_CODE}; the directory step did not set it up.")
    hashed = hash_password(get_settings().DEMO_PASSWORD or "")
    now = utcnow().replace(minute=0, second=0, microsecond=0)
    created = skipped = 0
    for i, (email, name, kind, age, gender, area) in enumerate(ADYAR):
        if await user_by_email(session, email):
            skipped += 1
            continue
        rng = random.Random(f"adyar-{kind}")
        days = 3 if kind == "new" else 28
        joined = now - timedelta(days=days + 4)
        citizen = User(
            name=name, email=email, hashed_password=hashed, role=UserRole.user, consent=True, profile_completed=True,
            is_verified=True, email_verified=True, verified_at=joined, phc_id=facility.id, district=facility.district,
            state=facility.state, phone=f"+91 98840 {20100 + i * 211:05d}", pincode="600020", area=area,
            geo_lat=round((facility.latitude or 13.0) + rng.uniform(-0.01, 0.01), 6),
            geo_lng=round((facility.longitude or 80.25) + rng.uniform(-0.01, 0.01), 6), created_at=joined,
        )
        session.add(citizen)
        await session.flush()
        session.add(UserProfile(
            user_id=citizen.id, age=age, gender=gender, height_cm=round(rng.uniform(152, 178), 1), weight_kg=64.0,
            blood_group=list(BloodGroup)[i % len(BloodGroup)],
            existing_conditions={"bp": ["hypertension"], "glucose": ["prediabetes"]}.get(kind, []),
            has_smartwatch=kind != "new", permission_health_tracking=True, created_at=joined, updated_at=joined,
        ))
        await grant_consents(session, citizen, [ConsentType.health_tracking, ConsentType.community_surveillance,
                                                ConsentType.phc_worker_access], joined)
        flags: list[ProcessedData] = []
        for day in range(days):
            vitals, symptoms = adyar_reading(rng, kind, day, days)
            processed = await add_scored_reading(session, citizen, vitals, now - timedelta(days=days - 1 - day, hours=3 + i), symptoms)
            if processed.is_anomaly:
                flags.append(processed)

        if kind == "stable":
            session.add(ScheduledVisit(worker_id=worker.id, citizen_id=citizen.id, scheduled_for=now - timedelta(days=10),
                                       reason="Routine check-up", status=VisitStatus.completed, location=facility.name,
                                       created_at=now - timedelta(days=14)))
            session.add(Alert(user_id=citizen.id, alert_type=AlertType.personal, severity=AlertSeverity.low,
                              message=REMINDER_MESSAGE, is_read=True, created_at=now - timedelta(days=6)))
        elif kind == "bp":
            session.add(ScheduledVisit(worker_id=worker.id, citizen_id=citizen.id, case_id=flags[-1].id if flags else None,
                                       scheduled_for=(now + timedelta(days=2)).replace(hour=5, minute=0),
                                       reason="Blood pressure high for 3 days", status=VisitStatus.scheduled,
                                       location=f"Home visit, {area}", created_at=now))
        elif kind == "glucose":
            for f in flags[:-2]:
                f.resolution, f.reviewed_by, f.reviewed_at = FlagResolution.reviewed, worker.id, f.processed_at + timedelta(hours=6)
            session.add(ScheduledVisit(worker_id=worker.id, citizen_id=citizen.id, scheduled_for=now - timedelta(days=2, hours=-4),
                                       reason="Blood glucose review", status=VisitStatus.scheduled, location=facility.name,
                                       created_at=now - timedelta(days=5)))
        elif kind == "new":
            session.add(Alert(user_id=citizen.id, alert_type=AlertType.personal, severity=AlertSeverity.low,
                              message=REMINDER_MESSAGE, is_read=False, created_at=now - timedelta(hours=20)))
        created += 1
        print(f"   {email}: {kind}, {days} readings, {len(flags)} flagged")
    print(f"   Second catchment ({facility.name}, worker {SECOND_WORKER_EMAIL}): {created} created, {skipped} already existed")


async def align_passwords(session: AsyncSession) -> None:
    """Give every demo-owned account the shared demo password. Other accounts are not touched."""
    hashed = hash_password(get_settings().DEMO_PASSWORD or "")
    owned = or_(User.email.in_(OWNED_EMAILS), *[User.email.like(f"%{d}") for d in OWNED_DOMAINS])
    result = await session.execute(update(User).where(owned).values(hashed_password=hashed, is_active=True))
    print(f"   {result.rowcount} demo accounts use DEMO_PASSWORD")


async def main() -> None:
    password = check_config()
    try:
        await check_schema()
        before = await counts()
        await step("Health centre registry", seed_phc_facilities.seed)
        await step("Workers for every centre and an admin per district", seed_directory.seed)
        await step("Demo admin", seed_admin.seed)
        await step("Main PHC worker (Mylapore)", seed_phc_worker.seed)
        await step("Citizen with 90 days of history", seed_citizen.seed)
        await step("Mylapore catchment (27 citizens)", seed_demo_catchment.seed)
        await step("Second catchment (Adyar)", seed_second_catchment)
        await step("Admin work: applications, concerns, advisory", seed_admin_workflow.seed)
        await step("Complaints and missed visits", seed_complaints.seed)
        await step("Fever cluster for outbreak detection", lambda s: seed_outbreak.seed_area(s, "Mandaveli"))
        await step("Demo passwords", align_passwords)
        after = await counts()
    finally:
        await engine.dispose()

    print("\n== Record counts (whole database)\n")
    print(f"   {'':28} {'before':>8} {'after':>8} {'added':>8}")
    for name, _ in TABLES:
        print(f"   {name:28} {before[name]:>8} {after[name]:>8} {after[name] - before[name]:>8}")
    print("\n== Demo logins (password for all: the DEMO_PASSWORD in backend/.env)\n")
    for role, email in [("Admin", ADMIN_EMAIL), ("PHC worker, Mylapore", WORKER_EMAIL), ("PHC worker, Adyar", SECOND_WORKER_EMAIL),
                        ("Citizen, 90-day history", seed_citizen.EMAIL), *[(f"Citizen, {a[2]}", a[0]) for a in ADYAR]]:
        print(f"   {role:28} {email}")
    print(f"\n   Password: {'*' * len(password)} (see DEMO_PASSWORD; documented in docs/DEMO_READINESS.md)")


if __name__ == "__main__":
    asyncio.run(main())
