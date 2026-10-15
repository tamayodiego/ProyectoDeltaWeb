"""/auth/oauth/{provider}/start and /callback (needs Docker).

The providers are never called: ``fetch_profile`` is replaced by a fake that returns the
profile each test chooses. Settings get fake client ids so both providers are enabled.
"""

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from deltaweb.api import oauth as oauth_api
from deltaweb.config import Settings
from deltaweb.models import OAuthAccount, User, UserSession
from deltaweb.services import oauth as oauth_service
from deltaweb.services.auth import SESSION_COOKIE, create_session
from deltaweb.services.oauth import OAuthError, OAuthProfile
from deltaweb.services.passwords import hash_password

APP = "http://localhost:5173"
LOGIN_ERROR = f"{APP}/login?error=oauth"


@pytest.fixture(autouse=True)
def providers_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        google_client_id="google-id",
        google_client_secret="google-secret",
        github_client_id="github-id",
        github_client_secret="github-secret",
    )
    monkeypatch.setattr(oauth_service, "get_settings", lambda: settings)


@pytest.fixture
def profile(monkeypatch: pytest.MonkeyPatch) -> list[OAuthProfile]:
    """Put the profile the provider will "return" in this list (the last one is used)."""
    profiles: list[OAuthProfile] = []

    def fake_fetch_profile(provider: object, code: str, flow: object) -> OAuthProfile:
        assert code == "the-code"
        return profiles[-1]

    monkeypatch.setattr(oauth_api, "fetch_profile", fake_fetch_profile)
    return profiles


def google(
    sub: str = "g-123", email: str | None = "ana@example.com", verified: bool = True
) -> OAuthProfile:
    return OAuthProfile("google", sub, email, verified)


def start(client: TestClient, provider: str = "google") -> str:
    """Run /start and return the state the provider would echo back."""
    response = client.get(f"/auth/oauth/{provider}/start", follow_redirects=False)
    assert response.status_code == 302
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


def callback(client: TestClient, state: str, provider: str = "google", **params: str) -> str:
    """Run /callback and return where it redirects."""
    query = {"code": "the-code", "state": state, **params}
    response = client.get(f"/auth/oauth/{provider}/callback", params=query, follow_redirects=False)
    assert response.status_code == 302
    return str(response.headers["location"])


def log_in_with_google(client: TestClient) -> str:
    return callback(client, start(client))


# --- /start ---


