"""The signed-in person's own profile: details, avatar and cover images, and changing their email."""

import re
import secrets
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import require_any_verified
from app.core.security import EMAIL_RESEND_INTERVAL, VERIFICATION_TOKEN_TTL, hash_token, new_token, verify_password
from app.db.session import get_session
from app.models import PhcApplication, User, ValidPhcFacility
from app.models.base import utcnow
from app.models.enums import Designation, UserRole
from app.schemas.auth import Email, Message, TokenRequest
from app.services.mailer import send_email_change_email, send_email_changed_notice

router = APIRouter(prefix="/profile", tags=["profile"])

MEDIA_URL = "/api/v1/media"
Kind = Literal["avatars", "covers"]
MAX_BYTES: dict[str, int] = {"avatars": 2 * 1024 * 1024, "covers": 5 * 1024 * 1024}
# Sniffed from the bytes, never trusted from the filename or Content-Type.
SIGNATURES = ((b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"))


def _blank_to_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


def _check_phone(value: str) -> str:
    if not re.fullmatch(r"\+?[0-9]{7,15}", re.sub(r"[\s\-()]", "", value)):
        raise ValueError("Enter a valid phone number")
    return value


def _check_dob(value: date) -> date:
    if not date(1900, 1, 1) <= value < date.today():
        raise ValueError("Enter a real date of birth")
    return value


def _optional(max_length: int):
    return Annotated[
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=max_length)] | None,
        BeforeValidator(_blank_to_none),
    ]


class ProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    pending_email: str | None
    role: UserRole
    phone: str | None
    bio: str | None
    location: str | None
    department: str | None
    date_of_birth: date | None
    avatar_url: str | None
    cover_url: str | None
    facility: str | None
    designation: Designation | None
    created_at: datetime


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None
    phone: Annotated[
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=25), AfterValidator(_check_phone)] | None,
        BeforeValidator(_blank_to_none),
    ] = None
    bio: _optional(280) = None
    location: _optional(120) = None
    department: _optional(120) = None
    date_of_birth: Annotated[date, AfterValidator(_check_dob)] | None = None


async def _profile_out(db: AsyncSession, user: User) -> ProfileOut:
    facility = await db.get(ValidPhcFacility, user.phc_id) if user.phc_id else None
    designation = None
    if user.role == UserRole.phc_worker:
        designation = await db.scalar(select(PhcApplication.designation).where(PhcApplication.user_id == user.id))
    return ProfileOut(
        id=user.id,
        name=user.name,
        email=user.email,
        pending_email=user.pending_email
        if user.email_token_expires_at is not None and user.email_token_expires_at > utcnow()
        else None,
        role=user.role,
        phone=user.phone,
        bio=user.bio,
        location=user.location,
        department=user.department,
        date_of_birth=user.date_of_birth,
        avatar_url=user.avatar_url,
        cover_url=user.cover_url,
        facility=facility.name if facility else None,
        designation=designation,
        created_at=user.created_at,
    )


@router.get("", response_model=ProfileOut)
async def get_profile(user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)) -> ProfileOut:
    return await _profile_out(db, user)


