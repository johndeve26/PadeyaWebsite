"""Block sensitive mutations while an admin is impersonating a user.

Impersonation must not bypass Host-as-Fan product rules. Checkout and other
money paths are blocked here; affiliation asserts in ``fan_self_abuse`` still
apply to any allowed mutations. There is no production override — a future
admin-only test mode must be explicit, audited, and excluded from public
metrics (see ``order_excluded_from_public_metrics``).

Capability packs (scopes) further restrict what is allowed:

- ``view`` — GET / navigation only (plus exit)
- ``host_events`` — host studio mutations (events / media / ticket tiers / legacy /
  CRM drafts). Marketing email *dispatch* stays full-pack only.
- ``credentials`` — full pack: unrestricted audited mutations (finance, privacy, …)
  plus password / email / phone recovery. Admin APIs stay blocked.

Exact 403 copy: ``IMPERSONATION_SENSITIVE_ACTION_DETAIL``.
"""

from __future__ import annotations

import re
from typing import Collection

from app.admin.impersonation_scopes import (
    SCOPE_CREDENTIALS,
    SCOPE_HOST_EVENTS,
    SCOPE_VIEW,
    has_scope,
    has_unrestricted_impersonation,
    normalize_scopes,
)

# Exact product copy for blocked sensitive actions (10C).
IMPERSONATION_SENSITIVE_ACTION_DETAIL = (
    "This action is disabled during admin impersonation."
)

_MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# 2FA / account delete stay blocked. Password/email/phone are scope-gated.
_ACCOUNT_SECURITY = re.compile(
    r"(?:"
    r"/auth/(?:2fa|mfa|totp|otp|delete|security)"
    r"|/users/me/(?:2fa|mfa|totp|delete|security|account)"
    r"|/(?:enable-2fa|disable-2fa|delete-account)"
    r")",
    re.IGNORECASE,
)

# Credential recovery — allowed only with ``credentials`` scope.
_CREDENTIALS = re.compile(
    r"(?:"
    r"/auth/change-password"
    r"|/auth/change-email"
    r"|/auth/change-email/confirm"
    r"|/users/me/(?:email|phone|password)"
    r"|/users/me/change-(?:email|password|phone)"
    r")",
    re.IGNORECASE,
)

# Host studio mutations — allowed only with ``host_events`` scope.
_HOST_EVENTS = re.compile(
    r"(?:"
    r"/events(?:/|$)"
    r"|/host/events(?:/|$)"
    r"|/host/legacy(?:/|$)"
    r"|/legacy/me(?:/|$)"
    r"|/crm/host(?:/|$)"
    r")",
    re.IGNORECASE,
)

# Real marketing delivery — full pack only (even when CRM drafts are allowed).
_HOST_CRM_DISPATCH = re.compile(
    r"/crm/host/announcements/[^/]+/dispatch-email$",
    re.IGNORECASE,
)

# Host studio may delete unused ticket tiers / event media while scoped.
_HOST_EVENT_DELETE_ALLOWED = re.compile(
    r"/events/by-id/[^/]+/(?:ticket-types|media)/[^/]+$",
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

# Soft-delete of messaging content only — host event /media/ uploads must work.
_CONTENT_DESTROY = re.compile(
    r"(?:"
    r"/messages/[^/]+/delete"
    r"|/host/messages/[^/]+/delete"
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
    """Exit impersonation and auth logout must remain allowed."""
    if method.upper() != "POST":
        return False
    path_n = _normalize_path(path)
    return path_n.endswith("/admin/impersonation/end") or path_n.endswith("/auth/logout")


def is_admin_api_path(path: str) -> bool:
    return bool(_ADMIN_SEGMENT.search(_normalize_path(path)))


def is_credential_impersonation_path(path: str) -> bool:
    return bool(_CREDENTIALS.search(_normalize_path(path)))


def is_host_event_impersonation_path(path: str) -> bool:
    path_n = _normalize_path(path)
    if _HOST_CRM_DISPATCH.search(path_n):
        # Dispatch is gated separately (full pack only).
        return False
    if _HOST_EVENTS.search(path_n):
        return True
    if _HOST_EVENT_DELETE_ALLOWED.search(path_n):
        return True
    return False


def should_block_impersonation_action(
    method: str,
    path: str,
    scopes: Collection[str] | None = None,
) -> bool:
    """Return True when this HTTP action must be refused during impersonation.

    Admin APIs are always blocked. View / host_events packs use a mutation
    denylist (money, privacy, …). Full pack (``credentials`` scope) allows
    unrestricted audited mutations. ``scopes=None`` is view-only.
    """
    method_u = method.upper()
    path_n = _normalize_path(path)
    have = set(normalize_scopes(scopes) if scopes is not None else [SCOPE_VIEW])

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

    # Reads stay allowed for support navigation / reproduction (view pack).
    if method_u == "GET":
        return False

    if method_u not in _MUTATING:
        return False

    # Full pack (super_admin): allow all user-surface mutations (audited).
    if has_unrestricted_impersonation(have):
        return False

    # Denylist for view / host_events packs.
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
    if "/refunds/" in lowered:
        return True
    if "/reviews/" in lowered and (
        lowered.endswith("/moderate") or "/moderate" in lowered
    ):
        return True
    if "reward-status" in lowered or lowered.endswith("/reverse"):
        return True

    # Marketing blast send — never with view / host_events (fans would get real mail).
    if _HOST_CRM_DISPATCH.search(path_n):
        return True

    # Credential recovery — credentials pack only.
    if is_credential_impersonation_path(path_n):
        return not has_scope(have, SCOPE_CREDENTIALS)

    # Host event studio / CRM drafts — host_events pack only.
    if method_u == "DELETE":
        if _HOST_EVENT_DELETE_ALLOWED.search(path_n):
            return not has_scope(have, SCOPE_HOST_EVENTS)
        # CRM host resource deletes (segments, etc.) — same pack as drafts.
        if re.search(r"/crm/host(?:/|$)", path_n, re.IGNORECASE):
            return not has_scope(have, SCOPE_HOST_EVENTS)
        return True

    if is_host_event_impersonation_path(path_n):
        return not has_scope(have, SCOPE_HOST_EVENTS)

    # View pack: no other mutations.
    return True
