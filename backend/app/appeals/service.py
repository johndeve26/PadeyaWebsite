"""Appeals domain — create suspension records, user appeals, admin review."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appeals.models import (
    APPEAL_STATUS_APPROVED,
    APPEAL_STATUS_PENDING,
    APPEAL_STATUS_REJECTED,
    SUSPENSION_REASON_CATEGORIES,
    SUSPENSION_STATUS_ACTIVE,
    SUSPENSION_STATUS_LIFTED,
    AccountAppeal,
    AccountSuspension,
)
from app.appeals.suspension_notify import (
    AUDIT_ACCOUNT_UNSUSPENDED,
    AUDIT_APPEAL_APPROVED,
    AUDIT_APPEAL_REJECTED,
    AUDIT_APPEAL_SUBMITTED,
    notify_account_suspended,
    notify_appeal_decision,
)
from app.users.account_status_constants import ACCOUNT_STATUS_ACTIVE, ACCOUNT_STATUS_SUSPENDED
from app.users.account_status_service import change_account_status, effective_account_status
from app.users.admin_user_audit import write_admin_user_audit
from app.users.admin_users_permissions import require_admin_users_perm
from app.users.models import User
from app.users.service import get_user_by_id


def normalize_reason_category(raw: str | None) -> str:
    code = (raw or "other").strip().lower().replace(" ", "_")
    if code not in SUSPENSION_REASON_CATEGORIES:
        return "other"
    return code


def get_active_suspension(db: Session, user_id: uuid.UUID) -> AccountSuspension | None:
    return db.scalar(
        select(AccountSuspension)
        .where(
            AccountSuspension.user_id == user_id,
            AccountSuspension.status == SUSPENSION_STATUS_ACTIVE,
        )
        .order_by(AccountSuspension.created_at.desc())
        .limit(1)
    )


def serialize_suspension_public(row: AccountSuspension) -> dict:
    """Safe fields for the suspended user — never admin notes."""
    from app.appeals.models import SUSPENSION_CATEGORY_LABELS
    from app.appeals.suspension_notify import _duration_label

    return {
        "id": str(row.id),
        "status": row.status,
        "reason_category": row.reason_category,
        "reason_category_label": SUSPENSION_CATEGORY_LABELS.get(
            row.reason_category, "Account review"
        ),
        "starts_at": row.starts_at,
        "ends_at": row.ends_at,
        "duration_label": _duration_label(row.starts_at, row.ends_at),
    }


def serialize_appeal(row: AccountAppeal, *, include_admin: bool = False) -> dict:
    data = {
        "id": row.id,
        "user_id": row.user_id,
        "suspension_id": row.suspension_id,
        "message": row.message,
        "status": row.status,
        "admin_reply": row.admin_reply,
        "reviewed_at": row.reviewed_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if include_admin:
        data["reviewed_by_admin_id"] = row.reviewed_by_admin_id
    return data


def record_suspension(
    db: Session,
    *,
    admin: User,
    target: User,
    reason_category: str | None,
    ends_at: datetime | None,
    notify: bool = True,
) -> AccountSuspension:
    """Create active suspension row when account moves to suspended."""
    # Lift any prior active row (history preserved via status).
    prior = get_active_suspension(db, target.id)
    now = datetime.now(UTC)
    if prior is not None:
        prior.status = SUSPENSION_STATUS_LIFTED
        prior.lifted_at = now
        prior.lifted_by_admin_id = admin.id

    row = AccountSuspension(
        user_id=target.id,
        status=SUSPENSION_STATUS_ACTIVE,
        reason_category=normalize_reason_category(reason_category),
        starts_at=now,
        ends_at=ends_at,
        created_by_admin_id=admin.id,
    )
    db.add(row)
    db.flush()
    if notify:
        notify_account_suspended(db, user=target, suspension=row)
    return row


def submit_appeal(
    db: Session,
    *,
    user: User,
    message: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AccountAppeal:
    if effective_account_status(user) != ACCOUNT_STATUS_SUSPENDED:
        raise HTTPException(
            status_code=400,
            detail="Appeals are only available for suspended accounts",
        )
    suspension = get_active_suspension(db, user.id)
    if suspension is None:
        raise HTTPException(status_code=400, detail="No active suspension found")

    cleaned = (message or "").strip()
    if len(cleaned) < 10:
        raise HTTPException(
            status_code=400,
            detail="Appeal message must be at least 10 characters",
        )
    if len(cleaned) > 4000:
        raise HTTPException(status_code=400, detail="Appeal message is too long")

    existing = db.scalar(
        select(AccountAppeal).where(
            AccountAppeal.suspension_id == suspension.id,
            AccountAppeal.status == APPEAL_STATUS_PENDING,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending appeal for this suspension",
        )

    appeal = AccountAppeal(
        user_id=user.id,
        suspension_id=suspension.id,
        message=cleaned,
        status=APPEAL_STATUS_PENDING,
    )
    db.add(appeal)
    db.flush()

    write_admin_user_audit(
        db,
        action=AUDIT_APPEAL_SUBMITTED,
        admin_user_id=user.id,
        target_user_id=user.id,
        reason=None,
        extra={
            "appeal_id": str(appeal.id),
            "suspension_id": str(suspension.id),
            "message_length": len(cleaned),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(appeal)
    return appeal


def list_appeals_admin(
    db: Session,
    *,
    status: str | None = None,
    page: int = 1,
    limit: int = 40,
) -> dict:
    page = max(1, page)
    limit = min(max(1, limit), 100)
    filters = []
    if status:
        filters.append(AccountAppeal.status == status.strip().lower())
    from sqlalchemy import func

    count_stmt = select(func.count(AccountAppeal.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(db.scalar(count_stmt) or 0)
    stmt = select(AccountAppeal).order_by(AccountAppeal.created_at.desc())
    if filters:
        stmt = stmt.where(*filters)
    rows = list(
        db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
    )
    items = []
    for row in rows:
        user = get_user_by_id(db, row.user_id)
        suspension = db.get(AccountSuspension, row.suspension_id)
        item = serialize_appeal(row, include_admin=True)
        item["user_email"] = user.email if user else None
        item["user_full_name"] = user.full_name if user else None
        item["suspension"] = (
            serialize_suspension_public(suspension) if suspension else None
        )
        items.append(item)
    return {"items": items, "page": page, "limit": limit, "total": total}


def get_appeal_admin(db: Session, appeal_id: uuid.UUID) -> dict:
    row = db.get(AccountAppeal, appeal_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    user = get_user_by_id(db, row.user_id)
    suspension = db.get(AccountSuspension, row.suspension_id)
    item = serialize_appeal(row, include_admin=True)
    item["user_email"] = user.email if user else None
    item["user_full_name"] = user.full_name if user else None
    item["suspension"] = (
        serialize_suspension_public(suspension) if suspension else None
    )
    return item


def approve_appeal(
    db: Session,
    *,
    admin: User,
    appeal_id: uuid.UUID,
    admin_reply: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    require_admin_users_perm(admin, "admin.users.suspend", "admin.appeals.review")
    appeal = db.get(AccountAppeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.status != APPEAL_STATUS_PENDING:
        raise HTTPException(status_code=400, detail="Appeal is not pending")

    now = datetime.now(UTC)
    appeal.status = APPEAL_STATUS_APPROVED
    appeal.admin_reply = (admin_reply or "").strip()[:1000] or None
    appeal.reviewed_by_admin_id = admin.id
    appeal.reviewed_at = now

    suspension = db.get(AccountSuspension, appeal.suspension_id)
    if suspension and suspension.status == SUSPENSION_STATUS_ACTIVE:
        suspension.status = SUSPENSION_STATUS_LIFTED
        suspension.lifted_at = now
        suspension.lifted_by_admin_id = admin.id

    target = get_user_by_id(db, appeal.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Unsuspend via status service (audited).
    if effective_account_status(target) == ACCOUNT_STATUS_SUSPENDED:
        change_account_status(
            db,
            admin=admin,
            user_id=target.id,
            new_status=ACCOUNT_STATUS_ACTIVE,
            reason="Appeal approved",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        target = get_user_by_id(db, appeal.user_id) or target

    write_admin_user_audit(
        db,
        action=AUDIT_APPEAL_APPROVED,
        admin_user_id=admin.id,
        target_user_id=appeal.user_id,
        reason="Appeal approved",
        extra={
            "appeal_id": str(appeal.id),
            "suspension_id": str(appeal.suspension_id),
            "admin_reply_present": bool(appeal.admin_reply),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    write_admin_user_audit(
        db,
        action=AUDIT_ACCOUNT_UNSUSPENDED,
        admin_user_id=admin.id,
        target_user_id=appeal.user_id,
        reason="Appeal approved",
        extra={"appeal_id": str(appeal.id), "via": "appeal_approval"},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    notify_appeal_decision(
        db,
        user=target,
        approved=True,
        admin_reply=appeal.admin_reply,
        appeal_id=appeal.id,
    )
    db.commit()
    db.refresh(appeal)
    return get_appeal_admin(db, appeal.id)


def reject_appeal(
    db: Session,
    *,
    admin: User,
    appeal_id: uuid.UUID,
    admin_reply: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    require_admin_users_perm(admin, "admin.users.suspend", "admin.appeals.review")
    appeal = db.get(AccountAppeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.status != APPEAL_STATUS_PENDING:
        raise HTTPException(status_code=400, detail="Appeal is not pending")

    now = datetime.now(UTC)
    appeal.status = APPEAL_STATUS_REJECTED
    appeal.admin_reply = (admin_reply or "").strip()[:1000] or None
    appeal.reviewed_by_admin_id = admin.id
    appeal.reviewed_at = now

    target = get_user_by_id(db, appeal.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    write_admin_user_audit(
        db,
        action=AUDIT_APPEAL_REJECTED,
        admin_user_id=admin.id,
        target_user_id=appeal.user_id,
        reason="Appeal rejected",
        extra={
            "appeal_id": str(appeal.id),
            "suspension_id": str(appeal.suspension_id),
            "admin_reply_present": bool(appeal.admin_reply),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    notify_appeal_decision(
        db,
        user=target,
        approved=False,
        admin_reply=appeal.admin_reply,
        appeal_id=appeal.id,
    )
    db.commit()
    db.refresh(appeal)
    return get_appeal_admin(db, appeal.id)
