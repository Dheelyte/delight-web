"""Comments: submit (honeypot + min-time + heuristics), list, moderate."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.core.errors import DomainError, NotFoundError
from app.infra.db.models.auth import AuthAttemptKind
from app.infra.db.models.content import Post, PostStatus
from app.infra.db.models.engagement import Comment, CommentStatus
from app.infra.db.models.users import User
from app.services import audit, throttle

# Spam knobs.
MAX_URLS_IN_BODY = 3
DUPE_WINDOW = timedelta(hours=24)
MIN_FORM_FILL_SECONDS = 2

_URL_RE = re.compile(r"https?://", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _hash(value: str) -> str:
    """Salted SHA-256 (secret key as salt) - keeps PII out of the DB."""
    salt = get_settings().SECRET_KEY
    return hashlib.sha256(f"{salt}|{value}".encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


async def submit(
    db: AsyncSession,
    *,
    post_slug: str,
    author_name: str,
    author_email: str,
    content: str,
    parent_id: UUID | None,
    ip: str | None,
    user_agent: str | None,
    honeypot: str | None,
    form_fill_seconds: float | None,
) -> Comment:
    if honeypot:
        # Bot tripped the honeypot. Look successful from the outside.
        raise DomainError("Comment rejected.")
    if form_fill_seconds is not None and form_fill_seconds < MIN_FORM_FILL_SECONDS:
        raise DomainError("Comment rejected.")

    body = content.strip()
    if not body:
        raise DomainError("Comment is empty.")
    if len(body) > 5000:
        raise DomainError("Comment is too long.")

    identifier = ip or _hash(author_email.lower())
    await throttle.check_allowed(
        db, identifier=identifier, kind=AuthAttemptKind.comment
    )

    post = (
        await db.execute(
            select(Post).where(
                Post.slug == post_slug, Post.status == PostStatus.published
            )
        )
    ).scalar_one_or_none()
    if post is None:
        raise NotFoundError("Post not found.")

    if parent_id is not None:
        parent = (
            await db.execute(
                select(Comment).where(
                    Comment.id == parent_id, Comment.post_id == post.id
                )
            )
        ).scalar_one_or_none()
        if parent is None:
            raise DomainError("Parent comment not found.")
        # Threading is one level deep per spec.
        if parent.parent_id is not None:
            raise DomainError("Replies cannot be nested further.")

    # Spam heuristics - flagged as `spam`, not rejected outright, so the admin
    # can rescue false positives from the queue.
    is_spam = _looks_like_spam(body=body, ip=ip)
    if not is_spam:
        is_spam = await _is_duplicate(db, ip=ip, body=body)

    comment = Comment(
        post_id=post.id,
        parent_id=parent_id,
        author_name=author_name.strip()[:120],
        author_email_hash=_hash(author_email.lower()),
        content=body,
        status=CommentStatus.spam if is_spam else CommentStatus.pending,
        ip_hash=_hash(ip) if ip else _hash("anonymous"),
        user_agent=(user_agent or "")[:500] or None,
    )
    db.add(comment)
    await db.flush()
    await throttle.record_attempt(
        db, identifier=identifier, kind=AuthAttemptKind.comment, succeeded=True
    )
    return comment


def _looks_like_spam(*, body: str, ip: str | None) -> bool:
    if len(_URL_RE.findall(body)) > MAX_URLS_IN_BODY:
        return True
    if ip is None:
        # Anonymous via X-Forwarded-For absent - common with bots.
        return False
    return False


async def _is_duplicate(db: AsyncSession, *, ip: str | None, body: str) -> bool:
    if ip is None:
        return False
    ip_hash = _hash(ip)
    cutoff = _now() - DUPE_WINDOW
    exists = (
        await db.execute(
            select(Comment.id).where(
                Comment.ip_hash == ip_hash,
                Comment.created_at >= cutoff,
                Comment.content == body,
            ).limit(1)
        )
    ).scalar_one_or_none()
    return exists is not None


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def list_approved(
    db: AsyncSession, *, post_id: UUID
) -> list[Comment]:
    rows = (
        await db.execute(
            select(Comment)
            .where(
                Comment.post_id == post_id,
                Comment.status == CommentStatus.approved,
            )
            .order_by(Comment.created_at.asc())
        )
    ).scalars().all()
    return list(rows)


async def list_pending(
    db: AsyncSession, *, limit: int, offset: int
) -> tuple[list[Comment], int]:
    # `joinedload(Comment.post)` eager-loads the parent post so the router can
    # read `comment.post.title/slug` without triggering lazy IO from a sync
    # attribute access (async sessions can't lazy-load). Many-to-one join +
    # LIMIT is safe - no row multiplication.
    base = (
        select(Comment)
        .options(joinedload(Comment.post))
        .where(Comment.status.in_([CommentStatus.pending, CommentStatus.spam]))
    )
    total = (
        await db.execute(
            select(func.count())
            .select_from(Comment)
            .where(Comment.status.in_([CommentStatus.pending, CommentStatus.spam]))
        )
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(desc(Comment.created_at)).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def count_pending(db: AsyncSession) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Comment)
            .where(Comment.status == CommentStatus.pending)
        )
    ).scalar_one()


async def count_approved(db: AsyncSession, *, post_id: UUID) -> int:
    """Public comment count for a post - feeds the BlogPosting JSON-LD."""
    return (
        await db.execute(
            select(func.count())
            .select_from(Comment)
            .where(
                Comment.post_id == post_id,
                Comment.status == CommentStatus.approved,
            )
        )
    ).scalar_one()


# ---------------------------------------------------------------------------
# Moderation
# ---------------------------------------------------------------------------


async def _transition(
    db: AsyncSession,
    *,
    actor: User,
    comment_id: UUID,
    new_status: CommentStatus,
) -> Comment:
    c = (
        await db.execute(
            select(Comment)
            .options(joinedload(Comment.post))
            .where(Comment.id == comment_id)
        )
    ).scalar_one_or_none()
    if c is None:
        raise NotFoundError("Comment not found.")
    c.status = new_status
    await audit.write(
        db,
        actor_id=actor.id,
        action=f"comment.{new_status.value}",
        resource_type="comment",
        resource_id=str(c.id),
    )
    return c


async def approve(db: AsyncSession, *, actor: User, comment_id: UUID) -> Comment:
    return await _transition(db, actor=actor, comment_id=comment_id, new_status=CommentStatus.approved)


async def mark_spam(db: AsyncSession, *, actor: User, comment_id: UUID) -> Comment:
    return await _transition(db, actor=actor, comment_id=comment_id, new_status=CommentStatus.spam)


async def delete(db: AsyncSession, *, actor: User, comment_id: UUID) -> Comment:
    return await _transition(db, actor=actor, comment_id=comment_id, new_status=CommentStatus.deleted)
