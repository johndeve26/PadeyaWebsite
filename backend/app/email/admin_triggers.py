"""Product hooks for admin platform email notifications (template-driven)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.email.admin_dispatch import notify_admins_platform_email


def _money(amount: Any, currency: str = "NGN") -> tuple[str, str]:
    try:
        val = float(amount)
    except (TypeError, ValueError):
        val = 0.0
    return f"{val:,.2f}", currency or "NGN"


def admin_notify_user_registered(
    db: Session,
    *,
    user_id: UUID,
    user_name: str,
    user_email: str,
    username: str,
    registered_at: str,
) -> None:
    notify_admins_platform_email(
        db,
        template_key="admin_new_user_registered",
        context={
            "user_name": user_name,
            "user_email": user_email,
            "username": username,
            "registered_at": registered_at,
            "user_id_safe": str(user_id),
            "admin_user_url": f"/admin/users/{user_id}",
        },
        dedupe_key=f"admin:user_registered:{user_id}",
        entity_id=user_id,
    )


def admin_notify_user_email_verified(
    db: Session,
    *,
    user_id: UUID,
    user_name: str,
    user_email: str,
    username: str,
    verified_at: str,
) -> None:
    notify_admins_platform_email(
        db,
        template_key="admin_user_email_verified",
        context={
            "user_name": user_name,
            "user_email": user_email,
            "username": username,
            "verified_at": verified_at,
            "admin_user_url": f"/admin/users/{user_id}",
        },
        dedupe_key=f"admin:user_verified:{user_id}",
        entity_id=user_id,
    )


def admin_notify_ticket_sale_paid(
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
) -> None:
    amt, cur = _money(amount, currency)
    ctx = {
        "event_title": event_title,
        "host_name": host_name,
        "buyer_name": buyer_name,
        "order_reference": order_reference,
        "ticket_count": str(ticket_count),
        "amount": amt,
        "currency": cur,
        "payment_status": payment_status,
        "admin_order_url": f"/admin/payments/orders/{order_id}",
        "admin_event_url": "/admin/events",
    }
    notify_admins_platform_email(
        db,
        template_key="admin_new_ticket_sale",
        context=ctx,
        dedupe_key=f"admin:ticket_sale:{order_id}",
        entity_id=order_id,
    )
    notify_admins_platform_email(
        db,
        template_key="admin_large_ticket_order",
        context=ctx,
        dedupe_key=f"admin:large_ticket:{order_id}",
        entity_id=order_id,
    )


def admin_notify_merch_sale_paid(
    db: Session,
    *,
    order_id: UUID,
    order_reference: str,
    product_title: str,
    host_name: str,
    buyer_name: str,
    quantity: int,
    amount: Decimal | float,
    currency: str = "NGN",
    fulfillment_type: str,
) -> None:
    amt, cur = _money(amount, currency)
    notify_admins_platform_email(
        db,
        template_key="admin_new_merch_sale",
        context={
            "product_title": product_title,
            "host_name": host_name,
            "buyer_name": buyer_name,
            "order_reference": order_reference,
            "quantity": str(quantity),
            "amount": amt,
            "currency": cur,
            "fulfillment_type": fulfillment_type,
            "admin_order_url": f"/admin/payments/orders/{order_id}",
            "admin_merch_url": "/admin/merch",
        },
        dedupe_key=f"admin:merch_sale:{order_id}",
        entity_id=order_id,
    )


def admin_notify_support_ticket_created(
    db: Session,
    *,
    case_id: UUID,
    ticket_number: str,
    subject: str,
    requester_name: str,
    category: str,
    priority: str,
) -> None:
    notify_admins_platform_email(
        db,
        template_key="admin_new_support_ticket",
        context={
            "ticket_number": ticket_number,
            "subject": subject,
            "requester_name": requester_name,
            "category": category,
            "priority": priority,
            "admin_ticket_url": f"/admin/support/{case_id}",
        },
        dedupe_key=f"admin:support_ticket:{case_id}",
        entity_id=case_id,
    )


def admin_notify_new_event(
    db: Session,
    *,
    event_id: UUID,
    event_title: str,
    host_name: str,
    event_date: str,
    status: str,
    city: str,
    published: bool = False,
) -> None:
    key = "admin_event_published" if published else "admin_new_event_created"
    notify_admins_platform_email(
        db,
        template_key=key,
        context={
            "event_title": event_title,
            "host_name": host_name,
            "event_date": event_date,
            "status": status,
            "city": city,
            "admin_event_url": f"/admin/events/{event_id}",
        },
        dedupe_key=f"admin:event:{key}:{event_id}",
        entity_id=event_id,
    )


def admin_notify_sponsor_inquiry(
    db: Session,
    *,
    inquiry_id: UUID,
    host_name: str,
    brand_name: str,
) -> None:
    notify_admins_platform_email(
        db,
        template_key="admin_new_sponsor_inquiry",
        context={
            "host_name": host_name,
            "brand_name": brand_name,
            "inquiry_id_safe": str(inquiry_id),
            "admin_inquiry_url": f"/admin/sponsors/inquiries/{inquiry_id}",
        },
        dedupe_key=f"admin:sponsor_inquiry:{inquiry_id}",
        entity_id=inquiry_id,
    )


def admin_notify_ambassador_fraud_signal(
    db: Session,
    *,
    campaign_id: UUID,
    event_title: str,
    host_name: str,
    campaign_name: str,
    signal_summary: str,
) -> None:
    notify_admins_platform_email(
        db,
        template_key="admin_ambassador_click_inflation_suspect",
        context={
            "event_title": event_title,
            "host_name": host_name,
            "campaign_name": campaign_name,
            "signal_summary": signal_summary,
            "admin_campaign_url": f"/admin/ambassadors/campaigns/{campaign_id}",
        },
        dedupe_key=f"admin:ambassador_fraud:{campaign_id}",
        entity_id=campaign_id,
    )
