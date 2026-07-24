"""Location and online-link privacy rules for events."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from app.events.maps import resolve_public_map
from app.events.models import Event

AccessLevel = Literal["public", "buyer", "host", "admin"]


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def timing_allows_reveal(event: Event, rule: str | None, *, now: datetime | None = None) -> bool:
    """Whether reveal timing alone permits sharing restricted details."""
    current = _aware(now) or datetime.now(UTC)
    start = _aware(event.start_datetime)
    rule = rule or getattr(event, "reveal_timing", None) or "immediately"

    if rule == "immediately":
        return True
    if rule == "after_payment":
        return False
    if rule == "manual_approval":
        return False
    if rule == "twenty_four_hours_before":
        if start is None:
            return False
        return current >= start - timedelta(hours=24)
    if rule == "event_day":
        if start is None:
            return False
        return current.date() >= start.date()
    return False


def can_reveal_full_address(
    event: Event,
    *,
    access: AccessLevel = "public",
    now: datetime | None = None,
) -> bool:
    if access in {"host", "admin"}:
        return True

    visibility = getattr(event, "location_visibility", None) or "full_public"
    if visibility == "full_public":
        return True
    if visibility == "online_only":
        return False
    if visibility == "area_only":
        return False
    if visibility == "hidden_until_manual_approval":
        return access == "buyer" and timing_allows_reveal(
            event, "manual_approval", now=now
        )
    if visibility == "hidden_until_24h_before":
        return timing_allows_reveal(event, "twenty_four_hours_before", now=now) or (
            access == "buyer"
            and timing_allows_reveal(event, getattr(event, "reveal_timing", None), now=now)
        )
    if visibility == "hidden_until_payment":
        if access != "buyer":
            return False
        # Buyers with confirmed access always get the address after purchase.
        return True

    # Fallback: buyer + reveal timing
    if access == "buyer":
        rule = getattr(event, "reveal_timing", None) or "after_payment"
        if rule == "after_payment":
            return True
        return timing_allows_reveal(event, rule, now=now)
    return False


def can_reveal_online_url(
    event: Event,
    *,
    access: AccessLevel = "public",
    now: datetime | None = None,
) -> bool:
    if access in {"host", "admin"}:
        return True
    rule = getattr(event, "online_url_reveal_rule", None) or "after_payment"
    if rule == "immediately":
        return True
    if access == "buyer":
        if rule == "after_payment":
            return True
        return timing_allows_reveal(event, rule, now=now)
    return timing_allows_reveal(event, rule, now=now) and rule not in {
        "after_payment",
        "manual_approval",
    }


def public_location_label(event: Event) -> str | None:
    label = getattr(event, "public_location_label", None)
    if label:
        return label
    visibility = getattr(event, "location_visibility", None) or "full_public"
    city = event.city
    state = event.state
    if visibility == "area_only":
        parts = [p for p in (city, state) if p]
        return ", ".join(parts) if parts else "Area shared after booking"
    if visibility == "online_only":
        return "Online Event"
    if visibility in {
        "hidden_until_payment",
        "hidden_until_24h_before",
        "hidden_until_manual_approval",
    }:
        if city and state:
            return f"{city}, {state} — exact venue revealed later"
        return "Secret location — details shared with approved attendees"
    return None


def location_privacy_message(event: Event, *, reveal_full: bool) -> str | None:
    if reveal_full:
        return None
    visibility = getattr(event, "location_visibility", None) or "full_public"
    note = getattr(event, "reveal_note", None)
    if note:
        return note
    messages = {
        "area_only": "Exact venue revealed after purchase.",
        "hidden_until_payment": "Exact venue revealed after purchase.",
        "hidden_until_24h_before": "Exact venue revealed 24 hours before the event.",
        "hidden_until_manual_approval": "Full details sent to approved attendees.",
        "online_only": "Online link revealed after payment.",
    }
    return messages.get(visibility)


def apply_location_privacy(
    event: Event,
    data: dict[str, Any],
    *,
    access: AccessLevel = "public",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Mutate serialized event dict to respect location privacy."""
    reveal = can_reveal_full_address(event, access=access, now=now)
    reveal_url = can_reveal_online_url(event, access=access, now=now)
    label = public_location_label(event)
    message = location_privacy_message(event, reveal_full=reveal)

    data["location_visibility"] = getattr(event, "location_visibility", None) or "full_public"
    data["reveal_timing"] = getattr(event, "reveal_timing", None) or "immediately"
    data["reveal_note"] = getattr(event, "reveal_note", None)
    data["public_location_label"] = label
    data["location_address_revealed"] = reveal
    data["location_privacy_message"] = message
    data["country"] = getattr(event, "country", None) or (
        getattr(event.venue, "country", None) if event.venue else None
    )
    data["area"] = getattr(event, "area", None)
    data["approximate_latitude"] = getattr(event, "approximate_latitude", None)
    data["approximate_longitude"] = getattr(event, "approximate_longitude", None)
    data["approximate_map_label"] = getattr(event, "approximate_map_label", None)

    if reveal:
        data["latitude"] = getattr(event, "latitude", None) or (
            event.venue.latitude if event.venue else None
        )
        data["longitude"] = getattr(event, "longitude", None) or (
            event.venue.longitude if event.venue else None
        )
        data["postcode"] = getattr(event, "postcode", None)
        data["google_maps_share_url"] = getattr(event, "google_maps_share_url", None)
        data["google_maps_place_url"] = getattr(event, "google_maps_place_url", None)
    else:
        data["address"] = None
        data["latitude"] = None
        data["longitude"] = None
        data["postcode"] = None
        data["google_maps_share_url"] = None
        data["google_maps_place_url"] = None
        if data.get("venue") is not None:
            venue = data["venue"]
            if hasattr(venue, "__dict__") and not isinstance(venue, dict):
                venue_dict = {
                    "id": getattr(venue, "id", None),
                    "name": label or getattr(venue, "name", None) or event.venue_name,
                    "address": None,
                    "city": event.city if data["location_visibility"] == "area_only" else None,
                    "state": event.state if data["location_visibility"] == "area_only" else None,
                    "country": getattr(venue, "country", None),
                    "latitude": None,
                    "longitude": None,
                    "notes": None,
                }
                data["venue"] = venue_dict
            elif isinstance(venue, dict):
                venue = {**venue}
                venue["address"] = None
                venue["latitude"] = None
                venue["longitude"] = None
                venue["notes"] = None
                if data["location_visibility"] != "area_only":
                    venue["city"] = None
                    venue["state"] = None
                venue["name"] = label or venue.get("name") or event.venue_name
                data["venue"] = venue
        # Prefer public label over exact venue name when hidden.
        if label and data["location_visibility"] != "full_public":
            if data["location_visibility"] in {
                "hidden_until_payment",
                "hidden_until_24h_before",
                "hidden_until_manual_approval",
                "online_only",
            }:
                data["venue_name"] = label
            elif data["location_visibility"] == "area_only":
                # Keep city/state for discovery; never expose street-level venue name
                # when hosts stored a private venue under venue_name.
                data["venue_name"] = label
                data["address"] = None

    map_payload = resolve_public_map(event, reveal_exact=reveal)
    data.update(map_payload)

    # Discovery may still include taxonomy location (country/state/city/area).
    # Never include raw street address on the taxonomy node payload.
    if access == "public" and data.get("location") and not reveal:
        loc = data["location"]
        if isinstance(loc, dict):
            ancestors = loc.get("ancestors") or []
            scrubbed_ancestors = [
                {
                    "slug": a.get("slug"),
                    "name": a.get("name"),
                    "kind": a.get("kind"),
                }
                for a in ancestors
                if isinstance(a, dict)
            ]
            data["location"] = {
                "slug": loc.get("slug"),
                "name": loc.get("name"),
                "kind": loc.get("kind"),
                "ancestors": scrubbed_ancestors,
            }

    if not reveal_url:
        data["online_event_url"] = None
    else:
        data["online_event_url"] = getattr(event, "online_event_url", None)

    # Never leak private address into SEO / social fields for public viewers.
    if access == "public" and not reveal:
        label_safe = label or "secret location"
        addr = (event.address or "").strip()
        fragments = [addr] if addr else []
        if addr and "," in addr:
            first = addr.split(",", 1)[0].strip()
            if len(first) >= 6:
                fragments.append(first)

        def _scrub_text(value: str) -> str:
            next_value = value
            for fragment in fragments:
                if fragment and fragment in next_value:
                    next_value = next_value.replace(fragment, label_safe)
            return next_value

        if fragments:
            for key in (
                "seo_title",
                "seo_description",
                "social_share_title",
                "social_share_description",
            ):
                value = data.get(key)
                if isinstance(value, str):
                    data[key] = _scrub_text(value)
            for key in ("hashtags", "discoverable_keywords"):
                value = data.get(key)
                if isinstance(value, list):
                    data[key] = [
                        _scrub_text(item) if isinstance(item, str) else item
                        for item in value
                    ]
                elif isinstance(value, str):
                    data[key] = _scrub_text(value)

    return data
