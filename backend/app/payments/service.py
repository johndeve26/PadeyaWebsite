"""Order creation, inventory reservation, and checkout initialization."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.events.models import Event, EventCheckoutQuestion, TicketType
from app.payments.capacity import (
    assert_event_capacity_allows,
    lock_event_for_capacity,
    seats_for_units,
)
from app.payments.models import Order, OrderCheckoutAnswer, OrderItem, Payment
from app.payments.paystack import PaystackError, initialize_transaction, verify_transaction
from app.payments.reservations import (
    assert_ticket_sales_window,
    compute_reservation_expires_at,
    ensure_pending_reservation_active,
)
from app.payments.schemas import CheckoutAnswerIn, OrderCreate
from app.tickets.service import issue_tickets_for_paid_order, send_ticket_email
from app.users.models import User

settings = get_settings()


def _buyer_fee_breakdown_for_order(db: Session, order_id: uuid.UUID) -> list[dict]:
    """Buyer-visible fee lines only — never expose host commercial terms."""
    from app.finance.fees.models import OrderFeeSnapshot
    from app.finance.fees.money import minor_to_major

    rows = db.scalars(
        select(OrderFeeSnapshot)
        .where(
            OrderFeeSnapshot.order_id == order_id,
            OrderFeeSnapshot.payer == "buyer",
        )
        .order_by(OrderFeeSnapshot.created_at.asc())
    ).all()
    out: list[dict] = []
    for row in rows:
        out.append(
            {
                "fee_key": row.fee_key,
                "label": row.label,
                "payer": row.payer,
                "amount": minor_to_major(int(row.amount), currency=row.currency),
                "currency": row.currency,
            }
        )
    return out


def _new_reference() -> str:
    return f"PDY-{secrets.token_hex(8).upper()}"


def normalize_order_reference(raw: str) -> str:
    """Strip whitespace and normalize PDY- references for lookup."""
    cleaned = "".join(str(raw or "").split())
    if not cleaned:
        return ""
    upper = cleaned.upper()
    if upper.startswith("PDY-"):
        return "PDY-" + upper[4:]
    return upper


def _available(tt: TicketType) -> int:
    return max(0, tt.quantity - tt.quantity_sold - tt.quantity_reserved)


def _normalize_answer_value(value: str | list[str]) -> str:
    if isinstance(value, list):
        parts = [str(v).strip() for v in value if str(v).strip()]
        return ", ".join(parts)
    return str(value or "").strip()


def _validate_checkout_answers(
    questions: list[EventCheckoutQuestion],
    answers: list[CheckoutAnswerIn] | None,
) -> list[tuple[EventCheckoutQuestion, str]]:
    """Validate buyer answers against event questions. Empty questions → no-op."""
    if not questions:
        return []

    provided = {a.question_id: a for a in (answers or [])}
    stored: list[tuple[EventCheckoutQuestion, str]] = []

    for question in sorted(questions, key=lambda q: q.sort_order):
        answer = provided.get(question.id)
        raw = _normalize_answer_value(answer.value) if answer else ""
        if question.required and not raw:
            raise HTTPException(
                status_code=400,
                detail=f"Answer required: {question.label}",
            )
        if not raw:
            continue

        options = list(question.options or [])
        if question.type == "dropdown":
            if options and raw not in options:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid option for: {question.label}",
                )
        elif question.type == "checkbox":
            selected = [p.strip() for p in raw.split(",") if p.strip()]
            if options and any(s not in options for s in selected):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid option for: {question.label}",
                )
            raw = ", ".join(selected)
        elif question.type == "email":
            if "@" not in raw or "." not in raw.split("@")[-1]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Enter a valid email for: {question.label}",
                )
        elif question.type == "phone":
            digits = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
            if len(digits) < 7:
                raise HTTPException(
                    status_code=400,
                    detail=f"Enter a valid phone for: {question.label}",
                )

        stored.append((question, raw))

    return stored


def serialize_order(db: Session, order: Order) -> dict:
    from app.hosts.models import Host
    from app.merch.fulfillment import list_fulfillments_for_order

    event = db.get(Event, order.event_id) if order.event_id is not None else None
    host = (
        db.get(Host, event.host_id)
        if event is not None
        else (
            db.get(Host, order.host_id)
            if getattr(order, "host_id", None) is not None
            else None
        )
    )
    fulfillments = list_fulfillments_for_order(db, order_id=order.id)
    by_item = {str(f.order_item_id): f for f in fulfillments}

    items_out: list[dict] = []
    for item in order.items:
        row = {
            "id": item.id,
            "item_kind": getattr(item, "item_kind", None) or "ticket",
            "ticket_type_id": item.ticket_type_id,
            "ticket_type_name": item.ticket_type_name,
            "merch_product_id": getattr(item, "merch_product_id", None),
            "merch_variant_id": getattr(item, "merch_variant_id", None),
            "bundle_id": getattr(item, "bundle_id", None),
            "product_name": getattr(item, "product_name", None),
            "variant_label": getattr(item, "variant_label", None),
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": item.line_total,
            "fulfillment_status": None,
            "pickup_code": None,
            "pickup_instructions": None,
        }
        fulfillment = by_item.get(str(item.id))
        if fulfillment is not None:
            row["fulfillment_status"] = fulfillment.status
            row["pickup_code"] = fulfillment.pickup_code
            row["pickup_instructions"] = fulfillment.pickup_instructions_snapshot
        items_out.append(row)

    return {
        "id": order.id,
        "reference": order.reference,
        "event_id": order.event_id,
        "status": order.status,
        "currency": order.currency,
        "subtotal_amount": order.subtotal_amount,
        "discount_amount": order.discount_amount or Decimal("0"),
        "merch_discount_amount": getattr(order, "merch_discount_amount", None)
        or Decimal("0"),
        "shipping_amount": getattr(order, "shipping_amount", None) or Decimal("0"),
        "buyer_fee_total": getattr(order, "buyer_fee_total", None) or Decimal("0"),
        "host_fee_total": getattr(order, "host_fee_total", None) or Decimal("0"),
        "processing_fee_total": getattr(order, "processing_fee_total", None)
        or Decimal("0"),
        "platform_revenue_total": getattr(order, "platform_revenue_total", None)
        or Decimal("0"),
        "host_net_estimate": getattr(order, "host_net_estimate", None)
        or Decimal("0"),
        "total_amount": order.total_amount,
        "discount_total": (
            Decimal(order.discount_amount or 0)
            + Decimal(getattr(order, "merch_discount_amount", None) or 0)
        ),
        "final_total": order.total_amount,
        "fee_breakdown": _buyer_fee_breakdown_for_order(db, order.id),
        "promo_code_snapshot": order.promo_code_snapshot,
        "merch_discount_code_snapshot": getattr(
            order, "merch_discount_code_snapshot", None
        ),
        "referral_code": order.referral_code,
        "fulfillment_method": getattr(order, "fulfillment_method", None),
        "buyer_email": order.buyer_email,
        "buyer_name": order.buyer_name,
        "is_guest_checkout": bool(getattr(order, "is_guest_checkout", False)),
        "guest_buyer_email": getattr(order, "guest_buyer_email", None),
        "purchase_mode": getattr(order, "purchase_mode", None) or "self",
        "is_gift": bool(getattr(order, "is_gift", False)),
        "purchased_for_someone_else": bool(
            getattr(order, "purchased_for_someone_else", False)
        ),
        "gift_message": getattr(order, "gift_message", None),
        "send_ticket_to_recipient": bool(
            getattr(order, "send_ticket_to_recipient", False)
        ),
        "keep_buyer_copy": bool(getattr(order, "keep_buyer_copy", True)),
        "recipient_name": getattr(order, "recipient_name", None),
        "recipient_email": getattr(order, "recipient_email", None),
        "recipient_phone": getattr(order, "recipient_phone", None),
        "claimed_at": getattr(order, "claimed_at", None),
        "created_at": order.created_at,
        "paid_at": order.paid_at,
        "archived_at": order.archived_at,
        "reservation_expires_at": getattr(order, "reservation_expires_at", None),
        "items": items_out,
        "payments": order.payments,
        "checkout_answers": getattr(order, "checkout_answers", None) or [],
        "attendees": [
            {
                "id": a.id,
                "ticket_type_id": a.ticket_type_id,
                "unit_index": a.unit_index,
                "attendee_name": a.attendee_name,
                "attendee_email": a.attendee_email,
                "attendee_phone": a.attendee_phone,
                "delivery_email": a.delivery_email,
                "delivery_phone": a.delivery_phone,
            }
            for a in (getattr(order, "attendees", None) or [])
        ],
        "event_title": event.title if event else None,
        "event_slug": event.slug if event else None,
        "host_id": host.id if host else None,
        "host_name": host.display_name if host else None,
        "host_slug": host.slug if host else None,
        "merch_fulfillments": [
            {
                "id": f.id,
                "order_item_id": f.order_item_id,
                "status": f.status,
                "pickup_code": f.pickup_code,
                "pickup_instructions_snapshot": f.pickup_instructions_snapshot,
                "product_name_snapshot": f.product_name_snapshot,
                "variant_label_snapshot": f.variant_label_snapshot,
                "quantity": f.quantity,
                "fulfilled_at": f.fulfilled_at,
            }
            for f in fulfillments
        ],
    }


def get_order_by_id(db: Session, order_id: uuid.UUID) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.checkout_answers),
            selectinload(Order.attendees),
        )
    )


def get_order_by_reference(db: Session, reference: str) -> Order | None:
    normalized = normalize_order_reference(reference)
    if not normalized:
        return None
    return db.scalar(
        select(Order)
        .where(func.upper(Order.reference) == normalized)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
            selectinload(Order.checkout_answers),
            selectinload(Order.attendees),
        )
    )


def create_order(
    db: Session,
    *,
    user: User | None,
    payload: OrderCreate,
    client_ip: str | None = None,
) -> Order:
    if payload.event_id is None and payload.host_id is not None:
        return _create_host_shop_merch_order(
            db, user=user, payload=payload, client_ip=client_ip
        )
    return _create_event_order(db, user=user, payload=payload, client_ip=client_ip)


def _create_host_shop_merch_order(
    db: Session,
    *,
    user: User | None,
    payload: OrderCreate,
    client_ip: str | None = None,
) -> Order:
    """Standalone host-shop merch checkout (no event_id). Tickets/bundles not allowed."""
    from decimal import Decimal

    from app.hosts.fan_self_abuse import assert_owner_not_buying_own_host
    from app.hosts.models import Host
    from app.merch.access import assert_buyer_can_purchase
    from app.merch.constants import ITEM_KIND_BUNDLE, ITEM_KIND_MERCH, ITEM_KIND_TICKET
    from app.merch.discounts import attach_pending_redemption, validate_merch_discount
    from app.merch.service import (
        assert_variant_quantity_ok,
        buyer_prior_product_quantity,
        effective_variant_price,
        load_sellable_host_variant,
        reserve_variant_quantity,
    )
    from app.merch.shipping import compute_shipping_fee, create_shipping_address
    from app.payments.attendees import assert_checkout_rate_limit
    from app.payments.guest import (
        assert_guest_checkout_rate_limit,
        assert_guest_email_allowed_for_checkout,
        validate_guest_buyer_fields,
    )
    from app.users.restrictions import assert_can_buy_merch, assert_can_checkout

    host_id = payload.host_id
    assert host_id is not None
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=400, detail="Host shop is not available")

    for item in payload.items:
        kind = item.item_kind or ITEM_KIND_TICKET
        if kind != ITEM_KIND_MERCH:
            raise HTTPException(
                status_code=400,
                detail="Host shop checkout supports merch items only",
            )

    is_guest = user is None
    if user is not None:
        assert_can_checkout(db, user)
        assert_checkout_rate_limit(db, user_id=user.id)
        assert_can_buy_merch(db, user)
        assert_owner_not_buying_own_host(db, user_id=user.id, host_id=host.id)
        buyer_name = user.full_name or user.email.split("@")[0]
        buyer_email = user.email
        buyer_phone = None
    else:
        raise HTTPException(
            status_code=400,
            detail="Log in to buy host shop merch.",
        )

    buyer_uid = user.id if user is not None else None
    qty_by_variant: dict[uuid.UUID, int] = {}
    for item in payload.items:
        assert item.merch_variant_id is not None
        qty_by_variant[item.merch_variant_id] = (
            qty_by_variant.get(item.merch_variant_id, 0) + item.quantity
        )
    if not qty_by_variant:
        raise HTTPException(status_code=400, detail="Order must include at least one item")

    merch_line_items: list[tuple] = []
    qty_by_product: dict[uuid.UUID, int] = {}
    subtotal = Decimal("0")
    for variant_id, quantity in qty_by_variant.items():
        product, variant = load_sellable_host_variant(
            db,
            host_id=host.id,
            variant_id=variant_id,
            for_update=True,
            buyer_user_id=buyer_uid,
        )
        assert_buyer_can_purchase(db, product=product, buyer_user_id=buyer_uid)
        qty_by_product[product.id] = qty_by_product.get(product.id, 0) + quantity
        assert_variant_quantity_ok(
            product=product,
            variant=variant,
            quantity=quantity,
            product_order_quantity=qty_by_product[product.id],
        )
        max_buyer = getattr(product, "max_per_buyer", None)
        if max_buyer is not None:
            prior = buyer_prior_product_quantity(
                db, buyer_user_id=buyer_uid, product_id=product.id
            )
            if prior + qty_by_product[product.id] > max_buyer:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Quantity for {product.name} exceeds the per-buyer limit "
                        f"({max_buyer})"
                    ),
                )
        unit = effective_variant_price(product, variant)
        reserve_variant_quantity(variant, quantity)
        merch_line_items.append((product, variant, quantity, unit, None, False))
        subtotal += unit * quantity

    fulfillment_method = payload.fulfillment_method or "pickup"
    needs_shipping = fulfillment_method == "shipping"
    shipping_amount = Decimal("0")
    if needs_shipping:
        if payload.shipping_address is None:
            raise HTTPException(status_code=400, detail="Shipping address is required")
        shipping_amount = compute_shipping_fee(
            db,
            host_id=host.id,
            event_id=None,
            country=payload.shipping_address.country,
            state=payload.shipping_address.state,
            city=payload.shipping_address.city,
        )

    merch_discount = Decimal("0")
    merch_discount_code_id = None
    merch_discount_snapshot = None
    if payload.merch_discount_code and user is not None:
        merch_lines = [
            (product, unit * quantity, False)
            for product, _variant, quantity, unit, _b, _fb in merch_line_items
        ]
        code_row, merch_discount, shipping_amount = validate_merch_discount(
            db,
            code_str=payload.merch_discount_code,
            host_id=host.id,
            buyer=user,
            merch_lines=merch_lines,
            ticket_subtotal=Decimal("0"),
            shipping_amount=shipping_amount,
        )
        merch_discount_code_id = code_row.id
        merch_discount_snapshot = code_row.code

    from app.finance.fees.checkout_fees import (
        calculate_checkout_fees,
        persist_order_fee_result,
    )

    fee_result = calculate_checkout_fees(
        db,
        host_id=host.id,
        ticket_subtotal=Decimal("0"),
        merch_subtotal=subtotal,
        ticket_discount=Decimal("0"),
        merch_discount=merch_discount,
        shipping_amount=shipping_amount,
        currency="NGN",
    )
    total = fee_result.final_total
    reference = _new_reference()
    while db.scalar(select(Order.id).where(Order.reference == reference)):
        reference = _new_reference()

    order = Order(
        reference=reference,
        buyer_user_id=buyer_uid,
        event_id=None,
        host_id=host.id,
        status="pending",
        currency="NGN",
        subtotal_amount=subtotal,
        discount_amount=Decimal("0"),
        merch_discount_amount=merch_discount,
        shipping_amount=shipping_amount,
        buyer_fee_total=fee_result.buyer_fee_total,
        host_fee_total=fee_result.host_fee_total,
        processing_fee_total=fee_result.processing_fee_total,
        platform_revenue_total=fee_result.platform_revenue_total,
        host_net_estimate=fee_result.host_net_estimate,
        total_amount=total,
        fulfillment_method=fulfillment_method,
        buyer_email=buyer_email,
        buyer_name=buyer_name,
        is_guest_checkout=False,
        purchase_mode="self",
        is_gift=False,
        purchased_for_someone_else=False,
        send_ticket_to_recipient=False,
        reservation_expires_at=compute_reservation_expires_at(),
    )
    if merch_discount_code_id:
        order.merch_discount_code_id = merch_discount_code_id
        order.merch_discount_code_snapshot = merch_discount_snapshot
    db.add(order)
    db.flush()
    persist_order_fee_result(
        db, order_id=order.id, host_id=host.id, result=fee_result
    )
    if needs_shipping and payload.shipping_address is not None:
        create_shipping_address(
            db,
            order=order,
            buyer=user,
            recipient_name=payload.shipping_address.recipient_name,
            phone=payload.shipping_address.phone,
            line1=payload.shipping_address.line1,
            line2=payload.shipping_address.line2,
            city=payload.shipping_address.city,
            state=payload.shipping_address.state,
            country=payload.shipping_address.country,
            postal_code=payload.shipping_address.postal_code,
            notes=payload.shipping_address.notes,
        )
    if merch_discount_code_id and user is not None:
        from app.merch.models import MerchDiscountCode

        code_obj = db.get(MerchDiscountCode, merch_discount_code_id)
        if code_obj is not None:
            attach_pending_redemption(
                db,
                order=order,
                code=code_obj,
                buyer=user,
                discount_amount=merch_discount,
            )

    for product, variant, quantity, unit, _bundle_id, _from_bundle in merch_line_items:
        db.add(
            OrderItem(
                order_id=order.id,
                item_kind=ITEM_KIND_MERCH,
                merch_product_id=product.id,
                merch_variant_id=variant.id,
                quantity=quantity,
                unit_price=unit,
                line_total=unit * quantity,
                product_name=product.name,
                variant_label=variant.label,
            )
        )
    db.commit()
    loaded = get_order_by_id(db, order.id)
    assert loaded is not None
    return loaded


def _create_event_order(
    db: Session,
    *,
    user: User | None,
    payload: OrderCreate,
    client_ip: str | None = None,
) -> Order:
    from app.payments.attendees import (
        assert_checkout_rate_limit,
        persist_order_attendees,
        resolve_attendees_for_order,
    )
    from app.payments.guest import (
        assert_guest_checkout_rate_limit,
        assert_guest_email_allowed_for_checkout,
        validate_guest_buyer_fields,
    )
    from app.users.restrictions import assert_can_buy_merch, assert_can_buy_tickets, assert_can_checkout
    from app.merch.constants import ITEM_KIND_BUNDLE, ITEM_KIND_MERCH, ITEM_KIND_TICKET

    is_guest = user is None
    has_tickets = any(
        (item.item_kind or ITEM_KIND_TICKET) == ITEM_KIND_TICKET for item in payload.items
    )
    has_merch = any(
        (item.item_kind or ITEM_KIND_TICKET) in {ITEM_KIND_MERCH, ITEM_KIND_BUNDLE}
        for item in payload.items
    )

    if user is not None:
        assert_can_checkout(db, user)
        assert_checkout_rate_limit(db, user_id=user.id)
        if has_tickets:
            assert_can_buy_tickets(db, user)
        if has_merch:
            assert_can_buy_merch(db, user)
        buyer_name = user.full_name or user.email.split("@")[0]
        buyer_email = user.email
        buyer_phone = None
    else:
        buyer_name, buyer_email, buyer_phone = validate_guest_buyer_fields(
            name=payload.guest_buyer_name,
            email=payload.guest_buyer_email,
            phone=payload.guest_buyer_phone,
        )
        assert_guest_checkout_rate_limit(
            db, email=buyer_email, ip_address=client_ip
        )

    event = db.scalar(
        select(Event)
        .where(Event.id == payload.event_id)
        .options(selectinload(Event.checkout_questions))
    )
    if event is None:
        raise HTTPException(status_code=400, detail="Event is not available for purchase")

    from app.hosts.fan_self_abuse import assert_owner_not_buying_own_host

    if user is not None:
        # Production checkout only — host owner cannot buy own-host tickets/merch.
        assert_owner_not_buying_own_host(
            db, user_id=user.id, host_id=event.host_id
        )
    else:
        # Detect own-host / restricted bypass via matching email (no auto-login).
        assert_guest_email_allowed_for_checkout(
            db,
            email=buyer_email,
            host_id=event.host_id,
            has_tickets=has_tickets,
            has_merch=has_merch,
        )

    from app.merch.access import assert_buyer_can_purchase
    from app.merch.bundles import (
        buyer_prior_bundle_quantity,
        expand_bundle_allocation,
        load_active_bundle,
        reserve_bundle_pack,
    )
    from app.merch.constants import ITEM_KIND_BUNDLE, ITEM_KIND_MERCH, ITEM_KIND_TICKET
    from app.merch.discounts import (
        attach_pending_redemption,
        validate_merch_discount,
    )
    from app.merch.service import (
        assert_event_host_sellable,
        assert_variant_quantity_ok,
        buyer_has_active_event_ticket,
        buyer_prior_product_quantity,
        effective_variant_price,
        load_sellable_variant,
        reserve_variant_quantity,
    )
    from app.merch.shipping import compute_shipping_fee, create_shipping_address

    # Aggregate quantities per ticket type / merch variant / bundle
    qty_by_type: dict[uuid.UUID, int] = {}
    qty_by_variant: dict[uuid.UUID, int] = {}
    qty_by_bundle: dict[uuid.UUID, int] = {}
    for item in payload.items:
        kind = item.item_kind or ITEM_KIND_TICKET
        if kind == ITEM_KIND_MERCH:
            assert item.merch_variant_id is not None
            qty_by_variant[item.merch_variant_id] = (
                qty_by_variant.get(item.merch_variant_id, 0) + item.quantity
            )
        elif kind == ITEM_KIND_BUNDLE:
            assert item.bundle_id is not None
            qty_by_bundle[item.bundle_id] = (
                qty_by_bundle.get(item.bundle_id, 0) + item.quantity
            )
        else:
            assert item.ticket_type_id is not None
            qty_by_type[item.ticket_type_id] = (
                qty_by_type.get(item.ticket_type_id, 0) + item.quantity
            )

    if not qty_by_type and not qty_by_variant and not qty_by_bundle:
        raise HTTPException(status_code=400, detail="Order must include at least one item")

    if is_guest:
        from app.payments.checkout_account import assert_no_existing_account_for_email_checkout

        assert_no_existing_account_for_email_checkout(db, email=buyer_email)

    buyer_uid = user.id if user is not None else None

    # Completed events: merch/bundle-only (post-event drops). Tickets still require published.
    merch_only_order = bool(qty_by_variant or qty_by_bundle) and not qty_by_type
    if event.status == "published":
        pass
    elif event.status == "completed" and merch_only_order:
        pass
    else:
        raise HTTPException(status_code=400, detail="Event is not available for purchase")

    active_questions = [
        q
        for q in list(event.checkout_questions or [])
        if getattr(q, "status", "active") == "active"
    ]
    validated_answers = _validate_checkout_answers(
        active_questions,
        payload.checkout_answers,
    )

    has_existing_ticket = False
    if (qty_by_variant or qty_by_bundle) and not qty_by_type and not qty_by_bundle:
        has_existing_ticket = (
            buyer_has_active_event_ticket(
                db, buyer_user_id=buyer_uid, event_id=event.id
            )
            if buyer_uid is not None
            else False
        )
        if not bool(getattr(event, "allow_merch_only_checkout", False)) and not (
            has_existing_ticket
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "This event does not allow merch-only checkout. "
                    "Add a ticket, use an existing ticket for this event, "
                    "or ask the host to enable merch-only sales."
                ),
            )

    if qty_by_variant or qty_by_bundle:
        assert_event_host_sellable(db, event=event)

    # ticket_line_items: (TicketType, qty, unit_price, bundle_id|None)
    ticket_line_items: list[tuple[TicketType, int, Decimal, uuid.UUID | None]] = []
    # merch_line_items: (product, variant, qty, unit, bundle_id|None, from_bundle)
    merch_line_items: list[tuple[object, object, int, Decimal, uuid.UUID | None, bool]] = []
    subtotal = Decimal("0.00")

    # Optional venue hard cap — lock event before tier reservations when set.
    capacity_locked_event: Event | None = None
    if getattr(event, "capacity", None) is not None and (qty_by_type or qty_by_bundle):
        capacity_locked_event = lock_event_for_capacity(db, event.id)
        event = capacity_locked_event

    for ticket_type_id, quantity in qty_by_type.items():
        tt = db.scalar(
            select(TicketType)
            .where(
                TicketType.id == ticket_type_id,
                TicketType.event_id == event.id,
            )
            .with_for_update()
        )
        if tt is None:
            raise HTTPException(status_code=400, detail="Invalid ticket type for event")
        if tt.status != "active" or tt.visibility == "hidden":
            raise HTTPException(status_code=400, detail=f"Ticket type {tt.name} is unavailable")
        assert_ticket_sales_window(tt)
        if quantity < tt.min_per_order or quantity > tt.max_per_order:
            raise HTTPException(
                status_code=400,
                detail=f"Quantity for {tt.name} must be between {tt.min_per_order} and {tt.max_per_order}",
            )
        if _available(tt) < quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Not enough tickets available for {tt.name}",
            )
        assert_event_capacity_allows(
            db, event=event, additional_seats=seats_for_units(tt, quantity)
        )
        tt.quantity_reserved += quantity
        unit = Decimal(tt.price)
        ticket_line_items.append((tt, quantity, unit, None))
        subtotal += unit * quantity

    # Expand bundles into ticket + merch lines (allocated prices)
    for bundle_id, pack_qty in qty_by_bundle.items():
        bundle = load_active_bundle(
            db, event_id=event.id, bundle_id=bundle_id, for_update=True
        )
        if bundle.max_per_buyer is not None:
            prior = buyer_prior_bundle_quantity(
                db, buyer_user_id=buyer_uid, bundle_id=bundle.id
            )
            if prior + pack_qty > int(bundle.max_per_buyer):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Quantity for {bundle.name} exceeds the per-buyer limit "
                        f"({bundle.max_per_buyer})"
                    ),
                )
        reserve_bundle_pack(bundle, pack_qty)
        b_tickets, b_merch, pack_total = expand_bundle_allocation(
            db, bundle=bundle, quantity=pack_qty
        )
        for tt, quantity, unit in b_tickets:
            # expand_bundle_allocation locked + validated inventory
            assert_ticket_sales_window(tt)
            assert_event_capacity_allows(
                db, event=event, additional_seats=seats_for_units(tt, quantity)
            )
            tt.quantity_reserved += quantity
            ticket_line_items.append((tt, quantity, unit, bundle.id))
        for product, variant, quantity, unit in b_merch:
            assert_buyer_can_purchase(
                db,
                product=product,
                buyer_user_id=buyer_uid,
                has_ticket_cover=True,
            )
            reserve_variant_quantity(variant, quantity)
            from app.merch.stock_alerts import evaluate_variant_stock_alerts

            evaluate_variant_stock_alerts(db, product=product, variant=variant)
            merch_line_items.append((product, variant, quantity, unit, bundle.id, True))
        subtotal += pack_total

    # Resolve a-la-carte merch lines
    resolved_merch: list[tuple[object, object, int]] = []
    qty_by_product: dict[uuid.UUID, int] = {}
    for variant_id, quantity in qty_by_variant.items():
        product, variant = load_sellable_variant(
            db,
            event_id=event.id,
            variant_id=variant_id,
            for_update=True,
            buyer_user_id=buyer_uid,
        )
        resolved_merch.append((product, variant, quantity))
        qty_by_product[product.id] = qty_by_product.get(product.id, 0) + quantity

    ticket_cover = bool(qty_by_type) or bool(qty_by_bundle) or has_existing_ticket
    if not ticket_cover and qty_by_variant:
        ticket_cover = buyer_has_active_event_ticket(
            db, buyer_user_id=buyer_uid, event_id=event.id
        )

    for product, variant, quantity in resolved_merch:
        assert_buyer_can_purchase(
            db,
            product=product,
            buyer_user_id=buyer_uid,
            has_ticket_cover=ticket_cover,
        )
        if bool(getattr(product, "requires_ticket", False)) and not ticket_cover:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{product.name} requires a ticket for this event "
                    "(buy one in this order or use an existing ticket)."
                ),
            )
        product_qty = qty_by_product[product.id]
        assert_variant_quantity_ok(
            product=product,
            variant=variant,
            quantity=quantity,
            product_order_quantity=product_qty,
        )
        max_buyer = getattr(product, "max_per_buyer", None)
        if max_buyer is not None:
            prior = buyer_prior_product_quantity(
                db, buyer_user_id=buyer_uid, product_id=product.id
            )
            if prior + product_qty > max_buyer:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Quantity for {product.name} exceeds the per-buyer limit "
                        f"({max_buyer})"
                    ),
                )
        reserve_variant_quantity(variant, quantity)
        from app.merch.stock_alerts import evaluate_variant_stock_alerts

        evaluate_variant_stock_alerts(db, product=product, variant=variant)
        unit = effective_variant_price(product, variant)
        merch_line_items.append((product, variant, quantity, unit, None, False))
        subtotal += unit * quantity

    fulfillment_method = payload.fulfillment_method
    needs_shipping = False
    if merch_line_items:
        shippable = any(
            bool(getattr(p, "shipping_enabled", False)) for p, *_ in merch_line_items
        )
        pickupable = any(
            bool(getattr(p, "pickup_enabled", True)) for p, *_ in merch_line_items
        )
        if fulfillment_method is None:
            fulfillment_method = "shipping" if shippable and not pickupable else "pickup"
        if fulfillment_method == "shipping":
            if not shippable:
                raise HTTPException(
                    status_code=400, detail="Selected merch does not support shipping"
                )
            needs_shipping = True
        elif fulfillment_method == "pickup" and not pickupable:
            raise HTTPException(
                status_code=400, detail="Selected merch does not support pickup"
            )

    shipping_amount = Decimal("0.00")
    if needs_shipping:
        if payload.shipping_address is None:
            raise HTTPException(
                status_code=400, detail="Shipping address is required for delivery"
            )
        shipping_amount = compute_shipping_fee(
            db,
            host_id=event.host_id,
            event_id=event.id,
            country=payload.shipping_address.country,
            state=payload.shipping_address.state,
            city=payload.shipping_address.city,
        )

    # Ticket promos apply to ticket lines only (existing engine)
    priced_lines = [
        (tt, quantity, unit) for tt, quantity, unit, _bid in ticket_line_items
    ]
    discount = Decimal("0.00")
    promo = None
    if payload.promo_code:
        if not priced_lines:
            raise HTTPException(
                status_code=400,
                detail="Promo codes apply to ticket purchases only",
            )
        from app.promos.service import validate_promo_for_cart

        promo, discount = validate_promo_for_cart(
            db,
            code=payload.promo_code,
            event=event,
            user=user,
            line_items=priced_lines,
            reserve_usage=True,
        )

    merch_discount = Decimal("0.00")
    merch_code = None
    if payload.merch_discount_code:
        ticket_sub = sum(
            (unit * qty for _, qty, unit, _ in ticket_line_items), Decimal("0")
        )
        merch_lines_for_discount = [
            (product, unit * qty, from_bundle)
            for product, _v, qty, unit, _bid, from_bundle in merch_line_items
        ]
        merch_code, merch_discount, shipping_amount = validate_merch_discount(
            db,
            code_str=payload.merch_discount_code,
            host_id=event.host_id,
            buyer=user,
            merch_lines=merch_lines_for_discount,
            ticket_subtotal=ticket_sub,
            shipping_amount=shipping_amount,
        )

    ticket_subtotal = sum(
        (unit * quantity for _tt, quantity, unit, _bid in ticket_line_items),
        Decimal("0.00"),
    )
    merch_subtotal = sum(
        (
            unit * quantity
            for _p, _v, quantity, unit, _bid, _fb in merch_line_items
        ),
        Decimal("0.00"),
    )

    from app.finance.fees.checkout_fees import (
        calculate_checkout_fees,
        persist_order_fee_result,
    )

    fee_result = calculate_checkout_fees(
        db,
        host_id=event.host_id,
        ticket_subtotal=ticket_subtotal,
        merch_subtotal=merch_subtotal,
        ticket_discount=discount,
        merch_discount=merch_discount,
        shipping_amount=shipping_amount,
        currency="NGN",
    )
    # Server source of truth for Paystack — includes buyer-paid fees only.
    total = fee_result.final_total

    reference = _new_reference()
    while db.scalar(select(Order.id).where(Order.reference == reference)):
        reference = _new_reference()

    # Attendee / gift assignment — order belongs to buyer; tickets to attendees
    ticket_qty_for_attendees: dict[uuid.UUID, int] = {}
    for tt, quantity, _unit, _bid in ticket_line_items:
        ticket_qty_for_attendees[tt.id] = (
            ticket_qty_for_attendees.get(tt.id, 0) + quantity
        )
    _mode, resolved_attendees, gift_fields = resolve_attendees_for_order(
        user=user,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        payload=payload,
        ticket_qty_by_type=ticket_qty_for_attendees,
    )

    order = Order(
        reference=reference,
        buyer_user_id=buyer_uid,
        event_id=event.id,
        host_id=event.host_id,
        status="pending",
        currency="NGN",
        subtotal_amount=subtotal,
        discount_amount=discount,
        merch_discount_amount=merch_discount,
        shipping_amount=shipping_amount,
        buyer_fee_total=fee_result.buyer_fee_total,
        host_fee_total=fee_result.host_fee_total,
        processing_fee_total=fee_result.processing_fee_total,
        platform_revenue_total=fee_result.platform_revenue_total,
        host_net_estimate=fee_result.host_net_estimate,
        total_amount=total,
        fulfillment_method=fulfillment_method,
        buyer_email=buyer_email,
        buyer_name=buyer_name,
        is_guest_checkout=is_guest,
        guest_buyer_name=buyer_name if is_guest else None,
        guest_buyer_email=buyer_email if is_guest else None,
        guest_buyer_phone=buyer_phone if is_guest else None,
        purchase_mode=gift_fields["purchase_mode"],
        is_gift=gift_fields["is_gift"],
        purchased_for_someone_else=gift_fields["purchased_for_someone_else"],
        gift_message=gift_fields["gift_message"],
        send_ticket_to_recipient=gift_fields["send_ticket_to_recipient"],
        keep_buyer_copy=gift_fields["keep_buyer_copy"],
        recipient_name=gift_fields["recipient_name"],
        recipient_email=gift_fields["recipient_email"],
        recipient_phone=gift_fields["recipient_phone"],
        recipient_user_id=gift_fields["recipient_user_id"],
        reservation_expires_at=compute_reservation_expires_at(
            ticket_types=[tt for tt, _q, _u, _b in ticket_line_items]
        )
        if (ticket_line_items or merch_line_items)
        else None,
    )
    db.add(order)
    db.flush()
    persist_order_fee_result(
        db, order_id=order.id, host_id=event.host_id, result=fee_result
    )
    persist_order_attendees(
        db,
        order=order,
        attendees=resolved_attendees,
        actor_user_id=buyer_uid,
    )

    if needs_shipping and payload.shipping_address is not None:
        create_shipping_address(
            db,
            order=order,
            buyer=user,
            recipient_name=payload.shipping_address.recipient_name,
            phone=payload.shipping_address.phone,
            line1=payload.shipping_address.line1,
            line2=payload.shipping_address.line2,
            city=payload.shipping_address.city,
            state=payload.shipping_address.state,
            country=payload.shipping_address.country,
            postal_code=payload.shipping_address.postal_code,
            notes=payload.shipping_address.notes,
        )

    for tt, quantity, unit, bundle_id in ticket_line_items:
        db.add(
            OrderItem(
                order_id=order.id,
                item_kind=ITEM_KIND_TICKET,
                ticket_type_id=tt.id,
                bundle_id=bundle_id,
                quantity=quantity,
                unit_price=unit,
                line_total=unit * quantity,
                ticket_type_name=tt.name,
            )
        )

    for product, variant, quantity, unit, bundle_id, _from_bundle in merch_line_items:
        db.add(
            OrderItem(
                order_id=order.id,
                item_kind=ITEM_KIND_MERCH,
                merch_product_id=product.id,
                merch_variant_id=variant.id,
                bundle_id=bundle_id,
                quantity=quantity,
                unit_price=unit,
                line_total=unit * quantity,
                product_name=product.name,
                variant_label=variant.label,
            )
        )

    for question, value in validated_answers:
        db.add(
            OrderCheckoutAnswer(
                order_id=order.id,
                question_id=question.id,
                question_label=question.label,
                question_type=question.type,
                value=value,
            )
        )

    if promo is not None:
        from app.promos.service import attach_promo_to_order

        attach_promo_to_order(
            db, order=order, promo=promo, user=user, discount=discount
        )

    if merch_code is not None:
        attach_pending_redemption(
            db,
            order=order,
            code=merch_code,
            buyer=user,
            discount_amount=merch_discount,
        )

    if (
        payload.referral_code
        or getattr(payload, "platform_referral_code", None)
        or getattr(payload, "ambassador_attribution_id", None) is not None
    ):
        from app.promos.constants import (
            PRODUCT_SLICE_MERCH,
            PRODUCT_SLICE_TICKETS,
            REFERRAL_SOURCES,
        )
        from app.promos.attribution import resolve_platform_ambassador
        from app.promos.service import (
            attach_ambassador_to_order,
            resolve_ambassador_for_event,
        )

        prefer_merch = any(
            getattr(item, "item_kind", "ticket") in {"merch", "bundle"}
            for item in order.items
        ) and not any(
            getattr(item, "item_kind", "ticket") == "ticket" for item in order.items
        )
        source = (
            payload.referral_source
            if payload.referral_source in REFERRAL_SOURCES
            else "link"
        )
        platform_code = getattr(payload, "platform_referral_code", None)
        if platform_code:
            order.platform_referral_code = platform_code.strip().lower()

        # v1 ambassador row (legacy) — dual-write until cutover.
        if payload.referral_code:
            ambassador = resolve_ambassador_for_event(
                db,
                referral_code=payload.referral_code,
                event=event,
                prefer_merch=prefer_merch,
            )
            if ambassador is None:
                # Platform-wide code may be sent as the primary referral_code.
                slice_name = (
                    PRODUCT_SLICE_MERCH if prefer_merch else PRODUCT_SLICE_TICKETS
                )
                plat = resolve_platform_ambassador(
                    db,
                    referral_code=payload.referral_code,
                    event=event,
                    product_slice=slice_name,
                )
                if plat is not None:
                    ambassador = plat.ambassador
            if ambassador is not None:
                attach_ambassador_to_order(
                    db,
                    order=order,
                    ambassador=ambassador,
                    attribution_source=source,
                )
        elif platform_code:
            slice_name = (
                PRODUCT_SLICE_MERCH if prefer_merch else PRODUCT_SLICE_TICKETS
            )
            plat = resolve_platform_ambassador(
                db,
                referral_code=platform_code,
                event=event,
                product_slice=slice_name,
            )
            if plat is not None:
                attach_ambassador_to_order(
                    db,
                    order=order,
                    ambassador=plat.ambassador,
                    attribution_source=source,
                )

        # Domain participant — requires authenticated buyer; guests keep referral_code only.
        if user is not None:
            from app.ambassadors.payment import attach_domain_attribution_to_order

            attach_domain_attribution_to_order(
                db,
                order=order,
                event=event,
                buyer=user,
                referral_code=payload.referral_code,
                referral_source=source,
                attribution_id=getattr(payload, "ambassador_attribution_id", None),
                session_id=getattr(payload, "referral_session_id", None),
            )

    # Cart conversion waits for verified payment webhook — never invent paid state here.

    write_audit_log(
        db,
        action="orders.create",
        actor_user_id=buyer_uid,
        resource_type="order",
        resource_id=str(order.id),
        details={
            "reference": reference,
            "subtotal": str(subtotal),
            "discount": str(discount),
            "merch_discount": str(merch_discount),
            "shipping": str(shipping_amount),
            "total": str(total),
            "promo": promo.code if promo else None,
            "merch_discount_code": merch_code.code if merch_code else None,
            "referral": order.referral_code,
            "fulfillment_method": fulfillment_method,
            "is_guest_checkout": is_guest,
            # Never log shipping street/phone
        },
    )
    db.commit()
    return get_order_by_id(db, order.id)  # type: ignore[return-value]


def initialize_checkout(
    db: Session,
    *,
    user: User | None,
    order_id: uuid.UUID,
    payment_email: str | None = None,
) -> dict:
    order = get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    is_guest_order = bool(getattr(order, "is_guest_checkout", False)) or order.buyer_user_id is None
    if user is not None:
        from app.users.restrictions import assert_can_checkout

        assert_can_checkout(db, user)
        if order.buyer_user_id != user.id:
            raise HTTPException(status_code=404, detail="Order not found")
    elif not is_guest_order:
        raise HTTPException(status_code=401, detail="Authentication required")
    # Guest checkout: order lookup by id is enough for pending Paystack init
    # (reference is unguessable; no account to steal).

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Order is not pending payment")

    ensure_pending_reservation_active(db, order=order)

    event = db.get(Event, order.event_id)
    if event is not None and user is not None:
        from app.hosts.fan_self_abuse import assert_owner_not_buying_own_host

        assert_owner_not_buying_own_host(
            db, user_id=user.id, host_id=event.host_id
        )
    elif event is not None and is_guest_order:
        from app.payments.guest import assert_guest_email_allowed_for_checkout

        assert_guest_email_allowed_for_checkout(
            db,
            email=order.buyer_email,
            host_id=event.host_id,
            has_tickets=any(
                (getattr(i, "item_kind", None) or "ticket") == "ticket"
                and i.ticket_type_id
                for i in order.items
            ),
            has_merch=any(
                (getattr(i, "item_kind", None) or "ticket") in {"merch", "bundle"}
                for i in order.items
            ),
        )

    # Free checkout — complete server-side (never trust a frontend success callback)
    if order.total_amount <= 0:
        return _complete_free_order(db, order=order, user=user)

    # Reuse any prior attempt's row instead of inserting a new one — `reference`
    # is unique, so retrying checkout after a failed/timed-out attempt (e.g. a
    # misconfigured Paystack key) would otherwise crash with an IntegrityError.
    payment = db.scalar(select(Payment).where(Payment.order_id == order.id))
    if payment is None:
        payment = Payment(order_id=order.id, reference=order.reference)
        db.add(payment)
    payment.provider = "paystack"
    payment.amount = order.total_amount
    payment.currency = order.currency
    payment.status = "pending"
    payment.authorization_url = None
    payment.access_code = None
    payment.raw_response = None
    db.flush()

    amount_kobo = int(order.total_amount * 100)
    callback_url = (
        f"{settings.frontend_url.rstrip('/')}/checkout/success"
        f"?order={order.reference}"
    )

    try:
        from app.payments.paystack_email import resolve_paystack_customer_email

        paystack_email = resolve_paystack_customer_email(
            order.buyer_email,
            payment_email_override=payment_email,
        )
        data = initialize_transaction(
            email=paystack_email,
            amount_kobo=amount_kobo,
            reference=order.reference,
            callback_url=callback_url,
            metadata={
                "order_id": str(order.id),
                "event_id": str(order.event_id),
                "buyer_user_id": str(user.id) if user else None,
                "is_guest": is_guest_order,
            },
            db=db,
        )
    except PaystackError as exc:
        payment.status = "failed"
        db.commit()
        detail = str(exc)
        if "invalid email" in detail.lower():
            from app.payments.paystack_email import PAYSTACK_INCOMPATIBLE_CHECKOUT_DETAIL

            detail = PAYSTACK_INCOMPATIBLE_CHECKOUT_DETAIL
        # 503, not 502/504 — Cloudflare (and many CDNs) treat 502/504 as edge
        # connectivity failures and replace the body with their own branded
        # error page, hiding this actionable detail from the frontend/user.
        raise HTTPException(status_code=503, detail=detail) from exc

    payment.authorization_url = data.get("authorization_url")
    payment.access_code = data.get("access_code")
    payment.raw_response = data
    write_audit_log(
        db,
        action="payments.checkout_initialized",
        actor_user_id=user.id if user else None,
        resource_type="payment",
        resource_id=str(payment.id),
        details={
            "order_id": str(order.id),
            "reference": order.reference,
            "is_guest": is_guest_order,
        },
    )
    db.commit()
    from app.payments.config import paystack_runtime

    pay_cfg = paystack_runtime(db)
    return {
        "order_id": order.id,
        "reference": order.reference,
        "amount": order.total_amount,
        "currency": order.currency,
        "free_checkout": False,
        "authorization_url": payment.authorization_url,
        "access_code": payment.access_code,
        "public_key": pay_cfg.public_key or None,
        "paystack_mode": pay_cfg.mode,
        "paystack_customer_email": paystack_email,
        "buyer_fee_total": getattr(order, "buyer_fee_total", None) or Decimal("0"),
        "final_total": order.total_amount,
        "fee_breakdown": _buyer_fee_breakdown_for_order(db, order.id),
    }


def finalize_pending_order_via_paystack(
    db: Session,
    order: Order,
    *,
    actor_user_id: uuid.UUID | None = None,
    audit_action: str = "payments.checkout_confirmed",
) -> Order:
    """Verify Paystack and finalize a pending order (idempotent when already paid)."""
    if order.status == "paid":
        return order

    if order.status == "paid":
        return order
    if order.status == "payment_received":
        return order

    if order.status not in {"pending", "expired", "cancelled"}:
        raise HTTPException(
            status_code=400,
            detail=f"Order status {order.status} cannot be confirmed",
        )

    try:
        charge = verify_transaction(reference=order.reference, db=db)
    except PaystackError as exc:
        # See initialize_checkout: 503 avoids Cloudflare replacing the body
        # with its own error page (which it does for 502/504).
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    paystack_status = str(charge.get("status") or "").lower()
    if paystack_status != "success":
        raise HTTPException(
            status_code=409,
            detail="Payment is not confirmed yet. If you just paid, try again in a moment.",
        )

    charge_ref = str(charge.get("reference") or order.reference)
    if normalize_order_reference(charge_ref) != normalize_order_reference(order.reference):
        raise HTTPException(status_code=400, detail="Payment reference mismatch")

    from app.payments.webhook import apply_paystack_charge_success

    apply_paystack_charge_success(
        db,
        reference=order.reference,
        data=charge,
        raw_payload={"event": "charge.success", "data": charge, "source": "paystack_verify"},
        actor_user_id=actor_user_id or order.buyer_user_id,
    )
    write_audit_log(
        db,
        action=audit_action,
        actor_user_id=actor_user_id or order.buyer_user_id,
        resource_type="order",
        resource_id=str(order.id),
        details={"reference": order.reference, "via": "paystack_verify"},
    )
    db.commit()
    confirmed = get_order_by_id(db, order.id)
    if confirmed is None:
        raise HTTPException(status_code=500, detail="Order could not be loaded after confirm")
    return confirmed


def confirm_checkout_payment(
    db: Session,
    *,
    user: User | None,
    order_id: uuid.UUID,
) -> Order:
    """Verify Paystack server-side after popup success (webhook may be delayed or absent in dev)."""
    order = get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    is_guest_order = bool(getattr(order, "is_guest_checkout", False)) or order.buyer_user_id is None
    if user is not None:
        if order.buyer_user_id != user.id:
            raise HTTPException(status_code=404, detail="Order not found")
    elif not is_guest_order:
        raise HTTPException(status_code=401, detail="Authentication required")

    return finalize_pending_order_via_paystack(
        db,
        order,
        actor_user_id=user.id if user else None,
    )


def _complete_free_order(db: Session, *, order: Order, user: User | None) -> dict:
    from app.payments.webhook import finalize_successful_payment

    payment = Payment(
        order_id=order.id,
        provider="internal",
        reference=order.reference,
        amount=Decimal("0.00"),
        currency=order.currency,
        status="pending",
    )
    db.add(payment)
    db.flush()
    finalize_successful_payment(
        db,
        order=order,
        payment=payment,
        provider_payment_id="free",
        raw_payload={"type": "free_checkout"},
        actor_user_id=user.id if user else None,
    )
    db.commit()
    return {
        "order_id": order.id,
        "reference": order.reference,
        "amount": order.total_amount,
        "currency": order.currency,
        "free_checkout": True,
        "authorization_url": None,
        "access_code": None,
        "public_key": None,
        "buyer_fee_total": getattr(order, "buyer_fee_total", None) or Decimal("0"),
        "final_total": order.total_amount,
        "fee_breakdown": _buyer_fee_breakdown_for_order(db, order.id),
    }


def list_buyer_orders(
    db: Session, user: User, *, include_archived: bool = False
) -> list[Order]:
    q = select(Order).where(Order.buyer_user_id == user.id)
    if not include_archived:
        q = q.where(Order.archived_at.is_(None))
    return list(
        db.scalars(
            q.options(
                selectinload(Order.items),
                selectinload(Order.payments),
                selectinload(Order.checkout_answers),
            selectinload(Order.attendees),
            ).order_by(Order.created_at.desc())
        )
    )


def require_buyer_order(db: Session, user: User, order_id: uuid.UUID) -> Order:
    order = get_order_by_id(db, order_id)
    if order is None or order.buyer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def cancel_buyer_order(db: Session, *, user: User, order_id: uuid.UUID) -> Order:
    """Cancel an unpaid pending order and release inventory exactly once."""
    from sqlalchemy.orm import selectinload

    from app.payments.reservations import cancel_pending_order

    order = require_buyer_order(db, user, order_id)
    locked = db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items))
        .with_for_update()
    )
    if locked is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if locked.status == "cancelled":
        return locked
    if locked.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Order status {locked.status} cannot be cancelled",
        )
    cancel_pending_order(db, order=locked, actor_user_id=user.id)
    db.commit()
    db.refresh(locked)
    return locked


def archive_order(db: Session, *, user: User, order_id: uuid.UUID) -> Order:
    """UI archive for failed/abandoned orders — row remains in DB forever."""
    order = require_buyer_order(db, user, order_id)
    if order.status not in {
        "pending",
        "failed",
        "abandoned",
        "cancelled",
        "expired",
        "payment_received",
    }:
        raise HTTPException(
            status_code=400,
            detail="Only failed or abandoned unpaid orders can be archived",
        )
    if order.archived_at is not None:
        return order
    order.archived_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="orders.archive",
        actor_user_id=user.id,
        resource_type="order",
        resource_id=str(order.id),
        details={"status": order.status, "reference": order.reference},
    )
    db.commit()
    db.refresh(order)
    return order


def list_all_orders(db: Session) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.payments),
                selectinload(Order.checkout_answers),
            selectinload(Order.attendees),
            )
            .order_by(Order.created_at.desc())
        )
    )


def list_all_payments(db: Session) -> list[Payment]:
    return list(db.scalars(select(Payment).order_by(Payment.created_at.desc())))
