"""Authenticated encryption for admin-managed secrets (SMTP, future API keys).

Uses Fernet (AES-128-CBC + HMAC). Key source:

1. ``EMAIL_SETTINGS_ENCRYPTION_KEY`` (preferred, stable infrastructure secret)
2. Derived from ``SECRET_KEY`` when the dedicated key is empty (local/test only)

Never log plaintext or decrypted values.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

logger = logging.getLogger("padeya.encryption")

_PREFIX = "fernet:v1:"


def _fernet_key_bytes() -> bytes:
    settings = get_settings()
    raw = (settings.email_settings_encryption_key or "").strip()
    if not raw:
        raw = (settings.secret_key or "").strip()
        if settings.is_production:
            logger.error(
                "EMAIL_SETTINGS_ENCRYPTION_KEY is empty in production — "
                "falling back to SECRET_KEY derivation (set a dedicated key)"
            )
    if not raw:
        raise RuntimeError(
            "EMAIL_SETTINGS_ENCRYPTION_KEY (or SECRET_KEY) is required to encrypt email settings"
        )
    # Accept a full Fernet key, or derive a stable 32-byte key from any passphrase.
    try:
        if len(raw) == 44:
            Fernet(raw.encode("ascii"))
            return raw.encode("ascii")
    except Exception:  # noqa: BLE001
        pass
    digest = hashlib.sha256(f"padeya-email-settings:{raw}".encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_fernet_key_bytes())


def encrypt_secret(value: str) -> str:
    """Encrypt a secret for DB storage. Empty input raises ValueError."""
    text = (value or "").strip()
    if not text:
        raise ValueError("Cannot encrypt empty secret")
    token = _fernet().encrypt(text.encode("utf-8")).decode("ascii")
    return f"{_PREFIX}{token}"


def decrypt_secret(token: str) -> str:
    """Decrypt a value produced by ``encrypt_secret``. Never log the result."""
    raw = (token or "").strip()
    if not raw:
        return ""
    if raw.startswith(_PREFIX):
        raw = raw[len(_PREFIX) :]
    try:
        return _fernet().decrypt(raw.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        logger.error("Failed to decrypt secret (invalid token / wrong key)")
        raise ValueError("Unable to decrypt secret with current encryption key") from exc


def secret_last4(value: str) -> str | None:
    """Return last 4 characters for masked display (never the full secret)."""
    text = (value or "").strip()
    if not text:
        return None
    return text[-4:] if len(text) >= 4 else text


def secret_first4(value: str) -> str | None:
    """Return first 4 characters for masked display (never the full secret)."""
    text = (value or "").strip()
    if not text:
        return None
    return text[:4] if len(text) >= 4 else text


def secret_fingerprint_parts(value: str) -> tuple[str | None, str | None]:
    """First and last four characters for admin key display."""
    text = (value or "").strip()
    if not text:
        return None, None
    return secret_first4(text), secret_last4(text)


def format_secret_fingerprint(
    first4: str | None,
    last4: str | None,
    *,
    prefix: str = "Configured · ",
) -> str | None:
    """Human-readable fingerprint e.g. ``Configured · AIza…jzyk``."""
    if not first4 and not last4:
        return None
    if first4 and last4:
        return f"{prefix}{first4}…{last4}"
    if last4:
        return f"{prefix}····{last4}"
    if first4:
        return f"{prefix}{first4}…"
    return prefix.rstrip(" ·") or "Configured"


def generate_email_settings_encryption_key() -> str:
    """Helper for operators: print a new Fernet key for .env."""
    return Fernet.generate_key().decode("ascii")
