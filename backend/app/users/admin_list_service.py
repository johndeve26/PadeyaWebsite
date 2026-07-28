"""Admin user list / search — safe fields only (no secrets)."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.users.models import Role, User
from app.users.service import user_role_names


def _admin_user_row(user: User) -> dict:
    """Serialize a user for admin list/detail without secrets or payloads."""
    from app.users.account_status_service import effective_account_status
    from app.users.admin_response_safety import (
        assert_admin_user_payload_safe,
        scrub_admin_user_payload,
    )

    row = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "ambassadors_blocked": bool(getattr(user, "ambassadors_blocked", False)),
        "roles": user_role_names(user),
        "created_at": user.created_at,
        "deactivated_at": getattr(user, "deactivated_at", None),
        "security_locked": getattr(user, "security_locked_at", None) is not None,
        "security_lock_reason": getattr(user, "security_lock_reason", None),
        "under_review": getattr(user, "under_review_at", None) is not None,
        "account_status": effective_account_status(user),
    }
    safe = scrub_admin_user_payload(row)
    assert_admin_user_payload_safe(safe)
    return safe


def list_admin_users(
    db: Session,
    *,
    q: str | None = None,
    status: str | None = None,
    role: str | None = None,
    page: int = 1,
    limit: int = 40,
) -> dict:
    """Paginated admin user directory.

    Never returns password hashes, tokens, QR secrets, payment payloads,
    or message bodies.
    """
    page = max(1, page)
    limit = min(max(1, limit), 100)

    filters: list = []
    if q:
        raw = f"%{q.strip()}%"
        filters.append(or_(User.email.ilike(raw), User.full_name.ilike(raw)))

    status_norm = (status or "").strip().lower()
    if status_norm in {
        "active",
        "under_review",
        "restricted",
        "suspended",
        "banned",
        "deleted",
    }:
        filters.append(User.account_status == status_norm)
    elif status_norm == "inactive":
        filters.append(User.is_active.is_(False))

    role_norm = (role or "").strip().lower()
    if role_norm:
        filters.append(User.roles.any(Role.name == role_norm))

    count_stmt = select(func.count(User.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(db.scalar(count_stmt) or 0)

    # Active accounts first; deactivated/inactive sink to the bottom.
    # Secondary sort preserves newest-first within each group.
    stmt = (
        select(User)
        .options(selectinload(User.roles))
        .order_by(User.is_active.desc(), User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)

    users = list(db.scalars(stmt).all())
    items = [_admin_user_row(u) for u in users]
    return {"items": items, "page": page, "limit": limit, "total": total}
