"""Create one verified, approved PHC worker linked to a registry facility.

    python -m app.seeds.seed_phc_worker

Run after seed_phc_facilities. Uses PHC_WORKER_EMAIL / PHC_WORKER_PASSWORD
(a password is generated and printed if none is set). The facility is found the
same way real approval does it: by matching the claimed PHC name against
valid_phc_facilities.normalised_name.
"""

import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import PhcApplication, PhcVerificationAuditLog, User
from app.models.enums import ApplicationStatus, Designation, PhcVerificationAction, UserRole
from app.services.phc_registry import match_facility

from ._common import password_or_generated, run, user_by_email, utcnow

# Deliberately written differently from the registry's "Mylapore PHC" to
# exercise name normalisation.
CLAIMED_PHC = "Mylapore Primary Health Centre"
DISTRICT = "Chennai"
STATE = "Tamil Nadu"


async def seed(session: AsyncSession) -> None:
    settings = get_settings()
    email = settings.PHC_WORKER_EMAIL.strip().lower()
    if await user_by_email(session, email):
        print(f"PHC worker exists, skipping: {email}")
        return

    facility = await match_facility(session, CLAIMED_PHC, DISTRICT, STATE)
    if facility is None:
        sys.exit(f"No unique registry match for {CLAIMED_PHC!r}. Run seed_phc_facilities first.")

    now = utcnow()
    password = password_or_generated(settings.PHC_WORKER_PASSWORD, "PHC worker")
    worker = User(
        name="Kavitha Raman",
        email=email,
        hashed_password=hash_password(password),
        role=UserRole.phc_worker,
        is_verified=True,
        email_verified=True,
        verified_at=now,
        consent=True,
        profile_completed=True,
        department="Community Health",
        phone="+91 98400 12345",
        phc_id=facility.id,
        district=facility.district,
        state=facility.state,
        area=facility.block,
        geo_lat=facility.latitude,
        geo_lng=facility.longitude,
        created_at=now,
    )
    session.add(worker)
    await session.flush()

    application = PhcApplication(
        user_id=worker.id,
        employee_id="TN-HW-20417",
        designation=Designation.staff_nurse,
        phc_name=CLAIMED_PHC,
        district=DISTRICT,
        state=STATE,
        years_of_service=6,
        status=ApplicationStatus.approved,
        facility_id=facility.id,
        last_checked_at=now,
        reviewed_at=now,
        created_at=now,
    )
    session.add(application)
    await session.flush()

    session.add(
        PhcVerificationAuditLog(
            application_id=application.id,
            subject_user_id=worker.id,
            action=PhcVerificationAction.application_approved,
            from_status=ApplicationStatus.pending.value,
            to_status=ApplicationStatus.approved.value,
            reason="Seeded demo worker",
            ip_address="seed",
            created_at=now,
        )
    )
    print(f"PHC worker created: {email} -> {facility.name} ({facility.facility_code})")


if __name__ == "__main__":
    run(seed)
