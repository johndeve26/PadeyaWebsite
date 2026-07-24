"""Paystack customer email rules (stricter than local/demo registration)."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.payments.attendees import normalize_email, validate_email

# Paystack rejects many reserved / demo TLDs even in test mode.
_PAYSTACK_BLOCKED_DOMAIN_SUFFIXES: tuple[str, ...] = (
    ".test",
    ".invalid",
    ".localhost",
    ".local",
    ".example",
    ".internal",
)

PAYSTACK_INCOMPATIBLE_CHECKOUT_DETAIL = (
    "Paystack requires a standard email address (for example Gmail or work email). "
    "Demo addresses like @demo.padeye.test are not accepted — enter a payment email "
    "below or continue as guest with a real address."
)


def is_paystack_compatible_email(value: str | None) -> bool:
    email = normalize_email(value or "")
    if not email:
        return False
    try:
        validate_email(email, field="email")
    except HTTPException:
        return False
    domain = email.rsplit("@", 1)[-1]
    return not any(domain.endswith(suffix) for suffix in _PAYSTACK_BLOCKED_DOMAIN_SUFFIXES)


def resolve_paystack_customer_email(
    order_email: str,
    *,
    payment_email_override: str | None = None,
) -> str:
    """Email sent to Paystack initialize — override for demo/logins with .test addresses."""
    if payment_email_override and str(payment_email_override).strip():
        resolved = validate_email(payment_email_override, field="payment email")
        if not is_paystack_compatible_email(resolved):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=PAYSTACK_INCOMPATIBLE_CHECKOUT_DETAIL,
            )
        return resolved

    base = validate_email(order_email, field="buyer email")
    if is_paystack_compatible_email(base):
        return base

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=PAYSTACK_INCOMPATIBLE_CHECKOUT_DETAIL,
    )


def friendly_paystack_email_error(message: str | None) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    lower = text.lower()
    if "invalid email" in lower:
        return PAYSTACK_INCOMPATIBLE_CHECKOUT_DETAIL
    return None
