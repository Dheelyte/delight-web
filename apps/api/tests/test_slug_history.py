"""Verify the slug-change ORM event listener writes to slug_history."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.infra.db.models.content import Post, PostStatus
from app.infra.db.models.system import SlugEntityType, SlugHistory
from app.infra.db.models.users import User, UserRole

pytestmark = pytest.mark.usefixtures("db_session")


async def test_slug_change_records_history(db_session: AsyncSession) -> None:
    user = User(
        email="slug-author@test.local",
        password_hash=hash_password("test-password"),
        role=UserRole.editor,
        display_name="Slug Author",
    )
    db_session.add(user)
    await db_session.flush()

    post = Post(
        slug="original-slug",
        title="A post that will be renamed",
        content_html="",
        content_json={},
        author_id=user.id,
        status=PostStatus.draft,
    )
    db_session.add(post)
    await db_session.flush()

    # No history row on initial insert.
    history = (
        await db_session.execute(
            select(SlugHistory).where(SlugHistory.entity_id == post.id)
        )
    ).scalars().all()
    assert history == []

    post.slug = "renamed-slug"
    await db_session.flush()

    history = (
        await db_session.execute(
            select(SlugHistory).where(SlugHistory.entity_id == post.id)
        )
    ).scalars().all()
    assert len(history) == 1
    row = history[0]
    assert row.entity_type == SlugEntityType.post
    assert row.old_slug == "original-slug"
    assert row.new_slug == "renamed-slug"

    await db_session.rollback()
