"""Dependencies shared by the routers (``Depends(...)``)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from deltaweb.db import get_session
from deltaweb.models import User

SessionDep = Annotated[Session, Depends(get_session)]

DEMO_EMAIL = "demo@deltaweb.local"


def get_current_user(session: SessionDep) -> User:
    """TEMPORARY (block 2a): everyone is the same demo user, created on first use.

    Block 2b replaces this with the user from the login cookie. Routers only depend on
    ``CurrentUser``, so they will not change.
    """
    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(email=DEMO_EMAIL)
        session.add(user)
        session.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
