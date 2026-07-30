"""Server-to-server Next.js revalidation (authenticated).

Used when Redis invalidation alone is not enough (directory ISR, sitemap).
Fan Passport **HTML** stays force-dynamic/no-store — this is defense-in-depth
for `/fans` and sitemap after visibility changes.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import httpx

from app.core.config import get_settings

logger = logging.getLogger("padeya.frontend_revalidate")


def notify_fan_frontend_revalidate(
    *,
    username: str | None,
    previous_username: str | None = None,
) -> bool:
    """POST /api/revalidate/fan with shared secret. Returns True on 2xx."""
    settings = get_settings()
    secret = (settings.revalidate_secret or "").strip()
    frontend = (settings.frontend_url or "").rstrip("/")
    if not secret or not frontend:
        logger.warning(
            "fan frontend revalidate skipped (REVALIDATE_SECRET or FRONTEND_URL unset)"
        )
        return False

    url = urljoin(frontend + "/", "api/revalidate/fan")
    payload: dict[str, Any] = {}
    if username:
        payload["username"] = username
    if previous_username:
        payload["previous_username"] = previous_username

    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Content-Type": "application/json",
                },
            )
        if 200 <= res.status_code < 300:
            return True
        logger.error(
            "fan frontend revalidate failed status=%s body=%s",
            res.status_code,
            (res.text or "")[:200],
        )
    except Exception:  # noqa: BLE001
        logger.exception("fan frontend revalidate request failed")
        return False
    return False


def notify_memories_frontend_revalidate(*, slug: str | None) -> bool:
    """POST /api/revalidate/memories — bust hub + album + event page ISR."""
    settings = get_settings()
    secret = (settings.revalidate_secret or "").strip()
    frontend = (settings.frontend_url or "").rstrip("/")
    if not secret or not frontend:
        logger.warning(
            "memories frontend revalidate skipped "
            "(REVALIDATE_SECRET or FRONTEND_URL unset)"
        )
        return False

    url = urljoin(frontend + "/", "api/revalidate/memories")
    payload: dict[str, Any] = {}
    if slug:
        payload["slug"] = slug

    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Content-Type": "application/json",
                },
            )
        if 200 <= res.status_code < 300:
            return True
        logger.error(
            "memories frontend revalidate failed status=%s body=%s",
            res.status_code,
            (res.text or "")[:200],
        )
    except Exception:  # noqa: BLE001
        logger.exception("memories frontend revalidate request failed")
        return False
    return False


def notify_taxonomy_frontend_revalidate() -> bool:
    """POST /api/revalidate/taxonomy — bust events + category/city hub ISR."""
    settings = get_settings()
    secret = (settings.revalidate_secret or "").strip()
    frontend = (settings.frontend_url or "").rstrip("/")
    if not secret or not frontend:
        logger.warning(
            "taxonomy frontend revalidate skipped "
            "(REVALIDATE_SECRET or FRONTEND_URL unset)"
        )
        return False

    url = urljoin(frontend + "/", "api/revalidate/taxonomy")
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.post(
                url,
                json={},
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Content-Type": "application/json",
                },
            )
        if 200 <= res.status_code < 300:
            return True
        logger.error(
            "taxonomy frontend revalidate failed status=%s body=%s",
            res.status_code,
            (res.text or "")[:200],
        )
    except Exception:  # noqa: BLE001
        logger.exception("taxonomy frontend revalidate request failed")
        return False
    return False
