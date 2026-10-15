"""Users: who owns folders and delta-matroids, and who can log in.

The email is the login name and is stored in lowercase, so "Ana@X.com" and "ana@x.com"
are the same account. Only a hash of the password is kept. ``password_hash`` is None for
accounts without a password (login with Google or GitHub, block 2c), and ``email_verified_at``
stays None until the user confirms their email.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from deltaweb.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    password_hash: Mapped[str | None] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
