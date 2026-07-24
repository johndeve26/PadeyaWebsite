"""Block sensitive mutations while an admin is impersonating a user.

Impersonation must not bypass Host-as-Fan product rules. Checkout and other
money paths are blocked here; affiliation asserts in ``fan_self_abuse`` still
apply to any allowed mutations. There is no production override — a future
admin-only test mode must be explicit, audited, and excluded from public
metrics (see ``order_excluded_from_public_metrics``).

Exact 403 copy: ``IMPERSONATION_SENSITIVE_ACTION_DETAIL``.
"""

from __future__ import annotations

import re

# Exact product copy for blocked sensitive actions (10C).
IMPERSONATION_SENSITIVE_ACTION_DETAIL = (
    "This action is disabled during admin impersonation."
)

_MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Password / email / phone / 2FA / account delete (present + future-proof).
_ACCOUNT_SECURITY = re.compile(
    r"(?:"
    r"/auth/(?:change-password|password|email|phone|2fa|mfa|totp|otp|delete|security)"
    r"|/users/me/(?:password|email|phone|2fa|mfa|totp|delete|security|account)"
    r"|/(?:change-password|enable-2fa|disable-2fa|delete-account)"
    r")",
    re.IGNORECASE,
)

# Money movement, checkout, payouts, bank details, cart → paid purchase.
_MONEY = re.compile(
    r"(?:"
    r"/bank-accounts"
    r"|/finance/"
    r"|/host/payouts"
    r"|/payments/"
    r"|/orders(?:/|$)"
    r"|/dashboard/cart"
    r"|/merch/discounts/validate"
    r"|/track-checkout-started"
    r"|/vault/.+/unlock"
    r"|/vault/subscriptions"
    r"|/print-on-demand/integrations"
    r")",
    re.IGNORECASE,
)

# Ticket ownership transfer (and related ownership mutations).
_TICKETS = re.compile(
    r"/tickets/[^/]+/(?:transfer|cancel|qr-mode|qr-regenerate|bind-device)",
    re.IGNORECASE,
)

# Passport privacy settings + fan passport AI drafts.
_PASSPORT_PRIVACY = re.compile(
    r"(?:/passport/.*/settings|/dashboard/passport/settings|/ai/fan/passport)",
    re.IGNORECASE,
)

# Soft-delete / destructive content actions (POST …/delete and similar).
_CONTENT_DESTROY = re.compile(
    r"(?:"
    r"/messages/[^/]+/delete"
    r"|/host/messages/[^/]+/delete"
    r"|/media/"
    r")",
    re.IGNORECASE,
)

# Support queue mutations (assign/resolve/close/notes/…).
_SUPPORT = re.compile(r"/support/", re.IGNORECASE)

# Provider / API / email / push settings mutations.
_PROVIDER_KEYS = re.compile(
    r"(?:"
    r"/runtime/"
    r"|/email/settings"
    r"|/emails/settings"
    r"|/emails/process-pending"
    r"|/emails/[^/]+/resend"
    r"|/push/settings"
    r"|/push/cleanup-subscriptions"
    r"|/api[-_]?keys?"
    r"|/provider[-_]?keys?"
    r")",
    re.IGNORECASE,
)

# Social / Fan Connect connect-disconnect (OAuth + Fan Connect).
_SOCIAL = re.compile(
    r"(?:"
    r"/oauth"
    r"|/social/(?:connect|disconnect|link|unlink)"
    r"|/connected-accounts"
    r"|/auth/social"
    r"|/fan-connect/"
    r")",
    re.IGNORECASE,
)

# Admin-shaped paths: /admin/… or …/admin/…
_ADMIN_SEGMENT = re.compile(r"(?:^|/)admin(?:/|$)", re.IGNORECASE)


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    if len(path) > 1 and path.endswith("/"):
        return path[:-1]
    return path


def is_impersonation_exit_path(method: str, path: str) -> bool:
    """Exit impersonation must always remain allowed."""
    return method.upper() == "POST" and _normalize_path(path).endswith(
        "/admin/impersonation/end"
    )


def is_admin_api_path(path: str) -> bool:
    return bool(_ADMIN_SEGMENT.search(_normalize_path(path)))


def should_block_impersonation_action(method: str, path: str) -> bool:
    """Return True when this HTTP action must be refused during impersonation.

    Blocked (10C): password/email/phone/2FA, account delete, bank/payouts,
    checkout/paid purchase, ticket transfer, content delete, Passport privacy,
    social/Fan Connect link changes, API/provider keys, all admin routes,
    support-queue mutations, finance mutations.

    Allowed: GET dashboard / tickets / orders / merch / refunds / Passport /
    Vault / settings reads, UI navigation, and ``POST …/admin/impersonation/end``.
    """
    method_u = method.upper()
    path_n = _normalize_path(path)

    if is_impersonation_exit_path(method_u, path_n):
        return False

    # Provider webhooks are not user sessions.
    lowered = path_n.lower()
    if "/payments/webhooks/" in lowered:
        return False

    if method_u in ("HEAD", "OPTIONS"):
        return False

    # Admin surface: block all methods (UI already denies /admin while impersonating).
    if is_admin_api_path(path_n):
        return True

    # Reads stay allowed for support navigation / reproduction.
    if method_u == "GET":
        return False

    if method_u not in _MUTATING:
        return False

    # Any DELETE of user/host content is sensitive.
    if method_u == "DELETE":
        return True

    # POST/PUT/PATCH: category denylist.
    if _ACCOUNT_SECURITY.search(path_n):
        return True
    if _MONEY.search(path_n):
        return True
    if _TICKETS.search(path_n):
        return True
    if _PASSPORT_PRIVACY.search(path_n):
        return True
    if _CONTENT_DESTROY.search(path_n):
        return True
    if _SUPPORT.search(path_n):
        return True
    if _PROVIDER_KEYS.search(path_n):
        return True
    if _SOCIAL.search(path_n):
        return True

    # Refunds / reviews moderation / CRM destructive — covered by /finance/ and
    # DELETE; also block review moderate + refund request posts by name.
    if "/refunds/" in lowered:
        return True
    if "/reviews/" in lowered and (
        lowered.endswith("/moderate") or "/moderate" in lowered
    ):
        return True
    if "reward-status" in lowered or lowered.endswith("/reverse"):
        return True

    return False
