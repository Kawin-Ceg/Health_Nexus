"""Create the admin account from ADMIN_EMAIL / ADMIN_PASSWORD, already verified.

    python -m app.seeds.seed_admin

Idempotent: an existing account with that email is promoted to admin and
verified; its password is left unchanged.
"""

import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole

from ._common import run, user_by_email, utcnow


async def seed(session: AsyncSession) -> None:
    settings = get_settings()
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        sys.exit("Set ADMIN_EMAIL and ADMIN_PASSWORD (environment or .env) first.")

    email = settings.ADMIN_EMAIL.strip().lower()
    now = utcnow()
    admin = await user_by_email(session, email)
    if admin is None:
        admin = User(name=settings.ADMIN_NAME, email=email, hashed_password=hash_password(settings.ADMIN_PASSWORD))
        session.add(admin)
        print(f"Admin created: {email}")
    else:
        print(f"Admin exists, ensuring role and verification: {email}")

    admin.role = UserRole.admin
    admin.is_active = True
    admin.is_verified = True
    admin.email_verified = True
    admin.verified_at = admin.verified_at or now
    admin.profile_completed = True
    admin.consent = True


if __name__ == "__main__":
    run(seed)
