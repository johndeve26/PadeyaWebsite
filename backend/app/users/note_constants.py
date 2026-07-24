"""Admin internal note catalog — types for user detail moderation."""

from __future__ import annotations

NOTE_TYPES: tuple[str, ...] = (
    "general",
    "support",
    "fraud",
    "moderation",
    "finance",
    "security",
)
NOTE_TYPE_SET = frozenset(NOTE_TYPES)

NOTE_TYPE_LABELS: dict[str, str] = {
    "general": "General",
    "support": "Support",
    "fraud": "Fraud",
    "moderation": "Moderation",
    "finance": "Finance",
    "security": "Security",
}

# Reject bodies that look like they contain secrets (never store these in notes).
NOTE_SECRET_HINTS = (
    "password_hash",
    "password:",
    "passwd:",
    "pwd:",
    "refresh_token",
    "access_token",
    "bearer ",
    "authorization:",
    "qr_secret",
    "qr_payload",
    "raw_payload",
    "provider_payload",
    "paystack_secret",
    "stripe_secret",
    "sk_live",
    "sk_test",
    "pk_live_secret",
)
