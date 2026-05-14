"""media: focal point coords + LQIP placeholder data URL

Revision ID: 0002_media_focal
Revises: 0001_initial
Create Date: 2026-05-14
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_media_focal"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE media ADD COLUMN focal_x DOUBLE PRECISION",
    "ALTER TABLE media ADD COLUMN focal_y DOUBLE PRECISION",
    "ALTER TABLE media ADD COLUMN placeholder_data_url TEXT",
    # Focal coords are normalised [0, 1] when present.
    """
    ALTER TABLE media ADD CONSTRAINT ck_media_focal_x_range
        CHECK (focal_x IS NULL OR (focal_x >= 0 AND focal_x <= 1))
    """,
    """
    ALTER TABLE media ADD CONSTRAINT ck_media_focal_y_range
        CHECK (focal_y IS NULL OR (focal_y >= 0 AND focal_y <= 1))
    """,
]

DOWNGRADE_STATEMENTS: list[str] = [
    "ALTER TABLE media DROP CONSTRAINT IF EXISTS ck_media_focal_y_range",
    "ALTER TABLE media DROP CONSTRAINT IF EXISTS ck_media_focal_x_range",
    "ALTER TABLE media DROP COLUMN IF EXISTS placeholder_data_url",
    "ALTER TABLE media DROP COLUMN IF EXISTS focal_y",
    "ALTER TABLE media DROP COLUMN IF EXISTS focal_x",
]


def upgrade() -> None:
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
