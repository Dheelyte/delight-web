"""Database infrastructure: declarative base, ORM models, and event hooks."""

from app.infra.db.base import Base
from app.infra.db.models import (
    AuditLog,
    AuthAttempt,
    Category,
    Comment,
    Media,
    Outbox,
    PageView,
    Post,
    PostRevision,
    PostTag,
    Series,
    Session,
    SlugHistory,
    Subscriber,
    Tag,
    User,
)

# Import side-effecting event listeners so they register on import.
from app.infra.db import events as _events  # noqa: F401

__all__ = [
    "AuditLog",
    "AuthAttempt",
    "Base",
    "Category",
    "Comment",
    "Media",
    "Outbox",
    "PageView",
    "Post",
    "PostRevision",
    "PostTag",
    "Series",
    "Session",
    "SlugHistory",
    "Subscriber",
    "Tag",
    "User",
]
