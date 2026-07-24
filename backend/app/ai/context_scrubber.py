"""Strip secrets and private fields before any AI provider call."""

from __future__ import annotations

import re
from typing import Any

# Keys that must never reach a provider (case-insensitive match on dict keys)
FORBIDDEN_CONTEXT_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "passwd",
        "secret",
        "secrets",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "ai_api_key",
        "authorization",
        "paystack",
        "paystack_secret",
        "paystack_key",
        "provider_payload",
        "provider_reference",
        "authorization_code",
        "card",
        "pan",
        "cvv",
        "qr",
        "qr_payload",
        "qr_secret",
        "qr_token",
        "jti",
        "device_binding",
        "ticket_secret",
        "signed_payload",
        "vault_body",
        "vault_content",
        "locked_body",
        "invite_code",
        "private_message",
        "message_body",
        "messages",
        "admin_note",
        "admin_notes",
        "internal_note",
        "internal_notes",
        "crm_note",
        "crm_notes",
        "buyer_email",
        "buyer_phone",
        "email",
        "phone",
        "whatsapp",
        "shipping_address",
        "street_address",
        "private_address",
        "hidden_address",
        "venue_address",
        "address",
        "address_line",
        "lat",
        "lng",
        "latitude",
        "longitude",
        "gps",
        "online_event_url",
        "join_url",
        "private_join_url",
        "fulfillment_notes",
        "shipping_notes",
        "order_details",
        "order_id",
        "payment_ref",
    }
)

# Substring patterns that imply secret-ish values in free text
_SECRETISH_VALUE = re.compile(
    r"(?i)(password\s*[:=]|api[_ -]?key\s*[:=]|bearer\s+[a-z0-9._\-]+|"
    r"sk-[a-z0-9]{10,}|paystack[_-]?(secret|key)|authorization:\s*\S+)"
)

# Location privacy modes that must not expose venue name to the model
_VENUE_HIDDEN_MODES = frozenset(
    {
        "area_only",
        "hidden_until_payment",
        "hidden_until_24h_before",
        "hidden_until_manual_approval",
        "online_only",
    }
)

# Safe allowlist for Event Studio / host.event.* generation
EVENT_STUDIO_SAFE_KEYS = frozenset(
    {
        "title",
        "notes",
        "city",
        "area",
        "category",
        "vibe",
        "date",
        "capacity",
        "ticket_tiers",
        "short_tagline",
        "venue",  # only if privacy allows — scrubber clears otherwise
        "location_visibility",
    }
)

# Safe allowlist for Merch Studio / host.merch.* generation
MERCH_STUDIO_SAFE_KEYS = frozenset(
    {
        "title",
        "name",
        "notes",
        "description",
        "short_description",
        "product_type",
        "merch_kind",
        "marketplace_kind",
        "event_title",
        "event_category",
        "event_city",
        "event_date",
        "host_name",
        "audience_label",
        "fulfillment_label",
        "limited_stock",
        "catalog_categories",
        "existing_category",
        "existing_tags",
        "location_visibility",
    }
)


def _key_forbidden(key: str) -> bool:
    k = key.strip().lower().replace("-", "_")
    if k in FORBIDDEN_CONTEXT_KEYS:
        return True
    for bad in FORBIDDEN_CONTEXT_KEYS:
        if bad in k and bad not in {"qr"}:  # avoid over-matching short tokens in normal words
            return True
        if bad == "qr" and (k == "qr" or k.startswith("qr_") or k.endswith("_qr")):
            return True
    return False


def scrub_value(value: Any, *, max_len: int = 2000) -> str:
    """Normalize a single context value; blank out secret-looking strings."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if _SECRETISH_VALUE.search(text):
        return "[redacted]"
    if len(text) > max_len:
        return text[:max_len]
    return text


def venue_allowed_for_ai(location_visibility: str | None) -> bool:
    mode = (location_visibility or "full_public").strip().lower()
    return mode == "full_public"


def scrub_context(
    raw: dict[str, Any],
    *,
    location_visibility: str | None = None,
    allowlist: frozenset[str] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Return scrubbed string context and list of redaction actions applied."""
    applied: list[str] = []
    visibility = location_visibility
    if visibility is None and "location_visibility" in raw:
        visibility = str(raw.get("location_visibility") or "")

    out: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            applied.append("drop_non_string_key")
            continue
        if _key_forbidden(key):
            applied.append(f"drop_forbidden:{key}")
            continue
        if allowlist is not None and key not in allowlist:
            applied.append(f"drop_not_allowlisted:{key}")
            continue

        scrubbed = scrub_value(value)
        if scrubbed == "[redacted]":
            applied.append(f"redact_value:{key}")
            continue
        out[key] = scrubbed

    # Venue / address privacy
    if not venue_allowed_for_ai(visibility):
        if out.get("venue"):
            out["venue"] = ""
            applied.append("clear_venue_non_public_location")
        for addr_key in ("address", "venue_address", "private_address", "street"):
            if addr_key in out:
                out.pop(addr_key, None)
                applied.append(f"clear_{addr_key}")
        mode = (visibility or "").strip().lower()
        if mode in _VENUE_HIDDEN_MODES:
            applied.append(f"location_privacy:{mode or 'unknown'}")

    # Never keep location_visibility as model content beyond scrubbing decisions
    out.pop("location_visibility", None)

    return out, applied


def scrub_event_studio_context(raw: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Allowlisted scrubber for host.event.title / host.event.description."""
    visibility = str(raw.get("location_visibility") or "full_public")
    return scrub_context(
        raw,
        location_visibility=visibility,
        allowlist=EVENT_STUDIO_SAFE_KEYS,
    )


def scrub_merch_studio_context(raw: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Allowlisted scrubber for host.merch.* features."""
    visibility = str(raw.get("location_visibility") or "full_public")
    scrubbed, applied = scrub_context(
        raw,
        location_visibility=visibility,
        allowlist=MERCH_STUDIO_SAFE_KEYS,
    )
    # Normalize title/name alias
    if scrubbed.get("name") and not scrubbed.get("title"):
        scrubbed["title"] = scrubbed["name"]
    if scrubbed.get("marketplace_kind") and not scrubbed.get("merch_kind"):
        scrubbed["merch_kind"] = scrubbed["marketplace_kind"]
    return scrubbed, applied


def scrub_prompt_text(text: str) -> str:
    """Final pass on assembled prompts — blank obvious secret patterns."""
    if not text:
        return ""
    return _SECRETISH_VALUE.sub("[redacted]", text)
