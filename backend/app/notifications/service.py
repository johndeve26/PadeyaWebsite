"""Central in-app + push notification helpers.

Email remains via ``enqueue_template`` in domain modules — this module does not
duplicate email. Messaging WebSockets stay untouched.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, not_, select
from sqlalchemy.orm import Session

from app.messaging.models import InAppNotification
from app.notifications.prefs import push_preference_allows

logger = logging.getLogger("padeya.notifications")


def create_in_app_notification(
    db: Session,
    *,
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    link_path: str | None = None,
    thread_id: UUID | None = None,
    dedupe_key: str | None = None,
) -> InAppNotification | None:
    """Create an in-app row. Returns None when dedupe_key already exists."""
    if dedupe_key:
        existing = db.scalar(
            select(InAppNotification).where(InAppNotification.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return None

    row = InAppNotification(
        user_id=user_id,
        kind=kind[:64],
        title=title[:160],
        body=body[:240],
        link_path=(link_path or "")[:300] or None,
        thread_id=thread_id,
        dedupe_key=dedupe_key,
    )
    db.add(row)
    db.flush()
    return row


def _publish_notification_created(
    db: Session,
    *,
    row: InAppNotification,
) -> None:
    """Fan-out personal WS event for in-app toast bridge (safe fields only)."""
    try:
        from app.messaging.ws_events import publish_to_users

        publish_to_users(
            [row.user_id],
            {
                "type": "notification.created",
                "event_id": f"notif:{row.id}",
                "notification": {
                    "id": str(row.id),
                    "kind": row.kind,
                    "title": row.title,
                    "body": row.body,
                    "link_path": row.link_path,
                    "thread_id": str(row.thread_id) if row.thread_id else None,
                    "created_at": (
                        row.created_at.isoformat()
                        if getattr(row, "created_at", None)
                        else None
                    ),
                },
                "unread_count": unread_count(db, user_id=row.user_id),
            },
        )
    except Exception:  # noqa: BLE001 — never break product flows
        logger.exception("notification.created publish failed for %s", row.id)


def notify_user(
    db: Session,
    *,
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    link_path: str | None = None,
    thread_id: UUID | None = None,
    dedupe_key: str | None = None,
    send_push: bool = True,
    force_push: bool = False,
    push_context: dict | None = None,
) -> InAppNotification | None:
    """Write in-app notification, emit WS toast event, enqueue browser push.

    Commerce callers must invoke only after payment verification (webhook).
    ``push_context`` may only include privacy-safe fields (sanitized in enqueue).
    """
    # Admin type kill-switch (when the kind maps to a registered type).
    try:
        from app.admin_notifications.registry import resolve_type_key
        from app.admin_notifications.settings_service import get_or_create_setting

        type_key = resolve_type_key(kind)
        if type_key is not None:
            setting = get_or_create_setting(db, type_key)
            if not setting.enabled:
                return None
            if not setting.channel_in_app and not (
                send_push and setting.channel_push
            ):
                # If both primary channels off, skip entirely.
                if not setting.channel_email:
                    return None
            if not setting.channel_push:
                send_push = False
    except Exception:  # noqa: BLE001
        pass

    if send_push:
        from app.notifications.channel_registry import push_channel_allowed

        push_ok, _block = push_channel_allowed(kind)
        if not push_ok:
            send_push = False

    row = create_in_app_notification(
        db,
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        link_path=link_path,
        thread_id=thread_id,
        dedupe_key=dedupe_key,
    )
    if row is None:
        return None

    _publish_notification_created(db, row=row)

    if send_push:
        try:
            from app.push.service import enqueue_push
            from app.push.templates import resolve_template_name

            push_template = resolve_template_name(kind)
            ctx = {
                "action_url": link_path or "/dashboard/notifications",
                "notification_id": str(row.id),
                "kind": kind,
                **(push_context or {}),
            }
            # Generic / admin-test templates may use title/body; never for chat kinds.
            if push_template in {"generic", "admin_push_test"}:
                ctx["title"] = title
                ctx["body"] = body
            enqueue_push(
                db,
                template=push_template,
                recipient_user_id=user_id,
                context=ctx,
                dedupe_key=(f"push:{dedupe_key}" if dedupe_key else None),
                force=force_push,
                notification_id=row.id,
                preference_kind=kind,
            )
        except Exception:  # noqa: BLE001 — never break product flows
            logger.exception("push enqueue failed for notification %s", row.id)
    return row


def list_user_notifications(
    db: Session,
    *,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    include_archived: bool = False,
    category: str | None = None,
    unread_only: bool = False,
) -> tuple[list[InAppNotification], int]:
    from app.notifications.categories import (
        category_filter_clause,
        exclude_message_kinds_clause,
        normalize_category,
    )

    stmt = select(InAppNotification).where(InAppNotification.user_id == user_id)
    count_stmt = (
        select(func.count())
        .select_from(InAppNotification)
        .where(InAppNotification.user_id == user_id)
    )
    if not include_archived:
        stmt = stmt.where(InAppNotification.archived_at.is_(None))
        count_stmt = count_stmt.where(InAppNotification.archived_at.is_(None))
    if unread_only:
        stmt = stmt.where(InAppNotification.read_at.is_(None))
        count_stmt = count_stmt.where(InAppNotification.read_at.is_(None))
    cat = normalize_category(category)
    cat_clause = category_filter_clause(category)
    if cat_clause is not None:
        stmt = stmt.where(cat_clause)
        count_stmt = count_stmt.where(cat_clause)
        if cat == "fan_connect":
            fc_msg = InAppNotification.kind == "fan_connect.message"
            stmt = stmt.where(not_(fc_msg))
            count_stmt = count_stmt.where(not_(fc_msg))
    elif cat == "all":
        exclude_msgs = exclude_message_kinds_clause()
        if exclude_msgs is not None:
            stmt = stmt.where(exclude_msgs)
            count_stmt = count_stmt.where(exclude_msgs)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(InAppNotification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return rows, total


def unread_count(
    db: Session,
    *,
    user_id: UUID,
    category: str | None = None,
) -> int:
    from app.notifications.categories import (
        category_filter_clause,
        exclude_message_kinds_clause,
        normalize_category,
    )

    stmt = (
        select(func.count())
        .select_from(InAppNotification)
        .where(
            InAppNotification.user_id == user_id,
            InAppNotification.read_at.is_(None),
            InAppNotification.archived_at.is_(None),
        )
    )
    cat = normalize_category(category)
    cat_clause = category_filter_clause(category)
    if cat_clause is not None:
        stmt = stmt.where(cat_clause)
    elif cat == "all":
        exclude_msgs = exclude_message_kinds_clause()
        if exclude_msgs is not None:
            stmt = stmt.where(exclude_msgs)
    return int(db.scalar(stmt) or 0)


def mark_read(
    db: Session,
    *,
    user_id: UUID,
    notification_id: UUID,
) -> InAppNotification:
    row = db.get(InAppNotification, notification_id)
    if row is None or row.user_id != user_id:
        raise LookupError("Notification not found")
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        db.flush()
    return row


def mark_all_read(db: Session, *, user_id: UUID) -> int:
    rows = list(
        db.scalars(
            select(InAppNotification).where(
                InAppNotification.user_id == user_id,
                InAppNotification.read_at.is_(None),
                InAppNotification.archived_at.is_(None),
            )
        )
    )
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
    db.flush()
    return len(rows)


def archive_notification(
    db: Session,
    *,
    user_id: UUID,
    notification_id: UUID,
) -> InAppNotification:
    row = db.get(InAppNotification, notification_id)
    if row is None or row.user_id != user_id:
        raise LookupError("Notification not found")
    row.archived_at = datetime.now(UTC)
    if row.read_at is None:
        row.read_at = row.archived_at
    db.flush()
    return row


def popup_candidates(
    db: Session,
    *,
    user_id: UUID,
    limit: int = 5,
) -> list[InAppNotification]:
    """Unread, not yet shown as popup — for in-app toast bridge (not chat)."""
    from app.notifications.categories import exclude_message_kinds_clause

    stmt = select(InAppNotification).where(
        InAppNotification.user_id == user_id,
        InAppNotification.read_at.is_(None),
        InAppNotification.archived_at.is_(None),
        InAppNotification.popup_shown_at.is_(None),
    )
    exclude_msgs = exclude_message_kinds_clause()
    if exclude_msgs is not None:
        stmt = stmt.where(exclude_msgs)
    return list(
        db.scalars(
            stmt.order_by(InAppNotification.created_at.desc()).limit(limit)
        )
    )


def mark_popup_shown(
    db: Session,
    *,
    user_id: UUID,
    notification_ids: list[UUID],
) -> int:
    if not notification_ids:
        return 0
    now = datetime.now(UTC)
    n = 0
    for nid in notification_ids:
        row = db.get(InAppNotification, nid)
        if row is None or row.user_id != user_id:
            continue
        if row.popup_shown_at is None:
            row.popup_shown_at = now
            n += 1
    db.flush()
    return n


def serialize_notification(row: InAppNotification) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "title": row.title,
        "body": row.body,
        "link_path": row.link_path,
        "thread_id": row.thread_id,
        "read_at": row.read_at,
        "archived_at": row.archived_at,
        "popup_shown_at": row.popup_shown_at,
        "created_at": row.created_at,
    }


# Re-export for domain helpers that want a one-liner check
__all__ = [
    "create_in_app_notification",
    "notify_user",
    "list_user_notifications",
    "unread_count",
    "mark_read",
    "mark_all_read",
    "archive_notification",
    "popup_candidates",
    "mark_popup_shown",
    "serialize_notification",
    "push_preference_allows",
]
