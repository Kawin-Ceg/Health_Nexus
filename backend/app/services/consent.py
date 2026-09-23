"""consent_records is append-only; the current state of a type is its latest row."""

import uuid
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConsentRecord
from app.models.enums import ConsentType


async def current_consents(session: AsyncSession, user_id: uuid.UUID) -> dict[ConsentType, bool]:
    rows = await session.execute(
        select(ConsentRecord.consent_type, ConsentRecord.granted)
        .where(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.created_at, ConsentRecord.id)
    )
    return {consent_type: granted for consent_type, granted in rows}


async def record_consents(
    session: AsyncSession,
    user_id: uuid.UUID,
    choices: Mapping[ConsentType, bool],
    *,
    source: str,
    ip_address: str | None,
) -> list[ConsentRecord]:
    """Append a row for each choice that differs from the current state.

    A first answer is always recorded, including a refusal: "asked and declined"
    is history worth keeping. Does not commit; the caller owns the transaction.
    """
    current = await current_consents(session, user_id)
    added = [
        ConsentRecord(user_id=user_id, consent_type=consent_type, granted=granted, source=source, ip_address=ip_address)
        for consent_type, granted in choices.items()
        if current.get(consent_type) != granted
    ]
    session.add_all(added)
    return added
