"""Push subscription + outbox service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.email.prefs import get_or_create_preferences
from app.notifications.prefs import push_preference_allows
from app.notifications.push import (
    FAILURE_DEACTIVATE_THRESHOLD,
    deactivate_subscription,
    list_user_subscriptions,
    revoke_subscription,
    serialize_subscription_public,
    upsert_subscription,
)
from app.notifications.settings_service import (
    get_active_push_settings,
    record_push_test,
)
from app.push.models import PushEvent, PushSubscription
from app.push.provider import PushPayload, get_push_provider
from app.push.templates import render_push
from app.users.models import User

logger = logging.getLogger("padeya.push.service")

MAX_ATTEMPTS = 5


@dataclass
class DrainStats:
    pending_before: int
    attempted: int
    sent: int
    failed: int
    skipped: int
    still_pending: int
    provider_mode: str
    deactivated_subscriptions: int = 0


def register_subscription(
    db: Session,
    *,
    user_id: UUID,
    subscription: dict[str, Any],
) -> PushSubscription:
    """Upsert a browser push subscription for the user (multi-device)."""
    settings = get_active_push_settings(db)
    if settings is None or not settings.push_enabled:
        raise ValueError("Push notifications are not enabled")
    row = upsert_subscription(
        db,
        user_id=user_id,
        endpoint=str(subscription.get("endpoint") or ""),
        p256dh=str(subscription.get("p256dh") or ""),
        auth=str(subscription.get("auth") or ""),
        user_agent=subscription.get("user_agent"),
        device_label=subscription.get("device_label"),
        platform=subscription.get("platform"),
    )
    prefs = get_or_create_preferences(db, user_id)
    if not prefs.push_enabled:
        prefs.push_enabled = True
    db.flush()
    return row


def unregister_subscription(
    db: Session,
    *,
    user_id: UUID,
    endpoint: str | None = None,
    subscription_id: UUID | None = None,
) -> bool:
    return revoke_subscription(
        db,
        user_id=user_id,
        endpoint=endpoint,
        subscription_id=subscription_id,
    )


def enqueue_push(
    db: Session,
    *,
    template: str,
    recipient_user_id: UUID,
    context: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
    force: bool = False,
    notification_id: UUID | None = None,
    preference_kind: str | None = None,
) -> PushEvent | None:
    """Create a pending push_events row. Does not send.

    Call only after payment verification for commerce templates.
    Returns existing row when dedupe_key already present.
    """
    from app.push.privacy import sanitize_push_context

    ctx = sanitize_push_context(context)
    title, body, action_url, icon_url, badge_url = render_push(template, ctx)

    if dedupe_key:
        existing = db.scalar(
            select(PushEvent).where(PushEvent.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return existing

    settings = get_active_push_settings(db)
    status = "pending"
    error_message = None

    if settings is None or not settings.push_enabled:
        status = "skipped"
        error_message = "push_disabled"
    elif not force:
        pref_kind = (preference_kind or str(ctx.get("kind") or "") or template).strip()
        allowed, reason = push_preference_allows(
            db, user_id=recipient_user_id, kind=pref_kind, force=force
        )
        if not allowed:
            status = "skipped"
            error_message = reason
        else:
            # Opt-in also requires at least one active device for non-log readiness,
            # but log mode can still enqueue for observability.
            pass

    data = {
        **ctx,
        "kind": template,
        "notification_id": str(notification_id)
        if notification_id
        else ctx.get("notification_id"),
    }

    event = PushEvent(
        recipient_user_id=recipient_user_id,
        template=template[:64],
        title=title,
        body=body,
        action_url=action_url,
        icon_url=icon_url,
        badge_url=badge_url,
        data_json=data,
        status=status,
        error_message=error_message,
        attempts=0,
        dedupe_key=dedupe_key,
        notification_id=notification_id,
    )
    try:
        with db.begin_nested():
            db.add(event)
            db.flush()
    except IntegrityError:
        if dedupe_key:
            return db.scalar(
                select(PushEvent).where(PushEvent.dedupe_key == dedupe_key)
            )
        raise

    settings_cfg = get_settings()
    if (
        event.status == "pending"
        and not settings_cfg.push_queue_enabled
    ):
        send_push_event(db, event.id)

    return event


def send_push_event(db: Session, push_event_id: UUID) -> PushEvent:
    """Attempt delivery for one outbox row."""
    event = db.get(PushEvent, push_event_id)
    if event is None:
        raise LookupError("Push event not found")
    if event.status in {"sent", "skipped"}:
        return event
    if event.attempts >= MAX_ATTEMPTS:
        event.status = "failed"
        event.error_message = event.error_message or "max_attempts"
        db.flush()
        return event

    settings = get_active_push_settings(db)
    if settings is None or not settings.push_enabled:
        event.status = "skipped"
        event.error_message = "push_disabled"
        event.last_attempt_at = datetime.now(UTC)
        db.flush()
        return event

    event.attempts += 1
    event.last_attempt_at = datetime.now(UTC)

    subs = list_user_subscriptions(db, user_id=event.recipient_user_id)
    provider = get_push_provider(db)
    payload = PushPayload(
        title=event.title,
        body=event.body,
        url=event.action_url or "/dashboard/notifications",
        kind=event.template,
        notification_id=str(event.notification_id) if event.notification_id else None,
        icon=event.icon_url,
        badge=event.badge_url,
        tag=str(event.notification_id or event.id),
        timestamp_ms=int(datetime.now(UTC).timestamp() * 1000),
    )
    result = provider.send(
        db,
        user_id=event.recipient_user_id,
        subscriptions=subs,
        payload=payload,
        push_event_id=event.id,
    )

    if result.status == "skipped" and result.ok is False:
        # No devices — keep pending briefly then skip after attempts
        if event.attempts >= MAX_ATTEMPTS or result.error == "no_active_subscriptions":
            event.status = "skipped"
            event.error_message = result.error or "no_active_subscriptions"
        else:
            event.status = "pending"
            event.error_message = result.error
    elif result.ok:
        event.status = "sent"
        event.sent_at = datetime.now(UTC)
        event.error_message = None
    else:
        event.status = "failed" if event.attempts >= MAX_ATTEMPTS else "pending"
        event.error_message = result.error

    db.flush()
    return event


TEST_PUSH_TITLE = "Pàdéyá test notification"
TEST_PUSH_BODY = "Push notifications are working."
TEST_PUSH_ACTION_URL = "/dashboard/notifications"
NO_ACTIVE_DEVICE_MESSAGE = (
    "This user has no active push devices. "
    "Ask them to enable browser notifications on Pàdéyá first."
)


def resolve_user_for_push(
    db: Session,
    *,
    user_id: UUID | None = None,
    email: str | None = None,
) -> User:
    user: User | None = None
    if user_id is not None:
        user = db.get(User, user_id)
    elif email and email.strip():
        user = db.scalar(
            select(User).where(func.lower(User.email) == email.strip().lower())
        )
    if user is None:
        raise LookupError("User not found")
    return user


def user_push_subscription_status(
    db: Session,
    *,
    user_id: UUID | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Safe subscription summary for admin (no endpoint secrets / keys)."""
    from app.notifications.push import serialize_subscription_public

    user = resolve_user_for_push(db, user_id=user_id, email=email)
    subs = list_user_subscriptions(db, user_id=user.id, include_inactive=False)
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "active_subscription_count": len(subs),
        "has_active_device": len(subs) > 0,
        "devices": [serialize_subscription_public(s) for s in subs],
    }


