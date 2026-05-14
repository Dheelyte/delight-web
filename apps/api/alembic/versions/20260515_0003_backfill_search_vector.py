"""backfill posts.search_vector for any row missed by the trigger

Revision ID: 0003_backfill_search
Revises: 0002_media_focal
Create Date: 2026-05-15

Rationale: a row inserted before the trigger existed — or one whose vector
column was somehow left NULL — will silently never match `@@ tsquery`. We
touch every row, which fires the BEFORE-UPDATE trigger and rebuilds the
vector from title/excerpt/content_html. Idempotent: re-running it just
recomputes vectors that are already correct.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_backfill_search"
down_revision: str | None = "0002_media_focal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `SET title = title` fires the BEFORE UPDATE OF title trigger, so the
    # trigger function recomputes search_vector for every row.
    op.execute("UPDATE posts SET title = title")


def downgrade() -> None:
    # No-op; a downgrade can't un-populate a tsvector without losing data we
    # cannot reconstruct.
    pass
