"""Analytics: bot filter, debounce, top-posts ranking."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.users import UserRole
from app.services import analytics, posts as posts_service
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


REAL_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


async def _published(db, actor, title):
    p = await posts_service.create_post(db, actor=actor, title=title, excerpt=None)
    await posts_service.publish(db, actor=actor, post=p)
    return p


async def test_bot_user_agent_is_skipped(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published(db_session, admin, "x")
    inserted = await analytics.record_view(
        db_session, post_slug=post.slug, ip="1.1.1.1",
        user_agent="Googlebot/2.1 (+http://www.google.com/bot.html)",
        referrer=None,
    )
    assert inserted is False
    await db_session.rollback()


async def test_view_records_then_debounces(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published(db_session, admin, "x")
    first = await analytics.record_view(
        db_session, post_slug=post.slug, ip="1.1.1.1",
        user_agent=REAL_UA, referrer="https://news.example/",
    )
    assert first is True
    second = await analytics.record_view(
        db_session, post_slug=post.slug, ip="1.1.1.1",
        user_agent=REAL_UA, referrer=None,
    )
    assert second is False  # same session within debounce window
    await db_session.rollback()


async def test_top_posts_orders_by_views_desc(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    a = await _published(db_session, admin, "Aleph")
    b = await _published(db_session, admin, "Beth")
    c = await _published(db_session, admin, "Gimel")

    # 3 unique viewers on `b`, 2 on `a`, 0 on `c`.
    for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        await analytics.record_view(
            db_session, post_slug=b.slug, ip=ip, user_agent=REAL_UA, referrer=None,
        )
    for ip in ("4.4.4.4", "5.5.5.5"):
        await analytics.record_view(
            db_session, post_slug=a.slug, ip=ip, user_agent=REAL_UA, referrer=None,
        )

    rows = await analytics.top_posts(db_session, window=30)
    titles = [p.title for p, _ in rows]
    counts = {p.title: v for p, v in rows}
    assert titles[0] == "Beth"
    assert titles[1] == "Aleph"
    assert counts["Beth"] == 3
    assert counts["Aleph"] == 2
    assert "Gimel" not in counts
    await db_session.rollback()


async def test_unknown_slug_does_not_insert(db_session: AsyncSession) -> None:
    inserted = await analytics.record_view(
        db_session, post_slug="ghost", ip="1.1.1.1",
        user_agent=REAL_UA, referrer=None,
    )
    assert inserted is False
    await db_session.rollback()
