"""Authoritative ticket-fulfillment policy during checkout finalization.

Pending reservations created while the event was purchasable may complete
payment until ``reservation_expires_at`` **only while ticket fulfillment
remains allowed** for the event lifecycle state.

Sales-window close is **not** re-checked at finalize (HONORED_UNTIL_EXPIRY).
Event cancellation invalidates pending holds immediately (see
``invalidate_event_pending_reservations``).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.events.models import Event
from app.merch.constants import ITEM_KIND_MERCH, ITEM_KIND_TICKET
from app.payments.models import Order

# Ticket fulfillment blocked — no new admission entitlements.
BLOCK_TICKET_FULFILLMENT_STATUSES = frozenset(
    {
        "draft",
        "rejected",
        "cancelled",
        "archived",
    }
)

COMPLETED_STATUS = "completed"


@dataclass(frozen=True)
class FulfillmentDecision:
    allow_tickets: bool
    allow_merch: bool
    block_reason: str | None = None


def order_has_ticket_lines(order: Order) -> bool:
    for item in order.items or []:
        kind = getattr(item, "item_kind", None) or (
            ITEM_KIND_MERCH if item.merch_variant_id else ITEM_KIND_TICKET
        )
        if kind == ITEM_KIND_TICKET and item.ticket_type_id is not None:
            return True
    return False


def order_has_merch_lines(order: Order) -> bool:
    for item in order.items or []:
        kind = getattr(item, "item_kind", None) or (
            ITEM_KIND_MERCH if item.merch_variant_id else ITEM_KIND_TICKET
        )
        if kind == ITEM_KIND_MERCH and item.merch_variant_id is not None:
            return True
        if getattr(item, "bundle_id", None) is not None:
            return True
    return False


def ticket_fulfillment_decision(
    db: Session,
    *,
    order: Order,
    event: Event | None,
) -> FulfillmentDecision:
    """Return whether ticket/merch fulfillment is allowed for this pending order."""
    if event is None:
        if order_has_ticket_lines(order):
            return FulfillmentDecision(
                allow_tickets=False,
                allow_merch=order_has_merch_lines(order),
                block_reason="event_missing",
            )
        return FulfillmentDecision(allow_tickets=False, allow_merch=True)

    status = (event.status or "").lower()

    if status in BLOCK_TICKET_FULFILLMENT_STATUSES:
        return FulfillmentDecision(
            allow_tickets=False,
            allow_merch=order_has_merch_lines(order) and not order_has_ticket_lines(order),
            block_reason=f"event_status_{status}",
        )

    if status == COMPLETED_STATUS:
        if order_has_ticket_lines(order):
            return FulfillmentDecision(
                allow_tickets=False,
                allow_merch=False,
                block_reason="event_completed_tickets",
            )
        return FulfillmentDecision(
            allow_tickets=False,
            allow_merch=order_has_merch_lines(order),
            block_reason=None,
        )

    if status == "paused":
        return FulfillmentDecision(
            allow_tickets=order_has_ticket_lines(order),
            allow_merch=order_has_merch_lines(order),
            block_reason=None,
        )

    if status == "published":
        return FulfillmentDecision(
            allow_tickets=order_has_ticket_lines(order),
            allow_merch=order_has_merch_lines(order),
            block_reason=None,
        )

    return FulfillmentDecision(
        allow_tickets=False,
        allow_merch=order_has_merch_lines(order) and not order_has_ticket_lines(order),
        block_reason=f"event_status_{status}",
    )


def assert_ticket_fulfillment_allowed(
    db: Session,
    *,
    order: Order,
    event: Event | None,
) -> FulfillmentDecision:
    """Raise 409 when ticket lines cannot be fulfilled (mixed orders are all-or-nothing)."""
    decision = ticket_fulfillment_decision(db, order=order, event=event)
    if order_has_ticket_lines(order) and not decision.allow_tickets:
        reason = decision.block_reason or "event_not_available"
        raise HTTPException(
            status_code=409,
            detail=f"Ticket fulfillment is no longer available ({reason})",
        )
    return decision


def load_order_event(db: Session, order: Order) -> Event | None:
    if order.event_id is None:
        return None
    return db.get(Event, order.event_id)
