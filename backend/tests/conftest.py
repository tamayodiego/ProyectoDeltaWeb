"""Shared fixtures.

Domain tests (matrix, fingerprint, golden...) need nothing from here. Tests that ask for
``session`` or ``client`` get a real PostgreSQL in a throwaway Docker container
(Testcontainers), migrated with Alembic. Docker (OrbStack) must be running.

Each test runs inside a transaction that is rolled back at the end, so tests never see
each other's data and the database is not recreated for every test.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from deltaweb.db import get_session
from deltaweb.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]


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
def client(session: Session) -> Iterator[TestClient]:
    """HTTP client whose requests use the test session."""
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
