"""Account settings for every approved role: preferences, privacy, security, support, and the citizen's health centre."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import require_any_verified, require_onboarding_user
from app.core.security import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH, hash_password, verify_password
from app.db.session import get_session
from app.models import (
    Alert,
    AuditLog,
    Concern,
    ConsentRecord,
    HealthRecord,
    ProcessedData,
    ScheduledVisit,
    User,
    UserProfile,
    ValidPhcFacility,
)
from app.models.base import utcnow
from app.models.enums import ConcernCategory, ConcernStatus, ConsentType, UserRole
from app.schemas.auth import RETIRED_CONSENTS, ConsentUpdate, Message, Password
from app.services import sessions
from app.services.catchment import facility_serves_district
from app.services.consent import change_consents, current_consents
from app.services.preferences import Preferences, current_preferences, deep_merge
from app.services.visits import cancel_open_visits

router = APIRouter(prefix="/settings", tags=["settings"])

APP_VERSION = "0.1.0"
EXPORT_READINGS_CAP = 10_000
CONCERN_NOT_FOUND = "Concern not found."


# --- Preferences -----------------------------------------------------------------

@router.get("/preferences", response_model=Preferences)
async def get_preferences(user: User = Depends(require_any_verified)) -> Preferences:
    return current_preferences(user)


@router.patch("/preferences", response_model=Preferences)
async def update_preferences(
    patch: dict[str, Any], user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> Preferences:
    """Any subset, nested keys included. The merged result is validated as a whole."""
    merged = deep_merge(current_preferences(user).model_dump(), patch)
    try:
        prefs = Preferences.model_validate(merged)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_context=False, include_input=False)) from None
    user.preferences = prefs.model_dump()  # a new object, so the JSON column is marked dirty
    await db.commit()
    return prefs


# --- Consents --------------------------------------------------------------------


class ConsentsOut(BaseModel):
    # None: never asked.
    consents: dict[ConsentType, bool | None]


class ConsentHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    consent_type: ConsentType
    granted: bool
    source: str
    created_at: datetime


async def _consents_out(db: AsyncSession, user: User) -> ConsentsOut:
    current = await current_consents(db, user.id)
    return ConsentsOut(consents={t: current.get(t) for t in ConsentType if t not in RETIRED_CONSENTS})


@router.get("/consents", response_model=ConsentsOut)
async def get_consents(user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)) -> ConsentsOut:
    return await _consents_out(db, user)


@router.patch("/consents", response_model=ConsentsOut)
async def update_consents(
    data: ConsentUpdate,
    request: Request,
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> ConsentsOut:
    choices = {c.consent_type: c.granted for c in data.consents}
    await change_consents(db, user, choices, source="settings", ip_address=sessions.client_ip(request))
    await db.commit()
    return await _consents_out(db, user)


@router.get("/consents/history", response_model=list[ConsentHistoryItem])
async def consent_history(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> list[ConsentRecord]:
    rows = await db.scalars(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user.id)
        .order_by(ConsentRecord.created_at.desc(), ConsentRecord.id)
        .limit(limit)
    )
    return list(rows.all())


# --- About and export ------------------------------------------------------------


class DataHeld(BaseModel):
    readings: int
    alerts: int
    visits: int
    concerns: int
    consent_changes: int


class AboutOut(BaseModel):
    app: str
    version: str
    role: UserRole
    facility: str | None
    data_held: DataHeld
    who_can_see: str
    scoring_note: str


async def _count(db: AsyncSession, query) -> int:
    return await db.scalar(query) or 0


@router.get("/about", response_model=AboutOut)
async def about(user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)) -> AboutOut:
    facility = await db.get(ValidPhcFacility, user.phc_id) if user.phc_id else None
    visit_owner = ScheduledVisit.citizen_id if user.role == UserRole.user else ScheduledVisit.worker_id
    if user.role == UserRole.user:
        consents = await current_consents(db, user.id)
        if not facility:
            who = "No health centre is linked to your account, so no health worker can see your readings."
        elif consents.get(ConsentType.phc_worker_access) is False:
            who = (
                f"Nobody at {facility.name}: you turned off health worker access, so your readings, profile and "
                "contact details are hidden from its health workers and they cannot book visits with you."
            )
        else:
            who = f"Health workers at {facility.name} can see your readings, profile and contact details."
        if consents.get(ConsentType.community_surveillance):
            who += " Area-level figures count you, without your name, in groups of at least 3 people."
        else:
            who += " You are left out of area-level figures."
    else:
        who = "Only you. Your own account details are never shown to citizens beyond your name on a booked visit."
    return AboutOut(
        app="HealthNexus",
        version=APP_VERSION,
        role=user.role,
        facility=facility.name if facility else None,
        data_held=DataHeld(
            readings=await _count(db, select(func.count()).where(HealthRecord.user_id == user.id)),
            alerts=await _count(db, select(func.count()).where(Alert.user_id == user.id)),
            visits=await _count(db, select(func.count()).where(visit_owner == user.id)),
            concerns=await _count(db, select(func.count()).where(Concern.user_id == user.id)),
            consent_changes=await _count(db, select(func.count()).where(ConsentRecord.user_id == user.id)),
        ),
        who_can_see=who,
        scoring_note=(
            "Readings are compared with published normal ranges and, once you have about a week of them, with "
            "your own usual values. Heart rate and breathing rate are also checked against a model trained on "
            "71 people's data, shown with each reading. A flag is a prompt to check, not a diagnosis."
        ),
    )


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


@router.get("/export")
async def export(
    request: Request, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> JSONResponse:
    """Everything held about the caller, as one JSON file. Secrets (password and token hashes) are never included."""
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    readings = (
        await db.execute(
            select(HealthRecord, ProcessedData)
            .outerjoin(ProcessedData, ProcessedData.health_record_id == HealthRecord.id)
            .where(HealthRecord.user_id == user.id)
            .order_by(HealthRecord.timestamp)
            .limit(EXPORT_READINGS_CAP)
        )
    ).all()
    alerts = (await db.scalars(select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at))).all()
    visits = (
        await db.scalars(
            select(ScheduledVisit)
            .where((ScheduledVisit.citizen_id == user.id) | (ScheduledVisit.worker_id == user.id))
            .order_by(ScheduledVisit.scheduled_for)
        )
    ).all()
    consents = (
        await db.scalars(select(ConsentRecord).where(ConsentRecord.user_id == user.id).order_by(ConsentRecord.created_at))
    ).all()
    concerns = (await db.scalars(select(Concern).where(Concern.user_id == user.id).order_by(Concern.created_at))).all()

    payload = {
        "exported_at": utcnow().isoformat(),
        "account": {
            k: _iso(getattr(user, k))
            for k in (
                "id", "name", "email", "role", "phone", "bio", "location", "department", "date_of_birth",
                "district", "state", "pincode", "area", "created_at", "preferences",
            )
        },
        "profile": {
            k: _iso(getattr(profile, k))
            for k in (
                "age", "gender", "height_cm", "weight_kg", "blood_group", "existing_conditions",
                "current_medications", "emergency_contact_name", "emergency_contact_phone",
                "has_smartwatch", "smartwatch_brand",
            )
        }
        if profile
        else None,
        "readings": [
            {
                "measured_at": r.timestamp.isoformat(),
                "vitals": r.vitals,
                "symptoms": r.symptoms,
                "flagged": bool(p and p.is_anomaly),
                "anomaly_score": p.anomaly_score if p else None,
                "features": p.features if p else None,
                "reviewed_at": _iso(p.reviewed_at) if p else None,
            }
            for r, p in readings
        ],
        "readings_truncated": len(readings) >= EXPORT_READINGS_CAP,
        "alerts": [
            {"created_at": a.created_at.isoformat(), "severity": a.severity, "message": a.message, "is_read": a.is_read}
            for a in alerts
        ],
        "visits": [
            {"scheduled_for": v.scheduled_for.isoformat(), "status": v.status, "reason": v.reason, "location": v.location}
            for v in visits
        ],
        "consents": [
            {"type": c.consent_type, "granted": c.granted, "source": c.source, "at": c.created_at.isoformat()}
            for c in consents
        ],
        "concerns": [
            {"ticket_ref": c.ticket_ref, "category": c.category, "status": c.status, "created_at": c.created_at.isoformat()}
            for c in concerns
        ],
    }
    db.add(AuditLog(user_id=user.id, action="export_data", entity="users", entity_id=user.id,
                    ip_address=sessions.client_ip(request) or "unknown"))
    await db.commit()
    stamp = utcnow().strftime("%Y%m%d")
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={"Content-Disposition": f'attachment; filename="healthnexus-export-{stamp}.json"'},
    )


# --- Password and deactivation ---------------------------------------------------


class PasswordChange(BaseModel):
    current_password: Annotated[str, Field(min_length=1, max_length=1024)]
    new_password: Password


@router.post("/password", response_model=Message)
async def change_password(
    data: PasswordChange,
    request: Request,
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
    raw_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Message:
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is not correct.")
    if verify_password(data.new_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a password different from your current one.")
    user.hashed_password = hash_password(data.new_password)
    current = await sessions.current_session_id(
        db, user.id, raw_cookie, getattr(request.state, "token_session_id", None)
    )
    await sessions.revoke_all_for_user(db, user.id, sessions.REASON_PASSWORD_RESET, except_id=current)
    await db.commit()
    return Message(detail="Password changed. Your other sessions have been signed out.")


class Deactivate(BaseModel):
    password: Annotated[str, Field(min_length=1, max_length=1024)]
    confirm: Literal["DEACTIVATE"]


@router.post("/deactivate", response_model=Message)
async def deactivate(
    data: Deactivate,
    request: Request,
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your password is not correct.")
    now = utcnow()
    user.is_active = False
    user.deactivated_at = now
    # Nobody should travel to a visit for an account that no longer exists.
    await cancel_open_visits(db, user)
    await sessions.revoke_all_for_user(db, user.id, "deactivated")
    db.add(AuditLog(user_id=user.id, action="deactivate", entity="users", entity_id=user.id,
                    ip_address=sessions.client_ip(request) or "unknown"))
    await db.commit()
    response = JSONResponse({"detail": "Your account has been deactivated."})
    response.delete_cookie(
        REFRESH_COOKIE_NAME, httponly=True, samesite="lax", secure=get_settings().COOKIE_SECURE, path=REFRESH_COOKIE_PATH
    )
    return response


# --- Support concerns -------------------------------------------------------------


class ConcernCreate(BaseModel):
    category: ConcernCategory
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]


class ConcernOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticket_ref: str
    category: ConcernCategory
    description: str
    status: ConcernStatus
    admin_note: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


@router.post("/concerns", response_model=ConcernOut, status_code=status.HTTP_201_CREATED)
async def raise_concern(
    data: ConcernCreate, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> Concern:
    concern = Concern(user_id=user.id, category=data.category, description=data.description)
    db.add(concern)
    await db.commit()
    await db.refresh(concern)
    return concern


@router.get("/concerns", response_model=list[ConcernOut])
async def list_concerns(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> list[Concern]:
    rows = await db.scalars(
        select(Concern).where(Concern.user_id == user.id).order_by(Concern.created_at.desc()).limit(limit)
    )
    return list(rows.all())


@router.get("/concerns/{concern_id}", response_model=ConcernOut)
async def get_concern(
    concern_id: uuid.UUID, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> Concern:
    concern = await db.scalar(select(Concern).where(Concern.id == concern_id, Concern.user_id == user.id))
    if concern is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, CONCERN_NOT_FOUND)
    return concern


# --- The citizen's health centre ------------------------------------------------


class CentreOut(BaseModel):
    id: uuid.UUID
    name: str
    block: str | None
    workers_assigned: int
    is_current: bool


class HealthCentreOut(BaseModel):
    district: str | None
    state: str | None
    current: CentreOut | None
    # Every active centre in the citizen's district, the current one included.
    options: list[CentreOut]


class HealthCentreChange(BaseModel):
    phc_id: uuid.UUID


async def _health_centre(db: AsyncSession, user: User) -> HealthCentreOut:
    if not user.district:
        return HealthCentreOut(district=None, state=user.state, current=None, options=[])
    query = select(ValidPhcFacility).where(
        ValidPhcFacility.is_active.is_(True), func.lower(ValidPhcFacility.district) == user.district.lower()
    )
    if user.state:
        query = query.where(func.lower(ValidPhcFacility.state) == user.state.lower())
    facilities = (await db.scalars(query.order_by(ValidPhcFacility.name).limit(200))).all()
    ids = [f.id for f in facilities] + ([user.phc_id] if user.phc_id else [])
    staffed = dict(
        (
            await db.execute(
                select(User.phc_id, func.count())
                .where(User.phc_id.in_(ids), User.role == UserRole.phc_worker, User.is_active.is_(True))
                .group_by(User.phc_id)
            )
        ).all()
    )

    def out(f: ValidPhcFacility) -> CentreOut:
        return CentreOut(id=f.id, name=f.name, block=f.block, workers_assigned=staffed.get(f.id, 0), is_current=f.id == user.phc_id)

    current = await db.get(ValidPhcFacility, user.phc_id) if user.phc_id else None
    return HealthCentreOut(
        district=user.district,
        state=user.state,
        current=out(current) if current else None,
        options=[out(f) for f in facilities],
    )


@router.get("/health-centre", response_model=HealthCentreOut)
async def get_health_centre(
    user: User = Depends(require_onboarding_user), db: AsyncSession = Depends(get_session)
) -> HealthCentreOut:
    return await _health_centre(db, user)


@router.patch("/health-centre", response_model=HealthCentreOut)
async def change_health_centre(
    data: HealthCentreChange,
    request: Request,
    user: User = Depends(require_onboarding_user),
    db: AsyncSession = Depends(get_session),
) -> HealthCentreOut:
    if not user.district or not await facility_serves_district(db, data.phc_id, user.district, user.state):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose an active health centre in your own district."
        )
    if data.phc_id == user.phc_id:
        return await _health_centre(db, user)
    # Visits booked by the old centre's workers can no longer happen: they lose sight of this person.
    await cancel_open_visits(db, user, unless_phc=data.phc_id)
    user.phc_id = data.phc_id
    db.add(AuditLog(user_id=user.id, action="change_health_centre", entity="valid_phc_facilities",
                    entity_id=data.phc_id, ip_address=sessions.client_ip(request) or "unknown"))
    await db.commit()
    return await _health_centre(db, user)

