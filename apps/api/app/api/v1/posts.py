"""Posts router. State transitions are explicit endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    client_ip,
    current_user,
    get_db,
    require_editor_or_admin,
    require_post_ownership,
    user_agent,
)
from app.infra.db.models.content import Post, PostStatus, PostTag
from app.infra.db.models.users import User
from app.schemas.posts import (
    PostContentIn,
    PostCreateIn,
    PostDetailOut,
    PostListOut,
    PostMetadataIn,
    PostSummaryOut,
    RevisionOut,
    SlugCheckOut,
)
from app.services import posts as posts_service

router = APIRouter(prefix="/posts", tags=["posts"])


async def _tag_ids_for_post(db: AsyncSession, post_id: UUID) -> list[UUID]:
    rows = (
        await db.execute(select(PostTag.tag_id).where(PostTag.post_id == post_id))
    ).scalars().all()
    return list(rows)


async def _detail_out(db: AsyncSession, post: Post) -> PostDetailOut:
    return PostDetailOut(
        id=post.id,
        slug=post.slug,
        title=post.title,
        excerpt=post.excerpt,
        status=post.status,
        author_id=post.author_id,
        published_at=post.published_at,
        scheduled_for=post.scheduled_for,
        updated_at=post.updated_at,
        reading_time_minutes=post.reading_time_minutes,
        content_html=post.content_html,
        cover_image_id=post.cover_image_id,
        category_id=post.category_id,
        series_id=post.series_id,
        series_order=post.series_order,
        meta_title=post.meta_title,
        meta_description=post.meta_description,
        canonical_url=post.canonical_url,
        robots=post.robots,
        tag_ids=await _tag_ids_for_post(db, post.id),
    )


def _summary_out(post: Post) -> PostSummaryOut:
    return PostSummaryOut(
        id=post.id,
        slug=post.slug,
        title=post.title,
        excerpt=post.excerpt,
        status=post.status,
        author_id=post.author_id,
        published_at=post.published_at,
        scheduled_for=post.scheduled_for,
        updated_at=post.updated_at,
        reading_time_minutes=post.reading_time_minutes,
    )


# ---------------------------------------------------------------------------


@router.get("", response_model=PostListOut)
async def list_posts(
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
    status_filter: PostStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PostListOut:
    rows, total = await posts_service.list_posts(
        db, actor=actor, status_filter=status_filter, q=q, limit=limit, offset=offset
    )
    return PostListOut(
        items=[_summary_out(p) for p in rows], total=total, limit=limit, offset=offset
    )


@router.post("", response_model=PostDetailOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: PostCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    post = await posts_service.create_post(
        db, actor=actor, title=body.title, excerpt=body.excerpt
    )
    return await _detail_out(db, post)


@router.get("/check-slug", response_model=SlugCheckOut)
async def check_slug(
    slug: str = Query(min_length=1, max_length=80),
    exclude_post_id: UUID | None = Query(default=None),
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> SlugCheckOut:
    available = await posts_service.slug_available(
        db, slug=slug, exclude_post_id=exclude_post_id
    )
    return SlugCheckOut(slug=slug, available=available)


@router.get("/{post_id}", response_model=PostDetailOut)
async def get_post(
    post: Post = Depends(require_post_ownership),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    return await _detail_out(db, post)


@router.put("/{post_id}/content", response_model=PostDetailOut)
async def update_content(
    body: PostContentIn,
    post: Post = Depends(require_post_ownership),
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    await posts_service.update_post_content(
        db,
        actor=actor,
        post=post,
        title=body.title,
        excerpt=body.excerpt,
        content_html=body.content_html,
        autosave=body.autosave,
    )
    return await _detail_out(db, post)


@router.put("/{post_id}/metadata", response_model=PostDetailOut)
async def update_metadata(
    body: PostMetadataIn,
    post: Post = Depends(require_post_ownership),
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    await posts_service.update_post_metadata(
        db,
        actor=actor,
        post=post,
        slug=body.slug,
        cover_image_id=body.cover_image_id,
        category_id=body.category_id,
        series_id=body.series_id,
        series_order=body.series_order,
        tag_ids=body.tag_ids,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        canonical_url=body.canonical_url,
        robots=body.robots,
    )
    return await _detail_out(db, post)


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


@router.post("/{post_id}/publish", response_model=PostDetailOut)
async def publish_post(
    post: Post = Depends(require_post_ownership),
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    await posts_service.publish(db, actor=actor, post=post)
    return await _detail_out(db, post)


@router.post("/{post_id}/unpublish", response_model=PostDetailOut)
async def unpublish_post(
    post: Post = Depends(require_post_ownership),
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    await posts_service.unpublish(db, actor=actor, post=post)
    return await _detail_out(db, post)


@router.post("/{post_id}/archive", response_model=PostDetailOut)
async def archive_post(
    post: Post = Depends(require_post_ownership),
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    await posts_service.archive(db, actor=actor, post=post)
    return await _detail_out(db, post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post: Post = Depends(require_post_ownership),
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await posts_service.delete_post(db, actor=actor, post=post)


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


@router.get("/{post_id}/revisions", response_model=list[RevisionOut])
async def list_revisions(
    post: Post = Depends(require_post_ownership),
    db: AsyncSession = Depends(get_db),
) -> list[RevisionOut]:
    rows = await posts_service.list_revisions(db, post_id=post.id)
    return [
        RevisionOut(
            id=r.id,
            title=r.title,
            is_autosave=r.is_autosave,
            created_at=r.created_at,
            created_by=r.created_by,
        )
        for r in rows
    ]


@router.post("/{post_id}/revisions/{revision_id}/restore", response_model=PostDetailOut)
async def restore_revision(
    revision_id: UUID,
    post: Post = Depends(require_post_ownership),
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetailOut:
    await posts_service.restore_revision(
        db, actor=actor, post=post, revision_id=revision_id
    )
    return await _detail_out(db, post)
