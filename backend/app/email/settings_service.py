"""Admin-managed email provider settings (Fernet-encrypted SMTP secrets)."""

from __future__ import annotations

import logging
import re
import smtplib
import ssl
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.config import Settings, get_settings
from app.core.encryption import decrypt_secret, encrypt_secret, secret_last4, secret_first4, format_secret_fingerprint, secret_fingerprint_parts
from app.email.config import BRAND_NAME, EmailRuntimeConfig
from app.email.models import EmailEvent, EmailProviderSettings
from app.email.provider import OutboundEmail, get_email_provider
from app.email.smtp_errors import humanize_smtp_error_for_admin, redact_smtp_error_text

logger = logging.getLogger("padeya.email.settings")

ALLOWED_PROVIDERS = frozenset(
    {"log", "console", "smtp", "postmark", "brevo", "resend", "sendgrid"}
)
IMPLEMENTED_PROVIDERS = frozenset({"log", "console", "smtp"})
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _default_seed_row() -> dict[str, Any]:
    """Safe defaults when no active email_provider_settings row exists yet."""
    from_email = "noreply@padeya.com"
    from_name = BRAND_NAME
    reply_to = "support@padeya.com"
    data: dict[str, Any] = {
        "provider": "log",
        "is_active": True,
        "email_enabled": True,
        "dev_mode": True,
        "smtp_host": None,
        "smtp_port": None,
        "smtp_use_tls": True,
        "smtp_use_ssl": False,
        "smtp_from_email": from_email,
        "smtp_from_name": from_name,
        "smtp_reply_to": reply_to,
        "smtp_username_encrypted": None,
        "smtp_password_encrypted": None,
        "smtp_username_last4": None,
        "smtp_password_last4": None,
    }
    return data


def get_active_provider_settings(db: Session) -> EmailProviderSettings | None:
    return db.scalar(
        select(EmailProviderSettings)
        .where(EmailProviderSettings.is_active.is_(True))
        .order_by(EmailProviderSettings.updated_at.desc())
        .limit(1)
    )


def get_or_create_active_settings(
    db: Session,
    *,
    settings: Settings | None = None,
    actor_user_id: UUID | None = None,
) -> EmailProviderSettings:
    del settings  # email product config is admin DB only
    row = get_active_provider_settings(db)
    if row is not None:
        return row
    seed = _default_seed_row()
    row = EmailProviderSettings(
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
        **seed,
    )
    db.add(row)
    db.flush()
    return row


def _decrypt_field(token: str | None) -> str:
    if not token:
        return ""
    try:
        return decrypt_secret(token)
    except Exception:  # noqa: BLE001
        logger.error("Failed to decrypt email settings field — treating as empty")
        return ""


def decrypt_smtp_username(row: EmailProviderSettings) -> str:
    return _decrypt_field(row.smtp_username_encrypted)


def decrypt_smtp_password(row: EmailProviderSettings) -> str:
    return _decrypt_field(row.smtp_password_encrypted)


def apply_admin_override(
    env_cfg: EmailRuntimeConfig,
    row: EmailProviderSettings | None,
) -> EmailRuntimeConfig:
    """Active DB row overrides code defaults. No active row → caller uses email_runtime defaults."""
    if row is None or not row.is_active:
        return env_cfg
    return EmailRuntimeConfig(
        enabled=bool(row.email_enabled),
        provider=(row.provider or "log").strip().lower(),
        dev_mode=bool(row.dev_mode),
        queue_enabled=env_cfg.queue_enabled,
        log_body_in_dev=env_cfg.log_body_in_dev,
        from_email=(row.smtp_from_email or env_cfg.from_email).strip(),
        from_name=(row.smtp_from_name or BRAND_NAME).strip() or BRAND_NAME,
        reply_to=(row.smtp_reply_to or "").strip() or env_cfg.reply_to,
        support_email=env_cfg.support_email,
        app_base_url=env_cfg.app_base_url,
        rate_limit_per_user_per_hour=env_cfg.rate_limit_per_user_per_hour,
        smtp_host=(row.smtp_host or "").strip(),
        smtp_port=int(row.smtp_port or 587),
        smtp_username=decrypt_smtp_username(row),
        smtp_password=decrypt_smtp_password(row),
        smtp_use_tls=bool(row.smtp_use_tls),
        smtp_use_ssl=bool(row.smtp_use_ssl),
    )


