"""Media: server signs Cloudinary uploads, persists media rows, edits alt/focal."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_editor_or_admin
from app.core.config import get_settings
from app.infra.db.models.users import User
from app.schemas.posts import CloudinarySignOut, MediaCreateIn, MediaOut, MediaUpdateIn
from app.services import media as media_service

router = APIRouter(prefix="/media", tags=["media"])


class _SignIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folder: str | None = Field(default=None, max_length=120)


def _to_out(m: object) -> MediaOut:  # accepts the ORM Media row
    # Embed cloud_name so the client never has to read a build-time env var to
    # construct delivery URLs. One short string per response - worth the bytes.
    return MediaOut(
        id=m.id,  # type: ignore[attr-defined]
        cloud_name=get_settings().CLOUDINARY_CLOUD_NAME,
        cloudinary_public_id=m.cloudinary_public_id,  # type: ignore[attr-defined]
        width=m.width,  # type: ignore[attr-defined]
        height=m.height,  # type: ignore[attr-defined]
        format=m.format,  # type: ignore[attr-defined]
        bytes=m.bytes,  # type: ignore[attr-defined]
        blurhash=m.blurhash,  # type: ignore[attr-defined]
        placeholder_data_url=m.placeholder_data_url,  # type: ignore[attr-defined]
        focal_x=m.focal_x,  # type: ignore[attr-defined]
        focal_y=m.focal_y,  # type: ignore[attr-defined]
        alt=m.alt,  # type: ignore[attr-defined]
    )


@router.post("/sign", response_model=CloudinarySignOut)
async def sign_upload(
    body: _SignIn,
    _: User = Depends(require_editor_or_admin),
) -> CloudinarySignOut:
    payload = media_service.sign_upload(folder=body.folder)
    return CloudinarySignOut(**payload)


@router.post("", response_model=MediaOut, status_code=status.HTTP_201_CREATED)
async def create_media(
    body: MediaCreateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    m = await media_service.record_media(
        db,
        actor=actor,
        cloudinary_public_id=body.cloudinary_public_id,
        width=body.width,
        height=body.height,
        format_=body.format,
        bytes_=body.bytes,
        blurhash=body.blurhash,
        placeholder_data_url=body.placeholder_data_url,
        alt=body.alt,
    )
    return _to_out(m)


@router.get("/{media_id}", response_model=MediaOut)
async def get_media(
    media_id: UUID,
    _: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    m = await media_service.get_media(db, media_id)
    return _to_out(m)


@router.patch("/{media_id}", response_model=MediaOut)
async def update_media(
    media_id: UUID,
    body: MediaUpdateIn,
    actor: User = Depends(require_editor_or_admin),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    m = await media_service.update_media(
        db,
        actor=actor,
        media_id=media_id,
        alt=body.alt,
        focal_x=body.focal_x,
        focal_y=body.focal_y,
        placeholder_data_url=body.placeholder_data_url,
    )
    return _to_out(m)
