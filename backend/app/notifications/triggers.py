"""Product trigger helpers — keep email / in-app / push aligned.

Channel matrix (important events):

| Event | Email | Push | In-app |
|---|---|---|---|
| Ticket confirmed | yes (required) | if opted in | yes |
| Ticket checked in | optional | if opted in | yes |
| Merch pickup ready | yes (pref) | if opted in | yes |
| New message | preference + away | if opted in **and offline/inactive** | yes (toast when online) |
| Fan Connect request | preference | preference | yes |
| Sponsor inquiry | yes | host preference | yes |
| Admin report | admin (required) | admin preference | admin inbox |

Domain modules still call ``enqueue_template`` for email. This module covers
shared fan-out that must stay next to those email sends.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications.service import notify_user
from app.users.models import Role


def notify_ticket_qr_ready(
    db: Session,
    *,
    user_id: UUID | None,
    event_title: str,
    order_id: UUID,
) -> None:
    """In-app + preference-gated push when ticket QR is available after purchase."""
    if user_id is None:
        return
    notify_user(
        db,
        user_id=user_id,
        kind="ticket.qr_ready",
        title="QR ready",
        body=f"Your ticket QR for {event_title} is ready on Pàdéyá.",
        link_path="/dashboard/tickets",
        dedupe_key=f"order:{order_id}:ticket.qr_ready",
        send_push=True,
    )


def notify_buyer_ticket_refund(
    db: Session,
    *,
    buyer_user_id: UUID | None,
    event_title: str,
    refund_status: str,
    dedupe_key: str,
) -> None:
    """Mirror ticket_refund_update email with in-app + push."""
    if buyer_user_id is None:
        return
    status = (refund_status or "updated").strip().lower()
    notify_user(
        db,
        user_id=buyer_user_id,
        kind="ticket.refund_update",
        title="Refund update",
        body=f"Ticket refund status for {event_title}: {status}."[:240],
        link_path="/dashboard/refunds",
        dedupe_key=dedupe_key,
        send_push=True,
    )


# Back-compat alias
notify_ticket_refund_update = notify_buyer_ticket_refund


def notify_ticket_checked_in(
    db: Session,
    *,
    attendee_user_id: UUID | None,
    ticket_id: UUID,
    event_title: str,
    event_slug: str | None = None,
    host_display_name: str | None = None,
    ticket_label: str | None = None,
) -> None:
    """In-app + push when a fan ticket is checked in (account holder only)."""
    if attendee_user_id is None:
        return
    title_text = (event_title or "your event").strip() or "your event"
    link_path = "/dashboard/tickets"
    if event_slug:
        link_path = f"/events/{event_slug.strip('/')}"
    body = f"You've been checked in for {title_text}."
    ctx: dict = {
        "event_title": title_text,
        "action_url": link_path,
    }
    if host_display_name:
        ctx["host_display_name"] = host_display_name.strip()[:120]
    if ticket_label:
        ctx["name"] = ticket_label.strip()[:80]

    notify_user(
        db,
        user_id=attendee_user_id,
        kind="ticket.checked_in",
        title="You're checked in",
        body=body[:240],
        link_path=link_path,
        dedupe_key=f"ticket:{ticket_id}:checked_in",
        send_push=True,
        push_context=ctx,
    )


def notify_admins_report(
    db: Session,
    *,
    report_kind: str,
    report_id: UUID,
    title: str,
    body: str,
    link_path: str,
    limit: int = 5,
) -> int:
    """Email + in-app + push for configured admin moderation recipients."""
    from app.email.admin_dispatch import notify_admins_platform_email

    template_key = "admin_new_report"
    kind = (report_kind or "").lower()
    if "safety" in kind:
        template_key = "admin_safety_report"
    elif "abuse" in kind:
        template_key = "admin_abuse_report"
    elif "message" in kind:
        template_key = "admin_message_report"

    ctx = {
        "report_kind": report_kind,
        "report_id_safe": str(report_id),
        "admin_report_url": link_path,
        "preview_text": body[:240],
    }
    emailed = notify_admins_platform_email(
        db,
        template_key=template_key,
        context=ctx,
        dedupe_key=f"{report_kind}_report:{report_id}",
        entity_id=report_id,
    )

    admin_role = db.scalar(select(Role).where(Role.name == "super_admin"))
    if admin_role is None:
        return emailed

    notified = 0
    for admin in list(admin_role.users)[:limit]:
        notify_user(
            db,
            user_id=admin.id,
            kind="admin.report",
            title=title[:160],
            body=body[:240],
            link_path=link_path,
            dedupe_key=f"{report_kind}_report:{report_id}:admin.notif:{admin.id}",
            send_push=True,
        )
        notified += 1
    return max(emailed, notified)


# Back-compat alias
notify_admins_new_report = notify_admins_report
