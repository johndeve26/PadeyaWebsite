"""Support center constants — categories, statuses, priorities."""

from __future__ import annotations

CATEGORIES: tuple[str, ...] = (
    "account_login",
    "tickets_orders",
    "payments_refunds",
    "event_issue",
    "host_issue",
    "merch",
    "fan_connect",
    "messaging_abuse",
    "sponsorship",
    "ambassador",
    "technical",
    "other",
)

CATEGORY_LABELS: dict[str, str] = {
    "account_login": "Account / login",
    "tickets_orders": "Tickets / orders",
    "payments_refunds": "Payments / refunds",
    "event_issue": "Event issue",
    "host_issue": "Host issue",
    "merch": "Merch",
    "fan_connect": "Fan Connect",
    "messaging_abuse": "Messaging / report abuse",
    "sponsorship": "Sponsorship",
    "ambassador": "Ambassador",
    "technical": "Technical issue",
    "other": "Other",
}

STATUSES: tuple[str, ...] = (
    "open",
    "pending",
    "waiting_on_user",
    "escalated",
    "resolved",
    "closed",
    "archived",
)

PRIORITIES: tuple[str, ...] = ("low", "normal", "high", "urgent")

REQUESTER_CONTEXTS: tuple[str, ...] = ("fan", "host", "visitor", "admin")

# Max public submissions per IP per hour
PUBLIC_RATE_LIMIT = 5
PUBLIC_RATE_WINDOW_SECONDS = 3600

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_ATTACHMENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
    }
)
