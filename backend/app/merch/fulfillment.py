"""Merch fulfillment after paid orders and staff pickup."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host
from app.merch.constants import FULFILLMENT_STATUS_ALIASES, ITEM_KIND_MERCH
from app.merch.models import (
    EventMerchProduct,
    EventMerchVariant,
    MerchFulfillment,
    MerchFulfillmentEvent,
)
from app.merch.privacy import buyer_pickup_fields, public_pickup_fields
from app.merch.service import (
    can_fulfill_event_merch,
    can_reveal_shipping_address,
    can_view_event_merch_fulfillments,
    commit_variant_sale,
    restock_variant_on_refund,
)
from app.payments.models import Order
from app.users.models import User


def buyer_display_status(*, fulfillment_status: str, order_status: str | None) -> str:
    """Buyer-facing status keys used by the dashboard."""
    order_status = (order_status or "").lower()
    status = (fulfillment_status or "").lower()
    if order_status == "refunded" or status == "refunded":
        return "refunded"
    if status == "cancelled":
        return "cancelled"
    if status == "fulfilled":
        return "picked_up"
    if status == "delivered":
        return "delivered"
    if status == "shipped":
        return "shipped"
    if status in {"awaiting_shipment", "packed"}:
        return "awaiting_shipment"
    if status == "collect_at_stand":
        return "ready_for_pickup"
    if status == "awaiting_pickup":
        return "confirmed"
    if status == "pending_payment" or order_status in {"pending", "failed"}:
        return "pending_payment"
    return status or "pending_payment"


def _record_fulfillment_event(
    db: Session,
    *,
    fulfillment: MerchFulfillment,
    action: str,
    actor_user_id: uuid.UUID | None,
    note: str | None = None,
) -> None:
    cleaned = (note or "").strip() or None
    db.add(
        MerchFulfillmentEvent(
            merch_fulfillment_id=fulfillment.id,
            actor_user_id=actor_user_id,
            action=action,
            note=cleaned,
        )
    )


def normalize_fulfillment_status(status: str) -> str:
    return FULFILLMENT_STATUS_ALIASES.get(status, status)


def _new_pickup_code(db: Session) -> str:
    """Allocate a unique merch pickup code (not a ticket QR token)."""
    for _ in range(12):
        # 8 hex chars — separate namespace from ticket QR payloads.
        code = f"MRCH-{secrets.token_hex(4).upper()}"
        exists = db.scalar(
            select(MerchFulfillment.id).where(MerchFulfillment.pickup_code == code)
        )
        if exists is None:
            return code
    return f"MRCH-{uuid.uuid4().hex[:8].upper()}"


def serialize_fulfillment(
    db: Session,
    row: MerchFulfillment,
    *,
    include_buyer: bool = False,
    reveal_shipping_address: bool = False,
) -> dict:
    from app.merch.models import MerchShippingAddress
    from app.merch.shipping import decrypt_address_for_staff, public_shipping_hint

    event = db.get(Event, row.event_id)
    host = db.get(Host, row.host_id)
    order = db.scalar(
        select(Order)
        .where(Order.id == row.order_id)
        .options(selectinload(Order.items))
    )
    variant = db.get(EventMerchVariant, row.merch_variant_id)
    product = (
        db.get(EventMerchProduct, variant.product_id) if variant is not None else None
    )
    pickup = buyer_pickup_fields(
        None,
        event,
        snapshots={
            "pickup_instructions": row.pickup_instructions_snapshot,
            "pickup_location_label": getattr(
                row, "pickup_location_label_snapshot", None
            ),
            "pickup_time_window": getattr(row, "pickup_time_window_snapshot", None),
            "fulfillment_notes": getattr(row, "fulfillment_notes_snapshot", None),
        },
    )
    order_status = order.status if order else None
    method = getattr(row, "fulfillment_method", None) or "pickup"
    # Desk-only notes: never on buyer `/mine`; host desk may see snapshot.
    desk_notes = None
    if include_buyer:
        desk_notes = getattr(row, "fulfillment_notes_snapshot", None) or None

    shipping_payload = None
    if method == "shipping" and getattr(row, "shipping_address_id", None):
        addr = db.get(MerchShippingAddress, row.shipping_address_id)
        if addr is not None:
            if reveal_shipping_address:
                # Host/staff with fulfill permission only.
                shipping_payload = decrypt_address_for_staff(addr)
            else:
                # Buyer (or view-only staff): city/state/country summary only.
                shipping_payload = public_shipping_hint(addr)

    data = {
        "id": row.id,
        "order_id": row.order_id,
        "order_item_id": row.order_item_id,
        "event_id": row.event_id,
        "host_id": row.host_id,
        "buyer_user_id": row.buyer_user_id,
        "merch_variant_id": row.merch_variant_id,
        "quantity": row.quantity,
        "status": row.status,
        "fulfillment_method": method,
        "display_status": buyer_display_status(
            fulfillment_status=row.status, order_status=order_status
        ),
        "pickup_code": row.pickup_code,
        "pickup_instructions_snapshot": pickup["pickup_instructions"],
        "pickup_location_label": pickup["pickup_location_label"],
        "pickup_time_window": pickup["pickup_time_window"],
        "fulfillment_notes": desk_notes,
        "product_name_snapshot": row.product_name_snapshot,
        "variant_label_snapshot": row.variant_label_snapshot,
        "product_image_url": product.image_url if product else None,
        "tracking_number": getattr(row, "tracking_number", None),
        "carrier": getattr(row, "carrier", None),
        "shipped_at": getattr(row, "shipped_at", None),
        "delivered_at": getattr(row, "delivered_at", None),
        "bundle_id": getattr(row, "bundle_id", None),
        "fulfilled_at": row.fulfilled_at,
        "fulfilled_by_user_id": row.fulfilled_by_user_id,
        "fulfilled_by_name": None,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "event_title": event.title if event else None,
        "event_slug": event.slug if event else None,
        "host_name": host.display_name if host else None,
        "host_slug": host.slug if host else None,
        "order_reference": order.reference if order else None,
        "order_status": order_status,
        # Never expose buyer email/phone on merch APIs (privacy).
        "buyer_email": None,
        "buyer_name": None,
        "shipping_address": shipping_payload,
        "qr_token": None,
        "qr_typ": "padeya.merch.pickup",
    }
    if not include_buyer:
        from app.merch.qr_pickup import attach_qr_to_serialize

        attach_qr_to_serialize(db, data, row)
    if row.fulfilled_by_user_id is not None:
        staff = db.get(User, row.fulfilled_by_user_id)
        data["fulfilled_by_name"] = staff.full_name if staff else None

    if include_buyer and order is not None:
        data["buyer_name"] = order.buyer_name
        ticket_count = sum(
            item.quantity
            for item in (order.items or [])
            if (getattr(item, "item_kind", None) or "ticket") != ITEM_KIND_MERCH
            and item.ticket_type_id is not None
        )
        data["has_ticket"] = ticket_count > 0
        data["ticket_count"] = ticket_count
    else:
        data["has_ticket"] = None
        data["ticket_count"] = None
    return data


def _assert_pickup_allowed(db: Session, row: MerchFulfillment) -> None:
    """Block double pickup and cancelled/refunded collections."""
    if row.status == "fulfilled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already picked up",
        )
    if row.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Cancelled or refunded merch cannot be picked up",
        )
    order = db.get(Order, row.order_id)
    if order is not None and order.status in {"refunded", "failed", "cancelled"}:
        raise HTTPException(
            status_code=400,
            detail="This merch order cannot be picked up",
        )


def create_fulfillments_for_paid_order(db: Session, order: Order) -> list[MerchFulfillment]:
    """Decrement inventory and create fulfillment rows for merch lines. Idempotent.

    Merch is only marked purchased here — after verified payment webhook.
    """
    existing = list(
        db.scalars(select(MerchFulfillment).where(MerchFulfillment.order_id == order.id))
    )
    existing_by_item = {row.order_item_id: row for row in existing}
    created: list[MerchFulfillment] = list(existing)

    # Host-shop orders have no event_id — fall back to the order's own host_id
    # so merch pickup fulfillment (and its QR) still gets created for them.
    event = db.get(Event, order.event_id) if order.event_id is not None else None
    order_host_id = event.host_id if event is not None else getattr(order, "host_id", None)
    if order_host_id is None:
        return created

    order_method = getattr(order, "fulfillment_method", None) or "pickup"
    bundle_ids_seen: set = set()

    for item in order.items:
        kind = getattr(item, "item_kind", None) or (
            ITEM_KIND_MERCH if item.merch_variant_id else "ticket"
        )
        if kind != ITEM_KIND_MERCH or item.merch_variant_id is None:
            continue
        if item.id in existing_by_item:
            continue

        variant = db.scalar(
            select(EventMerchVariant)
            .where(EventMerchVariant.id == item.merch_variant_id)
            .with_for_update()
        )
        if variant is None:
            raise HTTPException(status_code=400, detail="Merch variant missing at finalize")
        prev_available = None
        from app.merch.service import available_variant_stock

        prev_available = available_variant_stock(variant)
        became_sold_out = commit_variant_sale(variant, item.quantity)

        product = db.get(EventMerchProduct, item.merch_product_id or variant.product_id)
        if became_sold_out and product is not None:
            from app.analytics.trusted import emit_merch_sold_out

            emit_merch_sold_out(
                db,
                event_id=order.event_id,
                host_id=order_host_id,
                merch_product_id=product.id,
                merch_variant_id=variant.id,
            )

        method = "pickup"
        status_value = "awaiting_pickup"
        if product is not None and product.print_on_demand_enabled:
            method = "print_on_demand"
            status_value = "awaiting_shipment"
        elif order_method == "shipping" and product is not None and product.shipping_enabled:
            method = "shipping"
            status_value = "awaiting_shipment"

        fulfillment = MerchFulfillment(
            order_id=order.id,
            order_item_id=item.id,
            event_id=product.event_id if product and product.event_id else order.event_id,
            host_id=product.host_id if product else order_host_id,
            buyer_user_id=order.buyer_user_id,
            merch_variant_id=variant.id,
            quantity=item.quantity,
            status=status_value,
            fulfillment_method=method,
            pickup_code=_new_pickup_code(db),
            shipping_address_id=getattr(order, "shipping_address_id", None)
            if method == "shipping"
            else None,
            bundle_id=getattr(item, "bundle_id", None),
            pickup_instructions_snapshot=(
                (product.pickup_instructions if product else None) or None
            ),
            pickup_location_label_snapshot=(
                getattr(product, "pickup_location_label", None) if product else None
            ),
            pickup_time_window_snapshot=(
                getattr(product, "pickup_time_window", None) if product else None
            ),
            fulfillment_notes_snapshot=(
                getattr(product, "fulfillment_notes", None) if product else None
            ),
            product_name_snapshot=item.product_name
            or (product.name if product else "Merch"),
            variant_label_snapshot=item.variant_label or variant.label,
        )
        db.add(fulfillment)
        db.flush()

        if method == "pickup":
            from app.merch.qr_pickup import issue_pickup_qr_for_fulfillment

            issue_pickup_qr_for_fulfillment(db, fulfillment)

        if product is not None:
            from app.merch.stock_alerts import evaluate_variant_stock_alerts

            evaluate_variant_stock_alerts(
                db,
                product=product,
                variant=variant,
                previous_available=prev_available,
            )

        bid = getattr(item, "bundle_id", None)
        if bid and bid not in bundle_ids_seen:
            from app.merch.bundles import commit_bundle_sale
            from app.merch.models import MerchBundle

            bundle = db.get(MerchBundle, bid)
            if bundle is not None:
                # Count packs from order: max qty among ticket lines with this bundle
                pack_qty = max(
                    (
                        oi.quantity
                        for oi in order.items
                        if getattr(oi, "bundle_id", None) == bid
                        and oi.ticket_type_id is not None
                    ),
                    default=1,
                )
                commit_bundle_sale(bundle, pack_qty)
            bundle_ids_seen.add(bid)

        _record_fulfillment_event(
            db,
            fulfillment=fulfillment,
            action="created",
            actor_user_id=order.buyer_user_id,
        )
        created.append(fulfillment)
        existing_by_item[item.id] = fulfillment

    db.flush()
    return created


def cancel_fulfillments_for_refunded_order(
    db: Session,
    *,
    order: Order,
    actor_user_id: uuid.UUID | None = None,
) -> list[MerchFulfillment]:
    """Cancel unfulfilled merch; restock only when product.restock_on_refund is true."""
    rows = list(
        db.scalars(
            select(MerchFulfillment).where(
                MerchFulfillment.order_id == order.id,
                MerchFulfillment.status.in_(("awaiting_pickup", "collect_at_stand")),
            )
        )
    )
    for row in rows:
        row.status = "cancelled"
        product = None
        restocked = False
        if row.merch_variant_id:
            variant = db.scalar(
                select(EventMerchVariant)
                .where(EventMerchVariant.id == row.merch_variant_id)
                .with_for_update()
            )
            if variant is not None:
                product = db.get(EventMerchProduct, variant.product_id)
                if product is not None and product.restock_on_refund:
                    from app.merch.service import available_variant_stock
                    from app.merch.stock_alerts import evaluate_variant_stock_alerts

                    prev_available = available_variant_stock(variant)
                    restock_variant_on_refund(variant, row.quantity)
                    restocked = True
                    evaluate_variant_stock_alerts(
                        db,
                        product=product,
                        variant=variant,
                        previous_available=prev_available,
                    )
        _record_fulfillment_event(
            db,
            fulfillment=row,
            action="refunded",
            actor_user_id=actor_user_id or order.buyer_user_id,
        )
        write_audit_log(
            db,
            action="merch.fulfillment_cancel_refund",
            actor_user_id=actor_user_id or order.buyer_user_id,
            resource_type="merch_fulfillment",
            resource_id=str(row.id),
            details={"order_id": str(order.id), "restocked": restocked},
        )
    if rows:
        from app.merch.badges_hook import revoke_merch_badges_for_user
        from app.merch.discounts import reverse_redemption_on_refund
        from app.merch.notifications import notify_buyer_merch_refunded
        from app.merch.revenue import reverse_splits_on_refund

        notify_buyer_merch_refunded(db, order=order, fulfillments=rows)
        reverse_redemption_on_refund(db, order)
        reverse_splits_on_refund(db, order)
        try:
            revoke_merch_badges_for_user(db, order.buyer_user_id)
        except Exception:  # noqa: BLE001 — badge sync must not block refund
            import logging

            logging.getLogger(__name__).exception(
                "merch badge revoke failed for order %s", order.id
            )
    db.flush()
    return rows


def list_host_fulfillments(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    status_filter: str | None = None,
    q: str | None = None,
) -> list[dict]:
    if not can_view_event_merch_fulfillments(db, user, event_id):
        raise HTTPException(status_code=403, detail="Not allowed to view merch fulfillments")

    status_groups = {
        "pending": ("awaiting_pickup",),
        "ready": ("collect_at_stand",),
        "picked_up": ("fulfilled",),
        "cancelled": ("cancelled",),
        "refunded": ("cancelled",),
    }

    stmt = (
        select(MerchFulfillment)
        .where(MerchFulfillment.event_id == event_id)
        .order_by(MerchFulfillment.created_at.desc())
    )
    if status_filter:
        if status_filter in status_groups:
            stmt = stmt.where(MerchFulfillment.status.in_(status_groups[status_filter]))
        else:
            normalized = normalize_fulfillment_status(status_filter)
            stmt = stmt.where(MerchFulfillment.status == normalized)

    rows = list(db.scalars(stmt).all())
    can_reveal = can_reveal_shipping_address(db, user, event_id)
    out = [
        serialize_fulfillment(
            db,
            r,
            include_buyer=True,
            reveal_shipping_address=can_reveal,
        )
        for r in rows
    ]
    if q:
        needle = q.strip().lower()
        out = [
            row
            for row in out
            if needle
            in " ".join(
                str(row.get(k) or "")
                for k in (
                    "pickup_code",
                    "buyer_name",
                    "order_reference",
                    "product_name_snapshot",
                    "variant_label_snapshot",
                )
            ).lower()
        ]
    return out


def add_fulfillment_note(
    db: Session,
    *,
    user: User,
    fulfillment_id: uuid.UUID,
    note: str,
) -> dict:
    row = db.get(MerchFulfillment, fulfillment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fulfillment not found")
    if not can_fulfill_event_merch(db, user, row.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to fulfill merch")
    note_clean = note.strip()
    if len(note_clean) < 2:
        raise HTTPException(status_code=400, detail="Note is too short")
    _record_fulfillment_event(
        db,
        fulfillment=row,
        action="note_added",
        actor_user_id=user.id,
        note=note_clean[:1000],
    )
    write_audit_log(
        db,
        action="merch.fulfillment_note",
        actor_user_id=user.id,
        resource_type="merch_fulfillment",
        resource_id=str(row.id),
        details={"note": note_clean[:200]},
    )
    db.commit()
    db.refresh(row)
    return serialize_fulfillment(
        db,
        row,
        include_buyer=True,
        reveal_shipping_address=can_reveal_shipping_address(db, user, row.event_id),
    )


def get_buyer_fulfillment(
    db: Session, *, user: User, item_id: uuid.UUID
) -> dict:
    """Resolve a buyer merch row by fulfillment id or order_item id."""
    rows = list_buyer_fulfillments(db, user=user)
    for row in rows:
        if str(row.get("id")) == str(item_id) or str(row.get("order_item_id")) == str(
            item_id
        ):
            return row
    raise HTTPException(status_code=404, detail="Merch item not found")


def resolve_host_fulfillment_id(
    db: Session, *, user: User, item_id: uuid.UUID
) -> uuid.UUID:
    """Resolve fulfillment id from fulfillment id or order_item id for host actions."""
    row = db.get(MerchFulfillment, item_id)
    if row is None:
        row = db.scalar(
            select(MerchFulfillment).where(MerchFulfillment.order_item_id == item_id)
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Merch order item not found")
    if not can_view_event_merch_fulfillments(db, user, row.event_id):
        raise HTTPException(status_code=403, detail="Not allowed")
    return row.id


def list_buyer_fulfillments(db: Session, *, user: User) -> list[dict]:
    """Paid fulfillments plus unpaid merch lines (pending payment)."""
    rows = list(
        db.scalars(
            select(MerchFulfillment)
            .where(MerchFulfillment.buyer_user_id == user.id)
            .order_by(MerchFulfillment.created_at.desc())
        ).all()
    )
    out = [serialize_fulfillment(db, r) for r in rows]
    fulfilled_item_ids = {str(r.order_item_id) for r in rows}

    pending_orders = list(
        db.scalars(
            select(Order)
            .where(
                Order.buyer_user_id == user.id,
                Order.status.in_(("pending", "failed")),
            )
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
        ).all()
    )
    for order in pending_orders:
        event = db.get(Event, order.event_id)
        host = db.get(Host, event.host_id) if event else None
        for item in order.items or []:
            kind = getattr(item, "item_kind", None) or (
                ITEM_KIND_MERCH if item.merch_variant_id else "ticket"
            )
            if kind != ITEM_KIND_MERCH or item.merch_variant_id is None:
                continue
            if str(item.id) in fulfilled_item_ids:
                continue
            product = None
            if item.merch_product_id:
                product = db.get(EventMerchProduct, item.merch_product_id)
            elif item.merch_variant_id:
                variant = db.get(EventMerchVariant, item.merch_variant_id)
                if variant is not None:
                    product = db.get(EventMerchProduct, variant.product_id)
            if event is None:
                continue
            # Pre-payment: same public-safe pickup copy as the catalog.
            pickup = (
                public_pickup_fields(product, event)
                if product is not None
                else {
                    "pickup_instructions": None,
                    "pickup_location_label": None,
                    "pickup_time_window": None,
                    "fulfillment_notes": None,
                }
            )
            pending_method = getattr(order, "fulfillment_method", None) or "pickup"
            shipping_hint = None
            if pending_method == "shipping" and getattr(
                order, "shipping_address_id", None
            ):
                from app.merch.models import MerchShippingAddress
                from app.merch.shipping import public_shipping_hint

                addr = db.get(MerchShippingAddress, order.shipping_address_id)
                shipping_hint = public_shipping_hint(addr)
            out.append(
                {
                    "id": item.id,
                    "order_id": order.id,
                    "order_item_id": item.id,
                    "event_id": order.event_id,
                    "host_id": event.host_id,
                    "buyer_user_id": order.buyer_user_id,
                    "merch_variant_id": item.merch_variant_id,
                    "quantity": item.quantity,
                    "status": "pending_payment",
                    "display_status": "pending_payment",
                    "fulfillment_method": pending_method,
                    "pickup_code": "",
                    "pickup_instructions_snapshot": pickup["pickup_instructions"],
                    "pickup_location_label": pickup["pickup_location_label"],
                    "pickup_time_window": pickup["pickup_time_window"],
                    "fulfillment_notes": None,
                    "product_name_snapshot": item.product_name
                    or (product.name if product else "Merch"),
                    "variant_label_snapshot": item.variant_label or "Standard",
                    "product_image_url": product.image_url if product else None,
                    "tracking_number": None,
                    "carrier": None,
                    "shipping_address": shipping_hint,
                    "fulfilled_at": None,
                    "fulfilled_by_user_id": None,
                    "created_at": order.created_at,
                    "updated_at": order.updated_at,
                    "event_title": event.title if event else None,
                    "event_slug": event.slug if event else None,
                    "host_name": host.display_name if host else None,
                    "host_slug": host.slug if host else None,
                    "order_reference": order.reference,
                    "order_status": order.status,
                    "buyer_email": None,
                    "buyer_name": None,
                    "has_ticket": None,
                    "ticket_count": None,
                }
            )

    out.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return out


def list_fulfillments_for_order(
    db: Session, order_id: uuid.UUID
) -> list[MerchFulfillment]:
    return list(
        db.scalars(select(MerchFulfillment).where(MerchFulfillment.order_id == order_id))
    )


def update_fulfillment_status(
    db: Session,
    *,
    user: User,
    fulfillment_id: uuid.UUID,
    status: str,
) -> dict:
    row = db.get(MerchFulfillment, fulfillment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fulfillment not found")
    if not can_fulfill_event_merch(db, user, row.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to fulfill merch")
    if row.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Cancelled or refunded merch cannot be updated",
        )
    next_status = normalize_fulfillment_status(status)
    if next_status == "fulfilled":
        _assert_pickup_allowed(db, row)

    allowed = {
        "awaiting_pickup",
        "collect_at_stand",
        "awaiting_shipment",
        "packed",
        "shipped",
        "delivered",
        "fulfilled",
    }
    if next_status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid fulfillment status")
    if row.status == "fulfilled" and next_status != "fulfilled":
        raise HTTPException(
            status_code=400,
            detail="Picked up merch cannot change status",
        )

    previous_status = row.status
    row.status = next_status
    now = datetime.now(UTC)
    if next_status == "fulfilled":
        row.fulfilled_at = now
        row.fulfilled_by_user_id = user.id
        event_action = "picked_up"
    elif next_status == "collect_at_stand":
        row.fulfilled_at = None
        row.fulfilled_by_user_id = None
        event_action = "ready_for_pickup"
    elif next_status == "shipped":
        row.shipped_at = now
        event_action = "shipped"
    elif next_status == "delivered":
        row.delivered_at = now
        row.fulfilled_at = now
        row.fulfilled_by_user_id = user.id
        event_action = "delivered"
    elif next_status == "packed":
        event_action = "packed"
    else:
        if next_status == "awaiting_pickup":
            row.fulfilled_at = None
            row.fulfilled_by_user_id = None
        event_action = "status_updated"

    _record_fulfillment_event(
        db,
        fulfillment=row,
        action=event_action,
        actor_user_id=user.id,
    )
    write_audit_log(
        db,
        action="merch.fulfillment_update",
        actor_user_id=user.id,
        resource_type="merch_fulfillment",
        resource_id=str(row.id),
        details={
            "status": next_status,
            "event_id": str(row.event_id),
            "pickup_code": row.pickup_code,
            "staff_name": user.full_name,
        },
    )
    if next_status == "fulfilled" and previous_status != "fulfilled":
        from app.analytics.trusted import emit_merch_picked_up
        from app.merch.models import EventMerchVariant
        from app.merch.notifications import (
            notify_buyer_merch_picked_up,
            notify_host_merch_pickup,
        )

        variant = db.get(EventMerchVariant, row.merch_variant_id)
        emit_merch_picked_up(
            db,
            fulfillment_id=row.id,
            event_id=row.event_id,
            host_id=row.host_id,
            actor_user_id=user.id,
            merch_product_id=variant.product_id if variant else None,
            merch_variant_id=row.merch_variant_id,
            quantity=row.quantity,
            fulfillment_method=row.fulfillment_method,
        )
        notify_buyer_merch_picked_up(db, fulfillment=row)
        notify_host_merch_pickup(db, fulfillment=row)
    elif next_status == "shipped" and previous_status != "shipped":
        from app.analytics.trusted import emit_merch_shipped
        from app.merch.models import EventMerchVariant

        variant = db.get(EventMerchVariant, row.merch_variant_id)
        emit_merch_shipped(
            db,
            fulfillment_id=row.id,
            event_id=row.event_id,
            host_id=row.host_id,
            actor_user_id=user.id,
            merch_product_id=variant.product_id if variant else None,
            merch_variant_id=row.merch_variant_id,
            quantity=row.quantity,
        )
    elif next_status == "delivered" and previous_status != "delivered":
        from app.analytics.trusted import emit_merch_delivered
        from app.merch.models import EventMerchVariant

        variant = db.get(EventMerchVariant, row.merch_variant_id)
        emit_merch_delivered(
            db,
            fulfillment_id=row.id,
            event_id=row.event_id,
            host_id=row.host_id,
            actor_user_id=user.id,
            merch_product_id=variant.product_id if variant else None,
            merch_variant_id=row.merch_variant_id,
            quantity=row.quantity,
        )
    elif (
        next_status == "collect_at_stand"
        and previous_status != "collect_at_stand"
    ):
        from app.merch.notifications import notify_buyer_merch_ready

        notify_buyer_merch_ready(db, fulfillment=row)
    db.commit()
    db.refresh(row)
    return serialize_fulfillment(
        db,
        row,
        include_buyer=True,
        reveal_shipping_address=can_reveal_shipping_address(db, user, row.event_id),
    )


def mark_fulfilled(
    db: Session,
    *,
    user: User,
    fulfillment_id: uuid.UUID,
) -> dict:
    row = db.get(MerchFulfillment, fulfillment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fulfillment not found")
    if not can_fulfill_event_merch(db, user, row.event_id):
        raise HTTPException(status_code=403, detail="Not allowed to fulfill merch")
    _assert_pickup_allowed(db, row)
    return update_fulfillment_status(
        db, user=user, fulfillment_id=fulfillment_id, status="fulfilled"
    )
