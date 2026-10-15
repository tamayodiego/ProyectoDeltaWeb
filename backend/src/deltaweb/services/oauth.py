"""Log in with Google or GitHub: the OAuth 2.0 Authorization Code flow with PKCE.

The flow, seen from the browser:

1. ``/auth/oauth/{provider}/start`` creates an ``OAuthFlow`` (``new_flow``), keeps it in a
   short-lived cookie and redirects to ``authorization_url``.
2. The user accepts on the provider's site, which redirects back to
   ``/auth/oauth/{provider}/callback?code=...&state=...``.
3. The callback checks that ``state`` matches the cookie (stops CSRF: an attacker cannot
   make the victim's browser finish a login the attacker started), then
   ``fetch_profile`` trades the code for an access token and asks who the user is.

PKCE: the provider only sees ``code_challenge`` = SHA-256 of our secret ``code_verifier``.
Trading the code needs the verifier itself, so a stolen code is useless on its own.

Only this module talks to the providers. It knows nothing about our users or sessions:
it returns an ``OAuthProfile`` and the endpoint decides what to do with it.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlencode

import httpx

from deltaweb.config import get_settings

ProviderName = Literal["google", "github"]


class OAuthError(Exception):
    """The provider refused the code, or answered something we cannot use."""


class ProviderNotConfigured(Exception):
    """Unknown provider, or no client id/secret for it in the settings."""


@dataclass(frozen=True)
class Provider:
    name: ProviderName
    authorize_url: str
    token_url: str
    scope: str


PROVIDERS: dict[str, Provider] = {
    "google": Provider(
        name="google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scope="openid email",
    ),
    "github": Provider(
        name="github",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        scope="read:user user:email",
    ),
}

GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"  # /user hides private emails


@dataclass(frozen=True)
class OAuthFlow:
    """The secrets of one login attempt; both stay in our cookie."""

    state: str
    code_verifier: str

    @property
    def code_challenge(self) -> str:
        """PKCE S256: base64url(sha256(verifier)) without "=" padding (RFC 7636)."""
        digest = hashlib.sha256(self.code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@dataclass(frozen=True)
class OAuthProfile:
    """Who the provider says the user is."""

    provider: ProviderName
    provider_user_id: str  # stable id at the provider (the email can change)
    email: str | None  # lowercase; None if the provider gave none
    email_verified: bool  # only a verified email may be linked to an existing account


# --- Settings ---


def get_provider(name: str) -> Provider:
    """The provider called ``name``, if it exists and has credentials."""
    provider = PROVIDERS.get(name)
    if provider is None or _credentials(provider) is None:
        raise ProviderNotConfigured(name)
    return provider


def _credentials(provider: Provider) -> tuple[str, str] | None:
    settings = get_settings()
    client_id = getattr(settings, f"{provider.name}_client_id")
    client_secret = getattr(settings, f"{provider.name}_client_secret")
    return (client_id, client_secret) if client_id and client_secret else None


def redirect_uri(provider: Provider) -> str:
    """Where the provider sends the user back. Must match the one registered in the app."""
    return f"{get_settings().api_url}/auth/oauth/{provider.name}/callback"


# --- Step 1: send the user to the provider ---


def new_flow() -> OAuthFlow:
    # token_urlsafe(64) -> 86 characters; PKCE asks for 43 to 128
    return OAuthFlow(state=secrets.token_urlsafe(32), code_verifier=secrets.token_urlsafe(64))


def authorization_url(provider: Provider, flow: OAuthFlow) -> str:
    client_id, _ = _credentials(provider) or ("", "")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": provider.scope,
        "state": flow.state,
        "code_challenge": flow.code_challenge,
        "code_challenge_method": "S256",
    }
    if provider.name == "google":
        params["prompt"] = "select_account"  # let people with several accounts choose
    return f"{provider.authorize_url}?{urlencode(params)}"


# --- Step 3: trade the code and read the profile ---


def fetch_profile(
    provider: Provider, code: str, flow: OAuthFlow, client: httpx.Client | None = None
) -> OAuthProfile:
    """Trade ``code`` for an access token and ask the provider who the user is.

    ``client`` is for tests (httpx.MockTransport); by default a new one is used.
    Any network error or unexpected answer becomes ``OAuthError``.
    """
    own_client = client is None
    http = client or httpx.Client(timeout=get_settings().oauth_timeout_seconds)
    try:
        token = _exchange_code(http, provider, code, flow)
        if provider.name == "google":
            return _google_profile(http, token)
        return _github_profile(http, token)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise OAuthError(f"{provider.name}: {exc}") from exc
    finally:
        if own_client:
            http.close()


def _exchange_code(http: httpx.Client, provider: Provider, code: str, flow: OAuthFlow) -> str:
    client_id, client_secret = _credentials(provider) or ("", "")
    response = http.post(
        provider.token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(provider),
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": flow.code_verifier,
        },
        headers={"Accept": "application/json"},  # GitHub answers form-encoded otherwise
    )
    response.raise_for_status()
    body = response.json()
    token = body.get("access_token")
    if not token:
        # GitHub says "no" with a 200 and {"error": "bad_verification_code", ...}
        raise OAuthError(f"{provider.name}: no access token ({body.get('error', 'unknown')})")
    return str(token)


def _get_json(http: httpx.Client, url: str, token: str, **headers: str) -> Any:
    response = http.get(url, headers={"Authorization": f"Bearer {token}", **headers})
    response.raise_for_status()
    return response.json()


def _lower(email: Any) -> str | None:
    return email.lower() if isinstance(email, str) and email else None


def _google_profile(http: httpx.Client, token: str) -> OAuthProfile:
    data = _get_json(http, GOOGLE_USERINFO_URL, token)
    return OAuthProfile(
        provider="google",
        provider_user_id=str(data["sub"]),
        email=_lower(data.get("email")),
        email_verified=data.get("email_verified") is True,
    )


def _github_profile(http: httpx.Client, token: str) -> OAuthProfile:
    github = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    user = _get_json(http, GITHUB_USER_URL, token, **github)
    emails = _get_json(http, GITHUB_EMAILS_URL, token, **github)
    primary = next((e for e in emails if e.get("primary")), None)
    return OAuthProfile(
        provider="github",
        provider_user_id=str(user["id"]),
        email=_lower(primary["email"]) if primary else None,
        email_verified=bool(primary and primary.get("verified") is True),
    )
