"""Application settings, read from ``DELTAWEB_*`` environment variables or a ``.env`` file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DELTAWEB_", env_file=".env", extra="ignore")

    app_name: str = "ProyectoDeltaWeb API"
    environment: str = "local"  # local | dev | prod
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
