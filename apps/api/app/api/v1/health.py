"""Healthcheck endpoint reporting database connectivity."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.db import get_sessionmaker
from app.core.logging import get_logger

router = APIRouter(tags=["health"])
log = get_logger(__name__)


class ComponentStatus(BaseModel):
    status: Literal["ok", "down"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str = "api"
    components: dict[str, ComponentStatus]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    components: dict[str, ComponentStatus] = {}

    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        components["db"] = ComponentStatus(status="ok")
    except Exception as exc:
        log.warning("healthcheck.db.failed", error=str(exc))
        components["db"] = ComponentStatus(status="down", detail=str(exc))

    overall = "ok" if all(c.status == "ok" for c in components.values()) else "degraded"
    return HealthResponse(status=overall, components=components)
