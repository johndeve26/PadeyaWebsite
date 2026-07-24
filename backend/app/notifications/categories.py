"""In-app notification category filters for the notification center."""

from __future__ import annotations

from sqlalchemy import not_, or_

from app.messaging.models import InAppNotification

# Query ?category= values (UI labels map 1:1 except casing).
NOTIFICATION_CATEGORIES = frozenset(
    {
        "all",
        "tickets",
        "merch",
        "messages",
        "fan_connect",
        "host",
        "sponsor",
        "admin",
        "ambassador",
        "security",
    }
)

# kind prefix / exact rules per category (lowercase match on kind).
_CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "tickets": ("ticket.", "ticket_"),
    "merch": ("merch.", "merch_", "post_event_drop"),
    "messages": (
        "message.",
        "messaging.",
        "new_message",
        "message_request",
        "attachment_received",
    ),
    "fan_connect": ("fan_connect.", "fan_connect_", "fan_connect"),
    "host": ("host.", "host_", "review.", "review_", "vault.", "event."),
    "sponsor": ("sponsor.", "sponsor_"),
    "admin": ("admin.", "admin_", "account.", "appeal.", "support."),
    "ambassador": ("ambassador.", "ambassador_"),
    "security": ("security.", "security_"),
}


def normalize_category(category: str | None) -> str:
    key = (category or "all").strip().lower().replace("-", "_").replace(" ", "_")
    if key in {"fanconnect", "connect"}:
        return "fan_connect"
    if key not in NOTIFICATION_CATEGORIES:
        return "all"
    return key


def kind_matches_category(kind: str, category: str) -> bool:
    cat = normalize_category(category)
    if cat == "all":
        return True
    k = (kind or "").strip().lower()
    rules = _CATEGORY_RULES.get(cat, ())
    return any(k.startswith(r) or k == r.rstrip(".") for r in rules)


def message_kinds_clause():
    """Kinds that belong in the messaging inbox, not the notification bell."""
    return category_filter_clause("messages")


def inbox_only_kinds_clause():
    """In-app rows that belong under Messages, not Account → Notifications."""
    parts = []
    msg = message_kinds_clause()
    if msg is not None:
        parts.append(msg)
    parts.append(InAppNotification.kind == "fan_connect.message")
    return or_(*parts) if parts else None


def exclude_message_kinds_clause():
    """Exclude chat message kinds from default notification surfaces."""
    clause = inbox_only_kinds_clause()
    if clause is None:
        return None
    return not_(clause)


def category_filter_clause(category: str | None):
    """SQLAlchemy clause for InAppNotification.kind, or None for all."""
    cat = normalize_category(category)
    if cat == "all":
        return None
    rules = _CATEGORY_RULES.get(cat, ())
    if not rules:
        return None
    parts = []
    for rule in rules:
        if rule.endswith(".") or rule.endswith("_"):
            parts.append(InAppNotification.kind.ilike(f"{rule}%"))
        else:
            parts.append(InAppNotification.kind == rule)
            parts.append(InAppNotification.kind.ilike(f"{rule}.%"))
            parts.append(InAppNotification.kind.ilike(f"{rule}_%"))
    return or_(*parts) if parts else None
