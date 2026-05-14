"""Audit log writes for every privileged action.

The append-only `audit_log` table is the source of truth for "who did what when".
Service-layer code is expected to call `write` after any state-changing action.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.system import AuditLog


async def write(
    db: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            audit_metadata=metadata,
            ip=ip,
            user_agent=user_agent,
        )
    )
    await db.flush()
