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
| Admin new registration | admin (ops email) | admin preference | admin inbox |
| Admin ticket sale | admin (finance email) | admin preference | admin inbox |

Domain modules still call ``enqueue_template`` for email. This module covers
shared fan-out that must stay next to those email sends.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications.service import notify_user
from app.users.models import Role, User
from app.users.service import user_has_permission, user_has_role

logger = logging.getLogger("padeya.notifications.triggers")

# Cap in-app fan-out so registration/payment hooks stay cheap.
_ADMIN_IN_APP_LIMIT = 20


def _admin_user_ids_for_alert(
    db: Session,
    *,
    permissions: tuple[str, ...],
    roles: tuple[str, ...] = ("super_admin",),
    limit: int = _ADMIN_IN_APP_LIMIT,
) -> list[UUID]:
    """Active staff who hold any listed permission or role (deduped, capped)."""
    rows = db.scalars(select(User).where(User.is_active.is_(True))).all()
    out: list[UUID] = []
    for user in rows:
        if any(user_has_permission(user, code) for code in permissions) or user_has_role(
            user, *roles
        ):
            out.append(user.id)
            if len(out) >= limit:
                break
    return out


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


def notify_admins_user_registered(
    db: Session,
    *,
    user_id: UUID,
    user_name: str,
    user_email: str,
    username: str,
    registered_at: str,
) -> int:
    """Email + in-app + push when a new account is created.

    Failures are logged and never raised — registration must keep succeeding.
    """
    notified = 0
    try:
        from app.email.admin_triggers import admin_notify_user_registered

        admin_notify_user_registered(
            db,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            username=username,
            registered_at=registered_at,
        )
    except Exception:  # noqa: BLE001 — never block registration
        logger.exception("admin email for new user %s failed", user_id)

    display = (user_name or username or "New user").strip() or "New user"
    handle = (username or "").strip()
    body = f"{display} joined Pàdéyá."
    if handle:
        body = f"{display} (@{handle}) joined Pàdéyá."

    try:
        admin_ids = _admin_user_ids_for_alert(
            db,
            permissions=("admin.users.view", "admin.full_access"),
        )
        for admin_id in admin_ids:
            row = notify_user(
                db,
                user_id=admin_id,
                kind="admin.user_registered",
                title="New user registered",
                body=body[:240],
                link_path=f"/admin/users/{user_id}",
                dedupe_key=f"admin:user_registered:{user_id}:notif:{admin_id}",
                send_push=True,
            )
            if row is not None:
                notified += 1
    except Exception:  # noqa: BLE001 — never block registration
        logger.exception("admin in-app for new user %s failed", user_id)
    return notified


def notify_admins_ticket_sale_paid(
    db: Session,
    *,
    order_id: UUID,
    order_reference: str,
    event_title: str,
    host_name: str,
    buyer_name: str,
    ticket_count: int,
    amount: Decimal | float,
    currency: str = "NGN",
    payment_status: str = "paid",
) -> int:
    """Email + in-app + push after verified payment / ticket issuance.

    Call only from the paid-fulfillment path (not checkout init). Dedupe keys
    keep webhook retries and email resends from spamming admins.
    """
    notified = 0
    try:
        from app.email.admin_triggers import admin_notify_ticket_sale_paid

        admin_notify_ticket_sale_paid(
            db,
            order_id=order_id,
            order_reference=order_reference,
            event_title=event_title,
            host_name=host_name,
            buyer_name=buyer_name,
            ticket_count=ticket_count,
            amount=amount,
            currency=currency,
            payment_status=payment_status,
        )
    except Exception:  # noqa: BLE001 — never block fulfillment
        logger.exception("admin email for ticket sale %s failed", order_id)

    title_text = (event_title or "an event").strip() or "an event"
    buyer = (buyer_name or "Buyer").strip() or "Buyer"
    count = max(int(ticket_count or 0), 0)
    body = f"{count} ticket(s) sold for {title_text} ({buyer})."

    try:
        admin_ids = _admin_user_ids_for_alert(
            db,
            permissions=(
                "payments.view",
                "admin.finance.view_fees",
                "refunds.review",
                "admin.full_access",
            ),
        )
        for admin_id in admin_ids:
            row = notify_user(
                db,
                user_id=admin_id,
                kind="admin.ticket_sale",
                title="New ticket sale",
                body=body[:240],
                link_path=f"/admin/payments/orders/{order_id}",
                dedupe_key=f"admin:ticket_sale:{order_id}:notif:{admin_id}",
                send_push=True,
            )
            if row is not None:
                notified += 1
    except Exception:  # noqa: BLE001 — never block fulfillment
        logger.exception("admin in-app for ticket sale %s failed", order_id)
    return notified
