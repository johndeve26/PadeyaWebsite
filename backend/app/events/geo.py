"""Privacy-safe distance helpers for nearby event discovery (Haversine fallback)."""

from __future__ import annotations

import math
from datetime import date, datetime, UTC
from typing import Literal

from sqlalchemy.orm import Session

from app.events.maps import resolve_public_map
from app.events.models import Event
from app.events.privacy import can_reveal_full_address, public_location_label

ALLOWED_RADIUS_KM = frozenset({5, 10, 25, 50, 100})
DEFAULT_RADIUS_KM = 25
MAX_LIMIT = 50

# ~0.05° ≈ 5–6 km — nearby/map cache keys never store exact GPS.
GEO_CACHE_BUCKET_DEG = 0.05

MapMode = Literal["exact", "approximate", "none"]


def bucket_coord(value: float, *, step: float = GEO_CACHE_BUCKET_DEG) -> float:
    """Snap a coordinate to a coarse grid for cache keys / public echoes."""
    if step <= 0:
        return round(float(value), 3)
    snapped = round(round(float(value) / step) * step, 4)
    return snapped


def bucket_lat_lng(
    lat: float, lng: float, *, step: float = GEO_CACHE_BUCKET_DEG
) -> tuple[float, float]:
    """Return privacy-safe lat/lng bucket used for nearby/map Redis keys."""
    return bucket_coord(lat, step=step), bucket_coord(lng, step=step)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def parse_coord(value: str | float | None) -> float | None:
    if value is None:
        return None
    try:
        n = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(n):
        return None
    return n


def validate_lat_lng(lat: float, lng: float) -> None:
    from fastapi import HTTPException, status

    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid latitude or longitude.",
        )


def normalize_radius_km(radius_km: float | int | None) -> int:
    from fastapi import HTTPException, status

    if radius_km is None:
        return DEFAULT_RADIUS_KM
    try:
        value = int(round(float(radius_km)))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid radius_km."
        ) from exc
    if value not in ALLOWED_RADIUS_KM:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"radius_km must be one of: {sorted(ALLOWED_RADIUS_KM)}.",
        )
    return value


def discovery_point(event: Event) -> tuple[float, float, MapMode] | None:
    """
    Coords safe for public distance ranking — mirrors public map resolution.
    Never uses hidden exact street pins for ranking when privacy forbids reveal.
    """
    reveal = can_reveal_full_address(event, access="public")
    payload = resolve_public_map(event, reveal_exact=reveal)
    mode = payload.get("location_map_mode") or "none"
    if mode == "none":
        return None
    lat = parse_coord(payload.get("map_latitude"))
    lng = parse_coord(payload.get("map_longitude"))
    if lat is None or lng is None:
        return None
    return lat, lng, mode  # type: ignore[return-value]


def format_distance_km(distance: float, *, approximate: bool) -> str:
    if distance < 0.1:
        label = "Nearby"
    elif distance < 10:
        label = f"{distance:.1f} km away"
    else:
        label = f"{distance:.0f} km away"
    if approximate and distance >= 0.1:
        return f"About {label}"
    return label


def _ticket_sold_proxy(event: Event) -> int:
    """Higher is more popular — sold ≈ capacity - remaining when quantity set."""
    sold = 0
    for tt in event.ticket_types or []:
        qty = int(getattr(tt, "quantity", 0) or 0)
        # Without sales ledger on list path, invert remaining stock as soft signal.
        # Prefer featured + freshness when this is weak.
        sold += max(0, 1000 - qty) if qty else 0
    return sold


def list_nearby_events(
    db: Session,
    *,
    lat: float,
    lng: float,
    radius_km: int = DEFAULT_RADIUS_KM,
    category_slug: str | None = None,
    on_date: date | None = None,
    limit: int = 20,
    page: int = 1,
) -> tuple[list[tuple[Event, float, MapMode]], int]:
    """
    Return (event, distance_km, map_mode) ranked for nearby discovery.
    Events without discovery-safe coordinates are excluded.
    """
    from app.events.service import list_published_events

    validate_lat_lng(lat, lng)
    radius_km = normalize_radius_km(radius_km)
    limit = max(1, min(int(limit or 20), MAX_LIMIT))
    page = max(1, int(page or 1))

    rows = list_published_events(
        db,
        category_slug=category_slug,
        sort=None,
    )

    scored: list[tuple[Event, float, MapMode]] = []
    for event in rows:
        if on_date is not None:
            start = event.start_datetime
            if start is None:
                continue
            local = start.date() if hasattr(start, "date") else None
            if local != on_date:
                continue
        point = discovery_point(event)
        if point is None:
            continue
        elat, elng, mode = point
        dist = haversine_km(lat, lng, elat, elng)
        if dist <= radius_km:
            scored.append((event, dist, mode))

    now = datetime.now(UTC)

    def sort_key(item: tuple[Event, float, MapMode]):
        event, dist, _mode = item
        start = event.start_datetime or now
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        featured_rank = 0 if event.featured else 1
        popularity = -_ticket_sold_proxy(event)
        freshest = event.published_at or event.created_at or start
        if freshest.tzinfo is None:
            freshest = freshest.replace(tzinfo=UTC)
        freshness = -freshest.timestamp()
        # Closest first; then soonest start among equal distance.
        return (dist, start, featured_rank, popularity, freshness)

    scored.sort(key=sort_key)
    total = len(scored)
    start_i = (page - 1) * limit
    end_i = start_i + limit
    return scored[start_i:end_i], total


def location_label_for_nearby(event: Event) -> str:
    return (
        public_location_label(event)
        or event.public_location_label
        or event.city
        or event.area
        or "Location TBA"
    )


def event_has_valid_coordinates(event: Event) -> bool:
    lat = parse_coord(getattr(event, "latitude", None)) or parse_coord(
        event.venue.latitude if event.venue else None
    )
    lng = parse_coord(getattr(event, "longitude", None)) or parse_coord(
        event.venue.longitude if event.venue else None
    )
    return lat is not None and lng is not None
