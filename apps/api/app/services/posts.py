"""Post lifecycle: create, save, autosave, state transitions, list."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.core.sanitize import clean_html
from app.core.slug import make_slug, unique_slug
from app.infra.db.models.content import Post, PostRevision, PostStatus, PostTag, Tag
from app.infra.db.models.users import User, UserRole
from app.services import audit

AUTOSAVE_COALESCE_WINDOW = timedelta(minutes=5)

# Storage shape for `content_json` going forward: a JSON envelope holding the
# editor's HTML output. Kept inside `content_json` so the column schema is
# stable across the TipTap → CKEditor migration.
_CONTENT_JSON_FORMAT = "html"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _empty_doc() -> dict[str, Any]:
    return {"format": _CONTENT_JSON_FORMAT, "html": ""}


def _envelope(html: str) -> dict[str, Any]:
    return {"format": _CONTENT_JSON_FORMAT, "html": html}


def _reading_minutes(html: str) -> int:
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", html)).strip()
    words = len(text.split())
    return max(1, round(words / 220))


def _extract_html(envelope_or_doc: dict[str, Any]) -> str:
    """Read HTML from the new envelope; pre-CKEditor revisions return empty."""
    if envelope_or_doc.get("format") == _CONTENT_JSON_FORMAT:
        html = envelope_or_doc.get("html")
        return html if isinstance(html, str) else ""
    return ""


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------


async def slug_available(
    db: AsyncSession, *, slug: str, exclude_post_id: UUID | None = None
) -> bool:
    stmt = select(Post.id).where(Post.slug == slug)
    if exclude_post_id is not None:
        stmt = stmt.where(Post.id != exclude_post_id)
    return (await db.execute(stmt)).first() is None


# ---------------------------------------------------------------------------
# Create / read / list
# ---------------------------------------------------------------------------


async def create_post(
    db: AsyncSession,
    *,
    actor: User,
    title: str,
    excerpt: str | None,
) -> Post:
    base = make_slug(title)
    slug = await unique_slug(db, base=base, model=Post)
    doc = _empty_doc()
    post = Post(
        slug=slug,
        title=title,
        excerpt=excerpt,
        content_json=doc,
        content_html="",
        author_id=actor.id,
        status=PostStatus.draft,
        reading_time_minutes=1,
    )
    db.add(post)
    await db.flush()
    await audit.write(
        db,
        actor_id=actor.id,
        action="post.created",
        resource_type="post",
        resource_id=str(post.id),
    )
    return post


async def get_post(db: AsyncSession, post_id: UUID) -> Post:
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise NotFoundError("Post not found.")
    return post


async def list_posts(
    db: AsyncSession,
    *,
    actor: User,
    status_filter: PostStatus | None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Post], int]:
    stmt = select(Post)
    count_stmt = select(func.count()).select_from(Post)

    if actor.role is UserRole.editor:
        stmt = stmt.where(Post.author_id == actor.id)
        count_stmt = count_stmt.where(Post.author_id == actor.id)
    if status_filter is not None:
        stmt = stmt.where(Post.status == status_filter)
        count_stmt = count_stmt.where(Post.status == status_filter)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Post.title.ilike(like), Post.slug.ilike(like)))
        count_stmt = count_stmt.where(or_(Post.title.ilike(like), Post.slug.ilike(like)))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(desc(Post.updated_at)).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total


# ---------------------------------------------------------------------------
# Save / autosave (coalesces autosave revisions within 5 min)
# ---------------------------------------------------------------------------


async def _record_revision(
    db: AsyncSession,
    *,
    post: Post,
    title: str,
    content_json: dict[str, Any],
    actor: User,
    autosave: bool,
) -> PostRevision:
    cutoff = _now() - AUTOSAVE_COALESCE_WINDOW

    if autosave:
        latest = (
            await db.execute(
                select(PostRevision)
                .where(
                    PostRevision.post_id == post.id,
                    PostRevision.is_autosave.is_(True),
                    PostRevision.created_by == actor.id,
                    PostRevision.created_at >= cutoff,
                )
                .order_by(desc(PostRevision.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest is not None:
            latest.title = title
            latest.content_json = content_json
            return latest

    rev = PostRevision(
        post_id=post.id,
        title=title,
        content_json=content_json,
        created_by=actor.id,
        is_autosave=autosave,
    )
    db.add(rev)
    await db.flush()
    return rev


async def update_post_content(
    db: AsyncSession,
    *,
    actor: User,
    post: Post,
    title: str,
    excerpt: str | None,
    content_html: str,
    autosave: bool,
) -> Post:
    # nh3 is the only safety boundary; whatever HTML the editor produces gets
    # filtered against the allowlist in app.core.sanitize before persisting.
    sanitised = clean_html(content_html or "")
    post.title = title
    post.excerpt = excerpt
    post.content_html = sanitised
    post.content_json = _envelope(sanitised)
    post.reading_time_minutes = _reading_minutes(sanitised)
    await _record_revision(
        db,
        post=post,
        title=title,
        content_json=post.content_json,
        actor=actor,
        autosave=autosave,
    )
    await audit.write(
        db,
        actor_id=actor.id,
        action="post.autosaved" if autosave else "post.saved",
        resource_type="post",
        resource_id=str(post.id),
    )
    # `updated_at` is server-generated (onupdate) and `search_vector` is set by
    # a BEFORE-UPDATE trigger — both expire after flush. Refresh so callers can
    # read them without triggering implicit IO from sync attribute access.
    await db.flush()
    await db.refresh(post)
    return post


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


async def update_post_metadata(
    db: AsyncSession,
    *,
    actor: User,
    post: Post,
    slug: str | None,
    cover_image_id: UUID | None,
    category_id: UUID | None,
    series_id: UUID | None,
    series_order: int | None,
    tag_ids: list[UUID] | None,
    meta_title: str | None,
    meta_description: str | None,
    canonical_url: str | None,
    robots: str | None,
) -> Post:
    if slug is not None and slug != post.slug:
        if not await slug_available(db, slug=slug, exclude_post_id=post.id):
            raise ConflictError("Slug already in use.")
        post.slug = slug

    if cover_image_id is not None:
        post.cover_image_id = cover_image_id
    post.category_id = category_id

    if series_id is None:
        post.series_id = None
        post.series_order = None
    else:
        if series_order is None:
            raise DomainError("series_order is required when series_id is set.")
        post.series_id = series_id
        post.series_order = series_order

    if tag_ids is not None:
        await _replace_tags(db, post=post, tag_ids=tag_ids)

    post.meta_title = meta_title
    post.meta_description = meta_description
    post.canonical_url = canonical_url
    post.robots = robots

    await audit.write(
        db,
        actor_id=actor.id,
        action="post.metadata_updated",
        resource_type="post",
        resource_id=str(post.id),
    )
    await db.flush()
    await db.refresh(post)
    return post


async def _replace_tags(
    db: AsyncSession, *, post: Post, tag_ids: list[UUID]
) -> None:
    # Validate every tag exists before mutating.
    found = (
        await db.execute(select(Tag.id).where(Tag.id.in_(tag_ids) if tag_ids else False))
    ).scalars().all()
    if set(found) != set(tag_ids):
        raise DomainError("Unknown tag id.")

    from sqlalchemy import delete as sql_delete

    await db.execute(sql_delete(PostTag).where(PostTag.post_id == post.id))
    for tid in tag_ids:
        db.add(PostTag(post_id=post.id, tag_id=tid))


# ---------------------------------------------------------------------------
# State transitions — explicit endpoints
# ---------------------------------------------------------------------------


async def publish(db: AsyncSession, *, actor: User, post: Post) -> Post:
    post.status = PostStatus.published
    post.published_at = _now()
    await audit.write(
        db,
        actor_id=actor.id,
        action="post.published",
        resource_type="post",
        resource_id=str(post.id),
    )
    await db.flush()
    await db.refresh(post)
    return post


async def unpublish(db: AsyncSession, *, actor: User, post: Post) -> Post:
    post.status = PostStatus.draft
    post.published_at = None
    await audit.write(
        db,
        actor_id=actor.id,
        action="post.unpublished",
        resource_type="post",
        resource_id=str(post.id),
    )
    await db.flush()
    await db.refresh(post)
    return post


async def archive(db: AsyncSession, *, actor: User, post: Post) -> Post:
    post.status = PostStatus.archived
    await audit.write(
        db,
        actor_id=actor.id,
        action="post.archived",
        resource_type="post",
        resource_id=str(post.id),
    )
    await db.flush()
    await db.refresh(post)
    return post


async def delete_post(db: AsyncSession, *, actor: User, post: Post) -> None:
    post_id = post.id
    await db.delete(post)
    await audit.write(
        db,
        actor_id=actor.id,
        action="post.deleted",
        resource_type="post",
        resource_id=str(post_id),
    )


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


async def list_revisions(
    db: AsyncSession, *, post_id: UUID, limit: int = 50
) -> list[PostRevision]:
    rows = (
        await db.execute(
            select(PostRevision)
            .where(PostRevision.post_id == post_id)
            .order_by(desc(PostRevision.created_at))
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def restore_revision(
    db: AsyncSession, *, actor: User, post: Post, revision_id: UUID
) -> Post:
    rev = (
        await db.execute(
            select(PostRevision).where(
                PostRevision.id == revision_id, PostRevision.post_id == post.id
            )
        )
    ).scalar_one_or_none()
    if rev is None:
        raise NotFoundError("Revision not found.")
    # Revisions store the HTML envelope; old TipTap-era revisions store the
    # full JSON doc — for those we fall back to whatever content_html the post
    # already has, since the renderer is gone.
    rev_html = _extract_html(rev.content_json) if isinstance(rev.content_json, dict) else ""
    if not rev_html:
        rev_html = post.content_html
    sanitised = clean_html(rev_html)
    post.title = rev.title
    post.content_html = sanitised
    post.content_json = _envelope(sanitised)
    post.reading_time_minutes = _reading_minutes(sanitised)
    # Record the restore itself as a non-autosave revision so it shows in history.
    await _record_revision(
        db,
        post=post,
        title=rev.title,
        content_json=post.content_json,
        actor=actor,
        autosave=False,
    )
    await audit.write(
        db,
        actor_id=actor.id,
        action="post.revision_restored",
        resource_type="post",
        resource_id=str(post.id),
        metadata={"revision_id": str(rev.id)},
    )
    return post
