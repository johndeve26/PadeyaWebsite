"""User profile update and admin deactivate/restore (delegates status MVP)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.users.account_status_constants import (
    ACCOUNT_STATUS_ACTIVE,
    ACCOUNT_STATUS_DELETED,
    ACCOUNT_STATUS_SUSPENDED,
)
from app.users.account_status_service import (
    change_account_status,
    effective_account_status,
    stored_restrictions,
)
from app.users.admin_user_audit import (
    ADMIN_USER_STATUS_CHANGED,
    write_admin_user_audit,
)
from app.users.admin_users_permissions import require_admin_users_perm
from app.users.models import User
from app.users.service import get_user_by_id


def update_my_profile(
    db: Session,
    *,
    user: User,
    full_name: str | None = None,
    display_name: str | None = None,
    username: str | None = None,
    avatar_url: str | None = None,
    clear_avatar: bool = False,
    gender: str | None = None,
    gender_set: bool = False,
    gender_visibility: str | None = None,
    gender_visibility_set: bool = False,
) -> User:
    from app.users.gender import (
        DEFAULT_GENDER_VISIBILITY,
        parse_gender,
        parse_gender_visibility,
    )
    from app.users.unified_profile import (
        apply_unified_avatar,
        apply_unified_display_name,
        apply_unified_username,
    )

    details: dict[str, str] = {}
    name = display_name if display_name is not None else full_name
    if name is not None:
        applied = apply_unified_display_name(db, user, name)
        details["display_name"] = applied
    if username is not None:
        details["username"] = apply_unified_username(db, user, username)
    if clear_avatar:
        apply_unified_avatar(db, user, None)
        details["avatar_url"] = ""
    elif avatar_url is not None:
        applied_avatar = apply_unified_avatar(db, user, avatar_url)
        details["avatar_url"] = applied_avatar or ""

    gender_changed = False
    if gender_set:
        try:
            parsed = parse_gender(gender)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        user.gender = parsed
        details["gender"] = parsed or ""
        gender_changed = True
    if gender_visibility_set:
        try:
            vis = parse_gender_visibility(gender_visibility)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        user.gender_visibility = vis or DEFAULT_GENDER_VISIBILITY
        details["gender_visibility"] = user.gender_visibility
        gender_changed = True

    write_audit_log(
        db,
        action="users.profile_update",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        details=details or {"display_name": user.full_name},
    )
    db.commit()
    db.refresh(user)

    if gender_changed:
        from app.core.cache_invalidation import (
            invalidate_fan_public_caches,
            invalidate_host_public_caches,
        )
        from app.hosts.models import Host
        from app.passport.models import FanPassport
        from sqlalchemy import select

        passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user.id))
        if passport and passport.username:
            invalidate_fan_public_caches(username=passport.username)
        host = db.scalar(select(Host).where(Host.user_id == user.id))
        if host is not None:
            invalidate_host_public_caches(host_id=host.id, username=host.slug)

    return user


def deactivate_user(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    reason: str | None = None,
) -> User:
    return change_account_status(
        db,
        admin=admin,
        user_id=user_id,
        new_status=ACCOUNT_STATUS_SUSPENDED,
        reason=reason or "",
    )


def restore_user(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    reason: str | None = None,
) -> User:
    return change_account_status(
        db,
        admin=admin,
        user_id=user_id,
        new_status=ACCOUNT_STATUS_ACTIVE,
        reason=reason or "",
    )


def delete_user_blocked() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Hard delete blocked for users; suspend then POST .../force-delete",
    )


def force_delete_user(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    """Soft end-of-life: set ``account_status=deleted``.

    Requires the target to already be ``suspended``. Row and commerce history
    are retained; hard ``DELETE`` remains blocked.
    """
    require_admin_users_perm(admin, "admin.users.force_delete")
    target = get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(
            status_code=400, detail="Cannot force-delete your own account"
        )

    cleaned_reason = (reason or "").strip()
    if len(cleaned_reason) < 3:
        raise HTTPException(
            status_code=400, detail="A reason is required for force delete"
        )

    current = effective_account_status(target)
    if current == ACCOUNT_STATUS_DELETED:
        raise HTTPException(status_code=400, detail="Account is already deleted")
    if current != ACCOUNT_STATUS_SUSPENDED:
        raise HTTPException(
            status_code=400,
            detail="User must be suspended before force delete",
        )

    before_restrictions = stored_restrictions(target)
    before_json = {
        "account_status": current,
        "restrictions": before_restrictions,
        "is_active": bool(target.is_active),
    }

    now = datetime.now(UTC)
    target.is_active = False
    if target.deactivated_at is None:
        target.deactivated_at = now
    target.under_review_at = None
    target.under_review_reason = None
    target.account_status = ACCOUNT_STATUS_DELETED

    write_admin_user_audit(
        db,
        action=ADMIN_USER_STATUS_CHANGED,
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason=cleaned_reason,
        before_json=before_json,
        after_json={
            "account_status": ACCOUNT_STATUS_DELETED,
            "restrictions": before_restrictions,
            "is_active": False,
        },
        extra={
            "previous_status": current,
            "new_status": ACCOUNT_STATUS_DELETED,
            "force_delete": True,
            "restriction_keys": before_restrictions,
            "internal_note_present": False,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    from app.users.admin_actions_service import revoke_all_sessions

    revoke_all_sessions(
        db,
        admin=admin,
        user_id=user_id,
        reason=cleaned_reason,
        commit=False,
        skip_permission_check=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    from app.appeals.models import (
        SUSPENSION_STATUS_ACTIVE,
        SUSPENSION_STATUS_LIFTED,
    )
    from app.appeals.service import get_active_suspension

    prior = get_active_suspension(db, target.id)
    if prior is not None and prior.status == SUSPENSION_STATUS_ACTIVE:
        prior.status = SUSPENSION_STATUS_LIFTED
        prior.lifted_at = now
        prior.lifted_by_admin_id = admin.id

    db.commit()
    db.refresh(target)
    return target


def set_ambassadors_blocked(
    db: Session, *, admin: User, user_id: uuid.UUID, blocked: bool
) -> User:
    """Block/unblock a user from all Pàdéyá Ambassadors programs (not host team)."""
    require_admin_users_perm(
        admin, "admin.users.restrict", "admin.users.add_restriction"
    )
    target = get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    from app.users.restrictions_service import (
        apply_restrictions,
        list_restriction_rows,
        revoke_restriction,
    )

    code = "cannot_join_ambassador_campaigns"
    if blocked:
        apply_restrictions(
            db,
            admin=admin,
            user_id=user_id,
            restriction_keys=[code],
            reason="Ambassadors program blocked by admin",
        )
    else:
        rows = list_restriction_rows(db, user_id, include_inactive=False)
        for row in rows:
            if row.restriction_key in {
                "cannot_join_ambassador_campaigns",
                "cannot_promote_events",
                "cannot_receive_ambassador_rewards",
                "cannot_request_ambassador_payouts",
            }:
                try:
                    revoke_restriction(
                        db,
                        admin=admin,
                        user_id=user_id,
                        restriction_id=row.id,
                        reason="Ambassadors program unblocked by admin",
                    )
                except HTTPException:
                    continue

    write_audit_log(
        db,
        action="users.ambassadors_block" if blocked else "users.ambassadors_unblock",
        actor_user_id=admin.id,
        resource_type="user",
        resource_id=str(user_id),
        details={"ambassadors_blocked": blocked},
    )
    db.commit()
    refreshed = get_user_by_id(db, user_id)
    return refreshed  # type: ignore[return-value]
