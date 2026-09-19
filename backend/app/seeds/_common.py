"""Shared helpers for the seed scripts. Run each script with `python -m app.seeds.<name>`."""

import asyncio
import secrets
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, engine
from app.models import Alert, ConsentRecord, HealthRecord, ProcessedData, User
from app.models.enums import AlertSeverity, AlertType, ConsentType
from app.services.scoring import score_reading
from app.services.vitals import VITALS, validate_vitals


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
    """Store a reading and its score, plus a personal alert when it is flagged."""
    clean = validate_vitals(vitals)
    record = HealthRecord(
        user_id=user.id,
        vitals=clean,
        symptoms=symptoms or [],
        geo_lat=user.geo_lat,
        geo_lng=user.geo_lng,
        timestamp=measured_at,
        created_at=measured_at,
    )
    session.add(record)
    await session.flush()

    score = score_reading(clean)
    processed = ProcessedData(
        health_record_id=record.id,
        user_id=user.id,
        features=score.features,
        anomaly_score=score.anomaly_score,
        is_anomaly=score.is_anomaly,
        processed_at=measured_at,
    )
    session.add(processed)

    if score.is_anomaly and score.top_feature:
        key = score.top_feature
        severity = AlertSeverity.high if score.anomaly_score >= 0.75 else AlertSeverity.medium
        session.add(
            Alert(
                user_id=user.id,
                alert_type=AlertType.personal,
                severity=severity,
                message=f"Your {key.replace('_', ' ')} reading of {clean[key]:g} {VITALS[key].unit} is outside the normal range.",
                created_at=measured_at,
            )
        )
    await session.flush()
    return processed


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
