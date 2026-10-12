"""Staff every registry health centre: one approved PHC worker per centre and one admin per district.

    python -m app.seeds.seed_directory

Run after seed_phc_facilities. Every account shares one demo password: SEED_DEMO_PASSWORD
from the environment, or a generated one. The full list, with the password, is written to
backend/SEED_ACCOUNTS.md (git-ignored). Idempotent: existing emails are left alone.
"""

import os
import pathlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import PhcApplication, PhcVerificationAuditLog, User, ValidPhcFacility
from app.models.enums import ApplicationStatus, Designation, PhcVerificationAction, UserRole

from ._common import run, user_by_email, utcnow

OUT = pathlib.Path(__file__).resolve().parents[2] / "SEED_ACCOUNTS.md"

FIRST = ["Kavitha", "Senthil", "Meena", "Arun", "Lakshmi", "Prakash", "Divya", "Ganesh", "Revathi", "Karthik",
         "Anitha", "Suresh", "Priya", "Murugan", "Deepa", "Rajesh", "Saranya", "Vignesh", "Bhavani", "Ramesh"]
LAST = ["Raman", "Kumar", "Subramanian", "Krishnan", "Rajan", "Natarajan", "Iyer", "Pillai", "Selvam", "Murthy"]
DESIGNATIONS = [Designation.staff_nurse, Designation.medical_officer, Designation.health_inspector, Designation.asha_supervisor]


def slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


async def seed(session: AsyncSession) -> None:
    password = os.environ.get("SEED_DEMO_PASSWORD") or f"Demo-{secrets.token_urlsafe(9)}1"
    hashed = hash_password(password)
    now = utcnow()
    facilities = (await session.scalars(select(ValidPhcFacility).where(ValidPhcFacility.is_active.is_(True)).order_by(
        ValidPhcFacility.district, ValidPhcFacility.facility_code))).all()
    if not facilities:
        raise SystemExit("No health centres found. Run python -m app.seeds.seed_phc_facilities first.")

    workers: list[tuple[str, str, str, str, bool]] = []
    admins: list[tuple[str, str, str, bool]] = []

    for i, f in enumerate(facilities):
        email = f"{slug(f.facility_code)}@phc.example.com"
        name = f"{FIRST[i % len(FIRST)]} {LAST[(i // len(FIRST)) % len(LAST)]}"
        created = await user_by_email(session, email) is None
        if created:
            worker = User(
                name=name, email=email, hashed_password=hashed, role=UserRole.phc_worker,
                is_verified=True, email_verified=True, verified_at=now, consent=True, profile_completed=True,
                department="Primary care", phc_id=f.id, district=f.district, state=f.state, area=f.block,
                geo_lat=f.latitude, geo_lng=f.longitude,
            )
            session.add(worker)
            await session.flush()
            area = f.facility_code.split("-")[1] if f.facility_code.count("-") >= 2 else "TN"
            application = PhcApplication(
                user_id=worker.id, employee_id=f"TNPHC-{area}-{1000 + i}", designation=DESIGNATIONS[i % len(DESIGNATIONS)],
                phc_name=f.name, district=f.district, state=f.state, years_of_service=2 + i % 15,
                status=ApplicationStatus.approved, facility_id=f.id, last_checked_at=now, reviewed_at=now,
            )
            session.add(application)
            await session.flush()
            session.add(PhcVerificationAuditLog(
                application_id=application.id, subject_user_id=worker.id, action=PhcVerificationAction.application_approved,
                from_status=ApplicationStatus.pending.value, to_status=ApplicationStatus.approved.value,
                reason="Seeded demo worker", ip_address="seed",
            ))
        workers.append((f.district, f.name, name, email, created))

    for district in sorted({f.district for f in facilities}):
        email = f"admin.{slug(district)}@admin.example.com"
        name = f"{district} District Admin"
        created = await user_by_email(session, email) is None
        if created:
            session.add(User(
                name=name, email=email, hashed_password=hashed, role=UserRole.admin, district=district, state="Tamil Nadu",
                is_verified=True, email_verified=True, verified_at=now, consent=True, profile_completed=True,
            ))
        admins.append((district, name, email, created))

    new_w = sum(1 for w in workers if w[4])
    new_a = sum(1 for a in admins if a[3])
    lines = [
        "# Seeded demo accounts",
        "",
        "Created by `python -m app.seeds.seed_directory`. Demo data only: never use these in production.",
        "",
        f"**Password for every account created in the run that wrote this file:** `{password}`",
        "",
        "Accounts marked *existing* were already in the database and keep their own password.",
        "Admin access is app-wide: the app has no district-limited admin role, so each district admin can see everything.",
        "",
        f"## Admins ({len(admins)}, one per district)",
        "",
        "| District | Name | Email | |",
        "|---|---|---|---|",
        *[f"| {d} | {n} | `{e}` | {'' if c else 'existing'} |" for d, n, e, c in admins],
        "",
        f"## PHC workers ({len(workers)}, one per health centre)",
        "",
        "| District | Health centre | Name | Email | |",
        "|---|---|---|---|---|",
        *[f"| {d} | {h} | {n} | `{e}` | {'' if c else 'existing'} |" for d, h, n, e, c in workers],
        "",
    ]
    if new_w or new_a or not OUT.exists():
        OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"PHC workers: {new_w} created, {len(workers) - new_w} existing. Admins: {new_a} created, {len(admins) - new_a} existing.")
    print(f"Account list: {OUT}")


if __name__ == "__main__":
    run(seed)
