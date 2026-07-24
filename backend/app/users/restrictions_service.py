"""Admin selective user restrictions — table-backed, soft lifecycle.

Primary path: add/revoke individual keys → account_status=restricted.
Full suspension is an admin preset only (status=suspended + major keys).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.users.account_status_constants import (
    ACCOUNT_RESTRICTION_GROUP_LABELS,
    ACCOUNT_RESTRICTION_GROUPS,
    ACCOUNT_RESTRICTION_LABELS,
    ACCOUNT_RESTRICTION_SET,
    ACCOUNT_STATUS_ACTIVE,
    ACCOUNT_STATUS_BANNED,
    ACCOUNT_STATUS_DELETED,
    ACCOUNT_STATUS_RESTRICTED,
    ACCOUNT_STATUS_SUSPENDED,
    ACCOUNT_STATUS_UNDER_REVIEW,
    ADMIN_RESTRICTION_PRESETS,
    AMBASSADOR_RESTRICTION_KEYS,
    FULL_SUSPENSION_RESTRICTIONS,
    RESTRICTION_STATUS_ACTIVE,
    RESTRICTION_STATUS_EXPIRED,
    RESTRICTION_STATUS_REVOKED,
    canonicalize_restriction_key,
)
from app.users.admin_user_audit import (
    ADMIN_USER_RESTRICTION_ADDED,
    ADMIN_USER_RESTRICTION_EXTENDED,
    ADMIN_USER_RESTRICTION_PRESET_APPLIED,
    ADMIN_USER_RESTRICTION_REVOKED,
    ADMIN_USER_STATUS_CHANGED,
    write_admin_user_audit,
)
from app.users.admin_users_permissions import require_admin_users_perm
from app.users.models import User, UserRestriction
from app.users.restrictions import active_restriction_keys as active_keys_for_user
from app.users.service import (
    get_user_by_id,
    user_has_permission,
    user_has_role,
)

_KEY_TO_CATEGORY: dict[str, str] = {
    key: group
    for group, keys in ACCOUNT_RESTRICTION_GROUPS.items()
    for key in keys
}


def restriction_category(key: str) -> str | None:
    return _KEY_TO_CATEGORY.get(key)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _require_reason(reason: str | None) -> str:
    cleaned = (reason or "").strip()
    if len(cleaned) < 3:
        raise HTTPException(status_code=400, detail="A reason is required")
    return cleaned[:500]


def normalize_restriction_keys(raw: list[str] | None) -> list[str]:
    if not raw:
        raise HTTPException(status_code=400, detail="restriction_keys is required")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        code = canonicalize_restriction_key(item or "")
        if not code:
            continue
        if code not in ACCOUNT_RESTRICTION_SET:
            raise HTTPException(
                status_code=400, detail=f"Invalid restriction code: {code}"
            )
        if code not in seen:
            seen.add(code)
            cleaned.append(code)
    if not cleaned:
        raise HTTPException(status_code=400, detail="restriction_keys is required")
    return cleaned


def _is_row_effectively_active(
    row: UserRestriction, *, now: datetime | None = None
) -> bool:
    if row.status != RESTRICTION_STATUS_ACTIVE:
        return False
    when = now or _utcnow()
    ends = row.ends_at
    if ends is not None:
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=UTC)
        if ends <= when:
            return False
    return True


def mark_expired_rows(db: Session, user_id: uuid.UUID) -> int:
    now = _utcnow()
    rows = list(
        db.scalars(
            select(UserRestriction).where(
                UserRestriction.user_id == user_id,
                UserRestriction.status == RESTRICTION_STATUS_ACTIVE,
                UserRestriction.ends_at.is_not(None),
                UserRestriction.ends_at <= now,
            )
        ).all()
    )
    for row in rows:
        row.status = RESTRICTION_STATUS_EXPIRED
        row.updated_at = now
    return len(rows)


def list_restriction_rows(
    db: Session, user_id: uuid.UUID, *, include_inactive: bool = True
) -> list[UserRestriction]:
    mark_expired_rows(db, user_id)
    stmt = (
        select(UserRestriction)
        .where(UserRestriction.user_id == user_id)
        .order_by(UserRestriction.created_at.desc())
    )
    if not include_inactive:
        stmt = stmt.where(UserRestriction.status == RESTRICTION_STATUS_ACTIVE)
    return list(db.scalars(stmt).all())


def active_restriction_keys(db: Session, user: User) -> list[str]:
    mark_expired_rows(db, user.id)
    return active_keys_for_user(db, user.id)


def _admin_name_map(
    db: Session, admin_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not admin_ids:
        return {}
    rows = list(db.scalars(select(User).where(User.id.in_(admin_ids))).all())
    return {u.id: u.full_name for u in rows}


def serialize_restriction(
    row: UserRestriction,
    *,
    admin_names: dict[uuid.UUID, str] | None = None,
) -> dict:
    names = admin_names or {}
    key = row.restriction_key
    category = restriction_category(key)
    return {
        "id": row.id,
        "user_id": row.user_id,
        "restriction_key": key,
        "label": ACCOUNT_RESTRICTION_LABELS.get(key, key),
        "category": category,
        "category_label": (
            ACCOUNT_RESTRICTION_GROUP_LABELS.get(category) if category else None
        ),
        "status": row.status,
        "reason": row.reason,
        "internal_note": row.internal_note,
        "starts_at": row.starts_at,
        "ends_at": row.ends_at,
        "created_by_admin_id": row.created_by_admin_id,
        "created_by_admin_name": names.get(row.created_by_admin_id),
        "revoked_by_admin_id": row.revoked_by_admin_id,
        "revoked_by_admin_name": (
            names.get(row.revoked_by_admin_id) if row.revoked_by_admin_id else None
        ),
        "revoked_at": row.revoked_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def serialize_restriction_list(
    db: Session, rows: list[UserRestriction]
) -> list[dict]:
    admin_ids: set[uuid.UUID] = set()
    for row in rows:
        admin_ids.add(row.created_by_admin_id)
        if row.revoked_by_admin_id:
            admin_ids.add(row.revoked_by_admin_id)
    names = _admin_name_map(db, admin_ids)
    return [serialize_restriction(r, admin_names=names) for r in rows]


def sync_ambassadors_blocked(db: Session, user: User) -> None:
    keys = set(active_restriction_keys(db, user))
    user.ambassadors_blocked = bool(keys & AMBASSADOR_RESTRICTION_KEYS)


def sync_account_restrictions_mirror(db: Session, user: User) -> None:
    user.account_restrictions = active_restriction_keys(db, user) or None


def derive_and_apply_account_status(
    user: User,
    *,
    active_keys: list[str],
    force_suspended: bool = False,
) -> str:
    """Derive account_status after restriction mutations.

    Selective path → restricted (or preserve under_review).
    Full-suspension preset → suspended.
    Global suspended/banned/deleted win over restricted.
    """
    current = (getattr(user, "account_status", None) or "").strip().lower()
    if current in {ACCOUNT_STATUS_BANNED, ACCOUNT_STATUS_DELETED}:
        return current

    if force_suspended:
        now = _utcnow()
        user.is_active = False
        user.deactivated_at = now
        user.under_review_at = None
        user.under_review_reason = None
        user.account_status = ACCOUNT_STATUS_SUSPENDED
        return ACCOUNT_STATUS_SUSPENDED

    if current == ACCOUNT_STATUS_SUSPENDED:
        return ACCOUNT_STATUS_SUSPENDED

    under_review = (
        current == ACCOUNT_STATUS_UNDER_REVIEW
        or getattr(user, "under_review_at", None) is not None
    )
    if under_review:
        user.account_status = ACCOUNT_STATUS_UNDER_REVIEW
        user.is_active = True
        return ACCOUNT_STATUS_UNDER_REVIEW

    if active_keys:
        user.account_status = ACCOUNT_STATUS_RESTRICTED
        user.is_active = True
        user.deactivated_at = None
        return ACCOUNT_STATUS_RESTRICTED

    user.account_status = ACCOUNT_STATUS_ACTIVE
    user.is_active = True
    user.deactivated_at = None
    return ACCOUNT_STATUS_ACTIVE


def _assert_may_moderate_target(admin: User, target: User) -> None:
    if target.id == admin.id:
        raise HTTPException(
            status_code=400, detail="Cannot restrict your own account"
        )
    target_is_platform_admin = user_has_role(target, "super_admin") or (
        user_has_permission(target, "admin.full_access")
    )
    if not target_is_platform_admin:
        return
    settings = get_settings()
    if user_has_role(admin, "super_admin") and (
        settings.super_admin_may_restrict_platform_admins
    ):
        return
    raise HTTPException(
        status_code=403,
        detail="Cannot restrict platform administrators",
    )


def _get_target(db: Session, *, admin: User, user_id: uuid.UUID) -> User:
    target = get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _assert_may_moderate_target(admin, target)
    return target


def _get_restriction_row(
    db: Session, *, user_id: uuid.UUID, restriction_id: uuid.UUID
) -> UserRestriction:
    row = db.scalar(
        select(UserRestriction).where(
            UserRestriction.id == restriction_id,
            UserRestriction.user_id == user_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Restriction not found")
    return row


def _restriction_audit_extra(
    *,
    keys: list[str],
    starts_at: datetime | None,
    ends_at: datetime | None,
    internal_note_present: bool,
    previous_status: str,
    new_status: str,
    preset: str | None = None,
) -> dict:
    extra: dict = {
        "restriction_keys": keys,
        "internal_note_present": internal_note_present,
        "starts_at": starts_at.isoformat() if starts_at else None,
        "ends_at": ends_at.isoformat() if ends_at else None,
        "previous_status": previous_status,
        "new_status": new_status,
    }
    if preset:
        extra["preset"] = preset
    return extra


def list_user_restrictions(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
) -> dict:
    require_admin_users_perm(
        admin, "admin.users.view_restrictions", "admin.users.view", "admin.users.restrict"
    )
    target = get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    rows = list_restriction_rows(db, user_id, include_inactive=True)
    keys = active_restriction_keys(db, target)
    db.commit()
    return {
        "user_id": user_id,
        "account_status": getattr(target, "account_status", ACCOUNT_STATUS_ACTIVE),
        "active_keys": keys,
        "items": serialize_restriction_list(db, rows),
    }


def apply_restrictions(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    restriction_keys: list[str],
    reason: str,
    internal_note: str | None = None,
    ends_at: datetime | None = None,
    preset: str | None = None,
    force_full_suspension: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Primary path: create active rows → status=restricted.

    Full suspension is preset-only (not the default path).
    """
    require_admin_users_perm(
        admin, "admin.users.add_restriction", "admin.users.restrict"
    )

    preset_clean = (preset or "").strip().lower() or None
    is_full_suspension = force_full_suspension or preset_clean == "full_suspension"
    if is_full_suspension:
        require_admin_users_perm(admin, "admin.users.suspend")

    target = _get_target(db, admin=admin, user_id=user_id)
    cleaned_reason = _require_reason(reason)

    if preset_clean and preset_clean != "full_suspension":
        if preset_clean not in ADMIN_RESTRICTION_PRESETS:
            raise HTTPException(status_code=400, detail=f"Unknown preset: {preset_clean}")
        keys = list(ADMIN_RESTRICTION_PRESETS[preset_clean])
        for k in (
            normalize_restriction_keys(restriction_keys) if restriction_keys else []
        ):
            if k not in keys:
                keys.append(k)
    elif is_full_suspension and not restriction_keys:
        keys = list(FULL_SUSPENSION_RESTRICTIONS)
    else:
        keys = normalize_restriction_keys(restriction_keys)

    if is_full_suspension:
        for k in FULL_SUSPENSION_RESTRICTIONS:
            if k not in keys:
                keys.append(k)

    if ends_at is not None:
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=UTC)
        if ends_at <= _utcnow():
            raise HTTPException(status_code=400, detail="ends_at must be in the future")

    note = (internal_note or "").strip()[:4000] or None
    before_keys = active_restriction_keys(db, target)
    before_status = getattr(target, "account_status", ACCOUNT_STATUS_ACTIVE) or ACCOUNT_STATUS_ACTIVE

    now = _utcnow()
    existing_active = {
        r.restriction_key: r
        for r in list_restriction_rows(db, user_id, include_inactive=False)
        if _is_row_effectively_active(r, now=now)
    }

    created: list[UserRestriction] = []
    for key in keys:
        if key in existing_active:
            continue
        row = UserRestriction(
            user_id=target.id,
            restriction_key=key,
            status=RESTRICTION_STATUS_ACTIVE,
            reason=cleaned_reason,
            internal_note=note,
            starts_at=now,
            ends_at=ends_at,
            created_by_admin_id=admin.id,
        )
        db.add(row)
        created.append(row)

    db.flush()

    keys_now = active_restriction_keys(db, target)
    after_status = derive_and_apply_account_status(
        target, active_keys=keys_now, force_suspended=is_full_suspension
    )
    sync_ambassadors_blocked(db, target)
    sync_account_restrictions_mirror(db, target)

    if is_full_suspension and before_status != ACCOUNT_STATUS_SUSPENDED:
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
        from app.appeals.service import record_suspension

        record_suspension(
            db,
            admin=admin,
            target=target,
            reason_category="terms_of_service",
            ends_at=ends_at,
            notify=True,
        )

    created_keys = [r.restriction_key for r in created]
    extra = _restriction_audit_extra(
        keys=created_keys or keys,
        starts_at=now,
        ends_at=ends_at,
        internal_note_present=note is not None,
        previous_status=before_status,
        new_status=after_status,
        preset=preset_clean if (preset_clean or is_full_suspension) else None,
    )

    if is_full_suspension or (preset_clean and preset_clean != "full_suspension"):
        audit_action = ADMIN_USER_RESTRICTION_PRESET_APPLIED
        if is_full_suspension:
            extra["preset"] = "full_suspension"
    else:
        audit_action = ADMIN_USER_RESTRICTION_ADDED

    write_admin_user_audit(
        db,
        action=audit_action,
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason=cleaned_reason,
        before_json={"account_status": before_status, "active_keys": before_keys},
        after_json={
            "account_status": after_status,
            "active_keys": keys_now,
            "created_keys": created_keys,
        },
        extra=extra,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if before_status != after_status:
        write_admin_user_audit(
            db,
            action=ADMIN_USER_STATUS_CHANGED,
            admin_user_id=admin.id,
            target_user_id=target.id,
            reason=cleaned_reason,
            before_json={"account_status": before_status},
            after_json={"account_status": after_status},
            extra={
                "previous_status": before_status,
                "new_status": after_status,
                "restriction_keys": created_keys or keys,
                "internal_note_present": note is not None,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    db.commit()
    rows = list_restriction_rows(db, user_id, include_inactive=True)
    db.refresh(target)
    return {
        "user_id": user_id,
        "account_status": after_status,
        "active_keys": keys_now,
        "created_count": len(created),
        "items": serialize_restriction_list(db, rows),
    }


def extend_restriction(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    restriction_id: uuid.UUID,
    reason: str,
    ends_at: datetime | None = None,
    internal_note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    require_admin_users_perm(
        admin, "admin.users.add_restriction", "admin.users.restrict"
    )
    target = _get_target(db, admin=admin, user_id=user_id)
    cleaned_reason = _require_reason(reason)
    row = _get_restriction_row(db, user_id=user_id, restriction_id=restriction_id)

    if row.status == RESTRICTION_STATUS_REVOKED:
        raise HTTPException(
            status_code=400, detail="Cannot extend a revoked restriction"
        )

    now = _utcnow()
    if ends_at is not None:
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=UTC)
        if ends_at <= now:
            raise HTTPException(status_code=400, detail="ends_at must be in the future")

    before_ends = row.ends_at
    before_status = getattr(target, "account_status", ACCOUNT_STATUS_ACTIVE)

    if ends_at is not None:
        row.ends_at = ends_at
        if row.status == RESTRICTION_STATUS_EXPIRED:
            row.status = RESTRICTION_STATUS_ACTIVE
            row.revoked_at = None
            row.revoked_by_admin_id = None

    note_present = False
    if internal_note is not None:
        note = internal_note.strip()[:4000]
        row.internal_note = note or None
        note_present = bool(note)
    row.updated_at = now
    db.flush()

    keys_now = active_restriction_keys(db, target)
    after_status = derive_and_apply_account_status(target, active_keys=keys_now)
    sync_ambassadors_blocked(db, target)
    sync_account_restrictions_mirror(db, target)

    write_admin_user_audit(
        db,
        action=ADMIN_USER_RESTRICTION_EXTENDED,
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason=cleaned_reason,
        before_json={
            "ends_at": before_ends.isoformat() if before_ends else None,
            "status": row.status,
            "restriction_key": row.restriction_key,
        },
        after_json={
            "ends_at": row.ends_at.isoformat() if row.ends_at else None,
            "status": row.status,
            "restriction_key": row.restriction_key,
            "account_status": after_status,
        },
        extra=_restriction_audit_extra(
            keys=[row.restriction_key],
            starts_at=row.starts_at,
            ends_at=row.ends_at,
            internal_note_present=note_present or bool(row.internal_note),
            previous_status=before_status,
            new_status=after_status,
        ),
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.commit()
    db.refresh(row)
    names = _admin_name_map(
        db,
        {row.created_by_admin_id}
        | ({row.revoked_by_admin_id} if row.revoked_by_admin_id else set()),
    )
    return serialize_restriction(row, admin_names=names)


def revoke_restriction(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    restriction_id: uuid.UUID,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    require_admin_users_perm(
        admin, "admin.users.revoke_restriction", "admin.users.restrict"
    )
    target = _get_target(db, admin=admin, user_id=user_id)
    cleaned_reason = _require_reason(reason)
    row = _get_restriction_row(db, user_id=user_id, restriction_id=restriction_id)

    if row.status == RESTRICTION_STATUS_REVOKED:
        raise HTTPException(status_code=400, detail="Restriction already revoked")

    now = _utcnow()
    before_status = getattr(target, "account_status", ACCOUNT_STATUS_ACTIVE)
    row.status = RESTRICTION_STATUS_REVOKED
    row.revoked_at = now
    row.revoked_by_admin_id = admin.id
    row.updated_at = now
    db.flush()  # so active_keys SELECT sees revoked status

    keys_now = active_restriction_keys(db, target)
    after_status = derive_and_apply_account_status(target, active_keys=keys_now)
    sync_ambassadors_blocked(db, target)
    sync_account_restrictions_mirror(db, target)

    write_admin_user_audit(
        db,
        action=ADMIN_USER_RESTRICTION_REVOKED,
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason=cleaned_reason,
        before_json={
            "status": RESTRICTION_STATUS_ACTIVE,
            "restriction_key": row.restriction_key,
        },
        after_json={
            "status": RESTRICTION_STATUS_REVOKED,
            "restriction_key": row.restriction_key,
            "account_status": after_status,
            "active_keys": keys_now,
        },
        extra=_restriction_audit_extra(
            keys=[row.restriction_key],
            starts_at=row.starts_at,
            ends_at=row.ends_at,
            internal_note_present=bool(row.internal_note),
            previous_status=before_status,
            new_status=after_status,
        ),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if before_status != after_status:
        write_admin_user_audit(
            db,
            action=ADMIN_USER_STATUS_CHANGED,
            admin_user_id=admin.id,
            target_user_id=target.id,
            reason=cleaned_reason,
            before_json={"account_status": before_status},
            after_json={"account_status": after_status},
            extra={
                "previous_status": before_status,
                "new_status": after_status,
                "restriction_keys": [row.restriction_key],
                "internal_note_present": bool(row.internal_note),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    db.commit()
    db.refresh(row)
    names = _admin_name_map(db, {row.created_by_admin_id, admin.id})
    return serialize_restriction(row, admin_names=names)
