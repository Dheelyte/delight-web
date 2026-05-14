"""Cloudinary signing - deterministic + raises when unconfigured."""

from __future__ import annotations

import hashlib
import os
from unittest.mock import patch

import pytest

from app.core.errors import ExternalServiceError
from app.services import media as media_service


def test_sign_upload_raises_when_unconfigured() -> None:
    # The test conftest leaves Cloudinary unset.
    with pytest.raises(ExternalServiceError):
        media_service.sign_upload(folder=None)


def test_sign_upload_returns_valid_signature() -> None:
    env = {
        "CLOUDINARY_CLOUD_NAME": "demo",
        "CLOUDINARY_API_KEY": "key123",
        "CLOUDINARY_API_SECRET": "supersecret",
    }
    with patch.dict(os.environ, env, clear=False):
        from app.core.config import get_settings

        get_settings.cache_clear()  # type: ignore[attr-defined]
        try:
            with patch("app.services.media.time.time", return_value=1700000000):
                payload = media_service.sign_upload(folder="posts")
        finally:
            get_settings.cache_clear()  # type: ignore[attr-defined]

    assert payload["cloud_name"] == "demo"
    assert payload["api_key"] == "key123"
    assert payload["timestamp"] == 1700000000
    expected = hashlib.sha1(
        b"folder=posts&timestamp=1700000000supersecret"
    ).hexdigest()
    assert payload["signature"] == expected
