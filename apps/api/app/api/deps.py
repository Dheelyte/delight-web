"""FastAPI dependencies: DB session, current user, role/ownership guards."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from uuid import UUID

from fastapi import Cookie, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_sessionmaker
from app.core.errors import AuthError, ForbiddenError, NotFoundError
from app.infra.db.models.content import Post
from app.infra.db.models.users import User, UserRole
from app.services.sessions import load_session

SESSION_COOKIE = "session"


async def get_db() -> AsyncIterator[AsyncSession]:
    """Per-request transaction. Commits on success, rolls back on exception."""
    factory = get_sessionmaker()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def current_user_optional(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if session_token is None:
        return None
    row = await load_session(db, session_token)
    if row is None:
        return None
    user = (
        await db.execute(select(User).where(User.id == row.user_id))
    ).scalar_one_or_none()
    return user


async def current_user(
    user: User | None = Depends(current_user_optional),
) -> User:
    if user is None:
        raise AuthError("Authentication required.")
    return user


def require_role(*roles: UserRole) -> Callable[..., User]:
    allowed = set(roles)

    async def _dep(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError("Insufficient role.")
        return user

    return _dep


require_admin = require_role(UserRole.admin)
require_editor_or_admin = require_role(UserRole.editor, UserRole.admin)


async def require_post_ownership(
    post_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Post:
    """Admin always passes; editors only for their own posts."""
    post = (
        await db.execute(select(Post).where(Post.id == post_id))
    ).scalar_one_or_none()
    if post is None:
        raise NotFoundError("Post not found.")
    if user.role is UserRole.admin:
        return post
    if user.role is UserRole.editor and post.author_id == user.id:
        return post
    raise ForbiddenError("You may not modify this post.")
