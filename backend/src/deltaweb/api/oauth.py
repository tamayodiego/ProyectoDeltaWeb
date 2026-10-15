"""Log in with Google or GitHub (see services/oauth.py for the protocol).

The browser goes: /auth/oauth/{provider}/start -> provider -> /auth/oauth/{provider}/callback
-> back to the web app with a session cookie. This is a browser navigation, not a JSON
call, so every failure is a redirect to ``{app_url}/login?error=<code>`` that the
frontend turns into a message:

- ``email_in_use``: an account has this email, but the provider did not verify it, so it
  cannot be linked. Tell the user to log in with their password.
- ``no_email``: the provider gave no email (e.g. a GitHub account without one).
- ``oauth``: anything else (cancelled, expired or forged attempt, provider error...).
"""

import logging
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from deltaweb.api.deps import SessionDep, set_session_cookie
from deltaweb.config import get_settings
from deltaweb.models import OAuthAccount, User, UserSession
from deltaweb.services.auth import create_session
from deltaweb.services.oauth import (
    OAuthError,
    OAuthFlow,
    OAuthProfile,
    Provider,
    ProviderNotConfigured,
    authorization_url,
    fetch_profile,
    get_provider,
    new_flow,
)

router = APIRouter(prefix="/auth/oauth", tags=["auth"])

logger = logging.getLogger(__name__)

# The secrets of one login attempt ("state:verifier"), only sent back to /auth/oauth/...
FLOW_COOKIE = "deltaweb_oauth"
FLOW_COOKIE_PATH = "/auth/oauth"
FLOW_COOKIE_SECONDS = 10 * 60


def provider_or_404(name: str) -> Provider:
    try:
        return get_provider(name)
    except ProviderNotConfigured as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown login provider") from exc


class LoginFailed(Exception):
    """The provider answered, but the login cannot go on. ``code`` goes to the frontend."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def to_login_with_error(code: str = "oauth") -> RedirectResponse:
    response = RedirectResponse(f"{get_settings().app_url}/login?error={code}", status_code=302)
    response.delete_cookie(FLOW_COOKIE, path=FLOW_COOKIE_PATH)
    return response


@router.get("/{provider}/start")
def start(provider: str) -> RedirectResponse:
    """Send the browser to the provider's consent page."""
    chosen = provider_or_404(provider)
    flow = new_flow()

    response = RedirectResponse(authorization_url(chosen, flow), status_code=302)
    response.set_cookie(
        FLOW_COOKIE,
        f"{flow.state}:{flow.code_verifier}",
        max_age=FLOW_COOKIE_SECONDS,
        httponly=True,
        secure=get_settings().secure_cookies(),
        # Lax: still sent when the provider redirects back (a top-level GET navigation)
        samesite="lax",
        path=FLOW_COOKIE_PATH,
    )
    return response


@router.get("/{provider}/callback")
def callback(
    provider: str,
    request: Request,
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """Finish the login: check the state, read the profile, find or create the user."""
    chosen = provider_or_404(provider)

    # The flow cookie is single-use: every answer below deletes it
    stored = request.cookies.get(FLOW_COOKIE, "")
    stored_state, _, verifier = stored.partition(":")
    # compare_digest raises TypeError on non-ASCII str ("?state=ñ" would be a 500): compare bytes
    same_state = state is not None and secrets.compare_digest(stored_state.encode(), state.encode())
    if not code or not verifier or not same_state:
        # No cookie, a forged or replayed state, or the user cancelled at the provider
        return to_login_with_error()

    try:
        profile = fetch_profile(chosen, code, OAuthFlow(stored_state, verifier))
    except OAuthError:
        logger.warning("OAuth login with %s failed", chosen.name, exc_info=True)
        return to_login_with_error()

    try:
        user = find_or_create_user(session, profile)
    except LoginFailed as exc:
        return to_login_with_error(exc.code)

    response = RedirectResponse(get_settings().app_url, status_code=302)
    set_session_cookie(response, create_session(session, user))
    response.delete_cookie(FLOW_COOKIE, path=FLOW_COOKIE_PATH)
    return response


def find_or_create_user(session: Session, profile: OAuthProfile) -> User:
    """The user for this provider account, in this order:

    1. The account is already linked: its user.
    2. The provider verified the email and a user has it: link the account to that user.
    3. Nobody has the email: a new user without password, linked to the account.

    Raises LoginFailed("no_email") without an email, and LoginFailed("email_in_use") when
    the email belongs to a user but the provider did not verify it (linking then would
    hand that account to whoever controls the provider account).
    """
    linked = session.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == profile.provider,
            OAuthAccount.provider_user_id == profile.provider_user_id,
        )
    )
    if linked is not None:
        owner = session.get(User, linked.user_id)
        if owner is None:  # cannot happen: the foreign key keeps them together
            raise LoginFailed("oauth")
        return owner

    if profile.email is None:
        raise LoginFailed("no_email")

    now = datetime.now(UTC)
    user = session.scalar(select(User).where(User.email == profile.email))
    if user is not None:
        if not profile.email_verified:
            raise LoginFailed("email_in_use")
        if user.email_verified_at is None:
            # Nobody proved this email before, so the password may belong to someone who
            # registered with another person's address ("pre-account takeover"). The
            # provider just proved who owns it: drop that password and its sessions.
            user.password_hash = None
            session.execute(delete(UserSession).where(UserSession.user_id == user.id))
            user.email_verified_at = now
    else:
        user = User(
            email=profile.email,
            password_hash=None,
            email_verified_at=now if profile.email_verified else None,
        )
        session.add(user)
        session.flush()

    session.add(
        OAuthAccount(
            user_id=user.id, provider=profile.provider, provider_user_id=profile.provider_user_id
        )
    )
    try:
        session.commit()
    except IntegrityError:
        # Lost a race with another login of the same account (or of the same new email):
        # nothing was saved; the user just tries again
        session.rollback()
        logger.warning("OAuth account %s already linked", profile.provider, exc_info=True)
        raise LoginFailed("oauth") from None
    return user
