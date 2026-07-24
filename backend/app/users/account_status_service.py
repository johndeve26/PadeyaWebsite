"""Admin account status transitions — audited, reason-required.

Selective activity limits use ``user_restrictions`` (primary path → restricted).
Suspend/ban remain global secondary actions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.users.admin_user_audit import (
    ADMIN_USER_STATUS_CHANGED,
    write_admin_user_audit,
)
from app.users.admin_users_permissions import require_admin_users_perm
from app.users.account_status_constants import (
    ACCOUNT_STATUS_ACTIVE,
    ACCOUNT_STATUS_BANNED,
    ACCOUNT_STATUS_DELETED,
    ACCOUNT_STATUS_RESTRICTED,
    ACCOUNT_STATUS_SUSPENDED,
    ACCOUNT_STATUS_UNDER_REVIEW,
    ACCOUNT_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
)
from app.users.models import User
from app.users.service import get_user_by_id


def effective_account_status(user: User) -> str:
    """Prefer stored account_status; fall back for pre-migration rows."""
    stored = (getattr(user, "account_status", None) or "").strip().lower()
    if stored in ACCOUNT_STATUSES:
        return stored
    if not user.is_active or user.deactivated_at is not None:
        return ACCOUNT_STATUS_SUSPENDED
    if getattr(user, "under_review_at", None) is not None:
        return ACCOUNT_STATUS_UNDER_REVIEW
    return ACCOUNT_STATUS_ACTIVE


def stored_restrictions(user: User) -> list[str]:
    """Active restriction keys — prefers table; falls back to legacy JSON."""
    from sqlalchemy.orm import object_session

    session = object_session(user)
    if session is not None:
        from app.users.restrictions import active_restriction_keys

        return active_restriction_keys(session, user.id)
    raw = getattr(user, "account_restrictions", None)
    if not isinstance(raw, list):
        return []
    from app.users.account_status_constants import (
        ACCOUNT_RESTRICTION_SET,
        canonicalize_restriction_key,
    )

    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            code = canonicalize_restriction_key(item)
            if code in ACCOUNT_RESTRICTION_SET:
                out.append(code)
    return out


def _apply_side_effects(target: User, *, new_status: str, reason: str) -> None:
    now = datetime.now(UTC)
    if new_status == ACCOUNT_STATUS_ACTIVE:
        target.is_active = True
        target.deactivated_at = None
        target.under_review_at = None
        target.under_review_reason = None
    elif new_status == ACCOUNT_STATUS_UNDER_REVIEW:
        target.is_active = True
        target.deactivated_at = None
        target.under_review_at = now
        target.under_review_reason = reason[:500]
    elif new_status == ACCOUNT_STATUS_RESTRICTED:
        target.is_active = True
        target.deactivated_at = None
    elif new_status == ACCOUNT_STATUS_SUSPENDED:
        target.is_active = False
        target.deactivated_at = now
        target.under_review_at = None
        target.under_review_reason = None
    elif new_status == ACCOUNT_STATUS_BANNED:
        target.is_active = False
        target.deactivated_at = now
        target.under_review_at = None
        target.under_review_reason = None
    target.account_status = new_status


def _assert_status_change_permission(
    admin: User,
    *,
    current: str,
    new_status: str,
) -> None:
    needs_suspend = False
    needs_ban = False
    needs_restrict = False
    if new_status != current:
        if new_status == ACCOUNT_STATUS_SUSPENDED or current == ACCOUNT_STATUS_SUSPENDED:
            needs_suspend = True
        if new_status == ACCOUNT_STATUS_BANNED or current == ACCOUNT_STATUS_BANNED:
            needs_ban = True
        if new_status in {
            ACCOUNT_STATUS_UNDER_REVIEW,
            ACCOUNT_STATUS_RESTRICTED,
        } or (
            current in {ACCOUNT_STATUS_UNDER_REVIEW, ACCOUNT_STATUS_RESTRICTED}
            and new_status == ACCOUNT_STATUS_ACTIVE
        ):
            needs_restrict = True
    if needs_ban:
        require_admin_users_perm(admin, "admin.users.ban", "admin.users.suspend")
    if needs_suspend:
        require_admin_users_perm(admin, "admin.users.suspend")
    if needs_restrict:
        require_admin_users_perm(
            admin, "admin.users.restrict", "admin.users.add_restriction"
        )
    if not needs_suspend and not needs_restrict and not needs_ban:
        require_admin_users_perm(
            admin, "admin.users.restrict", "admin.users.suspend", "admin.users.ban"
        )


def change_account_status(
    db: Session,
    *,
    admin: User,
    user_id: UUID,
    new_status: str,
    reason: str,
    restrictions: list[str] | None = None,
    reason_category: str | None = None,
    ends_at: datetime | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    """Apply an allowed status transition. Reason is always required.

    Prefer selective restrictions API for activity limits; this endpoint is for
    global status (under_review / suspended / banned / active).
    ``deleted`` is soft EOL and not a casual writable toggle here.
    """
    target = get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own account status")

    cleaned_reason = (reason or "").strip()
    if len(cleaned_reason) < 3:
        raise HTTPException(status_code=400, detail="A reason is required for status changes")

    status_clean = (new_status or "").strip().lower()
    if status_clean not in ACCOUNT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid account status")
    if status_clean == ACCOUNT_STATUS_DELETED:
        raise HTTPException(
            status_code=400,
            detail="deleted is soft end-of-life and not set via this endpoint",
        )

    current = effective_account_status(target)
    if status_clean == current and restrictions is None:
        raise HTTPException(status_code=400, detail="Account already has this status")

    _assert_status_change_permission(
        admin, current=current, new_status=status_clean
    )

    before_restrictions = stored_restrictions(target)
    before_json = {
        "account_status": current,
        "restrictions": before_restrictions,
        "is_active": bool(target.is_active),
    }

    if status_clean != current:
        if (current, status_clean) not in ALLOWED_STATUS_TRANSITIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Transition from {current} to {status_clean} is not allowed. "
                    "Use selective restrictions for partial limits; suspend/ban for global blocks."
                ),
            )
        _apply_side_effects(target, new_status=status_clean, reason=cleaned_reason)

    after_status = effective_account_status(target)

    if status_clean != current:
        write_admin_user_audit(
            db,
            action=ADMIN_USER_STATUS_CHANGED,
            admin_user_id=admin.id,
            target_user_id=target.id,
            reason=cleaned_reason,
            before_json=before_json,
            after_json={
                "account_status": after_status,
                "restrictions": before_restrictions,
                "is_active": bool(target.is_active),
            },
            extra={
                "previous_status": current,
                "new_status": after_status,
                "restriction_keys": before_restrictions,
                "internal_note_present": False,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    if status_clean in {ACCOUNT_STATUS_SUSPENDED, ACCOUNT_STATUS_BANNED} and current not in {
        ACCOUNT_STATUS_SUSPENDED,
        ACCOUNT_STATUS_BANNED,
    }:
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

    if status_clean == ACCOUNT_STATUS_SUSPENDED and current != ACCOUNT_STATUS_SUSPENDED:
        from app.appeals.service import record_suspension

        record_suspension(
            db,
            admin=admin,
            target=target,
            reason_category=reason_category,
            ends_at=ends_at,
            notify=True,
        )
    elif (
        status_clean == ACCOUNT_STATUS_ACTIVE
        and current == ACCOUNT_STATUS_SUSPENDED
    ):
        from app.appeals.models import (
            SUSPENSION_STATUS_ACTIVE,
            SUSPENSION_STATUS_LIFTED,
        )
        from app.appeals.service import get_active_suspension

        prior = get_active_suspension(db, target.id)
        if prior is not None and prior.status == SUSPENSION_STATUS_ACTIVE:
            prior.status = SUSPENSION_STATUS_LIFTED
            prior.lifted_at = datetime.now(UTC)
            prior.lifted_by_admin_id = admin.id

    # Optional legacy restrictions list → selective restrictions API (primary path).
    if restrictions is not None:
        db.flush()
        from app.users.restrictions_service import apply_restrictions

        apply_restrictions(
            db,
            admin=admin,
            user_id=user_id,
            restriction_keys=restrictions,
            reason=cleaned_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.refresh(target)
        return target

    db.commit()
    db.refresh(target)
    return target
