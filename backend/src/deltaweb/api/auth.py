"""Accounts: register, log in, log out, and who am I.

The session lives in an httpOnly cookie (see services/auth.py). SameSite=Lax means the
browser does not send it on cross-site POSTs, which blocks classic CSRF against this API.
"""

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from deltaweb.api.deps import CurrentUser, SessionDep, SessionToken
from deltaweb.config import get_settings
from deltaweb.models import User
from deltaweb.schemas.auth import Credentials, UserOut
from deltaweb.services.auth import SESSION_COOKIE, create_session, end_session
from deltaweb.services.passwords import (
    WeakPasswordError,
    check_password_strength,
    hash_password,
    needs_rehash,
    verify_password,
)
from deltaweb.services.rate_limit import RateLimited, RateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
# Per IP: slows down one machine guessing many accounts. Per email: slows down many
# machines guessing one account. Checked before any password hashing (the costly part).
login_by_ip = RateLimiter(_settings.login_attempts_per_ip, window=60)
login_by_email = RateLimiter(_settings.login_attempts_per_email, window=60)
register_by_ip = RateLimiter(_settings.registrations_per_ip, window=60 * 60)
LIMITERS = (login_by_ip, login_by_email, register_by_ip)


def check_rate(limiter: RateLimiter, key: str) -> None:
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


def to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
    )


def set_session_cookie(response: Response, token: str) -> None:
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


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    body: Credentials, request: Request, response: Response, session: SessionDep
) -> UserOut:
    """Create the account and log in right away (the email can be verified later)."""
    check_rate(register_by_ip, client_ip(request))
    try:
        check_password_strength(body.password)
    except WeakPasswordError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "The password is too weak", "missing": exc.problems},
        ) from exc

    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="An account with that email already exists"
        ) from exc
    session.refresh(user)

    set_session_cookie(response, create_session(session, user))
    return to_out(user)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response, session: SessionDep) -> UserOut:
    """Same answer for "no such email" and "wrong password": never reveal who has an account."""
    check_rate(login_by_ip, client_ip(request))
    check_rate(login_by_email, body.email)

    user = session.scalar(select(User).where(User.email == body.email))
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.password_hash is not None and needs_rehash(user.password_hash):
        # Hashed with older parameters: upgrade now that we know the password
        user.password_hash = hash_password(body.password)

    set_session_cookie(response, create_session(session, user))
    return to_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, session: SessionDep, token: SessionToken = None) -> None:
    """End this session (the row is deleted, so the token is useless even if copied)."""
    if token:
        end_session(session, token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return to_out(user)
