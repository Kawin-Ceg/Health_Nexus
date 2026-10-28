"""One rich demo citizen: 90 days of readings, alerts, a chat, and visits.

    python -m app.seeds.seed_citizen

Run after seed_phc_worker so the citizen lands in that worker's catchment and
gets a visit from them. Uses DEMO_CITIZEN_PASSWORD (generated if unset).
"""

import random
import sys
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Advisory, ChatMessage, ChatSession, ProcessedData, ScheduledVisit, User, UserProfile
from app.models.enums import (
    AdvisoryScope,
    AlertSeverity,
    BloodGroup,
    ChatMessageRole,
    ConsentType,
    FlagResolution,
    Gender,
    UserRole,
    VisitStatus,
)

from ._common import add_scored_reading, grant_consents, password_or_generated, run, user_by_email, utcnow

EMAIL = "citizen.demo@example.com"
DAYS = 90


async def seed(session: AsyncSession) -> None:
    settings = get_settings()
    if await user_by_email(session, EMAIL):
        print(f"Demo citizen exists, skipping: {EMAIL}")
        return
    worker = await user_by_email(session, settings.PHC_WORKER_EMAIL)
    if worker is None or worker.phc_id is None:
        sys.exit("Run seed_phc_worker first: the demo citizen joins that worker's catchment.")

    rng = random.Random(90)
    now = utcnow().replace(second=0, microsecond=0)
    joined = now - timedelta(days=DAYS + 3)
    password = password_or_generated(settings.DEMO_CITIZEN_PASSWORD, "Demo citizen")

    citizen = User(
        name="Anjali Venkatesan",
        email=EMAIL,
        hashed_password=hash_password(password),
        role=UserRole.user,
        consent=True,
        profile_completed=True,
        is_verified=True,
        email_verified=True,
        verified_at=joined,
        phone="+91 98410 67890",
        bio="Tracking my blood pressure after a hypertension diagnosis.",
        phc_id=worker.phc_id,
        district=worker.district,
        state=worker.state,
        pincode="600004",
        area="Mandaveli",
        geo_lat=13.0271,
        geo_lng=80.2632,
        created_at=joined,
    )
    session.add(citizen)
    await session.flush()

    session.add(
        UserProfile(
            user_id=citizen.id,
            age=52,
            gender=Gender.female,
            height_cm=158.0,
            weight_kg=67.5,
            blood_group=BloodGroup.b_pos,
            existing_conditions=["hypertension"],
            current_medications=["amlodipine 5 mg"],
            emergency_contact_name="Ravi Venkatesan",
            emergency_contact_phone="+91 98410 11223",
            has_smartwatch=True,
            smartwatch_brand="Noise",
            permission_health_tracking=True,
            created_at=joined,
            updated_at=joined,
        )
    )
    await grant_consents(
        session,
        citizen,
        [
            ConsentType.health_tracking,
            ConsentType.community_surveillance,
            ConsentType.phc_worker_access,
            ConsentType.research_analytics,
        ],
        joined,
    )

    flags: list[ProcessedData] = []
    for day in range(DAYS):
        for slot in range(1 if day % 3 else 2):
            measured_at = now - timedelta(days=DAYS - 1 - day, hours=14 - slot * 9 + rng.randint(0, 2))
            spike = 30 <= day <= 34 or day >= DAYS - 4
            vitals = {
                "systolic": rng.uniform(158, 172) if spike else rng.gauss(122, 4),
                "diastolic": rng.uniform(95, 104) if spike else rng.gauss(80, 3),
                "heart_rate": rng.gauss(78, 4),
                "temperature_c": rng.gauss(36.7, 0.12),
                "spo2": min(100, rng.gauss(97.6, 0.5)),
                "respiratory_rate": rng.gauss(15, 1),
                "glucose_mg_dl": rng.gauss(96, 6),
                "weight_kg": 69.0 - day * 0.02 + rng.gauss(0, 0.2),
            }
            processed = await add_scored_reading(
                session,
                citizen,
                {k: round(v, 1) for k, v in vitals.items()},
                measured_at,
                ["headache"] if spike else [],
            )
            if processed.is_anomaly:
                flags.append(processed)

    earlier = [f for f in flags if f.processed_at < now - timedelta(days=30)]
    for flag in earlier:
        flag.resolution = FlagResolution.reviewed
        flag.reviewed_by = worker.id
        flag.reviewed_at = flag.processed_at + timedelta(days=1)
        flag.resolution_note = "Medication dose reviewed at the PHC."
    open_flags = [f for f in flags if f.resolution is None]

    session.add(
        Advisory(
            scope=AdvisoryScope.district,
            district="Chennai",
            state="Tamil Nadu",
            title="Seasonal fever",
            body="Seasonal fever cases are rising in Chennai. Report a temperature above 38 °C.",
            severity=AlertSeverity.low,
            created_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=25),
        )
    )

    session.add(
        ScheduledVisit(
            worker_id=worker.id,
            citizen_id=citizen.id,
            case_id=earlier[0].id if earlier else None,
            scheduled_for=now - timedelta(days=DAYS - 36),
            reason="Follow up on raised blood pressure",
            status=VisitStatus.completed,
            location="Home visit, Mandaveli",
            created_at=now - timedelta(days=DAYS - 35),
        )
    )
    session.add(
        ScheduledVisit(
            worker_id=worker.id,
            citizen_id=citizen.id,
            case_id=open_flags[-1].id if open_flags else None,
            scheduled_for=(now + timedelta(days=1)).replace(hour=4, minute=30),
            reason="Blood pressure above normal for 4 days",
            status=VisitStatus.scheduled,
            location="Mylapore PHC",
            created_at=now,
        )
    )

    chat = ChatSession(user_id=citizen.id, title="Blood pressure this week", auto_titled=True, created_at=now, updated_at=now)
    session.add(chat)
    await session.flush()
    session.add_all(
        [
            ChatMessage(
                session_id=chat.id,
                user_id=citizen.id,
                role=ChatMessageRole.user,
                content="How has my blood pressure been this week?",
                created_at=now,
            ),
            ChatMessage(
                session_id=chat.id,
                user_id=citizen.id,
                role=ChatMessageRole.assistant,
                content="Your systolic pressure has been above 158 mmHg for the last 4 days, up from around 122 before. Your PHC has scheduled a visit for tomorrow.",
                retrieval={"tool": "recent_vitals", "arguments": {"days": 7, "vital": "systolic"}, "row_count": 9},
                latency_ms=840,
                created_at=now + timedelta(seconds=2),
            ),
        ]
    )

    print(
        f"Demo citizen created: {EMAIL} ({len(flags)} flagged readings, {len(open_flags)} still open, "
        f"2 visits, 1 chat)"
    )


if __name__ == "__main__":
    run(seed)
