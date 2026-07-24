"""Signed QR payload helpers — never embed plain ticket UUIDs."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from app.core.config import get_settings

settings = get_settings()

# Short-lived rotating QR TTL (seconds). Static tickets keep multi-day expiry.
ROTATING_QR_TTL_SECONDS = 90


def new_public_ticket_code() -> str:
    return f"PDY-{secrets.token_hex(4).upper()}-{secrets.token_hex(2).upper()}"


def new_qr_jti() -> str:
    return secrets.token_urlsafe(24)


def hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def hash_device_fingerprint(fingerprint: str) -> str:
    return hashlib.sha256(fingerprint.strip().encode("utf-8")).hexdigest()


def create_signed_qr_payload(
    *,
    public_code: str,
    event_id: UUID | str,
    jti: str,
    expires_days: int = 365,
    expires_seconds: int | None = None,
    rotation_version: int = 1,
) -> str:
    """Compact signed token for QR encoding (no plain ticket UUID)."""
    now = datetime.now(UTC)
    if expires_seconds is not None:
        exp = now + timedelta(seconds=expires_seconds)
    else:
        exp = now + timedelta(days=expires_days)
    payload: dict[str, Any] = {
        "typ": "padeya.ticket.qr",
        "code": public_code,
        "eid": str(event_id),
        "jti": jti,
        "rv": rotation_version,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, settings.effective_qr_secret, algorithm="HS256")


def decode_signed_qr_payload(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.effective_qr_secret,
        algorithms=["HS256"],
    )
    if payload.get("typ") != "padeya.ticket.qr":
        raise jwt.InvalidTokenError("Invalid QR token type")
    return payload
