"""Tests run against a real Postgres that Alembic has already migrated.

    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/healthnexus_test pytest

The database name must end in `_test`: the fixtures TRUNCATE the user tables
between tests, and must never be pointed at real data.
"""

import os

import pytest

_url = os.environ.get("TEST_DATABASE_URL", "")
if not _url.rsplit("/", 1)[-1].endswith("_test"):
    pytest.exit("Set TEST_DATABASE_URL to a migrated database whose name ends in '_test'.", returncode=2)

# Before any app import, so Settings and the module-level engine see them.
os.environ["DATABASE_URL"] = _url
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-0123456789"
os.environ["SMTP_HOST"] = ""

from collections.abc import AsyncIterator  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402

BASE = "/api/v1"
PASSWORD = "correct horse battery"


@dataclass
class Outbox:
    """Raw tokens the app 'emailed', in order. The database only ever holds their hashes."""

    verification: list[tuple[str, str]] = field(default_factory=list)  # (to, token)
    reset: list[tuple[str, str]] = field(default_factory=list)


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    box = Outbox()

    async def verification(to: str, name: str, token: str) -> None:
        box.verification.append((to, token))

    async def reset(to: str, name: str, token: str) -> None:
        box.reset.append((to, token))

    monkeypatch.setattr("app.api.routes.auth.send_verification_email", verification)
    monkeypatch.setattr("app.api.routes.auth.send_password_reset_email", reset)
    return box


@pytest.fixture
async def engine():
    eng = create_async_engine(_url, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE users, refresh_tokens, user_profiles, phc_applications, consent_records "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
async def client(engine, outbox: Outbox) -> AsyncIterator[AsyncClient]:
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def anon(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """A second client with its own empty cookie jar: another device."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


async def register_and_login(
    client: AsyncClient, outbox: Outbox, email: str = "asha@example.com", *, verify: bool = True
) -> dict[str, str]:
    """A citizen, optionally verified, signed in on `client`. Returns the Authorization header."""
    r = await client.post(f"{BASE}/auth/register/citizen", json={"name": "Asha", "email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    if verify:
        token = outbox.verification[-1][1]
        assert (await client.post(f"{BASE}/auth/email/verify", json={"token": token})).status_code == 200
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
