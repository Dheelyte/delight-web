"""Smoke tests that do not require a live database."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError


def test_settings_load() -> None:
    s = get_settings()
    assert s.ENVIRONMENT == "test"
    assert len(s.SECRET_KEY) >= 32


def test_error_hierarchy() -> None:
    assert issubclass(NotFoundError, AppError)
    err = NotFoundError("missing")
    assert err.status_code == 404
    assert err.code == "not_found"
