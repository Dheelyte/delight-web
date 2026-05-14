"""DTOs for the public read surface."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorOut(_Strict):
    display_name: str
    bio: str | None
    avatar_url: str | None


class MediaRef(_Strict):
    cloud_name: str
    cloudinary_public_id: str
    width: int
    height: int
    alt: str
    placeholder_data_url: str | None
    focal_x: float | None
    focal_y: float | None


class TagRef(_Strict):
    slug: str
    name: str


class CategoryRef(_Strict):
    slug: str
    name: str


class SeriesRef(_Strict):
    slug: str
    title: str


class PublicPostSummary(_Strict):
    slug: str
    title: str
    excerpt: str | None
    published_at: datetime
    reading_time_minutes: int
    cover: MediaRef | None
    tags: list[TagRef]
    author: AuthorOut


class PublicPostDetail(PublicPostSummary):
    content_html: str
    updated_at: datetime
    meta_title: str | None
    meta_description: str | None
    canonical_url: str | None
    robots: str | None
    category: CategoryRef | None
    series: SeriesRef | None
    series_order: int | None
    comment_count: int
    prev_in_series: PublicPostSummary | None
    next_in_series: PublicPostSummary | None
    related: list[PublicPostSummary]


class PublicPostList(_Strict):
    items: list[PublicPostSummary]
    total: int
    limit: int
    offset: int


class TagDetailOut(_Strict):
    slug: str
    name: str
    posts: PublicPostList


class CategoryDetailOut(_Strict):
    slug: str
    name: str
    description: str | None
    posts: PublicPostList


class SeriesDetailOut(_Strict):
    slug: str
    title: str
    description: str | None
    posts: list[PublicPostSummary]


class SearchResults(_Strict):
    q: str
    items: list[PublicPostSummary]
    total: int
    limit: int
    offset: int


class SitemapEntry(_Strict):
    slug: str
    updated_at: datetime
    published_at: datetime


class SitemapOut(_Strict):
    posts: list[SitemapEntry]


class SlugRedirectOut(_Strict):
    entity_type: Literal["post", "tag", "category", "series"]
    old_slug: str
    new_slug: str
