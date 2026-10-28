import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/healthnexus"

    JWT_SECRET_KEY: str | None = None
    COOKIE_SECURE: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173"

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "HealthNexus <no-reply@healthnexus.local>"
    SMTP_STARTTLS: bool = True
    READING_REMINDERS: bool = True
    OUTBREAK_CLUSTERING: bool = True

    POPULATION_MODEL_PATH: str | None = None

    GEMINI_API_KEY: str | None = None
    GEMINI_API_KEYS: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    ASSISTANT_QUESTIONS_PER_MINUTE: int = 20

    MEDIA_DIR: str = "media"
    PRIVATE_UPLOAD_DIR: str = "private_uploads"
    TESSERACT_CMD: str | None = None

    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_NAME: str = "HealthNexus Admin"
    PHC_WORKER_EMAIL: str = "phc.worker@example.com"
    PHC_WORKER_PASSWORD: str | None = None
    DEMO_CITIZEN_PASSWORD: str | None = None
    DEMO_MODE: bool = False
    DEMO_PASSWORD: str | None = None

    @property
    def gemini_keys(self) -> list[str]:
        raw = ",".join(k for k in (self.GEMINI_API_KEY, self.GEMINI_API_KEYS) if k)
        return [k.strip() for k in raw.split(",") if k.strip() and k.strip() not in ("key1", "key2")]

    @property
    def cors_origins(self) -> list[str]:
        """Accepts a comma-separated list or a JSON array.

        Both spellings turn up in .env files, and a mis-parsed origin fails
        silently: the browser just refuses every request.
        """
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = []
            if isinstance(parsed, list):
                return [str(o).strip() for o in parsed if str(o).strip()]
        return [o.strip().strip('"').strip("'") for o in raw.split(",") if o.strip().strip('"').strip("'")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
