"""Merge catalog defaults with DB overrides, safe render, preview, test send."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.email.admin_catalog import (
    ADMIN_TEMPLATE_CATALOG,
    AdminTemplateCatalogEntry,
    build_admin_lines,
    catalog_entry,
    sample_context_for,
)
from app.email.admin_recipients import (
    MAX_RECIPIENTS_PER_TEMPLATE,
    MAX_TEST_RECIPIENTS,
    RECIPIENT_MODES,
    effective_recipient_group,
    effective_recipient_mode,
    parse_recipient_emails_http,
    resolve_admin_template_recipient_list,
)
from app.email.models import EmailAdminNotificationSettings, EmailAdminTemplate
from app.email.config import email_runtime
from app.email.renderer import render_html, render_plain
from app.email.service import send_template
from app.email.templates import TemplateDef, assert_brand_safe, get_template, render_subject

_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

FORBIDDEN_CONTEXT_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "card",
        "pan",
        "cvv",
        "webhook_payload",
        "payment_payload",
    }
)


def _sanitize_context(raw: dict[str, Any], allowed: frozenset[str]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, val in raw.items():
        if key in FORBIDDEN_CONTEXT_KEYS:
            continue
        if allowed and key not in allowed and key not in ("cta_path", "cta_url", "cta_label", "preview_text", "admin_lines"):
            continue
        if val is None:
            continue
        clean[key] = str(val)[:2000]
    return clean


def ensure_admin_template_rows(db: Session) -> None:
    existing = {row.key for row in db.scalars(select(EmailAdminTemplate)).all()}
    for key, entry in ADMIN_TEMPLATE_CATALOG.items():
        if key in existing:
            continue
        db.add(
            EmailAdminTemplate(
                key=key,
                category=entry.category,
                title=entry.title,
                subject=None,
                preview_text=None,
                html_body=None,
                text_body=None,
                variables_schema=list(entry.variables),
                is_required=entry.required,
                is_enabled=entry.default_enabled,
                default_recipient_group=entry.default_recipient_group,
                recipient_mode=(
                    "custom" if entry.default_recipient_group == "custom" else "group"
                ),
                recipient_group=None,
                custom_recipient_emails=[],
                delivery_mode=entry.delivery_mode,
                threshold_amount=entry.threshold_amount,
            )
        )


def get_global_admin_email_settings(db: Session) -> EmailAdminNotificationSettings:
    row = db.scalar(select(EmailAdminNotificationSettings).limit(1))
    if row is None:
        row = EmailAdminNotificationSettings()
        db.add(row)
        db.flush()
    return row


def _merged_entry(db: Session, key: str) -> tuple[AdminTemplateCatalogEntry, EmailAdminTemplate | None]:
    cat = catalog_entry(key)
    if cat is None:
        raise HTTPException(status_code=404, detail="Unknown admin template")
    row = db.scalar(select(EmailAdminTemplate).where(EmailAdminTemplate.key == key))
    return cat, row


def effective_enabled(cat: AdminTemplateCatalogEntry, row: EmailAdminTemplate | None) -> bool:
    if row is not None and row.is_enabled is not None:
        return bool(row.is_enabled)
    return bool(cat.default_enabled)


def effective_delivery_mode(row: EmailAdminTemplate | None, cat: AdminTemplateCatalogEntry) -> str:
    if row is not None and row.delivery_mode:
        return row.delivery_mode
    return cat.delivery_mode


def effective_threshold(row: EmailAdminTemplate | None, cat: AdminTemplateCatalogEntry) -> float | None:
    if row is not None and row.threshold_amount is not None:
        return row.threshold_amount
    return cat.threshold_amount


def serialize_admin_template(
    db: Session,
    key: str,
    *,
    include_bodies: bool = False,
    mask_recipient_emails: bool = False,
) -> dict[str, Any]:
    ensure_admin_template_rows(db)
    cat, row = _merged_entry(db, key)
    if row is None:
        ensure_admin_template_rows(db)
        db.flush()
        row = db.scalar(select(EmailAdminTemplate).where(EmailAdminTemplate.key == key))
    assert row is not None
    reg = get_template(key)
    mode = effective_recipient_mode(row, default_group=cat.default_recipient_group)
    custom_emails = list(row.custom_recipient_emails or [])
    resolved = resolve_admin_template_recipient_list(db, template_key=key, row=row)
    return {
        "key": key,
        "title": row.title or cat.title,
        "category": row.category,
        "is_required": row.is_required,
        "is_enabled": effective_enabled(cat, row),
        "default_enabled": cat.default_enabled,
        "recipient_mode": mode,
        "recipient_group": effective_recipient_group(cat, row),
        "default_recipient_group": cat.default_recipient_group,
        "custom_recipient_emails": [] if mask_recipient_emails else custom_emails,
        "recipient_emails_display": (
            None if mask_recipient_emails else ", ".join(custom_emails)
        ),
        "resolved_recipient_count": len(resolved),
        "max_recipients": MAX_RECIPIENTS_PER_TEMPLATE,
        "delivery_mode": effective_delivery_mode(row, cat),
        "threshold_amount": effective_threshold(row, cat),
        "variables": list(row.variables_schema or cat.variables),
        "subject": row.subject or cat.subject,
        "default_subject": cat.subject,
        "preview_text": row.preview_text or cat.preview_text,
        "default_preview_text": cat.preview_text,
        "headline": cat.headline,
        "html_body": row.html_body if include_bodies else None,
        "text_body": row.text_body if include_bodies else None,
        "default_html_body": None,
        "default_text_body": None,
        "registry_subject": reg.subject,
        "updated_at": row.updated_at,
        "updated_by_admin_id": row.updated_by_admin_id,
    }


def list_admin_templates(
    db: Session,
    *,
    category: str | None = None,
    q: str | None = None,
    mask_recipient_emails: bool = False,
) -> list[dict[str, Any]]:
    ensure_admin_template_rows(db)
    db.flush()
    keys = sorted(ADMIN_TEMPLATE_CATALOG.keys())
    items = [
        serialize_admin_template(db, k, mask_recipient_emails=mask_recipient_emails)
        for k in keys
    ]
    if category:
        items = [i for i in items if i["category"] == category]
    if q:
        needle = q.lower().strip()
        items = [
            i
            for i in items
            if needle in i["key"].lower() or needle in i["title"].lower()
        ]
    return items


def _substitute(
    template: str, context: dict[str, str], *, scrub: Iterable[str] = ()
) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        return context.get(name, "")

    out = _VAR_PATTERN.sub(repl, template)
    assert_brand_safe(out, scrub=scrub)
    return out


def _render_with_overrides(
    key: str,
    context: dict[str, Any],
    *,
    db: Session | None,
) -> tuple[str, str, str]:
    cat = catalog_entry(key)
    tmpl = get_template(key)
    ctx = dict(context or {})
    if cat is not None:
        allowed = frozenset(cat.variables)
        safe = _sanitize_context(ctx, allowed)
        safe["preview_text"] = safe.get("preview_text") or cat.preview_text
        safe["admin_lines"] = build_admin_lines(cat, safe)
        ctx = {**ctx, **safe, "admin_lines": safe["admin_lines"]}

    scrub = [str(v) for v in ctx.values() if isinstance(v, str) and v.strip()]

    row = None
    if db is not None:
        row = db.scalar(select(EmailAdminTemplate).where(EmailAdminTemplate.key == key))

    subject_base = (row.subject if row and row.subject else None) or (
        cat.subject if cat else tmpl.subject
    )
    subject = _substitute(
        subject_base, {k: str(v) for k, v in ctx.items()}, scrub=scrub
    )
    if not subject:
        subject = render_subject(tmpl, ctx)

    if row and row.text_body:
        text = _substitute(
            row.text_body, {k: str(v) for k, v in ctx.items()}, scrub=scrub
        )
    else:
        cfg = email_runtime(db=db)
        text = render_plain(tmpl, ctx, base_url=cfg.app_base_url, support_email=cfg.support_email)

    if row and row.html_body:
        html_out = _substitute(
            row.html_body,
            {k: html.escape(str(v)) for k, v in ctx.items()},
            scrub=scrub,
        )
    else:
        cfg = email_runtime(db=db)
        html_out = render_html(tmpl, ctx, base_url=cfg.app_base_url, support_email=cfg.support_email)

    assert_brand_safe(text, scrub=scrub)
    return subject, text, html_out


def render_template_for_queue(
    name: str, context: dict[str, Any] | None, *, db: Session | None
) -> tuple[str, str, str]:
    if catalog_entry(name) is not None:
        return _render_with_overrides(name, context or {}, db=db)
    from app.email.renderer import render_template

    return render_template(name, context)


def update_admin_template(
    db: Session,
    *,
    key: str,
    admin_id: UUID,
    updates: dict[str, Any],
    actor: Any | None = None,
) -> dict[str, Any]:
    from app.users.service import user_has_permission

    ensure_admin_template_rows(db)
    cat, row = _merged_entry(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail="Template row missing")
    if cat.required and updates.get("is_enabled") is False:
        raise HTTPException(status_code=400, detail="Required admin templates cannot be disabled")

    recipient_field_keys = {
        "recipient_mode",
        "recipient_group",
        "custom_recipient_emails",
        "recipient_emails",
    }
    if recipient_field_keys & updates.keys() and actor is not None:
        if not user_has_permission(actor, "admin.emails.manage_recipients"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="admin.emails.manage_recipients required to edit recipients",
            )

    if "recipient_emails" in updates:
        raw = updates.pop("recipient_emails")
        if raw is None or str(raw).strip() == "":
            updates["custom_recipient_emails"] = []
        else:
            updates["custom_recipient_emails"] = parse_recipient_emails_http(str(raw))

    if "recipient_mode" in updates and updates["recipient_mode"] not in RECIPIENT_MODES:
        raise HTTPException(status_code=400, detail="Invalid recipient_mode")

    if "custom_recipient_emails" in updates and updates["custom_recipient_emails"] is not None:
        emails = updates["custom_recipient_emails"]
        if isinstance(emails, str):
            updates["custom_recipient_emails"] = parse_recipient_emails_http(emails)
        else:
            joined = ", ".join(str(e) for e in emails)
            updates["custom_recipient_emails"] = parse_recipient_emails_http(joined)

    recipients_changed = bool(recipient_field_keys & set(updates.keys()))

    for field in (
        "subject",
        "preview_text",
        "html_body",
        "text_body",
        "is_enabled",
        "recipient_mode",
        "recipient_group",
        "custom_recipient_emails",
        "delivery_mode",
        "threshold_amount",
    ):
        if field in updates:
            setattr(row, field, updates[field])
    row.updated_by_admin_id = admin_id
    write_audit_log(
        db,
        action="admin.emails.template_updated",
        actor_user_id=admin_id,
        resource_type="email_admin_template",
        resource_id=key,
    )
    if recipients_changed:
        write_audit_log(
            db,
            action="admin.emails.recipients_updated",
            actor_user_id=admin_id,
            resource_type="email_admin_template",
            resource_id=key,
            details={
                "recipient_mode": row.recipient_mode,
                "recipient_count": len(row.custom_recipient_emails or []),
            },
        )
    db.flush()
    mask = False
    if actor is not None:
        mask = not user_has_permission(actor, "admin.emails.manage_recipients")
    return serialize_admin_template(
        db, key, include_bodies=True, mask_recipient_emails=mask
    )


def restore_admin_template_default(db: Session, *, key: str, admin_id: UUID) -> dict[str, Any]:
    ensure_admin_template_rows(db)
    cat, row = _merged_entry(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail="Template row missing")
    row.subject = None
    row.preview_text = None
    row.html_body = None
    row.text_body = None
    row.recipient_group = None
    row.recipient_mode = (
        "custom" if cat.default_recipient_group == "custom" else "group"
    )
    row.custom_recipient_emails = []
    row.delivery_mode = cat.delivery_mode
    row.threshold_amount = cat.threshold_amount
    row.is_enabled = cat.default_enabled
    row.updated_by_admin_id = admin_id
    write_audit_log(
        db,
        action="admin.emails.template_restored",
        actor_user_id=admin_id,
        resource_type="email_admin_template",
        resource_id=key,
    )
    db.flush()
    return serialize_admin_template(db, key, include_bodies=True)


def preview_admin_template(db: Session, key: str, context: dict[str, Any] | None = None) -> dict[str, str]:
    cat = catalog_entry(key)
    if cat is None:
        raise HTTPException(status_code=404, detail="Unknown template")
    ctx = sample_context_for(cat)
    if context:
        ctx.update({k: str(v) for k, v in context.items()})
    subject, text, html_body = _render_with_overrides(key, ctx, db=db)
    return {"subject": subject, "text": text, "html": html_body}


def test_send_admin_template(
    db: Session,
    *,
    key: str,
    admin: Any,
    context: dict[str, Any] | None = None,
    test_recipient_emails: str | None = None,
) -> int:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func, select

    from app.core.audit import AuditLog

    cat = catalog_entry(key)
    if cat is None:
        raise HTTPException(status_code=404, detail="Unknown template")

    since = datetime.now(UTC) - timedelta(minutes=1)
    recent_tests = db.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.action == "admin.emails.template_test_send",
            AuditLog.actor_user_id == admin.id,
            AuditLog.created_at >= since,
        )
    )
    if (recent_tests or 0) >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many test sends — wait a minute and try again.",
        )

    ctx = sample_context_for(cat)
    if context:
        ctx.update({k: str(v) for k, v in context.items() if k != "test_recipient_emails"})
    ctx["preview_text"] = "[TEST] " + (ctx.get("preview_text") or cat.preview_text)

    targets: list[str] = []
    if test_recipient_emails and test_recipient_emails.strip():
        targets = parse_recipient_emails_http(
            test_recipient_emails,
            max_count=MAX_TEST_RECIPIENTS,
        )
    elif admin.email:
        targets = [admin.email.strip().lower()]

    if not targets:
        raise HTTPException(status_code=400, detail="No test recipient email")

    sent = 0
    for email in targets:
        send_template(
            db,
            template=key,
            to=email,
            recipient_user_id=admin.id if email == admin.email.lower() else None,
            context=ctx,
            dedupe_key=None,
            force=True,
            deliver_now=True,
        )
        sent += 1

    write_audit_log(
        db,
        action="admin.emails.template_test_send",
        actor_user_id=admin.id,
        resource_type="email_admin_template",
        resource_id=key,
        details={"recipient_count": sent},
    )
    return sent
