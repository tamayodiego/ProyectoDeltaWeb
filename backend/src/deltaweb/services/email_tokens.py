"""One-time email tokens: create them, and redeem them exactly once.

The token travels in a link inside an email; only its SHA-256 is stored (see
models/email_token.py). Asking for a new token cancels the previous unused ones of the
same purpose, so only the latest email works.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import update
from sqlalchemy.orm import Session

from deltaweb.models import EmailToken, User
from deltaweb.services.auth import hash_token

Purpose = Literal["verify", "reset"]


def create_email_token(db: Session, user: User, purpose: Purpose, valid_for: timedelta) -> str:
    """Store a new token for ``user`` and return the raw value (it is never stored)."""
    now = datetime.now(UTC)
    db.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user.id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(32)
    db.add(
        EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(token),
            expires_at=now + valid_for,
        )
    )
    db.commit()
    return token


def redeem_email_token(db: Session, token: str, purpose: Purpose) -> User | None:
    """Mark the token as used and return its user; None if unknown, used, expired or for
    another purpose.

    One UPDATE ... WHERE used_at IS NULL does the check and the marking at once, so two
    requests racing with the same token cannot both succeed. The caller commits.
    """
    now = datetime.now(UTC)
    user_id = db.scalar(
        update(EmailToken)
        .where(
            EmailToken.token_hash == hash_token(token),
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(EmailToken.user_id)
    )
    return db.get(User, user_id) if user_id is not None else None
