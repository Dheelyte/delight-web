"""Tags, categories, series - admin-managed taxonomy endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_editor_or_admin
from app.infra.db.models.users import User
from app.schemas.posts import (
    CategoryCreateIn,
    CategoryOut,
    SeriesCreateIn,
    SeriesOut,
    TagCreateIn,
    TagOut,
)
from app.services import taxonomy

tags_router = APIRouter(prefix="/tags", tags=["taxonomy"])
categories_router = APIRouter(prefix="/categories", tags=["taxonomy"])
series_router = APIRouter(prefix="/series", tags=["taxonomy"])


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


@tags_router.get("", response_model=list[TagOut])
async def list_tags(
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> list[TagOut]:
    return [TagOut(id=t.id, slug=t.slug, name=t.name) for t in await taxonomy.list_tags(db)]


@tags_router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(
    body: TagCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> TagOut:
    t = await taxonomy.create_tag(db, actor=actor, name=body.name)
    return TagOut(id=t.id, slug=t.slug, name=t.name)


@tags_router.patch("/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: UUID,
    body: TagCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> TagOut:
    t = await taxonomy.update_tag(db, actor=actor, tag_id=tag_id, name=body.name)
    return TagOut(id=t.id, slug=t.slug, name=t.name)


@tags_router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await taxonomy.delete_tag(db, actor=actor, tag_id=tag_id)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@categories_router.get("", response_model=list[CategoryOut])
async def list_categories(
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryOut]:
    return [
        CategoryOut(id=c.id, slug=c.slug, name=c.name, description=c.description)
        for c in await taxonomy.list_categories(db)
    ]


@categories_router.post(
    "", response_model=CategoryOut, status_code=status.HTTP_201_CREATED
)
async def create_category(
    body: CategoryCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    c = await taxonomy.create_category(
        db, actor=actor, name=body.name, description=body.description
    )
    return CategoryOut(id=c.id, slug=c.slug, name=c.name, description=c.description)


@categories_router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    body: CategoryCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    c = await taxonomy.update_category(
        db, actor=actor, category_id=category_id,
        name=body.name, description=body.description,
    )
    return CategoryOut(id=c.id, slug=c.slug, name=c.name, description=c.description)


@categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await taxonomy.delete_category(db, actor=actor, category_id=category_id)


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------


@series_router.get("", response_model=list[SeriesOut])
async def list_series(
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> list[SeriesOut]:
    return [
        SeriesOut(id=s.id, slug=s.slug, title=s.title, description=s.description)
        for s in await taxonomy.list_series(db)
    ]


@series_router.post(
    "", response_model=SeriesOut, status_code=status.HTTP_201_CREATED
)
async def create_series(
    body: SeriesCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> SeriesOut:
    s = await taxonomy.create_series(
        db, actor=actor, title=body.title, description=body.description
    )
    return SeriesOut(id=s.id, slug=s.slug, title=s.title, description=s.description)


@series_router.patch("/{series_id}", response_model=SeriesOut)
async def update_series(
    series_id: UUID,
    body: SeriesCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> SeriesOut:
    s = await taxonomy.update_series(
        db, actor=actor, series_id=series_id,
        title=body.title, description=body.description,
    )
    return SeriesOut(id=s.id, slug=s.slug, title=s.title, description=s.description)


@series_router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series(
    series_id: UUID,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    await taxonomy.delete_series(db, actor=actor, series_id=series_id)
