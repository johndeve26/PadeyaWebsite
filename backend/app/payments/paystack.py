"""Paystack HTTP client and webhook signature verification."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.payments.config import paystack_runtime, paystack_secret_not_configured_message


class PaystackError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def verify_webhook_signature(
    *,
    body: bytes,
    signature: str | None,
    db: Session | None = None,
) -> bool:
    cfg = paystack_runtime(db)
    secret = cfg.effective_webhook_secret
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


def initialize_transaction(
    *,
    email: str,
    amount_kobo: int,
    reference: str,
    callback_url: str,
    metadata: dict[str, Any] | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    cfg = paystack_runtime(db)
    if not cfg.secret_key:
        raise PaystackError(paystack_secret_not_configured_message(db))

    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": callback_url,
        "currency": "NGN",
        "metadata": metadata or {},
    }
    headers = {
        "Authorization": f"Bearer {cfg.secret_key}",
        "Content-Type": "application/json",
    }
    url = f"{cfg.base_url.rstrip('/')}/transaction/initialize"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, content=json.dumps(payload))
    data = response.json()
    if response.status_code >= 400 or not data.get("status"):
        raw_msg = data.get("message") or "Paystack initialize failed"
        from app.payments.paystack_email import friendly_paystack_email_error

        friendly = friendly_paystack_email_error(str(raw_msg))
        raise PaystackError(
            friendly or raw_msg,
            status_code=response.status_code,
        )
    return data["data"]


def verify_transaction(
    *,
    reference: str,
    db: Session | None = None,
) -> dict[str, Any]:
    """Fetch Paystack transaction status by reference (server-side verify)."""
    cfg = paystack_runtime(db)
    if not cfg.secret_key:
        raise PaystackError(paystack_secret_not_configured_message(db))

    ref = reference.strip()
    if not ref:
        raise PaystackError("Payment reference is required")

    headers = {
        "Authorization": f"Bearer {cfg.secret_key}",
        "Content-Type": "application/json",
    }
    url = f"{cfg.base_url.rstrip('/')}/transaction/verify/{quote(ref, safe='')}"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
    data = response.json()
    if response.status_code >= 400 or not data.get("status"):
        raw_msg = data.get("message") or "Paystack verify failed"
        raise PaystackError(raw_msg, status_code=response.status_code)
    return data["data"]


def sign_body_for_tests(body: bytes, secret: str | None = None, db: Session | None = None) -> str:
    key = (secret or paystack_runtime(db).effective_webhook_secret).encode("utf-8")
    return hmac.new(key, body, hashlib.sha512).hexdigest()
