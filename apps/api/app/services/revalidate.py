"""Emit on-demand revalidation calls to the web app.

The web app exposes `/api/revalidate` (secret-protected). We POST a list of
paths to invalidate after publish/update/delete. Failure is non-fatal - ISR's
time-based revalidation is the safety net.
"""

from __future__ import annotations

import os
from typing import Final

import httpx

from app.core.logging import get_logger

_log = get_logger(__name__)

_WEB_BASE: Final = os.environ.get("WEB_BASE_URL", "http://localhost:3000")
_SECRET: Final = os.environ.get("REVALIDATE_SECRET", "")


async def revalidate(paths: list[str]) -> None:
    if not paths or not _SECRET:
        return
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                f"{_WEB_BASE}/api/revalidate",
                json={"paths": paths},
                headers={"x-revalidate-secret": _SECRET},
            )
    except Exception as exc:  # noqa: BLE001  fire-and-forget - log and move on
        _log.warning("revalidate.failed", paths=paths, error=str(exc))


def paths_for_post(slug: str, *, tag_slugs: list[str] | None = None) -> list[str]:
    paths = ["/", f"/posts/{slug}", "/sitemap.xml", "/rss.xml", "/atom.xml"]
    for t in tag_slugs or []:
        paths.append(f"/tags/{t}")
    return paths
