"""Public-facing read-only API. No auth, ISR-friendly cache headers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.errors import NotFoundError
from app.infra.db.models.content import Post
from app.infra.db.models.system import SlugEntityType
from app.schemas.public import (
    AuthorOut,
    CategoryDetailOut,
    CategoryRef,
    MediaRef,
    PublicPostDetail,
    PublicPostList,
    PublicPostSummary,
    SearchResults,
    SeriesDetailOut,
    SeriesRef,
    SitemapEntry,
    SitemapOut,
    SlugRedirectOut,
    TagDetailOut,
    TagRef,
)
from app.services.media import get_media
from app.services import public as svc

router = APIRouter(prefix="/public", tags=["public"])

CACHE_LIST = "public, s-maxage=60, stale-while-revalidate=300"
CACHE_POST = "public, s-maxage=300, stale-while-revalidate=600"


async def _cover(db: AsyncSession, post: Post) -> MediaRef | None:
    if post.cover_image_id is None:
        return None
    try:
        m = await get_media(db, post.cover_image_id)
    except Exception:
        return None
    from app.core.config import get_settings

    return MediaRef(
        cloud_name=get_settings().cloudinary_cloud_name,
        cloudinary_public_id=m.cloudinary_public_id,
        width=m.width,
        height=m.height,
        alt=m.alt,
        placeholder_data_url=m.placeholder_data_url,
        focal_x=m.focal_x,
        focal_y=m.focal_y,
    )


async def _summary(db: AsyncSession, post: Post) -> PublicPostSummary:
    author = await svc.get_author(db, post.author_id)
    tags = await svc.tags_for_post(db, post.id)
    assert post.published_at is not None  # invariant for published filter
    return PublicPostSummary(
        slug=post.slug,
        title=post.title,
        excerpt=post.excerpt,
        published_at=post.published_at,
        reading_time_minutes=post.reading_time_minutes,
        cover=await _cover(db, post),
        tags=[TagRef(slug=t.slug, name=t.name) for t in tags],
        author=AuthorOut(
            display_name=author.display_name,
            bio=author.bio,
            avatar_url=author.avatar_url,
        ),
    )


@router.get("/posts", response_model=PublicPostList)
async def list_posts(
    response: Response,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> PublicPostList:
    rows, total = await svc.list_published(db, limit=limit, offset=offset)
    response.headers["cache-control"] = CACHE_LIST
    return PublicPostList(
        items=[await _summary(db, p) for p in rows],
        total=total, limit=limit, offset=offset,
    )


@router.get("/posts/{slug}", response_model=PublicPostDetail)
async def get_post(slug: str, response: Response, db: AsyncSession = Depends(get_db)) -> PublicPostDetail:
    post = await svc.get_published_by_slug(db, slug)
    author = await svc.get_author(db, post.author_id)
    tags = await svc.tags_for_post(db, post.id)

    category_ref: CategoryRef | None = None
    if post.category_id is not None:
        from app.services.taxonomy import list_categories

        for cat in await list_categories(db):
            if cat.id == post.category_id:
                category_ref = CategoryRef(slug=cat.slug, name=cat.name)
                break

    series_ref: SeriesRef | None = None
    if post.series_id is not None:
        from app.services.taxonomy import get_series

        s = await get_series(db, post.series_id)
        series_ref = SeriesRef(slug=s.slug, title=s.title)

    prev, nxt = await svc.series_prev_next(db, post=post)
    related = await svc.related_posts(db, post=post, limit=5)

    from app.services.comments import count_approved

    comment_count = await count_approved(db, post_id=post.id)

    response.headers["cache-control"] = CACHE_POST
    assert post.published_at is not None
    return PublicPostDetail(
        slug=post.slug,
        title=post.title,
        excerpt=post.excerpt,
        published_at=post.published_at,
        updated_at=post.updated_at,
        reading_time_minutes=post.reading_time_minutes,
        cover=await _cover(db, post),
        tags=[TagRef(slug=t.slug, name=t.name) for t in tags],
        author=AuthorOut(
            display_name=author.display_name,
            bio=author.bio,
            avatar_url=author.avatar_url,
        ),
        content_html=post.content_html,
        meta_title=post.meta_title,
        meta_description=post.meta_description,
        canonical_url=post.canonical_url,
        robots=post.robots,
        category=category_ref,
        series=series_ref,
        series_order=post.series_order,
        comment_count=comment_count,
        prev_in_series=(await _summary(db, prev)) if prev else None,
        next_in_series=(await _summary(db, nxt)) if nxt else None,
        related=[await _summary(db, r) for r in related],
    )


@router.get("/tags/{slug}", response_model=TagDetailOut)
async def get_tag(
    slug: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> TagDetailOut:
    tag, posts, total = await svc.posts_by_tag(db, tag_slug=slug, limit=limit, offset=offset)
    response.headers["cache-control"] = CACHE_LIST
    return TagDetailOut(
        slug=tag.slug, name=tag.name,
        posts=PublicPostList(
            items=[await _summary(db, p) for p in posts],
            total=total, limit=limit, offset=offset,
        ),
    )


@router.get("/categories/{slug}", response_model=CategoryDetailOut)
async def get_category(
    slug: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> CategoryDetailOut:
    cat, posts, total = await svc.posts_by_category(
        db, category_slug=slug, limit=limit, offset=offset
    )
    response.headers["cache-control"] = CACHE_LIST
    return CategoryDetailOut(
        slug=cat.slug, name=cat.name, description=cat.description,
        posts=PublicPostList(
            items=[await _summary(db, p) for p in posts],
            total=total, limit=limit, offset=offset,
        ),
    )


@router.get("/series/{slug}", response_model=SeriesDetailOut)
async def get_series(slug: str, response: Response, db: AsyncSession = Depends(get_db)) -> SeriesDetailOut:
    series, posts = await svc.posts_in_series(db, series_slug=slug)
    response.headers["cache-control"] = CACHE_LIST
    return SeriesDetailOut(
        slug=series.slug, title=series.title, description=series.description,
        posts=[await _summary(db, p) for p in posts],
    )


@router.get("/search", response_model=SearchResults)
async def search(
    response: Response,
    db: AsyncSession = Depends(get_db),
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> SearchResults:
    rows, total = await svc.search(db, q=q, limit=limit, offset=offset)
    response.headers["cache-control"] = CACHE_LIST
    return SearchResults(
        q=q,
        items=[await _summary(db, p) for p in rows],
        total=total, limit=limit, offset=offset,
    )


@router.get("/sitemap", response_model=SitemapOut)
async def sitemap(response: Response, db: AsyncSession = Depends(get_db)) -> SitemapOut:
    rows = await svc.sitemap_posts(db)
    response.headers["cache-control"] = CACHE_LIST
    return SitemapOut(
        posts=[
            SitemapEntry(slug=p.slug, updated_at=p.updated_at, published_at=p.published_at)  # type: ignore[arg-type]
            for p in rows
            if p.published_at is not None
        ]
    )


@router.get("/slug-history/{entity_type}/{old_slug}", response_model=SlugRedirectOut)
async def slug_history(
    entity_type: SlugEntityType, old_slug: str, db: AsyncSession = Depends(get_db)
) -> SlugRedirectOut:
    new = await svc.lookup_slug_history(db, entity_type=entity_type, old_slug=old_slug)
    if new is None:
        raise NotFoundError("No redirect.")
    return SlugRedirectOut(
        entity_type=entity_type.value, old_slug=old_slug, new_slug=new
    )
