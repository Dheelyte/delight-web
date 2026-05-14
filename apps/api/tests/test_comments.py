"""Comments: honeypot, min-time, link-spam, dupe, threading, moderation."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.infra.db.models.engagement import Comment, CommentStatus
from app.infra.db.models.users import UserRole
from app.services import comments, posts as posts_service
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def _published_post(db, actor, *, slug=None, title="T"):
    p = await posts_service.create_post(db, actor=actor, title=title, excerpt=None)
    if slug:
        p.slug = slug
    await posts_service.publish(db, actor=actor, post=p)
    await db.flush()
    return p


async def test_submit_creates_pending_comment(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published_post(db_session, admin)
    c = await comments.submit(
        db_session,
        post_slug=post.slug, author_name="Alice", author_email="a@b.co",
        content="A real comment.", parent_id=None,
        ip="1.2.3.4", user_agent="Mozilla/5.0",
        honeypot=None, form_fill_seconds=10.0,
    )
    assert c.status is CommentStatus.pending
    await db_session.rollback()


async def test_honeypot_trips(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published_post(db_session, admin)
    with pytest.raises(DomainError):
        await comments.submit(
            db_session, post_slug=post.slug, author_name="bot",
            author_email="b@c.d", content="x", parent_id=None,
            ip=None, user_agent="Mozilla/5.0",
            honeypot="oops", form_fill_seconds=10.0,
        )
    await db_session.rollback()


async def test_min_time_kicks_out_fast_submit(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published_post(db_session, admin)
    with pytest.raises(DomainError):
        await comments.submit(
            db_session, post_slug=post.slug, author_name="fast",
            author_email="b@c.d", content="x", parent_id=None,
            ip=None, user_agent="Mozilla/5.0",
            honeypot=None, form_fill_seconds=0.5,
        )
    await db_session.rollback()


async def test_too_many_urls_marked_spam(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published_post(db_session, admin)
    body = "Check http://a.com http://b.com http://c.com http://d.com"
    c = await comments.submit(
        db_session, post_slug=post.slug, author_name="A",
        author_email="a@b.co", content=body, parent_id=None,
        ip="1.2.3.4", user_agent="Mozilla/5.0",
        honeypot=None, form_fill_seconds=10.0,
    )
    assert c.status is CommentStatus.spam
    await db_session.rollback()


async def test_duplicate_within_window_marked_spam(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published_post(db_session, admin)
    args = dict(
        post_slug=post.slug, author_name="A", author_email="a@b.co",
        content="Same content from same IP.", parent_id=None,
        ip="9.9.9.9", user_agent="Mozilla/5.0",
        honeypot=None, form_fill_seconds=10.0,
    )
    first = await comments.submit(db_session, **args)
    second = await comments.submit(db_session, **args)
    assert first.status is CommentStatus.pending
    assert second.status is CommentStatus.spam
    await db_session.rollback()


async def test_thread_depth_capped_at_one(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published_post(db_session, admin)

    parent = await comments.submit(
        db_session, post_slug=post.slug, author_name="A",
        author_email="a@b.co", content="top", parent_id=None,
        ip="1.1.1.1", user_agent="Mozilla/5.0",
        honeypot=None, form_fill_seconds=10.0,
    )
    reply = await comments.submit(
        db_session, post_slug=post.slug, author_name="B",
        author_email="b@b.co", content="reply", parent_id=parent.id,
        ip="2.2.2.2", user_agent="Mozilla/5.0",
        honeypot=None, form_fill_seconds=10.0,
    )
    with pytest.raises(DomainError):
        await comments.submit(
            db_session, post_slug=post.slug, author_name="C",
            author_email="c@b.co", content="reply-to-reply", parent_id=reply.id,
            ip="3.3.3.3", user_agent="Mozilla/5.0",
            honeypot=None, form_fill_seconds=10.0,
        )
    await db_session.rollback()


async def test_moderation_transitions_and_list_approved(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    post = await _published_post(db_session, admin)
    c = await comments.submit(
        db_session, post_slug=post.slug, author_name="A",
        author_email="a@b.co", content="text", parent_id=None,
        ip="1.1.1.1", user_agent="Mozilla/5.0",
        honeypot=None, form_fill_seconds=10.0,
    )
    assert (await comments.list_approved(db_session, post_id=post.id)) == []

    await comments.approve(db_session, actor=admin, comment_id=c.id)
    approved = await comments.list_approved(db_session, post_id=post.id)
    assert len(approved) == 1

    await comments.mark_spam(db_session, actor=admin, comment_id=c.id)
    assert (await comments.list_approved(db_session, post_id=post.id)) == []

    await comments.delete(db_session, actor=admin, comment_id=c.id)
    row = (
        await db_session.execute(select(Comment).where(Comment.id == c.id))
    ).scalar_one()
    assert row.status is CommentStatus.deleted
    await db_session.rollback()


async def test_submit_to_unknown_post_404s(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await comments.submit(
            db_session, post_slug="does-not-exist", author_name="A",
            author_email="a@b.co", content="x", parent_id=None,
            ip="1.1.1.1", user_agent="Mozilla/5.0",
            honeypot=None, form_fill_seconds=10.0,
        )
    await db_session.rollback()
