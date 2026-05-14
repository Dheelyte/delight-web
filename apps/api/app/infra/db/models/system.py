"""System tables: audit log, page views (partitioned), slug history, outbox."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base, UUIDPKMixin


class AuditLog(UUIDPKMixin, Base):
    """Append-only record of every privileged action."""

    __tablename__ = "audit_log"

    actor_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    audit_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    ip: Mapped[str | None] = mapped_column(INET(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_actor_id_created_at", "actor_id", "created_at"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )


class PageView(Base):
    """Read-side analytics. Partitioned by month on `viewed_at`.

    The partitioning is created in the migration, not via SQLAlchemy DDL -
    SA's declarative layer does not model PARTITION BY cleanly.
    The primary key is composite (id, viewed_at) to satisfy Postgres's
    rule that the partition key must be part of every unique constraint.
    """

    __tablename__ = "page_views"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    post_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Salted hash of (IP || UA || day) for debouncing without storing PII.
    session_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    referrer_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", "viewed_at", name="pk_page_views"),
        Index("ix_page_views_post_id_viewed_at", "post_id", "viewed_at"),
        Index("ix_page_views_viewed_at", "viewed_at"),
        {"postgresql_partition_by": "RANGE (viewed_at)"},
    )


class SlugEntityType(str, enum.Enum):
    post = "post"
    tag = "tag"
    category = "category"
    series = "series"


class SlugHistory(UUIDPKMixin, Base):
    """SEO equity preservation - every slug change is recorded for 301 redirects."""

    __tablename__ = "slug_history"

    entity_type: Mapped[SlugEntityType] = mapped_column(
        Enum(SlugEntityType, name="slug_entity_type", native_enum=True),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    old_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    new_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("old_slug <> new_slug", name="old_and_new_differ"),
        Index("ix_slug_history_entity_type_old_slug", "entity_type", "old_slug"),
        Index("ix_slug_history_entity", "entity_type", "entity_id"),
    )


class Outbox(UUIDPKMixin, Base):
    """Transactional outbox: messages enqueued atomically with the writing tx."""

    __tablename__ = "outbox"

    topic: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)

    __table_args__ = (
        Index(
            "ix_outbox_unprocessed",
            "created_at",
            postgresql_where="processed_at IS NULL",
        ),
    )
