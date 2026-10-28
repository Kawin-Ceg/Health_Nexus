"""Registration, email verification and password reset."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    EMAIL_RESEND_INTERVAL,
    PASSWORD_RESET_TOKEN_TTL,
    VERIFICATION_TOKEN_TTL,
    burn_password_check,
    hash_password,
    hash_token,
    new_token,
    verify_password,
)
from app.models import PhcApplication, User
from app.models.base import utcnow
from app.models.enums import ApplicationStatus, UserRole
from app.schemas.auth import CitizenRegister, PhcWorkerRegister
from app.services import sessions

EMAIL_TAKEN = "An account with this email already exists."
BAD_LOGIN = "Incorrect email or password."
BAD_VERIFY_LINK = "This verification link is invalid or has expired."
BAD_RESET_LINK = "This reset link is invalid or has expired."


def issue_verification_token(user: User) -> str:
    """Replaces any earlier link: only the newest hash is kept."""
    raw = new_token()
    now = utcnow()
    user.verification_token_hash = hash_token(raw)
    user.verification_token_expires_at = now + VERIFICATION_TOKEN_TTL
    user.verification_sent_at = now
    return raw


def issue_reset_token(user: User) -> str:
    raw = new_token()
    now = utcnow()
    user.password_reset_token_hash = hash_token(raw)
    user.password_reset_expires_at = now + PASSWORD_RESET_TOKEN_TTL
    user.password_reset_sent_at = now
    return raw


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def _create(
    session: AsyncSession, data: CitizenRegister | PhcWorkerRegister, role: UserRole
) -> tuple[User, str]:
    """One transaction: the user, and for a PHC worker the application beside it."""
    if await get_user_by_email(session, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)

    user = User(name=data.name, email=data.email, hashed_password=hash_password(data.password), role=role)
    raw_token = issue_verification_token(user)
    session.add(user)
    try:
        await session.flush()
        if isinstance(data, PhcWorkerRegister):
            session.add(
                PhcApplication(
                    user_id=user.id,
                    employee_id=data.employee_id,
                    designation=data.designation,
                    phc_name=data.phc_name,
                    district=data.district,
                    state=data.state,
                    years_of_service=data.years_of_service,
                    status=ApplicationStatus.pending,
                )
            )
            await session.flush()
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN) from None
    return user, raw_token


async def register_citizen(session: AsyncSession, data: CitizenRegister) -> tuple[User, str]:
    return await _create(session, data, UserRole.user)


async def register_phc_worker(session: AsyncSession, data: PhcWorkerRegister) -> tuple[User, str]:
    return await _create(session, data, UserRole.pending_phc)


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    """One message for a wrong password, an unknown address and a disabled account."""
    user = await get_user_by_email(session, email)
    if user is None:
        burn_password_check(password)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_LOGIN)
    if not verify_password(password, user.hashed_password) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_LOGIN)
    return user


async def prepare_verification_email(session: AsyncSession, user: User) -> str | None:
    """A fresh raw token to mail, or None if the address is already verified."""
    if user.is_verified:
        return None
    now = utcnow()
    if user.verification_sent_at is not None and now - user.verification_sent_at < EMAIL_RESEND_INTERVAL:
        wait = int((EMAIL_RESEND_INTERVAL - (now - user.verification_sent_at)).total_seconds()) + 1
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Please wait {wait} seconds before requesting another email.",
            headers={"Retry-After": str(wait)},
        )
    raw = issue_verification_token(user)
    await session.commit()
    return raw


async def redeem_verification(session: AsyncSession, raw_token: str) -> None:
    """Public: the link is usually opened on a device with no session."""
    user = await session.scalar(
        select(User).where(User.verification_token_hash == hash_token(raw_token)).with_for_update()
    )
    now = utcnow()
    if user is None or user.verification_token_expires_at is None or user.verification_token_expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, BAD_VERIFY_LINK)
    user.is_verified = True
    user.verified_at = now
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    await session.commit()


async def prepare_password_reset(session: AsyncSession, email: str) -> tuple[User, str] | None:
    """A (user, raw token) to mail, or None when nothing should be sent.

    The caller answers identically either way. An address asked about again
    inside the resend interval is skipped so this cannot be used to spam it.
    """
    user = await get_user_by_email(session, email)
    if user is None or not user.is_active:
        return None
    now = utcnow()
    if user.password_reset_sent_at is not None and now - user.password_reset_sent_at < EMAIL_RESEND_INTERVAL:
        return None
    raw = issue_reset_token(user)
    await session.commit()
    return user, raw


async def redeem_password_reset(session: AsyncSession, raw_token: str, new_password: str) -> None:
    user = await session.scalar(
        select(User).where(User.password_reset_token_hash == hash_token(raw_token)).with_for_update()
    )
    now = utcnow()
    if user is None or user.password_reset_expires_at is None or user.password_reset_expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, BAD_RESET_LINK)
    user.hashed_password = hash_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    await sessions.revoke_all_for_user(session, user.id, sessions.REASON_PASSWORD_RESET)
    await session.commit()
