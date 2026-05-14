"""Login flow: success, bad password, account enumeration, throttling, audit."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError
from app.infra.db.models.auth import AuthAttempt, AuthAttemptKind, Session
from app.infra.db.models.system import AuditLog
from app.services import auth as auth_service
from app.services.throttle import SHORT_MAX_FAILURES, ThrottledError
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def test_login_success_creates_session_and_audit(db_session: AsyncSession) -> None:
    user = await create_user(db_session, password="correct-horse-battery")

    token, row = await auth_service.login(
        db_session,
        email=user.email,
        password="correct-horse-battery",
        ip="1.2.3.4",
        user_agent="pytest",
    )

    assert token
    assert row.user_id == user.id

    sessions = (await db_session.execute(select(Session))).scalars().all()
    assert any(s.user_id == user.id for s in sessions)

    audit_rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "auth.login")
        )
    ).scalars().all()
    assert any(a.actor_id == user.id for a in audit_rows)

    await db_session.rollback()


async def test_login_wrong_password_raises_auth_error(db_session: AsyncSession) -> None:
    user = await create_user(db_session, password="correct-horse-battery")

    with pytest.raises(AuthError):
        await auth_service.login(
            db_session,
            email=user.email,
            password="wrong",
            ip=None,
            user_agent=None,
        )

    # Failed attempt recorded.
    fails = (
        await db_session.execute(
            select(AuthAttempt).where(
                AuthAttempt.identifier == user.email.lower(),
                AuthAttempt.succeeded.is_(False),
            )
        )
    ).scalars().all()
    assert len(fails) == 1

    await db_session.rollback()


async def test_login_unknown_user_indistinguishable(db_session: AsyncSession) -> None:
    """Same error class, no leaked timing pathway - and an auth_attempt row."""
    with pytest.raises(AuthError):
        await auth_service.login(
            db_session,
            email="does-not-exist@test.local",
            password="anything",
            ip=None,
            user_agent=None,
        )

    fails = (
        await db_session.execute(
            select(AuthAttempt).where(
                AuthAttempt.identifier == "does-not-exist@test.local"
            )
        )
    ).scalars().all()
    assert len(fails) == 1
    assert fails[0].succeeded is False

    await db_session.rollback()


async def test_login_throttle_kicks_in(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    for _ in range(SHORT_MAX_FAILURES):
        with pytest.raises(AuthError):
            await auth_service.login(
                db_session,
                email=user.email,
                password="wrong",
                ip=None,
                user_agent=None,
            )

    with pytest.raises(ThrottledError):
        await auth_service.login(
            db_session,
            email=user.email,
            password="wrong",
            ip=None,
            user_agent=None,
        )

    await db_session.rollback()
