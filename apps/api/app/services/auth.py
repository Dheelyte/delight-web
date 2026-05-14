"""Authentication flows: login, logout, signup-by-admin-invite, password reset."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import (
    hash_password,
    sign_payload,
    verify_password,
    verify_signed_payload,
)
from app.infra.db.models.auth import AuthAttemptKind, Session
from app.infra.db.models.users import User, UserRole
from app.services import audit, sessions, throttle

PASSWORD_RESET_MAX_AGE: Final = 15 * 60  # 15 minutes


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def login(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[str, Session]:
    """Returns (raw_session_token, session_row). Account-enumeration-safe."""
    identifier = email.lower()
    await throttle.check_allowed(db, identifier=identifier, kind=AuthAttemptKind.login)

    user = (
        await db.execute(select(User).where(User.email == identifier))
    ).scalar_one_or_none()

    # Always run a password hash to avoid timing/account enumeration.
    password_ok = verify_password(password, user.password_hash if user else None)

    succeeded = user is not None and password_ok
    await throttle.record_attempt(
        db, identifier=identifier, kind=AuthAttemptKind.login, succeeded=succeeded
    )

    if not succeeded:
        # Single, identical failure mode for all rejections.
        raise AuthError("Invalid credentials.")

    assert user is not None  # for type-checker; succeeded implies user is not None
    token, row = await sessions.create_session(
        db, user_id=user.id, ip=ip, user_agent=user_agent
    )
    await audit.write(
        db,
        actor_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
    )
    return token, row


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def logout(
    db: AsyncSession,
    *,
    token: str,
    actor_id: UUID | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    revoked = await sessions.revoke_session(db, token)
    if revoked:
        await audit.write(
            db,
            actor_id=actor_id,
            action="auth.logout",
            resource_type="user",
            resource_id=None if actor_id is None else str(actor_id),
            ip=ip,
            user_agent=user_agent,
        )


async def logout_all(
    db: AsyncSession,
    *,
    user_id: UUID,
    ip: str | None,
    user_agent: str | None,
) -> int:
    n = await sessions.revoke_all_user_sessions(db, user_id)
    await audit.write(
        db,
        actor_id=user_id,
        action="auth.logout_all",
        resource_type="user",
        resource_id=str(user_id),
        metadata={"sessions_revoked": n},
        ip=ip,
        user_agent=user_agent,
    )
    return n


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


async def request_password_reset(
    db: AsyncSession,
    *,
    email: str,
    ip: str | None,
    user_agent: str | None,
) -> str | None:
    """Always returns silently to prevent account enumeration.

    Returns the signed token *only when a real reset was initiated*, so the
    caller (or an outbox-driven email job) can deliver it. The HTTP layer
    must NOT leak this return value to the requester.
    """
    identifier = email.lower()
    await throttle.check_allowed(db, identifier=identifier, kind=AuthAttemptKind.reset)
    user = (
        await db.execute(select(User).where(User.email == identifier))
    ).scalar_one_or_none()

    await throttle.record_attempt(
        db, identifier=identifier, kind=AuthAttemptKind.reset, succeeded=user is not None
    )

    if user is None:
        return None

    token = sign_payload(str(user.id))
    await audit.write(
        db,
        actor_id=user.id,
        action="auth.password_reset.requested",
        resource_type="user",
        resource_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
    )
    return token


async def confirm_password_reset(
    db: AsyncSession,
    *,
    signed_token: str,
    new_password: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    payload = verify_signed_payload(signed_token, max_age_seconds=PASSWORD_RESET_MAX_AGE)
    if payload is None:
        raise AuthError("Reset token is invalid or expired.")

    try:
        user_id = UUID(payload)
    except ValueError as exc:
        raise AuthError("Reset token is invalid.") from exc

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise AuthError("Reset token is invalid.")

    # Reset password and revoke all existing sessions.
    user.password_hash = hash_password(new_password)
    await sessions.revoke_all_user_sessions(db, user.id)

    await audit.write(
        db,
        actor_id=user.id,
        action="auth.password_reset.confirmed",
        resource_type="user",
        resource_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Admin-only signup (invite-based account creation)
# ---------------------------------------------------------------------------


async def admin_create_user(
    db: AsyncSession,
    *,
    actor: User,
    email: str,
    password: str,
    role: UserRole,
    display_name: str,
    ip: str | None,
    user_agent: str | None,
) -> User:
    if actor.role is not UserRole.admin:
        raise ForbiddenError("Only admins can create users.")

    identifier = email.lower()
    existing = (
        await db.execute(select(User).where(User.email == identifier))
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("User already exists.")

    user = User(
        email=identifier,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
    )
    db.add(user)
    await db.flush()

    await audit.write(
        db,
        actor_id=actor.id,
        action="user.created",
        resource_type="user",
        resource_id=str(user.id),
        metadata={"role": role.value, "email": identifier},
        ip=ip,
        user_agent=user_agent,
    )
    return user


# ---------------------------------------------------------------------------
# Helper for tests / scripts
# ---------------------------------------------------------------------------


async def get_user_by_email(db: AsyncSession, email: str) -> User:
    user = (
        await db.execute(select(User).where(User.email == email.lower()))
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundError(f"User {email} not found.")
    return user
