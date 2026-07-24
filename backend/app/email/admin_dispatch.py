"""Dispatch admin platform emails to configured recipient groups."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.admin_catalog import build_admin_lines, catalog_entry
from app.email.admin_recipients import resolve_admin_template_recipient_list
from app.email.admin_template_service import (
    effective_delivery_mode,
    effective_enabled,
    effective_threshold,
    ensure_admin_template_rows,
    get_global_admin_email_settings,
)
from app.email.models import EmailAdminTemplate
from app.email.service import enqueue_template

logger = logging.getLogger("padeya.email.admin")


def notify_admins_platform_email(
    db: Session,
    *,
    template_key: str,
    context: dict[str, Any],
    dedupe_key: str,
    entity_id: UUID | str | None = None,
) -> int:
    """Enqueue one outbox row per recipient (individual To, per-recipient tracking)."""
    entry = catalog_entry(template_key)
    if entry is None:
        logger.warning("unknown admin template key=%s", template_key)
        return 0

    ensure_admin_template_rows(db)
    row = db.scalar(select(EmailAdminTemplate).where(EmailAdminTemplate.key == template_key))
    settings = get_global_admin_email_settings(db)
    if not settings.master_enabled:
        return 0

    if not effective_enabled(entry, row):
        return 0

    delivery = effective_delivery_mode(row, entry)
    if delivery == "disabled":
        return 0
    if delivery == "digest":
        return 0

    threshold = effective_threshold(row, entry)
    if threshold is not None:
        try:
            amount = float(context.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount < threshold:
            return 0

    recipients = resolve_admin_template_recipient_list(db, template_key=template_key, row=row)
    if not recipients:
        return 0

    ctx = dict(context)
    ctx.setdefault("preview_text", entry.preview_text)
    ctx["admin_lines"] = build_admin_lines(entry, ctx)
    if entity_id is not None:
        ctx.setdefault("entity_id_safe", str(entity_id))

    sent = 0
    for user, email in recipients:
        user_part = str(user.id) if user else email
        dkey = f"{dedupe_key}:admin:{user_part}"
        enqueue_template(
            db,
            template=template_key,
            to=email,
            recipient_user_id=user.id if user else None,
            context=ctx,
            dedupe_key=dkey,
            force=True,
        )
        sent += 1
    return sent
