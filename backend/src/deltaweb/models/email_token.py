"""One-time tokens sent by email: verify the address, or reset the password.

Same idea as login sessions: the email carries a random token, the database keeps only
its SHA-256. ``used_at`` makes each token single-use.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from deltaweb.db import Base


class EmailToken(Base):
    __tablename__ = "email_tokens"
    __table_args__ = (CheckConstraint("purpose IN ('verify', 'reset')", name="purpose_valid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Deleting a user deletes their tokens
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # "verify" or "reset"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # SHA-256 in hex
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # None = unused
