"""Sanitize messaging WebSocket/Redis fan-out payloads.

Never publish payment/order/private venue/shipping/contact fields.
Defense-in-depth on top of participant-scoped serializers.
"""

from __future__ import annotations

from typing import Any

from app.messaging.attachment_privacy import strip_forbidden_attachment_fields

# Exact key denylist (case-insensitive).
_FORBIDDEN_KEYS = frozenset(
    {
        "email",
        "phone",
        "phone_number",
        "mobile",
        "whatsapp",
        "shipping_address",
        "shipping_line1",
        "shipping_line2",
        "billing_address",
        "address_line1",
        "address_line2",
        "street_address",
        "exact_address",
        "private_venue",
        "private_location",
        "hidden_venue",
        "venue_address",
        "order_id",
        "related_order_id",
        "related_ticket_id",
        "payment_id",
        "paystack_reference",
        "card_last4",
        "bank_account",
        "account_number",
        "account_name",
        "latitude",
        "longitude",
        "exact_lat",
        "exact_lng",
        "password",
        "password_hash",
        "access_token",
        "refresh_token",
        "storage_key",
        "checksum",
        "checksum_sha256",
        "file_path",
        "filepath",
        "local_path",
        "absolute_path",
        "media_root",
        "rejection_reason",
        "uploader_user_id",
        "safe_filename",
        "exif",
        "gps",
    }
)

# Substring matches on key names (case-insensitive).
_FORBIDDEN_SUBSTR = (
    "email",
    "phone",
    "whatsapp",
    "shipping",
    "billing_address",
    "order_id",
    "payment_",
    "paystack",
    "private_venue",
    "hidden_venue",
    "street",
    "password",
    "secret",
    "storage_key",
    "checksum",
    "file_path",
    "uploader_user",
)


def _key_blocked(key: str) -> bool:
    kl = key.lower()
    if kl in _FORBIDDEN_KEYS:
        return True
    return any(part in kl for part in _FORBIDDEN_SUBSTR)


def sanitize_event_payload(value: Any) -> Any:
    """Return a deep-copied payload with forbidden keys stripped."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str) or _key_blocked(key):
                continue
            out[key] = sanitize_event_payload(child)
        # Clip attachment-shaped objects to the public allowlist.
        return strip_forbidden_attachment_fields(out)
    if isinstance(value, list):
        return [sanitize_event_payload(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_event_payload(item) for item in value]
    return value
