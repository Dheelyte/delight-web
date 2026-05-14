"""Cloudinary signed-upload helper + media row persistence.

The browser uploads *directly* to Cloudinary; the server only signs the
upload params. We never accept raw file bytes through FastAPI - that keeps
the Lambda payload tiny and offloads transformation to Cloudinary.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import DomainError, ExternalServiceError, NotFoundError
from app.infra.db.models.content import Media
from app.services import audit
from app.infra.db.models.users import User


def sign_upload(*, folder: str | None = None) -> dict[str, Any]:
    """Return params for an unsigned-in-the-browser, signed-by-us Cloudinary upload."""
    settings = get_settings()
    if not (settings.CLOUDINARY_CLOUD_NAME and settings.cloudinary_api_key and settings.CLOUDINARY_API_SECRET):
        raise ExternalServiceError("Cloudinary is not configured.")

    timestamp = int(time.time())
    params: dict[str, Any] = {"timestamp": timestamp}
    if folder:
        params["folder"] = folder

    # Cloudinary signature: SHA1 of "<param1>=<v>&<param2>=<v>...<api_secret>"
    # over the alphabetised non-empty params.
    serialised = "&".join(f"{k}={params[k]}" for k in sorted(params))
    signature = hashlib.sha1(
        f"{serialised}{settings.CLOUDINARY_API_SECRET}".encode("utf-8")
    ).hexdigest()

    return {
        "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
        "api_key": settings.CLOUDINARY_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "folder": folder,
    }


async def record_media(
    db: AsyncSession,
    *,
    actor: User,
    cloudinary_public_id: str,
    width: int,
    height: int,
    format_: str,
    bytes_: int,
    blurhash: str | None,
    placeholder_data_url: str | None,
    alt: str,
) -> Media:
    if not alt.strip():
        raise DomainError("Alt text is required.")
    media = Media(
        cloudinary_public_id=cloudinary_public_id,
        width=width,
        height=height,
        format=format_,
        bytes=bytes_,
        blurhash=blurhash,
        placeholder_data_url=placeholder_data_url,
        alt=alt,
        uploaded_by=actor.id,
    )
    db.add(media)
    await db.flush()
    await audit.write(
        db,
        actor_id=actor.id,
        action="media.uploaded",
        resource_type="media",
        resource_id=str(media.id),
        metadata={"public_id": cloudinary_public_id, "bytes": bytes_},
    )
    return media


async def update_media(
    db: AsyncSession,
    *,
    actor: User,
    media_id: UUID,
    alt: str | None,
    focal_x: float | None,
    focal_y: float | None,
    placeholder_data_url: str | None,
) -> Media:
    media = await get_media(db, media_id)
    changed: list[str] = []

    if alt is not None:
        stripped = alt.strip()
        if not stripped:
            raise DomainError("Alt text cannot be empty.")
        media.alt = stripped
        changed.append("alt")

    if focal_x is not None:
        media.focal_x = focal_x
        changed.append("focal_x")
    if focal_y is not None:
        media.focal_y = focal_y
        changed.append("focal_y")
    if placeholder_data_url is not None:
        media.placeholder_data_url = placeholder_data_url
        changed.append("placeholder_data_url")

    await audit.write(
        db,
        actor_id=actor.id,
        action="media.updated",
        resource_type="media",
        resource_id=str(media.id),
        metadata={"fields": changed},
    )
    return media


async def get_media(db: AsyncSession, media_id: UUID) -> Media:
    m = (await db.execute(select(Media).where(Media.id == media_id))).scalar_one_or_none()
    if m is None:
        raise NotFoundError("Media not found.")
    return m
