"""Onboarding: the registry lookups behind the dropdowns, and the profile write."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserProfile, ValidPhcFacility
from app.models.enums import ConsentType, UserRole
from app.schemas.onboarding import ConsentAnswers, FacilityOut, ProfileFields, ProfileOut
from app.services.consent import current_consents

NOT_SERVING = "The health centre you chose does not serve that district. Choose one from the list."


def _same(column, value: str):
    return func.lower(column) == value.strip().lower()


async def list_states(db: AsyncSession) -> list[str]:
    rows = await db.scalars(
        select(ValidPhcFacility.state).where(ValidPhcFacility.is_active.is_(True)).distinct().order_by(ValidPhcFacility.state)
    )
    return list(rows)


async def list_districts(db: AsyncSession, state: str) -> list[str]:
    """Only districts with at least one active centre: an empty dropdown is a dead end."""
    rows = await db.scalars(
        select(ValidPhcFacility.district)
        .where(ValidPhcFacility.is_active.is_(True), _same(ValidPhcFacility.state, state))
        .distinct()
        .order_by(ValidPhcFacility.district)
    )
    return list(rows)


async def list_facilities(db: AsyncSession, state: str, district: str) -> list[tuple[ValidPhcFacility, int]]:
    """Centres in a district, each with the number of workers reviewing readings there.

    A centre with no worker still appears: people live in that catchment. The
    count lets the picker say so before the choice is made, instead of the
    dashboard reporting it afterwards.
    """
    workers = (
        select(func.count())
        .select_from(User)
        .where(
            User.phc_id == ValidPhcFacility.id,
            User.role == UserRole.phc_worker,
            User.is_active.is_(True),
        )
        .correlate(ValidPhcFacility)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(ValidPhcFacility, workers.label("workers_assigned"))
        .where(
            ValidPhcFacility.is_active.is_(True),
            _same(ValidPhcFacility.state, state),
            _same(ValidPhcFacility.district, district),
        )
        .order_by(ValidPhcFacility.name)
    )
    return [(facility, count) for facility, count in rows.all()]


async def resolve_facility(db: AsyncSession, state: str, district: str, phc_id: uuid.UUID) -> ValidPhcFacility:
    """The chosen centre, or 422 if it is unknown, inactive, or not in that state and district."""
    facility = await db.get(ValidPhcFacility, phc_id)
    if (
        facility is None
        or not facility.is_active
        or facility.state.lower() != state.strip().lower()
        or facility.district.lower() != district.strip().lower()
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, NOT_SERVING)
    return facility


PROFILE_COLUMNS = (
    "age",
    "gender",
    "height_cm",
    "weight_kg",
    "blood_group",
    "existing_conditions",
    "current_medications",
    "has_smartwatch",
    "smartwatch_brand",
    "emergency_contact_name",
    "emergency_contact_phone",
)
USER_COLUMNS = ("pincode", "area")


def apply_fields(user: User, profile: UserProfile, fields: ProfileFields, facility: ValidPhcFacility, only: set[str] | None = None) -> None:
    """Copy validated values onto the rows. `only` limits it to the keys a PATCH sent."""

    def wanted(key: str) -> bool:
        return only is None or key in only

    for column in PROFILE_COLUMNS:
        if wanted(column):
            setattr(profile, column, getattr(fields, column))
    for column in USER_COLUMNS:
        if wanted(column):
            setattr(user, column, getattr(fields, column))
    if only is None or only & {"state", "district", "phc_id"}:
        user.phc_id, user.state, user.district = facility.id, facility.state, facility.district


async def build_profile_out(db: AsyncSession, user: User, profile: UserProfile) -> ProfileOut:
    facility = await db.get(ValidPhcFacility, user.phc_id) if user.phc_id else None
    consents = await current_consents(db, user.id)
    answered = ConsentType.health_tracking in consents and ConsentType.community_surveillance in consents
    return ProfileOut(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        blood_group=profile.blood_group,
        state=user.state,
        district=user.district,
        phc_id=user.phc_id,
        facility=FacilityOut.model_validate(facility) if facility else None,
        pincode=user.pincode,
        area=user.area,
        existing_conditions=profile.existing_conditions,
        current_medications=profile.current_medications,
        has_smartwatch=profile.has_smartwatch,
        smartwatch_brand=profile.smartwatch_brand,
        emergency_contact_name=profile.emergency_contact_name,
        emergency_contact_phone=profile.emergency_contact_phone,
        consents=ConsentAnswers(
            health_tracking=consents[ConsentType.health_tracking],
            community_surveillance=consents[ConsentType.community_surveillance],
            phc_worker_access=consents.get(ConsentType.phc_worker_access),
        )
        if answered
        else None,
    )
