"""Role-based impersonation capability packs (scopes).

Packs are derived from the actor admin's permissions — not per-session
checkboxes. Money / 2FA / admin-panel denylist stays global regardless of pack.

Scopes
------
``view``         Read dashboards, tickets, orders, inbox (no mutations).
``host_events``  Host event studio mutations (edit / media / tickets / submit).
``credentials``  Password / email / phone recovery (super_admin via full_access).

Pack labels (for audit / UI)
---------------------------
``view``         → only view
``host_events``  → view + host_events
``full``         → view + host_events + credentials
"""

from __future__ import annotations

from typing import Collection, Iterable

from app.users.models import User
from app.users.service import user_has_permission, user_permission_codes

SCOPE_VIEW = "view"
SCOPE_HOST_EVENTS = "host_events"
SCOPE_CREDENTIALS = "credentials"

ALL_SCOPES: tuple[str, ...] = (
    SCOPE_VIEW,
    SCOPE_HOST_EVENTS,
    SCOPE_CREDENTIALS,
)

# Permission that adds host_events on top of base impersonate (view).
PERM_IMPERSONATE_HOST_EVENTS = "admin.users.impersonate.host_events"

_PACK_ORDER = (SCOPE_VIEW, SCOPE_HOST_EVENTS, SCOPE_CREDENTIALS)


def normalize_scopes(scopes: Iterable[str] | None) -> list[str]:
    """Return known scopes in canonical order (deduped)."""
    if not scopes:
        return []
    have = {str(s).strip() for s in scopes if str(s).strip()}
    return [s for s in _PACK_ORDER if s in have]


def pack_label(scopes: Collection[str] | None) -> str:
    """Derive pack name from scopes for audit / UI."""
    have = set(normalize_scopes(scopes))
    if SCOPE_CREDENTIALS in have and SCOPE_HOST_EVENTS in have:
        return "full"
    if SCOPE_HOST_EVENTS in have:
        return "host_events"
    if SCOPE_VIEW in have:
        return "view"
    return "none"


def has_scope(scopes: Collection[str] | None, scope: str) -> bool:
    return scope in set(normalize_scopes(scopes))


def resolve_impersonation_scopes(admin: User) -> list[str]:
    """Scopes this admin may carry when starting impersonation.

    Requires ``admin.users.impersonate`` (or ``admin.full_access``). Base grant
    is ``view`` only. ``host_events`` needs an explicit permission (or full
    access). ``credentials`` requires ``admin.full_access`` (super_admin).

    Caller must still enforce ``can_start_impersonation`` (platform-operator gate).
    """
    if not user_has_permission(admin, "admin.users.impersonate"):
        return []

    scopes: list[str] = [SCOPE_VIEW]
    perms = set(user_permission_codes(admin))
    full = "admin.full_access" in perms

    if full or user_has_permission(admin, PERM_IMPERSONATE_HOST_EVENTS):
        scopes.append(SCOPE_HOST_EVENTS)

    if full:
        scopes.append(SCOPE_CREDENTIALS)

    return normalize_scopes(scopes)
