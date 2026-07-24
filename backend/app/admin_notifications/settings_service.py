"""Settings + template CRUD + audit helpers."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_notifications.models import (
    NotificationAuditLog,
    NotificationSetting,
    NotificationTemplate,
)
from app.admin_notifications.registry import NOTIFICATION_TYPES, get_type_def
from app.core.audit import write_audit_log


def record_notification_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None,
    resource_type: str,
    resource_id: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    safe = dict(details or {})
    # Never persist bodies / secrets in domain audit.
    for key in ("body", "title", "message", "token", "password", "private_key"):
        safe.pop(key, None)
    row = NotificationAuditLog(
        action=action,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=safe,
    )
    db.add(row)
    write_audit_log(
        db,
        action=action,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=safe,
    )


def ensure_default_settings(db: Session) -> int:
    """Seed missing type settings + system templates. Returns created count."""
    created = 0
    existing = set(db.scalars(select(NotificationSetting.type_key)).all())

    for typedef in NOTIFICATION_TYPES:
        if typedef.key in existing:
            continue
        tmpl = NotificationTemplate(
            type_key=typedef.key,
            name=f"{typedef.label} (system)",
            title_template=typedef.label,
            body_template=typedef.description[:240],
            cta_url_template="/dashboard/notifications",
            email_template_key=typedef.email_template,
            is_system=True,
        )
        db.add(tmpl)
        db.flush()
        row = NotificationSetting(
            type_key=typedef.key,
            enabled=typedef.default_enabled,
            channel_in_app="in_app" in typedef.default_channels,
            channel_push="push" in typedef.default_channels,
            channel_email="email" in typedef.default_channels,
            audience=typedef.default_audience,
            template_id=tmpl.id,
            cooldown_seconds=typedef.default_cooldown_seconds,
            send_mode="queued" if typedef.default_queued else "immediate",
            classification=typedef.classification,
            respect_user_prefs=typedef.respect_user_prefs,
            audience_filters={},
        )
        db.add(row)
        created += 1
    if created:
        db.flush()
    return created


def get_or_create_setting(db: Session, type_key: str) -> NotificationSetting:
    ensure_default_settings(db)
    row = db.scalar(
        select(NotificationSetting).where(NotificationSetting.type_key == type_key)
    )
    if row is None:
        raise ValueError(f"Unknown notification type: {type_key}")
    return row


def list_settings(db: Session) -> list[dict[str, Any]]:
    ensure_default_settings(db)
    rows = list(db.scalars(select(NotificationSetting).order_by(NotificationSetting.type_key)))
    out = []
    for row in rows:
        typedef = get_type_def(row.type_key)
        out.append(serialize_setting(row, typedef))
    return out


def serialize_setting(row: NotificationSetting, typedef=None) -> dict[str, Any]:
    typedef = typedef or get_type_def(row.type_key)
    push_unavailable_reason: str | None = None
    if typedef:
        from app.notifications.channel_registry import push_channel_allowed

        probe_kind = (typedef.kind_aliases or (typedef.key,))[0]
        allowed, reason = push_channel_allowed(probe_kind)
        if not allowed:
            push_unavailable_reason = reason
    return {
        "id": str(row.id),
        "type_key": row.type_key,
        "label": typedef.label if typedef else row.type_key,
        "description": typedef.description if typedef else "",
        "critical": bool(typedef.critical) if typedef else False,
        "enabled": bool(row.enabled),
        "channels": {
            "in_app": bool(row.channel_in_app),
            "push": bool(row.channel_push),
            "email": bool(row.channel_email),
        },
        "push_unavailable_reason": push_unavailable_reason,
        "audience": row.audience,
        "template_id": str(row.template_id) if row.template_id else None,
        "cooldown_seconds": int(row.cooldown_seconds or 0),
        "send_mode": row.send_mode,
        "classification": row.classification,
        "respect_user_prefs": bool(row.respect_user_prefs),
        "audience_filters": row.audience_filters or {},
        "updated_at": row.updated_at,
    }


def update_setting(
    db: Session,
    *,
    type_key: str,
    updates: dict[str, Any],
    actor_user_id: uuid.UUID,
    actor_is_super_admin: bool,
) -> dict[str, Any]:
    row = get_or_create_setting(db, type_key)
    typedef = get_type_def(type_key)
    if typedef and typedef.critical and "enabled" in updates:
        if updates["enabled"] is False and not actor_is_super_admin:
            raise PermissionError(
                "Only super_admin can disable critical notification types"
            )

    if "enabled" in updates and updates["enabled"] is not None:
        row.enabled = bool(updates["enabled"])
    channels = updates.get("channels") or {}
    if "in_app" in channels:
        row.channel_in_app = bool(channels["in_app"])
    if "push" in channels:
        row.channel_push = bool(channels["push"])
    if "email" in channels:
        row.channel_email = bool(channels["email"])
    for field in (
        "audience",
        "send_mode",
        "classification",
        "cooldown_seconds",
        "respect_user_prefs",
        "audience_filters",
    ):
        if field in updates and updates[field] is not None:
            setattr(row, field, updates[field])
    if "template_id" in updates:
        tid = updates["template_id"]
        row.template_id = uuid.UUID(str(tid)) if tid else None
    row.updated_by_user_id = actor_user_id
    db.flush()
    record_notification_audit(
        db,
        action="notification.setting_changed",
        actor_user_id=actor_user_id,
        resource_type="notification_setting",
        resource_id=str(row.id),
        details={
            "type_key": type_key,
            "enabled": row.enabled,
            "channels": {
                "in_app": row.channel_in_app,
                "push": row.channel_push,
                "email": row.channel_email,
            },
            "audience": row.audience,
        },
    )
    return serialize_setting(row, typedef)


def list_templates(db: Session, *, include_archived: bool = False) -> list[dict]:
    stmt = select(NotificationTemplate).order_by(NotificationTemplate.name)
    if not include_archived:
        stmt = stmt.where(NotificationTemplate.archived_at.is_(None))
    rows = list(db.scalars(stmt))
    return [serialize_template(r) for r in rows]


def serialize_template(row: NotificationTemplate) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "type_key": row.type_key,
        "name": row.name,
        "title_template": row.title_template,
        "body_template": row.body_template,
        "cta_text": row.cta_text,
        "cta_url_template": row.cta_url_template,
        "email_template_key": row.email_template_key,
        "is_system": bool(row.is_system),
        "archived_at": row.archived_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def create_template(
    db: Session,
    *,
    payload: dict[str, Any],
    actor_user_id: uuid.UUID,
) -> dict[str, Any]:
    row = NotificationTemplate(
        type_key=payload.get("type_key"),
        name=str(payload["name"]).strip()[:120],
        title_template=str(payload["title_template"]).strip()[:200],
        body_template=str(payload["body_template"]).strip()[:500],
        cta_text=(str(payload["cta_text"]).strip()[:80] if payload.get("cta_text") else None),
        cta_url_template=(
            str(payload["cta_url_template"]).strip()[:300]
            if payload.get("cta_url_template")
            else None
        ),
        email_template_key=payload.get("email_template_key"),
        is_system=False,
        created_by_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    record_notification_audit(
        db,
        action="notification.template_changed",
        actor_user_id=actor_user_id,
        resource_type="notification_template",
        resource_id=str(row.id),
        details={"name": row.name, "type_key": row.type_key, "op": "create"},
    )
    return serialize_template(row)


def update_template(
    db: Session,
    *,
    template_id: uuid.UUID,
    payload: dict[str, Any],
    actor_user_id: uuid.UUID,
) -> dict[str, Any]:
    row = db.get(NotificationTemplate, template_id)
    if row is None or row.archived_at is not None:
        raise ValueError("Template not found")
    for key in (
        "name",
        "title_template",
        "body_template",
        "cta_text",
        "cta_url_template",
        "email_template_key",
        "type_key",
    ):
        if key in payload and payload[key] is not None:
            setattr(row, key, payload[key])
    db.flush()
    record_notification_audit(
        db,
        action="notification.template_changed",
        actor_user_id=actor_user_id,
        resource_type="notification_template",
        resource_id=str(row.id),
        details={"name": row.name, "op": "update"},
    )
    return serialize_template(row)
