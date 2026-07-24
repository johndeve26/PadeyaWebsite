"""Append-only ledger helpers and host balance mutations."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.finance.models import HostBalance, LedgerEntry


def get_or_create_host_balance(
    db: Session, host_id: UUID, *, currency: str = "NGN"
) -> HostBalance:
    balance = db.scalar(select(HostBalance).where(HostBalance.host_id == host_id))
    if balance is not None:
        return balance
    balance = HostBalance(
        host_id=host_id,
        currency=currency,
        available_balance=Decimal("0"),
        pending_payout_balance=Decimal("0"),
        lifetime_earned=Decimal("0"),
        lifetime_refunded=Decimal("0"),
        lifetime_paid_out=Decimal("0"),
    )
    db.add(balance)
    db.flush()
    return balance


def append_ledger_entry(
    db: Session,
    *,
    host_id: UUID,
    entry_type: str,
    direction: str,
    amount: Decimal,
    currency: str = "NGN",
    reference_type: str | None = None,
    reference_id: str | None = None,
    description: str | None = None,
    created_by_user_id: UUID | None = None,
    available_delta: Decimal = Decimal("0"),
    pending_delta: Decimal = Decimal("0"),
    lifetime_earned_delta: Decimal = Decimal("0"),
    lifetime_refunded_delta: Decimal = Decimal("0"),
    lifetime_paid_out_delta: Decimal = Decimal("0"),
) -> LedgerEntry:
    """Create an immutable ledger row and apply balance deltas. Never updates prior rows."""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Ledger amount must be positive")
    if direction not in {"credit", "debit"}:
        raise HTTPException(status_code=400, detail="Invalid ledger direction")

    # Lock balance row so concurrent vault/sale credits cannot race totals.
    balance = db.scalar(
        select(HostBalance).where(HostBalance.host_id == host_id).with_for_update()
    )
    if balance is None:
        balance = get_or_create_host_balance(db, host_id, currency=currency)
        balance = db.scalar(
            select(HostBalance).where(HostBalance.host_id == host_id).with_for_update()
        )
        assert balance is not None

    new_available = balance.available_balance + available_delta
    new_pending = balance.pending_payout_balance + pending_delta
    if new_available < 0 or new_pending < 0:
        raise HTTPException(
            status_code=400,
            detail="Insufficient host balance for this financial action",
        )

    balance.available_balance = new_available
    balance.pending_payout_balance = new_pending
    balance.lifetime_earned += lifetime_earned_delta
    balance.lifetime_refunded += lifetime_refunded_delta
    balance.lifetime_paid_out += lifetime_paid_out_delta

    entry = LedgerEntry(
        host_id=host_id,
        entry_type=entry_type,
        direction=direction,
        amount=amount,
        currency=currency,
        available_balance_after=new_available,
        pending_payout_balance_after=new_pending,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        created_by_user_id=created_by_user_id,
    )
    db.add(entry)
    db.flush()
    return entry


def credit_sale(
    db: Session,
    *,
    host_id: UUID,
    amount: Decimal,
    currency: str,
    order_id: UUID,
    actor_user_id: UUID | None = None,
) -> LedgerEntry:
    return append_ledger_entry(
        db,
        host_id=host_id,
        entry_type="sale_credit",
        direction="credit",
        amount=amount,
        currency=currency,
        reference_type="order",
        reference_id=str(order_id),
        description=f"Sale credit for order {order_id}",
        created_by_user_id=actor_user_id,
        available_delta=amount,
        lifetime_earned_delta=amount,
    )


def debit_refund(
    db: Session,
    *,
    host_id: UUID,
    amount: Decimal,
    currency: str,
    refund_request_id: UUID,
    actor_user_id: UUID,
) -> LedgerEntry:
    return append_ledger_entry(
        db,
        host_id=host_id,
        entry_type="refund_debit",
        direction="debit",
        amount=amount,
        currency=currency,
        reference_type="refund_request",
        reference_id=str(refund_request_id),
        description=f"Refund debit for request {refund_request_id}",
        created_by_user_id=actor_user_id,
        available_delta=-amount,
        lifetime_refunded_delta=amount,
    )


def hold_payout(
    db: Session,
    *,
    host_id: UUID,
    amount: Decimal,
    currency: str,
    payout_request_id: UUID,
    actor_user_id: UUID,
) -> LedgerEntry:
    return append_ledger_entry(
        db,
        host_id=host_id,
        entry_type="payout_hold",
        direction="debit",
        amount=amount,
        currency=currency,
        reference_type="payout_request",
        reference_id=str(payout_request_id),
        description=f"Payout hold for request {payout_request_id}",
        created_by_user_id=actor_user_id,
        available_delta=-amount,
        pending_delta=amount,
    )


def release_payout_hold(
    db: Session,
    *,
    host_id: UUID,
    amount: Decimal,
    currency: str,
    payout_request_id: UUID,
    actor_user_id: UUID,
) -> LedgerEntry:
    return append_ledger_entry(
        db,
        host_id=host_id,
        entry_type="payout_release",
        direction="credit",
        amount=amount,
        currency=currency,
        reference_type="payout_request",
        reference_id=str(payout_request_id),
        description=f"Payout hold released for request {payout_request_id}",
        created_by_user_id=actor_user_id,
        available_delta=amount,
        pending_delta=-amount,
    )


def complete_payout(
    db: Session,
    *,
    host_id: UUID,
    amount: Decimal,
    currency: str,
    payout_request_id: UUID,
    actor_user_id: UUID,
) -> LedgerEntry:
    return append_ledger_entry(
        db,
        host_id=host_id,
        entry_type="payout_paid",
        direction="debit",
        amount=amount,
        currency=currency,
        reference_type="payout_request",
        reference_id=str(payout_request_id),
        description=f"Payout paid for request {payout_request_id}",
        created_by_user_id=actor_user_id,
        pending_delta=-amount,
        lifetime_paid_out_delta=amount,
    )
