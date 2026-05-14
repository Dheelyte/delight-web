"""Newsletter subscribers: double opt-in, signed tokens, send-via-outbox.

Tokens follow the same `sign_payload`/`verify_signed_payload` pattern as
password reset, with the payload being `<subscriber_id>:<purpose>` so a
single helper covers both confirmation and unsubscribe links.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final, Literal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.core.security import (
    generate_token,
    hash_token,
    sign_payload,
    verify_signed_payload,
)
from app.infra.db.models.engagement import Subscriber, SubscriberStatus
from app.infra.db.models.system import Outbox
from app.services import audit

UNSUBSCRIBE_MAX_AGE: Final = 365 * 24 * 60 * 60  # ~1 year - generous, link must work


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _make_purpose_token(subscriber_id: UUID, purpose: str) -> str:
    return sign_payload(f"{subscriber_id}:{purpose}")


def _decode_purpose_token(
    token: str, *, expected_purpose: str, max_age: int
) -> UUID | None:
    payload = verify_signed_payload(token, max_age_seconds=max_age)
    if payload is None:
        return None
    try:
        sub_id_str, purpose = payload.split(":", 1)
    except ValueError:
        return None
    if purpose != expected_purpose:
        return None
    try:
        return UUID(sub_id_str)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Subscribe / confirm / unsubscribe
# ---------------------------------------------------------------------------


async def subscribe(
    db: AsyncSession, *, email: str, ip: str | None
) -> Subscriber:
    """Single-step subscribe: confirm immediately, no opt-in email."""
    normalised = email.lower().strip()
    existing = (
        await db.execute(select(Subscriber).where(Subscriber.email == normalised))
    ).scalar_one_or_none()

    if existing is not None:
        if existing.status is not SubscriberStatus.confirmed:
            existing.status = SubscriberStatus.confirmed
            existing.confirmed_at = _now()
            existing.confirmation_token_hash = None
        return existing

    unsub_raw = generate_token()
    sub = Subscriber(
        email=normalised,
        status=SubscriberStatus.confirmed,
        confirmed_at=_now(),
        unsubscribe_token_hash=hash_token(unsub_raw),
        ip=ip,
    )
    db.add(sub)
    await db.flush()
    return sub


async def unsubscribe(db: AsyncSession, *, token: str) -> Subscriber:
    sub_id = _decode_purpose_token(
        token, expected_purpose="unsubscribe", max_age=UNSUBSCRIBE_MAX_AGE
    )
    if sub_id is None:
        raise DomainError("Unsubscribe link is invalid.")
    sub = (
        await db.execute(select(Subscriber).where(Subscriber.id == sub_id))
    ).scalar_one_or_none()
    if sub is None:
        raise NotFoundError("Subscriber not found.")
    sub.status = SubscriberStatus.unsubscribed
    return sub


def unsubscribe_url(subscriber_id: UUID, *, base_url: str) -> str:
    token = _make_purpose_token(subscriber_id, "unsubscribe")
    return f"{base_url}/subscribe/unsubscribe?token={token}"


# ---------------------------------------------------------------------------
# Admin reads + send
# ---------------------------------------------------------------------------


SubscriberStatusFilter = Literal["all", "pending", "confirmed", "unsubscribed"]


async def list_all(
    db: AsyncSession,
    *,
    status_filter: SubscriberStatusFilter,
    limit: int,
    offset: int,
) -> tuple[list[Subscriber], int]:
    base = select(Subscriber)
    count = select(func.count()).select_from(Subscriber)
    if status_filter != "all":
        s = SubscriberStatus(status_filter)
        base = base.where(Subscriber.status == s)
        count = count.where(Subscriber.status == s)
    total = (await db.execute(count)).scalar_one()
    rows = (
        await db.execute(base.order_by(desc(Subscriber.created_at)).limit(limit).offset(offset))
    ).scalars().all()
    return list(rows), total


async def count_confirmed(db: AsyncSession) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Subscriber)
            .where(Subscriber.status == SubscriberStatus.confirmed)
        )
    ).scalar_one()


async def send_to_confirmed(
    db: AsyncSession, *, actor_id: UUID, post_slug: str, base_url: str
) -> int:
    """Enqueue one outbox row per confirmed subscriber. Returns the count."""
    rows = (
        await db.execute(
            select(Subscriber).where(Subscriber.status == SubscriberStatus.confirmed)
        )
    ).scalars().all()
    for sub in rows:
        db.add(
            Outbox(
                topic="newsletter.send_post",
                payload_json={
                    "subscriber_id": str(sub.id),
                    "email": sub.email,
                    "post_slug": post_slug,
                    "unsubscribe_url": unsubscribe_url(sub.id, base_url=base_url),
                },
            )
        )
    await audit.write(
        db,
        actor_id=actor_id,
        action="newsletter.broadcast_enqueued",
        resource_type="post",
        resource_id=post_slug,
        metadata={"recipients": len(rows)},
    )
    return len(rows)
