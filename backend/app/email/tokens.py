"""Signed tokens for unsubscribe / email preferences links (stdlib HMAC)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from uuid import UUID

from app.core.config import get_settings

_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def _sign(payload: bytes) -> str:
    key = get_settings().secret_key.encode("utf-8")
    sig = hmac.new(key, payload, hashlib.sha256).digest()
    return _b64encode(sig)


def make_prefs_token(user_id: UUID, *, purpose: str = "preferences") -> str:
    body = {
        "uid": str(user_id),
        "purpose": purpose,
        "exp": int(time.time()) + _MAX_AGE_SECONDS,
    }
    payload = _b64encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    return f"{payload}.{_sign(payload.encode('ascii'))}"


def parse_prefs_token(token: str, *, purpose: str | None = None) -> UUID:
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid token") from exc
    expected = _sign(payload_b64.encode("ascii"))
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Invalid token")
    try:
        data = json.loads(_b64decode(payload_b64).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid token") from exc
    if int(data.get("exp", 0)) < int(time.time()):
        raise ValueError("Token expired")
    if purpose and data.get("purpose") != purpose:
        raise ValueError("Invalid token purpose")
    return UUID(str(data["uid"]))
