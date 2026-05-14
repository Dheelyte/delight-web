"""Sliding-window auth throttling backed by the `auth_attempts` table.

Two limits per (identifier, kind):
- short:  5 failures per 60s
- long:   20 failures per 3600s

Successful attempts are recorded too but do not consume budget.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.infra.db.models.auth import AuthAttempt, AuthAttemptKind

SHORT_WINDOW = timedelta(seconds=60)
SHORT_MAX_FAILURES = 5
LONG_WINDOW = timedelta(seconds=3600)
LONG_MAX_FAILURES = 20


class ThrottledError(AppError):
    status_code = 429
    code = "throttled"


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def _failures_within(
    db: AsyncSession,
    *,
    identifier: str,
    kind: AuthAttemptKind,
    since: datetime,
) -> int:
    stmt = select(func.count()).select_from(AuthAttempt).where(
        AuthAttempt.identifier == identifier,
        AuthAttempt.kind == kind,
        AuthAttempt.succeeded.is_(False),
        AuthAttempt.attempted_at >= since,
    )
    return (await db.execute(stmt)).scalar_one()


async def check_allowed(
    db: AsyncSession, *, identifier: str, kind: AuthAttemptKind
) -> None:
    now = _now()
    short = await _failures_within(
        db, identifier=identifier, kind=kind, since=now - SHORT_WINDOW
    )
    if short >= SHORT_MAX_FAILURES:
        raise ThrottledError("Too many attempts. Try again in a minute.")
    long = await _failures_within(
        db, identifier=identifier, kind=kind, since=now - LONG_WINDOW
    )
    if long >= LONG_MAX_FAILURES:
        raise ThrottledError("Too many attempts. Try again later.")


async def record_attempt(
    db: AsyncSession,
    *,
    identifier: str,
    kind: AuthAttemptKind,
    succeeded: bool,
) -> None:
    db.add(AuthAttempt(identifier=identifier, kind=kind, succeeded=succeeded))
    await db.flush()
