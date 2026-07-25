"""Request-scoped IDs and lightweight observability counters.

No secrets, tokens, or private content belong here.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_MAX_REQUEST_ID_LEN = 64

request_id_var: ContextVar[str | None] = ContextVar("padeya_request_id", default=None)


@dataclass
class AuthLoadCounters:
    """How often identity/RBAC was loaded for the current request."""

    user_loads: int = 0
    # roles/permissions are loaded with the user via selectinload today;
    # counted when that path runs so Phase 1 can confirm duplication.
    roles_loads: int = 0
    permissions_loads: int = 0


_auth_counters: ContextVar[AuthLoadCounters | None] = ContextVar(
    "padeya_auth_load_counters", default=None
)


def sanitize_request_id(raw: str | None) -> str | None:
    """Accept a client X-Request-ID only when short and safe."""
    if raw is None:
        return None
    value = raw.strip()
    if not value or len(value) > _MAX_REQUEST_ID_LEN:
        return None
    if not _REQUEST_ID_RE.fullmatch(value):
        return None
    return value


def new_request_id() -> str:
    return uuid.uuid4().hex


def resolve_request_id(incoming: str | None) -> str:
    return sanitize_request_id(incoming) or new_request_id()


def reset_auth_load_counters() -> Token:
    return _auth_counters.set(AuthLoadCounters())


def restore_auth_load_counters(token: Token) -> None:
    _auth_counters.reset(token)


def get_auth_load_counters() -> AuthLoadCounters:
    current = _auth_counters.get()
    if current is None:
        current = AuthLoadCounters()
        _auth_counters.set(current)
    return current


def note_user_rbac_load() -> None:
    """Record one DB load of user + roles + permissions (selectinload path)."""
    counters = get_auth_load_counters()
    counters.user_loads += 1
    counters.roles_loads += 1
    counters.permissions_loads += 1


# Per-request memo: user_id -> (session_id, User). Never share across sessions.
_user_rbac_cache: ContextVar[dict | None] = ContextVar(
    "padeya_user_rbac_cache", default=None
)


def reset_user_rbac_cache() -> Token:
    return _user_rbac_cache.set({})


def restore_user_rbac_cache(token: Token) -> None:
    _user_rbac_cache.reset(token)


def get_cached_user_for_session(db: object, user_id: object):
    cache = _user_rbac_cache.get()
    if not cache:
        return None
    hit = cache.get(user_id)
    if hit is None:
        return None
    sess_id, user = hit
    if sess_id != id(db):
        return None
    return user


def store_cached_user_for_session(db: object, user: object) -> None:
    cache = _user_rbac_cache.get()
    if cache is None:
        cache = {}
        _user_rbac_cache.set(cache)
    uid = getattr(user, "id", None)
    if uid is None:
        return
    cache[uid] = (id(db), user)


def auth_load_summary() -> str:
    c = get_auth_load_counters()
    return (
        f"user_loads={c.user_loads} "
        f"roles_loads={c.roles_loads} "
        f"permissions_loads={c.permissions_loads}"
    )


@dataclass
class MaintenanceObs:
    looked_up: bool = False
    db_touched: bool = False
    duration_ms: float | None = None
    allowed: bool | None = None
    skipped: bool = False
    notes: list[str] = field(default_factory=list)


_maintenance_obs: ContextVar[MaintenanceObs | None] = ContextVar(
    "padeya_maintenance_obs", default=None
)


def reset_maintenance_obs() -> Token:
    return _maintenance_obs.set(MaintenanceObs())


def restore_maintenance_obs(token: Token) -> None:
    _maintenance_obs.reset(token)


def get_maintenance_obs() -> MaintenanceObs:
    current = _maintenance_obs.get()
    if current is None:
        current = MaintenanceObs()
        _maintenance_obs.set(current)
    return current
