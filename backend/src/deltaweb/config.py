"""Application settings, read from ``DELTAWEB_*`` environment variables or a ``.env`` file."""

from functools import lru_cache
from typing import Literal

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
    # Every email costs provider quota and lands in someone's inbox: keep them rare
    password_resets_per_ip: int = 5  # per hour
    password_resets_per_email: int = 3  # per hour
    verification_emails_per_user: int = 3  # per hour
    # Generation is CPU work in the worker pool: keep one client from hogging it
    generations_per_ip: int = 20  # per minute (/delta-matroids/generate, no login needed)
    saves_per_user: int = 30  # per minute (POST /delta-matroids)

    # One-time links sent by email
    verify_token_hours: int = 24
    reset_token_minutes: int = 60

    # Outgoing email over SMTP. Local defaults point to Mailpit (docker-compose.yml), which
    # catches every message: see them at http://localhost:8025. In production use a
    # provider's SMTP relay, e.g. Resend (smtp.resend.com:587, user "resend", password =
    # API key) or Brevo (smtp-relay.brevo.com:587), with smtp_security="starttls".
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_security: Literal["none", "starttls", "ssl"] = "none"
    smtp_timeout_seconds: float = 10.0
    mail_from: str = "ProyectoDeltaWeb <no-reply@deltaweb.local>"
    # Public address of the web app, used to build the links inside emails
    app_url: str = "http://localhost:5173"

    # Log in with Google / GitHub (OAuth 2.0). Create the apps in Google Cloud Console and
    # GitHub Developer Settings; a provider without client id and secret is disabled.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None
    # Public address of this API: providers redirect back to {api_url}/auth/oauth/...
    api_url: str = "http://localhost:8000"
    oauth_timeout_seconds: float = 10.0

    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment != "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
