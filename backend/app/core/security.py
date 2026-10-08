import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

ACCESS_TOKEN_TTL = timedelta(minutes=get_settings().ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_TTL = timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS)
# A refresh token unused for this long is rejected even though it has not expired.
REFRESH_IDLE_TIMEOUT = timedelta(hours=48)
# A token rotated this recently and presented again is a race between two tabs,
# not theft: reject it, but leave the session alone.
REFRESH_REUSE_GRACE = timedelta(seconds=10)
VERIFICATION_TOKEN_TTL = timedelta(hours=24)
PASSWORD_RESET_TOKEN_TTL = timedelta(hours=1)
EMAIL_RESEND_INTERVAL = timedelta(seconds=60)

REFRESH_COOKIE_NAME = "hn_refresh"
# Only ever sent to the auth endpoints.
REFRESH_COOKIE_PATH = "/api/v1/auth"

# Fixed on purpose: an environment-supplied algorithm is a way in for
# "alg: none" and key-confusion attacks.
JWT_ALGORITHM = "HS256"

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check, for logins that name no account."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = _pwd.hash(secrets.token_urlsafe(16))
    _pwd.verify(password, _dummy_hash)


def new_token() -> str:
    """A raw token for an email link or cookie. Only its hash is ever stored."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """SHA-256 hex digest: the only form in which tokens are persisted."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class InvalidAccessToken(Exception):
    pass


def _secret() -> str:
    secret = get_settings().JWT_SECRET_KEY
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not set")
    return secret


def create_access_token(user_id: uuid.UUID, role: str, session_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "sid": str(session_id),
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
    }
    return jwt.encode(claims, _secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        uuid.UUID(claims["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise InvalidAccessToken from exc
    return claims
