"""Password hashing and JWT helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *,
    subject: UUID | str,
    roles: list[str],
    permissions: list[str],
    expires_minutes: int | None = None,
) -> str:
    """Normal (non-impersonation) access token for the authenticated user."""
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "roles": roles,
        "permissions": permissions,
        "type": "access",
        "is_impersonating": False,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_impersonation_access_token(
    *,
    actual_user_id: UUID | str,
    actor_admin_id: UUID | str,
    impersonation_id: UUID | str,
    roles: list[str],
    permissions: list[str],
    started_at: datetime,
    expires_at: datetime,
    reason: str,
    support_ticket_id: str | None = None,
) -> str:
    """Short-lived impersonation session token (10D).

    Required claims: ``actual_user_id``, ``actor_admin_id``, ``impersonation_id``,
    ``is_impersonating``, ``started_at``, ``expires_at``, ``reason``.

    Carries the *target* user's roles/permissions only — admin privileges must
    never appear in this token. The admin's real session is preserved separately
    client-side and is not replaced permanently.
    """
    payload: dict[str, Any] = {
        # Standard subject = effective (impersonated) user for auth resolution.
        "sub": str(actual_user_id),
        "actual_user_id": str(actual_user_id),
        "actor_admin_id": str(actor_admin_id),
        "impersonation_id": str(impersonation_id),
        "is_impersonating": True,
        "started_at": started_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "reason": reason[:500],
        "support_ticket_id": support_ticket_id,
        # Target-only RBAC — never include the admin's permissions here.
        "roles": roles,
        "permissions": permissions,
        "type": "access",
        "exp": expires_at,
        "iat": started_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


_RESET_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_password_reset_code() -> str:
    """Six-character code for email-based password reset (no ambiguous chars)."""
    return "".join(secrets.choice(_RESET_CODE_ALPHABET) for _ in range(6))


def normalize_password_reset_code(raw: str) -> str:
    return (raw or "").strip().upper().replace(" ", "").replace("-", "")
