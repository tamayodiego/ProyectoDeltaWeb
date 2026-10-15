"""Verify the email and reset the password with one-time tokens (needs Docker).

``send_email`` is replaced by a fake inbox, so no real email is sent; the token is read
from the link in the captured email, like a user clicking it.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from deltaweb.api import auth as auth_api
from deltaweb.models import EmailToken, User, UserSession
from deltaweb.services.passwords import hash_password
from tests.conftest import SentEmail

PASSWORD = "Sup3r-secret"
NEW_PASSWORD = "N3w-passw0rd"


@pytest.fixture
def ana(session: Session) -> User:
    user = User(email="ana@example.com", password_hash=hash_password(PASSWORD))
    session.add(user)
    session.flush()
    return user


def expire_all_tokens(session: Session) -> None:
    session.execute(update(EmailToken).values(expires_at=datetime.now(UTC) - timedelta(1)))


# --- POST /auth/verify/request and POST /auth/verify ---


def test_register_emails_a_verification_link(
    anonymous_client: TestClient, inbox: list[SentEmail]
) -> None:
    body = {"email": "new@example.com", "password": PASSWORD}
    assert anonymous_client.post("/auth/register", json=body).status_code == 201

    assert len(inbox) == 1
    assert inbox[0].to == "new@example.com"
    assert inbox[0].subject == "Verifica tu correo"
    response = anonymous_client.post("/auth/verify", json={"token": inbox[0].token})
    assert response.status_code == 200
    assert response.json()["email_verified"] is True


def test_failed_register_sends_no_email(
    anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    body = {"email": "ana@example.com", "password": PASSWORD}  # already taken

    assert anonymous_client.post("/auth/register", json=body).status_code == 409
    assert inbox == []


def test_verify_request_needs_a_login(anonymous_client: TestClient) -> None:
    assert anonymous_client.post("/auth/verify/request").status_code == 401


def test_verify_request_emails_a_link(client: TestClient, inbox: list[SentEmail]) -> None:
    response = client.post("/auth/verify/request")

    assert response.status_code == 202
    assert len(inbox) == 1
    assert inbox[0].to == "me@example.com"
    assert inbox[0].subject == "Verifica tu correo"
    assert "http://localhost:5173/verify-email?token=" in inbox[0].text


def test_verify_marks_the_email_as_verified(client: TestClient, inbox: list[SentEmail]) -> None:
    client.post("/auth/verify/request")

    response = client.post("/auth/verify", json={"token": inbox[0].token})

    assert response.status_code == 200
    assert response.json()["email_verified"] is True
    assert client.get("/auth/me").json()["email_verified"] is True


def test_verify_works_without_a_session(
    client: TestClient, anonymous_client: TestClient, inbox: list[SentEmail]
) -> None:
    client.post("/auth/verify/request")
    client.cookies.clear()  # the link is opened in another browser

    assert client.post("/auth/verify", json={"token": inbox[0].token}).status_code == 200


def test_verification_token_works_only_once(client: TestClient, inbox: list[SentEmail]) -> None:
    client.post("/auth/verify/request")
    token = inbox[0].token

    assert client.post("/auth/verify", json={"token": token}).status_code == 200
    assert client.post("/auth/verify", json={"token": token}).status_code == 400


def test_expired_verification_token_is_rejected(
    client: TestClient, session: Session, inbox: list[SentEmail]
) -> None:
    client.post("/auth/verify/request")
    expire_all_tokens(session)

    assert client.post("/auth/verify", json={"token": inbox[0].token}).status_code == 400


def test_verification_token_lasts_24_hours(
    client: TestClient, session: Session, inbox: list[SentEmail]
) -> None:
    client.post("/auth/verify/request")

    token = session.scalars(select(EmailToken)).one()
    assert token.purpose == "verify"
    assert timedelta(hours=23, minutes=59) < token.expires_at - token.created_at
    assert token.expires_at - token.created_at <= timedelta(hours=24, minutes=1)


def test_a_new_request_cancels_the_previous_link(
    client: TestClient, inbox: list[SentEmail]
) -> None:
    client.post("/auth/verify/request")
    client.post("/auth/verify/request")

    assert client.post("/auth/verify", json={"token": inbox[0].token}).status_code == 400
    assert client.post("/auth/verify", json={"token": inbox[1].token}).status_code == 200


def test_already_verified_is_a_conflict(client: TestClient, inbox: list[SentEmail]) -> None:
    client.post("/auth/verify/request")
    client.post("/auth/verify", json={"token": inbox[0].token})

    assert client.post("/auth/verify/request").status_code == 409


def test_verify_request_is_rate_limited(client: TestClient, inbox: list[SentEmail]) -> None:
    codes = [client.post("/auth/verify/request").status_code for _ in range(4)]

    assert codes == [202, 202, 202, 429]


def test_unknown_token_is_rejected(anonymous_client: TestClient) -> None:
    assert anonymous_client.post("/auth/verify", json={"token": "made-up"}).status_code == 400


# --- POST /auth/password/forgot ---


def test_forgot_emails_a_reset_link(
    anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    response = anonymous_client.post("/auth/password/forgot", json={"email": "ANA@example.com"})

    assert response.status_code == 202
    assert len(inbox) == 1
    assert inbox[0].to == "ana@example.com"
    assert inbox[0].subject == "Recupera tu contraseña"
    assert "http://localhost:5173/reset-password?token=" in inbox[0].text
    assert "60 minutos" in inbox[0].text


def test_forgot_answers_the_same_for_unknown_emails(
    anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    known = anonymous_client.post("/auth/password/forgot", json={"email": "ana@example.com"})
    unknown = anonymous_client.post("/auth/password/forgot", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [email.to for email in inbox] == ["ana@example.com"]  # nothing sent to nobody


def test_reset_token_lasts_1_hour(
    anonymous_client: TestClient, session: Session, ana: User, inbox: list[SentEmail]
) -> None:
    anonymous_client.post("/auth/password/forgot", json={"email": "ana@example.com"})

    token = session.scalars(select(EmailToken)).one()
    assert token.purpose == "reset"
    assert timedelta(minutes=59) < token.expires_at - token.created_at <= timedelta(minutes=61)


def test_forgot_is_rate_limited_per_email(
    anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    codes = [
        anonymous_client.post(
            "/auth/password/forgot", json={"email": "ana@example.com"}
        ).status_code
        for _ in range(4)
    ]

    assert codes == [202, 202, 202, 429]


def test_forgot_is_rate_limited_per_ip(
    anonymous_client: TestClient, inbox: list[SentEmail]
) -> None:
    codes = [
        anonymous_client.post(
            "/auth/password/forgot", json={"email": f"user{i}@example.com"}
        ).status_code
        for i in range(6)
    ]

    assert codes == [202] * 5 + [429]


def test_a_failing_smtp_server_does_not_change_the_answer(
    anonymous_client: TestClient, ana: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: object) -> None:
        raise ConnectionRefusedError("SMTP is down")

    monkeypatch.setattr(auth_api, "send_email", broken)

    response = anonymous_client.post("/auth/password/forgot", json={"email": "ana@example.com"})

    assert response.status_code == 202


# --- POST /auth/password/reset ---


def forgot(client: TestClient, inbox: list[SentEmail]) -> str:
    client.post("/auth/password/forgot", json={"email": "ana@example.com"})
    return inbox[-1].token


def log_in(client: TestClient, password: str) -> int:
    body = {"email": "ana@example.com", "password": password}
    return client.post("/auth/login", json=body).status_code


def test_reset_changes_the_password(
    anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    token = forgot(anonymous_client, inbox)

    response = anonymous_client.post(
        "/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}
    )

    assert response.status_code == 204
    assert log_in(anonymous_client, PASSWORD) == 401
    assert log_in(anonymous_client, NEW_PASSWORD) == 200


def test_reset_closes_every_session(
    anonymous_client: TestClient, session: Session, ana: User, inbox: list[SentEmail]
) -> None:
    log_in(anonymous_client, PASSWORD)  # one open session...
    assert anonymous_client.get("/auth/me").status_code == 200
    token = forgot(anonymous_client, inbox)

    anonymous_client.post("/auth/password/reset", json={"token": token, "password": NEW_PASSWORD})

    assert anonymous_client.get("/auth/me").status_code == 401  # ...is gone
    assert session.scalars(select(UserSession).where(UserSession.user_id == ana.id)).all() == []


def test_reset_token_works_only_once(
    anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    token = forgot(anonymous_client, inbox)
    body = {"token": token, "password": NEW_PASSWORD}

    assert anonymous_client.post("/auth/password/reset", json=body).status_code == 204
    assert anonymous_client.post("/auth/password/reset", json=body).status_code == 400


def test_weak_password_does_not_burn_the_token(
    anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    token = forgot(anonymous_client, inbox)

    weak = anonymous_client.post("/auth/password/reset", json={"token": token, "password": "abc"})
    strong = anonymous_client.post(
        "/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}
    )

    assert weak.status_code == 422
    assert strong.status_code == 204


def test_expired_reset_token_is_rejected(
    anonymous_client: TestClient, session: Session, ana: User, inbox: list[SentEmail]
) -> None:
    token = forgot(anonymous_client, inbox)
    expire_all_tokens(session)

    body = {"token": token, "password": NEW_PASSWORD}
    assert anonymous_client.post("/auth/password/reset", json=body).status_code == 400


def test_tokens_only_work_for_their_purpose(
    client: TestClient, anonymous_client: TestClient, ana: User, inbox: list[SentEmail]
) -> None:
    client.post("/auth/verify/request")
    verify_token = inbox[-1].token

    body = {"token": verify_token, "password": NEW_PASSWORD}
    assert client.post("/auth/password/reset", json=body).status_code == 400


def test_reset_also_verifies_the_email(
    anonymous_client: TestClient, session: Session, ana: User, inbox: list[SentEmail]
) -> None:
    token = forgot(anonymous_client, inbox)
    anonymous_client.post("/auth/password/reset", json={"token": token, "password": NEW_PASSWORD})

    session.refresh(ana)
    assert ana.email_verified_at is not None


# --- Model ---


def test_only_verify_and_reset_are_valid_purposes(session: Session, ana: User) -> None:
    session.add(
        EmailToken(
            user_id=ana.id,
            purpose="login",
            token_hash="x" * 64,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )

    with pytest.raises(IntegrityError, match="ck_email_tokens_purpose_valid"):
        session.flush()
    session.rollback()


def test_only_the_token_hash_is_stored(
    anonymous_client: TestClient, session: Session, ana: User, inbox: list[SentEmail]
) -> None:
    token = forgot(anonymous_client, inbox)

    stored = session.scalars(select(EmailToken.token_hash)).all()
    assert token not in stored
    assert all(len(h) == 64 for h in stored)
