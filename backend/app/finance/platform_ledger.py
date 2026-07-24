"""Append-only platform ledger — Pàdéyá finance source of truth for reports.

Never update or delete rows. Corrections are new `adjustment` entries.
Webhook / refund / payout writers must use stable `dedupe_key` values.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event
from app.finance.constants import PLATFORM_LEDGER_DIRECTIONS, PLATFORM_LEDGER_ENTRY_TYPES
from app.finance.fees.constants import (
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_MERCH_COMMISSION,
    FEE_KEY_MERCH_FIXED,
    FEE_KEY_PAYMENT_PROCESSING,
    FEE_KEY_TICKET_COMMISSION,
    FEE_KEY_TICKET_FIXED,
    FEE_KEY_VAULT_COMMISSION,
    FEE_KEY_VAULT_FIXED,
)
from app.finance.fees.models import OrderFeeSnapshot
from app.finance.fees.money import minor_to_major
from app.finance.models import PlatformLedgerEntry
from app.payments.models import Order, OrderItem

TICKET_COMMISSION_KEYS = {FEE_KEY_TICKET_COMMISSION, FEE_KEY_TICKET_FIXED}
MERCH_COMMISSION_KEYS = {FEE_KEY_MERCH_COMMISSION, FEE_KEY_MERCH_FIXED}
VAULT_COMMISSION_KEYS = {FEE_KEY_VAULT_COMMISSION, FEE_KEY_VAULT_FIXED}


def _q(amount: Decimal | int | str | None) -> Decimal:
    return Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def mask_payment_reference(reference: str | None) -> str | None:
    """Safe display form — never return full secrets or raw Paystack payloads."""
    if not reference:
        return None
    ref = str(reference).strip()
    if len(ref) <= 8:
        return "••••" + ref[-2:]
    return f"{ref[:4]}••••{ref[-4:]}"


def append_platform_ledger_entry(
    db: Session,
    *,
    entry_type: str,
    amount: Decimal,
    direction: str,
    dedupe_key: str,
    currency: str = "NGN",
    order_id: UUID | None = None,
    ticket_id: UUID | None = None,
    host_id: UUID | None = None,
    user_id: UUID | None = None,
    event_id: UUID | None = None,
    description: str | None = None,
    metadata_json: dict[str, Any] | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    created_by: UUID | None = None,
) -> PlatformLedgerEntry | None:
    """Insert one immutable platform ledger row. Returns None if dedupe already exists."""
    if entry_type not in PLATFORM_LEDGER_ENTRY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid entry_type: {entry_type}")
    if direction not in PLATFORM_LEDGER_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Invalid ledger direction")
    amount_q = _q(amount)
    if amount_q <= 0:
        return None

    existing = db.scalar(
        select(PlatformLedgerEntry).where(PlatformLedgerEntry.dedupe_key == dedupe_key)
    )
    if existing is not None:
        return existing

    # Strip anything that looks like a raw gateway payload.
    safe_meta: dict[str, Any] | None = None
    if metadata_json:
        safe_meta = {
            k: v
            for k, v in metadata_json.items()
            if k
            not in {
                "raw_response",
                "raw_payload",
                "authorization",
                "card",
                "secret",
                "access_code",
            }
        }
        if "payment_reference" in safe_meta:
            safe_meta["payment_reference"] = mask_payment_reference(
                str(safe_meta["payment_reference"])
            )

    try:
        with db.begin_nested():
            row = PlatformLedgerEntry(
                entry_type=entry_type,
                order_id=order_id,
                ticket_id=ticket_id,
                host_id=host_id,
                user_id=user_id,
                event_id=event_id,
                amount=amount_q,
                currency=currency or "NGN",
                direction=direction,
                description=description,
                metadata_json=safe_meta,
                dedupe_key=dedupe_key[:220],
                reference_type=reference_type,
                reference_id=str(reference_id) if reference_id is not None else None,
                created_by=created_by,
            )
            db.add(row)
            db.flush()
            return row
    except IntegrityError:
        return db.scalar(
            select(PlatformLedgerEntry).where(
                PlatformLedgerEntry.dedupe_key == dedupe_key
            )
        )


def _item_totals(items: list[OrderItem]) -> tuple[Decimal, Decimal]:
    ticket = Decimal("0")
    merch = Decimal("0")
    for item in items:
        kind = (getattr(item, "item_kind", None) or "ticket").lower()
        total = _q(item.line_total)
        if kind in {"merch", "bundle"} or item.merch_variant_id is not None:
            merch += total
        else:
            ticket += total
    return _q(ticket), _q(merch)


def _commission_by_category(db: Session, order_id: UUID) -> dict[str, Decimal]:
    snaps = db.scalars(
        select(OrderFeeSnapshot).where(
            OrderFeeSnapshot.order_id == order_id,
            OrderFeeSnapshot.payer == "host",
        )
    ).all()
    ticket = Decimal("0")
    merch = Decimal("0")
    vault = Decimal("0")
    other = Decimal("0")
    for snap in snaps:
        amt = _q(minor_to_major(int(snap.amount), currency=snap.currency or "NGN"))
        if snap.fee_key in TICKET_COMMISSION_KEYS:
            ticket += amt
        elif snap.fee_key in MERCH_COMMISSION_KEYS:
            merch += amt
        elif snap.fee_key in VAULT_COMMISSION_KEYS:
            vault += amt
        else:
            other += amt
    return {
        "ticket": _q(ticket),
        "merch": _q(merch),
        "vault": _q(vault),
        "other": _q(other),
    }


def record_platform_entries_for_paid_order(
    db: Session,
    order: Order,
    *,
    actor_user_id: UUID | None = None,
) -> list[PlatformLedgerEntry]:
    """Idempotent platform journal rows after verified payment."""
    order = db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items))
    ) or order

    event = db.get(Event, order.event_id)
    host_id = event.host_id if event else None
    currency = order.currency or "NGN"
    oid = order.id
    created: list[PlatformLedgerEntry] = []

    def _add(**kwargs: Any) -> None:
        row = append_platform_ledger_entry(db, created_by=actor_user_id, **kwargs)
        if row is not None:
            created.append(row)

    total = _q(order.total_amount)
    if total > 0:
        _add(
            entry_type="buyer_payment",
            amount=total,
            direction="credit",
            dedupe_key=f"buyer_payment:order:{oid}",
            currency=currency,
            order_id=oid,
            host_id=host_id,
            user_id=order.buyer_user_id,
            event_id=order.event_id,
            description="Buyer payment (verified)",
            metadata_json={
                "payment_reference": mask_payment_reference(order.reference),
                "order_status": order.status,
            },
            reference_type="order",
            reference_id=str(oid),
        )

    ticket_gross, merch_gross = _item_totals(list(order.items or []))
    discount = _q(order.discount_amount) + _q(
        getattr(order, "merch_discount_amount", None)
    )
    # Allocate discount proportionally for revenue lines.
    subtotal = ticket_gross + merch_gross
    if subtotal > 0 and discount > 0:
        ticket_share = (ticket_gross / subtotal) * discount
        merch_share = discount - ticket_share
        ticket_net = max(Decimal("0"), ticket_gross - _q(ticket_share))
        merch_net = max(Decimal("0"), merch_gross - _q(merch_share))
    else:
        ticket_net, merch_net = ticket_gross, merch_gross

    if ticket_net > 0:
        _add(
            entry_type="ticket_revenue",
            amount=ticket_net,
            direction="credit",
            dedupe_key=f"ticket_revenue:order:{oid}",
            currency=currency,
            order_id=oid,
            host_id=host_id,
            user_id=order.buyer_user_id,
            event_id=order.event_id,
            description="Ticket revenue (after discounts)",
            reference_type="order",
            reference_id=str(oid),
        )
    if merch_net > 0:
        _add(
            entry_type="merch_revenue",
            amount=merch_net,
            direction="credit",
            dedupe_key=f"merch_revenue:order:{oid}",
            currency=currency,
            order_id=oid,
            host_id=host_id,
            user_id=order.buyer_user_id,
            event_id=order.event_id,
            description="Merch revenue (after discounts)",
            reference_type="order",
            reference_id=str(oid),
        )

    buyer_fees = _q(getattr(order, "buyer_fee_total", None))
    if buyer_fees > 0:
        _add(
            entry_type="buyer_platform_fee",
            amount=buyer_fees,
            direction="credit",
            dedupe_key=f"buyer_platform_fee:order:{oid}",
            currency=currency,
            order_id=oid,
            host_id=host_id,
            user_id=order.buyer_user_id,
            event_id=order.event_id,
            description="Buyer platform / service fee",
            metadata_json={"fee_key": FEE_KEY_BUYER_SERVICE},
            reference_type="order",
            reference_id=str(oid),
        )

    processing = _q(getattr(order, "processing_fee_total", None))
    if processing > 0:
        _add(
            entry_type="processing_fee",
            amount=processing,
            direction="credit",
            dedupe_key=f"processing_fee:order:{oid}",
            currency=currency,
            order_id=oid,
            host_id=host_id,
            user_id=order.buyer_user_id,
            event_id=order.event_id,
            description="Payment processing fee",
            metadata_json={"fee_key": FEE_KEY_PAYMENT_PROCESSING},
            reference_type="order",
            reference_id=str(oid),
        )

    commissions = _commission_by_category(db, oid)
    for category, amount in commissions.items():
        if amount <= 0:
            continue
        _add(
            entry_type="host_commission",
            amount=amount,
            direction="credit",
            dedupe_key=f"host_commission:order:{oid}:{category}",
            currency=currency,
            order_id=oid,
            host_id=host_id,
            user_id=order.buyer_user_id,
            event_id=order.event_id,
            description=f"Host commission ({category})",
            metadata_json={"category": category},
            reference_type="order",
            reference_id=str(oid),
        )

    # Fallback when snapshots missing but host_fee_total set on order.
    host_fees = _q(getattr(order, "host_fee_total", None))
    snap_total = sum(commissions.values(), Decimal("0"))
    if host_fees > snap_total:
        remainder = _q(host_fees - snap_total)
        _add(
            entry_type="host_commission",
            amount=remainder,
            direction="credit",
            dedupe_key=f"host_commission:order:{oid}:remainder",
            currency=currency,
            order_id=oid,
            host_id=host_id,
            user_id=order.buyer_user_id,
            event_id=order.event_id,
            description="Host commission",
            metadata_json={"category": "ticket"},
            reference_type="order",
            reference_id=str(oid),
        )

    return created


def record_platform_entries_for_vault_purchase(
    db: Session,
    *,
    purchase_id: UUID,
    host_id: UUID,
    user_id: UUID,
    amount: Decimal,
    currency: str,
    buyer_fee_total: Decimal = Decimal("0"),
    host_fee_total: Decimal = Decimal("0"),
    processing_fee_total: Decimal = Decimal("0"),
    payment_reference: str | None = None,
    actor_user_id: UUID | None = None,
) -> list[PlatformLedgerEntry]:
    """Idempotent vault unlock platform journal."""
    created: list[PlatformLedgerEntry] = []
    pid = purchase_id
    currency = currency or "NGN"

    def _add(**kwargs: Any) -> None:
        row = append_platform_ledger_entry(db, created_by=actor_user_id, **kwargs)
        if row is not None:
            created.append(row)

    total = _q(amount)
    if total > 0:
        _add(
            entry_type="buyer_payment",
            amount=total,
            direction="credit",
            dedupe_key=f"buyer_payment:vault_purchase:{pid}",
            currency=currency,
            host_id=host_id,
            user_id=user_id,
            description="Vault unlock payment (verified)",
            metadata_json={
                "payment_reference": mask_payment_reference(payment_reference),
            },
            reference_type="vault_purchase",
            reference_id=str(pid),
        )
    vault_gross = max(Decimal("0"), total - _q(buyer_fee_total))
    if vault_gross > 0:
        _add(
            entry_type="vault_revenue",
            amount=vault_gross,
            direction="credit",
            dedupe_key=f"vault_revenue:vault_purchase:{pid}",
            currency=currency,
            host_id=host_id,
            user_id=user_id,
            description="Vault revenue",
            reference_type="vault_purchase",
            reference_id=str(pid),
        )
    if _q(buyer_fee_total) > 0:
        _add(
            entry_type="buyer_platform_fee",
            amount=_q(buyer_fee_total),
            direction="credit",
            dedupe_key=f"buyer_platform_fee:vault_purchase:{pid}",
            currency=currency,
            host_id=host_id,
            user_id=user_id,
            description="Buyer platform fee (Vault)",
            reference_type="vault_purchase",
            reference_id=str(pid),
        )
    if _q(host_fee_total) > 0:
        _add(
            entry_type="host_commission",
            amount=_q(host_fee_total),
            direction="credit",
            dedupe_key=f"host_commission:vault_purchase:{pid}",
            currency=currency,
            host_id=host_id,
            user_id=user_id,
            description="Vault host commission",
            metadata_json={"category": "vault"},
            reference_type="vault_purchase",
            reference_id=str(pid),
        )
    if _q(processing_fee_total) > 0:
        _add(
            entry_type="processing_fee",
            amount=_q(processing_fee_total),
            direction="credit",
            dedupe_key=f"processing_fee:vault_purchase:{pid}",
            currency=currency,
            host_id=host_id,
            user_id=user_id,
            description="Processing fee (Vault)",
            reference_type="vault_purchase",
            reference_id=str(pid),
        )
    return created


def record_platform_refund_entries(
    db: Session,
    *,
    order: Order,
    refund_id: UUID,
    amount: Decimal,
    host_id: UUID,
    actor_user_id: UUID | None = None,
) -> list[PlatformLedgerEntry]:
    """Refund / reversal platform entries (idempotent per refund id)."""
    created: list[PlatformLedgerEntry] = []
    amount_q = _q(amount)
    if amount_q <= 0:
        return created

    row = append_platform_ledger_entry(
        db,
        entry_type="refund",
        amount=amount_q,
        direction="debit",
        dedupe_key=f"refund:refund:{refund_id}",
        currency=order.currency or "NGN",
        order_id=order.id,
        host_id=host_id,
        user_id=order.buyer_user_id,
        event_id=order.event_id,
        description="Refund debit",
        metadata_json={
            "payment_reference": mask_payment_reference(order.reference),
            "refund_id": str(refund_id),
        },
        reference_type="refund",
        reference_id=str(refund_id),
        created_by=actor_user_id,
    )
    if row is not None:
        created.append(row)

    # Reverse platform fee revenue proportionally when full order refund.
    order_total = _q(order.total_amount)
    if order_total > 0 and amount_q >= order_total:
        buyer_fees = _q(getattr(order, "buyer_fee_total", None))
        host_fees = _q(getattr(order, "host_fee_total", None))
        if buyer_fees > 0:
            rev = append_platform_ledger_entry(
                db,
                entry_type="adjustment",
                amount=buyer_fees,
                direction="debit",
                dedupe_key=f"adjustment:refund_buyer_fee:{refund_id}",
                currency=order.currency or "NGN",
                order_id=order.id,
                host_id=host_id,
                event_id=order.event_id,
                description="Reverse buyer platform fee on refund",
                metadata_json={"reverses": "buyer_platform_fee"},
                reference_type="refund",
                reference_id=str(refund_id),
                created_by=actor_user_id,
            )
            if rev is not None:
                created.append(rev)
        if host_fees > 0:
            rev = append_platform_ledger_entry(
                db,
                entry_type="adjustment",
                amount=host_fees,
                direction="debit",
                dedupe_key=f"adjustment:refund_host_commission:{refund_id}",
                currency=order.currency or "NGN",
                order_id=order.id,
                host_id=host_id,
                event_id=order.event_id,
                description="Reverse host commission on refund",
                metadata_json={"reverses": "host_commission"},
                reference_type="refund",
                reference_id=str(refund_id),
                created_by=actor_user_id,
            )
            if rev is not None:
                created.append(rev)
    return created


def record_platform_payout_entry(
    db: Session,
    *,
    payout_request_id: UUID,
    host_id: UUID,
    amount: Decimal,
    currency: str = "NGN",
    actor_user_id: UUID | None = None,
) -> PlatformLedgerEntry | None:
    """Host payout completed — platform debit."""
    return append_platform_ledger_entry(
        db,
        entry_type="host_payout",
        amount=_q(amount),
        direction="debit",
        dedupe_key=f"host_payout:payout_request:{payout_request_id}",
        currency=currency or "NGN",
        host_id=host_id,
        description="Host payout completed",
        metadata_json={"payout_request_id": str(payout_request_id)},
        reference_type="payout_request",
        reference_id=str(payout_request_id),
        created_by=actor_user_id,
    )


def record_platform_ambassador_reward(
    db: Session,
    *,
    order_id: UUID,
    host_id: UUID | None,
    event_id: UUID | None,
    amount: Decimal,
    currency: str = "NGN",
    sale_id: UUID | str,
    actor_user_id: UUID | None = None,
) -> PlatformLedgerEntry | None:
    return append_platform_ledger_entry(
        db,
        entry_type="ambassador_reward",
        amount=_q(amount),
        direction="debit",
        dedupe_key=f"ambassador_reward:sale:{sale_id}",
        currency=currency or "NGN",
        order_id=order_id,
        host_id=host_id,
        event_id=event_id,
        description="Ambassador reward",
        reference_type="ambassador_sale",
        reference_id=str(sale_id),
        created_by=actor_user_id,
    )
