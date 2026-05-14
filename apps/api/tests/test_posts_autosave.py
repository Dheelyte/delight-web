"""Autosave coalescing + explicit-save revision behaviour."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.users import UserRole
from app.services import posts as posts_service
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


def _html(text: str) -> str:
    return f"<p>{text}</p>"


async def test_autosave_coalesces_into_single_revision(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    post = await posts_service.create_post(
        db_session, actor=actor, title="T", excerpt=None
    )

    for n in range(5):
        await posts_service.update_post_content(
            db_session,
            actor=actor,
            post=post,
            title="T",
            excerpt=None,
            content_html=_html(f"draft {n}"),
            autosave=True,
        )

    revs = await posts_service.list_revisions(db_session, post_id=post.id)
    autosaves = [r for r in revs if r.is_autosave]
    assert len(autosaves) == 1
    assert "draft 4" in str(autosaves[0].content_json)
    await db_session.rollback()


async def test_explicit_save_creates_new_revision_each_time(
    db_session: AsyncSession,
) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    post = await posts_service.create_post(
        db_session, actor=actor, title="T", excerpt=None
    )
    for n in range(3):
        await posts_service.update_post_content(
            db_session, actor=actor, post=post, title=f"T{n}",
            excerpt=None, content_html=_html(str(n)), autosave=False,
        )
    revs = await posts_service.list_revisions(db_session, post_id=post.id)
    explicit = [r for r in revs if not r.is_autosave]
    assert len(explicit) == 3
    await db_session.rollback()


async def test_restore_revision_rolls_post_back(db_session: AsyncSession) -> None:
    actor = await create_user(db_session, role=UserRole.editor)
    post = await posts_service.create_post(
        db_session, actor=actor, title="Original", excerpt=None
    )
    await posts_service.update_post_content(
        db_session, actor=actor, post=post, title="V1",
        excerpt=None, content_html=_html("first version body"), autosave=False,
    )
    revs = await posts_service.list_revisions(db_session, post_id=post.id)
    v1_id = revs[0].id

    await posts_service.update_post_content(
        db_session, actor=actor, post=post, title="V2",
        excerpt=None, content_html=_html("second version body"), autosave=False,
    )
    assert post.title == "V2"
    assert "second version body" in post.content_html

    await posts_service.restore_revision(
        db_session, actor=actor, post=post, revision_id=v1_id
    )
    assert post.title == "V1"
    assert "first version body" in post.content_html
    await db_session.rollback()
