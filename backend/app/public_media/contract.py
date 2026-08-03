"""Public-safe media response contract (never exposes source keys)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.public_media.roles import VariantType


def variant_public_dict(
    *,
    url: str,
    width: int,
    height: int,
) -> dict[str, Any]:
    return {"url": url, "width": width, "height": height}


def build_public_media_payload(
    *,
    asset_id: UUID | str,
    role: str,
    variants: dict[str, dict[str, Any]],
    alt: str | None = None,
    focal_x: float | None = None,
    focal_y: float | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Structured public media object + convenience URL fields.

    ``url`` always means the standard display variant (never unrestricted source).
    """
    display = variants.get(VariantType.DISPLAY.value) or variants.get("display")
    card = variants.get(VariantType.CARD.value) or variants.get("card")
    thumb = variants.get(VariantType.THUMBNAIL.value) or variants.get("thumbnail")
    full = variants.get(VariantType.FULL.value) or variants.get("full")
    og = variants.get(VariantType.OG.value) or variants.get("og")

    display_url = (display or card or thumb or full or {}).get("url")
    payload: dict[str, Any] = {
        "id": str(asset_id),
        "role": role,
        "alt": alt,
        "focal_x": focal_x,
        "focal_y": focal_y,
        "width": width or (display or {}).get("width"),
        "height": height or (display or {}).get("height"),
        "variants": variants,
        # Convenience — keep FE/legacy callers working.
        "url": display_url,
        "thumbnail_url": (thumb or {}).get("url"),
        "card_url": (card or display or {}).get("url"),
        "display_url": display_url,
        "full_url": (full or display or {}).get("url"),
        "og_url": (og or {}).get("url"),
    }
    return payload


FALLBACK_ORDER = {
    "thumbnail": ("thumbnail", "card", "display", "full", "legacy"),
    "card": ("card", "display", "thumbnail", "full", "legacy"),
    "display": ("display", "full", "card", "thumbnail", "legacy"),
    "full": ("full", "display", "card", "legacy"),
    "og": ("og", "display", "card", "legacy"),
}


def select_variant_url(
    media: dict[str, Any] | None,
    *,
    intent: str,
    legacy_url: str | None = None,
) -> str | None:
    """Pick the best public URL for an intent with legacy fallback."""
    if not media and not legacy_url:
        return None
    media = media or {}
    variants = media.get("variants") if isinstance(media.get("variants"), dict) else {}
    order = FALLBACK_ORDER.get(intent, FALLBACK_ORDER["display"])
    for key in order:
        if key == "legacy":
            return (
                legacy_url
                or media.get("url")
                or media.get("display_url")
                or media.get("legacy_url")
            )
        # Convenience fields
        convenience = {
            "thumbnail": media.get("thumbnail_url"),
            "card": media.get("card_url"),
            "display": media.get("display_url") or media.get("url"),
            "full": media.get("full_url"),
            "og": media.get("og_url"),
        }.get(key)
        if convenience:
            return convenience
        entry = variants.get(key)
        if isinstance(entry, dict) and entry.get("url"):
            return entry["url"]
        if isinstance(entry, str) and entry:
            return entry
    return legacy_url
