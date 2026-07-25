"""ASGI middleware — enforce platform / section maintenance."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core import database as database
from app.core.request_context import get_maintenance_obs, request_id_var
from app.core.security import decode_access_token
from app.maintenance.sections import (
    ALWAYS_ALLOW_EXACT,
    ALWAYS_ALLOW_PREFIXES,
    SAFE_METHODS,
    SECTION_BY_KEY,
)
from app.maintenance.decision_cache import (
    get_cached_off_allow,
    store_off_allow,
    store_requires_db,
)
from app.maintenance.service import (
    BYPASS_HEADER,
    apply_due_schedules,
    ensure_section_rows,
    get_or_create_settings,
    validate_bypass_token,
    _section_window_active,
)
from app.users.service import get_user_by_id, user_has_permission

logger = logging.getLogger("padeya.maintenance.middleware")


def _allowed_always(path: str) -> bool:
    if path in ALWAYS_ALLOW_EXACT:
        return True
    return any(path.startswith(p) for p in ALWAYS_ALLOW_PREFIXES)


def _is_admin_api(path: str) -> bool:
    return path.startswith("/api/v1/admin/")


def _block(
    *,
    detail: str,
    section: str | None,
    expected_back_at: str | None,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "maintenance": True,
            "section": section,
            "expected_back_at": expected_back_at,
        },
    )


@dataclass(frozen=True)
class _MaintenanceDecision:
    """Computed before releasing the DB session — never await while holding a session."""

    allow: bool = True
    block: JSONResponse | None = None


def _decide(request: Request) -> _MaintenanceDecision:
    """Sync DB work only. Caller must not hold the session across awaits."""
    path = request.url.path
    method = request.method.upper()
    obs = get_maintenance_obs()
    obs.looked_up = True
    obs.db_touched = True
    started = time.perf_counter()
    db = None
    try:
        db = database.SessionLocal()
        try:
            apply_due_schedules(db)
        except Exception:  # noqa: BLE001
            logger.exception("maintenance schedule apply failed")
            db.rollback()

        settings = get_or_create_settings(db)
        sections = ensure_section_rows(db)
        mode = (settings.mode or "off").strip().lower()
        if mode in {"off", "scheduled"}:
            if not any(s.enabled and _section_window_active(s) for s in sections):
                obs.allowed = True
                store_off_allow(mode=mode or "off")
                return _MaintenanceDecision(allow=True)
            mode = "section_only"
            store_requires_db(mode=mode)

        user = None
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            try:
                payload = decode_access_token(auth.split(" ", 1)[1].strip())
                uid = UUID(str(payload.get("actual_user_id") or payload["sub"]))
                user = get_user_by_id(db, uid)
            except Exception:  # noqa: BLE001
                user = None

        if (
            _is_admin_api(path)
            and settings.allow_admin_panel
            and user is not None
            and (
                user_has_permission(user, "admin.full_access")
                or user_has_permission(user, "admin.maintenance.view")
                or user_has_permission(user, "admin.maintenance.manage")
            )
        ):
            obs.allowed = True
            return _MaintenanceDecision(allow=True)

        bypass_tok = request.headers.get(BYPASS_HEADER)
        if (
            user is not None
            and bypass_tok
            and user_has_permission(user, "admin.maintenance.bypass")
            and validate_bypass_token(db, token=bypass_tok, user_id=user.id)
        ):
            obs.allowed = True
            return _MaintenanceDecision(allow=True)

        expected = (
            settings.expected_back_at.isoformat()
            if settings.expected_back_at
            else None
        )

        if mode in {"active", "read_only", "section_only"}:
            store_requires_db(mode=mode)

        if mode == "active":
            obs.allowed = False
            return _MaintenanceDecision(
                allow=False,
                block=_block(
                    detail=settings.message
                    or "Pàdéyá is undergoing maintenance. We’ll be back soon.",
                    section="platform",
                    expected_back_at=expected,
                    status_code=503,
                ),
            )

        if mode == "read_only":
            if method in SAFE_METHODS:
                obs.allowed = True
                return _MaintenanceDecision(allow=True)
            obs.allowed = False
            return _MaintenanceDecision(
                allow=False,
                block=_block(
                    detail="Pàdéyá is in read-only mode. Changes are temporarily disabled.",
                    section="platform",
                    expected_back_at=expected,
                    status_code=423,
                ),
            )

        matched = None
        for sec in sections:
            if not sec.enabled or not _section_window_active(sec):
                continue
            scopes = sec.affected_api_scopes
            if not scopes:
                defn = SECTION_BY_KEY.get(sec.section_key)
                scopes = list(defn.api_prefixes) if defn else []
            for prefix in scopes:
                if path.startswith(str(prefix)):
                    matched = sec
                    break
            if matched is not None:
                break

        if matched is None:
            obs.allowed = True
            return _MaintenanceDecision(allow=True)

        sec_expected = matched.ends_at.isoformat() if matched.ends_at else expected
        if matched.mode == "read_only":
            if method in SAFE_METHODS:
                obs.allowed = True
                return _MaintenanceDecision(allow=True)
            obs.allowed = False
            return _MaintenanceDecision(
                allow=False,
                block=_block(
                    detail=matched.message
                    or "This section is temporarily read-only.",
                    section=matched.section_key,
                    expected_back_at=sec_expected,
                    status_code=423,
                ),
            )

        obs.allowed = False
        return _MaintenanceDecision(
            allow=False,
            block=_block(
                detail=matched.message
                or "This section is temporarily under maintenance.",
                section=matched.section_key,
                expected_back_at=sec_expected,
                status_code=503,
            ),
        )
    except Exception:  # noqa: BLE001
        logger.exception("maintenance middleware error")
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        obs.allowed = True
        obs.notes.append("fail_open")
        return _MaintenanceDecision(allow=True)
    finally:
        obs.duration_ms = (time.perf_counter() - started) * 1000.0
        rid = request_id_var.get()
        logger.info(
            "[MAINTENANCE] request_id=%s duration_ms=%.0f db_touched=%s "
            "allowed=%s path_skipped=false",
            rid or "-",
            obs.duration_ms or 0.0,
            obs.db_touched,
            obs.allowed,
        )
        if db is not None:
            db.close()


class MaintenanceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method.upper()
        if method == "OPTIONS" or _allowed_always(path):
            obs = get_maintenance_obs()
            obs.skipped = True
            obs.looked_up = False
            obs.db_touched = False
            return await call_next(request)

        cached = get_cached_off_allow()
        if cached is True:
            obs = get_maintenance_obs()
            obs.looked_up = True
            obs.db_touched = False
            obs.allowed = True
            obs.notes.append("decision_cache_hit")
            obs.duration_ms = 0.0
            return await call_next(request)

        # Sync SQLAlchemy off the event loop; never hold a Session across await.
        decision = await asyncio.to_thread(_decide, request)
        if decision.block is not None:
            return decision.block
        return await call_next(request)