@router.patch("", response_model=ProfileOut)
async def update_profile(
    data: ProfilePatch, user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> ProfileOut:
    sent = data.model_dump(exclude_unset=True)
    if "name" in sent and sent["name"] is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Your name cannot be empty.")
    for key, value in sent.items():
        setattr(user, key, value)
    await db.commit()
    return await _profile_out(db, user)


# --- Images ----------------------------------------------------------------------


def media_root() -> Path:
    return Path(get_settings().MEDIA_DIR).resolve()


def _sniff(head: bytes) -> str | None:
    for signature, ext in SIGNATURES:
        if head.startswith(signature):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _remove_old(url: str | None, kind: Kind) -> None:
    """Delete a file we stored earlier. Only ever inside our own media folder."""
    prefix = f"{MEDIA_URL}/{kind}/"
    if not url or not url.startswith(prefix):
        return
    name = url.removeprefix(prefix)
    if "/" in name or "\\" in name or name.startswith("."):
        return
    (media_root() / kind / name).unlink(missing_ok=True)


async def _store(file: UploadFile, kind: Kind, user: User) -> str:
    limit = MAX_BYTES[kind]
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Images must be {limit // (1024 * 1024)} MB or smaller.")
    ext = _sniff(content[:16])
    if ext is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a PNG, JPEG or WebP image.")
    folder = media_root() / kind
    folder.mkdir(parents=True, exist_ok=True)
    # Unguessable name, so a URL cannot be derived from a user id.
    name = f"{secrets.token_urlsafe(18)}.{ext}"
    (folder / name).write_bytes(content)
    _remove_old(user.avatar_url if kind == "avatars" else user.cover_url, kind)
    return f"{MEDIA_URL}/{kind}/{name}"


@router.post("/avatar", response_model=ProfileOut)
async def upload_avatar(
    file: UploadFile = File(...), user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> ProfileOut:
    user.avatar_url = await _store(file, "avatars", user)
    await db.commit()
    return await _profile_out(db, user)


@router.delete("/avatar", response_model=ProfileOut)
async def remove_avatar(user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)) -> ProfileOut:
    _remove_old(user.avatar_url, "avatars")
    user.avatar_url = None
    await db.commit()
    return await _profile_out(db, user)


@router.post("/cover", response_model=ProfileOut)
async def upload_cover(
    file: UploadFile = File(...), user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)
) -> ProfileOut:
    user.cover_url = await _store(file, "covers", user)
    await db.commit()
    return await _profile_out(db, user)


@router.delete("/cover", response_model=ProfileOut)
async def remove_cover(user: User = Depends(require_any_verified), db: AsyncSession = Depends(get_session)) -> ProfileOut:
    _remove_old(user.cover_url, "covers")
    user.cover_url = None
    await db.commit()
    return await _profile_out(db, user)


# --- Email change ------------------------------------------------------------------

EMAIL_TAKEN = "An account with this email already exists."
BAD_EMAIL_LINK = "This confirmation link is invalid or has expired."


class EmailChange(BaseModel):
    new_email: Email
    password: Annotated[str, Field(min_length=1, max_length=1024)]


@router.post("/email", response_model=Message)
async def request_email_change(
    data: EmailChange,
    background: BackgroundTasks,
    user: User = Depends(require_any_verified),
    db: AsyncSession = Depends(get_session),
) -> Message:
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your password is not correct.")
    if data.new_email == user.email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That is already your email address.")
    if await db.scalar(select(User.id).where(User.email == data.new_email)):
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)
    now = utcnow()
    sent_at = user.email_token_expires_at - VERIFICATION_TOKEN_TTL if user.email_token_expires_at else None
    if sent_at and user.pending_email == data.new_email and now - sent_at < EMAIL_RESEND_INTERVAL:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Please wait a minute before asking for another email.")
    raw = new_token()
    user.pending_email = data.new_email
    user.email_token_hash = hash_token(raw)
    user.email_token_expires_at = now + VERIFICATION_TOKEN_TTL
    await db.commit()
    background.add_task(send_email_change_email, data.new_email, user.name, raw)
    return Message(detail=f"We sent a confirmation link to {data.new_email}. Your current address works until you confirm.")


@router.post("/email/confirm", response_model=Message)
async def confirm_email_change(
    data: TokenRequest, background: BackgroundTasks, db: AsyncSession = Depends(get_session)
) -> Message:
    """Public, like email verification: the link is often opened on a device with no session."""
    user = await db.scalar(select(User).where(User.email_token_hash == hash_token(data.token)).with_for_update())
    now = utcnow()
    if (
        user is None
        or user.pending_email is None
        or user.email_token_expires_at is None
        or user.email_token_expires_at <= now
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, BAD_EMAIL_LINK)
    old, new = user.email, user.pending_email
    user.email = new
    user.email_verified = True
    user.pending_email = None
    user.email_token_hash = None
    user.email_token_expires_at = None
    try:
        await db.commit()
    except IntegrityError:  # someone registered the address in the meantime
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN) from None
    background.add_task(send_email_changed_notice, old, user.name, new)
    return Message(detail="Your email address has been changed. Use it next time you sign in.")
