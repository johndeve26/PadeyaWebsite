"""Privacy-safe map discovery — compact pins for current map bounds."""

from __future__ import annotations

from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.events.geo import (
    discovery_point,
    format_distance_km,
    haversine_km,
    parse_coord,
    validate_lat_lng,
    MapMode,
)
from app.events.models import Event
from app.events.privacy import (
    can_reveal_full_address,
    location_privacy_message,
    public_location_label,
)
from app.events.service import list_published_events

MAX_MAP_RESULTS = 200
MapPriceFilter = Literal["any", "free", "paid"]


def validate_bounds(
    *,
    north: float,
    south: float,
    east: float,
    west: float,
) -> None:
    if not (-90.0 <= south <= north <= 90.0):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid latitude bounds (need -90 ≤ south ≤ north ≤ 90).",
        )
    if not (-180.0 <= west <= 180.0) or not (-180.0 <= east <= 180.0):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid longitude bounds (need -180 ≤ west/east ≤ 180).",
        )
    # Reject degenerate / tiny-zero boxes that would scrape the globe.
    if abs(north - south) < 1e-6:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Map bounds north and south must differ.",
        )


def point_in_bounds(
    lat: float,
    lng: float,
    *,
    north: float,
    south: float,
    east: float,
    west: float,
) -> bool:
    if lat < south or lat > north:
        return False
    if west <= east:
        return west <= lng <= east
    # Antimeridian-crossing window
    return lng >= west or lng <= east


def _min_public_price(event: Event) -> Decimal | None:
    prices: list[Decimal] = []
    for tt in event.ticket_types or []:
        if getattr(tt, "visibility", "public") != "public":
            continue
        try:
            prices.append(Decimal(str(tt.price)))
        except Exception:  # noqa: BLE001
            continue
    if not prices:
        return None
    return min(prices)


def _price_label(min_price: Decimal | None) -> str:
    if min_price is None:
        return "See tickets"
    if min_price == 0:
        return "Free"
    # Compact label for markers / cards — NGN without forcing locale in BE.
    amount = float(min_price)
    if amount >= 1000 and amount == int(amount):
        return f"From ₦{int(amount):,}"
    if amount == int(amount):
        return f"From ₦{int(amount)}"
    return f"From ₦{amount:,.2f}"


def compact_map_event(
    event: Event,
    *,
    distance_km: float | None = None,
    map_mode: MapMode | None = None,
) -> dict:
    """
    Compact, map-safe public pin payload.

    Never includes street address, formatted_address, google_place_id, or
    exact venue coordinates when location privacy forbids reveal.
    Coordinates always come from privacy-safe discovery_point / public map.
    """
    from app.events.maps import resolve_public_map

    reveal = can_reveal_full_address(event, access="public")
    payload = resolve_public_map(event, reveal_exact=reveal)
    mode: MapMode = map_mode or payload.get("location_map_mode") or "none"  # type: ignore[assignment]
    lat_s = payload.get("map_latitude")
    lng_s = payload.get("map_longitude")

    min_price = _min_public_price(event)
    label = public_location_label(event) or event.public_location_label
    privacy_msg = location_privacy_message(event, reveal_full=reveal)
    approx = mode == "approximate"
    dist_rounded = None
    dist_label = None
    if distance_km is not None:
        dist_rounded = round(distance_km, 1 if distance_km < 10 else 0)
        dist_label = format_distance_km(distance_km, approximate=approx)

    visibility = getattr(event, "location_visibility", None) or "full_public"

    return {
        "id": event.id,
        "slug": event.slug,
        "title": event.title,
        "banner_url": event.banner_url or event.mobile_banner_url,
        "start_datetime": event.start_datetime,
        "end_datetime": event.end_datetime,
        "price_label": _price_label(min_price),
        "min_price": float(min_price) if min_price is not None else None,
        "is_free": min_price is not None and min_price == 0,
        "category_name": event.category.name if event.category is not None else None,
        "category_slug": event.category.slug if event.category is not None else None,
        "host_display_name": (
            event.host.display_name if event.host is not None else None
        ),
        "public_location_label": label,
        "city": event.city,
        "area": getattr(event, "area", None),
        # Privacy-safe map coords only (never raw hidden venue lat/lng).
        "latitude": lat_s,
        "longitude": lng_s,
        "location_visibility": visibility,
        "location_map_mode": mode,
        "location_privacy_message": privacy_msg,
        "distance_km": dist_rounded,
        "distance_label": dist_label,
        "distance_is_approximate": approx if distance_km is not None else False,
    }


def list_map_events(
    db: Session,
    *,
    north: float,
    south: float,
    east: float,
    west: float,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
    city: str | None = None,
    area: str | None = None,
    category_slug: str | None = None,
    on_date: date | None = None,
    price: MapPriceFilter = "any",
    host_id: UUID | None = None,
    limit: int = 100,
) -> tuple[list[dict], int]:
    """
    Return compact map pins inside bounds (and optional radius), privacy-safe.

    Events without a public discovery coordinate are excluded (cannot plot).
    Unlisted / private / invite-only events never appear (list_published_events).
    """
    validate_bounds(north=north, south=south, east=east, west=west)
    if lat is not None and lng is not None:
        validate_lat_lng(lat, lng)

    limit = max(1, min(int(limit or 100), MAX_MAP_RESULTS))

    rows = list_published_events(
        db,
        category_slug=category_slug,
        city_slug=city,
        sort=None,
    )

    if host_id is not None:
        rows = [e for e in rows if e.host_id == host_id]

    area_norm = (area or "").strip().lower()
    scored: list[tuple[Event, float | None, MapMode]] = []

    for event in rows:
        if area_norm:
            event_area = (getattr(event, "area", None) or "").strip().lower()
            if event_area != area_norm and area_norm not in event_area:
                continue

        if on_date is not None:
            start = event.start_datetime
            if start is None:
                continue
            local = start.date() if hasattr(start, "date") else None
            if local != on_date:
                continue

        min_price = _min_public_price(event)
        if price == "free" and (min_price is None or min_price != 0):
            continue
        if price == "paid" and (min_price is None or min_price == 0):
            continue

        point = discovery_point(event)
        if point is None:
            continue
        elat, elng, mode = point
        if not point_in_bounds(
            elat, elng, north=north, south=south, east=east, west=west
        ):
            continue

        dist: float | None = None
        if lat is not None and lng is not None:
            dist = haversine_km(lat, lng, elat, elng)
            if radius_km is not None and dist > float(radius_km):
                continue

        scored.append((event, dist, mode))

    now = datetime.now(UTC)

    def sort_key(item: tuple[Event, float | None, MapMode]):
        event, dist, _mode = item
        start = event.start_datetime or now
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        featured_rank = 0 if event.featured else 1
        # Prefer closer when user location present; else soonest.
        if dist is not None:
            return (0, dist, start.timestamp(), featured_rank)
        return (1, start.timestamp(), featured_rank, 0)

    scored.sort(key=sort_key)
    total = len(scored)
    page = scored[:limit]
    items = [
        compact_map_event(event, distance_km=dist, map_mode=mode)
        for event, dist, mode in page
    ]
    return items, total
