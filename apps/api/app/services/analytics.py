"""Page views + top-posts aggregation.

The view recorder is intentionally cheap (one INSERT). Heavy aggregation
happens at read time on the admin dashboard, with the result memoised by
the route handler's HTTP cache.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infra.db.models.content import Post, PostStatus
from app.infra.db.models.system import PageView

_BOT_UA_RE = re.compile(
    r"(?:bot|crawler|spider|crawling|preview|monitor|fetch|scrape|curl|wget|httpx|python|go-http|axios)",
    re.IGNORECASE,
)


def is_bot(user_agent: str | None) -> bool:
    if not user_agent:
        return True
    return _BOT_UA_RE.search(user_agent) is not None


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _session_hash(*, ip: str | None, user_agent: str | None, today: date) -> str:
    salt = get_settings().secret_key
    raw = f"{salt}|{ip or 'anon'}|{user_agent or 'anon'}|{today.isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


async def record_view(
    db: AsyncSession,
    *,
    post_slug: str,
    ip: str | None,
    user_agent: str | None,
    referrer: str | None,
) -> bool:
    """Returns True if a row was inserted (False on bot or unknown slug)."""
    if is_bot(user_agent):
        return False

    post = (
        await db.execute(
            select(Post.id).where(
                Post.slug == post_slug, Post.status == PostStatus.published
            )
        )
    ).scalar_one_or_none()
    if post is None:
        return False

    now = _now()
    session = _session_hash(ip=ip, user_agent=user_agent, today=now.date())

    # Debounce: same session + same post in the last hour → skip.
    cutoff = now - timedelta(hours=1)
    seen = (
        await db.execute(
            select(PageView.id)
            .where(
                PageView.post_id == post,
                PageView.session_hash == session,
                PageView.viewed_at >= cutoff,
            )
            .limit(1)
        )
    ).first()
    if seen:
        return False

    db.add(
        PageView(
            id=uuid4(),
            post_id=post,
            session_hash=session,
            referrer_host=_host_only(referrer),
            country_code=None,  # GeoIP wiring deferred — see docs/deferred.md
        )
    )
    return True


def _host_only(referrer: str | None) -> str | None:
    if not referrer:
        return None
    try:
        from urllib.parse import urlparse

        host = urlparse(referrer).hostname
        return host[:255] if host else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------


Window = Literal[7, 30, 90]


async def top_posts(
    db: AsyncSession, *, window: Window, limit: int = 10
) -> list[tuple[Post, int]]:
    since = _now() - timedelta(days=window)
    views = func.count(PageView.id).label("views")
    rows = (
        await db.execute(
            select(Post, views)
            .join(PageView, PageView.post_id == Post.id)
            .where(PageView.viewed_at >= since)
            .group_by(Post.id)
            .order_by(desc(views))
            .limit(limit)
        )
    ).all()
    return [(p, int(v)) for p, v in rows]


async def top_referrers(
    db: AsyncSession, *, window: Window, limit: int = 10
) -> list[tuple[str, int]]:
    since = _now() - timedelta(days=window)
    views = func.count(PageView.id).label("views")
    rows = (
        await db.execute(
            select(PageView.referrer_host, views)
            .where(
                PageView.viewed_at >= since,
                PageView.referrer_host.isnot(None),
            )
            .group_by(PageView.referrer_host)
            .order_by(desc(views))
            .limit(limit)
        )
    ).all()
    return [(h, int(v)) for h, v in rows]


