"""Media service: record, update (alt/focal/placeholder), validation."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.services import media as media_service
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def _seed(db, actor):
    return await media_service.record_media(
        db,
        actor=actor,
        cloudinary_public_id="posts/abc123",
        width=1600,
        height=900,
        format_="png",
        bytes_=204_800,
        blurhash=None,
        placeholder_data_url="data:image/png;base64,AAA",
        alt="An example image.",
    )


async def test_record_media_round_trip(db_session: AsyncSession) -> None:
    actor = await create_user(db_session)
    m = await _seed(db_session, actor)
    assert m.cloudinary_public_id == "posts/abc123"
    assert m.placeholder_data_url == "data:image/png;base64,AAA"
    assert m.focal_x is None and m.focal_y is None
    await db_session.rollback()


async def test_record_media_requires_alt(db_session: AsyncSession) -> None:
    actor = await create_user(db_session)
    with pytest.raises(DomainError):
        await media_service.record_media(
            db_session, actor=actor,
            cloudinary_public_id="x", width=10, height=10, format_="png",
            bytes_=10, blurhash=None, placeholder_data_url=None, alt="   ",
        )
    await db_session.rollback()


async def test_update_media_sets_focal_and_alt(db_session: AsyncSession) -> None:
    actor = await create_user(db_session)
    m = await _seed(db_session, actor)
    updated = await media_service.update_media(
        db_session, actor=actor, media_id=m.id,
        alt="Updated alt.", focal_x=0.25, focal_y=0.75,
        placeholder_data_url=None,
    )
    assert updated.alt == "Updated alt."
    assert updated.focal_x == 0.25
    assert updated.focal_y == 0.75
    await db_session.rollback()


async def test_update_media_rejects_blank_alt(db_session: AsyncSession) -> None:
    actor = await create_user(db_session)
    m = await _seed(db_session, actor)
    with pytest.raises(DomainError):
        await media_service.update_media(
            db_session, actor=actor, media_id=m.id,
            alt="   ", focal_x=None, focal_y=None, placeholder_data_url=None,
        )
    await db_session.rollback()


async def test_update_media_404(db_session: AsyncSession) -> None:
    actor = await create_user(db_session)
    from uuid import uuid4

    with pytest.raises(NotFoundError):
        await media_service.update_media(
            db_session, actor=actor, media_id=uuid4(),
            alt=None, focal_x=None, focal_y=None, placeholder_data_url=None,
        )
    await db_session.rollback()
