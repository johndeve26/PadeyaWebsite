"""Public email service API used by all product modules."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.email.config import email_runtime
from app.email.queue import deliver_email_event, enqueue_email_event


def enqueue_template(
    db: Session,
    *,
    template: str,
    to: str,
    context: dict[str, Any] | None = None,
    recipient_user_id: UUID | None = None,
    dedupe_key: str | None = None,
    force: bool = False,
):
    """Enqueue a templated email (preferred for payment/webhook paths)."""
    return enqueue_email_event(
        db,
        template=template,
        to=to,
        context=context,
        recipient_user_id=recipient_user_id,
        dedupe_key=dedupe_key,
        force=force,
    )


def send_template(
    db: Session,
    *,
    template: str,
    to: str,
    context: dict[str, Any] | None = None,
    recipient_user_id: UUID | None = None,
    dedupe_key: str | None = None,
    force: bool = False,
    deliver_now: bool | None = None,
):
    """Enqueue and optionally deliver immediately (auth flows, non-webhook).

    Payment/webhook callers should use ``enqueue_template`` only.
    """
    event = enqueue_template(
        db,
        template=template,
        to=to,
        context=context,
        recipient_user_id=recipient_user_id,
        dedupe_key=dedupe_key,
        force=force,
    )
    cfg = email_runtime(db=db)
    should_deliver = (
        deliver_now if deliver_now is not None else (not cfg.queue_enabled)
    )
    if event is not None and event.status == "pending" and should_deliver:
        deliver_email_event(db, event)
    return event
