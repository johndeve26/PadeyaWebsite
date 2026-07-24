"""Auth/session middleware — request identity bootstrap + cleanup.

Full impersonation validation (active / not expired / target user load) happens
in ``get_current_user``. This middleware ensures every request starts with a
clean identity slot on ``request.state`` and clears thread-local context after.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth.session import clear_auth_session, init_request_auth_state


class AuthSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        init_request_auth_state(request)
        clear_auth_session()
        try:
            return await call_next(request)
        finally:
            # Best-effort cleanup on the ASGI worker thread. Sync FastAPI deps
            # also clear threading.local at the start of get_current_user.
            clear_auth_session()
