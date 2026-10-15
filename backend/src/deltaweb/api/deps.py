"""Dependencies shared by the routers (``Depends(...)``)."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from deltaweb.config import get_settings
from deltaweb.db import get_session
from deltaweb.models import User
from deltaweb.services.auth import SESSION_COOKIE, user_for_token
from deltaweb.services.rate_limit import RateLimited, RateLimiter

SessionDep = Annotated[Session, Depends(get_session)]
SessionToken = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]


def get_current_user(session: SessionDep, token: SessionToken = None) -> User:
    """The logged-in user, from the session cookie. No cookie or a bad one -> 401."""
    user = user_for_token(session, token) if token else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def set_session_cookie(response: Response, token: str) -> None:
    """Log the browser in: the session token goes in an httpOnly cookie."""
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,  # JavaScript cannot read it, so an XSS bug cannot steal it
        secure=settings.secure_cookies(),  # HTTPS only, except environment "local"
        samesite="lax",
        path="/",
    )


# --- Rate limiting (limiters live next to the routes that use them) ---


def check_rate(limiter: RateLimiter, key: str) -> None:
    """Count one attempt for ``key``; over the limit -> 429 with a Retry-After header."""
    try:
        limiter.hit(key)
    except RateLimited as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, try again later",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc


def client_ip(request: Request) -> str:
    # Behind a proxy this is the proxy's address unless uvicorn trusts its
    # X-Forwarded-For header (--forwarded-allow-ips); see CLAUDE.md
    return request.client.host if request.client else "unknown"
