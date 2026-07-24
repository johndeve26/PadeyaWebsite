"""Email provider abstraction — SMTP first; Postmark/Brevo/Resend/SendGrid later."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.email.config import EmailRuntimeConfig, email_runtime, production_email_ready
from app.email.smtp_errors import humanize_smtp_error_for_admin

logger = logging.getLogger("padeya.email")


def _safe_error_text(
    exc: BaseException,
    *,
    cfg: EmailRuntimeConfig | None = None,
) -> str:
    """Strip credentials from exception text before logging/storing."""
    text = str(exc)[:500]
    runtime = cfg or email_runtime()
    if runtime.smtp_password:
        text = text.replace(runtime.smtp_password, "***")
    if runtime.smtp_username:
        text = text.replace(runtime.smtp_username, "***")
    return text


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


@dataclass
class OutboundEmail:
    to: str
    subject: str
    text: str
    html: str
    from_email: str
    from_name: str
    reply_to: str | None = None
    metadata: dict | None = None
    attachments: tuple[EmailAttachment, ...] = ()


@dataclass
class SendResult:
    ok: bool
    provider: str
    provider_message_id: str | None = None
    error: str | None = None
    skipped: bool = False


class EmailProvider(Protocol):
    name: str

    def send(self, message: OutboundEmail) -> SendResult: ...


class LogEmailProvider:
    """Dev/default — log only, never hits the network."""

    name = "log"

    def __init__(self, cfg: EmailRuntimeConfig | None = None) -> None:
        self._cfg = cfg

    def send(self, message: OutboundEmail) -> SendResult:
        cfg = self._cfg or email_runtime()
        settings = get_settings()
        # Never log full bodies in production — even if EMAIL_LOG_BODY_IN_DEV is set.
        allow_body = bool(cfg.log_body_in_dev) and not settings.is_production
        body_preview = message.text if allow_body else f"({len(message.text)} chars)"
        logger.info(
            "EMAIL[%s] to=%s subject=%s body=%s meta=%s",
            self.name,
            message.to,
            message.subject,
            body_preview,
            message.metadata,
        )
        print(f"[email:{self.name}] to={message.to} subject={message.subject!r}")
        if allow_body:
            out = Path("tmp/email_outbox")
            out.mkdir(parents=True, exist_ok=True)
            safe = message.to.replace("@", "_at_").replace("/", "_")[:80]
            path = out / f"{safe}_{abs(hash(message.subject)) % 10_000_000}.txt"
            path.write_text(
                f"To: {message.to}\nSubject: {message.subject}\n\n{message.text}\n",
                encoding="utf-8",
            )
            for attachment in message.attachments:
                att_path = out / f"{safe}_{attachment.filename}"
                att_path.write_bytes(attachment.content)
        return SendResult(ok=True, provider=self.name, provider_message_id="log")


class MisconfiguredEmailProvider:
    """Fails every send with a clear config error — used when production SMTP is broken."""

    name = "misconfigured"

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def send(self, message: OutboundEmail) -> SendResult:
        logger.error(
            "EMAIL misconfigured — refusing send template_meta=%s reason=%s",
            message.metadata,
            self.reason,
        )
        return SendResult(
            ok=False,
            provider=self.name,
            error=self.reason[:500],
            skipped=False,
        )


class SmtpEmailProvider:
    name = "smtp"

    def __init__(self, cfg: EmailRuntimeConfig | None = None) -> None:
        self._cfg = cfg

    def send(self, message: OutboundEmail) -> SendResult:
        import ssl

        cfg = self._cfg or email_runtime()
        if not cfg.smtp_host:
            return SendResult(
                ok=False,
                provider=self.name,
                error="SMTP host not configured",
                skipped=False,
            )
        if cfg.smtp_use_tls and cfg.smtp_use_ssl:
            return SendResult(
                ok=False,
                provider=self.name,
                error="Invalid SMTP security: TLS and SSL both enabled",
                skipped=False,
            )
        msg = EmailMessage()
        msg["Subject"] = message.subject
        msg["From"] = f"{message.from_name} <{message.from_email}>"
        msg["To"] = message.to
        if message.reply_to:
            msg["Reply-To"] = message.reply_to
        msg.set_content(message.text)
        msg.add_alternative(message.html, subtype="html")
        for attachment in message.attachments:
            main, _, sub = (attachment.mime_type or "application/pdf").partition("/")
            msg.add_attachment(
                attachment.content,
                maintype=main or "application",
                subtype=sub or "pdf",
                filename=attachment.filename,
            )
        port = int(cfg.smtp_port or (465 if cfg.smtp_use_ssl else 587))
        try:
            if cfg.smtp_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    cfg.smtp_host, port, timeout=30, context=context
                ) as smtp:
                    if cfg.smtp_username:
                        smtp.login(cfg.smtp_username, cfg.smtp_password)
                    smtp.send_message(msg)
            elif cfg.smtp_use_tls:
                with smtplib.SMTP(cfg.smtp_host, port, timeout=30) as smtp:
                    smtp.ehlo()
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                    if cfg.smtp_username:
                        smtp.login(cfg.smtp_username, cfg.smtp_password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(cfg.smtp_host, port, timeout=30) as smtp:
                    if cfg.smtp_username:
                        smtp.login(cfg.smtp_username, cfg.smtp_password)
                    smtp.send_message(msg)
            return SendResult(ok=True, provider=self.name, provider_message_id=None)
        except Exception as exc:  # noqa: BLE001
            safe = _safe_error_text(exc, cfg=cfg)
            safe = humanize_smtp_error_for_admin(
                safe,
                from_email=cfg.from_email,
                smtp_username=cfg.smtp_username or None,
            )
            logger.error("SMTP send failed to=%s error=%s", message.to, safe)
            return SendResult(ok=False, provider=self.name, error=safe)


class DisabledEmailProvider:
    name = "disabled"

    def send(self, message: OutboundEmail) -> SendResult:
        logger.info(
            "EMAIL skipped (EMAIL_ENABLED=false) to=%s subject=%s",
            message.to,
            message.subject,
        )
        return SendResult(
            ok=True,
            provider=self.name,
            skipped=True,
            provider_message_id=None,
            error="EMAIL_ENABLED=false",
        )


def get_email_provider(db: Session | None = None) -> EmailProvider:
    cfg = email_runtime(db=db)
    settings = get_settings()
    if not cfg.enabled:
        return DisabledEmailProvider()
    # Dev mode always logs (never real SMTP) even if provider=smtp
    if cfg.dev_mode or cfg.provider in {"log", "console"}:
        return LogEmailProvider(cfg)
    ok, err = production_email_ready(settings, db=db)
    if not ok:
        # Production SMTP misconfig: fail loudly on every send (do not silently log-send).
        logger.error("Email misconfigured — refusing real delivery: %s", err)
        return MisconfiguredEmailProvider(err or "email_misconfigured")
    if cfg.provider == "smtp":
        return SmtpEmailProvider(cfg)
    if cfg.provider in {"postmark", "brevo", "resend", "sendgrid"}:
        reason = f"Provider {cfg.provider} is not implemented yet — configure SMTP or log"
        logger.error("Email provider not implemented: %s", cfg.provider)
        return MisconfiguredEmailProvider(reason)
    logger.warning("Unknown EMAIL_PROVIDER=%s — using log", cfg.provider)
    return LogEmailProvider(cfg)
