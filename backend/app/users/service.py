"""User domain helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.users.models import Permission, Role, User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.email == email.lower())
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )


def get_user_by_id(db: Session, user_id) -> User | None:
    """Load user + roles + permissions once per request/session (memoized)."""
    from app.core.request_context import (
        get_cached_user_for_session,
        note_user_rbac_load,
        store_cached_user_for_session,
    )

    cached = get_cached_user_for_session(db, user_id)
    if cached is not None:
        return cached

    note_user_rbac_load()
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    if user is not None:
        store_cached_user_for_session(db, user)
    return user


def get_user_account_gate(db: Session, user_id) -> User | None:
    """Thin user load for suspension gate — no roles/permissions/admin notes."""
    from sqlalchemy.orm import noload

    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            noload(User.roles),
            noload("*"),
        )
    )


def user_role_names(user: User) -> list[str]:
    return sorted({role.name for role in user.roles})


def user_permission_codes(user: User) -> list[str]:
    codes: set[str] = set()
    for role in user.roles:
        if role.name == "super_admin":
            # Super admin is treated as holding full access.
            codes.add("admin.full_access")
        for permission in role.permissions:
            codes.add(permission.code)
    return sorted(codes)


def user_has_role(user: User, *role_names: str) -> bool:
    owned = set(user_role_names(user))
    return bool(owned.intersection(role_names)) or "super_admin" in owned


def user_has_permission(user: User, permission_code: str) -> bool:
    from app.users.constants import PERMISSION_IMPLIES

    codes = set(user_permission_codes(user))
    if "admin.full_access" in codes:
        return True
    if permission_code in codes:
        return True
    # Umbrella permissions satisfy implied granular checks.
    for owned, implied in PERMISSION_IMPLIES.items():
        if owned in codes and permission_code in implied:
            return True
    return False


def serialize_user(user: User, db: Session | None = None) -> dict:
    from sqlalchemy.orm import object_session

    from app.users.account_status_service import effective_account_status
    from app.users.admin_response_safety import (
        assert_admin_user_payload_safe,
        scrub_admin_user_payload,
    )

    # End-user: active keys only — never reason / internal_note.
    restriction_keys: list[str] = []
    session = db or object_session(user)
    username: str | None = None
    if session is not None:
        from app.users.restrictions import active_restriction_keys
        from app.users.unified_profile import resolve_user_username

        restriction_keys = active_restriction_keys(session, user.id)
        username = resolve_user_username(session, user)

    data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "username": username,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "ambassadors_blocked": bool(getattr(user, "ambassadors_blocked", False)),
        "roles": user_role_names(user),
        "permissions": user_permission_codes(user),
        "created_at": user.created_at,
        "deactivated_at": getattr(user, "deactivated_at", None),
        "security_locked": getattr(user, "security_locked_at", None) is not None,
        "security_lock_reason": getattr(user, "security_lock_reason", None),
        "under_review": getattr(user, "under_review_at", None) is not None,
        "under_review_reason": getattr(user, "under_review_reason", None),
        "under_review_at": getattr(user, "under_review_at", None),
        "account_status": effective_account_status(user),
        # Legacy alias — same as restriction_keys (keys only).
        "account_restrictions": list(restriction_keys),
        "restriction_keys": list(restriction_keys),
        "suspension": None,
    }
    if data["account_status"] == "suspended" and session is not None:
        from app.appeals.service import get_active_suspension, serialize_suspension_public

        active = get_active_suspension(session, user.id)
        if active is not None:
            data["suspension"] = serialize_suspension_public(active)
    safe = scrub_admin_user_payload(data)
    assert_admin_user_payload_safe(safe)
    return safe


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))


def get_permission_by_code(db: Session, code: str) -> Permission | None:
    return db.scalar(select(Permission).where(Permission.code == code))
