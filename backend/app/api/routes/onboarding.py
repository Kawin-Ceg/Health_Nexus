from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_onboarding_user
from app.db.session import get_session
from app.models import User, UserProfile
from app.models.enums import ConsentType
from app.schemas.onboarding import FacilityOption, FacilityOut, ProfileCreate, ProfileFields, ProfileOut, ProfilePatch
from app.services import onboarding as svc
from app.services.consent import record_consents
from app.services.sessions import client_ip

# Every route here is for a verified citizen, so the guard sits on the router.
router = APIRouter(prefix="/onboarding", tags=["onboarding"], dependencies=[Depends(require_onboarding_user)])

_ALREADY_DONE = "Your profile is already set up. Use PATCH to change it."


async def _profile_of(db: AsyncSession, user: User) -> UserProfile | None:
    return await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))


@router.get("/states", response_model=list[str])
async def states(db: AsyncSession = Depends(get_session)) -> list[str]:
    return await svc.list_states(db)


@router.get("/districts", response_model=list[str])
async def districts(state: str = Query(min_length=1, max_length=100), db: AsyncSession = Depends(get_session)) -> list[str]:
    return await svc.list_districts(db, state)


@router.get("/facilities", response_model=list[FacilityOption])
async def facilities(
    state: str = Query(min_length=1, max_length=100),
    district: str = Query(min_length=1, max_length=100),
    db: AsyncSession = Depends(get_session),
):
    return [
        FacilityOption(**FacilityOut.model_validate(facility).model_dump(), workers_assigned=workers)
        for facility, workers in await svc.list_facilities(db, state, district)
    ]


@router.post("/profile", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: ProfileCreate,
    request: Request,
    user: User = Depends(require_onboarding_user),
    db: AsyncSession = Depends(get_session),
) -> ProfileOut:
    if user.profile_completed or await _profile_of(db, user) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, _ALREADY_DONE)

    facility = await svc.resolve_facility(db, data.state, data.district, data.phc_id)

    # One transaction: profile, catchment link, completed flag and consent rows
    # commit together or not at all.
    profile = UserProfile(user_id=user.id, permission_health_tracking=data.consents.health_tracking)
    svc.apply_fields(user, profile, data, facility)
    user.profile_completed = True
    user.consent = data.consents.health_tracking
    db.add(profile)
    await record_consents(
        db,
        user.id,
        {
            ConsentType.health_tracking: data.consents.health_tracking,
            ConsentType.community_surveillance: data.consents.community_surveillance,
        },
        source="onboarding",
        ip_address=client_ip(request),
    )
    try:
        await db.commit()
    except IntegrityError:  # a second submit raced this one past the check above
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, _ALREADY_DONE) from None
    return await svc.build_profile_out(db, user, profile)


@router.get("/profile", response_model=ProfileOut)
async def get_profile(user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)) -> ProfileOut:
    profile = await _profile_of(db, user)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not set up yet.")
    return await svc.build_profile_out(db, user, profile)


@router.patch("/profile", response_model=ProfileOut)
async def update_profile(
    data: ProfilePatch, user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)
) -> ProfileOut:
    profile = await _profile_of(db, user)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not set up yet.")

    sent = data.model_dump(exclude_unset=True)
    # Merge onto what is saved and validate the result as a whole, so a patch
    # cannot leave the record in a state that creating it would have refused.
    merged = {
        **{column: getattr(profile, column) for column in svc.PROFILE_COLUMNS},
        "state": user.state,
        "district": user.district,
        "phc_id": user.phc_id,
        "pincode": user.pincode,
        "area": user.area,
        **sent,
    }
    if sent.get("has_smartwatch") is False and "smartwatch_brand" not in sent:
        merged["smartwatch_brand"] = None
    try:
        fields = ProfileFields.model_validate(merged)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_context=False, include_input=False)) from None

    facility = await svc.resolve_facility(db, fields.state, fields.district, fields.phc_id)
    changed = set(sent)
    if sent.get("has_smartwatch") is False:
        changed.add("smartwatch_brand")  # cleared above
    svc.apply_fields(user, profile, fields, facility, only=changed)
    await db.commit()
    return await svc.build_profile_out(db, user, profile)