def test_start_redirects_to_the_provider_with_pkce(anonymous_client: TestClient) -> None:
    response = anonymous_client.get("/auth/oauth/google/start", follow_redirects=False)

    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)
    assert f"{location.scheme}://{location.netloc}{location.path}" == (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )
    assert query["client_id"] == ["google-id"]
    assert query["redirect_uri"] == ["http://localhost:8000/auth/oauth/google/callback"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"][0]


def test_start_keeps_the_flow_in_a_short_httponly_cookie(anonymous_client: TestClient) -> None:
    response = anonymous_client.get("/auth/oauth/github/start", follow_redirects=False)

    header = response.headers["set-cookie"].lower()
    assert header.startswith(f"{oauth_api.FLOW_COOKIE}=")
    assert "httponly" in header
    assert "max-age=600" in header
    assert "path=/auth/oauth" in header
    assert "samesite=lax" in header


@pytest.mark.parametrize("provider", ["facebook", "GOOGLE"])
def test_unknown_provider_is_not_found(anonymous_client: TestClient, provider: str) -> None:
    response = anonymous_client.get(f"/auth/oauth/{provider}/start", follow_redirects=False)

    assert response.status_code == 404


def test_provider_without_credentials_is_not_found(
    anonymous_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Explicit None: a bare Settings() would also read backend/.env, with real credentials
    no_credentials = Settings(
        google_client_id=None,
        google_client_secret=None,
        github_client_id=None,
        github_client_secret=None,
    )
    monkeypatch.setattr(oauth_service, "get_settings", lambda: no_credentials)

    response = anonymous_client.get("/auth/oauth/google/start", follow_redirects=False)

    assert response.status_code == 404


# --- /callback: failures ---


def test_callback_without_the_flow_cookie_fails(
    anonymous_client: TestClient, profile: list[OAuthProfile]
) -> None:
    profile.append(google())

    assert callback(anonymous_client, "any-state") == LOGIN_ERROR


def test_callback_with_another_state_fails(
    anonymous_client: TestClient, profile: list[OAuthProfile]
) -> None:
    profile.append(google())
    start(anonymous_client)

    assert callback(anonymous_client, "forged-state") == LOGIN_ERROR


def test_non_ascii_state_is_an_error_not_a_crash(
    anonymous_client: TestClient, profile: list[OAuthProfile]
) -> None:
    # secrets.compare_digest raises TypeError on non-ASCII str; this used to be a 500
    profile.append(google())
    start(anonymous_client)

    assert callback(anonymous_client, "ñ") == LOGIN_ERROR


def test_user_cancelled_at_the_provider(anonymous_client: TestClient) -> None:
    state = start(anonymous_client)

    response = anonymous_client.get(
        "/auth/oauth/google/callback",
        params={"error": "access_denied", "state": state},
        follow_redirects=False,
    )

    assert response.headers["location"] == LOGIN_ERROR


def test_provider_error_fails(
    anonymous_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: object) -> OAuthProfile:
        raise OAuthError("google: bad_verification_code")

    monkeypatch.setattr(oauth_api, "fetch_profile", broken)

    assert log_in_with_google(anonymous_client) == LOGIN_ERROR


def test_flow_cookie_works_only_once(
    anonymous_client: TestClient, profile: list[OAuthProfile]
) -> None:
    profile.append(google())
    state = start(anonymous_client)

    assert callback(anonymous_client, state) == APP
    assert callback(anonymous_client, state) == LOGIN_ERROR  # replayed


def test_profile_without_email_fails(
    anonymous_client: TestClient, profile: list[OAuthProfile]
) -> None:
    profile.append(google(email=None, verified=False))

    assert log_in_with_google(anonymous_client) == f"{APP}/login?error=no_email"


# --- /callback: find, link or create ---


def test_first_login_creates_a_user_without_password(
    anonymous_client: TestClient, session: Session, profile: list[OAuthProfile]
) -> None:
    profile.append(google())

    assert log_in_with_google(anonymous_client) == APP

    me = anonymous_client.get("/auth/me").json()
    assert me["email"] == "ana@example.com"
    assert me["email_verified"] is True
    user = session.scalars(select(User).where(User.email == "ana@example.com")).one()
    assert user.password_hash is None
    account = session.scalars(select(OAuthAccount)).one()
    assert (account.user_id, account.provider, account.provider_user_id) == (
        user.id,
        "google",
        "g-123",
    )


def test_unverified_email_creates_an_unverified_user(
    anonymous_client: TestClient, profile: list[OAuthProfile]
) -> None:
    profile.append(google(verified=False))

    log_in_with_google(anonymous_client)

    assert anonymous_client.get("/auth/me").json()["email_verified"] is False


def test_second_login_finds_the_same_user(
    anonymous_client: TestClient, session: Session, profile: list[OAuthProfile]
) -> None:
    profile.append(google())
    log_in_with_google(anonymous_client)
    anonymous_client.cookies.clear()
    profile.append(google(email="ana.new@example.com"))  # changed email at Google

    log_in_with_google(anonymous_client)

    assert anonymous_client.get("/auth/me").json()["email"] == "ana@example.com"
    assert session.scalar(select(func.count()).select_from(User)) == 1
    assert session.scalar(select(func.count()).select_from(OAuthAccount)) == 1


def test_verified_email_links_to_an_existing_account(
    anonymous_client: TestClient, session: Session, profile: list[OAuthProfile]
) -> None:
    ana = User(
        email="ana@example.com", password_hash=hash_password("Sup3r-secret"), email_verified_at=None
    )
    session.add(ana)
    session.flush()
    profile.append(OAuthProfile("github", "42", "ana@example.com", True))

    callback(anonymous_client, start(anonymous_client, "github"), "github")

    assert anonymous_client.get("/auth/me").json()["id"] == ana.id
    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_linking_keeps_the_password_of_a_verified_account(
    anonymous_client: TestClient, session: Session, profile: list[OAuthProfile]
) -> None:
    password_hash = hash_password("Sup3r-secret")
    ana = User(
        email="ana@example.com", password_hash=password_hash, email_verified_at=datetime.now(UTC)
    )
    session.add(ana)
    session.flush()
    profile.append(google())

    log_in_with_google(anonymous_client)

    session.refresh(ana)
    assert ana.password_hash == password_hash  # can still log in with the password


def test_linking_an_unverified_account_drops_its_password_and_sessions(
    anonymous_client: TestClient, session: Session, profile: list[OAuthProfile]
) -> None:
    # Someone registered with Ana's email but never verified it ("pre-account takeover")
    squatter = User(email="ana@example.com", password_hash=hash_password("Att4cker-pass"))
    session.add(squatter)
    session.flush()
    create_session(session, squatter)
    profile.append(google())

    log_in_with_google(anonymous_client)  # the real Ana, proven by Google

    session.refresh(squatter)
    assert squatter.password_hash is None
    assert squatter.email_verified_at is not None
    sessions = session.scalars(select(UserSession).where(UserSession.user_id == squatter.id))
    assert len(sessions.all()) == 1  # only the session Ana just got


def test_unverified_email_does_not_link_to_an_existing_account(
    anonymous_client: TestClient, session: Session, profile: list[OAuthProfile]
) -> None:
    session.add(User(email="ana@example.com", password_hash=hash_password("Sup3r-secret")))
    session.flush()
    profile.append(google(verified=False))

    # A specific code, so the frontend can say "log in with your password"
    assert log_in_with_google(anonymous_client) == f"{APP}/login?error=email_in_use"
    assert session.scalar(select(func.count()).select_from(OAuthAccount)) == 0
    assert SESSION_COOKIE not in anonymous_client.cookies


def test_a_user_can_link_both_providers(
    anonymous_client: TestClient, session: Session, profile: list[OAuthProfile]
) -> None:
    profile.append(google())
    log_in_with_google(anonymous_client)
    profile.append(OAuthProfile("github", "42", "ana@example.com", True))

    callback(anonymous_client, start(anonymous_client, "github"), "github")

    providers = session.scalars(select(OAuthAccount.provider).order_by(OAuthAccount.provider))
    assert providers.all() == ["github", "google"]
    assert session.scalar(select(func.count()).select_from(User)) == 1
