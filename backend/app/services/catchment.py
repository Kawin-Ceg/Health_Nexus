"""The catchment rule. Every "which citizens can this worker see" question goes through here.

A worker sees citizens where `users.phc_id = worker.phc_id AND role = 'user'`.
A worker with no phc_id sees nobody, never everybody.
"""

import uuid

from sqlalchemy import Select, false, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, ValidPhcFacility
from app.models.enums import UserRole


def catchment_citizens(worker: User) -> Select[tuple[User]]:
    """Query for the citizens in `worker`'s catchment. Callers add ordering and a LIMIT."""
    if worker.phc_id is None:
        return select(User).where(false())
    return select(User).where(User.phc_id == worker.phc_id, User.role == UserRole.user)


def in_catchment(worker: User, citizen: User) -> bool:
    return worker.phc_id is not None and citizen.role == UserRole.user and citizen.phc_id == worker.phc_id


async def facility_serves_district(
    session: AsyncSession, facility_id: uuid.UUID, district: str, state: str | None = None
) -> bool:
    """A citizen may only choose an active facility in their own district."""
    query = select(ValidPhcFacility.id).where(
        ValidPhcFacility.id == facility_id,
        ValidPhcFacility.is_active.is_(True),
        ValidPhcFacility.district.ilike(district.strip()),
    )
    if state:
        query = query.where(ValidPhcFacility.state.ilike(state.strip()))
    return (await session.scalar(query)) is not None
