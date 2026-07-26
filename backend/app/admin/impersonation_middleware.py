"""HTTP middleware: block sensitive impersonation actions + audit requests."""

from __future__ import annotations

import logging
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.admin.impersonation_audit import (
    ADMIN_IMPERSONATION_REQUEST_MADE,
    ADMIN_IMPERSONATION_SENSITIVE_ACTION_BLOCKED,
    record_impersonation_audit,
)
from app.admin.impersonation_guards import (
    IMPERSONATION_SENSITIVE_ACTION_DETAIL,
    is_impersonation_exit_path,
    should_block_impersonation_action,
)
from app.admin.impersonation_scopes import normalize_scopes
from app.core import database as database_module
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

_SKIP_SUFFIXES = (
    "/health",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/favicon.ico",
)


def _safe_query_summary(query: str) -> str | None:
    """Keep only non-sensitive query keys (names only, not secret values)."""
    if not query:
        return None
    keys: list[str] = []
    for part in query.split("&"):
        if not part:
            continue
        key = part.split("=", 1)[0].strip()
        if not key:
            continue
        lowered = key.lower()
        if any(
            frag in lowered
            for frag in (
                "token",
                "password",
                "secret",
                "key",
                "code",
                "auth",
                "signature",
            )
        ):
            continue
        keys.append(key)
        if len(keys) >= 12:
            break
    return ",".join(keys) if keys else None


def _scopes_from_payload(payload: dict) -> list[str]:
    raw = payload.get("impersonation_scopes") or payload.get("scopes")
    return normalize_scopes(raw) or ["view"]


def _impersonation_claims(
    request: Request,
) -> tuple[dict, UUID, UUID, UUID, str | None, str | None, list[str]] | None:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    raw = auth.split(" ", 1)[1].strip()
    if not raw:
        return None
    try:
        payload = decode_access_token(raw)
    except Exception:
        return None
    if not payload.get("is_impersonating"):
        return None
    try:
        impersonation_id = UUID(str(payload["impersonation_id"]))
        actor_admin_id = UUID(str(payload["actor_admin_id"]))
        target_user_id = UUID(str(payload.get("actual_user_id") or payload["sub"]))
    except (KeyError, ValueError, TypeError):
        return None
    reason = payload.get("reason")
    if reason is not None and not isinstance(reason, str):
        reason = None
    ticket = payload.get("support_ticket_id")
    if ticket is not None and not isinstance(ticket, str):
        ticket = None
    scopes = _scopes_from_payload(payload)
    return (
        payload,
        impersonation_id,
        actor_admin_id,
        target_user_id,
        reason,
        ticket,
        scopes,
    )


def _resolve_scopes_for_guard(
    db,
    *,
    impersonation_id: UUID,
    jwt_scopes: list[str],
) -> list[str]:
    """Prefer DB session scopes when the row is available."""
    try:
        from app.admin.impersonation_store import get_impersonation_session

        row = get_impersonation_session(db, impersonation_id)
        if row is not None:
            db_scopes = normalize_scopes(getattr(row, "scopes", None))
            if db_scopes:
                return db_scopes
    except Exception:
        logger.exception("Failed to load impersonation scopes from DB")
    return jwt_scopes or ["view"]


class ImpersonationAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method

        claims = _impersonation_claims(request)
        if claims is not None:
            (
                _,
                impersonation_id,
                actor_admin_id,
                target_user_id,
                reason,
                ticket,
                jwt_scopes,
            ) = claims
            db = database_module.SessionLocal()
            try:
                scopes = _resolve_scopes_for_guard(
                    db,
                    impersonation_id=impersonation_id,
                    jwt_scopes=jwt_scopes,
                )
                if should_block_impersonation_action(
                    method, path, scopes
                ) and not is_impersonation_exit_path(method, path):
                    ip = request.client.host if request.client else None
                    ua = request.headers.get("user-agent")
                    try:
                        record_impersonation_audit(
                            db,
                            action=ADMIN_IMPERSONATION_SENSITIVE_ACTION_BLOCKED,
                            impersonation_id=impersonation_id,
                            actor_admin_id=actor_admin_id,
                            target_user_id=target_user_id,
                            reason=reason,
                            support_ticket_id=ticket,
                            method=method,
                            path=path[:512],
                            status_code=403,
                            action_attempted=f"{method} {path}",
                            metadata={
                                "blocked": True,
                                "guard": "middleware",
                                "scopes": scopes,
                            },
                            ip_address=ip,
                            user_agent=ua,
                        )
                        db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception(
                            "Failed to write impersonation sensitive-action audit log"
                        )
                    return JSONResponse(
                        status_code=403,
                        content={"detail": IMPERSONATION_SENSITIVE_ACTION_DETAIL},
                    )
            finally:
                db.close()

        response = await call_next(request)

        if any(path.endswith(suffix) for suffix in _SKIP_SUFFIXES):
            return response
        # Lifecycle endpoints are audited in the service layer.
        if path.endswith("/impersonation/start") or path.endswith("/impersonation/end"):
            return response
        if claims is None:
            return response

        (
            _,
            impersonation_id,
            actor_admin_id,
            target_user_id,
            reason,
            ticket,
            jwt_scopes,
        ) = claims
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

        db = database_module.SessionLocal()
        try:
            record_impersonation_audit(
                db,
                action=ADMIN_IMPERSONATION_REQUEST_MADE,
                impersonation_id=impersonation_id,
                actor_admin_id=actor_admin_id,
                target_user_id=target_user_id,
                reason=reason,
                support_ticket_id=ticket,
                method=method,
                path=path[:512],
                status_code=response.status_code,
                action_attempted=f"{method} {path}",
                metadata={
                    "query_keys": _safe_query_summary(str(request.url.query)),
                    "scopes": jwt_scopes,
                },
                ip_address=ip,
                user_agent=ua,
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to write impersonation request audit log")
        finally:
            db.close()

        return response