def serialize_provider_settings(
    row: EmailProviderSettings,
    *,
    pending_count: int = 0,
    failed_count: int = 0,
) -> dict[str, Any]:
    """Public admin view — never includes decrypted secrets."""
    has_user = bool(row.smtp_username_encrypted)
    has_pass = bool(row.smtp_password_encrypted)
    masked_user = None
    if has_user:
        masked_user = format_secret_fingerprint(
            row.smtp_username_first4, row.smtp_username_last4, prefix=""
        ) or (f"····{row.smtp_username_last4}" if row.smtp_username_last4 else "••••")
    return {
        "id": row.id,
        "provider": row.provider,
        "is_active": bool(row.is_active),
        "email_enabled": bool(row.email_enabled),
        "dev_mode": bool(row.dev_mode),
        "smtp_host": row.smtp_host,
        "smtp_port": row.smtp_port,
        "smtp_use_tls": bool(row.smtp_use_tls),
        "smtp_use_ssl": bool(row.smtp_use_ssl),
        "smtp_from_email": row.smtp_from_email,
        "smtp_from_name": row.smtp_from_name,
        "smtp_reply_to": row.smtp_reply_to,
        "smtp_username_masked": masked_user,
        "smtp_username_first4": row.smtp_username_first4,
        "smtp_username_last4": row.smtp_username_last4,
        "smtp_password_configured": has_pass,
        "smtp_password_first4": row.smtp_password_first4,
        "smtp_password_last4": row.smtp_password_last4,
        "smtp_password_hint": (
            format_secret_fingerprint(
                row.smtp_password_first4, row.smtp_password_last4, prefix=""
            )
            if has_pass and (row.smtp_password_first4 or row.smtp_password_last4)
            else ("••••••••" if has_pass else None)
        ),
        "last_test_status": row.last_test_status,
        "last_test_error": row.last_test_error,
        "last_test_at": row.last_test_at,
        "last_successful_send_at": row.last_successful_send_at,
        "pending_emails_count": pending_count,
        "failed_emails_count": failed_count,
        "created_by_user_id": row.created_by_user_id,
        "updated_by_user_id": row.updated_by_user_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "source": "admin_db",
    }


