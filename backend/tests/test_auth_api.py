"""Register, log in, log out and /auth/me (needs Docker, see conftest.py).

Emails use example.com: it is reserved for examples (RFC 2606) and passes validation,
while reserved names such as .local are rejected by email-validator.
"""

from datetime import UTC, datetime, timedelta

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from deltaweb.models import User, UserSession
from deltaweb.services.auth import SESSION_COOKIE

PASSWORD = "Sup3r-secret"


def register(
    client: TestClient, email: str = "ana@example.com", password: str = PASSWORD
) -> httpx.Response:
    return client.post("/auth/register", json={"email": email, "password": password})


# --- register ---


def test_register_creates_the_account_and_logs_in(anonymous_client: TestClient) -> None:
    response = register(anonymous_client)

    assert response.status_code == 201
    assert response.json()["email"] == "ana@example.com"
    assert response.json()["email_verified"] is False
    assert SESSION_COOKIE in response.cookies
    assert anonymous_client.get("/auth/me").json()["email"] == "ana@example.com"


def test_cookie_is_httponly_and_samesite_lax(anonymous_client: TestClient) -> None:
    header = register(anonymous_client).headers["set-cookie"].lower()

    assert "httponly" in header
    assert "samesite=lax" in header


def test_password_is_stored_hashed(anonymous_client: TestClient, session: Session) -> None:
    register(anonymous_client)

    stored = session.scalar(select(User.password_hash).where(User.email == "ana@example.com"))
    assert stored is not None
    assert stored.startswith("$argon2id$")


def test_email_is_saved_in_lowercase(anonymous_client: TestClient) -> None:
    assert register(anonymous_client, email="Ana@Example.COM").json()["email"] == (
        "ana@example.com"
    )


def test_email_already_registered_is_a_conflict(anonymous_client: TestClient) -> None:
    register(anonymous_client)

    assert register(anonymous_client, email="ANA@example.com").status_code == 409


def test_invalid_email_is_rejected(anonymous_client: TestClient) -> None:
    assert register(anonymous_client, email="not-an-email").status_code == 422


def test_weak_password_lists_what_is_missing(anonymous_client: TestClient) -> None:
    response = register(anonymous_client, password="password")

    assert response.status_code == 422
    missing = response.json()["detail"]["missing"]
    assert "an uppercase letter" in missing
    assert "a number" in missing
    assert "a symbol" in missing


# --- login ---


def test_login(anonymous_client: TestClient) -> None:
    register(anonymous_client)
    anonymous_client.cookies.clear()

    response = anonymous_client.post(
        "/auth/login", json={"email": "ANA@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert anonymous_client.get("/auth/me").status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_answer(
    anonymous_client: TestClient,
) -> None:
    register(anonymous_client)
    anonymous_client.cookies.clear()

    wrong = anonymous_client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "Wr0ng-pass"}
    )
    unknown = anonymous_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_account_without_password_cannot_log_in(
    anonymous_client: TestClient, session: Session
) -> None:
    session.add(User(email="oauth@example.com"))  # e.g. GitHub-only account (block 2c)
    session.flush()

    response = anonymous_client.post(
        "/auth/login", json={"email": "oauth@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401


# --- sessions, /me and logout ---


def test_me_without_a_session_is_401(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/auth/me").status_code == 401


def test_a_made_up_token_is_401(anonymous_client: TestClient) -> None:
    anonymous_client.cookies.set(SESSION_COOKIE, "made-up-token")

    assert anonymous_client.get("/auth/me").status_code == 401


def test_only_the_token_hash_is_stored(anonymous_client: TestClient, session: Session) -> None:
    token = register(anonymous_client).cookies[SESSION_COOKIE]

    stored = session.scalars(select(UserSession.token_hash)).all()
    assert token not in stored
    assert all(len(h) == 64 for h in stored)


def test_expired_session_is_401(client: TestClient, session: Session) -> None:
    expired = datetime.now(UTC) - timedelta(minutes=1)
    session.execute(update(UserSession).values(expires_at=expired))

    assert client.get("/auth/me").status_code == 401


def test_logout_ends_the_session(client: TestClient, session: Session) -> None:
    token = client.cookies[SESSION_COOKIE]

    assert client.post("/auth/logout").status_code == 204

    # Even if someone kept a copy of the token, it no longer works
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/auth/me").status_code == 401
    assert session.scalars(select(UserSession)).all() == []


# --- everything else now needs a login ---


def test_folders_and_delta_matroids_need_a_login(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/folders").status_code == 401
    assert anonymous_client.get("/delta-matroids").status_code == 401


def test_each_user_sees_only_their_own_folders(client: TestClient) -> None:
    client.post("/folders", json={"name": "Mine"})

    # A second account, in a second browser
    other = TestClient(client.app)
    other.post("/auth/register", json={"email": "bob@example.com", "password": PASSWORD})

    assert [f["name"] for f in other.get("/folders").json()] == []
    assert [f["name"] for f in client.get("/folders").json()] == ["Mine"]
