"""Security primitives: passwords, tokens, signed tokens, TOTP-secret encryption.

Everything that touches a cryptographic key lives here. Higher-level flows
(sessions, password reset, TOTP) compose these primitives.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Passwords (Argon2id)
# ---------------------------------------------------------------------------

_hasher = PasswordHasher(
    time_cost=3, memory_cost=64 * 1024, parallelism=2, hash_len=32, salt_len=16
)

# A fixed hash we verify against when the user is unknown. Comparing against
# this forces a real Argon2 verify so timing does not reveal account existence.
_DUMMY_HASH: Final = _hasher.hash("not-a-real-password-but-burns-the-cpu")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Constant-time-ish verify. Always runs Argon2 even when hash is None."""
    target = password_hash if password_hash is not None else _DUMMY_HASH
    try:
        _hasher.verify(target, password)
    except VerifyMismatchError:
        return False
    return password_hash is not None


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# ---------------------------------------------------------------------------
# Opaque tokens (sessions, unsubscribe links, etc.)
# ---------------------------------------------------------------------------


def generate_token(nbytes: int = 32) -> str:
    """URL-safe base64 token, defaults to 32 bytes of entropy."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """SHA-256 hex digest. Raw tokens are never stored — only this hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Signed, time-limited tokens (password reset, admin invite, unsubscribe)
# ---------------------------------------------------------------------------


def _hmac_key() -> bytes:
    return hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()


def sign_payload(payload: str) -> str:
    """Return `<payload>.<ts>.<hmac>`; verify_signed_payload checks the lot."""
    ts = str(int(time.time()))
    msg = f"{payload}.{ts}".encode("utf-8")
    sig = hmac.new(_hmac_key(), msg, hashlib.sha256).hexdigest()
    return f"{payload}.{ts}.{sig}"


def verify_signed_payload(signed: str, *, max_age_seconds: int) -> str | None:
    """Return the original payload if signature + freshness check pass, else None."""
    try:
        payload, ts_str, sig = signed.rsplit(".", 2)
    except ValueError:
        return None

    msg = f"{payload}.{ts_str}".encode("utf-8")
    expected = hmac.new(_hmac_key(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None

    try:
        ts = int(ts_str)
    except ValueError:
        return None

    if time.time() - ts > max_age_seconds:
        return None

    return payload


# ---------------------------------------------------------------------------
# TOTP-secret encryption at rest
# ---------------------------------------------------------------------------


def _fernet() -> Fernet:
    raw = hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("TOTP secret could not be decrypted") from exc
