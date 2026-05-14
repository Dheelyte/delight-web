"""DTOs for comments, subscribers, analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.infra.db.models.engagement import CommentStatus, SubscriberStatus


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- Comments ---------------------------------------------------------------


class CommentSubmitIn(_Strict):
    post_slug: str = Field(min_length=1, max_length=80)
    author_name: str = Field(min_length=1, max_length=120)
    author_email: EmailStr
    content: str = Field(min_length=1, max_length=5000)
    parent_id: UUID | None = None
    honeypot: str | None = Field(default=None, max_length=200)
    form_fill_seconds: float | None = Field(default=None, ge=0)


class CommentPublicOut(_Strict):
    id: UUID
    parent_id: UUID | None
    author_name: str
    content: str
    created_at: datetime


class CommentAdminOut(CommentPublicOut):
    post_id: UUID
    post_title: str
    post_slug: str
    status: CommentStatus


class CommentListOut(_Strict):
    items: list[CommentAdminOut]
    total: int
    limit: int
    offset: int


class ModerationCountOut(_Strict):
    pending: int


# --- Subscribers ------------------------------------------------------------


class SubscribeIn(_Strict):
    email: EmailStr


class UnsubscribeIn(_Strict):
    token: str = Field(min_length=10, max_length=512)


class SubscriberAdminOut(_Strict):
    id: UUID
    email: str
    status: SubscriberStatus
    confirmed_at: datetime | None
    created_at: datetime


class SubscriberListOut(_Strict):
    items: list[SubscriberAdminOut]
    total: int
    limit: int
    offset: int


class SubscriberCountOut(_Strict):
    confirmed: int


class BroadcastIn(_Strict):
    post_slug: str = Field(min_length=1, max_length=80)


class BroadcastOut(_Strict):
    recipients: int


# --- Analytics --------------------------------------------------------------


class TrackViewIn(_Strict):
    post_slug: str = Field(min_length=1, max_length=80)
    referrer: str | None = Field(default=None, max_length=500)


class TopPostOut(_Strict):
    slug: str
    title: str
    views: int


class ReferrerOut(_Strict):
    host: str
    views: int


class AnalyticsWindowOut(_Strict):
    window: Literal[7, 30, 90]
    top_posts: list[TopPostOut]
    top_referrers: list[ReferrerOut]
