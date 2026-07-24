"""Resolved Paystack credentials from Admin runtime settings (DB) only.

Secrets are never logged. Always pass a DB session so admin overrides apply.

Paystack test vs live (https://paystack.com/docs/api/authentication/):
- Same API base URL (https://api.paystack.co).
- Active mode picks sk_test_/pk_test_ or sk_live_/pk_live_ keys.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.runtime_settings.service import runtime_settings_service


@dataclass(frozen=True)
class PaystackRuntimeConfig:
    mode: str
    secret_key: str
    public_key: str
    webhook_secret: str
    base_url: str

    @property
    def effective_webhook_secret(self) -> str:
        return self.webhook_secret or self.secret_key

    @property
    def secret_configured(self) -> bool:
        return bool(self.secret_key.strip())

    @property
    def public_configured(self) -> bool:
        return bool(self.public_key.strip())

    @property
    def is_test_mode(self) -> bool:
        return self.mode != "live"

    @property
    def is_live_mode(self) -> bool:
        return self.mode == "live"


def paystack_runtime(db: Session | None = None) -> PaystackRuntimeConfig:
    """Resolve Paystack keys for payment/webhook flows."""
    svc = runtime_settings_service
    mode = _normalize_mode(str(svc.get_runtime_setting("paystack_mode", db=db) or "test"))

    if mode == "live":
        secret = (svc.get_runtime_secret("paystack_live_secret_key", db=db) or "").strip()
        webhook = (svc.get_runtime_secret("paystack_live_webhook_secret", db=db) or "").strip()
        public = str(svc.get_runtime_setting("paystack_live_public_key", db=db) or "").strip()
    else:
        secret = (svc.get_runtime_secret("paystack_secret_key", db=db) or "").strip()
        webhook = (svc.get_runtime_secret("paystack_webhook_secret", db=db) or "").strip()
        public = str(svc.get_runtime_setting("paystack_public_key", db=db) or "").strip()

    base = (
        str(svc.get_runtime_setting("paystack_base_url", db=db) or "https://api.paystack.co").strip()
        or "https://api.paystack.co"
    )
    return PaystackRuntimeConfig(
        mode=mode,
        secret_key=secret,
        public_key=public,
        webhook_secret=webhook,
        base_url=base,
    )


def _normalize_mode(raw: str | None) -> str:
    text = (raw or "test").strip().lower()
    return "live" if text == "live" else "test"


def paystack_secret_not_configured_message(db: Session | None) -> str:
    """Actionable copy when initialize/checkout cannot resolve a secret key."""
    svc = runtime_settings_service
    mode = _normalize_mode(str(svc.get_runtime_setting("paystack_mode", db=db) or "test"))
    admin = "Admin → Payment integration"
    if mode == "live":
        has_test = bool((svc.get_runtime_secret("paystack_secret_key", db=db) or "").strip())
        if has_test:
            return (
                f"Paystack mode is Live but only test keys are configured. "
                f"Add sk_live_… keys in {admin}, or set Paystack mode to Test."
            )
        return f"Paystack live secret key is not configured ({admin})."
    has_live = bool(
        (svc.get_runtime_secret("paystack_live_secret_key", db=db) or "").strip()
    )
    if has_live:
        return (
            f"Paystack mode is Test but only live keys are configured. "
            f"Add sk_test_… keys in {admin}, or set Paystack mode to Live."
        )
    return f"Paystack test secret key is not configured ({admin})."
