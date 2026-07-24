"""Idempotent Paystack webhook processing and ticket issuance."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import TicketType
from app.payments.models import Order, Payment, PaymentWebhookEvent
from app.payments.paystack import verify_webhook_signature
from app.tickets.service import issue_tickets_for_paid_order, send_ticket_email

logger = logging.getLogger(__name__)


def _event_key(payload: dict[str, Any], body: bytes) -> str:
    data = payload.get("data") or {}
    event_id = data.get("id")
    reference = data.get("reference")
    event_type = payload.get("event")
    if event_id is not None:
        return f"paystack:{event_type}:{event_id}"
    digest = hashlib.sha256(body).hexdigest()
    return f"paystack:{event_type}:{reference}:{digest[:32]}"


def finalize_successful_payment(
    db: Session,
    *,
    order: Order,
    payment: Payment,
    provider_payment_id: str | None,
    raw_payload: dict[str, Any],
    actor_user_id: uuid.UUID | None = None,
) -> list:
    """Mark order/payment paid, convert reservations to sold, issue tickets once."""
    from app.tickets.models import Ticket

    from app.merch.constants import ITEM_KIND_MERCH, ITEM_KIND_TICKET
    from app.merch.fulfillment import create_fulfillments_for_paid_order
    from app.merch.notifications import notify_buyer_merch_paid

    order_id_safe = order.id

    if order.status == "paid":
        # Idempotent recovery: ensure merch fulfillments/inventory commit exist.
        merch_fulfillments = create_fulfillments_for_paid_order(db, order)
        tickets = list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)))
        if merch_fulfillments:
            from app.merch.cart import mark_cart_converted
            from app.merch.discounts import finalize_paid_redemption
            from app.merch.pod import create_jobs_for_paid_order
            from app.merch.revenue import create_splits_for_paid_order

            finalize_paid_redemption(db, order)
            create_splits_for_paid_order(db, order)
            create_jobs_for_paid_order(db, order)
            if order.buyer_user_id is not None:
                mark_cart_converted(
                    db, user_id=order.buyer_user_id, order_id=order.id
                )
            notify_buyer_merch_paid(db, order=order, fulfillments=merch_fulfillments)
            try:
                from app.merch.badges_hook import award_merch_badges_for_user

                if order.buyer_user_id is not None:
                    award_merch_badges_for_user(db, order.buyer_user_id)
            except Exception:  # noqa: BLE001 — badge refresh must not block payment
                logger.exception(
                    "merch badge refresh failed for order %s", order_id_safe
                )
        # Idempotent recovery for domain conversions if the first pass missed them.
        from app.ambassadors.payment import finalize_ambassador_conversions

        finalize_ambassador_conversions(db, order=order)
        db.flush()
        from app.finance.platform_ledger import record_platform_entries_for_paid_order

        record_platform_entries_for_paid_order(
            db, order, actor_user_id=actor_user_id or order.buyer_user_id
        )
        if tickets:
            send_ticket_email(db, order, tickets)
        return tickets

    if order.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Order status {order.status} cannot be paid",
        )

    from app.payments.checkout_account import provision_guest_merch_buyer_if_needed

    provision_guest_merch_buyer_if_needed(db, order)
    db.refresh(order)

    for item in order.items:
        kind = getattr(item, "item_kind", None) or (
            ITEM_KIND_MERCH if item.merch_variant_id else ITEM_KIND_TICKET
        )
        if kind != ITEM_KIND_TICKET or item.ticket_type_id is None:
            continue
        tt = db.scalar(
            select(TicketType).where(TicketType.id == item.ticket_type_id).with_for_update()
        )
        if tt is None:
            continue
        tt.quantity_reserved = max(0, tt.quantity_reserved - item.quantity)
        tt.quantity_sold += item.quantity
        if tt.quantity_sold >= tt.quantity:
            tt.status = "sold_out"

    now = datetime.now(UTC)
    order.status = "paid"
    order.paid_at = now
    payment.status = "successful"
    payment.paid_at = now
    payment.provider_payment_id = provider_payment_id
    payment.raw_response = raw_payload

    # Merch inventory deducts only after verified payment (never issue tickets for merch)
    merch_fulfillments = create_fulfillments_for_paid_order(db, order)
    tickets = issue_tickets_for_paid_order(db, order)

    from app.promos.service import finalize_promo_and_attribution

    finalize_promo_and_attribution(db, order=order)

    # Domain Ambassadors conversions — verified payment only (never FE success).
    from app.ambassadors.payment import finalize_ambassador_conversions

    finalize_ambassador_conversions(db, order=order)

    from app.merch.discounts import finalize_paid_redemption
    from app.merch.pod import create_jobs_for_paid_order
    from app.merch.revenue import create_splits_for_paid_order

    finalize_paid_redemption(db, order)
    create_splits_for_paid_order(db, order)
    create_jobs_for_paid_order(db, order)

    from app.finance.service import record_sale_credit_for_order

    record_sale_credit_for_order(db, order)

    from app.finance.platform_ledger import record_platform_entries_for_paid_order

    record_platform_entries_for_paid_order(
        db, order, actor_user_id=actor_user_id or order.buyer_user_id
    )

    write_audit_log(
        db,
        action="payments.successful",
        actor_user_id=actor_user_id or order.buyer_user_id,
        resource_type="order",
        resource_id=str(order.id),
        details={
            "reference": order.reference,
            "ticket_count": len(tickets),
            "merch_fulfillment_count": len(merch_fulfillments),
            "provider_payment_id": provider_payment_id,
            "discount": str(order.discount_amount or 0),
            "promo": order.promo_code_snapshot,
            "referral": order.referral_code,
        },
    )
    db.flush()

    try:
        from app.analytics.trusted import (
            emit_merch_payment_confirmed,
            emit_merch_purchase_completed,
            emit_payment_success,
            emit_ticket_issued,
        )
        from app.events.models import Event as EventModel

        event_row = db.get(EventModel, order.event_id)
        host_id = event_row.host_id if event_row else None
        if host_id is not None:
            emit_payment_success(
                db,
                order_id=order.id,
                event_id=order.event_id,
                host_id=host_id,
                buyer_user_id=order.buyer_user_id,
                amount=order.total_amount,
                ticket_count=len(tickets),
            )
            if tickets:
                emit_ticket_issued(
                    db,
                    order_id=order.id,
                    event_id=order.event_id,
                    host_id=host_id,
                    buyer_user_id=order.buyer_user_id,
                    ticket_count=len(tickets),
                )
            if merch_fulfillments:
                merch_qty = sum(int(f.quantity or 0) for f in merch_fulfillments)
                emit_merch_payment_confirmed(
                    db,
                    order_id=order.id,
                    event_id=order.event_id,
                    host_id=host_id,
                    buyer_user_id=order.buyer_user_id,
                    merch_item_count=merch_qty,
                    currency=order.currency,
                )
                emit_merch_purchase_completed(
                    db,
                    order_id=order.id,
                    event_id=order.event_id,
                    host_id=host_id,
                    buyer_user_id=order.buyer_user_id,
                    merch_item_count=merch_qty,
                    currency=order.currency,
                )
                from app.analytics.trusted import emit_sponsor_sale
                from app.merch.models import EventMerchProduct

                for item in order.items or []:
                    kind = getattr(item, "item_kind", None) or (
                        ITEM_KIND_MERCH if item.merch_variant_id else "ticket"
                    )
                    if kind != ITEM_KIND_MERCH or not item.merch_product_id:
                        continue
                    product = db.get(EventMerchProduct, item.merch_product_id)
                    if not product or not product.is_sponsor_branded:
                        continue
                    emit_sponsor_sale(
                        db,
                        order_id=order.id,
                        order_item_id=item.id,
                        event_id=order.event_id,
                        host_id=host_id,
                        merch_product_id=product.id,
                        quantity=int(item.quantity or 0),
                        sponsor_brand_name=product.sponsor_brand_name,
                        currency=order.currency,
                    )
    except Exception:  # noqa: BLE001 — analytics must never abort paid finalize
        logger.exception(
            "trusted analytics failed during payment finalize for order %s",
            order_id_safe,
        )

    if tickets:
        send_ticket_email(db, order, tickets)
    if merch_fulfillments and order.buyer_user_id is not None:
        from app.merch.cart import mark_cart_converted

        mark_cart_converted(db, user_id=order.buyer_user_id, order_id=order.id)
        notify_buyer_merch_paid(db, order=order, fulfillments=merch_fulfillments)
        try:
            from app.merch.badges_hook import award_merch_badges_for_user

            award_merch_badges_for_user(db, order.buyer_user_id)
        except Exception:  # noqa: BLE001 — badge refresh must not block payment
            logger.exception(
                "merch badge refresh failed for order %s", order_id_safe
            )
    elif merch_fulfillments:
        notify_buyer_merch_paid(db, order=order, fulfillments=merch_fulfillments)
    return tickets


def apply_paystack_charge_success(
    db: Session,
    *,
    reference: str,
    data: dict[str, Any],
    raw_payload: dict[str, Any],
    actor_user_id: uuid.UUID | None = None,
) -> None:
    """Finalize a successful Paystack charge (webhook or verify-after-popup)."""
    ref = str(reference)
    if ref.startswith("PDY-SPN-"):
        from app.sponsorships.deals_payment import finalize_sponsorship_paystack_success

        finalize_sponsorship_paystack_success(
            db,
            reference=ref,
            data=data,
            raw_payload=raw_payload,
        )
        db.commit()
        return

    if ref.startswith("PDY-VLT-"):
        from app.vault.service import (
            finalize_vault_purchase,
            get_vault_purchase_by_reference,
        )

        purchase = get_vault_purchase_by_reference(db, ref, for_update=True)
        if purchase is None:
            raise HTTPException(status_code=404, detail="Vault purchase not found")
        amount = data.get("amount")
        if amount is not None:
            expected_kobo = int(purchase.amount * 100)
            if int(amount) != expected_kobo:
                raise HTTPException(status_code=400, detail="Payment amount mismatch")
        finalize_vault_purchase(
            db,
            purchase=purchase,
            provider_payment_id=str(data.get("id")) if data.get("id") is not None else None,
            raw_payload=raw_payload,
            actor_user_id=actor_user_id or purchase.user_id,
        )
        return

    order = db.scalar(
        select(Order)
        .where(Order.reference == ref)
        .options(
            selectinload(Order.items),
            selectinload(Order.payments),
        )
        .with_for_update()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found for reference")

    payment = db.scalar(
        select(Payment).where(Payment.reference == ref).with_for_update()
    )
    if payment is None:
        payment = Payment(
            order_id=order.id,
            provider="paystack",
            reference=ref,
            amount=order.total_amount,
            currency=order.currency,
            status="pending",
        )
        db.add(payment)
        db.flush()

    amount = data.get("amount")
    if amount is not None:
        expected_kobo = int(order.total_amount * 100)
        if int(amount) != expected_kobo:
            raise HTTPException(status_code=400, detail="Payment amount mismatch")

    finalize_successful_payment(
        db,
        order=order,
        payment=payment,
        provider_payment_id=str(data.get("id")) if data.get("id") is not None else None,
        raw_payload=raw_payload,
        actor_user_id=actor_user_id or order.buyer_user_id,
    )
    try:
        from app.core.cache_invalidation import invalidate_on_ticket_purchase
        from app.events.models import Event as EventModel

        ev = db.get(EventModel, order.event_id) if order.event_id else None
        invalidate_on_ticket_purchase(
            event_slug=ev.slug if ev else None,
            event_id=order.event_id,
        )
    except Exception:
        pass


def mark_payment_failed(
    db: Session,
    *,
    order: Order,
    payment: Payment,
    raw_payload: dict[str, Any],
) -> None:
    if order.status == "paid":
        return
    payment.status = "failed"
    payment.raw_response = raw_payload
    order.status = "failed"
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
                # Ticket line quantity == pack quantity for expanded bundles.
                release_bundle_reservation(bundle, item.quantity)
            released_bundle_ids.add(bid)

    from app.promos.service import release_promo_reservation

    release_promo_reservation(db, order=order)

    write_audit_log(
        db,
        action="payments.failed",
        actor_user_id=order.buyer_user_id,
        resource_type="order",
        resource_id=str(order.id),
        details={"reference": order.reference},
    )

    from app.analytics.trusted import emit_payment_failed
    from app.events.models import Event as EventModel

    event_row = db.get(EventModel, order.event_id)
    if event_row is not None:
        emit_payment_failed(
            db,
            order_id=order.id,
            event_id=order.event_id,
            host_id=event_row.host_id,
            buyer_user_id=order.buyer_user_id,
        )


def process_paystack_webhook(
    db: Session,
    *,
    body: bytes,
    signature: str | None,
) -> dict[str, str]:
    if not verify_webhook_signature(body=body, signature=signature, db=db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Paystack signature",
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    event_type = payload.get("event")
    data = payload.get("data") or {}
    reference = data.get("reference")
    event_key = _event_key(payload, body)

    existing = db.scalar(
        select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == "paystack",
            PaymentWebhookEvent.event_key == event_key,
        )
    )
    if existing is not None and existing.processing_status == "processed":
        return {"status": "duplicate", "event_key": event_key}

    if existing is None:
        webhook_event = PaymentWebhookEvent(
            provider="paystack",
            event_key=event_key,
            reference=reference,
            event_type=event_type,
            payload=payload,
            processing_status="received",
        )
        try:
            with db.begin_nested():
                db.add(webhook_event)
                db.flush()
        except IntegrityError:
            # Concurrent duplicate delivery of the same event_key
            existing = db.scalar(
                select(PaymentWebhookEvent).where(
                    PaymentWebhookEvent.provider == "paystack",
                    PaymentWebhookEvent.event_key == event_key,
                )
            )
            if existing is not None and existing.processing_status == "processed":
                return {"status": "duplicate", "event_key": event_key}
            if existing is None:
                raise
            webhook_event = existing
    else:
        webhook_event = existing

    try:
        if event_type == "charge.success" and reference:
            apply_paystack_charge_success(
                db,
                reference=str(reference),
                data=data,
                raw_payload=payload,
            )
        elif event_type in {"charge.failed", "transfer.failed"} and reference:
            if str(reference).startswith("PDY-VLT-"):
                from app.vault.service import get_vault_purchase_by_reference

                purchase = get_vault_purchase_by_reference(db, str(reference))
                if purchase and purchase.status != "paid":
                    purchase.status = "failed"
                    purchase.raw_response = payload
            else:
                order = db.scalar(
                    select(Order)
                    .where(Order.reference == reference)
                    .options(selectinload(Order.items), selectinload(Order.payments))
                    .with_for_update()
                )
                payment = db.scalar(select(Payment).where(Payment.reference == reference))
                if order and payment:
                    mark_payment_failed(db, order=order, payment=payment, raw_payload=payload)

        webhook_event.processing_status = "processed"
        webhook_event.processed_at = datetime.now(UTC)
        db.commit()
        return {"status": "ok", "event_key": event_key}
    except HTTPException as exc:
        webhook_event.processing_status = "failed"
        webhook_event.error_message = str(exc.detail)[:500]
        webhook_event.processed_at = datetime.now(UTC)
        db.commit()
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Webhook processing failed")
        webhook_event.processing_status = "failed"
        webhook_event.error_message = str(exc)[:500]
        webhook_event.processed_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=500, detail="Webhook processing failed") from exc
