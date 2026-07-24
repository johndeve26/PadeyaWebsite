"""Helpers for caching public event discovery payloads."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.cache import CacheTTL, cache_key, get_or_set
from app.events.geo import bucket_coord, bucket_lat_lng


def events_list_key(**filters: Any) -> str:
    return cache_key(
        "events",
        "list",
        **{k: v for k, v in filters.items() if v not in (None, "", False)},
    )


def events_picks_key(**filters: Any) -> str:
    return cache_key(
        "events",
        "picks",
        **{k: v for k, v in filters.items() if v not in (None, "", False)},
    )


def events_homepage_key(**filters: Any) -> str:
    """Homepage public rails (featured / weekend / default market)."""
    return cache_key(
        "events",
        "homepage",
        **{k: v for k, v in filters.items() if v not in (None, "", False)},
    )


def events_detail_key(slug: str) -> str:
    return cache_key("events", "detail", slug)


def events_categories_key() -> str:
    return cache_key("events", "categories", "all")


def events_calendar_key(**filters: Any) -> str:
    return cache_key(
        "events",
        "calendar",
        **{k: v for k, v in filters.items() if v not in (None, "", False)},
    )


def events_nearby_key(**filters: Any) -> str:
    """Nearby cache key — bucketed lat/lng only (never exact GPS).

    Ranking still uses the request's precise coords inside the producer;
    Redis keys share a ~5 km grid so we do not store raw browser GPS.
    ``location_label`` is display-only and must not affect the key.
    """
    rounded = {
        k: v
        for k, v in filters.items()
        if k not in ("location_label", "lat", "lng") and v not in (None, "", False)
    }
    lat = filters.get("lat")
    lng = filters.get("lng")
    if lat is not None and lng is not None:
        b_lat, b_lng = bucket_lat_lng(float(lat), float(lng))
        rounded["lat"] = b_lat
        rounded["lng"] = b_lng
    elif lat is not None:
        rounded["lat"] = bucket_coord(float(lat))
    elif lng is not None:
        rounded["lng"] = bucket_coord(float(lng))
    return cache_key("events", "nearby", **rounded)


def events_map_key(**filters: Any) -> str:
    rounded = dict(filters)
    for geo in ("north", "south", "east", "west", "lat", "lng"):
        if rounded.get(geo) is not None:
            rounded[geo] = bucket_coord(float(rounded[geo]))
    return cache_key(
        "events",
        "map",
        **{k: v for k, v in rounded.items() if v not in (None, "", False)},
    )


def cached_public(key: str, ttl: int, producer):
    return get_or_set(key, ttl, producer)


# Re-export TTLs for call sites
TTL = CacheTTL


def host_id_str(host_id: UUID | None) -> str | None:
    return str(host_id) if host_id else None
