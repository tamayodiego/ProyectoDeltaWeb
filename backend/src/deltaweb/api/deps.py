"""Dependencies shared by the routers (``Depends(...)``)."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from deltaweb.db import get_session
from deltaweb.models import User
from deltaweb.services.auth import SESSION_COOKIE, user_for_token

SessionDep = Annotated[Session, Depends(get_session)]
SessionToken = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]


def get_current_user(session: SessionDep, token: SessionToken = None) -> User:
    """The logged-in user, from the session cookie. No cookie or a bad one -> 401."""
    user = user_for_token(session, token) if token else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
