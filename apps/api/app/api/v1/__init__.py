from fastapi import APIRouter

from app.api.v1 import auth, engagement, health, media, posts, public, taxonomy

router = APIRouter(prefix="/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(posts.router)
router.include_router(taxonomy.tags_router)
router.include_router(taxonomy.categories_router)
router.include_router(taxonomy.series_router)
router.include_router(media.router)
router.include_router(public.router)
router.include_router(engagement.public_router)
router.include_router(engagement.admin_router)
