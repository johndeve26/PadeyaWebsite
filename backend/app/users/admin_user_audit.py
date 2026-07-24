"""Canonical admin-user management audit events (platform ``audit_logs``).

Action names and detail fields follow the product audit matrix (phase 11).
Sensitive metadata is scrubbed before persistence — never store passwords,
tokens, raw note/flag bodies, or payment/QR secrets.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.audit import AuditLog, write_audit_log
from app.users.admin_response_safety import scrub_admin_user_payload

# Canonical action names.
ADMIN_USER_VIEWED = "admin_user_viewed"
ADMIN_USER_PRIVATE_CONTACT_VIEWED = "admin_user_private_contact_viewed"
ADMIN_USER_ACTIVITY_DETAIL_VIEWED = "admin_user_activity_detail_viewed"
ADMIN_USER_FLAG_CREATED = "admin_user_flag_created"
ADMIN_USER_FLAG_UPDATED = "admin_user_flag_updated"
ADMIN_USER_NOTE_CREATED = "admin_user_note_created"
ADMIN_USER_STATUS_CHANGED = "admin_user_status_changed"
ADMIN_USER_RESTRICTION_ADDED = "admin_user_restriction_added"
ADMIN_USER_RESTRICTION_REVOKED = "admin_user_restriction_revoked"
ADMIN_USER_RESTRICTION_EXTENDED = "admin_user_restriction_extended"
ADMIN_USER_RESTRICTION_PRESET_APPLIED = "admin_user_restriction_preset_applied"
RESTRICTED_USER_BLOCKED_FROM_ACTION = "restricted_user_blocked_from_action"
# Legacy alias kept for older audits / transitions.
ADMIN_USER_RESTRICTIONS_CHANGED = "admin_user_restrictions_changed"
ADMIN_USER_FORCE_LOGOUT = "admin_user_force_logout"
ADMIN_USER_FORCE_PASSWORD_RESET = "admin_user_force_password_reset"
ADMIN_USER_SUSPENSION_NOTIFIED = "admin_user_suspension_notified"
ACCOUNT_APPEAL_SUBMITTED = "account_appeal_submitted"
ACCOUNT_APPEAL_APPROVED = "account_appeal_approved"
ACCOUNT_APPEAL_REJECTED = "account_appeal_rejected"
ADMIN_USER_UNSUSPENDED = "admin_user_unsuspended"

ADMIN_USER_AUDIT_ACTIONS: frozenset[str] = frozenset(
    {
        ADMIN_USER_VIEWED,
        ADMIN_USER_PRIVATE_CONTACT_VIEWED,
        ADMIN_USER_ACTIVITY_DETAIL_VIEWED,
        ADMIN_USER_FLAG_CREATED,
        ADMIN_USER_FLAG_UPDATED,
        ADMIN_USER_NOTE_CREATED,
        ADMIN_USER_STATUS_CHANGED,
        ADMIN_USER_RESTRICTION_ADDED,
        ADMIN_USER_RESTRICTION_REVOKED,
        ADMIN_USER_RESTRICTION_EXTENDED,
        ADMIN_USER_RESTRICTION_PRESET_APPLIED,
        RESTRICTED_USER_BLOCKED_FROM_ACTION,
        ADMIN_USER_RESTRICTIONS_CHANGED,
        ADMIN_USER_FORCE_LOGOUT,
        ADMIN_USER_FORCE_PASSWORD_RESET,
        ADMIN_USER_SUSPENSION_NOTIFIED,
        ACCOUNT_APPEAL_SUBMITTED,
        ACCOUNT_APPEAL_APPROVED,
        ACCOUNT_APPEAL_REJECTED,
        ADMIN_USER_UNSUSPENDED,
    }
)

# Extra fragments beyond response-safety (audit metadata is stricter).
_AUDIT_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "session",
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
    "internal_note",
    "note_body",
    "ciphertext",
    "raw_",
    "payload",
)


def _is_audit_sensitive_key(key: str) -> bool:
    lowered = (key or "").strip().lower()
    if not lowered:
        return True
    # Boolean flag only — must not match the ``internal_note`` fragment scrub.
    if lowered == "internal_note_present":
        return False
    return any(frag in lowered for frag in _AUDIT_SENSITIVE_KEY_FRAGMENTS)


def scrub_admin_user_audit_value(value: Any) -> Any:
    """Recursively scrub nested audit metadata."""
    value = scrub_admin_user_payload(value)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _is_audit_sensitive_key(str(key)):
                continue
            # Never persist free-text note/flag bodies under any alias.
            if str(key).lower() in {"body", "text", "content", "note"}:
                continue
            cleaned = scrub_admin_user_audit_value(item)
            if cleaned is not None and cleaned != {} and cleaned != []:
                out[str(key)] = cleaned
        return out
    if isinstance(value, (list, tuple)):
        scalars = [
            item
            for item in value
            if isinstance(item, (str, int, float, bool, type(None)))
        ]
        return scalars[:40]
    if isinstance(value, str) and len(value) > 500:
        return value[:500]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def scrub_admin_user_audit_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not metadata:
        return None
    cleaned = scrub_admin_user_audit_value(metadata)
    return cleaned if isinstance(cleaned, dict) and cleaned else None


def client_request_meta(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    if ua and len(ua) > 512:
        ua = ua[:512]
    return ip, ua


def write_admin_user_audit(
    db: Session,
    *,
    action: str,
    admin_user_id: UUID,
    target_user_id: UUID,
    reason: str | None = None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Append a scrubbed admin-user audit row to platform ``audit_logs``."""
    if action not in ADMIN_USER_AUDIT_ACTIONS:
        raise ValueError(f"Unknown admin user audit action: {action}")

    reason_clean = (reason or "").strip() or None
    if reason_clean and len(reason_clean) > 500:
        reason_clean = reason_clean[:500]

    payload: dict[str, Any] = {
        "admin_user_id": str(admin_user_id),
        "target_user_id": str(target_user_id),
        "reason": reason_clean,
        "before_json": scrub_admin_user_audit_metadata(before_json),
        "after_json": scrub_admin_user_audit_metadata(after_json),
    }
    if extra:
        payload.update(extra)

    details = scrub_admin_user_audit_metadata(payload)

    return write_audit_log(
        db,
        action=action,
        actor_user_id=admin_user_id,
        resource_type="user",
        resource_id=str(target_user_id),
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def record_admin_user_view(
    db: Session,
    *,
    admin_user_id: UUID,
    target_user_id: UUID,
    showed_private_contact: bool,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = True,
) -> None:
    """Record detail view (+ private-contact view when unmasked contact is shown)."""
    write_admin_user_audit(
        db,
        action=ADMIN_USER_VIEWED,
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if showed_private_contact:
        write_admin_user_audit(
            db,
            action=ADMIN_USER_PRIVATE_CONTACT_VIEWED,
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    if commit:
        db.commit()


def record_admin_user_activity_detail_view(
    db: Session,
    *,
    admin_user_id: UUID,
    target_user_id: UUID,
    activity_kind: str,
    page: int,
    finance_fields_included: bool,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = True,
) -> None:
    """Audit Activity tab drill-down (orders/refunds/hosts finance slices, etc.)."""
    write_admin_user_audit(
        db,
        action=ADMIN_USER_ACTIVITY_DETAIL_VIEWED,
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        extra={
            "activity_kind": activity_kind,
            "page": page,
            "finance_fields_included": finance_fields_included,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if commit:
        db.commit()
