"""Complaints with evidence: a citizen who keeps missing visits, the worker's complaint, and a smartwatch complaint.

    python -m app.seeds.seed_complaints

Run after seed_citizen. Idempotent: does nothing if the worker's complaint already exists.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Concern, ScheduledVisit, User
from app.models.enums import ConcernCategory, ConcernStatus, UserRole, VisitStatus
from app.services.complaints import _watch, missed_visits

from ._common import run, user_by_email, utcnow

WORKER = "phc.worker@example.com"
DEVICE_COMPLAINER = "citizen.demo@example.com"


async def seed(session: AsyncSession) -> None:
    worker = await user_by_email(session, WORKER)
    if worker is None or worker.phc_id is None:
        print("Run seed_citizen first: the demo PHC worker is missing.")
        return
    if await session.scalar(select(Concern.id).where(Concern.user_id == worker.id, Concern.category == ConcernCategory.citizen_missed_visits)):
        print("Complaints already seeded.")
        return

    citizen = await session.scalar(
        select(User).where(User.phc_id == worker.phc_id, User.role == UserRole.user, User.email != DEVICE_COMPLAINER).order_by(User.name).limit(1)
    )
    now = utcnow()
    places = ["Citizen's home, Luz Church Road", "Mylapore PHC", "Citizen's home, Luz Church Road", "Mylapore PHC"]
    for i, days_ago in enumerate((62, 41, 19, 6)):
        session.add(ScheduledVisit(
            worker_id=worker.id, citizen_id=citizen.id, scheduled_for=now - timedelta(days=days_ago, hours=-10),
            status=VisitStatus.missed, location=places[i], reason="Blood pressure follow-up",
            missed_notified_at=now - timedelta(days=days_ago),
            missed_reason="I was admitted at a hospital in Vellore that week." if i == 1 else None,
            missed_reason_at=now - timedelta(days=days_ago - 1) if i == 1 else None,
        ))
    await session.flush()

    evidence = await missed_visits(session, citizen.id, worker.phc_id)
    session.add(Concern(
        user_id=worker.id, subject_id=citizen.id, category=ConcernCategory.citizen_missed_visits, status=ConcernStatus.open,
        description=f"{citizen.name} has not been home for three booked blood pressure follow-ups and has not answered calls. "
                    "Their readings were flagged high twice this month, so I am worried.",
        evidence=evidence, created_at=now - timedelta(hours=5),
    ))

    complainer = await user_by_email(session, DEVICE_COMPLAINER)
    if complainer is not None:
        session.add(Concern(
            user_id=complainer.id, category=ConcernCategory.device_issue, status=ConcernStatus.open,
            description="My smartwatch readings stopped showing up since Friday even though the watch is charged and paired.",
            evidence=await _watch(session, complainer), created_at=now - timedelta(hours=2),
        ))
    await session.commit()
    print(f"Seeded: {evidence['unexplained']} unexplained missed visits for {citizen.name}, the worker's complaint, and a smartwatch complaint.")


if __name__ == "__main__":
    run(seed)
