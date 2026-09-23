from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/healthnexus"

    # Auth. Optional here so Alembic and the seed scripts import this module
    # without it; the API itself refuses to start without one (see main.py).
    JWT_SECRET_KEY: str | None = None
    # False so the refresh cookie works over plain http in development.
    COOKIE_SECURE: bool = False
    # Where the email links point, and which browser origins may call the API
    # directly (comma-separated). Through the Vite proxy the API is same-origin.
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173"

    # Outgoing mail. With no SMTP_HOST every message is printed to the console.
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "HealthNexus <no-reply@healthnexus.local>"
    SMTP_STARTTLS: bool = True

    # Seed scripts
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_NAME: str = "HealthNexus Admin"
    PHC_WORKER_EMAIL: str = "phc.worker@example.com"
    PHC_WORKER_PASSWORD: str | None = None
    DEMO_CITIZEN_PASSWORD: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
