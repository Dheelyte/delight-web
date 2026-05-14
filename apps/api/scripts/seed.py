"""Idempotent seed: one admin, a series, tags, three demo posts.

Run with:  uv run python -m scripts.seed
Safe to re-run; lookups by slug/email mean we never duplicate rows.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.db import session_scope
from app.core.security import hash_password
from app.infra.db.models.content import Post, PostStatus, Series, Tag
from app.infra.db.models.users import User, UserRole


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _doc(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


async def _get_or_create_admin() -> User:
    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@localhost.com")
    password = os.environ.get("SEED_ADMIN_PASSWORD", "changeme-then-rotate")
    async with session_scope() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        admin = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
            display_name="Admin",
            bio="Default admin account — rotate the password before going live.",
        )
        session.add(admin)
        await session.flush()
        return admin


async def _get_or_create_tag(slug: str, name: str) -> Tag:
    async with session_scope() as session:
        existing = (
            await session.execute(select(Tag).where(Tag.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        tag = Tag(slug=slug, name=name)
        session.add(tag)
        await session.flush()
        return tag


async def _get_or_create_series(slug: str, title: str, description: str) -> Series:
    async with session_scope() as session:
        existing = (
            await session.execute(select(Series).where(Series.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        series = Series(slug=slug, title=title, description=description)
        session.add(series)
        await session.flush()
        return series


async def _upsert_post(
    *,
    slug: str,
    title: str,
    excerpt: str,
    body: str,
    author_id: Any,
    series_id: Any | None,
    series_order: int | None,
    published: bool,
) -> None:
    async with session_scope() as session:
        existing = (
            await session.execute(select(Post).where(Post.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            return
        post = Post(
            slug=slug,
            title=title,
            excerpt=excerpt,
            content_json=_doc(body),
            content_html=f"<p>{body}</p>",
            author_id=author_id,
            status=PostStatus.published if published else PostStatus.draft,
            published_at=_now() if published else None,
            series_id=series_id,
            series_order=series_order,
            reading_time_minutes=max(1, len(body.split()) // 200),
        )
        session.add(post)


async def seed() -> None:
    admin = await _get_or_create_admin()
    tags = {
        "engineering": await _get_or_create_tag("engineering", "Engineering"),
        "writing": await _get_or_create_tag("writing", "Writing"),
        "tooling": await _get_or_create_tag("tooling", "Tooling"),
    }
    series = await _get_or_create_series(
        slug="building-this-blog",
        title="Building this blog",
        description="A walkthrough of every architectural decision.",
    )

    await _upsert_post(
        slug="hello-world",
        title="Hello, world",
        excerpt="The first post — a sanity check that publishing actually works.",
        body=(
            "This is a seeded post. The body is intentionally short — "
            "Stage 4 will replace it with real editorial content."
        ),
        author_id=admin.id,
        series_id=None,
        series_order=None,
        published=True,
    )
    await _upsert_post(
        slug="why-this-stack",
        title="Why this stack",
        excerpt="Choosing Next.js, FastAPI, and Postgres over the alternatives.",
        body=(
            "Boring technology wins. Each choice in the stack favours longevity "
            "over novelty — and the few interesting decisions are documented as ADRs."
        ),
        author_id=admin.id,
        series_id=series.id,
        series_order=1,
        published=True,
    )
    await _upsert_post(
        slug="serverless-tradeoffs",
        title="The serverless trade-offs",
        excerpt="What you give up by running a blog on Lambda — and why it's fine.",
        body=(
            "Cold starts, connection pooling, and the file-system being /tmp. "
            "Each one has a clean answer at this scale; this post explains them."
        ),
        author_id=admin.id,
        series_id=series.id,
        series_order=2,
        published=False,
    )

    # Attach tags to posts (idempotent via ON CONFLICT DO NOTHING).
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.infra.db.models.content import PostTag

    async with session_scope() as session:
        hello = (
            await session.execute(select(Post).where(Post.slug == "hello-world"))
        ).scalar_one()
        why = (
            await session.execute(select(Post).where(Post.slug == "why-this-stack"))
        ).scalar_one()

        for post_id, tag_id in (
            (hello.id, tags["engineering"].id),
            (why.id, tags["engineering"].id),
            (why.id, tags["tooling"].id),
        ):
            stmt = (
                pg_insert(PostTag)
                .values(post_id=post_id, tag_id=tag_id)
                .on_conflict_do_nothing(index_elements=["post_id", "tag_id"])
            )
            await session.execute(stmt)


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
