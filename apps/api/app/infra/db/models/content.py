"""Content models: media, taxonomy (tags/categories/series), posts, and revisions."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base, TimestampsMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.infra.db.models.engagement import Comment
    from app.infra.db.models.users import User


class PostStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"
    archived = "archived"


class Media(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "media"

    cloudinary_public_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    blurhash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Client-computed LQIP (data:image/png;base64,...). Inlined into srcset placeholders.
    placeholder_data_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # Focal point for cropping, normalised [0,1]. Maps to Cloudinary x_/y_ params.
    focal_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    focal_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    alt: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Tag(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "tags"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)


class Category(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)


class Series(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "series"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)


class PostTag(Base):
    __tablename__ = "post_tags"

    post_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Post(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "posts"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    content_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    content_html: Mapped[str] = mapped_column(Text(), nullable=False, default="")

    cover_image_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )
    author_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="post_status", native_enum=True),
        nullable=False,
        default=PostStatus.draft,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    series_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("series.id", ondelete="SET NULL"), nullable=True
    )
    series_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    reading_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Generated tsvector, weighted: A=title, B=excerpt, C=content_html stripped at write time.
    # We populate `search_vector` by trigger in the migration rather than as a generated
    # column, because Postgres generated columns cannot reference functions like
    # `to_tsvector` with immutable=false in all versions. The trigger keeps it in sync.
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)

    # SEO overrides (per-post; fall back to defaults in the renderer).
    meta_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    robots: Mapped[str | None] = mapped_column(String(80), nullable=True)

    author: Mapped[User] = relationship("User", back_populates="posts")
    comments: Mapped[list[Comment]] = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )
    revisions: Mapped[list[PostRevision]] = relationship(
        "PostRevision",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostRevision.created_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "(series_id IS NULL AND series_order IS NULL) "
            "OR (series_id IS NOT NULL AND series_order IS NOT NULL)",
            name="series_id_order_both_or_neither",
        ),
        UniqueConstraint("series_id", "series_order", name="uq_post_series_order"),
        Index(
            "ix_posts_status_published_at",
            "status",
            "published_at",
            postgresql_using="btree",
        ),
        Index(
            "ix_posts_published_at_desc",
            "published_at",
            postgresql_ops={"published_at": "DESC NULLS LAST"},
        ),
        Index("ix_posts_author_id", "author_id"),
        Index("ix_posts_category_id", "category_id"),
        Index(
            "ix_posts_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )


class PostRevision(UUIDPKMixin, Base):
    """A snapshot of a post's editable fields. Auto-saves coalesce within 5 min."""

    __tablename__ = "post_revisions"

    post_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Distinguish explicit saves from auto-saves; cleanup policies can use this.
    is_autosave: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    post: Mapped[Post] = relationship("Post", back_populates="revisions")

    __table_args__ = (Index("ix_post_revisions_post_id_created_at", "post_id", "created_at"),)
