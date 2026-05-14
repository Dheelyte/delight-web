"""Slug generation with collision suffixing."""

from __future__ import annotations

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.base import Base


def make_slug(value: str, *, max_length: int = 80) -> str:
    """Lowercase, hyphenated, ASCII-only. Never exceeds `max_length`."""
    s = slugify(value, max_length=max_length, word_boundary=True, save_order=True)
    return s or "untitled"


async def unique_slug(
    db: AsyncSession,
    *,
    base: str,
    model: type[Base],
    exclude_id: object | None = None,
) -> str:
    """Append -2, -3, ... until `base-N` is unused on `model.slug`."""
    candidate = base
    n = 1
    while True:
        stmt = select(model).where(model.slug == candidate)  # type: ignore[attr-defined]
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)  # type: ignore[attr-defined]
        existing = (await db.execute(stmt)).first()
        if existing is None:
            return candidate
        n += 1
        suffix = f"-{n}"
        candidate = f"{base[: 80 - len(suffix)]}{suffix}"
