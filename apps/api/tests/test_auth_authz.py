"""Role guards and post-ownership enforcement."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_post_ownership, require_role
from app.core.errors import ForbiddenError
from app.infra.db.models.content import Post, PostStatus
from app.infra.db.models.users import UserRole
from tests._factories import create_user

pytestmark = pytest.mark.usefixtures("db_session")


async def test_require_role_admits_matching_role(db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.admin)
    dep = require_role(UserRole.admin)
    # Dependency callables accept the User from the wrapping `current_user`.
    assert await dep(user=admin) is admin


async def test_require_role_rejects_mismatch(db_session: AsyncSession) -> None:
    editor = await create_user(db_session, role=UserRole.editor)
    dep = require_role(UserRole.admin)
    with pytest.raises(ForbiddenError):
        await dep(user=editor)


async def test_editor_can_modify_own_post_but_not_others(db_session: AsyncSession) -> None:
    alice = await create_user(db_session, role=UserRole.editor)
    bob = await create_user(db_session, role=UserRole.editor)
    admin = await create_user(db_session, role=UserRole.admin)

    alices_post = Post(
        slug=f"alice-{alice.id.hex[:8]}",
        title="Alice's post",
        content_html="",
        content_json={},
        author_id=alice.id,
        status=PostStatus.draft,
    )
    db_session.add(alices_post)
    await db_session.flush()

    # Alice can edit her own.
    got = await require_post_ownership(alices_post.id, user=alice, db=db_session)
    assert got.id == alices_post.id

    # Bob cannot.
    with pytest.raises(ForbiddenError):
        await require_post_ownership(alices_post.id, user=bob, db=db_session)

    # Admin can edit anyone's.
    got = await require_post_ownership(alices_post.id, user=admin, db=db_session)
    assert got.id == alices_post.id

    await db_session.rollback()
