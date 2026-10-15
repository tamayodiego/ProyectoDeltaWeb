"""Password rules and hashing. No database needed."""

import pytest

from deltaweb.services.passwords import (
    WeakPasswordError,
    check_password_strength,
    hash_password,
    verify_password,
)


@pytest.mark.parametrize(
    "password", ["Sup3r-secret", "Delta#2026", "Ñandú-99x", "Gr4fo con espacio!"]
)
def test_strong_passwords_pass(password: str) -> None:
    check_password_strength(password)


@pytest.mark.parametrize(
    ("password", "missing"),
    [
        ("Ab1!", "at least 8 characters"),
        ("sup3r-secret", "an uppercase letter"),
        ("Super-secret", "a number"),
        ("Sup3rsecret", "a symbol"),
        ("Password1!", "not a common password"),
        ("PASSWORD1!", "not a common password"),  # common list ignores case
        ("A1!" + "x" * 200, "at most 128 characters"),
    ],
)
def test_weak_passwords_say_what_is_missing(password: str, missing: str) -> None:
    with pytest.raises(WeakPasswordError) as exc:
        check_password_strength(password)

    assert missing in exc.value.problems


def test_every_problem_is_reported_at_once() -> None:
    with pytest.raises(WeakPasswordError) as exc:
        check_password_strength("abc")

    assert set(exc.value.problems) == {
        "at least 8 characters",
        "an uppercase letter",
        "a number",
        "a symbol",
    }


def test_hash_is_argon2id_and_salted() -> None:
    first = hash_password("Sup3r-secret")
    second = hash_password("Sup3r-secret")

    assert first.startswith("$argon2id$")
    assert "Sup3r-secret" not in first
    assert first != second  # a random salt each time


def test_verify() -> None:
    stored = hash_password("Sup3r-secret")

    assert verify_password("Sup3r-secret", stored)
    assert not verify_password("sup3r-secret", stored)
    assert not verify_password("Sup3r-secret", None)  # account without a password
    assert not verify_password("Sup3r-secret", "not-a-hash")
