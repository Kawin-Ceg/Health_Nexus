"""consent_records is append-only; the current state of a type is its latest row."""

import uuid
from collections.abc import Mapping

from sqlalchemy import ColumnElement, ScalarSelect, false, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConsentRecord, User, UserProfile
from app.models.enums import ConsentType, UserRole

from .visits import cancel_open_visits


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


def latest_consent(consent_type: ConsentType, user_id: ColumnElement[uuid.UUID]) -> ScalarSelect[bool]:
    """Correlated subquery: the person's latest answer for `consent_type`, NULL if never asked."""
    return (
        select(ConsentRecord.granted)
        .where(ConsentRecord.user_id == user_id, ConsentRecord.consent_type == consent_type)
        .order_by(ConsentRecord.created_at.desc(), ConsentRecord.id.desc())
        .limit(1)
        .scalar_subquery()
    )


def allows_worker_access(user_id: ColumnElement[uuid.UUID]) -> ColumnElement[bool]:
    """Health workers at the person's centre may see them unless they said no.

    Never answered counts as yes: choosing a health centre at onboarding is what
    links a citizen to it, and this consent is how they withdraw from it.
    """
    return func.coalesce(latest_consent(ConsentType.phc_worker_access, user_id), true())


def counts_in_community(user_id: ColumnElement[uuid.UUID]) -> ColumnElement[bool]:
    """Area-level figures (locality risk, the map, locality breakdowns) count only people who said yes."""
    return func.coalesce(latest_consent(ConsentType.community_surveillance, user_id), false())


def in_research(user_id: ColumnElement[uuid.UUID]) -> ColumnElement[bool]:
    return func.coalesce(latest_consent(ConsentType.research_analytics, user_id), false())


def _latest_sql(consent_type: ConsentType) -> str:
    return (
        "(SELECT cr.granted FROM consent_records cr WHERE cr.user_id = u.id "
        f"AND cr.consent_type = '{consent_type.value}' ORDER BY cr.created_at DESC, cr.id DESC LIMIT 1)"
    )


WORKER_ACCESS_SQL = f"coalesce({_latest_sql(ConsentType.phc_worker_access)}, true)"
COMMUNITY_SQL = f"coalesce({_latest_sql(ConsentType.community_surveillance)}, false)"


async def change_consents(
    session: AsyncSession,
    user: User,
    choices: Mapping[ConsentType, bool],
    *,
    source: str,
    ip_address: str | None,
) -> None:
    """Record the choices and carry out what they mean. Does not commit.

    Health tracking is mirrored onto the account and profile. Withdrawing health
    worker access cancels booked visits: the workers can no longer see this person.
    """
    before = await current_consents(session, user.id)
    await record_consents(session, user.id, choices, source=source, ip_address=ip_address)
    if user.role != UserRole.user:
        return
    if ConsentType.health_tracking in choices:
        granted = choices[ConsentType.health_tracking]
        user.consent = granted
        profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
        if profile is not None:
            profile.permission_health_tracking = granted
    if choices.get(ConsentType.phc_worker_access) is False and before.get(ConsentType.phc_worker_access) is not False:
        await cancel_open_visits(session, user)
