"""The database setup works: migrations ran and the demo user exists only once."""

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from deltaweb.api.deps import DEMO_EMAIL, get_current_user
from deltaweb.models import User


def test_migrations_created_the_users_table(session: Session) -> None:
    assert "users" in inspect(session.connection()).get_table_names()


def test_demo_user_is_created_once(session: Session) -> None:
    first = get_current_user(session)
    second = get_current_user(session)

    assert first.id == second.id
    assert first.email == DEMO_EMAIL
    assert session.scalar(select(func.count()).select_from(User)) == 1
