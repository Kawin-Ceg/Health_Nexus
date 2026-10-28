"""Auth dependencies. Identity and role always come from the token and the database, never the request body.

Put a guard on the APIRouter (`dependencies=[Depends(...)]`) when every route in it
shares one role; routes that need the user still declare the dependency, and
FastAPI resolves it once per request.
"""

import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import InvalidAccessToken, decode_access_token
from app.db.session import get_session
from app.models import User
from app.models.enums import UserRole

_bearer = HTTPBearer(auto_error=False)

APP_ROLES = frozenset({UserRole.user, UserRole.phc_worker, UserRole.admin})


def _unauthenticated(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise _unauthenticated("Not authenticated.")
    try:
        claims = decode_access_token(credentials.credentials)
    except InvalidAccessToken:
        raise _unauthenticated("Invalid or expired access token.") from None

    user = await session.get(User, uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise _unauthenticated("Invalid or expired access token.")
    request.state.token_session_id = claims.get("sid")
    return user


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail)


async def require_user(user: User = Depends(get_current_user)) -> User:
    """A citizen."""
    if user.role != UserRole.user:
        raise _forbidden("This area is for citizen accounts.")
    return user


async def require_phc_worker(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.phc_worker:
        raise _forbidden("This area is for approved PHC workers.")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise _forbidden("This area is for administrators.")
    return user


async def require_onboarding_user(user: User = Depends(require_user)) -> User:
    """A citizen who has confirmed their email: onboarding comes after verification."""
    if not user.is_verified:
        raise _forbidden("Verify your email address to continue.")
    return user


async def require_any_verified(user: User = Depends(get_current_user)) -> User:
    """Any approved role, with a confirmed email. A pending_phc account is not yet approved."""
    if user.role not in APP_ROLES:
        raise _forbidden("Your account is not active yet.")
    if not user.is_verified:
        raise _forbidden("Verify your email address to continue.")
    return user
