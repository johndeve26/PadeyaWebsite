"""Notification preference checks for transactional email."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.models import UserEmailPreferences
from app.email.templates import get_template

DEFAULTS = {
    "email_ticket_updates": True,
    "email_merch_updates": True,
    "email_event_reminders": True,
    "email_messages": True,
    "email_fan_connect": True,
    "email_sponsor_updates": True,
    "email_host_activity": True,
    "email_marketing": True,
    "email_security": True,
    "push_enabled": True,
    "push_ticket_updates": True,
    "push_merch_updates": True,
    "push_event_reminders": True,
    "push_messages": True,
    "push_message_previews": True,
    "push_fan_connect": True,
    "push_sponsor_updates": True,
    "push_host_activity": True,
    "push_reviews": True,
    "push_marketing": True,
    "push_security": True,
}


def get_or_create_preferences(db: Session, user_id: UUID) -> UserEmailPreferences:
    row = db.scalar(
        select(UserEmailPreferences).where(UserEmailPreferences.user_id == user_id)
    )
    if row is not None:
        return row
    row = UserEmailPreferences(user_id=user_id, **DEFAULTS)
    db.add(row)
    db.flush()
    return row


def preference_allows(
    db: Session,
    *,
    user_id: UUID | None,
    template_name: str,
    force: bool = False,
) -> tuple[bool, str | None]:
    """Return (allowed, skip_reason)."""
    if force:
        return True, None
    template = get_template(template_name)
    if template.required or template.preference_key is None:
        # Required transactional / security — always send
        return True, None
    if user_id is None:
        # Anonymous recipient — allow required already handled; optional needs user
        if template.preference_key == "email_marketing":
            return False, "marketing_requires_user"
        return True, None

    prefs = get_or_create_preferences(db, user_id)
    key = template.preference_key
    if key == "email_security":
        return True, None
    if key == "email_marketing":
        if prefs.unsubscribed_marketing_at is not None:
            return False, "marketing_unsubscribed"
        if not prefs.email_marketing:
            return False, "pref_email_marketing_off"
        return True, None
    allowed = bool(getattr(prefs, key, True))
    if not allowed:
        return False, f"pref_{key}_off"
    return True, None


def update_preferences(
    db: Session,
    *,
    user_id: UUID,
    updates: dict,
) -> UserEmailPreferences:
    prefs = get_or_create_preferences(db, user_id)
    for key, value in updates.items():
        if key in ("email_security", "push_security"):
            # Cannot disable security channel categories
            setattr(prefs, key, True)
            continue
        if key in DEFAULTS and value is not None:
            setattr(prefs, key, bool(value))
            if key in ("email_marketing", "push_marketing"):
                if value:
                    prefs.unsubscribed_marketing_at = None
                else:
                    prefs.unsubscribed_marketing_at = datetime.now(UTC)
    db.flush()
    return prefs


def unsubscribe_marketing(db: Session, *, user_id: UUID) -> UserEmailPreferences:
    prefs = get_or_create_preferences(db, user_id)
    prefs.email_marketing = False
    prefs.unsubscribed_marketing_at = datetime.now(UTC)
    db.flush()
    return prefs


def serialize_prefs(prefs: UserEmailPreferences) -> dict:
    return {
        "email_ticket_updates": prefs.email_ticket_updates,
        "email_merch_updates": prefs.email_merch_updates,
        "email_event_reminders": prefs.email_event_reminders,
        "email_messages": prefs.email_messages,
        "email_fan_connect": prefs.email_fan_connect,
        "email_sponsor_updates": prefs.email_sponsor_updates,
        "email_host_activity": prefs.email_host_activity,
        "email_marketing": prefs.email_marketing,
        "email_security": True,
        "unsubscribed_marketing_at": prefs.unsubscribed_marketing_at,
        "push_enabled": bool(getattr(prefs, "push_enabled", True)),
        "push_ticket_updates": bool(getattr(prefs, "push_ticket_updates", True)),
        "push_merch_updates": bool(getattr(prefs, "push_merch_updates", True)),
        "push_event_reminders": bool(getattr(prefs, "push_event_reminders", True)),
        "push_messages": bool(getattr(prefs, "push_messages", True)),
        "push_message_previews": bool(getattr(prefs, "push_message_previews", True)),
        "push_fan_connect": bool(getattr(prefs, "push_fan_connect", True)),
        "push_sponsor_updates": bool(getattr(prefs, "push_sponsor_updates", True)),
        "push_host_activity": bool(getattr(prefs, "push_host_activity", True)),
        "push_reviews": bool(getattr(prefs, "push_reviews", True)),
        "push_marketing": bool(getattr(prefs, "push_marketing", True)),
        "push_security": True,
    }