def send_test_push(
    db: Session,
    *,
    user_id: UUID | None = None,
    email: str | None = None,
    actor_user_id: UUID | None = None,
) -> dict[str, Any]:
    """Enqueue + immediately deliver a fixed-copy test push for a user."""
    user = resolve_user_for_push(db, user_id=user_id, email=email)

    settings = get_active_push_settings(db)
    if settings is None or not settings.push_enabled:
        record_push_test(
            db, actor_user_id=actor_user_id or user.id, ok=False, error="push_disabled"
        )
        raise ValueError("Push is not enabled")

    provider_mode = (settings.provider or "log").strip().lower()
    subs = list_user_subscriptions(db, user_id=user.id, include_inactive=False)
    if not subs:
        record_push_test(
            db,
            actor_user_id=actor_user_id or user.id,
            ok=False,
            error="no_subscription",
        )
        raise ValueError(NO_ACTIVE_DEVICE_MESSAGE)

    from app.notifications.service import notify_user

    notif = notify_user(
        db,
        user_id=user.id,
        kind="admin.push_test",
        title=TEST_PUSH_TITLE,
        body=TEST_PUSH_BODY,
        link_path=TEST_PUSH_ACTION_URL,
        send_push=True,
        force_push=True,
        push_context={
            "title": TEST_PUSH_TITLE,
            "body": TEST_PUSH_BODY,
            "action_url": TEST_PUSH_ACTION_URL,
        },
    )
    # Ensure outbox row is drained for immediate admin feedback
    event = db.scalar(
        select(PushEvent)
        .where(
            PushEvent.recipient_user_id == user.id,
            PushEvent.template.in_(("admin_push_test", "admin.push_test")),
        )
        .order_by(PushEvent.created_at.desc())
        .limit(1)
    )
    if event is not None and event.status == "pending":
        send_push_event(db, event.id)

    record_push_test(db, actor_user_id=actor_user_id or user.id, ok=True)
    return {
        "ok": True,
        "user_id": str(user.id),
        "email": user.email,
        "notification_id": str(notif.id) if notif else None,
        "push_event_id": str(event.id) if event else None,
        "provider": provider_mode,
        "status": event.status if event else None,
        "active_subscription_count": len(subs),
        "has_active_device": True,
        "title": TEST_PUSH_TITLE,
        "body": TEST_PUSH_BODY,
        "action_url": TEST_PUSH_ACTION_URL,
        "message": (
            f"Test push processed ({provider_mode}) to "
            f"{len(subs)} active device(s)."
        ),
    }


