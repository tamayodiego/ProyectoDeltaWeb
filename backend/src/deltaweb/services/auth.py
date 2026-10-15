"""Login sessions: create, look up and end them.

The browser keeps a random token in an httpOnly cookie (JavaScript cannot read it). The
database keeps only its SHA-256 hash, so a leaked copy of ``user_sessions`` lets nobody in.
A plain SHA-256 is enough here (unlike passwords): the token is 256 random bits, so
there is nothing to guess.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from deltaweb.config import get_settings
from deltaweb.models import User, UserSession

SESSION_COOKIE = "deltaweb_session"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    """Store a new session for ``user`` and return the raw token (it is never stored)."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=get_settings().session_days)
    db.add(UserSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at))
    db.commit()
    return token


def user_for_token(db: Session, token: str) -> User | None:
    """The user of a valid, unexpired session; None otherwise."""
    return db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(UserSession.token_hash == hash_token(token))
        .where(UserSession.expires_at > datetime.now(UTC))
    )


def end_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))
    db.commit()
