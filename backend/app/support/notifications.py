"""Support ticket notifications (in-app + push when enabled)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications.service import notify_user
from app.support.models import SupportCase
from app.users.models import User
from app.users.service import user_has_permission, user_has_role


def _staff_user_ids(db: Session) -> list[UUID]:
    rows = db.scalars(select(User).where(User.is_active.is_(True))).all()
    out: list[UUID] = []
    for u in rows:
        if (
            user_has_permission(u, "admin.support.view")
            or user_has_permission(u, "admin.support.view_all")
            or user_has_permission(u, "support.reply")
            or user_has_permission(u, "admin.full_access")
            or user_has_role(u, "support_agent", "super_admin")
        ):
            out.append(u.id)
    return out


def notify_ticket_created(db: Session, case: SupportCase) -> None:
    if case.requester_user_id:
        notify_user(
            db,
            user_id=case.requester_user_id,
            kind="support.ticket_updated",
            title="Support ticket created",
            body=f"We received {case.case_number}: {case.subject[:80]}",
            link_path=f"/dashboard/support/{case.id}",
            dedupe_key=f"support.created:{case.id}",
            send_push=True,
        )
    staff_link = f"/admin/support/{case.id}"
    title = "New support ticket"
    if case.priority == "urgent":
        title = "Urgent support ticket"
    for uid in _staff_user_ids(db):
        if case.requester_user_id and uid == case.requester_user_id:
            continue
        notify_user(
            db,
            user_id=uid,
            kind="admin_support_ticket",
            title=title,
            body=f"{case.case_number} · {case.category} · {case.subject[:60]}",
            link_path=staff_link,
            dedupe_key=f"support.staff.new:{case.id}:{uid}",
            send_push=True,
        )
    from app.email.admin_triggers import admin_notify_support_ticket_created

    admin_notify_support_ticket_created(
        db,
        case_id=case.id,
        ticket_number=case.case_number,
        subject=case.subject,
        requester_name=case.requester_name or "Requester",
        category=case.category,
        priority=case.priority,
    )


def notify_staff_reply(db: Session, case: SupportCase) -> None:
    if not case.requester_user_id:
        return
    notify_user(
        db,
        user_id=case.requester_user_id,
        kind="support.ticket_updated",
        title="Support replied",
        body=f"New reply on {case.case_number}",
        link_path=f"/dashboard/support/{case.id}",
        dedupe_key=None,
        send_push=True,
    )


def notify_user_reply_to_assignee(db: Session, case: SupportCase) -> None:
    if not case.assignee_user_id:
        return
    notify_user(
        db,
        user_id=case.assignee_user_id,
        kind="admin_support_ticket",
        title="User replied on assigned ticket",
        body=f"{case.case_number}: {case.subject[:80]}",
        link_path=f"/admin/support/{case.id}",
        dedupe_key=None,
        send_push=True,
    )


def notify_status_change(db: Session, case: SupportCase, *, status: str) -> None:
    if not case.requester_user_id:
        return
    labels = {
        "resolved": "resolved",
        "closed": "closed",
        "waiting_on_user": "waiting on your reply",
        "escalated": "escalated",
        "pending": "updated",
        "open": "reopened",
    }
    label = labels.get(status, "updated")
    notify_user(
        db,
        user_id=case.requester_user_id,
        kind="support.ticket_updated",
        title=f"Ticket {label}",
        body=f"{case.case_number} is now {status.replace('_', ' ')}",
        link_path=f"/dashboard/support/{case.id}",
        dedupe_key=f"support.status:{case.id}:{status}:{case.updated_at}",
        send_push=True,
    )
