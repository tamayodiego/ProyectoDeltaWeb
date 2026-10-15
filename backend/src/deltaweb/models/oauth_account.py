"""Accounts at Google or GitHub linked to a user, to log in without a password.

``provider_user_id`` is the provider's own stable id for the person (Google's ``sub``,
GitHub's numeric id), not the email: an email can change at the provider, that id cannot.
A provider account belongs to at most one user; a user can link both providers.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from deltaweb.db import Base


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        CheckConstraint("provider IN ('google', 'github')", name="provider_valid"),
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_oauth_accounts_provider_provider_user_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Deleting a user deletes their linked accounts
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(16))  # "google" or "github"
    provider_user_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
