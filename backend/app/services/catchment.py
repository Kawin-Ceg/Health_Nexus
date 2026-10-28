"""The catchment rule. Every "which citizens can this worker see" question goes through here.

A worker serves every account with `role = 'user'` whose `phc_id` equals the
worker's `phc_id`, except citizens who turned off health worker access
(services/consent.allows_worker_access). A worker with no phc_id serves nobody,
never everybody.
"""

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import Select, false, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_phc_worker
from app.models import User, ValidPhcFacility
from app.models.enums import ConsentType, UserRole

from .consent import allows_worker_access, current_consents

CITIZEN_NOT_FOUND = "Citizen not found."
NO_FACILITY = (
    "Your account is not linked to a health centre, so there is no catchment to show. "
    "An administrator needs to link you to your facility before readings can reach you."
)


def catchment_citizens(worker: User) -> Select[tuple[User]]:
    """Query for the citizens in `worker`'s catchment. Callers add ordering and a LIMIT."""
    if worker.phc_id is None:
        return select(User).where(false())
    return select(User).where(User.phc_id == worker.phc_id, User.role == UserRole.user, allows_worker_access(User.id))


def catchment_ids(worker: User) -> Select[tuple[uuid.UUID]]:
    """Ids of the catchment, for `.in_()` filters on other tables."""
    if worker.phc_id is None:
        return select(User.id).where(false())
    return select(User.id).where(User.phc_id == worker.phc_id, User.role == UserRole.user, allows_worker_access(User.id))


async def worker_access_allowed(session: AsyncSession, citizen_id: uuid.UUID) -> bool:
    return (await current_consents(session, citizen_id)).get(ConsentType.phc_worker_access) is not False


async def in_catchment(session: AsyncSession, worker: User, citizen: User) -> bool:
    return (
        worker.phc_id is not None
        and citizen.role == UserRole.user
        and citizen.phc_id == worker.phc_id
        and await worker_access_allowed(session, citizen.id)
    )


def citizen_not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, CITIZEN_NOT_FOUND)


async def get_catchment_citizen(session: AsyncSession, worker: User, user_id: uuid.UUID) -> User:
    """The citizen, or 404 with the same body whether they do not exist or are not this worker's."""
    citizen = await session.get(User, user_id)
    if citizen is None or not await in_catchment(session, worker, citizen):
        raise citizen_not_found()
    return citizen


async def require_catchment_worker(worker: User = Depends(require_phc_worker)) -> User:
    """An approved worker linked to a facility. 409 otherwise: "0 flagged" would read as a quiet day."""
    if worker.phc_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, NO_FACILITY)
    return worker


async def workers_serving(session: AsyncSession, phc_id: uuid.UUID | None) -> int:
    """How many active workers review readings at a facility."""
    if phc_id is None:
        return 0
    return await session.scalar(
        select(func.count()).where(
            User.phc_id == phc_id, User.role == UserRole.phc_worker, User.is_active.is_(True)
        )
    ) or 0


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
