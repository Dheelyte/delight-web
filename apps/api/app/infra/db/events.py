"""ORM event listeners.

Slug changes on any entity with SEO equity are recorded to `slug_history`
so the public site can issue 301 redirects from old URLs.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session as OrmSession

from app.infra.db.models.content import Category, Post, Series, Tag
from app.infra.db.models.system import SlugEntityType, SlugHistory

_SLUGGED: dict[type[Any], SlugEntityType] = {
    Post: SlugEntityType.post,
    Tag: SlugEntityType.tag,
    Category: SlugEntityType.category,
    Series: SlugEntityType.series,
}


def _record_slug_change(session: OrmSession, instance: Any) -> None:
    state = inspect(instance)
    history = state.attrs.slug.history
    if not history.has_changes():
        return

    deleted = history.deleted
    if not deleted:
        return  # initial insert sets slug for the first time - nothing to record

    old_slug = deleted[0]
    new_slug = instance.slug
    if old_slug == new_slug or old_slug is None:
        return

    entity_type = _SLUGGED[type(instance)]
    entity_id: UUID = instance.id

    session.add(
        SlugHistory(
            id=uuid4(),
            entity_type=entity_type,
            entity_id=entity_id,
            old_slug=old_slug,
            new_slug=new_slug,
        )
    )


@event.listens_for(OrmSession, "before_flush")
def _capture_slug_changes(
    session: OrmSession, _flush_context: Any, _instances: Any
) -> None:
    for obj in list(session.dirty):
        if type(obj) in _SLUGGED:
            _record_slug_change(session, obj)
