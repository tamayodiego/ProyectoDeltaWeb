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

    # Login sessions: a random token in an httpOnly cookie, its hash in user_sessions.
    session_days: int = 30
    # Send the cookie only over HTTPS. None = automatic: off only when environment is
    # "local" (plain http on localhost), on everywhere else, so it cannot be forgotten.
    cookie_secure: bool | None = None

    # Password hashing (Argon2id) costs memory: at most this many hashes run at once,
    # so the peak stays at ~19 MiB each, whatever the traffic.
    password_hash_concurrency: int = 2
    # Rate limits for /auth (in memory, per API process)
    login_attempts_per_ip: int = 10  # per minute
    login_attempts_per_email: int = 5  # per minute
    registrations_per_ip: int = 5  # per hour

    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment != "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
