"""Email outbox — enqueue + drain pending events."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.email.audit import log_email_event, write_email_audit
from app.email.config import email_runtime, provider_mode_label
from app.email.models import EmailEvent
from app.email.prefs import preference_allows
from app.email.provider import OutboundEmail, get_email_provider
from app.email.templates import get_template

logger = logging.getLogger("padeya.email.queue")

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


def enqueue_email_event(
    db: Session,
    *,
    template: str,
    to: str,
    context: dict[str, Any] | None = None,
    recipient_user_id: UUID | None = None,
    dedupe_key: str | None = None,
    force: bool = False,
) -> EmailEvent | None:
    """Create a pending email_events row. Does not send.

    Returns existing row when dedupe_key already present (idempotent webhooks).
    Returns None when skipped by preferences or EMAIL_ENABLED=false.
    """
    cfg = email_runtime(db=db)
    to_norm = (to or "").strip().lower()
    if not to_norm or "@" not in to_norm:
        return None

    if dedupe_key:
        existing = db.scalar(
            select(EmailEvent).where(EmailEvent.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return existing

    tmpl = get_template(template)
    allowed, reason = preference_allows(
        db, user_id=recipient_user_id, template_name=template, force=force
    )
    ctx = dict(context or {})
    from app.email.admin_template_service import render_template_for_queue

    subject, text, html = render_template_for_queue(template, ctx, db=db)

    status = "pending"
    error_message = None
    if not cfg.enabled:
        status = "skipped"
        error_message = "EMAIL_ENABLED=false"
    elif not allowed:
        status = "skipped"
        error_message = reason

    event = EmailEvent(
        template=template,
        recipient_email=to_norm,
        recipient_user_id=recipient_user_id,
        subject=subject,
        status=status,
        provider=cfg.provider,
        context_json=ctx,
        error_message=error_message,
        attempts=0,
        dedupe_key=dedupe_key,
        preference_key=tmpl.preference_key,
        body_text=text if cfg.dev_mode or cfg.log_body_in_dev else None,
        body_html=html if cfg.dev_mode or cfg.log_body_in_dev else None,
    )
    # Nested savepoint so unique-dedupe races never roll back the caller txn
    # (critical inside Paystack finalize).
    try:
        with db.begin_nested():
            db.add(event)
            db.flush()
    except IntegrityError:
        if dedupe_key:
            return db.scalar(
                select(EmailEvent).where(EmailEvent.dedupe_key == dedupe_key)
            )
        raise

    log_email_event(
        action=status if status == "skipped" else "enqueued",
        email_event_id=event.id,
        template=template,
        recipient=to_norm,
        detail=error_message,
    )
    return event


def deliver_email_event(db: Session, event: EmailEvent) -> EmailEvent:
    """Attempt delivery for one event."""
    cfg = email_runtime(db=db)
    if event.status in {"sent", "skipped"}:
        return event
    if event.attempts >= MAX_ATTEMPTS:
        event.status = "failed"
        event.error_message = event.error_message or "max_attempts"
        db.flush()
        return event

    from app.email.admin_template_service import render_template_for_queue

    subject, text, html = render_template_for_queue(
        event.template, event.context_json or {}, db=db
    )
    event.subject = subject
    if cfg.dev_mode or cfg.log_body_in_dev:
        event.body_text = text
        event.body_html = html

    event.attempts += 1
    event.last_attempt_at = datetime.now(UTC)
    provider = get_email_provider(db=db)
    from app.email.provider import EmailAttachment, OutboundEmail
    from app.payments.order_pdf import resolve_email_attachments_for_event

    pdf_attachments = resolve_email_attachments_for_event(db, event)
    attachments = tuple(
        EmailAttachment(
            filename=att.filename,
            content=att.content,
            mime_type=att.mime_type,
        )
        for att in pdf_attachments
    )
    result = provider.send(
        OutboundEmail(
            to=event.recipient_email,
            subject=subject,
            text=text,
            html=html,
            from_email=cfg.from_email,
            from_name=cfg.from_name,
            reply_to=cfg.reply_to,
            metadata={
                "email_event_id": str(event.id),
                "template": event.template,
                "dedupe_key": event.dedupe_key,
            },
            attachments=attachments,
        )
    )
    event.provider = result.provider
    event.provider_message_id = result.provider_message_id
    if result.skipped and result.ok:
        event.status = "skipped"
        event.error_message = result.error
    elif result.ok:
        event.status = "sent"
        event.sent_at = datetime.now(UTC)
        event.error_message = None
        try:
            from app.email.settings_service import mark_successful_send

            mark_successful_send(db)
        except Exception:  # noqa: BLE001
            pass
    else:
        event.status = "failed" if event.attempts >= MAX_ATTEMPTS else "pending"
        event.error_message = result.error
    db.flush()
    log_email_event(
        action=event.status,
        email_event_id=event.id,
        template=event.template,
        recipient=event.recipient_email,
        detail=event.error_message,
    )
    return event


def count_by_status(db: Session, status: str) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(EmailEvent).where(EmailEvent.status == status)
        )
        or 0
    )


def drain_email_outbox(db: Session, *, limit: int = 50, commit: bool = True) -> DrainStats:
    """Drain pending email events and return safe health stats (no bodies/secrets)."""
    pending_before = count_by_status(db, "pending")
    rows = list(
        db.scalars(
            select(EmailEvent)
            .where(
                EmailEvent.status == "pending",
                EmailEvent.attempts < MAX_ATTEMPTS,
            )
            .order_by(EmailEvent.created_at.asc())
            .limit(limit)
        )
    )
    sent = failed = skipped = 0
    for row in rows:
        deliver_email_event(db, row)
        if row.status == "sent":
            sent += 1
        elif row.status == "failed":
            failed += 1
        elif row.status == "skipped":
            skipped += 1
        elif row.status == "pending":
            # Retriable failure kept pending
            failed += 1
    if commit:
        db.commit()
    else:
        db.flush()
    still_pending = count_by_status(db, "pending")
    return DrainStats(
        pending_before=pending_before,
        attempted=len(rows),
        sent=sent,
        failed=failed,
        skipped=skipped,
        still_pending=still_pending,
        provider_mode=provider_mode_label(db=db),
    )


def process_pending_emails(db: Session, *, limit: int = 50, commit: bool = True) -> int:
    """Drain pending email events. Returns count attempted (backward compatible)."""
    return drain_email_outbox(db, limit=limit, commit=commit).attempted


def resend_email_event(
    db: Session,
    *,
    event_id: UUID,
    actor_user_id: UUID | None,
) -> EmailEvent:
    event = db.get(EmailEvent, event_id)
    if event is None:
        raise LookupError("Email event not found")
    event.status = "pending"
    event.error_message = None
    # Allow another attempt window
    if event.attempts >= MAX_ATTEMPTS:
        event.attempts = MAX_ATTEMPTS - 1
    db.flush()
    write_email_audit(
        db,
        action="emails.resend",
        actor_user_id=actor_user_id,
        email_event_id=event.id,
        details={"template": event.template},
    )
    deliver_email_event(db, event)
    db.commit()
    db.refresh(event)
    return event
