"""Privacy-safe map coordinate helpers for events."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from app.events.models import Event

# Coarse city/area centroids for approximate maps when hosts omit approximate coords.
CITY_CENTROIDS: dict[str, tuple[str, str]] = {
    "lagos": ("6.5244", "3.3792"),
    "lekki": ("6.4698", "3.5852"),
    "victoria island": ("6.4281", "3.4219"),
    "ikeja": ("6.6018", "3.3515"),
    "yaba": ("6.5095", "3.3711"),
    "mainland": ("6.5480", "3.3620"),
    "ibadan": ("7.3775", "3.9470"),
    "abuja": ("9.0765", "7.3986"),
    "akure": ("7.2526", "5.2103"),
}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def city_centroid(city: str | None, area: str | None = None) -> tuple[str, str] | None:
    for key in (_norm(area), _norm(city)):
        if key and key in CITY_CENTROIDS:
            return CITY_CENTROIDS[key]
    return None


def maps_open_url(*, lat: str, lng: str, label: str | None = None) -> str:
    q = f"{lat},{lng}"
    if label:
        q = f"{label}@{lat},{lng}"
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(q)}"


def resolve_public_map(
    event: Event,
    *,
    reveal_exact: bool,
) -> dict[str, Any]:
    """Return map payload fields safe for the given reveal state."""
    visibility = getattr(event, "location_visibility", None) or "full_public"
    if visibility == "online_only":
        return {
            "location_map_mode": "none",
            "map_latitude": None,
            "map_longitude": None,
            "map_label": "Online Event",
            "map_open_url": None,
        }

    exact_lat = getattr(event, "latitude", None) or (
        event.venue.latitude if event.venue else None
    )
    exact_lng = getattr(event, "longitude", None) or (
        event.venue.longitude if event.venue else None
    )
    approx_lat = getattr(event, "approximate_latitude", None)
    approx_lng = getattr(event, "approximate_longitude", None)
    approx_label = getattr(event, "approximate_map_label", None) or getattr(
        event, "public_location_label", None
    )

    if reveal_exact and exact_lat and exact_lng:
        label = event.venue_name or event.public_location_label or event.city
        share = getattr(event, "google_maps_share_url", None)
        place = getattr(event, "google_maps_place_url", None)
        open_url = share or place or maps_open_url(lat=exact_lat, lng=exact_lng, label=label)
        return {
            "location_map_mode": "exact",
            "map_latitude": exact_lat,
            "map_longitude": exact_lng,
            "map_label": label,
            "map_open_url": open_url,
        }

    # Approximate path for area_only / hidden modes (and full_public without coords).
    lat, lng = approx_lat, approx_lng
    if not (lat and lng):
        centroid = city_centroid(event.city, getattr(event, "area", None))
        if centroid:
            lat, lng = centroid
    if lat and lng:
        label = approx_label or event.public_location_label or event.city or "Area"
        # Area search only — never attach private street or exact venue pin.
        open_url = (
            f"https://www.google.com/maps/search/?api=1&query={quote_plus(label)}"
            if label
            else None
        )
        return {
            "location_map_mode": "approximate",
            "map_latitude": lat,
            "map_longitude": lng,
            "map_label": label,
            "map_open_url": open_url,
        }

    return {
        "location_map_mode": "none",
        "map_latitude": None,
        "map_longitude": None,
        "map_label": approx_label or event.public_location_label or event.city,
        "map_open_url": None,
    }
