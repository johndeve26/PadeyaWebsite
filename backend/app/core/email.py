"""Legacy email shim — prefer ``app.email.service.enqueue_template``.

Kept so older call sites keep working during migration. New code should
enqueue templated events via the email outbox.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from app.core.config import get_settings
from app.email.config import email_runtime
from app.email.provider import OutboundEmail, SendResult, get_email_provider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger("padeya.email")


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str
    metadata: dict | None = None


class EmailProvider(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class LogEmailProvider:
    def send(self, message: EmailMessage) -> None:
        send_email(
            to=message.to,
            subject=message.subject,
            body=message.body,
            metadata=message.metadata,
        )


def get_email_provider_legacy() -> EmailProvider:
    return LogEmailProvider()


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    metadata: dict | None = None,
    db: Session | None = None,
    html: str | None = None,
) -> SendResult:
    """Immediate plain-text send via the central provider (no outbox).

    Prefer enqueue_template for product flows. This remains for CRM blast
    compatibility and transitional call sites.
    """
    cfg = email_runtime(db=db)
    if not cfg.enabled:
        logger.info("EMAIL skipped (disabled) to=%s subject=%s", to, subject)
        return SendResult(
            ok=False,
            provider="disabled",
            skipped=True,
            error="EMAIL_ENABLED=false",
        )
    html_body = html
    if html_body is None:
        html_body = (
            "<html><body><pre style=\"font-family:Georgia,serif;white-space:pre-wrap;\">"
            f"{body}</pre></body></html>"
        )
    return get_email_provider(db=db).send(
        OutboundEmail(
            to=to,
            subject=subject,
            text=body,
            html=html_body,
            from_email=cfg.from_email,
            from_name=cfg.from_name,
            reply_to=cfg.reply_to,
            metadata=metadata,
        )
    )
