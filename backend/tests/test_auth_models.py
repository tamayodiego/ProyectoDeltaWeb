"""Auth tables: users, sessions and linked Google/GitHub accounts (needs Docker)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from deltaweb.models import OAuthAccount, User, UserSession


@pytest.fixture
def user(session: Session) -> User:
    user = User(email="ana@deltaweb.local")
    session.add(user)
    session.flush()
    return user


def new_session(user: User, token_hash: str = "a" * 64) -> UserSession:
    return UserSession(
        user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(days=30)
    )


# --- users ---


def test_new_user_has_no_password_and_is_not_verified(session: Session, user: User) -> None:
    session.refresh(user)

    assert user.password_hash is None
    assert user.email_verified_at is None


def test_user_with_password_and_verified_email(session: Session) -> None:
    verified = User(
        email="bob@deltaweb.local",
        password_hash="$argon2id$v=19$...",
        email_verified_at=datetime.now(UTC),
    )
    session.add(verified)
    session.flush()

    assert verified.id is not None


def test_email_must_be_lowercase(session: Session) -> None:
    session.add(User(email="Ana@DeltaWeb.local"))

    with pytest.raises(IntegrityError, match="ck_users_email_lowercase"):
        session.flush()
    session.rollback()


# --- user_sessions ---


def test_migrations_created_the_user_sessions_table(session: Session) -> None:
    assert "user_sessions" in inspect(session.connection()).get_table_names()


def test_create_session(session: Session, user: User) -> None:
    login = new_session(user)
    session.add(login)
    session.flush()
    session.refresh(login)

    assert login.id is not None
    assert login.created_at is not None
    assert login.expires_at > login.created_at


def test_token_hash_is_unique(session: Session, user: User) -> None:
    session.add(new_session(user, "b" * 64))
    session.flush()
    session.add(new_session(user, "b" * 64))

    with pytest.raises(IntegrityError, match="uq_user_sessions_token_hash"):
        session.flush()
    session.rollback()


def test_a_user_can_have_several_sessions(session: Session, user: User) -> None:
    session.add_all([new_session(user, "c" * 64), new_session(user, "d" * 64)])
    session.flush()

    sessions = session.scalars(select(UserSession).where(UserSession.user_id == user.id)).all()
    assert len(sessions) == 2


def test_expires_at_is_required(session: Session, user: User) -> None:
    session.add(UserSession(user_id=user.id, token_hash="e" * 64))

    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_deleting_a_user_deletes_their_sessions(session: Session, user: User) -> None:
    other = User(email="other@deltaweb.local")
    session.add(other)
    session.flush()
    session.add_all([new_session(user, "f" * 64), new_session(other, "g" * 64)])
    session.flush()

    session.execute(delete(User).where(User.id == user.id))

    remaining = session.scalars(select(UserSession.user_id)).all()
    assert remaining == [other.id]


# --- oauth_accounts ---


def test_only_google_and_github_are_valid_providers(session: Session, user: User) -> None:
    session.add(OAuthAccount(user_id=user.id, provider="facebook", provider_user_id="1"))

    with pytest.raises(IntegrityError, match="ck_oauth_accounts_provider_valid"):
        session.flush()
    session.rollback()


def test_a_provider_account_links_to_only_one_user(session: Session, user: User) -> None:
    other = User(email="other@deltaweb.local")
    session.add(other)
    session.flush()
    session.add(OAuthAccount(user_id=user.id, provider="google", provider_user_id="g-1"))
    session.flush()
    session.add(OAuthAccount(user_id=other.id, provider="google", provider_user_id="g-1"))

    with pytest.raises(IntegrityError, match="uq_oauth_accounts_provider_provider_user_id"):
        session.flush()
    session.rollback()


def test_the_same_id_at_another_provider_is_another_account(session: Session, user: User) -> None:
    session.add_all(
        [
            OAuthAccount(user_id=user.id, provider="google", provider_user_id="42"),
            OAuthAccount(user_id=user.id, provider="github", provider_user_id="42"),
        ]
    )
    session.flush()

    linked = session.scalars(select(OAuthAccount).where(OAuthAccount.user_id == user.id))
    assert len(linked.all()) == 2


def test_deleting_a_user_deletes_their_linked_accounts(session: Session, user: User) -> None:
    session.add(OAuthAccount(user_id=user.id, provider="github", provider_user_id="7"))
    session.flush()

    session.execute(delete(User).where(User.id == user.id))

    assert session.scalars(select(OAuthAccount)).all() == []
