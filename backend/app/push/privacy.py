"""Push privacy — never put sensitive fields on the wire or in outbox context.

Forbidden in push payloads / context:
- hidden venue / private event location
- payment or order references
- full pickup / entry codes
- shipping address, phone, email
- private chat bodies or attachment URLs
- locked Vault content
- Fan Connect graph / private attendee lists
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

BRAND = "Pàdéyá"

# Only these keys may appear in push_events.data_json / render context.
ALLOWED_CONTEXT_KEYS = frozenset(
    {
        "kind",
        "notification_id",
        "action_url",
        "event_title",
        "product_name",
        "sender_name",
        "allow_message_preview",
        "name",
        "requester_name",
        "acceptor_name",
        "host_display_name",
        "member_name",
        "invite_method",
        "invited_username",
        "campaign_name",
        "sale_count",
        "icon_url",
        "badge_url",
        # Admin test / generic fallback only (still scrubbed as copy)
        "title",
        "body",
        "force_title",
        "force_body",
    }
)

BLOCKED_CONTEXT_KEY = re.compile(
    r"("
    r"venue|address|location|shipping|phone|email|password|secret|token|"
    r"payment|paystack|order_ref|order_id|reference|pickup_code|entry_code|"
    r"attendee|vault|attachment|file_url|download|graph|connection_ids|"
    r"message_body|chat_body|body_full|card|account"
    r")",
    re.I,
)

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
# Codes only: explicit code/pin/otp labels, or 6–12 char tokens that include a digit.
_CODE_RE = re.compile(
    r"\b(?:code|pin|otp)[:\s#-]*[A-Z0-9]{4,}\b"
    r"|\b(?=[A-Z0-9]*\d)[A-Z0-9]{6,12}\b",
    re.I,
)
_ORDER_RE = re.compile(r"\b(?:order|pay|txn|ref)[_-]?\w{6,}\b", re.I)
_PATH_RE = re.compile(r"/(?:vault|api|messages/attachments|media)/\S+", re.I)

GENERIC_MESSAGE_BODY = f"You have a new message on {BRAND}."
GENERIC_MESSAGE_TITLE = "New message"


def safe_action_url(value: str | None, *, default: str = "/dashboard/notifications") -> str:
    raw = (value or default).strip() or default
    if raw.startswith("javascript:") or raw.startswith("data:"):
        return default
    if raw.startswith("/"):
        path = raw.split("?", 1)[0]
        if re.search(r"/(vault|checkout)(/|$)", path, re.I):
            return default
        return raw[:300]
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"} and parsed.path:
        path = parsed.path
        if re.search(r"/(vault|checkout)(/|$)", path, re.I):
            return default
        return (path + (f"?{parsed.query}" if parsed.query else ""))[:300]
    return default


def sanitize_delivery_error(message: str | None, *, limit: int = 200) -> str | None:
    """Store provider errors without endpoints, emails, or secret-looking blobs."""
    if not message:
        return None
    text = scrub_push_copy(str(message), limit=limit * 2, strip_codes=True)
    # Drop absolute URLs / FCM-style paths that scrub may leave partially.
    text = re.sub(r"https?://\S+", "[endpoint]", text, flags=re.I)
    text = re.sub(r"/fcm/send/\S+", "[endpoint]", text, flags=re.I)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if not text:
        return "provider_error"
    return text[:limit]


def scrub_push_copy(
    text: str | None,
    *,
    limit: int = 240,
    strip_codes: bool = True,
) -> str:
    """Remove emails, phones, URLs, private paths, and (optionally) codes."""
    if not text:
        return ""
    out = str(text)
    out = _URL_RE.sub("", out)
    out = _EMAIL_RE.sub("", out)
    out = _PHONE_RE.sub("", out)
    out = _PATH_RE.sub("", out)
    out = _ORDER_RE.sub("", out)
    if strip_codes:
        out = _CODE_RE.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out[:limit]


_SOFT_CONTEXT_KEYS = frozenset(
    {
        "event_title",
        "product_name",
        "sender_name",
        "name",
        "requester_name",
        "acceptor_name",
        "host_display_name",
        "member_name",
        "invited_username",
    }
)


def sanitize_push_context(context: dict[str, Any] | None) -> dict[str, Any]:
    """Whitelist-only context for render + outbox storage."""
    if not context:
        return {}
    clean: dict[str, Any] = {}
    for key, value in context.items():
        if value is None:
            continue
        k = str(key)
        if k not in ALLOWED_CONTEXT_KEYS or BLOCKED_CONTEXT_KEY.search(k):
            continue
        if k == "action_url":
            clean[k] = safe_action_url(str(value))
            continue
        if k == "allow_message_preview":
            clean[k] = bool(value)
            continue
        if k in {"notification_id", "kind"}:
            clean[k] = str(value)[:80]
            continue
        if isinstance(value, (str, int, float, bool)):
            if isinstance(value, str):
                text = scrub_push_copy(
                    value,
                    limit=120,
                    strip_codes=k not in _SOFT_CONTEXT_KEYS,
                )
                if text == "":
                    continue
                clean[k] = text
            else:
                clean[k] = value
    return clean


def safe_sender_display_name(name: str | None) -> str | None:
    """Public display name for previews — never email/phone; max ~40 chars."""
    if not name:
        return None
    raw = scrub_push_copy(str(name).strip(), limit=40, strip_codes=True)
    if not raw or "@" in raw or raw.isdigit():
        return None
    # Keep up to three short tokens (e.g. "DJ Maze") — not full attendee lists.
    parts = [p for p in raw.split() if p][:3]
    if not parts or len(parts[0]) < 2:
        return None
    return " ".join(parts)[:40]


def message_push_copy(
    *,
    sender_name: str | None,
    allow_preview: bool,
    has_attachments: bool = False,
    fan_connect: bool = False,
) -> tuple[str, str]:
    """Messaging push copy — generic by default; optional safer name preview."""
    title = GENERIC_MESSAGE_TITLE
    if fan_connect and not allow_preview:
        return title, f"You have a new Fan Connect message on {BRAND}."
    if allow_preview:
        safe = safe_sender_display_name(sender_name)
        if safe:
            return title, f"{safe} sent you a message."
    if has_attachments and not allow_preview:
        return title, f"You have a new message with an attachment on {BRAND}."
    return title, GENERIC_MESSAGE_BODY
