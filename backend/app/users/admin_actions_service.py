"""Safe admin user actions — notes, flags, sessions, review, password reset."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import PasswordResetToken, RefreshToken
from app.core.audit import write_audit_log
from app.core.security import (
    hash_password,
    hash_token,
)
from app.users.admin_user_audit import (
    ADMIN_USER_FLAG_CREATED,
    ADMIN_USER_FLAG_UPDATED,
    ADMIN_USER_FORCE_LOGOUT,
    ADMIN_USER_FORCE_PASSWORD_RESET,
    ADMIN_USER_NOTE_CREATED,
    write_admin_user_audit,
)
from app.users.admin_users_permissions import require_admin_users_perm
from app.users.flag_constants import (
    FLAG_SEVERITIES,
    FLAG_SEVERITY_MEDIUM,
    FLAG_STATUS_ACTIVE,
    FLAG_STATUS_DISMISSED,
    FLAG_STATUS_RESOLVED,
    FLAG_TYPE_SET,
)
from app.users.models import User, UserAdminFlag, UserAdminNote
from app.users.note_constants import NOTE_SECRET_HINTS, NOTE_TYPE_SET
from app.users.service import get_user_by_id


def _assert_note_body_safe(body: str) -> None:
    """Reject notes that appear to contain passwords, tokens, or payment/QR secrets."""
    lowered = body.lower()
    for hint in NOTE_SECRET_HINTS:
        if hint in lowered:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Notes must not contain passwords, tokens, "
                    "raw payment payloads, or QR secrets"
                ),
            )
    # JWT-shaped blobs
    if "eyj" in lowered and lowered.count(".") >= 2:
        raise HTTPException(
            status_code=400,
            detail="Notes must not contain access or refresh tokens",
        )


def _require_target(db: Session, user_id: uuid.UUID) -> User:
    target = get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return target


def serialize_note(note: UserAdminNote) -> dict:
    return {
        "id": note.id,
        "user_id": note.user_id,
        "note_type": note.note_type,
        "body": note.body,
        "created_by_admin_id": note.created_by_admin_id,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
    }


def serialize_flag(flag: UserAdminFlag) -> dict:
    from app.users.admin_response_safety import scrub_admin_user_payload

    return scrub_admin_user_payload(
        {
            "id": flag.id,
            "user_id": flag.user_id,
            "flag_type": flag.flag_type,
            "severity": flag.severity,
            "status": flag.status,
            "reason": flag.reason,
            "internal_note": flag.internal_note,
            "created_by_admin_id": flag.created_by_admin_id,
            "created_at": flag.created_at,
            "resolved_by_admin_id": flag.resolved_by_admin_id,
            "resolved_at": flag.resolved_at,
            "resolution_note": flag.resolution_note,
            "updated_at": flag.updated_at,
        }
    )


def list_notes(db: Session, *, admin: User, user_id: uuid.UUID) -> list[dict]:
    require_admin_users_perm(admin, "admin.users.view")
    _require_target(db, user_id)
    rows = list(
        db.scalars(
            select(UserAdminNote)
            .where(UserAdminNote.user_id == user_id)
            .order_by(UserAdminNote.created_at.desc())
            .limit(100)
        ).all()
    )
    return [serialize_note(n) for n in rows]


def add_note(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    body: str,
    note_type: str = "general",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Append an admin-only internal note. Never exposed on user-facing APIs."""
    require_admin_users_perm(admin, "admin.users.add_note")
    target = _require_target(db, user_id)
    cleaned_type = (note_type or "general").strip().lower().replace(" ", "_")
    if cleaned_type not in NOTE_TYPE_SET:
        raise HTTPException(status_code=400, detail="Invalid note type")
    cleaned = (body or "").strip()
    if len(cleaned) < 3:
        raise HTTPException(status_code=400, detail="Note body is required")
    _assert_note_body_safe(cleaned)
    note = UserAdminNote(
        user_id=target.id,
        note_type=cleaned_type,
        body=cleaned[:4000],
        created_by_admin_id=admin.id,
        updated_at=None,
    )
    db.add(note)
    db.flush()
    write_admin_user_audit(
        db,
        action=ADMIN_USER_NOTE_CREATED,
        admin_user_id=admin.id,
        target_user_id=target.id,
        after_json={
            "note_id": str(note.id),
            "note_type": cleaned_type,
            "body_length": len(cleaned),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(note)
    return serialize_note(note)


def list_flags(db: Session, *, admin: User, user_id: uuid.UUID) -> list[dict]:
    require_admin_users_perm(admin, "admin.users.view")
    _require_target(db, user_id)
    rows = list(
        db.scalars(
            select(UserAdminFlag)
            .where(UserAdminFlag.user_id == user_id)
            .order_by(UserAdminFlag.created_at.desc())
            .limit(100)
        ).all()
    )
    return [serialize_flag(f) for f in rows]


def add_flag(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    flag_type: str,
    reason: str,
    severity: str = FLAG_SEVERITY_MEDIUM,
    internal_note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    require_admin_users_perm(admin, "admin.users.flag")
    target = _require_target(db, user_id)
    cleaned_type = (flag_type or "").strip().lower().replace(" ", "_")
    if cleaned_type not in FLAG_TYPE_SET:
        raise HTTPException(status_code=400, detail="Invalid flag type")
    cleaned_severity = (severity or FLAG_SEVERITY_MEDIUM).strip().lower()
    if cleaned_severity not in FLAG_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail="Severity must be low, medium, high, or critical",
        )
    cleaned_reason = (reason or "").strip()
    if len(cleaned_reason) < 3:
        raise HTTPException(status_code=400, detail="Flag reason is required")
    note = (internal_note or "").strip() or None
    flag = UserAdminFlag(
        user_id=target.id,
        flag_type=cleaned_type,
        severity=cleaned_severity,
        status=FLAG_STATUS_ACTIVE,
        reason=cleaned_reason[:500],
        internal_note=note[:4000] if note else None,
        created_by_admin_id=admin.id,
    )
    db.add(flag)
    db.flush()
    write_admin_user_audit(
        db,
        action=ADMIN_USER_FLAG_CREATED,
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason=cleaned_reason,
        after_json={
            "flag_id": str(flag.id),
            "flag_type": cleaned_type,
            "severity": cleaned_severity,
            "status": FLAG_STATUS_ACTIVE,
            "has_internal_note": bool(note),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(flag)
    return serialize_flag(flag)


def _close_flag(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    flag_id: uuid.UUID,
    status_value: str,
    resolution_note: str | None,
    action_reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    require_admin_users_perm(admin, "admin.users.flag")
    _require_target(db, user_id)
    flag = db.scalar(
        select(UserAdminFlag).where(
            UserAdminFlag.id == flag_id,
            UserAdminFlag.user_id == user_id,
        )
    )
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    if flag.status != FLAG_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="Flag is already closed")
    note = (resolution_note or "").strip()
    cleaned_action_reason = (action_reason or "").strip()
    before = {
        "flag_id": str(flag.id),
        "flag_type": flag.flag_type,
        "severity": flag.severity,
        "status": flag.status,
    }
    flag.status = status_value
    flag.resolved_by_admin_id = admin.id
    flag.resolved_at = datetime.now(UTC)
    flag.resolution_note = note[:500] if note else None
    write_admin_user_audit(
        db,
        action=ADMIN_USER_FLAG_UPDATED,
        admin_user_id=admin.id,
        target_user_id=user_id,
        reason=cleaned_action_reason or None,
        before_json=before,
        after_json={
            "flag_id": str(flag.id),
            "flag_type": flag.flag_type,
            "severity": flag.severity,
            "status": status_value,
            "has_resolution_note": bool(note),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(flag)
    return serialize_flag(flag)


def resolve_flag(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    flag_id: uuid.UUID,
    resolution_note: str | None = None,
    action_reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    return _close_flag(
        db,
        admin=admin,
        user_id=user_id,
        flag_id=flag_id,
        status_value=FLAG_STATUS_RESOLVED,
        resolution_note=resolution_note,
        action_reason=action_reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def dismiss_flag(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    flag_id: uuid.UUID,
    resolution_note: str | None = None,
    action_reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    return _close_flag(
        db,
        admin=admin,
        user_id=user_id,
        flag_id=flag_id,
        status_value=FLAG_STATUS_DISMISSED,
        resolution_note=resolution_note,
        action_reason=action_reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def patch_flag(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    flag_id: uuid.UUID,
    status: str,
    reason: str,
    resolution_note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Soft-close a flag via PATCH — status must be resolved or dismissed."""
    cleaned_status = (status or "").strip().lower()
    cleaned_reason = (reason or "").strip()
    if len(cleaned_reason) < 3:
        raise HTTPException(status_code=400, detail="A reason is required")
    if cleaned_status == FLAG_STATUS_RESOLVED:
        return resolve_flag(
            db,
            admin=admin,
            user_id=user_id,
            flag_id=flag_id,
            resolution_note=resolution_note,
            action_reason=cleaned_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    if cleaned_status == FLAG_STATUS_DISMISSED:
        return dismiss_flag(
            db,
            admin=admin,
            user_id=user_id,
            flag_id=flag_id,
            resolution_note=resolution_note,
            action_reason=cleaned_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    raise HTTPException(
        status_code=400,
        detail="Flag status must be resolved or dismissed",
    )


def revoke_all_sessions(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    reason: str | None = None,
    commit: bool = True,
    require_reason: bool = False,
    skip_permission_check: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Force-logout: revoke all refresh tokens. Never returns token values."""
    if not skip_permission_check:
        require_admin_users_perm(admin, "admin.users.force_logout")
    target = _require_target(db, user_id)
    cleaned = (reason or "").strip()
    if require_reason and len(cleaned) < 3:
        raise HTTPException(status_code=400, detail="A reason is required")
    now = datetime.now(UTC)
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == target.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    revoked = int(result.rowcount or 0)
    write_admin_user_audit(
        db,
        action=ADMIN_USER_FORCE_LOGOUT,
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason=cleaned or None,
        after_json={"revoked_count": revoked},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if commit:
        db.commit()
    return {"user_id": target.id, "revoked_count": revoked}


def mark_under_review(
    db: Session, *, admin: User, user_id: uuid.UUID, reason: str
) -> User:
    from app.users.account_status_constants import ACCOUNT_STATUS_UNDER_REVIEW
    from app.users.account_status_service import change_account_status

    return change_account_status(
        db,
        admin=admin,
        user_id=user_id,
        new_status=ACCOUNT_STATUS_UNDER_REVIEW,
        reason=reason,
    )


def clear_under_review(
    db: Session, *, admin: User, user_id: uuid.UUID, reason: str | None = None
) -> User:
    from app.users.account_status_constants import ACCOUNT_STATUS_ACTIVE
    from app.users.account_status_service import change_account_status

    return change_account_status(
        db,
        admin=admin,
        user_id=user_id,
        new_status=ACCOUNT_STATUS_ACTIVE,
        reason=reason or "",
    )


def force_password_reset_email(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    reason: str | None = None,
    require_reason: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Create a reset token and email the user. Never returns the raw token."""
    from app.auth.password_reset import queue_password_reset_email

    require_admin_users_perm(admin, "admin.users.force_password_reset")
    target = _require_target(db, user_id)
    cleaned = (reason or "").strip()
    if require_reason and len(cleaned) < 3:
        raise HTTPException(status_code=400, detail="A reason is required")
    queue_password_reset_email(db, target)
    write_admin_user_audit(
        db,
        action=ADMIN_USER_FORCE_PASSWORD_RESET,
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason=cleaned or None,
        after_json={"email_sent": True},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return {"user_id": str(target.id), "email_sent": True}


def confirm_password_reset(
    db: Session, *, email: str, code: str, new_password: str
) -> None:
    """Public confirm — consumes code, sets password, revokes sessions."""
    from app.auth.password_reset import find_valid_password_reset_token

    password = (new_password or "").strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user, row = find_valid_password_reset_token(db, email=email, code=code)
    now = datetime.now(UTC)
    user.password_hash = hash_password(password)
    row.used_at = now
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    write_audit_log(
        db,
        action="auth.password_reset_confirm",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()
