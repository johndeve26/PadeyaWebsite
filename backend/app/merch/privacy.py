"""Pickup / location privacy for event merch."""

from __future__ import annotations

from app.events.models import Event
from app.events.privacy import can_reveal_full_address, public_location_label
from app.merch.content_safety import label_looks_like_street_address
from app.merch.models import EventMerchProduct

_PRIVATE_VISIBILITIES = frozenset(
    {
        "area_only",
        "online_only",
        "hidden_until_payment",
        "hidden_until_24h_before",
        "hidden_until_manual_approval",
    }
)

SAFE_PUBLIC_PICKUP_FALLBACK = "Pickup at the event — details after purchase"


def event_location_is_private(event: Event | None) -> bool:
    if event is None:
        return True
    visibility = getattr(event, "location_visibility", None) or "full_public"
    return visibility in _PRIVATE_VISIBILITIES


def public_pickup_fields(
    product: EventMerchProduct, event: Event | None
) -> dict[str, str | None]:
    """Safe fields for public catalog / pre-purchase (never leak private venue)."""
    label = (getattr(product, "pickup_location_label", None) or "").strip() or None
    window = (getattr(product, "pickup_time_window", None) or "").strip() or None
    event_address = getattr(event, "address", None) if event else None

    if event is not None and not event_location_is_private(event):
        # Public venue events may show stand label + instructions, never host notes.
        if label_looks_like_street_address(label, event_address=event_address):
            # Prefer stand-safe copy; do not echo event street into merch catalog.
            label = public_location_label(event) or None
        return {
            "pickup_location_label": label,
            "pickup_time_window": window,
            "pickup_instructions": (product.pickup_instructions or "").strip() or None,
            "fulfillment_notes": None,
        }

    # Restricted event location: scrub street-like labels and detailed instructions.
    safe_label = label
    if label_looks_like_street_address(safe_label, event_address=event_address):
        safe_label = None
    if not safe_label and event is not None:
        safe_label = public_location_label(event)
        if safe_label and "after" in safe_label.lower():
            safe_label = None

    return {
        "pickup_location_label": safe_label,
        "pickup_time_window": window,
        "pickup_instructions": (
            None if safe_label else SAFE_PUBLIC_PICKUP_FALLBACK
        ),
        "fulfillment_notes": None,
    }


def buyer_pickup_fields(
    product: EventMerchProduct | None,
    event: Event | None,
    *,
    snapshots: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Post-purchase pickup details. Still respects event address reveal rules.

    Fulfillment notes stay host/desk-only — never returned here.
    """
    snaps = snapshots or {}
    instructions = snaps.get("pickup_instructions") or (
        (product.pickup_instructions or "").strip() if product else None
    )
    label = snaps.get("pickup_location_label") or (
        (getattr(product, "pickup_location_label", None) or "").strip() if product else None
    )
    window = snaps.get("pickup_time_window") or (
        (getattr(product, "pickup_time_window", None) or "").strip() if product else None
    )
    event_address = getattr(event, "address", None) if event else None

    if event is not None and not can_reveal_full_address(event, access="buyer"):
        # Purchased, but street address still gated by event rules.
        if label_looks_like_street_address(label, event_address=event_address):
            label = public_location_label(event) or None
        if not label:
            label = public_location_label(event)
        if instructions and label_looks_like_street_address(
            instructions, event_address=event_address
        ):
            instructions = SAFE_PUBLIC_PICKUP_FALLBACK
        if not instructions:
            instructions = SAFE_PUBLIC_PICKUP_FALLBACK

    return {
        "pickup_location_label": label or None,
        "pickup_time_window": window or None,
        "pickup_instructions": instructions or None,
        "fulfillment_notes": None,
    }
