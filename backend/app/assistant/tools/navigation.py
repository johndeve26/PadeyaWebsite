"""Navigation and help tools."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.assistant.routes.auth_registry import resolve_auth_route
from app.assistant.routes.error_help import explain_ui_errors
from app.assistant.routes.page_help import get_page_help
from app.assistant.routes.public_registry import (
    get_route_by_key,
    resolve_public_route,
)


def navigate_to_route(
    db: Session,
    *,
    args: dict[str, Any],
    authenticated: bool = False,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    **_: Any,
) -> dict[str, Any]:
    key = str(args.get("route_key") or args.get("key") or "").strip()
    query = str(args.get("query") or args.get("q") or "").strip()
    if key:
        public = get_route_by_key(key)
        if public:
            return {
                "ok": True,
                "route_key": public.key,
                "path": public.path,
                "title": public.title,
                "mode": "public",
            }
        if authenticated:
            from app.assistant.routes.auth_registry import get_auth_route_by_key

            auth = get_auth_route_by_key(key)
            if auth:
                return {
                    "ok": True,
                    "route_key": auth.key,
                    "path": auth.path,
                    "title": auth.title,
                    "mode": "authenticated",
                    "navigation_only": auth.navigation_only,
                }
        return {"ok": False, "error": "unknown_route_key"}

    needle = query or key
    public = resolve_public_route(needle)
    if public:
        return {
            "ok": True,
            "route_key": public.key,
            "path": public.path,
            "title": public.title,
            "mode": "public",
        }
    if authenticated:
        auth = resolve_auth_route(needle, roles=roles, permissions=permissions)
        if auth:
            return {
                "ok": True,
                "route_key": auth.key,
                "path": auth.path,
                "title": auth.title,
                "mode": "authenticated",
                "navigation_only": auth.navigation_only,
            }
    return {"ok": False, "error": "no_match", "query": needle}


def explain_current_page(
    db: Session, *, args: dict[str, Any], page_context: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    ctx = page_context or {}
    route_key = str(args.get("route_key") or ctx.get("route_key") or "").strip()
    help_entry = get_page_help(route_key)
    errors = explain_ui_errors(list(ctx.get("ui_errors") or args.get("ui_errors") or []))
    return {
        "ok": True,
        "route_key": route_key or None,
        "page_title": ctx.get("page_title"),
        "summary": help_entry.summary if help_entry else "I can help with this page — ask a specific question.",
        "tips": list(help_entry.tips) if help_entry else [],
        "related_actions": list(help_entry.related_actions) if help_entry else [],
        "errors": [
            {
                "code": e.code,
                "summary": e.summary,
                "next_steps": list(e.next_steps),
                "related_route_key": e.related_route_key,
            }
            for e in errors
        ],
    }


def search_help(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    from app.assistant.tools.public_search import search_public_resources

    result = search_public_resources(db, args=args)
    # Prefer help-typed results
    help_only = [r for r in result.get("results", []) if r.get("type") == "help"]
    if help_only:
        result = {**result, "results": help_only, "count": len(help_only)}
    # Always include help hub
    result.setdefault("hub", {"title": "Help Center", "url": "/help"})
    result.setdefault("support", {"title": "Support", "url": "/support"})
    return result