def _validate_email(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if not EMAIL_RE.match(text):
        raise ValueError(f"Invalid {field} format")
    return text.lower() if field != "smtp_from_name" else text


def _validate_tls_ssl(use_tls: bool, use_ssl: bool) -> None:
    if use_tls and use_ssl:
        raise ValueError("smtp_use_tls and smtp_use_ssl cannot both be true")


def update_provider_settings(
    db: Session,
    *,
    updates: dict[str, Any],
    actor_user_id: UUID | None,
    commit: bool = True,
) -> EmailProviderSettings:
    row = get_or_create_active_settings(db, actor_user_id=actor_user_id)
    password_in = updates.pop("smtp_password", None)
    username_in = updates.pop("smtp_username", None)
    clear_password = bool(updates.pop("clear_smtp_password", False))
    clear_username = bool(updates.pop("clear_smtp_username", False))

    # Map legacy field names from earlier API
    if "enabled" in updates and "email_enabled" not in updates:
        updates["email_enabled"] = updates.pop("enabled")
    if "from_email" in updates and "smtp_from_email" not in updates:
        updates["smtp_from_email"] = updates.pop("from_email")
    if "from_name" in updates and "smtp_from_name" not in updates:
        updates["smtp_from_name"] = updates.pop("from_name")
    if "reply_to" in updates and "smtp_reply_to" not in updates:
        updates["smtp_reply_to"] = updates.pop("reply_to")

    if "provider" in updates and updates["provider"] is not None:
        provider = str(updates["provider"]).strip().lower()
        if provider not in ALLOWED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        row.provider = provider

    for key in ("email_enabled", "dev_mode", "is_active", "smtp_use_tls", "smtp_use_ssl"):
        if key in updates and updates[key] is not None:
            setattr(row, key, bool(updates[key]))

    _validate_tls_ssl(bool(row.smtp_use_tls), bool(row.smtp_use_ssl))

    if "smtp_host" in updates:
        host = (updates["smtp_host"] or "").strip() or None
        row.smtp_host = host

    if "smtp_port" in updates:
        if updates["smtp_port"] is None:
            row.smtp_port = None
        else:
            port = int(updates["smtp_port"])
            if port < 1 or port > 65535:
                raise ValueError("smtp_port must be between 1 and 65535")
            row.smtp_port = port

    if "smtp_from_email" in updates:
        row.smtp_from_email = _validate_email(
            updates["smtp_from_email"], field="smtp_from_email"
        )
    if "smtp_from_name" in updates:
        name = (updates["smtp_from_name"] or "").strip() or BRAND_NAME
        row.smtp_from_name = name
    if "smtp_reply_to" in updates:
        row.smtp_reply_to = _validate_email(
            updates["smtp_reply_to"], field="smtp_reply_to"
        )

    password_rotated = False
    if clear_password:
        row.smtp_password_encrypted = None
        row.smtp_password_last4 = None
        row.smtp_password_first4 = None
        password_rotated = True
    elif password_in is not None and str(password_in).strip():
        plain = str(password_in).strip()
        row.smtp_password_encrypted = encrypt_secret(plain)
        row.smtp_password_first4 = secret_first4(plain)
        row.smtp_password_last4 = secret_last4(plain)
        password_rotated = True

    if clear_username:
        row.smtp_username_encrypted = None
        row.smtp_username_last4 = None
        row.smtp_username_first4 = None
    elif username_in is not None and str(username_in).strip():
        plain_u = str(username_in).strip()
        row.smtp_username_encrypted = encrypt_secret(plain_u)
        row.smtp_username_first4 = secret_first4(plain_u)
        row.smtp_username_last4 = secret_last4(plain_u)

    row.is_active = True
    row.updated_by_user_id = actor_user_id
    if row.created_by_user_id is None:
        row.created_by_user_id = actor_user_id
    db.flush()
    deactivate_other_settings(db, keep_id=row.id)

    write_audit_log(
        db,
        action="emails.provider_settings_update",
        actor_user_id=actor_user_id,
        resource_type="email_provider_settings",
        resource_id=str(row.id),
        details={
            "provider": row.provider,
            "email_enabled": row.email_enabled,
            "dev_mode": row.dev_mode,
            "smtp_from_email": row.smtp_from_email,
            "smtp_host": row.smtp_host,
            "smtp_port": row.smtp_port,
            "smtp_use_tls": row.smtp_use_tls,
            "smtp_use_ssl": row.smtp_use_ssl,
            "smtp_password_updated": password_rotated,
            "smtp_username_updated": bool(
                clear_username or (username_in and str(username_in).strip())
            ),
        },
    )
    if commit:
        db.commit()
        db.refresh(row)
    return row


def deactivate_other_settings(db: Session, *, keep_id: UUID) -> None:
    db.execute(
        update(EmailProviderSettings)
        .where(
            EmailProviderSettings.id != keep_id,
            EmailProviderSettings.is_active.is_(True),
        )
        .values(is_active=False)
    )


def activate_provider_settings(
    db: Session,
    *,
    settings_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> EmailProviderSettings:
    if settings_id is None:
        row = get_or_create_active_settings(db, actor_user_id=actor_user_id)
    else:
        row = db.get(EmailProviderSettings, settings_id)
        if row is None:
            raise LookupError("Email settings not found")
    deactivate_other_settings(db, keep_id=row.id)
    row.is_active = True
    row.updated_by_user_id = actor_user_id
    db.flush()
    write_audit_log(
        db,
        action="emails.provider_settings_activate",
        actor_user_id=actor_user_id,
        resource_type="email_provider_settings",
        resource_id=str(row.id),
        details={"provider": row.provider},
    )
    db.commit()
    db.refresh(row)
    return row


def disable_email_sending(
    db: Session,
    *,
    actor_user_id: UUID | None = None,
) -> EmailProviderSettings:
    row = get_or_create_active_settings(db, actor_user_id=actor_user_id)
    row.email_enabled = False
    row.updated_by_user_id = actor_user_id
    db.flush()
    write_audit_log(
        db,
        action="emails.provider_settings_disable",
        actor_user_id=actor_user_id,
        resource_type="email_provider_settings",
        resource_id=str(row.id),
        details={"email_enabled": False},
    )
    db.commit()
    db.refresh(row)
    return row


def _safe_smtp_error(
    exc: BaseException,
    *,
    username: str,
    password: str,
    from_email: str | None = None,
) -> str:
    text = redact_smtp_error_text(exc, username=username, password=password)
    return humanize_smtp_error_for_admin(
        text, from_email=from_email, smtp_username=username or None
    )


def _open_smtp(cfg: EmailRuntimeConfig):
    host = cfg.smtp_host
    port = int(cfg.smtp_port or (465 if cfg.smtp_use_ssl else 587))
    if cfg.smtp_use_ssl:
        context = ssl.create_default_context()
        return smtplib.SMTP_SSL(host, port, timeout=20, context=context)
    smtp = smtplib.SMTP(host, port, timeout=20)
    smtp.ehlo()
    if cfg.smtp_use_tls:
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
    return smtp


def test_smtp_connection(
    db: Session,
    *,
    actor_user_id: UUID | None = None,
) -> dict[str, Any]:
    row = get_or_create_active_settings(db, actor_user_id=actor_user_id)
    from app.email.config import email_runtime

    cfg = email_runtime(db=db)
    username = cfg.smtp_username
    password = cfg.smtp_password

    if not cfg.smtp_host:
        row.last_test_at = datetime.now(UTC)
        row.last_test_status = "failed"
        row.last_test_error = "SMTP host is not configured"
        db.flush()
        write_audit_log(
            db,
            action="emails.provider_settings_test",
            actor_user_id=actor_user_id,
            resource_type="email_provider_settings",
            resource_id=str(row.id),
            details={"ok": False, "mode": "connection", "error": "smtp_host_missing"},
        )
        db.commit()
        return {"ok": False, "error": "SMTP host is not configured", "status": "failed"}

    try:
        with _open_smtp(cfg) as smtp:
            if username:
                smtp.login(username, password)
        row.last_test_at = datetime.now(UTC)
        row.last_test_status = "success"
        row.last_test_error = None
        db.flush()
        write_audit_log(
            db,
            action="emails.provider_settings_test",
            actor_user_id=actor_user_id,
            resource_type="email_provider_settings",
            resource_id=str(row.id),
            details={
                "ok": True,
                "mode": "connection",
                "smtp_host": cfg.smtp_host,
                "smtp_port": cfg.smtp_port,
            },
        )
        db.commit()
        return {
            "ok": True,
            "error": None,
            "status": "success",
            "smtp_host": cfg.smtp_host,
            "smtp_port": cfg.smtp_port,
        }
    except Exception as exc:  # noqa: BLE001
        safe = _safe_smtp_error(
            exc,
            username=username,
            password=password,
            from_email=cfg.from_email,
        )
        row.last_test_at = datetime.now(UTC)
        row.last_test_status = "failed"
        row.last_test_error = safe
        db.flush()
        write_audit_log(
            db,
            action="emails.provider_settings_test",
            actor_user_id=actor_user_id,
            resource_type="email_provider_settings",
            resource_id=str(row.id),
            details={"ok": False, "mode": "connection", "error": safe[:200]},
        )
        db.commit()
        return {"ok": False, "error": safe, "status": "failed"}


def send_test_email(
    db: Session,
    *,
    to: str,
    actor_user_id: UUID | None = None,
) -> dict[str, Any]:
    to_norm = (to or "").strip().lower()
    if not to_norm or not EMAIL_RE.match(to_norm):
        raise ValueError("Valid test_recipient_email is required")

    row = get_or_create_active_settings(db, actor_user_id=actor_user_id)
    from app.email.config import email_runtime

    cfg = email_runtime(db=db)
    provider = get_email_provider(db=db)
    subject = "Pàdéyá SMTP test"
    text = (
        "This is a test email from the Pàdéyá admin dashboard.\n\n"
        f"Provider: {cfg.provider}\n"
        f"From: {cfg.from_name} <{cfg.from_email}>\n"
    )
    html = (
        "<html><body>"
        "<p>This is a test email from the <strong>Pàdéyá</strong> admin dashboard.</p>"
        f"<p>Provider: {cfg.provider}<br/>"
        f"From: {cfg.from_name} &lt;{cfg.from_email}&gt;</p>"
        "</body></html>"
    )
    result = provider.send(
        OutboundEmail(
            to=to_norm,
            subject=subject,
            text=text,
            html=html,
            from_email=cfg.from_email,
            from_name=cfg.from_name,
            reply_to=cfg.reply_to,
            metadata={"purpose": "admin_smtp_test"},
        )
    )
    error_display = result.error
    if not result.ok and error_display:
        error_display = humanize_smtp_error_for_admin(
            error_display,
            from_email=cfg.from_email,
            smtp_username=cfg.smtp_username or None,
        )
    # Also record in outbox for audit visibility
    event = EmailEvent(
        template="admin_test",
        recipient_email=to_norm,
        recipient_user_id=actor_user_id,
        subject=subject,
        status="sent" if result.ok and not result.skipped else ("skipped" if result.skipped else "failed"),
        provider=result.provider,
        context_json={"purpose": "admin_smtp_test"},
        error_message=None if result.ok else (error_display or "send_failed")[:500],
        attempts=1,
        last_attempt_at=datetime.now(UTC),
        sent_at=datetime.now(UTC) if result.ok and not result.skipped else None,
        body_text=None,
        body_html=None,
    )
    db.add(event)

    row.last_test_at = datetime.now(UTC)
    row.last_test_status = "success" if result.ok else "failed"
    row.last_test_error = None if result.ok else (error_display or "send_failed")[:500]
    if result.ok and not result.skipped:
        row.last_successful_send_at = datetime.now(UTC)
    db.flush()
    write_audit_log(
        db,
        action="emails.provider_settings_test",
        actor_user_id=actor_user_id,
        resource_type="email_provider_settings",
        resource_id=str(row.id),
        details={
            "ok": result.ok,
            "mode": "send",
            "provider": result.provider,
            "skipped": result.skipped,
            "to_domain": to_norm.split("@")[-1],
            "error": (result.error or "")[:200] or None,
        },
    )
    db.commit()
    delivered_to_inbox = (
        bool(result.ok)
        and not result.skipped
        and result.provider == "smtp"
    )
    return {
        "ok": bool(result.ok),
        "provider": result.provider,
        "skipped": bool(result.skipped),
        "delivered_to_inbox": delivered_to_inbox,
        "error": error_display,
        "to": to_norm,
        "status": row.last_test_status,
        "email_event_id": event.id,
    }


def mark_successful_send(db: Session) -> None:
    row = get_active_provider_settings(db)
    if row is None:
        return
    row.last_successful_send_at = datetime.now(UTC)
    db.flush()


def outbox_counts(db: Session) -> tuple[int, int]:
    pending = int(
        db.scalar(
            select(func.count()).select_from(EmailEvent).where(EmailEvent.status == "pending")
        )
        or 0
    )
    failed = int(
        db.scalar(
            select(func.count()).select_from(EmailEvent).where(EmailEvent.status == "failed")
        )
        or 0
    )
    return pending, failed
