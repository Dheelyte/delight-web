"""Post lifecycle: create, save, transitions, ownership, slug-history side effect."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infra.db.models.content import PostStatus
from app.infra.db.models.system import SlugEntityType, SlugHistory
from app.infra.db.models.users import UserRole
from app.services import posts as posts_service
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def _new_post(db, actor, title="My Post"):
    return await posts_service.create_post(db, actor=actor, title=title, excerpt=None)


async def test_create_post_generates_unique_slug(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    p1 = await _new_post(db_session, actor, title="My Post")
    p2 = await _new_post(db_session, actor, title="My Post")
    assert p1.slug == "my-post"
    assert p2.slug.startswith("my-post-")
    await db_session.rollback()


async def test_state_transitions_round_trip(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    post = await _new_post(db_session, actor)

    await posts_service.publish(db_session, actor=actor, post=post)
    assert post.status is PostStatus.published
    assert post.published_at is not None

    await posts_service.unpublish(db_session, actor=actor, post=post)
    assert post.status is PostStatus.draft
    assert post.published_at is None

    await posts_service.archive(db_session, actor=actor, post=post)
    assert post.status is PostStatus.archived

    await db_session.rollback()


async def test_delete_post_removes_it(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    post = await _new_post(db_session, actor)
    pid = post.id
    await posts_service.delete_post(db_session, actor=actor, post=post)
    with pytest.raises(NotFoundError):
        await posts_service.get_post(db_session, pid)
    await db_session.rollback()


async def test_metadata_slug_change_writes_history(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    post = await _new_post(db_session, actor, title="Original")
    old_slug = post.slug

    await posts_service.update_post_metadata(
        db_session,
        actor=actor,
        post=post,
        slug="new-slug-here",
        cover_image_id=None,
        category_id=None,
        series_id=None,
        series_order=None,
        tag_ids=None,
        meta_title=None,
        meta_description=None,
        canonical_url=None,
        robots=None,
    )
    await db_session.flush()

    rows = (
        await db_session.execute(
            select(SlugHistory).where(SlugHistory.entity_id == post.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].entity_type is SlugEntityType.post
    assert rows[0].old_slug == old_slug
    assert rows[0].new_slug == "new-slug-here"
    await db_session.rollback()


async def test_slug_collision_rejected(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    p1 = await _new_post(db_session, actor, title="Alpha")
    p2 = await _new_post(db_session, actor, title="Beta")
    from app.core.errors import ConflictError

    with pytest.raises(ConflictError):
        await posts_service.update_post_metadata(
            db_session, actor=actor, post=p2, slug=p1.slug,
            cover_image_id=None, category_id=None, series_id=None,
            series_order=None, tag_ids=None, meta_title=None,
            meta_description=None, canonical_url=None, robots=None,
        )
    await db_session.rollback()
