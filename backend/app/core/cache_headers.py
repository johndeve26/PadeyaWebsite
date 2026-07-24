"""HTTP Cache-Control middleware for public vs private API surfaces.

Public GETs on an allowlist get short shared cache + SWR headers.
Everything sensitive (auth, admin, payments, tickets, messages, …) gets
``Cache-Control: no-store``. Authenticated requests to private paths never
receive public cache directives.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

# Path suffixes after api_prefix (e.g. /api/v1)
_NO_STORE_PREFIXES = (
    "/auth",
    "/admin",
    "/payments",
    "/orders",
    "/tickets",
    "/messages",
    "/notifications",
    "/push",
    "/support",
    "/checkins",
    "/hosts/me",
    "/passport/me",
    "/dashboard",
    "/vault",
    "/finance",
    "/crm",
    "/ai",
    "/appeals",
    "/runtime-settings",
    "/maintenance",
    "/email",
    "/promos",  # validate/redeem can be sensitive
    "/ambassadors",
    "/fan-connect",
    "/memories",
    "/analytics",
    "/me",
    "/team-invites",
)

# Explicit public GET allowlist (regex against path after api prefix).
_PUBLIC_GET_RULES: list[tuple[re.Pattern[str], str]] = [
    # events discovery
    (re.compile(r"^/events/?$"), "public, max-age=90, stale-while-revalidate=60"),
    (re.compile(r"^/events/categories/?$"), "public, max-age=1800, stale-while-revalidate=300"),
    (re.compile(r"^/events/padeya-picks/?$"), "public, max-age=120, stale-while-revalidate=60"),
    (re.compile(r"^/events/nearby/?$"), "public, max-age=90, stale-while-revalidate=30"),
    (re.compile(r"^/events/map/?$"), "public, max-age=90, stale-while-revalidate=30"),
    (re.compile(r"^/events/calendar/?$"), "public, max-age=120, stale-while-revalidate=60"),
    (re.compile(r"^/events/[a-z0-9-]+/?$"), "public, max-age=120, stale-while-revalidate=60"),
    # blog / help / cms
    (re.compile(r"^/blog/"), "public, max-age=3600, stale-while-revalidate=600"),
    (re.compile(r"^/help/"), "public, max-age=3600, stale-while-revalidate=600"),
    (re.compile(r"^/cms/faqs/?$"), "public, max-age=3600, stale-while-revalidate=600"),
    (re.compile(r"^/cms/banners/?$"), "public, max-age=600, stale-while-revalidate=120"),
    (re.compile(r"^/cms/browse-tiles/?$"), "public, max-age=1800, stale-while-revalidate=300"),
    # taxonomy (public vocab only — admin paths caught by /admin above if prefixed;
    # taxonomy admin is under /taxonomy/admin)
    (re.compile(r"^/taxonomy/(categories|host-types|audience-types|tags|vibes|venue-types|locations)(/|$)"), "public, max-age=1800, stale-while-revalidate=300"),
    # sponsorships public
    (re.compile(r"^/sponsorships/public/"), "public, max-age=180, stale-while-revalidate=60"),
    # directories / public profiles
    (re.compile(r"^/legacy/discover/hosts/?$"), "public, max-age=180, stale-while-revalidate=60"),
    (re.compile(r"^/fans/?$"), "public, max-age=180, stale-while-revalidate=60"),
    (re.compile(r"^/passport/public/"), "public, max-age=180, stale-while-revalidate=60"),
    (re.compile(r"^/f/[a-zA-Z0-9_]+(/activity|/badges)?/?$"), "public, max-age=180, stale-while-revalidate=60"),
    (re.compile(r"^/pricing/public/?$"), "public, max-age=600, stale-while-revalidate=120"),
    (re.compile(r"^/placements/public/"), "public, max-age=120, stale-while-revalidate=60"),
]

# Event paths that look like public slugs but are private
_EVENT_PRIVATE = re.compile(
    r"^/events/(mine|admin|templates|by-id|media|health)(/|$)|^/events/[^/]+/fan-connect/?$"
)


def _strip_api_prefix(path: str) -> str:
    prefix = get_settings().api_prefix.rstrip("/")
    if path.startswith(prefix):
        return path[len(prefix) :] or "/"
    return path


def is_no_store_path(api_path: str) -> bool:
    p = api_path if api_path.startswith("/") else f"/{api_path}"
    if _EVENT_PRIVATE.match(p):
        return True
    if p.startswith("/taxonomy/admin") or p.startswith("/cms/admin") or p.startswith("/blog/admin"):
        return True
    if p.startswith("/help/admin") or p.startswith("/knowledge"):
        # knowledge-base admin mounts vary; be safe
        if "/admin" in p:
            return True
    for prefix in _NO_STORE_PREFIXES:
        if p == prefix or p.startswith(prefix + "/") or p.startswith(prefix + "?"):
            return True
        # also match exact prefix without trailing content
        if p.startswith(prefix):
            return True
    return False


def public_cache_control(api_path: str) -> str | None:
    """Return Cache-Control value for a public GET, or None."""
    p = api_path if api_path.startswith("/") else f"/{api_path}"
    if is_no_store_path(p):
        return None
    for pattern, header in _PUBLIC_GET_RULES:
        if pattern.search(p):
            return header
    return None


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Attach Cache-Control for public GETs; no-store for private surfaces."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Do not override if handler already set Cache-Control
        if response.headers.get("cache-control"):
            return response

        method = request.method.upper()
        api_path = _strip_api_prefix(request.url.path)

        if method != "GET" and method != "HEAD":
            if is_no_store_path(api_path):
                response.headers["Cache-Control"] = "no-store"
            return response

        if is_no_store_path(api_path):
            response.headers["Cache-Control"] = "no-store"
            return response

        # Authenticated request → never public shared cache
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            # Still allow public discovery GETs without private data to be
            # privately cached briefly; but prefer no-store when ambiguous.
            # Public allowlist responses are identical for all users — OK to
            # keep public directive even with bearer (read-only discovery).
            cc = public_cache_control(api_path)
            if cc:
                response.headers["Cache-Control"] = cc
            else:
                response.headers["Cache-Control"] = "no-store"
            return response

        cc = public_cache_control(api_path)
        if cc:
            response.headers["Cache-Control"] = cc
            response.headers.setdefault("Vary", "Accept-Encoding")
        return response
