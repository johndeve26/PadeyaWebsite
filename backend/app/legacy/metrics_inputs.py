"""Authoritative Legacy score input collectors (repeat buyers, refund/dispute)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.finance.models import Refund
from app.hosts.fan_self_abuse import order_excluded_from_public_metrics
from app.payments.models import Order


def _quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _eligible_paid_orders(db: Session, host_id: UUID) -> list[Order]:
    from app.hosts.models import Host

    owner_user_id = db.scalar(select(Host.user_id).where(Host.id == host_id))
    rows = list(
        db.scalars(
            select(Order)
            .join(Event, Event.id == Order.event_id)
            .where(
                Event.host_id == host_id,
                Order.status.in_(("paid", "partially_refunded", "refunded")),
                Order.buyer_user_id.is_not(None),
            )
        ).all()
    )
    out: list[Order] = []
    for order in rows:
        if owner_user_id is not None and order.buyer_user_id == owner_user_id:
            continue
        if order_excluded_from_public_metrics(order):
            continue
        out.append(order)
    return out


def compute_repeat_buyers_rate(db: Session, host_id: UUID) -> Decimal | None:
    """Share of unique buyers with paid orders on 2+ distinct host events.

    Matches CRM ``repeat_buyers`` segment logic. Returns None when there are no
    eligible buyers (unknown — repeat factor uses 0 in scoring).
    """
    orders = _eligible_paid_orders(db, host_id)
    if not orders:
        return None

    events_by_buyer: dict[UUID, set[UUID]] = {}
    for order in orders:
        if order.buyer_user_id is None or order.event_id is None:
            continue
        events_by_buyer.setdefault(order.buyer_user_id, set()).add(order.event_id)

    unique_buyers = len(events_by_buyer)
    if unique_buyers == 0:
        return None

    repeat_buyers = sum(1 for events in events_by_buyer.values() if len(events) >= 2)
    return _quantize_rate(Decimal(repeat_buyers) / Decimal(unique_buyers) * Decimal("100"))


def compute_refund_dispute_rate(db: Session, host_id: UUID) -> Decimal | None:
    """Completed refunds as a percentage of eligible paid orders.

    Returns None when there is no eligible paid-order baseline (unknown — scoring
    uses the documented neutral default of 80 for the refund factor). Returns
    ``0`` when orders exist but no completed refunds.
    """
    orders = _eligible_paid_orders(db, host_id)
    paid_count = len(orders)
    if paid_count == 0:
        return None

    order_ids = {o.id for o in orders}
    refund_count = int(
        db.scalar(
            select(func.count())
            .select_from(Refund)
            .where(
                Refund.host_id == host_id,
                Refund.status == "completed",
                Refund.order_id.in_(order_ids),
            )
        )
        or 0
    )
    return _quantize_rate(Decimal(refund_count) / Decimal(paid_count) * Decimal("100"))
