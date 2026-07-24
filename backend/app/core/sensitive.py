"""Lightweight reversible obfuscation for sensitive host bank details.

Not a substitute for a KMS/HSM in production — keeps full account numbers
out of API responses while allowing payout tooling to recover them.
"""

from __future__ import annotations

import base64
import hashlib

from app.core.config import get_settings


def _key_bytes() -> bytes:
    return hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()


def encrypt_sensitive(value: str) -> str:
    key = _key_bytes()
    data = value.encode("utf-8")
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(xored).decode("ascii")


def decrypt_sensitive(token: str) -> str:
    key = _key_bytes()
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return plain.decode("utf-8")


def account_last4(account_number: str) -> str:
    digits = "".join(ch for ch in account_number if ch.isdigit())
    if len(digits) < 4:
        raise ValueError("account number must have at least 4 digits")
    return digits[-4:]
