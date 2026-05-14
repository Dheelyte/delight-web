"""Engagement routers: comments, subscribers, analytics.

Public surface lives under /public/. Admin moderation is gated by `require_editor_or_admin`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    client_ip,
    current_user,
    get_db,
    require_editor_or_admin,
    user_agent,
)
from app.core.errors import NotFoundError
from app.infra.db.models.content import Post, PostStatus
from app.infra.db.models.users import User
from app.schemas.engagement import (
    AnalyticsWindowOut,
    BroadcastIn,
    BroadcastOut,
    CommentAdminOut,
    CommentListOut,
    CommentPublicOut,
    CommentSubmitIn,
    ModerationCountOut,
    ReferrerOut,
    SubscribeIn,
    SubscriberAdminOut,
    SubscriberCountOut,
    SubscriberListOut,
    TopPostOut,
    TrackViewIn,
    UnsubscribeIn,
)
from app.services import analytics, comments, subscribers

public_router = APIRouter(prefix="/public", tags=["public"])
admin_router = APIRouter(tags=["admin"])


# ---------------------------------------------------------------------------
# Comments - public submit + list
# ---------------------------------------------------------------------------


@public_router.post(
    "/comments", response_model=CommentPublicOut, status_code=status.HTTP_201_CREATED
)
async def submit_comment(
    body: CommentSubmitIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CommentPublicOut:
    c = await comments.submit(
        db,
        post_slug=body.post_slug,
        author_name=body.author_name,
        author_email=body.author_email,
        content=body.content,
        parent_id=body.parent_id,
        ip=client_ip(request),
        user_agent=user_agent(request),
        honeypot=body.honeypot,
        form_fill_seconds=body.form_fill_seconds,
    )
    return CommentPublicOut(
        id=c.id, parent_id=c.parent_id, author_name=c.author_name,
        content=c.content, created_at=c.created_at,
    )


@public_router.get(
    "/posts/{slug}/comments", response_model=list[CommentPublicOut]
)
async def list_post_comments(
    slug: str, db: AsyncSession = Depends(get_db)
) -> list[CommentPublicOut]:
    post = (
        await db.execute(
            select(Post).where(Post.slug == slug, Post.status == PostStatus.published)
        )
    ).scalar_one_or_none()
    if post is None:
        raise NotFoundError("Post not found.")
    rows = await comments.list_approved(db, post_id=post.id)
    return [
        CommentPublicOut(
            id=c.id, parent_id=c.parent_id, author_name=c.author_name,
            content=c.content, created_at=c.created_at,
        )
        for c in rows
    ]


# ---------------------------------------------------------------------------
# Comments - admin
# ---------------------------------------------------------------------------


@admin_router.get("/comments", response_model=CommentListOut)
async def admin_list_comments(
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CommentListOut:
    rows, total = await comments.list_pending(db, limit=limit, offset=offset)
    return CommentListOut(
        items=[_admin_comment(c) for c in rows],
        total=total, limit=limit, offset=offset,
    )


@admin_router.get("/comments/count", response_model=ModerationCountOut)
async def admin_pending_count(
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> ModerationCountOut:
    return ModerationCountOut(pending=await comments.count_pending(db))


@admin_router.post("/comments/{comment_id}/approve", response_model=CommentAdminOut)
async def admin_approve(
    comment_id: UUID,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> CommentAdminOut:
    c = await comments.approve(db, actor=actor, comment_id=comment_id)
    return _admin_comment(c)


@admin_router.post("/comments/{comment_id}/spam", response_model=CommentAdminOut)
async def admin_spam(
    comment_id: UUID,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> CommentAdminOut:
    c = await comments.mark_spam(db, actor=actor, comment_id=comment_id)
    return _admin_comment(c)


@admin_router.delete("/comments/{comment_id}", response_model=CommentAdminOut)
async def admin_delete(
    comment_id: UUID,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> CommentAdminOut:
    c = await comments.delete(db, actor=actor, comment_id=comment_id)
    return _admin_comment(c)


def _admin_comment(c) -> CommentAdminOut:  # type: ignore[no-untyped-def]
    # `c.post` is eager-loaded by comments.list_pending / _transition.
    return CommentAdminOut(
        id=c.id, parent_id=c.parent_id, author_name=c.author_name,
        content=c.content, created_at=c.created_at,
        post_id=c.post_id, post_title=c.post.title, post_slug=c.post.slug,
        status=c.status,
    )


# ---------------------------------------------------------------------------
# Subscribers - public
# ---------------------------------------------------------------------------


@public_router.post("/subscribers", status_code=status.HTTP_204_NO_CONTENT)
async def public_subscribe(
    body: SubscribeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Per spec, we always return 204 so subscription status doesn't leak.
    try:
        await subscribers.subscribe(db, email=body.email, ip=client_ip(request))
    except Exception:
        pass  # fail-quiet; the user receives no signal either way
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.post("/subscribers/unsubscribe", response_model=SubscriberAdminOut)
async def public_unsubscribe(
    body: UnsubscribeIn, db: AsyncSession = Depends(get_db)
) -> SubscriberAdminOut:
    sub = await subscribers.unsubscribe(db, token=body.token)
    return SubscriberAdminOut(
        id=sub.id, email=sub.email, status=sub.status,
        confirmed_at=sub.confirmed_at, created_at=sub.created_at,
    )


# ---------------------------------------------------------------------------
# Subscribers - admin
# ---------------------------------------------------------------------------


@admin_router.get("/subscribers", response_model=SubscriberListOut)
async def admin_list_subscribers(
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
    status_filter: str = Query(default="all", alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SubscriberListOut:
    rows, total = await subscribers.list_all(
        db,
        status_filter=status_filter,  # type: ignore[arg-type]
        limit=limit, offset=offset,
    )
    return SubscriberListOut(
        items=[
            SubscriberAdminOut(
                id=s.id, email=s.email, status=s.status,
                confirmed_at=s.confirmed_at, created_at=s.created_at,
            )
            for s in rows
        ],
        total=total, limit=limit, offset=offset,
    )


@admin_router.get("/subscribers/count", response_model=SubscriberCountOut)
async def admin_subscriber_count(
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> SubscriberCountOut:
    return SubscriberCountOut(confirmed=await subscribers.count_confirmed(db))


@admin_router.post("/subscribers/broadcast", response_model=BroadcastOut)
async def admin_broadcast(
    body: BroadcastIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> BroadcastOut:
    import os

    base = os.environ.get("WEB_BASE_URL", "http://localhost:3000")
    n = await subscribers.send_to_confirmed(
        db, actor_id=actor.id, post_slug=body.post_slug, base_url=base
    )
    return BroadcastOut(recipients=n)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@public_router.post("/views", status_code=status.HTTP_204_NO_CONTENT)
async def public_track_view(
    body: TrackViewIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await analytics.record_view(
        db,
        post_slug=body.post_slug,
        ip=client_ip(request),
        user_agent=user_agent(request),
        referrer=body.referrer,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/analytics", response_model=AnalyticsWindowOut)
async def admin_analytics(
    window: int = Query(default=30),
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsWindowOut:
    if window not in (7, 30, 90):
        from app.core.errors import DomainError

        raise DomainError("window must be 7, 30, or 90.")
    top = await analytics.top_posts(db, window=window)  # type: ignore[arg-type]
    refs = await analytics.top_referrers(db, window=window)  # type: ignore[arg-type]
    return AnalyticsWindowOut(
        window=window,  # type: ignore[arg-type]
        top_posts=[
            TopPostOut(slug=p.slug, title=p.title, views=v) for p, v in top
        ],
        top_referrers=[ReferrerOut(host=h, views=v) for h, v in refs],
    )
