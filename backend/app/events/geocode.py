"""Optional server-side Google Geocoding for admin re-geocode tools."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.runtime_settings.service import runtime_settings_service


def google_places_api_key(db: Session | None = None) -> str:
    """Server-only Geocoding/Places key from Admin → Integrations (never .env)."""
    return (
        runtime_settings_service.get_runtime_secret("google_places_api_key", db=db) or ""
    ).strip()


def geocode_address(address: str, db: Session | None = None) -> dict[str, Any]:
    """
    Geocode a free-text address via Google Geocoding API.
    Uses admin runtime_settings key. Raises 400/503 on failure.
    """
    key = google_places_api_key(db)
    if not key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google Places / Geocoding is not configured. "
                "Set the API key in Admin → Integrations."
            ),
        )
    query = (address or "").strip()
    if len(query) < 3:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Address is required to geocode."
        )

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(url, params={"address": query, "key": key})
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Geocoding request failed.",
        ) from exc

    status_val = payload.get("status")
    results = payload.get("results") or []
    if status_val != "OK" or not results:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Could not geocode address ({status_val or 'UNKNOWN'}).",
        )

    top = results[0]
    loc = (top.get("geometry") or {}).get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")
    if lat is None or lng is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Geocode result missing coordinates."
        )

    components = top.get("address_components") or []

    def _comp(*types: str) -> str | None:
        for c in components:
            if any(t in (c.get("types") or []) for t in types):
                return c.get("long_name")
        return None

    return {
        "latitude": str(lat),
        "longitude": str(lng),
        "formatted_address": top.get("formatted_address"),
        "place_id": top.get("place_id"),
        "city": _comp("locality", "postal_town") or _comp("administrative_area_level_2"),
        "state": _comp("administrative_area_level_1"),
        "country": _comp("country"),
        "area": _comp("neighborhood", "sublocality", "sublocality_level_1"),
        "postcode": _comp("postal_code"),
    }
