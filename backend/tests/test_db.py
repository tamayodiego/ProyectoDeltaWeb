"""The database setup works: migrations ran."""

from sqlalchemy import inspect
from sqlalchemy.orm import Session


def test_migrations_created_the_users_table(session: Session) -> None:
    assert "users" in inspect(session.connection()).get_table_names()
