"""Schema-level integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.usefixtures("db_session")

EXPECTED_TABLES = {
    "users",
    "sessions",
    "auth_attempts",
    "media",
    "tags",
    "categories",
    "series",
    "posts",
    "post_tags",
    "post_revisions",
    "comments",
    "subscribers",
    "page_views",
    "audit_log",
    "slug_history",
    "outbox",
}


async def test_all_tables_present(db_session: AsyncSession) -> None:
    rows = (
        await db_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename = ANY(:names)"
            ),
            {"names": list(EXPECTED_TABLES)},
        )
    ).all()
    present = {r[0] for r in rows}
    assert present == EXPECTED_TABLES


async def test_page_views_is_partitioned(db_session: AsyncSession) -> None:
    row = (
        await db_session.execute(
            text(
                "SELECT relkind FROM pg_class WHERE relname = 'page_views'",
            )
        )
    ).scalar_one()
    # 'p' = partitioned table; 'r' = ordinary
    assert row == "p"


async def test_posts_search_vector_trigger(db_session: AsyncSession) -> None:
    from app.core.security import hash_password
    from app.infra.db.models.content import Post, PostStatus
    from app.infra.db.models.users import User, UserRole

    user = User(
        email="search@test.local",
        password_hash=hash_password("test-password"),
        role=UserRole.admin,
        display_name="Searcher",
    )
    db_session.add(user)
    await db_session.flush()

    post = Post(
        slug="trigger-test",
        title="The unique searchable phrase floccinaucinihilipilification",
        excerpt="needle",
        content_html="<p>haystack</p>",
        content_json={},
        author_id=user.id,
        status=PostStatus.draft,
    )
    db_session.add(post)
    await db_session.flush()
    await db_session.refresh(post, attribute_names=["search_vector"])

    assert post.search_vector is not None
    assert "floccinaucinihilipilification" in str(post.search_vector)

    # Cleanup so the DB stays usable for the next test.
    await db_session.rollback()
