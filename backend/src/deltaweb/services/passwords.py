"""Password rules and hashing (Argon2id, the current OWASP recommendation).

Only the hash is stored. Argon2 is slow and memory-hungry on purpose: checking one
password takes milliseconds, guessing billions from a stolen database does not scale.

Parameters: OWASP's "m=19 MiB, t=2, p=1" profile instead of argon2-cffi's default
(64 MiB, t=3, p=4). It is still within OWASP's recommendation, uses ~3.4x less memory
and is ~4x faster (~17 ms per hash on an Apple M3), which suits a 4 GB VPS. Each hash
stores its own parameters, so old hashes keep verifying; ``needs_rehash`` tells when one
should be upgraded. A semaphore caps how many hashes run at once, which bounds the
memory peak no matter how many requests arrive.
"""

import string
import threading

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from deltaweb.config import get_settings

_hasher = PasswordHasher(time_cost=2, memory_cost=19 * 1024, parallelism=1)
_slots = threading.BoundedSemaphore(get_settings().password_hash_concurrency)

MIN_LENGTH = 8
# Long enough for any passphrase; a cap stops someone sending megabytes to hash
MAX_LENGTH = 128
# Pass the rules below but are among the first guesses of any attacker
COMMON_PASSWORDS = frozenset(
    {
        "password1!",
        "password123!",
        "passw0rd!",
        "p@ssw0rd",
        "p@ssw0rd1",
        "p@ssword1",
        "qwerty123!",
        "qwerty1!",
        "welcome1!",
        "welcome123!",
        "admin123!",
        "abc123456!",
        "iloveyou1!",
        "letmein1!",
        "changeme1!",
        "123456aa!",
        "deltaweb1!",
    }
)


class WeakPasswordError(ValueError):
    """The password breaks one or more rules; ``problems`` lists them all."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def check_password_strength(password: str) -> None:
    """Raise WeakPasswordError listing every rule the password breaks (all at once, so the
    user can fix everything in one go)."""
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"at least {MIN_LENGTH} characters")
    if len(password) > MAX_LENGTH:
        problems.append(f"at most {MAX_LENGTH} characters")
    if not any(c.isupper() for c in password):
        problems.append("an uppercase letter")
    if not any(c.isdigit() for c in password):
        problems.append("a number")
    if not any(c in string.punctuation or not (c.isalnum() or c.isspace()) for c in password):
        problems.append("a symbol")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("not a common password")
    if problems:
        raise WeakPasswordError(problems)


def hash_password(password: str) -> str:
    """Argon2id hash with a random salt, e.g. ``$argon2id$v=19$m=19456,t=2,p=1$...``."""
    with _slots:
        return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """True if ``password`` matches. A missing hash (no password set) never matches."""
    with _slots:
        if password_hash is None:
            # Still do the work, so "no such account" and "wrong password" take the same time
            _hasher.hash(password)
            return False
        try:
            return _hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False


def needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with other parameters (e.g. the old 64 MiB default)."""
    return _hasher.check_needs_rehash(password_hash)
