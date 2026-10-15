"""Shared fixtures.

Domain tests (matrix, fingerprint, golden...) need nothing from here. Tests that ask
for ``session``, ``client`` (logged in) or ``anonymous_client`` get a real PostgreSQL in
a throwaway Docker container (Testcontainers), migrated with Alembic. Docker (OrbStack)
must be running.

Each test runs inside a transaction that is rolled back at the end, so tests never see
each other's data and the database is not recreated for every test.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from deltaweb.api import auth as auth_api
from deltaweb.api import delta_matroids as delta_matroids_api
from deltaweb.api.auth import LIMITERS as AUTH_LIMITERS
from deltaweb.db import get_session
from deltaweb.main import app
from deltaweb.models import User
from deltaweb.services.auth import SESSION_COOKIE, create_session
from deltaweb.services.passwords import hash_password

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def reset_rate_limits() -> Iterator[None]:
    """Every test starts with clean rate-limit counters (they live in memory, in the process)."""
    for limiter in (*AUTH_LIMITERS, *delta_matroids_api.LIMITERS):
        limiter.reset()
    yield


@dataclass
class SentEmail:
    """An email caught by ``inbox``; ``token`` is read from its link."""

    to: str
    subject: str
    html: str
    text: str

    @property
    def token(self) -> str:
        match = re.search(r"token=([\w-]+)", self.text)
        assert match, self.text
        return match.group(1)


@pytest.fixture(autouse=True)
def inbox(monkeypatch: pytest.MonkeyPatch) -> list[SentEmail]:
    """Catch every email instead of sending it; tests can read them from the list."""
    sent: list[SentEmail] = []
    monkeypatch.setattr(auth_api, "send_email", lambda *args: sent.append(SentEmail(*args)))
    return sent


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    with PostgresContainer("postgres:17", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", url)
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(url)
        yield engine
        engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose changes, even ``commit()``, are undone after the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        # commit() inside the code under test only releases a SAVEPOINT
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def anonymous_client(session: Session) -> Iterator[TestClient]:
    """HTTP client whose requests use the test session, not logged in."""
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def current_user(session: Session) -> User:
    """The user that ``client`` is logged in as."""
    user = User(email="me@example.com", password_hash=hash_password("Sup3r-secret"))
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def client(anonymous_client: TestClient, session: Session, current_user: User) -> TestClient:
    """HTTP client logged in as ``current_user`` (session cookie already set)."""
    anonymous_client.cookies.set(SESSION_COOKIE, create_session(session, current_user))
    return anonymous_client
