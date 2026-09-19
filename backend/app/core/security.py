import hashlib
import secrets

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def new_token() -> str:
    """A raw token for an email link or cookie. Only its hash is ever stored."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """SHA-256 hex digest: the only form in which tokens are persisted."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
