"""Rate-limit placeholders for auth endpoints.

Not enforced yet — hooks exist so login/register can plug in Redis-backed
limits without changing route signatures later.
"""

from __future__ import annotations

from fastapi import Request


async def rate_limit_login(request: Request) -> None:
    """Placeholder: enforce login attempt limits (IP + email) in a later pass."""
    _ = request.client.host if request.client else None
    return None


async def rate_limit_register(request: Request) -> None:
    """Placeholder: enforce registration attempt limits by IP."""
    _ = request.client.host if request.client else None
    return None


async def rate_limit_password_reset(request: Request) -> None:
    """Placeholder: enforce password-reset request limits by IP."""
    _ = request.client.host if request.client else None
    return None


async def rate_limit_email_verification(request: Request) -> None:
    """Placeholder: enforce email verification confirm/resend limits by IP."""
    _ = request.client.host if request.client else None
    return None
