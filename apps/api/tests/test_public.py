"""Public read surface: listing, slug-history follow, search, related."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infra.db.models.content import PostStatus, PostTag
from app.infra.db.models.system import SlugEntityType
from app.infra.db.models.users import UserRole
from app.services import posts as posts_service, public, taxonomy
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def _published(db, actor, *, title="P", slug=None):
    p = await posts_service.create_post(db, actor=actor, title=title, excerpt=None)
    if slug:
        p.slug = slug
    await posts_service.publish(db, actor=actor, post=p)
    return p


async def test_list_published_excludes_drafts_and_future_scheduled(
    db_session: AsyncSession,
) -> None:
    actor = await create_user(db_session, role=UserRole.admin)
    draft = await posts_service.create_post(
        db_session, actor=actor, title="Draft", excerpt=None
    )
    live = await _published(db_session, actor, title="Live")
    future = await posts_service.create_post(
        db_session, actor=actor, title="Future", excerpt=None
    )
    future.status = PostStatus.published
    future.published_at = datetime.now(tz=UTC) + timedelta(days=1)
    await db_session.flush()

    rows, total = await public.list_published(db_session, limit=10, offset=0)
    slugs = {p.slug for p in rows}
    assert live.slug in slugs
    assert draft.slug not in slugs
    assert future.slug not in slugs
    assert total >= 1
    await db_session.rollback()


async def test_search_partial_word_falls_back_to_ilike(db_session: AsyncSession) -> None:
    """`plainto_tsquery` won't match "server" against "serverless" - the ILIKE
    branch is what keeps partial-word queries useful for readers."""
    actor = await create_user(db_session, role=UserRole.admin)
    post = await _published(db_session, actor, title="The serverless trade-offs")

    rows, total = await public.search(db_session, q="server", limit=10, offset=0)
    assert total >= 1
    assert post.id in [r.id for r in rows]
    await db_session.rollback()


async def test_search_ranks_title_match_higher(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.admin)
    title_match = await _published(db_session, actor, title="quantum entanglement")
    body_match = await posts_service.create_post(
        db_session, actor=actor,
        title="Bridges of New York", excerpt="quantum entanglement is mentioned in passing",
    )
    await posts_service.publish(db_session, actor=actor, post=body_match)
    await db_session.flush()

    rows, _ = await public.search(db_session, q="quantum entanglement", limit=10, offset=0)
    assert rows
    assert rows[0].id == title_match.id
    await db_session.rollback()


async def test_related_posts_prefers_higher_overlap(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.admin)
    t1 = await taxonomy.create_tag(db_session, actor=actor, name="Alpha")
    t2 = await taxonomy.create_tag(db_session, actor=actor, name="Beta")

    target = await _published(db_session, actor, title="Target")
    overlap2 = await _published(db_session, actor, title="Two tags")
    overlap1 = await _published(db_session, actor, title="One tag")
    unrelated = await _published(db_session, actor, title="Unrelated")

    db_session.add_all([
        PostTag(post_id=target.id, tag_id=t1.id),
        PostTag(post_id=target.id, tag_id=t2.id),
        PostTag(post_id=overlap2.id, tag_id=t1.id),
        PostTag(post_id=overlap2.id, tag_id=t2.id),
        PostTag(post_id=overlap1.id, tag_id=t1.id),
    ])
    await db_session.flush()

    rows = await public.related_posts(db_session, post=target)
    ids = [p.id for p in rows]
    assert overlap2.id in ids and overlap1.id in ids
    assert ids.index(overlap2.id) < ids.index(overlap1.id)
    assert unrelated.id not in ids
    await db_session.rollback()


async def test_slug_history_follows_rename_chain(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    post = await posts_service.create_post(
        db_session, actor=actor, title="Renamed", excerpt=None
    )
    await posts_service.update_post_metadata(
        db_session, actor=actor, post=post, slug="middle-slug",
        cover_image_id=None, category_id=None, series_id=None,
        series_order=None, tag_ids=None, meta_title=None,
        meta_description=None, canonical_url=None, robots=None,
    )
    await posts_service.update_post_metadata(
        db_session, actor=actor, post=post, slug="final-slug",
        cover_image_id=None, category_id=None, series_id=None,
        series_order=None, tag_ids=None, meta_title=None,
        meta_description=None, canonical_url=None, robots=None,
    )
    await db_session.flush()

    found = await public.lookup_slug_history(
        db_session, entity_type=SlugEntityType.post, old_slug="renamed",
    )
    assert found == "final-slug"
    miss = await public.lookup_slug_history(
        db_session, entity_type=SlugEntityType.post, old_slug="never-existed",
    )
    assert miss is None
    await db_session.rollback()


async def test_get_published_by_slug_404_for_draft(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    draft = await posts_service.create_post(
        db_session, actor=actor, title="Hidden", excerpt=None
    )
    with pytest.raises(NotFoundError):
        await public.get_published_by_slug(db_session, draft.slug)
    await db_session.rollback()


async def test_series_prev_next_orders_correctly(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.admin)
    series = await taxonomy.create_series(
        db_session, actor=actor, title="S", description=None
    )
    p1 = await posts_service.create_post(db_session, actor=actor, title="One", excerpt=None)
    p2 = await posts_service.create_post(db_session, actor=actor, title="Two", excerpt=None)
    p3 = await posts_service.create_post(db_session, actor=actor, title="Three", excerpt=None)
    for i, p in enumerate([p1, p2, p3], start=1):
        await posts_service.update_post_metadata(
            db_session, actor=actor, post=p, slug=None,
            cover_image_id=None, category_id=None,
            series_id=series.id, series_order=i,
            tag_ids=None, meta_title=None,
            meta_description=None, canonical_url=None, robots=None,
        )
        await posts_service.publish(db_session, actor=actor, post=p)
    await db_session.flush()

    prev, nxt = await public.series_prev_next(db_session, post=p2)
    assert prev is not None and prev.id == p1.id
    assert nxt is not None and nxt.id == p3.id

    prev, nxt = await public.series_prev_next(db_session, post=p1)
    assert prev is None and nxt is not None and nxt.id == p2.id

    prev, nxt = await public.series_prev_next(db_session, post=p3)
    assert prev is not None and prev.id == p2.id and nxt is None
    await db_session.rollback()
