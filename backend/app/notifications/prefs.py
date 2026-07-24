"""Push preference gating — separate from email channel.

Rules:
- Never send if ``push_enabled`` is off (master kill switch).
- Security category cannot be opted out; security bypasses marketing opt-out.
- Category toggles (including marketing/messages) default on; respect user opt-out.
- Marketing push still respects marketing unsubscribe.
- Message push is rate-limited per user.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.email.prefs import get_or_create_preferences

# kind / template prefix or exact → push preference key
KIND_TO_PUSH_PREF: dict[str, str] = {
    "security.": "push_security",
    "account.": "push_security",
    "system.maintenance": "push_security",
    "system.": "push_security",
    "team.security_alert": "push_security",
    "support.": "push_ticket_updates",
    "admin_support_ticket": "push_host_activity",
    "vault.": "push_marketing",
    "auth.": "push_security",
    "password.": "push_security",
    "marketing.": "push_marketing",
    "merch.cart_reminder": "push_marketing",
    "merch_cart_reminder": "push_marketing",
    "merch.post_event_drop": "push_marketing",
    "post_event_drop_available": "push_marketing",
    "merch.review_received": "push_reviews",
    "host_new_review": "push_reviews",
    "review.": "push_reviews",
    "review_": "push_reviews",
    "ticket_event_reminder": "push_event_reminders",
    "ticket.event_reminder": "push_event_reminders",
    "merch.": "push_merch_updates",
    "merch_": "push_merch_updates",
    "ticket.": "push_ticket_updates",
    "ticket_": "push_ticket_updates",
    "event.": "push_event_reminders",
    "message.": "push_messages",
    "messaging.": "push_messages",
    "new_message": "push_messages",
    "message_request": "push_messages",
    "attachment_received": "push_messages",
    "fan_connect_message": "push_fan_connect",
    "fan_connect.": "push_fan_connect",
    "fan_connect_": "push_fan_connect",
    "fan_connect": "push_fan_connect",
    "sponsor_inquiry_host_alert": "push_host_activity",
    "host_sponsor_inquiry": "push_host_activity",
    "sponsor.": "push_sponsor_updates",
    "sponsor_": "push_sponsor_updates",
    "host.": "push_host_activity",
    "host_": "push_host_activity",
    "admin.": "push_host_activity",
    "admin_": "push_host_activity",
    "ambassador.": "push_ticket_updates",
    "ambassador_": "push_ticket_updates",
}


def push_pref_key_for_kind(kind: str) -> str | None:
    k = (kind or "").strip().lower()
    if not k:
        return None
    # Longer / more specific prefixes first
    for prefix, pref in sorted(
        KIND_TO_PUSH_PREF.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if k == prefix or k.startswith(prefix) or k == prefix.rstrip("."):
            return pref
    if "security" in k or "password" in k or k.startswith("auth"):
        return "push_security"
    if "marketing" in k or "cart_reminder" in k or "post_event_drop" in k:
        return "push_marketing"
    if "review" in k:
        return "push_reviews"
    if k in ("new_message", "message_request", "attachment_received") or "message" in k:
        return "push_messages"
    if "merch" in k:
        return "push_merch_updates"
    if "ticket" in k or "refund" in k:
        return "push_ticket_updates"
    if "fan_connect" in k:
        return "push_fan_connect"
    if "sponsor" in k:
        return "push_sponsor_updates"
    if "ambassador" in k:
        return "push_ticket_updates"
    return "push_host_activity"


def _message_push_rate_limited(db: Session, *, user_id: UUID) -> bool:
    # Lazy import avoids circular import via app.push.__init__ → service → prefs.
    from app.push.models import PushEvent
    from app.push.templates import MESSAGE_PUSH_TEMPLATES

    settings = get_settings()
    from app.runtime_settings import get_runtime_setting

    limit = int(
        get_runtime_setting("push_message_rate_limit_per_hour", db=db, settings=settings)
        or 12
    )
    if limit <= 0:
        return False
    since = datetime.now(UTC) - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(PushEvent)
        .where(
            PushEvent.recipient_user_id == user_id,
            PushEvent.created_at >= since,
            PushEvent.status.in_(("pending", "sending", "sent")),
            or_(
                PushEvent.template.in_(tuple(MESSAGE_PUSH_TEMPLATES)),
                PushEvent.template.startswith("message."),
                PushEvent.template.startswith("messaging."),
            ),
        )
    )
    return int(count or 0) >= limit


def push_preference_allows(
    db: Session,
    *,
    user_id: UUID | None,
    kind: str,
    force: bool = False,
) -> tuple[bool, str | None]:
    """Return (allowed, skip_reason).

    ``force`` is for admin test pushes only — still requires a recipient user.
    """
    if user_id is None:
        return False, "no_user"
    if force:
        return True, None

    prefs = get_or_create_preferences(db, user_id)

    # Master switch — always enforced (including security).
    if not bool(getattr(prefs, "push_enabled", False)):
        return False, "push_enabled_off"

    key = push_pref_key_for_kind(kind)
    if key is None:
        return False, "unknown_kind"

    # Security: always allowed when push is on; bypasses marketing opt-out.
    if key == "push_security":
        return True, None

    # Marketing: category toggle + unsubscribe respect (security never lands here).
    if key == "push_marketing":
        if getattr(prefs, "unsubscribed_marketing_at", None) is not None:
            return False, "marketing_unsubscribed"
        if not bool(getattr(prefs, "push_marketing", True)):
            return False, "pref_push_marketing_off"
        return True, None

    if not bool(getattr(prefs, key, True)):
        # Categories default on but honor an explicit user opt-out.
        return False, f"pref_{key}_off"

    if key == "push_messages" and _message_push_rate_limited(db, user_id=user_id):
        return False, "message_push_rate_limited"

    return True, None
