"""Session lifecycle: create, load, touch, revoke. See ADR 003."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_token, hash_token
from app.infra.db.models.auth import Session

SESSION_TTL = timedelta(days=14)


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def create_session(
    db: AsyncSession,
    *,
    user_id: UUID,
    ip: str | None,
    user_agent: str | None,
    ttl: timedelta = SESSION_TTL,
) -> tuple[str, Session]:
    """Returns (raw_token_for_cookie, persisted_session)."""
    token = generate_token()
    row = Session(
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=_now() + ttl,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(row)
    await db.flush()
    return token, row


async def load_session(db: AsyncSession, token: str) -> Session | None:
    """Look up a session by raw token. Updates last_seen_at on hit. None if missing/expired."""
    row = (
        await db.execute(select(Session).where(Session.token_hash == hash_token(token)))
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at <= _now():
        await db.delete(row)
        return None
    row.last_seen_at = _now()
    return row


async def revoke_session(db: AsyncSession, token: str) -> bool:
    result = await db.execute(
        delete(Session).where(Session.token_hash == hash_token(token))
    )
    return (result.rowcount or 0) > 0


async def revoke_all_user_sessions(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(delete(Session).where(Session.user_id == user_id))
    return result.rowcount or 0
