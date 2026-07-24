"""Lightweight rate-limit hooks for blog comment writes."""

from __future__ import annotations

from fastapi import Request


async def rate_limit_blog_comment_edit(request: Request) -> None:
    """Placeholder: enforce per-user comment edit limits (Redis) in a later pass."""
    _ = request.client.host if request.client else None
    return None


async def rate_limit_blog_comment_reply(request: Request) -> None:
    """Placeholder: enforce per-user/IP reply burst limits (Redis) in a later pass."""
    _ = request.client.host if request.client else None
    return None