def cleanup_failed_subscriptions(
    db: Session,
    *,
    older_than_days: int = 30,
) -> int:
    """Deactivate expired / high-failure / stale inactive rows. Returns count touched."""
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    rows = list(
        db.scalars(
            select(PushSubscription).where(
                PushSubscription.is_active.is_(True),
                or_(
                    PushSubscription.failure_count >= FAILURE_DEACTIVATE_THRESHOLD,
                    (
                        PushSubscription.last_failure_at.is_not(None)
                        & (PushSubscription.last_failure_at < cutoff)
                        & (PushSubscription.failure_count > 0)
                    ),
                ),
            )
        )
    )
    n = 0
    for row in rows:
        deactivate_subscription(row, reason="cleanup_failed")
        n += 1
    db.flush()
    return n


def count_by_status(db: Session, status: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(PushEvent)
            .where(PushEvent.status == status)
        )
        or 0
    )


def drain_push_outbox(
    db: Session, *, limit: int = 50, commit: bool = True
) -> DrainStats:
    settings = get_active_push_settings(db)
    provider_mode = (settings.provider if settings else "log") or "log"
    pending_before = count_by_status(db, "pending")
    rows = list(
        db.scalars(
            select(PushEvent)
            .where(
                PushEvent.status == "pending",
                PushEvent.attempts < MAX_ATTEMPTS,
            )
            .order_by(PushEvent.created_at.asc())
            .limit(limit)
        )
    )
    sent = failed = skipped = 0
    for row in rows:
        send_push_event(db, row.id)
        if row.status == "sent":
            sent += 1
        elif row.status == "failed":
            failed += 1
        elif row.status == "skipped":
            skipped += 1
        elif row.status == "pending":
            failed += 1
    if commit:
        db.commit()
    else:
        db.flush()
    return DrainStats(
        pending_before=pending_before,
        attempted=len(rows),
        sent=sent,
        failed=failed,
        skipped=skipped,
        still_pending=count_by_status(db, "pending"),
        provider_mode=provider_mode,
        deactivated_subscriptions=0,
    )


def serialize_push_event(row: PushEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "recipient_user_id": row.recipient_user_id,
        "template": row.template,
        "title": row.title,
        "body": row.body,
        "action_url": row.action_url,
        "status": row.status,
        "attempts": row.attempts,
        "error_message": row.error_message,
        "last_attempt_at": row.last_attempt_at,
        "sent_at": row.sent_at,
        "dedupe_key": row.dedupe_key,
        "notification_id": row.notification_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


# Re-export helpers used by routers
__all__ = [
    "register_subscription",
    "unregister_subscription",
    "enqueue_push",
    "send_push_event",
    "send_test_push",
    "user_push_subscription_status",
    "cleanup_failed_subscriptions",
    "drain_push_outbox",
    "serialize_push_event",
    "serialize_subscription_public",
    "list_user_subscriptions",
    "TEST_PUSH_TITLE",
    "TEST_PUSH_BODY",
    "TEST_PUSH_ACTION_URL",
    "NO_ACTIVE_DEVICE_MESSAGE",
]
