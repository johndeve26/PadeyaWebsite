"""Domain cache invalidation helpers for public discovery surfaces."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.cache import CACHE_PREFIX, cache_delete, cache_delete_pattern, cache_key

logger = logging.getLogger("padeya.cache")


def invalidate_event_caches(
    *,
    slug: str | None = None,
    event_id: UUID | str | None = None,
    host_id: UUID | str | None = None,
) -> None:
    """Invalidate event detail, lists, picks, homepage rails, calendar, map, nearby.

    Covers create / update / unpublish / cancel / sold-out / inventory changes.
    Checkout never trusts these caches — it always revalidates availability.
    """
    if slug:
        cache_delete(cache_key("events", "detail", slug))
        cache_delete(cache_key("events", "fan-connect", slug))
    if event_id:
        cache_delete(cache_key("events", "by-id", str(event_id)))
    # Broad list / discovery patterns (filters are in key suffixes).
    # Use `ns*` (not only `ns:*`) so bare keys like `events:list` also match.
    for ns in (
        "events:list*",
        "events:picks*",
        "events:homepage*",
        "events:calendar*",
        "events:map*",
        "events:nearby*",
        "events:categories*",
        "events:detail*",
    ):
        cache_delete_pattern(f"{CACHE_PREFIX}{ns}")
    if host_id:
        invalidate_host_public_caches(host_id=host_id)
    logger.debug(
        "invalidated event caches slug=%s id=%s host=%s",
        slug,
        event_id,
        host_id,
    )


def invalidate_blog_caches(*, slug: str | None = None) -> None:
    if slug:
        cache_delete(cache_key("blog", "post", slug))
    cache_delete_pattern(f"{CACHE_PREFIX}blog*")


def invalidate_help_caches(*, slug: str | None = None) -> None:
    if slug:
        cache_delete(cache_key("help", "article", slug))
    cache_delete_pattern(f"{CACHE_PREFIX}help*")


def invalidate_cms_caches() -> None:
    cache_delete_pattern(f"{CACHE_PREFIX}cms*")


def invalidate_taxonomy_caches() -> None:
    cache_delete_pattern(f"{CACHE_PREFIX}taxonomy*")
    # Event categories often mirror taxonomy for discovery filters
    cache_delete_pattern(f"{CACHE_PREFIX}events:categories*")


def invalidate_sponsorship_public_caches() -> None:
    cache_delete_pattern(f"{CACHE_PREFIX}sponsorships*")


def invalidate_host_public_caches(
    *,
    host_id: UUID | str | None = None,
    username: str | None = None,
) -> None:
    cache_delete_pattern(f"{CACHE_PREFIX}hosts:discover*")
    cache_delete_pattern(f"{CACHE_PREFIX}legacy:discover*")
    if host_id:
        cache_delete(cache_key("hosts", "public", str(host_id)))
    if username:
        cache_delete(cache_key("legacy", "page", username))
        cache_delete(cache_key("hosts", "username", username))


def invalidate_fan_public_caches(*, username: str | None = None) -> None:
    cache_delete_pattern(f"{CACHE_PREFIX}fans:directory*")
    if username:
        cache_delete(cache_key("passport", "public", username))
        cache_delete(cache_key("fans", "public", username))


def invalidate_pricing_public_caches() -> None:
    cache_delete_pattern(f"{CACHE_PREFIX}pricing*")


def invalidate_on_ticket_purchase(*, event_slug: str | None, event_id: Any = None) -> None:
    """Capacity / sold-out freshness after verified payment."""
    invalidate_event_caches(slug=event_slug, event_id=event_id)
