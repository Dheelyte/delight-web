"""Password reset: signed token, expiry, single-use behaviour."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError
from app.core.security import verify_password
from app.infra.db.models.users import User
from app.services import auth as auth_service
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def test_reset_unknown_email_returns_none_no_leak(db_session: AsyncSession) -> None:
    token = await auth_service.request_password_reset(
        db_session, email="ghost@test.local", ip=None, user_agent=None
    )
    assert token is None
    await db_session.rollback()


async def test_reset_round_trip(db_session: AsyncSession) -> None:
    user = await create_user(db_session, password="old-password-1234")
    token = await auth_service.request_password_reset(
        db_session, email=user.email, ip=None, user_agent=None
    )
    assert token is not None

    await auth_service.confirm_password_reset(
        db_session,
        signed_token=token,
        new_password="brand-new-password-9876",
        ip=None,
        user_agent=None,
    )

    fresh = (
        await db_session.execute(select(User).where(User.id == user.id))
    ).scalar_one()
    assert verify_password("brand-new-password-9876", fresh.password_hash)
    assert not verify_password("old-password-1234", fresh.password_hash)

    await db_session.rollback()


async def test_reset_token_expired_is_rejected(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    token = await auth_service.request_password_reset(
        db_session, email=user.email, ip=None, user_agent=None
    )
    assert token is not None

    # Jump 16 minutes into the future — past the 15-minute TTL.
    with patch("app.core.security.time.time", return_value=time.time() + 16 * 60):
        with pytest.raises(AuthError):
            await auth_service.confirm_password_reset(
                db_session,
                signed_token=token,
                new_password="brand-new-password-9876",
                ip=None,
                user_agent=None,
            )

    await db_session.rollback()


async def test_reset_token_tampered_is_rejected(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    token = await auth_service.request_password_reset(
        db_session, email=user.email, ip=None, user_agent=None
    )
    assert token is not None
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(AuthError):
        await auth_service.confirm_password_reset(
            db_session,
            signed_token=tampered,
            new_password="brand-new-password-9876",
            ip=None,
            user_agent=None,
        )
    await db_session.rollback()
