"""Permission helpers for admin user management."""

from __future__ import annotations

from fastapi import HTTPException

from app.users.models import User
from app.users.service import user_has_permission


def require_admin_users_perm(admin: User, *codes: str) -> None:
    """Raise 403 unless the admin has at least one of the given permission codes.

    ``admin.full_access`` (and therefore ``super_admin``) satisfies any code via
    ``user_has_permission``.
    """
    if not any(user_has_permission(admin, code) for code in codes):
        raise HTTPException(status_code=403, detail="Insufficient permission")
