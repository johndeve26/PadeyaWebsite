"""Suspension + appeal notifications (in-app, email, push) — public-safe copy only."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.appeals.models import (
    SUSPENSION_CATEGORY_LABELS,
    AccountSuspension,
)
from app.users.models import User

logger = logging.getLogger("padeya.suspension_notify")

AUDIT_SUSPENSION_NOTIFIED = "admin_user_suspension_notified"
AUDIT_APPEAL_SUBMITTED = "account_appeal_submitted"
AUDIT_APPEAL_APPROVED = "account_appeal_approved"
AUDIT_APPEAL_REJECTED = "account_appeal_rejected"
AUDIT_ACCOUNT_UNSUSPENDED = "admin_user_unsuspended"


def _category_label(category: str) -> str:
    return SUSPENSION_CATEGORY_LABELS.get(category, "Account review")


def _duration_label(starts_at: datetime, ends_at: datetime | None) -> str:
    if ends_at is None:
        return "Indefinite"
    try:
        delta = ends_at - starts_at
        days = max(1, int(delta.total_seconds() // 86400))
        if days == 1:
            return "24 hours"
        if days <= 7:
            return f"{days} days"
        return f"Until {ends_at.date().isoformat()}"
    except Exception:  # noqa: BLE001
        return "Limited"


def notify_account_suspended(
    db: Session,
    *,
    user: User,
    suspension: AccountSuspension,
) -> None:
    """In-app + email + push. Never includes internal admin notes or fraud logic."""
    category = _category_label(suspension.reason_category)
    duration = _duration_label(suspension.starts_at, suspension.ends_at)
    date_str = suspension.starts_at.date().isoformat()
    title = "Account suspended"
    body = (
        f"Your Pàdéyá account was suspended ({category}). "
        f"Duration: {duration}. Started: {date_str}."
    )[:240]
    dedupe = f"user:{user.id}:suspended:{suspension.id}"

    try:
        from app.notifications.service import notify_user

        notify_user(
            db,
            user_id=user.id,
            kind="account.suspended",
            title=title,
            body=body,
            link_path="/account/suspended",
            dedupe_key=dedupe,
            send_push=True,
            push_context={
                "action_url": "/account/suspended",
                "reason_category": suspension.reason_category,
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("in-app/push suspension notify failed for %s", user.id)

    if user.email:
        try:
            from app.email.service import enqueue_template

            enqueue_template(
                db,
                template="account_suspended",
                to=user.email,
                recipient_user_id=user.id,
                dedupe_key=f"{dedupe}:email",
                context={
                    "full_name": user.full_name,
                    "reason_category_label": category,
                    "duration_label": duration,
                    "starts_at": date_str,
                    "ends_at": (
                        suspension.ends_at.date().isoformat()
                        if suspension.ends_at
                        else None
                    ),
                    "action_url": "/account/suspended",
                },
                force=True,
            )
        except Exception:  # noqa: BLE001
            logger.exception("email suspension notify failed for %s", user.id)

    from app.users.admin_user_audit import write_admin_user_audit

    write_admin_user_audit(
        db,
        action=AUDIT_SUSPENSION_NOTIFIED,
        admin_user_id=suspension.created_by_admin_id,
        target_user_id=user.id,
        reason=None,
        extra={
            "suspension_id": str(suspension.id),
            "reason_category": suspension.reason_category,
            "starts_at": suspension.starts_at.isoformat(),
            "ends_at": suspension.ends_at.isoformat() if suspension.ends_at else None,
            "channels": ["in_app", "email", "push"],
            "internal_note_present": False,
        },
    )


def notify_appeal_decision(
    db: Session,
    *,
    user: User,
    approved: bool,
    admin_reply: str | None,
    appeal_id: UUID,
) -> None:
    title = "Appeal approved" if approved else "Appeal update"
    if approved:
        body = "Your suspension appeal was approved. Your account access has been restored."
    else:
        reply = (admin_reply or "").strip()
        body = (
            f"Your suspension appeal was not approved. {reply}".strip()
            if reply
            else "Your suspension appeal was not approved."
        )[:240]

    try:
        from app.notifications.service import notify_user

        notify_user(
            db,
            user_id=user.id,
            kind="account.appeal_decision",
            title=title,
            body=body,
            link_path="/account/suspended" if not approved else "/dashboard",
            dedupe_key=f"user:{user.id}:appeal:{appeal_id}:decision",
            send_push=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("appeal decision notify failed for %s", user.id)

    if user.email:
        try:
            from app.email.service import enqueue_template

            enqueue_template(
                db,
                template=(
                    "account_appeal_approved" if approved else "account_appeal_rejected"
                ),
                to=user.email,
                recipient_user_id=user.id,
                dedupe_key=f"user:{user.id}:appeal:{appeal_id}:email",
                context={
                    "full_name": user.full_name,
                    "admin_reply": (admin_reply or "").strip() or None,
                    "action_url": "/dashboard" if approved else "/account/suspended",
                },
                force=True,
            )
        except Exception:  # noqa: BLE001
            logger.exception("appeal decision email failed for %s", user.id)
