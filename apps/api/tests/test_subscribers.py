"""Newsletter: single-step confirm, idempotent re-subscribe, unsubscribe, broadcast outbox."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.infra.db.models.engagement import SubscriberStatus
from app.infra.db.models.system import Outbox
from app.infra.db.models.users import UserRole
from app.services import posts as posts_service, subscribers
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def test_subscribe_creates_confirmed_row(db_session: AsyncSession) -> None:
    sub = await subscribers.subscribe(
        db_session, email="reader@example.com", ip="1.1.1.1"
    )
    assert sub.status is SubscriberStatus.confirmed
    assert sub.confirmed_at is not None
    # No confirmation email is enqueued under the single-step flow.
    outbox = (
        await db_session.execute(
            select(Outbox).where(Outbox.topic == "newsletter.confirm_email")
        )
    ).scalars().all()
    assert outbox == []
    await db_session.rollback()


async def test_repeat_subscribe_idempotent(db_session: AsyncSession) -> None:
    a = await subscribers.subscribe(db_session, email="x@example.com", ip=None)
    b = await subscribers.subscribe(db_session, email="x@example.com", ip=None)
    assert a.id == b.id
    assert b.status is SubscriberStatus.confirmed
    await db_session.rollback()


async def test_unsubscribe_then_resubscribe(db_session: AsyncSession) -> None:
    sub = await subscribers.subscribe(
        db_session, email="back@example.com", ip=None
    )
    unsub_url = subscribers.unsubscribe_url(sub.id, base_url="https://x.test")
    token = unsub_url.split("token=", 1)[1]
    out = await subscribers.unsubscribe(db_session, token=token)
    assert out.status is SubscriberStatus.unsubscribed

    again = await subscribers.subscribe(
        db_session, email="back@example.com", ip=None
    )
    assert again.id == sub.id
    assert again.status is SubscriberStatus.confirmed
    await db_session.rollback()


async def test_unsubscribe_tampered_token_rejected(db_session: AsyncSession) -> None:
    sub = await subscribers.subscribe(db_session, email="t@example.com", ip=None)
    unsub_url = subscribers.unsubscribe_url(sub.id, base_url="https://x.test")
    token = unsub_url.split("token=", 1)[1]
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(DomainError):
        await subscribers.unsubscribe(db_session, token=tampered)
    await db_session.rollback()


async def test_broadcast_enqueues_one_per_confirmed(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    for i in range(3):
        await subscribers.subscribe(db_session, email=f"a{i}@example.com", ip=None)

    # Force one into the unsubscribed state to prove it's excluded.
    sub = await subscribers.subscribe(db_session, email="opt-out@example.com", ip=None)
    unsub_url = subscribers.unsubscribe_url(sub.id, base_url="https://x.test")
    await subscribers.unsubscribe(
        db_session, token=unsub_url.split("token=", 1)[1]
    )

    post = await posts_service.create_post(
        db_session, actor=admin, title="Hello", excerpt=None
    )
    await posts_service.publish(db_session, actor=admin, post=post)

    n = await subscribers.send_to_confirmed(
        db_session, actor_id=admin.id, post_slug=post.slug, base_url="https://x.test",
    )
    assert n == 3
    sends = (
        await db_session.execute(
            select(Outbox).where(Outbox.topic == "newsletter.send_post")
        )
    ).scalars().all()
    assert len(sends) == 3
    for o in sends:
        assert "unsubscribe_url" in o.payload_json
        assert o.payload_json["post_slug"] == post.slug
    await db_session.rollback()
