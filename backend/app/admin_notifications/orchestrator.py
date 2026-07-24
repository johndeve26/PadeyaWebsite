"""Notification orchestrator — admin-gated multi-channel fan-out."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_notifications.audience import resolve_notification_audience
from app.admin_notifications.models import NotificationDelivery, NotificationTemplate
from app.admin_notifications.registry import get_type_def, resolve_type_key
from app.admin_notifications.settings_service import get_or_create_setting
from app.email.prefs import get_or_create_preferences
from app.email.service import enqueue_template
from app.notifications.prefs import push_preference_allows
from app.notifications.service import notify_user
from app.users.models import User

_SAFE_PATH = re.compile(r"^/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]*$")


def safe_action_url(value: str | None, *, default: str = "/dashboard/notifications") -> str:
    raw = (value or default).strip() or default
    if raw.startswith("javascript:") or raw.startswith("data:"):
        return default
    if raw.startswith("/"):
        return raw if _SAFE_PATH.match(raw) else default
    try:
        parsed = urlparse(raw)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            # External absolute URLs not allowed for CTA — keep same-origin paths only.
            return default
    except Exception:  # noqa: BLE001
        return default
    return default


def render_template(template: str, context: dict[str, Any]) -> str:
    out = template or ""
    for key, value in (context or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, int, float)):
            out = out.replace("{{" + key + "}}", str(value)[:120])
    # Strip leftover placeholders.
    return re.sub(r"\{\{[a-zA-Z0-9_]+\}\}", "", out).strip()


def dedupe_notification(
    db: Session,
    *,
    type_key: str,
    user_id: uuid.UUID,
    dedupe_key: str | None,
    channel: str,
) -> bool:
    """Return True if this delivery should be skipped (already sent)."""
    if not dedupe_key:
        return False
    existing = db.scalar(
        select(NotificationDelivery.id).where(
            NotificationDelivery.type_key == type_key,
            NotificationDelivery.recipient_user_id == user_id,
            NotificationDelivery.channel == channel,
            NotificationDelivery.dedupe_key == dedupe_key,
            NotificationDelivery.status.in_(("sent", "pending")),
        )
    )
    return existing is not None


def _cooldown_blocks(
    db: Session,
    *,
    type_key: str,
    user_id: uuid.UUID,
    cooldown_seconds: int,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    since = datetime.now(UTC) - timedelta(seconds=cooldown_seconds)
    recent = db.scalar(
        select(NotificationDelivery.id).where(
            NotificationDelivery.type_key == type_key,
            NotificationDelivery.recipient_user_id == user_id,
            NotificationDelivery.status == "sent",
            NotificationDelivery.sent_at.is_not(None),
            NotificationDelivery.sent_at >= since,
        )
    )
    return recent is not None


def should_send_notification(
    db: Session,
    *,
    type_key: str,
    user: User,
    context: dict[str, Any] | None = None,
    channel: str,
) -> tuple[bool, str | None]:
    del context  # reserved for future rule hooks
    typedef = get_type_def(type_key)
    if typedef is None:
        return False, "unknown_type"
    setting = get_or_create_setting(db, type_key)
    if not setting.enabled:
        return False, "type_disabled"
    if channel == "in_app" and not setting.channel_in_app:
        return False, "channel_off"
    if channel == "push" and not setting.channel_push:
        return False, "channel_off"
    if channel == "email" and not setting.channel_email:
        return False, "channel_off"
    if not user.is_active or user.deactivated_at is not None:
        return False, "user_inactive"

    if setting.respect_user_prefs and setting.classification == "marketing":
        prefs = get_or_create_preferences(db, user.id)
        if channel == "email":
            if prefs.unsubscribed_marketing_at is not None:
                return False, "marketing_unsubscribed"
            if not prefs.email_marketing:
                return False, "pref_email_marketing_off"
        if channel == "push":
            ok, reason = push_preference_allows(
                db, user_id=user.id, kind="marketing.promo"
            )
            if not ok:
                return False, reason or "push_pref_off"

    if setting.classification == "critical":
        # Critical still honors master push_enabled for push, but not marketing prefs.
        if channel == "push":
            prefs = get_or_create_preferences(db, user.id)
            if not prefs.push_enabled:
                # Still allow in-app + email for critical; push optional if master off.
                return False, "push_enabled_off"

    if _cooldown_blocks(
        db,
        type_key=type_key,
        user_id=user.id,
        cooldown_seconds=int(setting.cooldown_seconds or 0),
    ):
        return False, "cooldown"

    return True, None


def _load_template(
    db: Session, *, setting_template_id: uuid.UUID | None, type_key: str
) -> NotificationTemplate | None:
    if setting_template_id:
        row = db.get(NotificationTemplate, setting_template_id)
        if row and row.archived_at is None:
            return row
    return db.scalar(
        select(NotificationTemplate).where(
            NotificationTemplate.type_key == type_key,
            NotificationTemplate.archived_at.is_(None),
        )
    )


def send_notification(
    db: Session,
    *,
    type_key: str,
    context: dict[str, Any] | None = None,
    recipient_user_ids: list[uuid.UUID] | None = None,
    title: str | None = None,
    body: str | None = None,
    link_path: str | None = None,
    dedupe_key: str | None = None,
    force: bool = False,
    created_by_admin_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Fan-out a typed notification to resolved audience."""
    canonical = resolve_type_key(type_key) or type_key
    typedef = get_type_def(canonical)
    if typedef is None:
        return {"ok": False, "error": "unknown_type", "sent": 0}

    setting = get_or_create_setting(db, canonical)
    if not setting.enabled and not force:
        return {"ok": False, "error": "type_disabled", "sent": 0}

    ctx = dict(context or {})
    if recipient_user_ids:
        ctx["recipient_user_ids"] = [str(u) for u in recipient_user_ids]

    audience_key = setting.audience or typedef.default_audience
    recipients = resolve_notification_audience(
        db,
        audience=audience_key,
        context=ctx,
        filters=setting.audience_filters or {},
    )
    if not recipients and recipient_user_ids:
        recipients = list(recipient_user_ids)

    tmpl = _load_template(db, setting_template_id=setting.template_id, type_key=canonical)
    render_ctx = {
        **ctx,
        "brand": "Pàdéyá",
        "host_name": ctx.get("host_name") or "a host",
        "event_title": ctx.get("event_title") or "an event",
        "item_title": ctx.get("item_title") or ctx.get("product_name") or "a drop",
    }
    final_title = (title or (render_template(tmpl.title_template, render_ctx) if tmpl else typedef.label))[
        :160
    ]
    final_body = (
        body
        or (render_template(tmpl.body_template, render_ctx) if tmpl else typedef.description)
    )[:240]
    final_link = safe_action_url(
        link_path
        or (render_template(tmpl.cta_url_template or "", render_ctx) if tmpl else None)
        or "/dashboard/notifications"
    )

    sent = 0
    skipped = 0
    failed = 0
    for user_id in recipients:
        user = db.get(User, user_id)
        if user is None:
            skipped += 1
            continue
        per_dedupe = dedupe_key or f"{canonical}:{ctx.get('context_id') or ''}:{user_id}"

        # in-app
        if setting.channel_in_app or force:
            ok, reason = should_send_notification(
                db, type_key=canonical, user=user, context=ctx, channel="in_app"
            )
            if force:
                ok, reason = True, None
            if ok and not dedupe_notification(
                db,
                type_key=canonical,
                user_id=user_id,
                dedupe_key=per_dedupe,
                channel="in_app",
            ):
                delivery = NotificationDelivery(
                    type_key=canonical,
                    recipient_user_id=user_id,
                    channel="in_app",
                    status="pending",
                    dedupe_key=per_dedupe,
                    campaign_id=campaign_id,
                    created_by_admin_id=created_by_admin_id,
                )
                db.add(delivery)
                db.flush()
                try:
                    row = notify_user(
                        db,
                        user_id=user_id,
                        kind=canonical,
                        title=final_title,
                        body=final_body,
                        link_path=final_link,
                        dedupe_key=per_dedupe,
                        send_push=False,  # push handled separately for channel control
                        force_push=False,
                    )
                    delivery.status = "sent"
                    delivery.sent_at = datetime.now(UTC)
                    delivery.in_app_notification_id = getattr(row, "id", None)
                    sent += 1
                except Exception as exc:  # noqa: BLE001
                    delivery.status = "failed"
                    delivery.failed_at = datetime.now(UTC)
                    delivery.error_reason = str(exc)[:240]
                    failed += 1
            else:
                skipped += 1

        # push
        if setting.channel_push or (force and campaign_id):
            ok, reason = should_send_notification(
                db, type_key=canonical, user=user, context=ctx, channel="push"
            )
            if force and campaign_id:
                ok = True
            if ok and not dedupe_notification(
                db,
                type_key=canonical,
                user_id=user_id,
                dedupe_key=per_dedupe,
                channel="push",
            ):
                delivery = NotificationDelivery(
                    type_key=canonical,
                    recipient_user_id=user_id,
                    channel="push",
                    status="pending",
                    dedupe_key=per_dedupe,
                    campaign_id=campaign_id,
                    created_by_admin_id=created_by_admin_id,
                )
                db.add(delivery)
                db.flush()
                try:
                    from app.push.service import enqueue_push
                    from app.push.templates import resolve_template_name

                    push_template = resolve_template_name(canonical)
                    push_ctx: dict = {
                        "kind": canonical,
                        "action_url": final_link,
                    }
                    if push_template == "generic":
                        push_ctx["title"] = final_title
                        push_ctx["body"] = final_body

                    event = enqueue_push(
                        db,
                        template=push_template,
                        recipient_user_id=user_id,
                        context=push_ctx,
                        dedupe_key=f"push:{per_dedupe}",
                        force=bool(force or setting.classification == "critical"),
                        preference_kind=canonical,
                    )
                    if event is None or getattr(event, "status", None) == "skipped":
                        delivery.status = "skipped"
                        delivery.error_reason = getattr(event, "error_message", None) or reason
                        skipped += 1
                    else:
                        delivery.status = "sent"
                        delivery.sent_at = datetime.now(UTC)
                        sent += 1
                except Exception as exc:  # noqa: BLE001
                    delivery.status = "failed"
                    delivery.failed_at = datetime.now(UTC)
                    delivery.error_reason = str(exc)[:240]
                    failed += 1
            elif not ok:
                skipped += 1

        # email
        if setting.channel_email:
            ok, reason = should_send_notification(
                db, type_key=canonical, user=user, context=ctx, channel="email"
            )
            if force and campaign_id:
                ok = True
            if ok and user.email and not dedupe_notification(
                db,
                type_key=canonical,
                user_id=user_id,
                dedupe_key=per_dedupe,
                channel="email",
            ):
                delivery = NotificationDelivery(
                    type_key=canonical,
                    recipient_user_id=user_id,
                    channel="email",
                    status="pending",
                    dedupe_key=per_dedupe,
                    campaign_id=campaign_id,
                    created_by_admin_id=created_by_admin_id,
                )
                db.add(delivery)
                db.flush()
                try:
                    email_key = (
                        (tmpl.email_template_key if tmpl else None)
                        or typedef.email_template
                    )
                    if email_key:
                        enqueue_template(
                            db,
                            template=email_key,
                            to=user.email,
                            recipient_user_id=user_id,
                            dedupe_key=f"email:{per_dedupe}",
                            context=render_ctx,
                            force=bool(force or setting.classification == "critical"),
                        )
                    else:
                        # Generic admin/custom — use security-safe simple template if available
                        enqueue_template(
                            db,
                            template="security_alert",
                            to=user.email,
                            recipient_user_id=user_id,
                            dedupe_key=f"email:{per_dedupe}",
                            context={
                                "alert_title": final_title,
                                "alert_body": final_body,
                            },
                            force=True,
                        )
                    delivery.status = "sent"
                    delivery.sent_at = datetime.now(UTC)
                    sent += 1
                except Exception as exc:  # noqa: BLE001
                    delivery.status = "failed"
                    delivery.failed_at = datetime.now(UTC)
                    delivery.error_reason = str(exc)[:240]
                    failed += 1
            elif not ok:
                skipped += 1

    db.flush()
    return {
        "ok": True,
        "type_key": canonical,
        "audience": audience_key,
        "recipient_count": len(recipients),
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "title": final_title,
    }


def dispatch_typed(
    db: Session,
    *,
    type_key: str,
    recipient_user_id: uuid.UUID | None = None,
    recipient_user_ids: list[uuid.UUID] | None = None,
    context: dict[str, Any] | None = None,
    title: str | None = None,
    body: str | None = None,
    link_path: str | None = None,
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    """Convenience entry for product code."""
    ids = list(recipient_user_ids or [])
    if recipient_user_id is not None:
        ids.append(recipient_user_id)
    return send_notification(
        db,
        type_key=type_key,
        context=context,
        recipient_user_ids=ids or None,
        title=title,
        body=body,
        link_path=link_path,
        dedupe_key=dedupe_key,
    )
