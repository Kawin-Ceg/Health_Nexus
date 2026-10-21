"""The health-centre registry, managed by admins: add, edit, deactivate and reactivate centres."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_session
from app.models import AuditLog, User, ValidPhcFacility
from app.models.enums import UserRole
from app.services import sessions
from app.services.phc_registry import normalise_facility_name

from .admin import area_of, in_area

router = APIRouter(prefix="/admin/registry", tags=["admin"], dependencies=[Depends(require_admin)])

NOT_FOUND = "Health centre not found."
CODE_TAKEN = "Another health centre already uses that code."

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
Optional = Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None


class CentreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facility_code: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{2,63}$")]
    name: Text
    district: Text
    state: Text
    block: Optional = None
    official_email_domain: Optional = None
    latitude: Annotated[float, Field(ge=-90, le=90)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180)] | None = None

    @model_validator(mode="after")
    def _both_or_neither(self) -> "CentreIn":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Give both latitude and longitude, or neither")
        return self


class CentrePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Text | None = None
    district: Text | None = None
    state: Text | None = None
    block: Optional = None
    official_email_domain: Optional = None
    latitude: Annotated[float, Field(ge=-90, le=90)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180)] | None = None


class CentreOut(BaseModel):
    id: uuid.UUID
    facility_code: str
    name: str
    district: str
    state: str
    block: str | None
    official_email_domain: str | None
    latitude: float | None
    longitude: float | None
    is_active: bool
    is_placeholder: bool
    workers: int
    citizens: int


class CentresOut(BaseModel):
    items: list[CentreOut]
    total: int
    districts: list[str]


def _counts():
    return (
        select(
            User.phc_id,
            func.count().filter(User.role == UserRole.phc_worker).label("workers"),
            func.count().filter(User.role == UserRole.user).label("citizens"),
        )
        .where(User.phc_id.is_not(None), User.is_active.is_(True))
        .group_by(User.phc_id)
        .subquery()
    )


async def _out(db: AsyncSession, facility_id: uuid.UUID) -> CentreOut:
    linked = _counts()
    row = (
        await db.execute(
            select(ValidPhcFacility, linked.c.workers, linked.c.citizens)
            .outerjoin(linked, linked.c.phc_id == ValidPhcFacility.id)
            .where(ValidPhcFacility.id == facility_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return _centre(*row)


def _centre(f: ValidPhcFacility, workers: int | None, citizens: int | None) -> CentreOut:
    return CentreOut(
        id=f.id, facility_code=f.facility_code, name=f.name, district=f.district, state=f.state, block=f.block,
        official_email_domain=f.official_email_domain, latitude=f.latitude, longitude=f.longitude,
        is_active=f.is_active, is_placeholder=f.is_placeholder, workers=workers or 0, citizens=citizens or 0,
    )


def _audit(db: AsyncSession, admin: User, action: str, facility_id: uuid.UUID, request: Request) -> None:
    db.add(AuditLog(user_id=admin.id, action=action, entity="valid_phc_facilities", entity_id=facility_id,
                    ip_address=sessions.client_ip(request) or "unknown"))


@router.get("", response_model=CentresOut)
async def list_centres(
    q: str | None = Query(None, max_length=120),
    district: str | None = Query(None, max_length=120),
    state: Literal["active", "inactive", "all"] = "all",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> CentresOut:
    filters = [in_area(ValidPhcFacility.district, area_of(admin))]
    if q:
        like = f"%{q.strip()}%"
        filters.append(or_(
            ValidPhcFacility.name.ilike(like),
            ValidPhcFacility.facility_code.ilike(like),
            ValidPhcFacility.block.ilike(like),
            ValidPhcFacility.normalised_name.ilike(f"%{normalise_facility_name(q)}%"),
        ))
    if district:
        filters.append(ValidPhcFacility.district.ilike(district.strip()))
    if state != "all":
        filters.append(ValidPhcFacility.is_active.is_(state == "active"))

    linked = _counts()
    rows = await db.execute(
        select(ValidPhcFacility, linked.c.workers, linked.c.citizens)
        .outerjoin(linked, linked.c.phc_id == ValidPhcFacility.id)
        .where(*filters)
        .order_by(ValidPhcFacility.district, ValidPhcFacility.name)
        .limit(limit)
        .offset(offset)
    )
    total = await db.scalar(select(func.count()).select_from(ValidPhcFacility).where(*filters)) or 0
    districts = (
        await db.scalars(
            select(ValidPhcFacility.district).where(in_area(ValidPhcFacility.district, area_of(admin))).distinct().order_by(ValidPhcFacility.district)
        )
    ).all()
    return CentresOut(items=[_centre(*r) for r in rows.all()], total=total, districts=list(districts))


@router.post("", response_model=CentreOut, status_code=status.HTTP_201_CREATED)
async def create_centre(
    data: CentreIn, request: Request, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_session)
) -> CentreOut:
    facility = ValidPhcFacility(**data.model_dump(), normalised_name=normalise_facility_name(data.name), is_placeholder=False)
    db.add(facility)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, CODE_TAKEN) from None
    _audit(db, admin, "create_health_centre", facility.id, request)
    await db.commit()
    return await _out(db, facility.id)


async def _load(db: AsyncSession, facility_id: uuid.UUID) -> ValidPhcFacility:
    facility = await db.get(ValidPhcFacility, facility_id, with_for_update=True)
    if facility is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return facility


@router.patch("/{facility_id}", response_model=CentreOut)
async def edit_centre(
    facility_id: uuid.UUID,
    data: CentrePatch,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> CentreOut:
    facility = await _load(db, facility_id)
    changes = data.model_dump(exclude_unset=True)
    for key in ("name", "district", "state"):
        if key in changes and changes[key] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{key.capitalize()} cannot be empty.")
    lat = changes.get("latitude", facility.latitude)
    lng = changes.get("longitude", facility.longitude)
    if (lat is None) != (lng is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Give both latitude and longitude, or neither.")
    for key, value in changes.items():
        setattr(facility, key, value)
    if "name" in changes:
        facility.normalised_name = normalise_facility_name(facility.name)
    if changes:
        # An admin has checked it: no longer a seeded placeholder.
        facility.is_placeholder = False
        _audit(db, admin, "edit_health_centre", facility.id, request)
    await db.commit()
    return await _out(db, facility.id)


@router.post("/{facility_id}/deactivate", response_model=CentreOut)
async def deactivate_centre(
    facility_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_session)
) -> CentreOut:
    """New citizens and applicants can no longer choose it. People already linked keep their link until moved."""
    facility = await _load(db, facility_id)
    if facility.is_active:
        facility.is_active = False
        _audit(db, admin, "deactivate_health_centre", facility.id, request)
        await db.commit()
    return await _out(db, facility.id)


@router.post("/{facility_id}/reactivate", response_model=CentreOut)
async def reactivate_centre(
    facility_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_session)
) -> CentreOut:
    facility = await _load(db, facility_id)
    if not facility.is_active:
        facility.is_active = True
        _audit(db, admin, "reactivate_health_centre", facility.id, request)
        await db.commit()
    return await _out(db, facility.id)
