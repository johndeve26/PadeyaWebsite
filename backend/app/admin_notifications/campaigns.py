"""Admin custom notification campaigns."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_notifications.audience import (
    preview_audience_count,
    resolve_notification_audience,
    search_users_for_campaign,
)
from app.admin_notifications.models import (
    NotificationCampaign,
    NotificationCampaignRecipient,
    NotificationDelivery,
)
from app.admin_notifications.orchestrator import safe_action_url, send_notification
from app.admin_notifications.settings_service import record_notification_audit


def serialize_campaign(row: NotificationCampaign) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "title": row.title,
        "body": row.body,
        "cta_text": row.cta_text,
        "cta_url": row.cta_url,
        "channels": {
            "in_app": bool(row.channel_in_app),
            "push": bool(row.channel_push),
            "email": bool(row.channel_email),
        },
        "audience_mode": row.audience_mode,
        "audience_filters": row.audience_filters or {},
        "status": row.status,
        "scheduled_at": row.scheduled_at,
        "sent_at": row.sent_at,
        "recipient_count": int(row.recipient_count or 0),
        "created_by_admin_id": str(row.created_by_admin_id),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_campaigns(db: Session, *, limit: int = 50) -> list[dict]:
    rows = list(
        db.scalars(
            select(NotificationCampaign)
            .order_by(NotificationCampaign.created_at.desc())
            .limit(limit)
        )
    )
    return [serialize_campaign(r) for r in rows]


def get_campaign(db: Session, campaign_id: uuid.UUID) -> NotificationCampaign | None:
    return db.get(NotificationCampaign, campaign_id)


def create_campaign(
    db: Session,
    *,
    payload: dict[str, Any],
    actor_user_id: uuid.UUID,
) -> dict[str, Any]:
    cta_url = safe_action_url(payload.get("cta_url"), default="/dashboard/notifications")
    if payload.get("cta_url") and cta_url == "/dashboard/notifications":
        raw = str(payload.get("cta_url") or "")
        if raw.startswith("http") or "javascript:" in raw.lower():
            raise ValueError("Unsafe CTA URL — use a same-origin path like /dashboard/…")

    row = NotificationCampaign(
        title=str(payload["title"]).strip()[:160],
        body=str(payload["body"]).strip()[:500],
        cta_text=(str(payload["cta_text"]).strip()[:80] if payload.get("cta_text") else None),
        cta_url=cta_url if payload.get("cta_url") else None,
        channel_in_app=bool((payload.get("channels") or {}).get("in_app", True)),
        channel_push=bool((payload.get("channels") or {}).get("push", True)),
        channel_email=bool((payload.get("channels") or {}).get("email", False)),
        audience_mode=str(payload.get("audience_mode") or "selected_users"),
        audience_filters=dict(payload.get("audience_filters") or {}),
        status="draft",
        scheduled_at=payload.get("scheduled_at"),
        created_by_admin_id=actor_user_id,
    )
    db.add(row)
    db.flush()

    user_ids = payload.get("user_ids") or (payload.get("audience_filters") or {}).get(
        "user_ids"
    ) or []
    for uid in user_ids:
        try:
            user_uuid = uuid.UUID(str(uid))
        except (TypeError, ValueError):
            continue
        db.add(
            NotificationCampaignRecipient(
                campaign_id=row.id, user_id=user_uuid, status="pending"
            )
        )
    row.recipient_count = len(user_ids) if user_ids else preview_audience_count(
        db,
        audience=row.audience_mode,
        filters=row.audience_filters,
    )
    db.flush()
    record_notification_audit(
        db,
        action="notification.campaign_created",
        actor_user_id=actor_user_id,
        resource_type="notification_campaign",
        resource_id=str(row.id),
        details={
            "status": row.status,
            "audience_mode": row.audience_mode,
            "recipient_count": row.recipient_count,
            "channels": {
                "in_app": row.channel_in_app,
                "push": row.channel_push,
                "email": row.channel_email,
            },
        },
    )
    return serialize_campaign(row)


def cancel_campaign(
    db: Session, *, campaign_id: uuid.UUID, actor_user_id: uuid.UUID
) -> dict[str, Any]:
    row = get_campaign(db, campaign_id)
    if row is None:
        raise ValueError("Campaign not found")
    if row.status not in {"draft", "scheduled"}:
        raise ValueError("Only draft/scheduled campaigns can be cancelled")
    row.status = "cancelled"
    db.flush()
    record_notification_audit(
        db,
        action="notification.campaign_cancelled",
        actor_user_id=actor_user_id,
        resource_type="notification_campaign",
        resource_id=str(row.id),
        details={"status": "cancelled"},
    )
    return serialize_campaign(row)


def send_custom_admin_notification(
    db: Session, *, campaign_id: uuid.UUID, actor_user_id: uuid.UUID
) -> dict[str, Any]:
    row = get_campaign(db, campaign_id)
    if row is None:
        raise ValueError("Campaign not found")
    if row.status not in {"draft", "scheduled"}:
        raise ValueError("Campaign already sent or cancelled")

    row.status = "sending"
    db.flush()

    recipients = list(
        db.scalars(
            select(NotificationCampaignRecipient.user_id).where(
                NotificationCampaignRecipient.campaign_id == row.id
            )
        )
    )
    if not recipients:
        recipients = resolve_notification_audience(
            db,
            audience=row.audience_mode,
            filters=row.audience_filters or {},
            limit=2000,
        )

    # Temporarily apply campaign channel overrides via send_notification force path
    # by updating admin.custom_campaign setting channels for this send only —
    # instead pass channels through context and handle in a dedicated path.
    from app.admin_notifications.settings_service import get_or_create_setting

    setting = get_or_create_setting(db, "admin.custom_campaign")
    prev = (
        setting.channel_in_app,
        setting.channel_push,
        setting.channel_email,
        setting.enabled,
    )
    setting.enabled = True
    setting.channel_in_app = row.channel_in_app
    setting.channel_push = row.channel_push
    setting.channel_email = row.channel_email
    db.flush()

    try:
        result = send_notification(
            db,
            type_key="admin.custom_campaign",
            recipient_user_ids=list(recipients),
            title=row.title,
            body=row.body,
            link_path=row.cta_url or "/dashboard/notifications",
            dedupe_key=f"campaign:{row.id}",
            force=True,
            created_by_admin_id=actor_user_id,
            campaign_id=row.id,
            context={"context_id": str(row.id)},
        )
    finally:
        setting.channel_in_app, setting.channel_push, setting.channel_email, setting.enabled = (
            prev
        )
        db.flush()

    for uid in recipients:
        recip = db.scalar(
            select(NotificationCampaignRecipient).where(
                NotificationCampaignRecipient.campaign_id == row.id,
                NotificationCampaignRecipient.user_id == uid,
            )
        )
        if recip is None:
            recip = NotificationCampaignRecipient(
                campaign_id=row.id, user_id=uid, status="sent"
            )
            db.add(recip)
        else:
            recip.status = "sent"

    row.status = "sent"
    row.sent_at = datetime.now(UTC)
    row.recipient_count = len(recipients)
    db.flush()
    record_notification_audit(
        db,
        action="notification.campaign_sent",
        actor_user_id=actor_user_id,
        resource_type="notification_campaign",
        resource_id=str(row.id),
        details={
            "recipient_count": len(recipients),
            "sent": result.get("sent"),
            "skipped": result.get("skipped"),
            "failed": result.get("failed"),
        },
    )
    return {"campaign": serialize_campaign(row), "delivery": result}


def test_campaign_to_self(
    db: Session, *, campaign_id: uuid.UUID, actor_user_id: uuid.UUID
) -> dict[str, Any]:
    row = get_campaign(db, campaign_id)
    if row is None:
        raise ValueError("Campaign not found")
    from app.admin_notifications.settings_service import get_or_create_setting

    setting = get_or_create_setting(db, "admin.custom_campaign")
    prev = (
        setting.channel_in_app,
        setting.channel_push,
        setting.channel_email,
        setting.enabled,
    )
    setting.enabled = True
    setting.channel_in_app = row.channel_in_app
    setting.channel_push = row.channel_push
    setting.channel_email = row.channel_email
    db.flush()
    try:
        result = send_notification(
            db,
            type_key="admin.custom_campaign",
            recipient_user_ids=[actor_user_id],
            title=f"[TEST] {row.title}",
            body=row.body,
            link_path=row.cta_url or "/dashboard/notifications",
            dedupe_key=f"campaign-test:{row.id}:{actor_user_id}:{int(datetime.now(UTC).timestamp())}",
            force=True,
            created_by_admin_id=actor_user_id,
            campaign_id=row.id,
        )
    finally:
        setting.channel_in_app, setting.channel_push, setting.channel_email, setting.enabled = (
            prev
        )
        db.flush()
    record_notification_audit(
        db,
        action="notification.campaign_test_sent",
        actor_user_id=actor_user_id,
        resource_type="notification_campaign",
        resource_id=str(row.id),
        details={"sent": result.get("sent")},
    )
    return result


def list_campaign_deliveries(
    db: Session, *, campaign_id: uuid.UUID, limit: int = 100
) -> list[dict]:
    rows = list(
        db.scalars(
            select(NotificationDelivery)
            .where(NotificationDelivery.campaign_id == campaign_id)
            .order_by(NotificationDelivery.created_at.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": str(r.id),
            "type_key": r.type_key,
            "recipient_user_id": str(r.recipient_user_id),
            "channel": r.channel,
            "status": r.status,
            "error_reason": r.error_reason,
            "sent_at": r.sent_at,
            "failed_at": r.failed_at,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def preview_recipients(
    db: Session,
    *,
    audience_mode: str,
    audience_filters: dict | None = None,
    user_ids: list | None = None,
) -> dict[str, Any]:
    filters = dict(audience_filters or {})
    if user_ids:
        filters["user_ids"] = user_ids
    ids = resolve_notification_audience(
        db, audience=audience_mode, filters=filters, limit=5000
    )
    return {
        "count": len(ids),
        "sample": search_users_for_campaign(db, q=None, limit=5)
        if audience_mode == "all_users"
        else [
            {"id": str(uid)} for uid in ids[:5]
        ],
    }
