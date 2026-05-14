"""Read-only services for the public site: feed, post detail, taxonomy, search."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.infra.db.models.content import (
    Category,
    Post,
    PostStatus,
    PostTag,
    Series,
    Tag,
)
from app.infra.db.models.system import SlugEntityType, SlugHistory
from app.infra.db.models.users import User


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _published_filter():
    """Reusable predicate: only published, non-future posts."""
    return (Post.status == PostStatus.published) & (Post.published_at <= _now())


async def list_published(
    db: AsyncSession, *, limit: int, offset: int
) -> tuple[list[Post], int]:
    base = select(Post).where(_published_filter())
    total = (
        await db.execute(select(func.count()).select_from(Post).where(_published_filter()))
    ).scalar_one()
    rows = (
        await db.execute(base.order_by(desc(Post.published_at)).limit(limit).offset(offset))
    ).scalars().all()
    return list(rows), total


async def get_published_by_slug(db: AsyncSession, slug: str) -> Post:
    post = (
        await db.execute(select(Post).where(Post.slug == slug, _published_filter()))
    ).scalar_one_or_none()
    if post is None:
        raise NotFoundError("Post not found.")
    return post


async def get_author(db: AsyncSession, user_id: UUID) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise NotFoundError("Author not found.")
    return user


async def tags_for_post(db: AsyncSession, post_id: UUID) -> list[Tag]:
    rows = (
        await db.execute(
            select(Tag)
            .join(PostTag, PostTag.tag_id == Tag.id)
            .where(PostTag.post_id == post_id)
            .order_by(Tag.name)
        )
    ).scalars().all()
    return list(rows)


# ---------------------------------------------------------------------------
# Taxonomy index pages
# ---------------------------------------------------------------------------


async def posts_by_tag(
    db: AsyncSession, *, tag_slug: str, limit: int, offset: int
) -> tuple[Tag, list[Post], int]:
    tag = (
        await db.execute(select(Tag).where(Tag.slug == tag_slug))
    ).scalar_one_or_none()
    if tag is None:
        raise NotFoundError("Tag not found.")
    base = (
        select(Post)
        .join(PostTag, PostTag.post_id == Post.id)
        .where(PostTag.tag_id == tag.id, _published_filter())
    )
    total = (
        await db.execute(
            select(func.count())
            .select_from(Post)
            .join(PostTag, PostTag.post_id == Post.id)
            .where(PostTag.tag_id == tag.id, _published_filter())
        )
    ).scalar_one()
    rows = (
        await db.execute(base.order_by(desc(Post.published_at)).limit(limit).offset(offset))
    ).scalars().all()
    return tag, list(rows), total


async def posts_by_category(
    db: AsyncSession, *, category_slug: str, limit: int, offset: int
) -> tuple[Category, list[Post], int]:
    cat = (
        await db.execute(select(Category).where(Category.slug == category_slug))
    ).scalar_one_or_none()
    if cat is None:
        raise NotFoundError("Category not found.")
    base = select(Post).where(Post.category_id == cat.id, _published_filter())
    total = (
        await db.execute(
            select(func.count())
            .select_from(Post)
            .where(Post.category_id == cat.id, _published_filter())
        )
    ).scalar_one()
    rows = (
        await db.execute(base.order_by(desc(Post.published_at)).limit(limit).offset(offset))
    ).scalars().all()
    return cat, list(rows), total


async def posts_in_series(
    db: AsyncSession, *, series_slug: str
) -> tuple[Series, list[Post]]:
    series = (
        await db.execute(select(Series).where(Series.slug == series_slug))
    ).scalar_one_or_none()
    if series is None:
        raise NotFoundError("Series not found.")
    rows = (
        await db.execute(
            select(Post)
            .where(Post.series_id == series.id, _published_filter())
            .order_by(Post.series_order.asc())
        )
    ).scalars().all()
    return series, list(rows)


async def series_prev_next(
    db: AsyncSession, *, post: Post
) -> tuple[Post | None, Post | None]:
    if post.series_id is None or post.series_order is None:
        return None, None
    prev = (
        await db.execute(
            select(Post)
            .where(
                Post.series_id == post.series_id,
                Post.series_order < post.series_order,
                _published_filter(),
            )
            .order_by(desc(Post.series_order))
            .limit(1)
        )
    ).scalar_one_or_none()
    nxt = (
        await db.execute(
            select(Post)
            .where(
                Post.series_id == post.series_id,
                Post.series_order > post.series_order,
                _published_filter(),
            )
            .order_by(Post.series_order.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return prev, nxt


# ---------------------------------------------------------------------------
# Related posts: tag-overlap score with recency tiebreaker
# ---------------------------------------------------------------------------


async def related_posts(
    db: AsyncSession, *, post: Post, limit: int = 5
) -> list[Post]:
    tag_ids_subq = (
        select(PostTag.tag_id).where(PostTag.post_id == post.id).scalar_subquery()
    )
    overlap = func.count(PostTag.tag_id).label("overlap")
    rows = (
        await db.execute(
            select(Post, overlap)
            .join(PostTag, PostTag.post_id == Post.id)
            .where(
                PostTag.tag_id.in_(tag_ids_subq),
                Post.id != post.id,
                _published_filter(),
            )
            .group_by(Post.id)
            .order_by(desc(overlap), desc(Post.published_at))
            .limit(limit)
        )
    ).all()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Full-text search via tsvector
# ---------------------------------------------------------------------------


async def search(
    db: AsyncSession, *, q: str, limit: int, offset: int
) -> tuple[list[Post], int]:
    """Return (rows, total) matching `q`.

    Strategy: prefer ranked tsvector matches; OR in an ILIKE on title/excerpt
    so partial words ("server" → "serverless") still surface — those rows
    fall to the bottom because their ts_rank is 0.
    """
    cleaned = q.strip()
    if not cleaned:
        return [], 0
    tsq = func.plainto_tsquery("english", cleaned)
    like = f"%{cleaned}%"
    match = (
        Post.search_vector.op("@@")(tsq)
        | Post.title.ilike(like)
        | Post.excerpt.ilike(like)
    )
    rank = func.ts_rank(
        func.coalesce(Post.search_vector, func.cast("", TSVECTOR)), tsq
    ).label("rank")

    total = (
        await db.execute(
            select(func.count())
            .select_from(Post)
            .where(_published_filter(), match)
        )
    ).scalar_one()

    rows = (
        await db.execute(
            select(Post, rank)
            .where(_published_filter(), match)
            .order_by(desc(rank), desc(Post.published_at))
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [r[0] for r in rows], total


# ---------------------------------------------------------------------------
# Sitemap & slug-history lookup
# ---------------------------------------------------------------------------


async def sitemap_posts(db: AsyncSession) -> list[Post]:
    rows = (
        await db.execute(
            select(Post)
            .where(_published_filter())
            .order_by(desc(Post.updated_at))
        )
    ).scalars().all()
    return list(rows)


async def lookup_slug_history(
    db: AsyncSession, *, entity_type: SlugEntityType, old_slug: str
) -> str | None:
    """Return the *current* slug for an entity whose slug used to be `old_slug`.

    If multiple renames happened, we follow the chain to the latest new_slug
    for that entity.
    """
    row = (
        await db.execute(
            select(SlugHistory)
            .where(
                SlugHistory.entity_type == entity_type, SlugHistory.old_slug == old_slug
            )
            .order_by(desc(SlugHistory.changed_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    # Follow the chain forward — the entity may have been renamed again.
    current = row.new_slug
    while True:
        nxt = (
            await db.execute(
                select(SlugHistory)
                .where(
                    SlugHistory.entity_type == entity_type,
                    SlugHistory.entity_id == row.entity_id,
                    SlugHistory.old_slug == current,
                )
                .order_by(desc(SlugHistory.changed_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if nxt is None:
            return current
        current = nxt.new_slug


