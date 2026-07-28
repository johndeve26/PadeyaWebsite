"""Pending-order reservation holds and expiry.

Inventory is reserved at ``create_order``. Holds expire at
``order.reservation_expires_at`` (derived from ticket-type
``reservation_hold_minutes``, falling back to a platform default).

Expiry and payment finalize race on the Order row (``FOR UPDATE``):
exactly one of {paid, expired} wins — never paid+released inventory.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import TicketType
from app.payments.models import Order, Payment

# Platform safety net when ticket types omit reservation_hold_minutes.
DEFAULT_RESERVATION_HOLD_MINUTES = 30


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def resolve_reservation_hold_minutes(ticket_types: list[TicketType]) -> int:
    """Max configured hold among lines; else platform default."""
    holds = [
        int(tt.reservation_hold_minutes)
        for tt in ticket_types
        if getattr(tt, "reservation_hold_minutes", None)
    ]
    if holds:
        return max(1, max(holds))
    return DEFAULT_RESERVATION_HOLD_MINUTES


def compute_reservation_expires_at(
    *,
    now: datetime | None = None,
    hold_minutes: int | None = None,
    ticket_types: list[TicketType] | None = None,
) -> datetime:
    moment = _aware(now) or datetime.now(UTC)
    if hold_minutes is not None:
        minutes = max(1, int(hold_minutes))
    elif ticket_types is not None:
        minutes = resolve_reservation_hold_minutes(ticket_types)
    else:
        minutes = DEFAULT_RESERVATION_HOLD_MINUTES
    return moment + timedelta(minutes=minutes)


def ticket_sales_window_open(
    tt: TicketType, *, now: datetime | None = None
) -> bool:
    """True when sale_start/sale_end (if set) allow purchase at ``now``."""
    moment = _aware(now) or datetime.now(UTC)
    start = _aware(getattr(tt, "sale_start", None))
    end = _aware(getattr(tt, "sale_end", None))
    if start is not None and moment < start:
        return False
    if end is not None and moment > end:
        return False
    return True


def assert_ticket_sales_window(
    tt: TicketType, *, now: datetime | None = None
) -> None:
    if ticket_sales_window_open(tt, now=now):
        return
    moment = _aware(now) or datetime.now(UTC)
    start = _aware(getattr(tt, "sale_start", None))
    end = _aware(getattr(tt, "sale_end", None))
    if start is not None and moment < start:
        raise HTTPException(
            status_code=400,
            detail=f"Sales have not opened yet for {tt.name}",
        )
    raise HTTPException(
        status_code=400,
        detail=f"Sales have closed for {tt.name}",
    )


def reservation_is_expired(
    order: Order, *, now: datetime | None = None
) -> bool:
    expires = _aware(getattr(order, "reservation_expires_at", None))
    if expires is None:
        return False
    moment = _aware(now) or datetime.now(UTC)
    return moment > expires


def release_order_inventory_holds(db: Session, *, order: Order) -> None:
    """Decrement reserved ticket/merch/bundle/promo holds for a pending order.

    Idempotent w.r.t. inventory math (floors at 0). Caller owns order status.
    """
    from app.merch.bundles import release_bundle_reservation
    from app.merch.constants import ITEM_KIND_MERCH, ITEM_KIND_TICKET
    from app.merch.models import EventMerchVariant, MerchBundle
    from app.merch.service import release_variant_reservation

    released_bundle_ids: set[uuid.UUID] = set()
    for item in order.items:
        kind = getattr(item, "item_kind", None) or (
            ITEM_KIND_MERCH if item.merch_variant_id else ITEM_KIND_TICKET
        )
        if kind == ITEM_KIND_TICKET and item.ticket_type_id is not None:
            tt = db.scalar(
                select(TicketType)
                .where(TicketType.id == item.ticket_type_id)
                .with_for_update()
            )
            if tt is None:
                continue
            tt.quantity_reserved = max(0, tt.quantity_reserved - item.quantity)
        elif kind == ITEM_KIND_MERCH and item.merch_variant_id is not None:
            variant = db.scalar(
                select(EventMerchVariant)
                .where(EventMerchVariant.id == item.merch_variant_id)
                .with_for_update()
            )
            if variant is not None:
                release_variant_reservation(variant, item.quantity)
                from app.merch.models import EventMerchProduct
                from app.merch.stock_alerts import evaluate_variant_stock_alerts

                product = db.get(EventMerchProduct, variant.product_id)
                if product is not None:
                    evaluate_variant_stock_alerts(
                        db, product=product, variant=variant
                    )

        bid = getattr(item, "bundle_id", None)
        if bid and bid not in released_bundle_ids and item.ticket_type_id is not None:
            bundle = db.scalar(
                select(MerchBundle).where(MerchBundle.id == bid).with_for_update()
            )
            if bundle is not None:
                release_bundle_reservation(bundle, item.quantity)
            released_bundle_ids.add(bid)

    from app.promos.service import release_promo_reservation

    release_promo_reservation(db, order=order)


def _release_pending_order(
    db: Session,
    *,
    order: Order,
    terminal_status: str,
    reason: str,
    actor_user_id: uuid.UUID | None = None,
    audit_action: str = "orders.reservation_released",
) -> bool:
    """Release inventory once and transition a pending order to a terminal state."""
    if order.status == "paid":
        return False
    if order.status in {"expired", "failed", "cancelled", "abandoned", "payment_received"}:
        return False
    if order.status != "pending":
        return False

    release_order_inventory_holds(db, order=order)
    order.status = terminal_status

    payment = db.scalar(select(Payment).where(Payment.order_id == order.id))
    if payment is not None and payment.status == "pending":
        payment.status = "failed"

    write_audit_log(
        db,
        action=audit_action,
        actor_user_id=actor_user_id or order.buyer_user_id,
        resource_type="order",
        resource_id=str(order.id),
        details={
            "reference": order.reference,
            "reason": reason,
            "terminal_status": terminal_status,
            "reservation_expires_at": (
                order.reservation_expires_at.isoformat()
                if order.reservation_expires_at
                else None
            ),
        },
    )
    return True


def expire_pending_order(
    db: Session,
    *,
    order: Order,
    now: datetime | None = None,
    reason: str = "reservation_ttl",
) -> bool:
    """Expire a pending order and release inventory exactly once."""
    if reason == "reservation_ttl" and not reservation_is_expired(order, now=now):
        return False
    return _release_pending_order(
        db,
        order=order,
        terminal_status="expired",
        reason=reason,
        actor_user_id=order.buyer_user_id,
        audit_action="orders.reservation_expired",
    )


def cancel_pending_order(
    db: Session,
    *,
    order: Order,
    actor_user_id: uuid.UUID | None = None,
    reason: str = "buyer_cancel",
) -> bool:
    """Buyer/system cancellation of an unpaid pending order — release holds once."""
    return _release_pending_order(
        db,
        order=order,
        terminal_status="cancelled",
        reason=reason,
        actor_user_id=actor_user_id,
        audit_action="orders.cancelled",
    )


def invalidate_event_pending_reservations(
    db: Session,
    *,
    event_id: uuid.UUID,
    reason: str = "event_cancelled",
    actor_user_id: uuid.UUID | None = None,
) -> int:
    """Release all pending holds for an event (e.g. on cancel). Idempotent per order."""
    from sqlalchemy.orm import selectinload

    pending_ids = list(
        db.scalars(
            select(Order.id).where(
                Order.event_id == event_id,
                Order.status == "pending",
            )
        )
    )
    released = 0
    for oid in pending_ids:
        locked = db.scalar(
            select(Order)
            .where(Order.id == oid)
            .options(selectinload(Order.items))
            .with_for_update()
        )
        if locked is None:
            continue
        if _release_pending_order(
            db,
            order=locked,
            terminal_status="cancelled",
            reason=reason,
            actor_user_id=actor_user_id,
            audit_action="orders.reservation_invalidated",
        ):
            released += 1
    return released


def lock_order_for_reservation(db: Session, order_id: uuid.UUID) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def ensure_pending_reservation_active(
    db: Session,
    *,
    order: Order,
    now: datetime | None = None,
) -> Order:
    """If pending hold elapsed, expire and raise 409. Else return order."""
    if order.status != "pending":
        return order
    if not reservation_is_expired(order, now=now):
        return order
    from sqlalchemy.orm import selectinload

    locked = db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items))
        .with_for_update()
    )
    if locked is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if expire_pending_order(db, order=locked, now=now):
        db.flush()
    raise HTTPException(
        status_code=409,
        detail="Reservation expired — inventory was released",
    )


def expire_due_reservations(
    db: Session,
    *,
    limit: int = 100,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Batch sweeper: expire pending orders past reservation_expires_at.

    Idempotent. Safe under concurrent workers when each order is locked.
    """
    from sqlalchemy.orm import selectinload

    moment = _aware(now) or datetime.now(UTC)
    due_ids = list(
        db.scalars(
            select(Order.id)
            .where(
                Order.status == "pending",
                Order.reservation_expires_at.is_not(None),
                Order.reservation_expires_at < moment,
            )
            .limit(max(1, int(limit)))
        )
    )
    expired = 0
    skipped = 0
    for oid in due_ids:
        locked = db.scalar(
            select(Order)
            .where(Order.id == oid)
            .options(selectinload(Order.items))
            .with_for_update()
        )
        if locked is None:
            skipped += 1
            continue
        if expire_pending_order(db, order=locked, now=moment):
            expired += 1
        else:
            skipped += 1
    if expired:
        db.commit()
    return {
        "examined": len(due_ids),
        "expired": expired,
        "skipped": skipped,
        "now": moment.isoformat(),
    }
