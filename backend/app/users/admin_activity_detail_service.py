"""Admin user Activity tab — safe paginated drill-down lists.

Never returns passwords, tokens, QR secrets, private message bodies, or raw
payment payloads. Finance depths (amounts, Paystack refs, host revenue,
ambassador rewards) are gated by viewer permissions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.finance.models import HostBalance, RefundRequest
from app.hosts.models import Host, HostTeamMember, HostVerification
from app.merch.models import MerchFulfillment
from app.payments.models import Order, OrderItem, Payment
from app.promos.ambassador_domain import (
    AmbassadorClick,
    AmbassadorConversion,
    AmbassadorParticipant,
)
from app.promos.models import AmbassadorCampaign
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.users.admin_response_safety import scrub_admin_user_payload
from app.users.models import User
from app.users.service import get_user_by_id, user_has_permission

ActivityKind = Literal[
    "tickets",
    "orders",
    "merch",
    "refunds",
    "reviews",
    "hosts",
    "teams",
    "ambassadors",
]

ACTIVITY_KINDS: frozenset[str] = frozenset(
    {
        "tickets",
        "orders",
        "merch",
        "refunds",
        "reviews",
        "hosts",
        "teams",
        "ambassadors",
    }
)


def _require_user(db: Session, user_id: uuid.UUID) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _can_view_payments(viewer: User) -> bool:
    return user_has_permission(viewer, "payments.view")


def _can_view_refund_amounts(viewer: User) -> bool:
    return (
        _can_view_payments(viewer)
        or user_has_permission(viewer, "refunds.review")
        or user_has_permission(viewer, "refunds.approve")
    )


def _can_view_ambassador_finance(viewer: User) -> bool:
    return (
        _can_view_payments(viewer)
        or user_has_permission(viewer, "ambassadors.view_payouts")
        or user_has_permission(viewer, "ambassadors.view_conversions")
    )


def _money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value):.2f}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _page_payload(
    *,
    items: list[dict[str, Any]],
    page: int,
    limit: int,
    total: int,
    kind: ActivityKind,
    finance_fields_included: bool,
) -> dict[str, Any]:
    safe_items = [scrub_admin_user_payload(row) for row in items]
    return scrub_admin_user_payload(
        {
            "kind": kind,
            "items": safe_items,
            "page": page,
            "limit": limit,
            "total": total,
            "finance_fields_included": finance_fields_included,
        }
    )


def _event_map(db: Session, event_ids: set[uuid.UUID]) -> dict[uuid.UUID, Event]:
    if not event_ids:
        return {}
    rows = list(db.scalars(select(Event).where(Event.id.in_(event_ids))).all())
    return {e.id: e for e in rows}


def _host_map(db: Session, host_ids: set[uuid.UUID]) -> dict[uuid.UUID, Host]:
    if not host_ids:
        return {}
    rows = list(db.scalars(select(Host).where(Host.id.in_(host_ids))).all())
    return {h.id: h for h in rows}


def _user_name_map(db: Session, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not user_ids:
        return {}
    rows = list(db.scalars(select(User).where(User.id.in_(user_ids))).all())
    return {u.id: (u.full_name or u.email) for u in rows}


def list_user_activity_tickets(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    total = int(
        db.scalar(
            select(func.count(Ticket.id)).where(Ticket.buyer_user_id == user_id)
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.buyer_user_id == user_id)
            .order_by(Ticket.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    event_ids = {t.event_id for t in rows}
    order_ids = {t.order_id for t in rows}
    events = _event_map(db, event_ids)
    host_ids = {e.host_id for e in events.values() if e.host_id}
    hosts = _host_map(db, host_ids)
    orders = {
        o.id: o
        for o in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
    } if order_ids else {}

    items: list[dict[str, Any]] = []
    for t in rows:
        event = events.get(t.event_id)
        host = hosts.get(event.host_id) if event else None
        order = orders.get(t.order_id)
        items.append(
            {
                "id": str(t.id),
                "public_code": t.public_code,
                "event_id": str(t.event_id),
                "event_name": event.title if event else None,
                "event_slug": event.slug if event else None,
                "host_id": str(host.id) if host else None,
                "host_name": host.display_name if host else None,
                "ticket_type": t.ticket_type_name,
                "status": t.status,
                "checked_in": t.checked_in_at is not None,
                "checked_in_at": _iso(t.checked_in_at),
                "purchase_date": _iso(t.created_at),
                "order_id": str(t.order_id),
                "order_reference": order.reference if order else None,
                "event_admin_href": f"/admin/events/{t.event_id}/buyers",
                "event_public_href": (
                    f"/events/{event.slug}" if event and event.slug else None
                ),
                "order_admin_href": "/admin/orders",
            }
        )
    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="tickets",
        finance_fields_included=False,
    )


def list_user_activity_orders(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    include_finance = _can_view_payments(viewer)
    total = int(
        db.scalar(select(func.count(Order.id)).where(Order.buyer_user_id == user_id))
        or 0
    )
    rows = list(
        db.scalars(
            select(Order)
            .where(Order.buyer_user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    order_ids = {o.id for o in rows}
    event_ids = {o.event_id for o in rows}
    events = _event_map(db, event_ids)

    ticket_counts: dict[uuid.UUID, int] = {}
    if order_ids:
        for oid, cnt in db.execute(
            select(Ticket.order_id, func.count(Ticket.id))
            .where(Ticket.order_id.in_(order_ids))
            .group_by(Ticket.order_id)
        ):
            ticket_counts[oid] = int(cnt)

    merch_labels: dict[uuid.UUID, str] = {}
    if order_ids:
        for oid, name, variant in db.execute(
            select(
                OrderItem.order_id,
                OrderItem.product_name,
                OrderItem.variant_label,
            ).where(
                OrderItem.order_id.in_(order_ids),
                OrderItem.item_kind == "merch",
            )
        ):
            label = " · ".join(p for p in (name, variant) if p)
            if label:
                merch_labels[oid] = label

    payments: dict[uuid.UUID, Payment] = {}
    if order_ids and include_finance:
        for pay in db.scalars(
            select(Payment)
            .where(Payment.order_id.in_(order_ids))
            .order_by(Payment.created_at.desc())
        ).all():
            payments.setdefault(pay.order_id, pay)

    refund_status: dict[uuid.UUID, str] = {}
    if order_ids:
        for oid, status, created in db.execute(
            select(
                RefundRequest.order_id,
                RefundRequest.status,
                RefundRequest.created_at,
            )
            .where(RefundRequest.order_id.in_(order_ids))
            .order_by(RefundRequest.created_at.desc())
        ):
            refund_status.setdefault(oid, status)

    items: list[dict[str, Any]] = []
    for o in rows:
        event = events.get(o.event_id)
        subject = event.title if event else None
        if o.id in merch_labels:
            subject = (
                f"{subject} / {merch_labels[o.id]}"
                if subject
                else merch_labels[o.id]
            )
        pay = payments.get(o.id)
        row: dict[str, Any] = {
            "id": str(o.id),
            "order_reference": o.reference,
            "event_id": str(o.event_id),
            "subject": subject,
            "payment_status": o.status,
            "created_at": _iso(o.created_at),
            "ticket_count": ticket_counts.get(o.id, 0),
            "refund_status": refund_status.get(o.id),
            "event_admin_href": f"/admin/events/{o.event_id}/buyers",
            "order_admin_href": "/admin/orders",
            "currency": None,
            "amount": None,
            "paystack_reference": None,
        }
        if include_finance:
            row["currency"] = o.currency
            row["amount"] = _money(o.total_amount)
            # Safe admin payment reference only — never raw_response / access_code.
            row["paystack_reference"] = pay.reference if pay else None
        items.append(row)

    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="orders",
        finance_fields_included=include_finance,
    )


def list_user_activity_merch(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    include_finance = _can_view_payments(viewer)
    total = int(
        db.scalar(
            select(func.count(MerchFulfillment.id)).where(
                MerchFulfillment.buyer_user_id == user_id
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(MerchFulfillment)
            .where(MerchFulfillment.buyer_user_id == user_id)
            .order_by(MerchFulfillment.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    order_ids = {r.order_id for r in rows}
    event_ids = {r.event_id for r in rows if r.event_id}
    host_ids = {r.host_id for r in rows}
    orders = {
        o.id: o
        for o in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
    } if order_ids else {}
    events = _event_map(db, event_ids)
    hosts = _host_map(db, host_ids)

    line_totals: dict[uuid.UUID, Decimal] = {}
    if order_ids and include_finance:
        for oid, line_total in db.execute(
            select(OrderItem.id, OrderItem.line_total).where(
                OrderItem.order_id.in_(order_ids)
            )
        ):
            line_totals[oid] = Decimal(line_total)

    items: list[dict[str, Any]] = []
    for r in rows:
        order = orders.get(r.order_id)
        event = events.get(r.event_id) if r.event_id else None
        host = hosts.get(r.host_id)
        merch_label = " · ".join(
            p for p in (r.product_name_snapshot, r.variant_label_snapshot) if p
        )
        picked_up = r.fulfilled_at is not None or r.status in {
            "fulfilled",
            "picked_up",
            "delivered",
        }
        row: dict[str, Any] = {
            "id": str(r.id),
            "merch_item": merch_label or "Merch",
            "event_id": str(r.event_id) if r.event_id else None,
            "event_name": event.title if event else None,
            "host_id": str(r.host_id),
            "host_name": host.display_name if host else None,
            "quantity": r.quantity,
            "fulfillment_status": r.status,
            "fulfillment_method": r.fulfillment_method,
            "pickup_or_check_in_status": (
                "completed" if picked_up else "pending"
            ),
            "order_id": str(r.order_id),
            "order_reference": order.reference if order else None,
            "created_at": _iso(r.created_at),
            "order_admin_href": "/admin/orders",
            "amount": None,
            "currency": None,
        }
        if include_finance:
            row["amount"] = _money(line_totals.get(r.order_item_id))
            row["currency"] = order.currency if order else None
        items.append(row)

    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="merch",
        finance_fields_included=include_finance,
    )


def list_user_activity_refunds(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    include_amounts = _can_view_refund_amounts(viewer)
    total = int(
        db.scalar(
            select(func.count(RefundRequest.id)).where(
                RefundRequest.buyer_user_id == user_id
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(RefundRequest)
            .where(RefundRequest.buyer_user_id == user_id)
            .order_by(RefundRequest.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    order_ids = {r.order_id for r in rows}
    reviewer_ids = {r.reviewed_by_user_id for r in rows if r.reviewed_by_user_id}
    orders = {
        o.id: o
        for o in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
    } if order_ids else {}
    names = _user_name_map(db, reviewer_ids)

    items: list[dict[str, Any]] = []
    for r in rows:
        order = orders.get(r.order_id)
        row: dict[str, Any] = {
            "id": str(r.id),
            "order_id": str(r.order_id),
            "order_reference": order.reference if order else None,
            "status": r.status,
            "reason_category": r.policy_snapshot,
            "requested_at": _iso(r.created_at),
            "resolved_at": _iso(r.reviewed_at),
            "handled_by_admin_id": (
                str(r.reviewed_by_user_id) if r.reviewed_by_user_id else None
            ),
            "handled_by_admin_name": (
                names.get(r.reviewed_by_user_id)
                if r.reviewed_by_user_id
                else None
            ),
            "order_admin_href": "/admin/orders",
            "refund_admin_href": "/admin/refunds",
            "amount": None,
            "currency": None,
        }
        if include_amounts:
            row["amount"] = _money(r.requested_amount)
            row["currency"] = r.currency
        items.append(row)

    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="refunds",
        finance_fields_included=include_amounts,
    )


def list_user_activity_reviews(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    total = int(
        db.scalar(
            select(func.count(VerifiedReview.id)).where(
                VerifiedReview.reviewer_user_id == user_id
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(VerifiedReview)
            .where(VerifiedReview.reviewer_user_id == user_id)
            .order_by(VerifiedReview.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    event_ids = {r.event_id for r in rows}
    host_ids = {r.host_id for r in rows}
    events = _event_map(db, event_ids)
    hosts = _host_map(db, host_ids)

    items: list[dict[str, Any]] = []
    for r in rows:
        event = events.get(r.event_id)
        host = hosts.get(r.host_id)
        visibility = "public" if r.status == "visible" else "private"
        items.append(
            {
                "id": str(r.id),
                "target_type": "event",
                "target_name": event.title if event else None,
                "event_id": str(r.event_id),
                "host_id": str(r.host_id),
                "host_name": host.display_name if host else None,
                "rating": r.rating,
                "visibility": visibility,
                "verified_attendance": True,
                "created_at": _iso(r.created_at),
                "moderation_status": r.status,
                "target_admin_href": f"/admin/events/{r.event_id}/buyers",
                "target_public_href": (
                    f"/events/{event.slug}" if event and event.slug else None
                ),
                "reviews_admin_href": "/admin/reviews",
            }
        )
    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="reviews",
        finance_fields_included=False,
    )


def list_user_activity_hosts(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    include_finance = _can_view_payments(viewer)
    total = int(
        db.scalar(select(func.count(Host.id)).where(Host.user_id == user_id)) or 0
    )
    rows = list(
        db.scalars(
            select(Host)
            .where(Host.user_id == user_id)
            .order_by(Host.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    host_ids = {h.id for h in rows}

    event_counts: dict[uuid.UUID, int] = {}
    if host_ids:
        for hid, cnt in db.execute(
            select(Event.host_id, func.count(Event.id))
            .where(Event.host_id.in_(host_ids))
            .group_by(Event.host_id)
        ):
            event_counts[hid] = int(cnt)

    verification: dict[uuid.UUID, str] = {}
    if host_ids:
        for hid, status, created in db.execute(
            select(
                HostVerification.host_id,
                HostVerification.status,
                HostVerification.created_at,
            )
            .where(HostVerification.host_id.in_(host_ids))
            .order_by(HostVerification.created_at.desc())
        ):
            verification.setdefault(hid, status)

    balances: dict[uuid.UUID, HostBalance] = {}
    if host_ids and include_finance:
        for bal in db.scalars(
            select(HostBalance).where(HostBalance.host_id.in_(host_ids))
        ).all():
            balances[bal.host_id] = bal

    items: list[dict[str, Any]] = []
    for h in rows:
        row: dict[str, Any] = {
            "id": str(h.id),
            "host_name": h.display_name,
            "host_slug": h.slug,
            "verification_status": verification.get(h.id, "unverified"),
            "events_count": event_counts.get(h.id, 0),
            "created_at": _iso(h.created_at),
            "status": h.status,
            "host_admin_href": "/admin/hosts",
            "host_public_href": f"/hosts/{h.slug}" if h.slug else None,
            "revenue_summary": None,
        }
        if include_finance:
            bal = balances.get(h.id)
            if bal:
                row["revenue_summary"] = {
                    "currency": bal.currency,
                    "available_balance": _money(bal.available_balance),
                    "lifetime_earned": _money(bal.lifetime_earned),
                    "lifetime_refunded": _money(bal.lifetime_refunded),
                    "lifetime_paid_out": _money(bal.lifetime_paid_out),
                }
            else:
                row["revenue_summary"] = {
                    "currency": "NGN",
                    "available_balance": "0.00",
                    "lifetime_earned": "0.00",
                    "lifetime_refunded": "0.00",
                    "lifetime_paid_out": "0.00",
                }
        items.append(row)

    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="hosts",
        finance_fields_included=include_finance,
    )


def list_user_activity_teams(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    total = int(
        db.scalar(
            select(func.count(HostTeamMember.id)).where(
                HostTeamMember.user_id == user_id
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(HostTeamMember)
            .where(HostTeamMember.user_id == user_id)
            .order_by(HostTeamMember.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    host_ids = {m.host_id for m in rows}
    inviter_ids = {m.invited_by_user_id for m in rows if m.invited_by_user_id}
    hosts = _host_map(db, host_ids)
    names = _user_name_map(db, inviter_ids)

    items: list[dict[str, Any]] = []
    for m in rows:
        host = hosts.get(m.host_id)
        perms = m.permissions_json or {}
        enabled = sorted(
            k for k, v in perms.items() if v is True or v == "true" or v == 1
        )
        items.append(
            {
                "id": str(m.id),
                "host_id": str(m.host_id),
                "host_name": host.display_name if host else None,
                "role": m.role_label or m.role,
                "permissions": enabled,
                "joined_at": _iso(m.joined_at or m.created_at),
                "status": m.status,
                "invited_by_user_id": (
                    str(m.invited_by_user_id) if m.invited_by_user_id else None
                ),
                "invited_by_name": (
                    names.get(m.invited_by_user_id)
                    if m.invited_by_user_id
                    else None
                ),
                "host_admin_href": "/admin/hosts",
                "host_public_href": (
                    f"/hosts/{host.slug}" if host and host.slug else None
                ),
            }
        )
    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="teams",
        finance_fields_included=False,
    )


def list_user_activity_ambassadors(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    _require_user(db, user_id)
    include_finance = _can_view_ambassador_finance(viewer)
    total = int(
        db.scalar(
            select(func.count(AmbassadorParticipant.id)).where(
                AmbassadorParticipant.user_id == user_id
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(AmbassadorParticipant)
            .where(AmbassadorParticipant.user_id == user_id)
            .order_by(AmbassadorParticipant.joined_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    campaign_ids = {p.campaign_id for p in rows}
    participant_ids = {p.id for p in rows}
    campaigns = {
        c.id: c
        for c in db.scalars(
            select(AmbassadorCampaign).where(AmbassadorCampaign.id.in_(campaign_ids))
        ).all()
    } if campaign_ids else {}
    event_ids = {c.event_id for c in campaigns.values() if c.event_id}
    host_ids = {c.host_id for c in campaigns.values() if c.host_id}
    events = _event_map(db, event_ids)
    hosts = _host_map(db, host_ids)

    click_counts: dict[uuid.UUID, int] = {}
    conversion_counts: dict[uuid.UUID, int] = {}
    rewards: dict[uuid.UUID, Decimal] = {}
    payout_status: dict[uuid.UUID, str] = {}
    if participant_ids:
        for pid, cnt in db.execute(
            select(AmbassadorClick.participant_id, func.count(AmbassadorClick.id))
            .where(AmbassadorClick.participant_id.in_(participant_ids))
            .group_by(AmbassadorClick.participant_id)
        ):
            click_counts[pid] = int(cnt)

        for pid, cnt in db.execute(
            select(
                AmbassadorConversion.participant_id,
                func.count(AmbassadorConversion.id),
            )
            .where(AmbassadorConversion.participant_id.in_(participant_ids))
            .group_by(AmbassadorConversion.participant_id)
        ):
            conversion_counts[pid] = int(cnt)

        for pid, total_commission in db.execute(
            select(
                AmbassadorConversion.participant_id,
                func.coalesce(func.sum(AmbassadorConversion.commission_amount), 0),
            )
            .where(
                AmbassadorConversion.participant_id.in_(participant_ids),
                AmbassadorConversion.status.in_(("approved", "payable", "paid")),
            )
            .group_by(AmbassadorConversion.participant_id)
        ):
            rewards[pid] = Decimal(total_commission)

        rank = {
            "paid": 5,
            "payable": 4,
            "approved": 3,
            "pending": 2,
            "rejected": 1,
            "reversed": 0,
        }
        for pid, status in db.execute(
            select(
                AmbassadorConversion.participant_id,
                AmbassadorConversion.status,
            ).where(AmbassadorConversion.participant_id.in_(participant_ids))
        ):
            prev = payout_status.get(pid)
            if prev is None or rank.get(status, -1) > rank.get(prev, -1):
                payout_status[pid] = status

    items: list[dict[str, Any]] = []
    for p in rows:
        campaign = campaigns.get(p.campaign_id)
        event = events.get(campaign.event_id) if campaign and campaign.event_id else None
        host = hosts.get(campaign.host_id) if campaign and campaign.host_id else None
        subject = None
        if event:
            subject = event.title
        elif host:
            subject = host.display_name
        row: dict[str, Any] = {
            "id": str(p.id),
            "campaign_id": str(p.campaign_id),
            "campaign_name": campaign.name if campaign else None,
            "event_or_host": subject,
            "role_status": p.status,
            "referral_code": p.ambassador_code,
            "clicks": click_counts.get(p.id, 0),
            "conversions": conversion_counts.get(p.id, 0),
            "joined_at": _iso(p.joined_at),
            "campaign_admin_href": "/admin/ambassadors/campaigns",
            "rewards_earned": None,
            "payout_status": None,
        }
        if include_finance:
            row["rewards_earned"] = _money(rewards.get(p.id, Decimal("0")))
            row["payout_status"] = payout_status.get(p.id)
        items.append(row)

    return _page_payload(
        items=items,
        page=page,
        limit=limit,
        total=total,
        kind="ambassadors",
        finance_fields_included=include_finance,
    )


_LISTERS = {
    "tickets": list_user_activity_tickets,
    "orders": list_user_activity_orders,
    "merch": list_user_activity_merch,
    "refunds": list_user_activity_refunds,
    "reviews": list_user_activity_reviews,
    "hosts": list_user_activity_hosts,
    "teams": list_user_activity_teams,
    "ambassadors": list_user_activity_ambassadors,
}


def list_user_activity_detail(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer: User,
    kind: str,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    if kind not in ACTIVITY_KINDS:
        raise HTTPException(status_code=404, detail="Unknown activity kind")
    return _LISTERS[kind](
        db, user_id=user_id, viewer=viewer, page=page, limit=limit
    )
