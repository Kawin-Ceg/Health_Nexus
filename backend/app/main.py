from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.api.routes.profile import MEDIA_URL, media_root
from app.core.config import get_settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    secret = get_settings().JWT_SECRET_KEY
    if not secret or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set (32+ characters) in backend/.env. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    yield
    await engine.dispose()


app = FastAPI(title="HealthNexus API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Uploaded profile images. File names are random, so a URL cannot be guessed from an id.
media_root().mkdir(parents=True, exist_ok=True)
app.mount(MEDIA_URL, StaticFiles(directory=media_root()), name="media")
