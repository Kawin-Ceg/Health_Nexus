"""Shared helpers for the seed scripts. Run each script with `python -m app.seeds.<name>`."""

import asyncio
import secrets
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, engine
from app.models import ConsentRecord, ProcessedData, User
from app.models.enums import ConsentType
from app.services.metrics import validate_vitals
from app.services.readings import record_reading


def run(main: Callable[[AsyncSession], Awaitable[None]]) -> None:
    async def _runner() -> None:
        try:
            async with SessionLocal() as session:
                await main(session)
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_runner())


def password_or_generated(configured: str | None, label: str) -> str:
    """Use the configured password, or generate one and print it once."""
    if configured:
        return configured
    generated = secrets.token_urlsafe(12)
    print(f"  {label}: no password configured, generated one: {generated}")
    return generated


async def user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.strip().lower()))


async def grant_consents(session: AsyncSession, user: User, types: list[ConsentType], at: datetime) -> None:
    for consent_type in types:
        session.add(ConsentRecord(user_id=user.id, consent_type=consent_type, granted=True, source="seed", created_at=at))


async def add_scored_reading(
    session: AsyncSession,
    user: User,
    vitals: dict[str, float],
    measured_at: datetime,
    symptoms: list[str] | None = None,
) -> ProcessedData:
    """Store and score a reading exactly as POST /health/vitals does, dated as if submitted then."""
    recorded = await record_reading(session, user, validate_vitals(vitals), symptoms or [], measured_at, stored_at=measured_at)
    return recorded.processed


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
