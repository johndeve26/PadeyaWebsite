"""Admin tools — navigation and explain only. No finance mutations."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.routes.auth_registry import get_auth_route_by_key, resolve_auth_route
from app.users.models import User
from app.users.service import user_has_permission


def _is_admin(user: User) -> bool:
    return user_has_permission(user, "admin.full_access") or user_has_permission(
        user, "admin.ai.manage_settings"
    )


def admin_navigate(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    permissions: list[str] | None = None,
    roles: list[str] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not _is_admin(user):
        return {"ok": False, "error": "forbidden"}
    args = args or {}
    key = str(args.get("route_key") or "").strip()
    query = str(args.get("query") or args.get("q") or "admin").strip()
    if key:
        entry = get_auth_route_by_key(key)
        if entry is None or not entry.navigation_only and not key.startswith("admin"):
            # Allow admin_* keys even if not flagged navigation_only when path starts /admin
            if entry is None or not str(entry.path).startswith("/admin"):
                return {"ok": False, "error": "not_admin_route"}
        return {
            "ok": True,
            "route_key": entry.key if entry else key,
            "path": entry.path if entry else "/admin",
            "title": entry.title if entry else "Admin",
            "navigation_only": True,
            "note": "Navigation only — the assistant cannot mutate finance or permissions.",
        }
    entry = resolve_auth_route(query, roles=roles, permissions=permissions)
    if entry is None or not str(entry.path).startswith("/admin"):
        return {
            "ok": True,
            "route_key": "admin_home",
            "path": "/admin",
            "title": "Admin",
            "navigation_only": True,
        }
    return {
        "ok": True,
        "route_key": entry.key,
        "path": entry.path,
        "title": entry.title,
        "navigation_only": True,
        "note": "Navigation only — no finance mutations via assistant.",
    }


def admin_explain(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    page_context: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not _is_admin(user):
        return {"ok": False, "error": "forbidden"}
    ctx = page_context or {}
    route_key = str((args or {}).get("route_key") or ctx.get("route_key") or "admin_home")
    entry = get_auth_route_by_key(route_key)
    return {
        "ok": True,
        "route_key": route_key,
        "summary": (
            entry.description
            if entry
            else "Admin Control Center. Use product UI for finance, payouts, and permissions."
        ),
        "constraints": [
            "Assistant cannot refund, approve payouts, edit ledger, or impersonate.",
            "Use Admin UI with proper permissions for sensitive actions.",
        ],
        "path": entry.path if entry else "/admin",
    }
