"""Admin-managed Web Push / VAPID settings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.encryption import decrypt_secret, encrypt_secret, secret_last4, secret_first4, format_secret_fingerprint
from app.notifications.models import PushProviderSettings

logger = logging.getLogger("padeya.notifications.settings")

PROVIDER_WEB_PUSH = "web_push"
PROVIDER_LOG = "log"
VALID_PROVIDERS = frozenset({PROVIDER_WEB_PUSH, PROVIDER_LOG})


def get_active_push_settings(db: Session) -> PushProviderSettings | None:
    return db.scalar(
        select(PushProviderSettings)
        .where(PushProviderSettings.is_active.is_(True))
        .order_by(PushProviderSettings.updated_at.desc())
        .limit(1)
    )


def get_or_create_active_push_settings(
    db: Session,
    *,
    actor_user_id: UUID | None = None,
) -> PushProviderSettings:
    row = get_active_push_settings(db)
    if row is not None:
        return row
    row = PushProviderSettings(
        is_active=True,
        push_enabled=False,
        provider=PROVIDER_LOG,
        vapid_subject="mailto:support@padeya.com",
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    return row


def serialize_push_settings(row: PushProviderSettings) -> dict[str, Any]:
    """Public admin payload — never includes vapid_private_key plaintext."""
    return {
        "id": row.id,
        "is_active": bool(row.is_active),
        "push_enabled": bool(row.push_enabled),
        "provider": (row.provider or PROVIDER_LOG).strip().lower(),
        "vapid_public_key": row.vapid_public_key,
        "vapid_subject": row.vapid_subject,
        "vapid_private_configured": bool(row.vapid_private_key_encrypted),
        "vapid_private_hint": (
            format_secret_fingerprint(
                row.vapid_private_first4, row.vapid_private_last4, prefix=""
            )
            if row.vapid_private_key_encrypted
            and (row.vapid_private_first4 or row.vapid_private_last4)
            else ("••••••••" if row.vapid_private_key_encrypted else None)
        ),
        "vapid_private_first4": row.vapid_private_first4,
        "last_test_status": row.last_test_status,
        "last_test_error": row.last_test_error,
        "last_test_at": row.last_test_at,
        "created_by_user_id": row.created_by_user_id,
        "updated_by_user_id": row.updated_by_user_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def generate_vapid_keypair() -> tuple[str, str]:
    """Return (public_key_urlsafe, private_key_pem) for admin setup."""
    import base64

    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid

    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public).decode("ascii").rstrip("=")
    private_pem = vapid.private_pem()
    if isinstance(private_pem, bytes):
        private_pem = private_pem.decode("utf-8")
    return public_b64, private_pem


def update_push_settings(
    db: Session,
    *,
    updates: dict[str, Any],
    actor_user_id: UUID | None,
    commit: bool = True,
) -> PushProviderSettings:
    row = get_or_create_active_push_settings(db, actor_user_id=actor_user_id)
    private_in = updates.pop("vapid_private_key", None)
    generate = bool(updates.pop("generate_vapid_keys", False))
    private_rotated = False

    if generate:
        public, private = generate_vapid_keypair()
        row.vapid_public_key = public
        row.vapid_private_key_encrypted = encrypt_secret(private)
        row.vapid_private_first4 = secret_first4(private)
        row.vapid_private_last4 = secret_last4(private)
        private_rotated = True

    if "push_enabled" in updates and updates["push_enabled"] is not None:
        row.push_enabled = bool(updates["push_enabled"])
    if "provider" in updates and updates["provider"] is not None:
        provider = str(updates["provider"]).strip().lower()
        if provider not in VALID_PROVIDERS:
            raise ValueError("provider must be web_push or log")
        row.provider = provider
    if "vapid_public_key" in updates and updates["vapid_public_key"] is not None:
        row.vapid_public_key = str(updates["vapid_public_key"]).strip() or None
    if "vapid_subject" in updates and updates["vapid_subject"] is not None:
        subject = str(updates["vapid_subject"]).strip()
        if subject and not (
            subject.startswith("mailto:") or subject.startswith("https://")
        ):
            raise ValueError("vapid_subject must be mailto: or https: URL")
        row.vapid_subject = subject or None

    if private_in is not None and str(private_in).strip():
        plain = str(private_in).strip()
        row.vapid_private_key_encrypted = encrypt_secret(plain)
        row.vapid_private_first4 = secret_first4(plain)
        row.vapid_private_last4 = secret_last4(plain)
        private_rotated = True

    row.is_active = True
    row.updated_by_user_id = actor_user_id
    if row.created_by_user_id is None:
        row.created_by_user_id = actor_user_id
    db.flush()
    db.execute(
        update(PushProviderSettings)
        .where(
            PushProviderSettings.id != row.id,
            PushProviderSettings.is_active.is_(True),
        )
        .values(is_active=False)
    )
    write_audit_log(
        db,
        action="notifications.push_settings_update",
        actor_user_id=actor_user_id,
        resource_type="push_provider_settings",
        resource_id=str(row.id),
        details={
            "push_enabled": row.push_enabled,
            "provider": row.provider,
            "vapid_public_set": bool(row.vapid_public_key),
            "vapid_private_updated": private_rotated,
            "vapid_subject": row.vapid_subject,
        },
    )
    if commit:
        db.commit()
        db.refresh(row)
    return row


def disable_push(
    db: Session,
    *,
    actor_user_id: UUID | None,
) -> PushProviderSettings:
    row = get_or_create_active_push_settings(db, actor_user_id=actor_user_id)
    row.push_enabled = False
    row.updated_by_user_id = actor_user_id
    db.flush()
    write_audit_log(
        db,
        action="notifications.push_settings_disable",
        actor_user_id=actor_user_id,
        resource_type="push_provider_settings",
        resource_id=str(row.id),
        details={"push_enabled": False},
    )
    db.commit()
    db.refresh(row)
    return row


def record_push_test(
    db: Session,
    *,
    actor_user_id: UUID | None,
    ok: bool,
    error: str | None = None,
) -> PushProviderSettings:
    row = get_or_create_active_push_settings(db, actor_user_id=actor_user_id)
    row.last_test_at = datetime.now(UTC)
    row.last_test_status = "success" if ok else "failed"
    row.last_test_error = None if ok else (error or "test_failed")[:500]
    db.flush()
    write_audit_log(
        db,
        action="notifications.push_settings_test",
        actor_user_id=actor_user_id,
        resource_type="push_provider_settings",
        resource_id=str(row.id),
        details={"ok": ok, "error": (error or "")[:200] or None},
    )
    db.commit()
    db.refresh(row)
    return row


def decrypt_vapid_private(row: PushProviderSettings) -> str:
    if not row.vapid_private_key_encrypted:
        return ""
    try:
        return decrypt_secret(row.vapid_private_key_encrypted)
    except Exception:  # noqa: BLE001
        logger.error("Failed to decrypt VAPID private key")
        return ""
