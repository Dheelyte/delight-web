"""Unit tests for the crypto primitives. No DB required."""

from __future__ import annotations

import time
from unittest.mock import patch

from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    generate_token,
    hash_password,
    hash_token,
    needs_rehash,
    sign_payload,
    verify_password,
    verify_signed_payload,
)


def test_password_round_trip() -> None:
    h = hash_password("hunter2")
    assert verify_password("hunter2", h)
    assert not verify_password("hunter3", h)


def test_verify_password_with_none_runs_but_fails() -> None:
    # Must return False *and* still perform real work (we cannot directly
    # measure timing here; covered by the integration test for enumeration).
    assert verify_password("anything", None) is False


def test_needs_rehash_false_for_current_params() -> None:
    assert not needs_rehash(hash_password("hunter2"))


def test_token_hash_is_deterministic_and_hex() -> None:
    t = generate_token()
    h = hash_token(t)
    assert len(h) == 64
    assert hash_token(t) == h


def test_signed_payload_round_trip() -> None:
    signed = sign_payload("payload-123")
    assert verify_signed_payload(signed, max_age_seconds=60) == "payload-123"


def test_signed_payload_expired() -> None:
    signed = sign_payload("p")
    with patch("app.core.security.time.time", return_value=time.time() + 120):
        assert verify_signed_payload(signed, max_age_seconds=60) is None


def test_signed_payload_tampered() -> None:
    signed = sign_payload("p")
    bad = signed[:-1] + ("a" if not signed.endswith("a") else "b")
    assert verify_signed_payload(bad, max_age_seconds=60) is None


def test_secret_encryption_round_trip() -> None:
    ct = encrypt_secret("JBSWY3DPEHPK3PXP")
    assert ct != "JBSWY3DPEHPK3PXP"
    assert decrypt_secret(ct) == "JBSWY3DPEHPK3PXP"
