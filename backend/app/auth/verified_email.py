"""Require a verified sign-in email for sensitive account actions."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.users.models import User

VERIFIED_EMAIL_REQUIRED_DETAIL = (
    "Verify your email to continue. Check your inbox or resend from Profile & security."
)


def assert_verified_email(user: User) -> None:
    if user.is_verified:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=VERIFIED_EMAIL_REQUIRED_DETAIL,
    )
