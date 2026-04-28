"""PBKDF2-HMAC-SHA256 password hashing for the app-lock PIN.

The lock PIN was historically stored as plaintext in user_profile.json. To
preserve backwards compatibility while migrating, we use a versioned string
format with a clear prefix:

    pbkdf2_sha256$<iterations>$<base64-salt>$<base64-hash>

`is_hashed()` detects the format. `verify_password()` accepts both new (hashed)
and legacy (plaintext) stored values, so users with an existing plaintext PIN
keep working until the next time the profile is saved — at which point
`UserProfileStore.save()` rewrites the stored value as a hash.

Constant-time comparison via `hmac.compare_digest` prevents timing leaks.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Optional

_PREFIX = "pbkdf2_sha256"
_ITERATIONS = 200_000  # NIST-aligned; ~50–100 ms on a modern laptop.
_SALT_BYTES = 16
_HASH_BYTES = 32


def is_hashed(stored: Optional[str]) -> bool:
    """Return True if *stored* is in the versioned hash format."""
    return bool(stored) and stored.startswith(_PREFIX + "$")  # type: ignore[union-attr]


def hash_password(plaintext: str) -> str:
    """Hash *plaintext* with a fresh random salt and return the encoded form.

    Returns an empty string for an empty input — callers treat that the same
    as "no password set".
    """
    if not plaintext:
        return ""
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        plaintext.encode("utf-8"),
        salt,
        _ITERATIONS,
        dklen=_HASH_BYTES,
    )
    return (
        f"{_PREFIX}${_ITERATIONS}"
        f"${base64.b64encode(salt).decode('ascii')}"
        f"${base64.b64encode(digest).decode('ascii')}"
    )


def verify_password(plaintext: str, stored: Optional[str]) -> bool:
    """Return True if *plaintext* matches *stored*.

    Accepts both the new hashed format and legacy plaintext entries, so an
    upgrade from an older user_profile.json doesn't lock the user out.
    """
    if not stored:
        return False
    if not is_hashed(stored):
        # Legacy plaintext: accept direct comparison so existing users still
        # log in. The next save will rewrite this in hashed form.
        return hmac.compare_digest(plaintext or "", stored)
    try:
        prefix, iters_s, salt_b64, hash_b64 = stored.split("$", 3)
        if prefix != _PREFIX:
            return False
        iters = int(iters_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            (plaintext or "").encode("utf-8"),
            salt,
            iters,
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False
