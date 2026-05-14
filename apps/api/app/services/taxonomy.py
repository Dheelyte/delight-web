"""Tags, categories, series — small CRUD services."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.slug import make_slug, unique_slug
from app.infra.db.models.content import Category, Post, PostTag, Series, Tag
from app.services import audit
from app.infra.db.models.users import User


async def list_tags(db: AsyncSession) -> list[Tag]:
    return list((await db.execute(select(Tag).order_by(Tag.name))).scalars().all())


async def create_tag(db: AsyncSession, *, actor: User, name: str) -> Tag:
    base = make_slug(name)
    slug = await unique_slug(db, base=base, model=Tag)
    tag = Tag(slug=slug, name=name)
    db.add(tag)
    await db.flush()
    await audit.write(
        db, actor_id=actor.id, action="tag.created", resource_type="tag",
        resource_id=str(tag.id),
    )
    return tag


async def list_categories(db: AsyncSession) -> list[Category]:
    return list(
        (await db.execute(select(Category).order_by(Category.name))).scalars().all()
    )


async def create_category(
    db: AsyncSession, *, actor: User, name: str, description: str | None
) -> Category:
    base = make_slug(name)
    slug = await unique_slug(db, base=base, model=Category)
    cat = Category(slug=slug, name=name, description=description)
    db.add(cat)
    await db.flush()
    await audit.write(
        db, actor_id=actor.id, action="category.created", resource_type="category",
        resource_id=str(cat.id),
    )
    return cat


async def list_series(db: AsyncSession) -> list[Series]:
    return list((await db.execute(select(Series).order_by(Series.title))).scalars().all())


async def create_series(
    db: AsyncSession, *, actor: User, title: str, description: str | None
) -> Series:
    base = make_slug(title)
    slug = await unique_slug(db, base=base, model=Series)
    s = Series(slug=slug, title=title, description=description)
    db.add(s)
    await db.flush()
    await audit.write(
        db, actor_id=actor.id, action="series.created", resource_type="series",
        resource_id=str(s.id),
    )
    return s


async def get_series(db: AsyncSession, series_id: UUID) -> Series:
    s = (
        await db.execute(select(Series).where(Series.id == series_id))
    ).scalar_one_or_none()
    if s is None:
        raise NotFoundError("Series not found.")
    return s


# ---------------------------------------------------------------------------
# Edit + delete (delete refuses if any posts are attached)
# ---------------------------------------------------------------------------


async def _post_count_for_tag(db: AsyncSession, tag_id: UUID) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(PostTag).where(PostTag.tag_id == tag_id)
        )
    ).scalar_one()


async def _post_count_for_category(db: AsyncSession, category_id: UUID) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Post).where(Post.category_id == category_id)
        )
    ).scalar_one()


async def _post_count_for_series(db: AsyncSession, series_id: UUID) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Post).where(Post.series_id == series_id)
        )
    ).scalar_one()


async def update_tag(
    db: AsyncSession, *, actor: User, tag_id: UUID, name: str
) -> Tag:
    tag = (await db.execute(select(Tag).where(Tag.id == tag_id))).scalar_one_or_none()
    if tag is None:
        raise NotFoundError("Tag not found.")
    new_slug = make_slug(name)
    if new_slug != tag.slug:
        tag.slug = await unique_slug(db, base=new_slug, model=Tag, exclude_id=tag.id)
    tag.name = name
    await audit.write(
        db, actor_id=actor.id, action="tag.updated", resource_type="tag",
        resource_id=str(tag.id),
    )
    return tag


async def delete_tag(db: AsyncSession, *, actor: User, tag_id: UUID) -> None:
    tag = (await db.execute(select(Tag).where(Tag.id == tag_id))).scalar_one_or_none()
    if tag is None:
        raise NotFoundError("Tag not found.")
    if (await _post_count_for_tag(db, tag.id)) > 0:
        raise ConflictError("Tag is in use by one or more posts.")
    await db.delete(tag)
    await audit.write(
        db, actor_id=actor.id, action="tag.deleted", resource_type="tag",
        resource_id=str(tag_id),
    )


async def update_category(
    db: AsyncSession,
    *,
    actor: User,
    category_id: UUID,
    name: str,
    description: str | None,
) -> Category:
    cat = (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()
    if cat is None:
        raise NotFoundError("Category not found.")
    new_slug = make_slug(name)
    if new_slug != cat.slug:
        cat.slug = await unique_slug(db, base=new_slug, model=Category, exclude_id=cat.id)
    cat.name = name
    cat.description = description
    await audit.write(
        db, actor_id=actor.id, action="category.updated",
        resource_type="category", resource_id=str(cat.id),
    )
    return cat


async def delete_category(db: AsyncSession, *, actor: User, category_id: UUID) -> None:
    cat = (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()
    if cat is None:
        raise NotFoundError("Category not found.")
    if (await _post_count_for_category(db, cat.id)) > 0:
        raise ConflictError("Category is in use by one or more posts.")
    await db.delete(cat)
    await audit.write(
        db, actor_id=actor.id, action="category.deleted",
        resource_type="category", resource_id=str(category_id),
    )


async def update_series(
    db: AsyncSession,
    *,
    actor: User,
    series_id: UUID,
    title: str,
    description: str | None,
) -> Series:
    s = await get_series(db, series_id)
    new_slug = make_slug(title)
    if new_slug != s.slug:
        s.slug = await unique_slug(db, base=new_slug, model=Series, exclude_id=s.id)
    s.title = title
    s.description = description
    await audit.write(
        db, actor_id=actor.id, action="series.updated",
        resource_type="series", resource_id=str(s.id),
    )
    return s


async def delete_series(db: AsyncSession, *, actor: User, series_id: UUID) -> None:
    s = await get_series(db, series_id)
    if (await _post_count_for_series(db, s.id)) > 0:
        raise ConflictError("Series has one or more posts attached.")
    await db.delete(s)
    await audit.write(
        db, actor_id=actor.id, action="series.deleted",
        resource_type="series", resource_id=str(series_id),
    )
