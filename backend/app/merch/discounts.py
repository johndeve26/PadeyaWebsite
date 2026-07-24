"""Merch discount codes — separate from ticket promo_codes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.merch.constants import DISCOUNT_APPLIES_TO, DISCOUNT_STATUSES, DISCOUNT_TYPES
from app.merch.models import EventMerchProduct, MerchDiscountCode, MerchDiscountRedemption
from app.payments.models import Order
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _effective_status(row: MerchDiscountCode) -> str:
    if row.archived_at is not None or row.status == "archived":
        return "archived"
    if row.status == "paused":
        return "paused"
    now = _now()
    ends = _as_utc(row.ends_at)
    if ends and now > ends:
        return "expired"
    return "active" if row.status == "active" else row.status


def serialize_discount(row: MerchDiscountCode) -> dict:
    paid = int(row.usage_count_paid or 0)
    return {
        "id": row.id,
        "host_id": row.host_id,
        "event_id": row.event_id,
        "code": row.code,
        "description": row.description,
        "discount_type": row.discount_type,
        "discount_value": row.discount_value,
        "value": row.discount_value,
        "currency": row.currency,
        "applies_to": row.applies_to,
        "product_ids": row.product_ids or [],
        "min_order_amount": row.min_order_amount,
        "usage_limit": row.usage_limit,
        "per_buyer_limit": row.per_buyer_limit,
        "usage_count": paid,
        "usage_count_paid": paid,
        "status": _effective_status(row),
        "starts_at": row.starts_at,
        "ends_at": row.ends_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "archived_at": row.archived_at,
    }


def _validate_create_fields(
    *,
    discount_type: str,
    discount_value: Decimal,
    applies_to: str,
    event_id: uuid.UUID | None,
    product_ids: list[str] | None,
    status: str,
) -> None:
    if discount_type not in DISCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid discount type")
    if applies_to not in DISCOUNT_APPLIES_TO:
        raise HTTPException(status_code=400, detail="Invalid applies_to")
    if status not in DISCOUNT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid discount status")
    value = Decimal(discount_value)
    if discount_type == "percent":
        if value <= 0 or value > 100:
            raise HTTPException(
                status_code=400, detail="Percent discount must be between 0 and 100"
            )
    elif discount_type == "fixed_amount":
        if value <= 0:
            raise HTTPException(status_code=400, detail="Fixed discount must be positive")
    elif discount_type == "free_shipping":
        # Value is unused for free_shipping; keep non-negative.
        if value < 0:
            raise HTTPException(status_code=400, detail="Invalid discount value")
    if applies_to == "specific_products":
        if not product_ids:
            raise HTTPException(
                status_code=400,
                detail="specific_products requires product_ids",
            )
    if applies_to == "specific_event_merch" and event_id is None:
        raise HTTPException(
            status_code=400,
            detail="specific_event_merch requires event_id",
        )


def create_discount(
    db: Session,
    *,
    host_id: uuid.UUID,
    code: str,
    discount_type: str,
    discount_value: Decimal,
    applies_to: str = "merch_only",
    event_id: uuid.UUID | None = None,
    description: str | None = None,
    currency: str | None = None,
    product_ids: list[str] | None = None,
    min_order_amount: Decimal | None = None,
    usage_limit: int | None = None,
    per_buyer_limit: int | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    status: str = "active",
) -> MerchDiscountCode:
    _validate_create_fields(
        discount_type=discount_type,
        discount_value=discount_value,
        applies_to=applies_to,
        event_id=event_id,
        product_ids=product_ids,
        status=status,
    )
    cleaned = code.strip().upper()
    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="Code too short")
    start_u = _as_utc(starts_at)
    end_u = _as_utc(ends_at)
    if start_u and end_u and start_u > end_u:
        raise HTTPException(status_code=400, detail="starts_at must be before ends_at")
    exists = db.scalar(
        select(MerchDiscountCode.id).where(
            MerchDiscountCode.host_id == host_id,
            func.upper(MerchDiscountCode.code) == cleaned,
        )
    )
    if exists:
        raise HTTPException(status_code=400, detail="Discount code already exists")
    archived_at = _now() if status == "archived" else None
    row = MerchDiscountCode(
        host_id=host_id,
        event_id=event_id,
        code=cleaned,
        description=(description or "").strip() or None,
        discount_type=discount_type,
        discount_value=Decimal(discount_value),
        currency=(currency or "").strip().upper() or None,
        applies_to=applies_to,
        product_ids=product_ids,
        min_order_amount=min_order_amount,
        usage_limit=usage_limit,
        per_buyer_limit=per_buyer_limit,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status if status != "expired" else "active",
        archived_at=archived_at,
    )
    db.add(row)
    db.flush()
    return row


def update_discount(
    db: Session,
    *,
    host_id: uuid.UUID,
    discount_id: uuid.UUID,
    description: str | None = None,
    discount_type: str | None = None,
    discount_value: Decimal | None = None,
    currency: str | None = None,
    applies_to: str | None = None,
    event_id: uuid.UUID | None = None,
    product_ids: list[str] | None = None,
    min_order_amount: Decimal | None = None,
    usage_limit: int | None = None,
    per_buyer_limit: int | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    status: str | None = None,
    clear_event_id: bool = False,
) -> MerchDiscountCode:
    row = db.scalar(
        select(MerchDiscountCode).where(
            MerchDiscountCode.id == discount_id,
            MerchDiscountCode.host_id == host_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Discount code not found")

    next_type = discount_type if discount_type is not None else row.discount_type
    next_value = (
        Decimal(discount_value) if discount_value is not None else Decimal(row.discount_value)
    )
    next_applies = applies_to if applies_to is not None else row.applies_to
    next_event = row.event_id
    if clear_event_id:
        next_event = None
    elif event_id is not None:
        next_event = event_id
    next_products = product_ids if product_ids is not None else row.product_ids
    next_status = status if status is not None else row.status
    _validate_create_fields(
        discount_type=next_type,
        discount_value=next_value,
        applies_to=next_applies,
        event_id=next_event,
        product_ids=[str(x) for x in (next_products or [])] or None,
        status=next_status,
    )

    if description is not None:
        row.description = description.strip() or None
    if discount_type is not None:
        row.discount_type = discount_type
    if discount_value is not None:
        row.discount_value = Decimal(discount_value)
    if currency is not None:
        row.currency = currency.strip().upper() or None
    if applies_to is not None:
        row.applies_to = applies_to
    if clear_event_id:
        row.event_id = None
    elif event_id is not None:
        row.event_id = event_id
    if product_ids is not None:
        row.product_ids = product_ids
    if min_order_amount is not None:
        row.min_order_amount = min_order_amount
    if usage_limit is not None:
        row.usage_limit = usage_limit
    if per_buyer_limit is not None:
        row.per_buyer_limit = per_buyer_limit
    if starts_at is not None:
        row.starts_at = starts_at
    if ends_at is not None:
        row.ends_at = ends_at
    if status is not None:
        if status == "archived":
            row.status = "archived"
            row.archived_at = row.archived_at or _now()
        elif status == "expired":
            row.status = "expired"
            row.archived_at = None
        else:
            row.status = status
            row.archived_at = None
    start_u = _as_utc(row.starts_at)
    end_u = _as_utc(row.ends_at)
    if start_u and end_u and start_u > end_u:
        raise HTTPException(status_code=400, detail="starts_at must be before ends_at")
    db.flush()
    return row


def archive_discount(
    db: Session, *, host_id: uuid.UUID, discount_id: uuid.UUID
) -> MerchDiscountCode:
    return update_discount(
        db, host_id=host_id, discount_id=discount_id, status="archived"
    )


def list_host_discounts(db: Session, *, host_id: uuid.UUID) -> list[dict]:
    rows = list(
        db.scalars(
            select(MerchDiscountCode)
            .where(
                MerchDiscountCode.host_id == host_id,
                MerchDiscountCode.archived_at.is_(None),
                MerchDiscountCode.status != "archived",
            )
            .order_by(MerchDiscountCode.created_at.desc())
        )
    )
    return [serialize_discount(r) for r in rows]


def _eligible_merch_subtotal(
    *,
    code: MerchDiscountCode,
    merch_lines: list[tuple[EventMerchProduct, Decimal, bool]],
    ticket_subtotal: Decimal,
) -> Decimal:
    """merch_lines: (product, line_total, from_bundle)."""
    applies = code.applies_to
    if applies == "tickets_and_merch":
        return ticket_subtotal + sum((t for _, t, _ in merch_lines), Decimal("0"))
    if applies == "bundles_only":
        return sum((t for _, t, b in merch_lines if b), Decimal("0"))
    if applies == "specific_products":
        allow = {str(x) for x in (code.product_ids or [])}
        return sum(
            (t for p, t, _ in merch_lines if str(p.id) in allow),
            Decimal("0"),
        )
    if applies == "specific_event_merch":
        if code.event_id is None:
            return Decimal("0")
        return sum(
            (t for p, t, _ in merch_lines if p.event_id == code.event_id),
            Decimal("0"),
        )
    if applies == "host_storefront_merch":
        return sum(
            (
                t
                for p, t, _ in merch_lines
                if p.storefront_visibility
                in {"host_storefront", "post_event_drop", "vault_exclusive"}
                or not p.is_event_linked
            ),
            Decimal("0"),
        )
    # merch_only
    return sum((t for _, t, _ in merch_lines), Decimal("0"))


def _buyer_paid_redemption_count(
    db: Session, *, discount_id: uuid.UUID, buyer_id: uuid.UUID
) -> int:
    used = db.scalar(
        select(func.count())
        .select_from(MerchDiscountRedemption)
        .where(
            MerchDiscountRedemption.discount_code_id == discount_id,
            MerchDiscountRedemption.buyer_user_id == buyer_id,
            MerchDiscountRedemption.status == "paid",
        )
    )
    return int(used or 0)


def validate_merch_discount(
    db: Session,
    *,
    code_str: str,
    host_id: uuid.UUID,
    buyer: User,
    merch_lines: list[tuple[EventMerchProduct, Decimal, bool]],
    ticket_subtotal: Decimal = Decimal("0"),
    shipping_amount: Decimal = Decimal("0"),
) -> tuple[MerchDiscountCode, Decimal, Decimal]:
    """Return (code, merch_discount_amount, shipping_after). Usage counted only on paid finalize."""
    cleaned = code_str.strip().upper()
    row = db.scalar(
        select(MerchDiscountCode).where(
            MerchDiscountCode.host_id == host_id,
            func.upper(MerchDiscountCode.code) == cleaned,
        )
    )
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Merch discount code is invalid")

    effective = _effective_status(row)
    if effective == "paused":
        raise HTTPException(status_code=400, detail="Merch discount code is paused")
    if effective == "expired":
        raise HTTPException(status_code=400, detail="Merch discount code has expired")
    if effective != "active":
        raise HTTPException(status_code=400, detail="Merch discount code is invalid")

    now = _now()
    starts = _as_utc(row.starts_at)
    ends = _as_utc(row.ends_at)
    if starts and now < starts:
        raise HTTPException(status_code=400, detail="Merch discount code is not active yet")
    if ends and now > ends:
        raise HTTPException(status_code=400, detail="Merch discount code has expired")
    if row.usage_limit is not None and int(row.usage_count_paid or 0) >= row.usage_limit:
        raise HTTPException(status_code=400, detail="Merch discount code usage limit reached")
    if row.per_buyer_limit is not None:
        used = _buyer_paid_redemption_count(db, discount_id=row.id, buyer_id=buyer.id)
        if used >= row.per_buyer_limit:
            raise HTTPException(
                status_code=400, detail="You have already used this merch discount code"
            )

    # Mode-specific eligibility
    if row.applies_to == "specific_products" and not (row.product_ids or []):
        raise HTTPException(
            status_code=400, detail="Merch discount is misconfigured for products"
        )
    if row.applies_to == "specific_event_merch" and row.event_id is None:
        raise HTTPException(
            status_code=400, detail="Merch discount is misconfigured for event merch"
        )
    if row.applies_to == "bundles_only" and not any(b for _, _, b in merch_lines):
        raise HTTPException(
            status_code=400, detail="No eligible bundle lines for this discount"
        )
    if row.applies_to == "tickets_and_merch" and ticket_subtotal <= 0 and not merch_lines:
        raise HTTPException(
            status_code=400, detail="No eligible lines for this discount"
        )

    eligible = _eligible_merch_subtotal(
        code=row, merch_lines=merch_lines, ticket_subtotal=ticket_subtotal
    )
    if row.min_order_amount is not None and eligible < Decimal(row.min_order_amount):
        raise HTTPException(
            status_code=400, detail="Order does not meet merch discount minimum"
        )

    shipping_after = Decimal(shipping_amount)
    discount = Decimal("0.00")
    if row.discount_type == "free_shipping":
        if shipping_after <= 0:
            raise HTTPException(
                status_code=400, detail="No shipping charges to waive with this code"
            )
        # Still require eligible merch context for applies_to (except pure tickets_and_merch).
        if eligible <= 0 and row.applies_to != "tickets_and_merch":
            raise HTTPException(
                status_code=400, detail="No eligible merch lines for this discount"
            )
        if eligible <= 0 and row.applies_to == "tickets_and_merch" and ticket_subtotal <= 0:
            raise HTTPException(
                status_code=400, detail="No eligible lines for this discount"
            )
        shipping_after = Decimal("0.00")
        discount = Decimal("0.00")
    else:
        if eligible <= 0:
            raise HTTPException(
                status_code=400, detail="No eligible merch lines for this discount"
            )
        if row.discount_type == "percent":
            discount = (
                eligible * Decimal(row.discount_value) / Decimal("100")
            ).quantize(Decimal("0.01"))
        elif row.discount_type == "fixed_amount":
            discount = min(Decimal(row.discount_value), eligible)
        discount = min(discount, eligible)
        # Never let discount exceed eligible base (total clamp happens in order create).
        if discount < 0:
            discount = Decimal("0.00")

    return row, discount, shipping_after


def clamp_order_total(
    *,
    subtotal: Decimal,
    ticket_discount: Decimal,
    merch_discount: Decimal,
    shipping_amount: Decimal,
) -> Decimal:
    """Order total cannot go below zero."""
    return max(
        Decimal("0.00"),
        Decimal(subtotal)
        - Decimal(ticket_discount)
        - Decimal(merch_discount)
        + Decimal(shipping_amount),
    )


def attach_pending_redemption(
    db: Session,
    *,
    order: Order,
    code: MerchDiscountCode,
    buyer: User,
    discount_amount: Decimal,
) -> None:
    order.merch_discount_code_id = code.id
    order.merch_discount_code_snapshot = code.code
    order.merch_discount_amount = discount_amount
    db.add(
        MerchDiscountRedemption(
            discount_code_id=code.id,
            order_id=order.id,
            buyer_user_id=buyer.id,
            discount_amount=discount_amount,
            status="pending",
        )
    )
    db.flush()


def finalize_paid_redemption(db: Session, order: Order) -> None:
    """Count usage only after webhook-verified payment. Idempotent."""
    red = db.scalar(
        select(MerchDiscountRedemption).where(
            MerchDiscountRedemption.order_id == order.id
        )
    )
    if red is None or red.status == "paid":
        return
    if red.status == "reversed":
        return
    red.status = "paid"
    code = db.get(MerchDiscountCode, red.discount_code_id)
    if code is not None:
        code.usage_count_paid = int(code.usage_count_paid or 0) + 1
    db.flush()


def reverse_redemption_on_refund(db: Session, order: Order) -> None:
    """Decrement paid usage so refunded orders do not count as successful redemptions."""
    red = db.scalar(
        select(MerchDiscountRedemption).where(
            MerchDiscountRedemption.order_id == order.id,
            MerchDiscountRedemption.status == "paid",
        )
    )
    if red is None:
        return
    red.status = "reversed"
    code = db.get(MerchDiscountCode, red.discount_code_id)
    if code is not None and int(code.usage_count_paid or 0) > 0:
        code.usage_count_paid = int(code.usage_count_paid) - 1
    db.flush()
