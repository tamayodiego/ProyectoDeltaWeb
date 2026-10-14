"""Rate limits on /auth, Argon2 parameters, rehashing and secure cookies.

The rate limiter and password tests need no database; the API tests need Docker.
"""

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from deltaweb.config import Settings
from deltaweb.models import User
from deltaweb.services import rate_limit
from deltaweb.services.passwords import hash_password, needs_rehash, verify_password
from deltaweb.services.rate_limit import RateLimited, RateLimiter

PASSWORD = "Sup3r-secret"


# --- RateLimiter ---


def test_limiter_allows_up_to_the_limit_then_blocks() -> None:
    limiter = RateLimiter(limit=3, window=60)
    for _ in range(3):
        limiter.hit("1.2.3.4")

    with pytest.raises(RateLimited) as exc:
        limiter.hit("1.2.3.4")
    assert 1 <= exc.value.retry_after <= 60


def test_limiter_counts_each_key_separately() -> None:
    limiter = RateLimiter(limit=1, window=60)
    limiter.hit("a")
    limiter.hit("b")  # another key: still allowed


def test_limiter_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: now[0])
    limiter = RateLimiter(limit=1, window=60)
    limiter.hit("a")

    now[0] += 61  # the old attempt left the window
    limiter.hit("a")


# --- Argon2 parameters ---


def test_new_hashes_use_the_lighter_owasp_profile() -> None:
    assert hash_password(PASSWORD).startswith("$argon2id$v=19$m=19456,t=2,p=1$")


def test_old_default_hashes_still_verify_and_need_a_rehash() -> None:
    old = PasswordHasher().hash(PASSWORD)  # argon2-cffi default: 64 MiB, t=3, p=4

    assert verify_password(PASSWORD, old)
    assert needs_rehash(old)
    assert not needs_rehash(hash_password(PASSWORD))


def test_login_upgrades_an_old_hash(anonymous_client: TestClient, session: Session) -> None:
    session.add(User(email="old@example.com", password_hash=PasswordHasher().hash(PASSWORD)))
    session.flush()

    response = anonymous_client.post(
        "/auth/login", json={"email": "old@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    stored = session.scalar(select(User.password_hash).where(User.email == "old@example.com"))
    assert stored is not None
    assert not needs_rehash(stored)


# --- Rate limits on the API ---


def login(client: TestClient, email: str, password: str = "Wr0ng-pass") -> int:
    return client.post("/auth/login", json={"email": email, "password": password}).status_code


def test_login_is_limited_per_email(anonymous_client: TestClient) -> None:
    codes = [login(anonymous_client, "target@example.com") for _ in range(6)]

    assert codes == [401] * 5 + [429]


def test_login_limit_per_email_does_not_block_other_emails(anonymous_client: TestClient) -> None:
    for _ in range(5):
        login(anonymous_client, "target@example.com")

    assert login(anonymous_client, "someone-else@example.com") == 401


def test_login_is_limited_per_ip(anonymous_client: TestClient) -> None:
    codes = [login(anonymous_client, f"user{i}@example.com") for i in range(11)]

    assert codes == [401] * 10 + [429]


def test_429_says_when_to_retry(anonymous_client: TestClient) -> None:
    for _ in range(5):
        login(anonymous_client, "target@example.com")

    response = anonymous_client.post(
        "/auth/login", json={"email": "target@example.com", "password": PASSWORD}
    )

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1


def test_registration_is_limited_per_ip(anonymous_client: TestClient) -> None:
    codes = [
        anonymous_client.post(
            "/auth/register", json={"email": f"new{i}@example.com", "password": PASSWORD}
        ).status_code
        for i in range(6)
    ]

    assert codes == [201] * 5 + [429]


# --- Secure cookies ---


@pytest.mark.parametrize(
    ("environment", "cookie_secure", "expected"),
    [
        ("local", None, False),  # plain http on localhost
        ("dev", None, True),
        ("prod", None, True),
        ("prod", False, False),  # an explicit setting always wins
        ("local", True, True),
    ],
)
def test_secure_cookies_follow_the_environment(
    environment: str, cookie_secure: bool | None, expected: bool
) -> None:
    settings = Settings(environment=environment, cookie_secure=cookie_secure)

    assert settings.secure_cookies() is expected
