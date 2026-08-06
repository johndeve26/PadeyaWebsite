"""Account-scoped tools — current user only."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.users.models import User
from app.users.service import user_permission_codes, user_role_names


def get_my_account_summary(
    db: Session, *, user: User | None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    return {
        "ok": True,
        "summary": {
            "display_name": (user.full_name or "").strip()[:80] or None,
            "username": getattr(user, "username", None),
            "email_verified": bool(getattr(user, "email_verified", False)),
            # Never return email / phone / secrets
        },
    }


def get_my_roles(
    db: Session, *, user: User | None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    return {
        "ok": True,
        "roles": user_role_names(user),
        "permissions_count": len(user_permission_codes(user)),
    }


def get_my_notifications_summary(
    db: Session, *, user: User | None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    try:
        from app.notifications.service import unread_count

        count = unread_count(db, user_id=user.id)
    except Exception:
        count = 0
    return {"ok": True, "unread_count": int(count)}
