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

    # Delta-matroid generation runs in separate processes (2^n subsets, CPU-bound).
    # The VPS has 2 vCPU: 2 workers use both without starving the API process.
    generation_workers: int = 2
    generation_timeout_seconds: float = 30.0
    max_matrix_size: int = 15  # n = 15 takes ~0.3 s locally; every +1 doubles it


@lru_cache
def get_settings() -> Settings:
    return Settings()
