"""Chore rules. Pure Python: no Home Assistant imports, so it is easy to test."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def is_valid_pin(pin: str, min_len: int = 4, max_len: int = 8) -> bool:
    """Return True if the PIN is min_len..max_len digits."""
    return pin.isdigit() and min_len <= len(pin) <= max_len


def hash_pin(pin: str) -> str:
    """Hash a PIN with a random salt. Format: scrypt$<salt hex>$<hash hex>."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    """Check a PIN against a stored hash in constant time."""
    try:
        algo, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return hmac.compare_digest(digest.hex(), digest_hex)
