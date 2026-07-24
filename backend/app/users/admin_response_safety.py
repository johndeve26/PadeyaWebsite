"""Safety rules for admin user API responses.

Admin user payloads must never expose credentials, tokens, QR/payment secrets,
or private message bodies. Prefer derived safe fields (masked, configured,
status, counts, timestamps).
"""

from __future__ import annotations

from typing import Any

# Exact key names (case-insensitive) that must never appear in admin user JSON.
FORBIDDEN_ADMIN_USER_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "hashed_password",
        "password_hash",
        "reset_token",
        "email_verification_token",
        "refresh_token",
        "access_token",
        "session_token",
        "oauth_token",
        "oauth_access_token",
        "oauth_refresh_token",
        "2fa_secret",
        "totp_secret",
        "mfa_secret",
        "qr_payload",
        "qr_secret",
        "ticket_qr_secret",
        "ticket_qr_payload",
        "merch_pickup_token",
        "pickup_token",
        "paystack_raw_payload",
        "provider_payload",
        "raw_payload",
        "payment_provider_secret",
        "paystack_secret",
        "stripe_secret",
        "private_message_body",
        "message_body",
        "message_bodies",
    }
)

# Substrings that indicate a secret-bearing key (case-insensitive).
# Keep narrow to avoid false positives on safe admin fields (e.g. note `body`).
FORBIDDEN_ADMIN_USER_KEY_SUBSTRINGS: tuple[str, ...] = (
    "password_hash",
    "hashed_password",
    "reset_token",
    "verification_token",
    "refresh_token",
    "access_token",
    "session_token",
    "oauth_token",
    "2fa_secret",
    "totp_secret",
    "mfa_secret",
    "qr_secret",
    "qr_payload",
    "pickup_token",
    "provider_secret",
    "paystack_raw",
    "raw_payment",
    "private_message",
)


def is_forbidden_admin_user_key(key: str) -> bool:
    kl = (key or "").strip().lower()
    if not kl:
        return False
    if kl in FORBIDDEN_ADMIN_USER_KEYS:
        return True
    return any(part in kl for part in FORBIDDEN_ADMIN_USER_KEY_SUBSTRINGS)


def mask_email(email: str | None) -> str:
    raw = (email or "").strip()
    if not raw or "@" not in raw:
        return "—"
    local, domain = raw.split("@", 1)
    if not local or not domain:
        return "—"
    keep = min(2, len(local))
    return f"{local[:keep]}•••@{domain}"


def mask_phone(phone: str | None) -> str | None:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) < 4:
        return None
    return f"•••{digits[-4:]}"


def last_four(value: str | None) -> str | None:
    raw = (value or "").strip()
    if len(raw) < 4:
        return None
    return raw[-4:]


def find_forbidden_admin_user_keys(
    payload: Any, *, path: str = "$"
) -> list[str]:
    """Return dotted paths of forbidden keys found in a nested payload."""
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_path = f"{path}.{key}"
            if is_forbidden_admin_user_key(str(key)):
                found.append(key_path)
            found.extend(find_forbidden_admin_user_keys(value, path=key_path))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            found.extend(
                find_forbidden_admin_user_keys(item, path=f"{path}[{idx}]")
            )
    return found


def assert_admin_user_payload_safe(payload: Any) -> None:
    leaked = find_forbidden_admin_user_keys(payload)
    if leaked:
        raise ValueError(
            "Admin user payload leaked forbidden keys: " + ", ".join(leaked[:20])
        )


def scrub_admin_user_payload(payload: Any) -> Any:
    """Deep-copy scrub: drop forbidden keys from dicts; leave other values."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            if is_forbidden_admin_user_key(str(key)):
                continue
            out[key] = scrub_admin_user_payload(value)
        return out
    if isinstance(payload, list):
        return [scrub_admin_user_payload(item) for item in payload]
    return payload
