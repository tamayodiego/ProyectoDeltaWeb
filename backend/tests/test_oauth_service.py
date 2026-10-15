"""The Google and GitHub clients, against fake providers (httpx.MockTransport).

No network: every request goes to ``FakeProvider``, which answers like the real APIs and
records what it received.
"""

from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from deltaweb.config import Settings
from deltaweb.services import oauth
from deltaweb.services.oauth import (
    OAuthError,
    OAuthFlow,
    ProviderNotConfigured,
    authorization_url,
    fetch_profile,
    get_provider,
    new_flow,
)

FLOW = OAuthFlow(state="the-state", code_verifier="the-verifier")


@pytest.fixture(autouse=True)
def credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        google_client_id="google-id",
        google_client_secret="google-secret",
        github_client_id="github-id",
        github_client_secret="github-secret",
        api_url="http://localhost:8000",
    )
    monkeypatch.setattr(oauth, "get_settings", lambda: settings)


class FakeProvider:
    """Answers each URL with a JSON body (or a status code) and records the requests."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.routes[str(request.url)]
        if isinstance(answer, int):
            return httpx.Response(answer)
        return httpx.Response(200, json=answer)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))

    def form(self, index: int) -> dict[str, str]:
        """The form-encoded body of request ``index``."""
        return {k: v[0] for k, v in parse_qs(self.requests[index].content.decode()).items()}


def google(userinfo: Any, token: Any = None) -> FakeProvider:
    return FakeProvider(
        {
            "https://oauth2.googleapis.com/token": token or {"access_token": "g-token"},
            "https://openidconnect.googleapis.com/v1/userinfo": userinfo,
        }
    )


def github(emails: Any, token: Any = None) -> FakeProvider:
    return FakeProvider(
        {
            "https://github.com/login/oauth/access_token": token or {"access_token": "gh-token"},
            "https://api.github.com/user": {"id": 583231, "login": "ana"},
            "https://api.github.com/user/emails": emails,
        }
    )


# --- Flow and URL ---


def test_code_challenge_matches_the_rfc_example() -> None:
    # RFC 7636, appendix B
    flow = OAuthFlow(state="x", code_verifier="dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")

    assert flow.code_challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_every_flow_is_new() -> None:
    first, second = new_flow(), new_flow()

    assert first.state != second.state
    assert first.code_verifier != second.code_verifier
    assert 43 <= len(first.code_verifier) <= 128


@pytest.mark.parametrize("name", ["google", "github"])
def test_authorization_url_carries_state_and_challenge_but_not_the_verifier(name: str) -> None:
    url = urlsplit(authorization_url(get_provider(name), FLOW))
    params = {k: v[0] for k, v in parse_qs(url.query).items()}

    assert params["client_id"] == f"{name}-id"
    assert params["redirect_uri"] == f"http://localhost:8000/auth/oauth/{name}/callback"
    assert params["response_type"] == "code"
    assert params["state"] == "the-state"
    assert params["code_challenge"] == FLOW.code_challenge
    assert params["code_challenge_method"] == "S256"
    assert "the-verifier" not in url.query


def test_unknown_provider_is_not_configured() -> None:
    with pytest.raises(ProviderNotConfigured):
        get_provider("facebook")


def test_provider_without_credentials_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oauth, "get_settings", lambda: Settings(google_client_id=None))

    with pytest.raises(ProviderNotConfigured):
        get_provider("google")


# --- Google ---


def test_google_profile() -> None:
    fake = google({"sub": "1091", "email": "Ana@Gmail.com", "email_verified": True})

    profile = fetch_profile(get_provider("google"), "the-code", FLOW, fake.client())

    assert profile == oauth.OAuthProfile("google", "1091", "ana@gmail.com", True)


def test_google_token_request_sends_the_code_and_the_verifier() -> None:
    fake = google({"sub": "1091", "email": "ana@gmail.com", "email_verified": True})

    fetch_profile(get_provider("google"), "the-code", FLOW, fake.client())

    assert fake.form(0) == {
        "grant_type": "authorization_code",
        "code": "the-code",
        "redirect_uri": "http://localhost:8000/auth/oauth/google/callback",
        "client_id": "google-id",
        "client_secret": "google-secret",
        "code_verifier": "the-verifier",
    }
    assert fake.requests[1].headers["Authorization"] == "Bearer g-token"


def test_google_unverified_email() -> None:
    fake = google({"sub": "1091", "email": "ana@gmail.com", "email_verified": False})

    profile = fetch_profile(get_provider("google"), "the-code", FLOW, fake.client())

    assert profile.email_verified is False


# --- GitHub ---


def test_github_uses_the_primary_email() -> None:
    fake = github(
        [
            {"email": "old@example.com", "primary": False, "verified": True},
            {"email": "Ana@Example.com", "primary": True, "verified": True},
        ]
    )

    profile = fetch_profile(get_provider("github"), "the-code", FLOW, fake.client())

    assert profile == oauth.OAuthProfile("github", "583231", "ana@example.com", True)
    assert fake.form(0)["code_verifier"] == "the-verifier"
    assert fake.requests[0].headers["Accept"] == "application/json"


def test_github_unverified_primary_email() -> None:
    fake = github([{"email": "ana@example.com", "primary": True, "verified": False}])

    profile = fetch_profile(get_provider("github"), "the-code", FLOW, fake.client())

    assert profile.email == "ana@example.com"
    assert profile.email_verified is False


def test_github_without_emails() -> None:
    profile = fetch_profile(get_provider("github"), "the-code", FLOW, github([]).client())

    assert profile.email is None
    assert profile.email_verified is False


# --- Errors ---


def test_github_refusing_the_code_with_a_200() -> None:
    fake = github([], token={"error": "bad_verification_code"})

    with pytest.raises(OAuthError, match="bad_verification_code"):
        fetch_profile(get_provider("github"), "used-code", FLOW, fake.client())


@pytest.mark.parametrize("status", [400, 401, 500])
def test_http_errors_become_oauth_errors(status: int) -> None:
    fake = google({"sub": "1"}, token=status)

    with pytest.raises(OAuthError):
        fetch_profile(get_provider("google"), "the-code", FLOW, fake.client())


def test_profile_without_an_id_is_an_oauth_error() -> None:
    fake = google({"email": "ana@gmail.com"})  # no "sub"

    with pytest.raises(OAuthError):
        fetch_profile(get_provider("google"), "the-code", FLOW, fake.client())


def test_network_error_is_an_oauth_error() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("provider is down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(down))

    with pytest.raises(OAuthError, match="provider is down"):
        fetch_profile(get_provider("google"), "the-code", FLOW, client)
