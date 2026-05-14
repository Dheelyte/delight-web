"""Session lifecycle: revoke single, revoke all, token-after-logout is rejected."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import auth as auth_service
from app.services.sessions import load_session, revoke_all_user_sessions
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def test_token_works_until_logout(db_session: AsyncSession) -> None:
    user = await create_user(db_session, password="pw-12345678")
    token, _ = await auth_service.login(
        db_session,
        email=user.email,
        password="pw-12345678",
        ip=None,
        user_agent=None,
    )

    found = await load_session(db_session, token)
    assert found is not None and found.user_id == user.id

    await auth_service.logout(
        db_session, token=token, actor_id=user.id, ip=None, user_agent=None
    )
    assert await load_session(db_session, token) is None

    await db_session.rollback()


async def test_logout_all_revokes_every_session(db_session: AsyncSession) -> None:
    user = await create_user(db_session, password="pw-12345678")
    tokens = []
    for _ in range(3):
        t, _ = await auth_service.login(
            db_session,
            email=user.email,
            password="pw-12345678",
            ip=None,
            user_agent=None,
        )
        tokens.append(t)

    n = await revoke_all_user_sessions(db_session, user.id)
    assert n == 3
    for t in tokens:
        assert await load_session(db_session, t) is None

    await db_session.rollback()


async def test_load_session_with_garbage_token_returns_none(db_session: AsyncSession) -> None:
    assert await load_session(db_session, "not-a-real-token") is None
