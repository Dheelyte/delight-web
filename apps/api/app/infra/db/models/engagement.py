"""Comments and newsletter subscribers."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import CITEXT, INET, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base, UUIDPKMixin

if TYPE_CHECKING:
    from app.infra.db.models.content import Post


class CommentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    spam = "spam"
    deleted = "deleted"


class Comment(UUIDPKMixin, Base):
    __tablename__ = "comments"

    post_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    author_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # We never store raw emails for anonymous commenters; only a salted hash
    # used to attach Gravatars and rate-limit per-author submissions.
    author_email_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[CommentStatus] = mapped_column(
        Enum(CommentStatus, name="comment_status", native_enum=True),
        nullable=False,
        default=CommentStatus.pending,
    )
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    post: Mapped[Post] = relationship("Post", back_populates="comments")

    __table_args__ = (
        Index("ix_comments_post_id_status_created_at", "post_id", "status", "created_at"),
        Index("ix_comments_parent_id", "parent_id"),
    )


class SubscriberStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    unsubscribed = "unsubscribed"


class Subscriber(UUIDPKMixin, Base):
    __tablename__ = "subscribers"

    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    status: Mapped[SubscriberStatus] = mapped_column(
        Enum(SubscriberStatus, name="subscriber_status", native_enum=True),
        nullable=False,
        default=SubscriberStatus.pending,
    )
    # HMAC-signed; stored as the hex digest.
    confirmation_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unsubscribe_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ip: Mapped[str | None] = mapped_column(INET(), nullable=True)
