from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/healthnexus"

    # Seed scripts
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_NAME: str = "HealthNexus Admin"
    PHC_WORKER_EMAIL: str = "phc.worker@example.com"
    PHC_WORKER_PASSWORD: str | None = None
    DEMO_CITIZEN_PASSWORD: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
