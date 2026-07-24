"""Privacy guards for demo messaging copy and notifications.

Demo seed must never put contact/payment/private venue/Vault secrets in
message bodies or notification summaries. Conversations stay on Pàdéyá.
"""

from __future__ import annotations

# Substrings banned in demo message bodies / notification summaries (lowercase).
DEMO_MESSAGE_BANNED_SUBSTRINGS: tuple[str, ...] = (
    "whatsapp",
    "wa.me",
    "telegram",
    "signal me",
    "call me",
    "text me at",
    "my number is",
    "my phone is",
    "+234",
    "0803",
    "0901",
    "@gmail",
    "@yahoo",
    "@icloud",
    "@demo.",
    "email me",
    "send money",
    "bank transfer",
    "bank details",
    "account number",
    "wire me",
    "paystack",
    "flutterwave",
    "payment link",
    "http://",
    "https://",
    "www.",
    "ngn ",
    "₦",
    "order #",
    "order id",
    "payment id",
    "secret street",
    "private address",
    "locked vault",
    "locked demo body",
    "crm note",
    "password",
    "outside padeya",
    "off padeya",
    "move to whatsapp",
    "chat on whatsapp",
)

# Preferred safe phrases for ticket / Vault / check-in guidance.
SAFE_PLACEHOLDERS: tuple[str, ...] = (
    "Open your Pàdéyá ticket",
    "Check your dashboard",
    "Use your QR code at check-in",
    "Your ticket-holder Vault access should unlock",
    "Refresh your Vault page",
)


def assert_safe_demo_copy(text: str, *, context: str = "message") -> None:
    """Raise AssertionError if demo copy violates privacy rules."""
    low = (text or "").lower()
    for banned in DEMO_MESSAGE_BANNED_SUBSTRINGS:
        if banned in low:
            raise AssertionError(
                f"Unsafe demo {context}: contains {banned!r} — {text[:120]!r}"
            )
