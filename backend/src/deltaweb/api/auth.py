"""Accounts: register, log in, log out, who am I, verify the email and reset the password.

The session lives in an httpOnly cookie (see services/auth.py). SameSite=Lax means the
browser does not send it on cross-site POSTs, which blocks classic CSRF against this API.
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from deltaweb.api.deps import CurrentUser, SessionDep, SessionToken
from deltaweb.config import get_settings
from deltaweb.models import User, UserSession
from deltaweb.schemas.auth import (
    Credentials,
    ForgotPassword,
    ResetPassword,
    TokenBody,
    UserOut,
)
from deltaweb.services.auth import SESSION_COOKIE, create_session, end_session
from deltaweb.services.email import Email, password_reset_email, send_email, verification_email
from deltaweb.services.email_tokens import create_email_token, redeem_email_token
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
forgot_by_ip = RateLimiter(_settings.password_resets_per_ip, window=60 * 60)
forgot_by_email = RateLimiter(_settings.password_resets_per_email, window=60 * 60)
verify_by_user = RateLimiter(_settings.verification_emails_per_user, window=60 * 60)
LIMITERS = (
    login_by_ip,
    login_by_email,
    register_by_ip,
    forgot_by_ip,
    forgot_by_email,
    verify_by_user,
)

logger = logging.getLogger(__name__)


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


def deliver(to: str, email: Email) -> None:
    """Send an email after the response (BackgroundTasks). A failure is logged, never
    shown: the answer was already sent, and for /password/forgot it must not differ."""
    try:
        send_email(to, email.subject, email.html, email.text)
    except Exception:
        logger.exception("Could not send %r to %s", email.subject, to)


def check_new_password(password: str) -> None:
    try:
        check_password_strength(password)
    except WeakPasswordError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "The password is too weak", "missing": exc.problems},
        ) from exc


INVALID_TOKEN = HTTPException(
    status.HTTP_400_BAD_REQUEST, detail="The link is invalid, expired or already used"
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
    body: Credentials,
    request: Request,
    response: Response,
    session: SessionDep,
    background: BackgroundTasks,
) -> UserOut:
    """Create the account and log in right away (the email can be verified later)."""
    check_rate(register_by_ip, client_ip(request))
    check_new_password(body.password)

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

    token = create_email_token(
        db=session,
        user=user,
        purpose="verify",
        valid_for=timedelta(hours=_settings.verify_token_hours),
    )
    link = f"{_settings.app_url}/verify-email?token={token}"
    background.add_task(deliver, user.email, verification_email(link))

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


# --- Verify the email ---


@router.post("/verify/request", status_code=status.HTTP_202_ACCEPTED)
def request_verification(
    user: CurrentUser, session: SessionDep, background: BackgroundTasks
) -> dict[str, str]:
    """Email a verification link to the logged-in user (valid 24 h, single use)."""
    if user.email_verified_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="The email is already verified")
    check_rate(verify_by_user, str(user.id))

    settings = get_settings()
    token = create_email_token(
        session, user, "verify", timedelta(hours=settings.verify_token_hours)
    )
    link = f"{settings.app_url}/verify-email?token={token}"
    background.add_task(deliver, user.email, verification_email(link))
    return {"detail": "Verification email sent"}


@router.post("/verify")
def verify_email(body: TokenBody, session: SessionDep) -> UserOut:
    """Redeem a verification link. No session needed: the link may open in another browser."""
    user = redeem_email_token(session, body.token, "verify")
    if user is None:
        raise INVALID_TOKEN
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
    session.commit()
    return to_out(user)


# --- Reset the password ---


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    body: ForgotPassword, request: Request, session: SessionDep, background: BackgroundTasks
) -> dict[str, str]:
    """Email a reset link (valid 1 h, single use). Always the same 202, whether the account
    exists or not, and the email goes out after the response, so the timing is the same too.
    """
    check_rate(forgot_by_ip, client_ip(request))
    check_rate(forgot_by_email, body.email)

    user = session.scalar(select(User).where(User.email == body.email))
    if user is not None:
        settings = get_settings()
        token = create_email_token(
            session, user, "reset", timedelta(minutes=settings.reset_token_minutes)
        )
        link = f"{settings.app_url}/reset-password?token={token}"
        email = password_reset_email(link, valid_minutes=settings.reset_token_minutes)
        background.add_task(deliver, user.email, email)
    return {"detail": "If the account exists, we sent an email with a link"}


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPassword, session: SessionDep) -> None:
    """Set a new password with a reset link and close every session of the user.

    The strength is checked first, so a weak password does not burn the link. Opening the
    link also proves the email belongs to the user, so it counts as verified.
    """
    check_new_password(body.password)
    user = redeem_email_token(session, body.token, "reset")
    if user is None:
        raise INVALID_TOKEN

    user.password_hash = hash_password(body.password)
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
    session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.commit()
