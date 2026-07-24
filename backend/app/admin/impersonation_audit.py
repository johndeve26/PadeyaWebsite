"""Canonical impersonation audit events + safe metadata scrubbing (phase 11B).

Domain table ``admin_impersonation_audit_logs`` + dual-write to platform
``audit_logs``. Never stores request bodies, passwords, tokens, payment/QR
payloads, or private message content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.admin.impersonation_store import write_impersonation_audit_log
from app.core.audit import write_audit_log

# Canonical action names (domain + global audit_logs).
ADMIN_IMPERSONATION_STARTED = "admin_impersonation_started"
ADMIN_IMPERSONATION_ENDED = "admin_impersonation_ended"
ADMIN_IMPERSONATION_EXPIRED = "admin_impersonation_expired"
ADMIN_IMPERSONATION_SENSITIVE_ACTION_BLOCKED = (
    "admin_impersonation_sensitive_action_blocked"
)
ADMIN_IMPERSONATION_REQUEST_MADE = "admin_impersonation_request_made"

ADMIN_IMPERSONATION_AUDIT_ACTIONS: frozenset[str] = frozenset(
    {
        ADMIN_IMPERSONATION_STARTED,
        ADMIN_IMPERSONATION_ENDED,
        ADMIN_IMPERSONATION_EXPIRED,
        ADMIN_IMPERSONATION_SENSITIVE_ACTION_BLOCKED,
        ADMIN_IMPERSONATION_REQUEST_MADE,
    }
)

# Key fragments that must never appear in metadata (case-insensitive).
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "refresh",
    "access_token",
    "api_key",
    "apikey",
    "paystack",
    "card",
    "cvv",
    "cvc",
    "pan",
    "iban",
    "account_number",
    "routing",
    "otp",
    "pin",
    "ssn",
    "qr",
    "jti",
    "private_key",
    "vapid",
    "message_body",
    "ciphertext",
    "request_body",
    "raw_body",
    "raw_payload",
    "payment_payload",
    "qr_payload",
)


def _is_sensitive_key(key: str) -> bool:
    lowered = (key or "").strip().lower()
    if not lowered:
        return True
    # Exact / alias ban for free-text bodies (do not store request content).
    if lowered in {
        "body",
        "text",
        "content",
        "payload",
        "message",
        "request_body",
        "raw",
    }:
        return True
    return any(frag in lowered for frag in _SENSITIVE_KEY_FRAGMENTS)


def scrub_impersonation_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Drop sensitive keys/values. Never stores request bodies or secrets."""
    if not metadata:
        return None

    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if _is_sensitive_key(str(key)):
            continue
        if isinstance(value, dict):
            nested = scrub_impersonation_metadata(value)
            if nested:
                cleaned[str(key)] = nested
            continue
        if isinstance(value, (list, tuple)):
            # Only keep simple scalar lists; drop nested objects that may hold secrets.
            scalars = [
                item
                for item in value
                if isinstance(item, (str, int, float, bool, type(None)))
            ]
            if scalars:
                cleaned[str(key)] = scalars[:20]
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > 500:
                cleaned[str(key)] = value[:500]
            else:
                cleaned[str(key)] = value
    return cleaned or None


def record_impersonation_audit(
    db: Session,
    *,
    action: str,
    impersonation_id: UUID,
    actor_admin_id: UUID,
    target_user_id: UUID,
    reason: str | None = None,
    support_ticket_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    action_attempted: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    dual_write_global: bool = True,
) -> None:
    """Write domain impersonation audit (+ optional global audit_logs row).

    Required field matrix (11B): impersonation_id, actor_admin_id, target_user_id,
    action, route/path, method, reason, support_ticket_id?, ip_address?,
    user_agent?, created_at.

    Internal-only: target users are never notified. Never skipped for
    demo/local/DEMO_MODE. Never persists request bodies or secrets.
    """
    if action not in ADMIN_IMPERSONATION_AUDIT_ACTIONS:
        raise ValueError(f"Unknown impersonation audit action: {action}")

    reason_clean = (reason or "").strip() or None
    if reason_clean and len(reason_clean) > 500:
        reason_clean = reason_clean[:500]

    ticket_clean = (support_ticket_id or "").strip() or None
    if ticket_clean and len(ticket_clean) > 128:
        ticket_clean = ticket_clean[:128]

    path_clean = (path or "").strip() or None
    if path_clean and len(path_clean) > 512:
        path_clean = path_clean[:512]

    method_clean = (method or "").strip().upper() or None
    if method_clean and len(method_clean) > 16:
        method_clean = method_clean[:16]

    # Strip any accidental body / secret keys from caller metadata first.
    safe_meta = scrub_impersonation_metadata(metadata) or {}
    # Prefer explicit args over metadata duplicates.
    safe_meta.pop("support_ticket_id", None)
    safe_meta.pop("reason", None)
    safe_meta.pop("route", None)
    safe_meta.pop("path", None)
    safe_meta.pop("method", None)
    safe_meta.pop("impersonation_id", None)
    safe_meta.pop("actor_admin_id", None)
    safe_meta.pop("target_user_id", None)

    if reason_clean is not None:
        safe_meta["reason"] = reason_clean
    if ticket_clean is not None:
        safe_meta["support_ticket_id"] = ticket_clean
    if action_attempted:
        safe_meta["action_attempted"] = str(action_attempted)[:200]
    if path_clean:
        safe_meta["route"] = path_clean
    safe_meta["recorded_at"] = datetime.now(UTC).isoformat()

    write_impersonation_audit_log(
        db,
        impersonation_id=impersonation_id,
        actor_admin_id=actor_admin_id,
        target_user_id=target_user_id,
        action=action,
        method=method_clean,
        path=path_clean,
        status_code=status_code,
        metadata_json=safe_meta or None,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if dual_write_global:
        details = scrub_impersonation_metadata(
            {
                "impersonation_id": str(impersonation_id),
                "actor_admin_id": str(actor_admin_id),
                "target_user_id": str(target_user_id),
                "reason": reason_clean,
                "support_ticket_id": ticket_clean,
                "method": method_clean,
                "path": path_clean,
                "route": path_clean,
                "action_attempted": (str(action_attempted)[:200] if action_attempted else None),
                "status_code": status_code,
                **safe_meta,
            }
        )
        write_audit_log(
            db,
            action=action,
            actor_user_id=actor_admin_id,
            resource_type="impersonation_session",
            resource_id=str(impersonation_id),
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
