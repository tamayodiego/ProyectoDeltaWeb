"""Application settings, read from ``DELTAWEB_*`` environment variables or a ``.env`` file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DELTAWEB_", env_file=".env", extra="ignore")

    app_name: str = "ProyectoDeltaWeb API"
    environment: str = "local"  # local | dev | prod
    debug: bool = False
    # Local default matches docker-compose.yml; dev and prod set DELTAWEB_DATABASE_URL
    database_url: str = "postgresql+psycopg://delta:delta_local_pw@localhost:5432/delta_dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
