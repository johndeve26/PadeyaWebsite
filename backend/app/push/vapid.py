"""VAPID key helpers for Web Push.

pywebpush passes string keys to ``Vapid.from_string()``, which accepts only
URL-safe base64 RAW (32-byte) or DER — not PEM. Admin-generated keys historically
used PEM via ``private_pem()``, which produces:

  Could not deserialize key data...

Load PEM explicitly (and accept raw/DER) so existing production keys keep working
without regenerating (subscriptions stay valid).
"""

from __future__ import annotations

import base64
import logging
from typing import Any

logger = logging.getLogger("padeya.push.vapid")


def generate_vapid_keypair() -> tuple[str, str]:
    """Return ``(public_urlsafe_b64, private_urlsafe_raw_b64)``.

    Private key is the 32-byte EC scalar as URL-safe base64 (no padding), which
    ``Vapid.from_string`` / pywebpush accept directly.
    """
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid

    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public).decode("ascii").rstrip("=")
    raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    private_b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return public_b64, private_b64


def is_pem_private_key(value: str) -> bool:
    text = (value or "").strip()
    return "BEGIN" in text and "PRIVATE" in text.upper()


def load_vapid_private(private_key: str) -> Any:
    """Return a ``py_vapid.Vapid`` instance from PEM or URL-safe raw/DER string."""
    from py_vapid import Vapid

    text = (private_key or "").strip()
    if not text:
        raise ValueError("vapid_private_missing")

    if is_pem_private_key(text):
        return Vapid.from_pem(text.encode("utf-8"))

    # Raw (32-byte) or DER URL-safe base64 — what from_string expects.
    return Vapid.from_string(private_key=text)


def fingerprint_vapid_private(private_key: str) -> tuple[str | None, str | None]:
    """Safe first4/last4 for admin hints (never PEM armor dashes)."""
    from app.core.encryption import secret_first4, secret_last4

    text = (private_key or "").strip()
    if not text:
        return None, None
    if is_pem_private_key(text):
        # Fingerprint the base64 body, not -----BEGIN...
        body = "".join(
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("-----")
        )
        if len(body) >= 8:
            return body[:4], body[-4:]
        return secret_first4(body), secret_last4(body)
    return secret_first4(text), secret_last4(text)
