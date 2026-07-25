"""Production-safe HTTP request timing, request IDs, and Server-Timing."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.request_context import (
    auth_load_summary,
    get_maintenance_obs,
    request_id_var,
    reset_auth_load_counters,
    reset_maintenance_obs,
    reset_user_rbac_cache,
    resolve_request_id,
    restore_auth_load_counters,
    restore_maintenance_obs,
    restore_user_rbac_cache,
)

logger = logging.getLogger("padeya.http")

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_HEX32_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_NUMERIC_RE = re.compile(r"^\d+$")

_DYNAMIC_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(/api/v1/events/)[^/]+$"), r"\1{slug}"),
    (re.compile(r"^(/api/v1/events/)[^/]+(/.*)$"), r"\1{slug}\2"),
    (re.compile(r"^(/api/v1/legacy/)[^/]+$"), r"\1{slug}"),
    (re.compile(r"^(/api/v1/u/)[^/]+(/legacy.*)$"), r"\1{username}\2"),
    (re.compile(r"^(/api/v1/u/)[^/]+$"), r"\1{username}"),
    (re.compile(r"^(/api/v1/f/)[^/]+$"), r"\1{username}"),
    (re.compile(r"^(/api/v1/sponsors/public/)[^/]+$"), r"\1{slug}"),
    (re.compile(r"^(/api/v1/merch/)[^/]+$"), r"\1{slug}"),
    (re.compile(r"^(/api/v1/blog/posts/)[^/]+$"), r"\1{slug}"),
    (re.compile(r"^(/api/v1/help/articles/)[^/]+$"), r"\1{slug}"),
    (re.compile(r"^(/api/v1/hosts/)[^/]+$"), r"\1{id_or_slug}"),
)


def normalize_path(path: str) -> str:
    """Collapse resource IDs/slugs for low-cardinality logging."""
    for pattern, repl in _DYNAMIC_RULES:
        if pattern.match(path):
            return pattern.sub(repl, path)

    parts = path.split("/")
    out: list[str] = []
    for part in parts:
        if not part:
            out.append(part)
            continue
        if _UUID_RE.fullmatch(part) or _HEX32_RE.fullmatch(part):
            out.append("{id}")
        elif _NUMERIC_RE.fullmatch(part) and len(part) > 2:
            out.append("{id}")
        else:
            out.append(part)
    return "/".join(out)


def route_template(request: Request) -> str:
    """Prefer FastAPI route path template; fall back to normalized URL path."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path and "{" in path:
        raw = request.url.path
        # Router paths may omit the /api/v1 mount prefix — prefer normalized URL.
        if raw.startswith("/api/") and not path.startswith("/api/"):
            return normalize_path(raw)
        return path
    return normalize_path(request.url.path)


def slow_label(duration_ms: float) -> str | None:
    if duration_ms >= 10_000:
        return "CRITICAL"
    if duration_ms >= 3_000:
        return "VERY_SLOW"
    if duration_ms >= 1_000:
        return "SLOW"
    return None


def _deployment_tag() -> str:
    settings = get_settings()
    version = (getattr(settings, "app_version", None) or "").strip()
    sha = (getattr(settings, "build_sha", None) or "").strip()
    if version and sha:
        return f"{version}+{sha[:12]}"
    if version:
        return version
    if sha:
        return sha[:12]
    return settings.app_env


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Outer middleware: request ID, duration logs, Server-Timing."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = request.headers.get("x-request-id")
        request_id = resolve_request_id(incoming)
        request.state.request_id = request_id
        rid_token = request_id_var.set(request_id)
        auth_token = reset_auth_load_counters()
        maint_token = reset_maintenance_obs()
        user_cache_token = reset_user_rbac_cache()

        started = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            status_code = getattr(response, "status_code", 500) if response else 500
            path = route_template(request)
            env = get_settings().app_env
            deploy = _deployment_tag()
            label = slow_label(duration_ms)
            prefix = f"[HTTP:{label}]" if label else "[HTTP]"
            auth_summary = auth_load_summary()
            maint = get_maintenance_obs()
            maint_bits = (
                f"maintenance_lookup={maint.looked_up} "
                f"maintenance_db={maint.db_touched} "
                f"maintenance_ms="
                f"{maint.duration_ms if maint.duration_ms is not None else '-'}"
            )
            log_line = (
                f"{prefix} request_id={request_id} {request.method} {path} "
                f"{status_code} duration_ms={duration_ms:.0f} "
                f"env={env} deploy={deploy} {auth_summary} {maint_bits}"
            )
            if label in {"VERY_SLOW", "CRITICAL"}:
                logger.warning(log_line)
            else:
                logger.info(log_line)

            if response is not None:
                response.headers["X-Request-ID"] = request_id
                # Application duration only — db/redis/upstream slots reserved later.
                existing = response.headers.get("Server-Timing")
                app_metric = f"app;dur={duration_ms:.1f}"
                response.headers["Server-Timing"] = (
                    f"{existing}, {app_metric}" if existing else app_metric
                )

            request_id_var.reset(rid_token)
            restore_auth_load_counters(auth_token)
            restore_maintenance_obs(maint_token)
            restore_user_rbac_cache(user_cache_token)
