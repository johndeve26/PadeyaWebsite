"""Global exception handlers — safe client responses, detailed server logs."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.http_errors import http_exception_handler
from app.core.request_context import request_id_var

logger = logging.getLogger("padeya.errors")


def _request_id(request: Request) -> str | None:
    rid = getattr(request.state, "request_id", None)
    if isinstance(rid, str) and rid:
        return rid
    return request_id_var.get()


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Log unexpected errors; never leak tracebacks to production clients."""
    if isinstance(exc, StarletteHTTPException):
        # Preserve FastAPI/Starlette HTTPException behavior (do not convert 4xx→500).
        return await http_exception_handler(request, exc)

    rid = _request_id(request)
    logger.exception(
        "Unhandled exception request_id=%s method=%s path=%s type=%s",
        rid or "-",
        request.method,
        request.url.path,
        type(exc).__name__,
    )

    headers = {"X-Request-ID": rid} if rid else None
    settings = get_settings()
    # Keep production clients generic; allow detail only in non-production DEBUG.
    if settings.debug and not settings.is_production:
        detail = f"Internal server error ({type(exc).__name__})"
    else:
        detail = "Internal server error"

    body: dict[str, str] = {"detail": detail}
    if rid:
        body["request_id"] = rid
    return JSONResponse(status_code=500, content=body, headers=headers)
