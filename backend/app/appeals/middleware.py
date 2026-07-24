"""Block suspended accounts from product APIs except appeal / auth / me."""

from __future__ import annotations

from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.users.account_status_service import effective_account_status
from app.users.account_status_constants import (
    ACCOUNT_STATUS_BANNED,
    ACCOUNT_STATUS_DELETED,
    ACCOUNT_STATUS_SUSPENDED,
)
from app.users.service import get_user_by_id

# Paths suspended users may still call.
_SUSPENDED_ALLOWED_EXACT = frozenset(
    {
        "/api/v1/users/me",
        "/api/v1/me/suspension",
        "/api/v1/appeals",
        "/api/v1/health",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)
_SUSPENDED_ALLOWED_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/me/session",
    "/api/v1/appeals/",
)


def _path_allowed(path: str) -> bool:
    if path in _SUSPENDED_ALLOWED_EXACT:
        return True
    return any(path.startswith(p) for p in _SUSPENDED_ALLOWED_PREFIXES)


class SuspendedAccountMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or _path_allowed(path):
            return await call_next(request)

        auth = request.headers.get("Authorization") or ""
        if not auth.lower().startswith("bearer "):
            return await call_next(request)

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            user_id = UUID(str(payload.get("actual_user_id") or payload["sub"]))
        except Exception:  # noqa: BLE001 — let route auth handle bad tokens
            return await call_next(request)

        db = SessionLocal()
        try:
            user = get_user_by_id(db, user_id)
            if user is None:
                blocked = False
                detail = ""
            else:
                status = effective_account_status(user)
                blocked = status in {
                    ACCOUNT_STATUS_SUSPENDED,
                    ACCOUNT_STATUS_BANNED,
                    ACCOUNT_STATUS_DELETED,
                } or (not user.is_active and status != ACCOUNT_STATUS_SUSPENDED)
                if status == ACCOUNT_STATUS_SUSPENDED and _path_allowed(path):
                    blocked = False
                detail = (
                    "Account suspended. You can appeal or sign out."
                    if status == ACCOUNT_STATUS_SUSPENDED
                    else "Account is not available."
                )
        except Exception:  # noqa: BLE001 — never break requests if session/engine mismatch
            blocked = False
            detail = ""
        finally:
            db.close()

        if blocked:
            return JSONResponse(status_code=403, content={"detail": detail})
        return await call_next(request)
