"""Refresh-token sessions: issue, rotate, revoke.

A session is one live row in refresh_tokens. Rotating swaps it for a new row
(`rotated_from` links back), so the chain of rows for one login is a linked list.
Only SHA-256 digests are stored; the raw token exists in the cookie alone.
"""

import re
import uuid
from datetime import datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    REFRESH_IDLE_TIMEOUT,
    REFRESH_REUSE_GRACE,
    REFRESH_TOKEN_TTL,
    hash_token,
    new_token,
)
from app.models import RefreshToken, User
from app.models.base import utcnow

ALREADY_USED = "Refresh token already used."

REASON_ROTATED = "rotated"
REASON_LOGOUT = "logout"
REASON_INACTIVITY = "inactivity"
REASON_REUSE = "reuse_detected"
REASON_USER_REVOKED = "revoked_by_user"
REASON_PASSWORD_RESET = "password_reset"

_BROWSERS = [("Edg", "Edge"), ("OPR", "Opera"), ("Firefox", "Firefox"), ("Chrome", "Chrome"), ("Safari", "Safari")]
_SYSTEMS = [
    ("Windows", "Windows"),
    ("Android", "Android"),
    ("iPhone", "iOS"),
    ("iPad", "iOS"),
    ("Mac OS X", "macOS"),
    ("Linux", "Linux"),
]


def device_label(user_agent: str | None) -> str:
    """'Chrome on Windows': enough to recognise a session, no fingerprinting."""
    if not user_agent:
        return "Unknown device"
    browser = next((label for token, label in _BROWSERS if token in user_agent), None)
    system = next((label for token, label in _SYSTEMS if token in user_agent), None)
    if browser and system:
        return f"{browser} on {system}"
    return browser or system or "Unknown device"


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _unauthorised(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail)


def _new_row(user_id: uuid.UUID, request: Request, now: datetime, rotated_from: uuid.UUID | None) -> tuple[str, RefreshToken]:
    raw = new_token()
    user_agent = request.headers.get("user-agent")
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw),
        expires_at=now + REFRESH_TOKEN_TTL,
        last_activity_at=now,
        user_agent=(user_agent or "")[:512] or None,
        ip_address=client_ip(request),
        device_label=device_label(user_agent),
        rotated_from=rotated_from,
    )
    return raw, row


async def start_session(session: AsyncSession, user: User, request: Request) -> tuple[str, RefreshToken]:
    raw, row = _new_row(user.id, request, utcnow(), None)
    session.add(row)
    await session.flush()
    return raw, row


async def _revoke_chain(session: AsyncSession, start_id: uuid.UUID, reason: str) -> None:
    """Revoke every still-live descendant of a reused token, i.e. the thief's copy."""
    chain = select(RefreshToken.id).where(RefreshToken.id == start_id).cte("chain", recursive=True)
    chain = chain.union_all(select(RefreshToken.id).where(RefreshToken.rotated_from == chain.c.id))
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.id.in_(select(chain.c.id)), RefreshToken.revoked.is_(False))
        .values(revoked=True, revoked_at=utcnow(), revoked_reason=reason)
    )


async def rotate_session(session: AsyncSession, raw_token: str, request: Request) -> tuple[User, RefreshToken, str]:
    """Validate a presented refresh token and swap it for a fresh one.

    Every rejection that changes state commits before raising, because the
    request's session would otherwise roll it back on the way out.
    """
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)).with_for_update()
    )
    if row is None:
        raise _unauthorised("Invalid refresh token.")

    now = utcnow()
    if row.revoked:
        if row.revoked_reason == REASON_ROTATED:
            if row.revoked_at is not None and now - row.revoked_at <= REFRESH_REUSE_GRACE:
                raise _unauthorised(ALREADY_USED)
            await _revoke_chain(session, row.id, REASON_REUSE)
            await session.commit()
            raise _unauthorised("Refresh token reuse detected. Please sign in again.")
        raise _unauthorised("This session has ended. Please sign in again.")

    if row.expires_at <= now:
        raise _unauthorised("Your session has expired. Please sign in again.")

    if now - row.last_activity_at > REFRESH_IDLE_TIMEOUT:
        row.revoked, row.revoked_at, row.revoked_reason = True, now, REASON_INACTIVITY
        await session.commit()
        raise _unauthorised("You were signed out due to inactivity.")

    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        row.revoked, row.revoked_at, row.revoked_reason = True, now, REASON_LOGOUT
        await session.commit()
        raise _unauthorised("This session has ended. Please sign in again.")

    raw, new_row = _new_row(user.id, request, now, rotated_from=row.id)
    row.revoked, row.revoked_at, row.revoked_reason = True, now, REASON_ROTATED
    session.add(new_row)
    await session.commit()
    return user, new_row, raw


async def revoke_by_token(session: AsyncSession, raw_token: str, reason: str) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw_token), RefreshToken.revoked.is_(False))
        .values(revoked=True, revoked_at=utcnow(), revoked_reason=reason)
    )


def revoke_row(row: RefreshToken, reason: str) -> None:
    row.revoked, row.revoked_at, row.revoked_reason = True, utcnow(), reason


async def revoke_all_for_user(
    session: AsyncSession, user_id: uuid.UUID, reason: str, *, except_id: uuid.UUID | None = None
) -> None:
    stmt = update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
    if except_id is not None:
        stmt = stmt.where(RefreshToken.id != except_id)
    await session.execute(stmt.values(revoked=True, revoked_at=utcnow(), revoked_reason=reason))


async def active_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[RefreshToken]:
    now = utcnow()
    rows = await session.scalars(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > now,
            RefreshToken.last_activity_at > now - REFRESH_IDLE_TIMEOUT,
        )
        .order_by(RefreshToken.last_activity_at.desc())
    )
    return list(rows)


async def current_session_id(
    session: AsyncSession, user_id: uuid.UUID, raw_cookie: str | None, token_sid: str | None
) -> uuid.UUID | None:
    """The caller's own session: by refresh cookie when present, else by the access token's `sid`."""
    if raw_cookie:
        found = await session.scalar(
            select(RefreshToken.id).where(
                RefreshToken.token_hash == hash_token(raw_cookie),
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
        )
        if found:
            return found
    if token_sid and re.fullmatch(r"[0-9a-fA-F-]{36}", token_sid):
        return uuid.UUID(token_sid)
    return None
