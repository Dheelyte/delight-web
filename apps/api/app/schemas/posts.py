"""DTOs for posts, taxonomy, media."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.infra.db.models.content import PostStatus


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


class PostCreateIn(_Strict):
    title: str = Field(min_length=1, max_length=200)
    excerpt: str | None = Field(default=None, max_length=500)


class PostContentIn(_Strict):
    title: str = Field(min_length=1, max_length=200)
    excerpt: str | None = Field(default=None, max_length=500)
    # HTML produced by the rich editor. The server sanitises with nh3 before
    # persisting; this is the only safety boundary for stored content.
    content_html: str = Field(default="", max_length=200_000)
    autosave: bool = False


class PostMetadataIn(_Strict):
    slug: str | None = Field(default=None, min_length=1, max_length=80)
    cover_image_id: UUID | None = None
    category_id: UUID | None = None
    series_id: UUID | None = None
    series_order: int | None = Field(default=None, ge=1)
    tag_ids: list[UUID] | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=200)
    canonical_url: str | None = Field(default=None, max_length=500)
    robots: str | None = Field(default=None, max_length=80)


class TagOut(_Strict):
    id: UUID
    slug: str
    name: str


class PostSummaryOut(_Strict):
    id: UUID
    slug: str
    title: str
    excerpt: str | None
    status: PostStatus
    author_id: UUID
    published_at: datetime | None
    scheduled_for: datetime | None
    updated_at: datetime
    reading_time_minutes: int


class PostDetailOut(PostSummaryOut):
    content_html: str
    cover_image_id: UUID | None
    category_id: UUID | None
    series_id: UUID | None
    series_order: int | None
    meta_title: str | None
    meta_description: str | None
    canonical_url: str | None
    robots: str | None
    tag_ids: list[UUID]


class PostListOut(_Strict):
    items: list[PostSummaryOut]
    total: int
    limit: int
    offset: int


class RevisionOut(_Strict):
    id: UUID
    title: str
    is_autosave: bool
    created_at: datetime
    created_by: UUID | None


class SlugCheckOut(_Strict):
    slug: str
    available: bool


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------


class TagCreateIn(_Strict):
    name: str = Field(min_length=1, max_length=80)


class CategoryOut(_Strict):
    id: UUID
    slug: str
    name: str
    description: str | None


class CategoryCreateIn(_Strict):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class SeriesOut(_Strict):
    id: UUID
    slug: str
    title: str
    description: str | None


class SeriesCreateIn(_Strict):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------


class CloudinarySignOut(_Strict):
    cloud_name: str
    api_key: str
    timestamp: int
    signature: str
    folder: str | None


class MediaCreateIn(_Strict):
    cloudinary_public_id: str = Field(min_length=1, max_length=255)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    format: str = Field(min_length=1, max_length=16)
    bytes: int = Field(ge=1)
    blurhash: str | None = Field(default=None, max_length=128)
    placeholder_data_url: str | None = Field(default=None, max_length=4_000)
    alt: str = Field(min_length=1, max_length=500)


class MediaUpdateIn(_Strict):
    alt: str | None = Field(default=None, min_length=1, max_length=500)
    focal_x: float | None = Field(default=None, ge=0.0, le=1.0)
    focal_y: float | None = Field(default=None, ge=0.0, le=1.0)
    placeholder_data_url: str | None = Field(default=None, max_length=4_000)


class MediaOut(_Strict):
    id: UUID
    cloud_name: str
    cloudinary_public_id: str
    width: int
    height: int
    format: str
    bytes: int
    blurhash: str | None
    placeholder_data_url: str | None
    focal_x: float | None
    focal_y: float | None
    alt: str
