"""Lightweight email audit helpers (application log + optional audit_log)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger("padeya.email.audit")


def log_email_event(
    *,
    action: str,
    email_event_id: UUID | None,
    template: str,
    recipient: str,
    detail: str | None = None,
) -> None:
    logger.info(
        "email_audit action=%s id=%s template=%s to=%s detail=%s",
        action,
        email_event_id,
        template,
        recipient,
        detail,
    )


def write_email_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: UUID | None,
    email_event_id: UUID,
    details: dict | None = None,
) -> None:
    try:
        from app.core.audit import write_audit_log

        write_audit_log(
            db,
            action=action,
            actor_user_id=actor_user_id,
            resource_type="email_event",
            resource_id=str(email_event_id),
            details=details,
        )
    except Exception:  # noqa: BLE001 — audit must not break send path
        logger.exception("failed to write email audit for %s", email_event_id)
