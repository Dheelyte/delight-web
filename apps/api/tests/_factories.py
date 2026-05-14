"""Minimal test factories. Keep them inline-friendly; no faker, no fluent builders."""

from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.infra.db.models.users import User, UserRole


async def create_user(
    db: AsyncSession,
    *,
    email: str | None = None,
    password: str = "test-password-1234",
    role: UserRole = UserRole.editor,
    display_name: str = "Test User",
) -> User:
    user = User(
        email=email or f"u-{secrets.token_hex(6)}@test.local",
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
    )
    db.add(user)
    await db.flush()
    return user
