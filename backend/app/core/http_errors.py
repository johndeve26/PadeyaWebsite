"""Standard HTTP error helpers — privacy-safe 404 responses."""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException

NOT_FOUND_DETAIL = "Resource not found."
NOT_FOUND_CODE = "NOT_FOUND"


def raise_not_found(detail: str | None = None) -> NoReturn:
    """Raise a privacy-safe 404 (generic detail by default)."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail or NOT_FOUND_DETAIL,
    )


def not_found_payload(detail: Any = None) -> dict[str, str]:
    """Build the canonical API 404 body."""
    if isinstance(detail, dict):
        message = str(
            detail.get("detail")
            or detail.get("message")
            or NOT_FOUND_DETAIL
        )
        code = str(detail.get("code") or NOT_FOUND_CODE)
    elif isinstance(detail, str) and detail.strip():
        message = detail.strip()
        code = NOT_FOUND_CODE
    else:
        message = NOT_FOUND_DETAIL
        code = NOT_FOUND_CODE
    return {"detail": message, "code": code}


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Ensure 404 responses always include ``code: NOT_FOUND``."""
    headers = getattr(exc, "headers", None)
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return JSONResponse(
            status_code=404,
            content=not_found_payload(exc.detail),
            headers=headers,
        )
    detail = exc.detail
    if not isinstance(detail, (str, list, dict)):
        detail = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=headers,
    )
