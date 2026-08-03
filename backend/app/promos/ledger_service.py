"""Append-only referral commission ledger writes and reversals."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.payments.models import Order
from app.promos.attribution import ItemAttributionWinner
from app.promos.constants import COMMISSION_TYPE_FLAT, COMMISSION_TYPE_REWARD_ONLY
from app.promos.referral_ledger import ReferralAttribution, ReferralCommissionEntry


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_item_commission(win: ItemAttributionWinner) -> Decimal:
    if win.commission_type == COMMISSION_TYPE_REWARD_ONLY:
        owed = Decimal("0")
    elif win.commission_type == COMMISSION_TYPE_FLAT or win.commission_mode == "fixed":
        qty = int(win.order_item.quantity or 0)
        owed = Decimal(win.commission_rate) * Decimal(qty)
    else:
        owed = win.eligible_commission_base * (
            Decimal(win.commission_rate) / Decimal("100")
        )
    owed = _q(owed)
    if win.max_commission_per_order is not None:
        owed = min(owed, _q(Decimal(win.max_commission_per_order)))
    return owed


def map_attribution_source(raw: str | None) -> str | None:
    if not raw:
        return None
    if raw == "explicit":
        return "explicit_code"
    if raw in {"link", "touch"}:
        return "touch"
    if raw == "cookie":
        return "cookie"
    return raw


def record_item_earning(
    db: Session,
    *,
    order: Order,
    win: ItemAttributionWinner,
    attribution_source: str | None = None,
) -> ReferralCommissionEntry | None:
    """Create attribution + earning ledger entry. Idempotent per item key."""
    from app.events.models import Event

    item = win.order_item
    item_key = win.attribution_item_key
    attr_idem = f"referral-attr:{order.id}:{item_key}"
    earn_idem = f"referral-earning:{order.id}:{item_key}"

    existing_earn = db.scalar(
        select(ReferralCommissionEntry).where(
            ReferralCommissionEntry.idempotency_key == earn_idem
        )
    )
    if existing_earn is not None:
        return existing_earn

    event = db.get(Event, order.event_id) if order.event_id else None
    host_id = (
        event.host_id
        if event is not None
        else (getattr(order, "host_id", None) or win.ambassador.host_id)
    )

    existing_attr = db.scalar(
        select(ReferralAttribution).where(
            ReferralAttribution.order_id == order.id,
            ReferralAttribution.attribution_item_key == item_key,
        )
    )
    if existing_attr is None:
        existing_attr = ReferralAttribution(
            id=uuid.uuid4(),
            order_id=order.id,
            order_item_id=item.id,
            attribution_item_key=item_key,
            program_id=win.program_id,
            campaign_id=win.campaign_id,
            enrollment_id=win.ambassador.id,
            ambassador_user_id=win.ambassador.user_id,
            event_id=order.event_id,
            host_id=host_id,
            product_type=win.product_type,
            product_id=win.product_id,
            payer_type=win.payer_type,
            winning_scope=win.winning_scope,
            attribution_source=map_attribution_source(
                attribution_source or getattr(order, "referral_attribution_source", None)
            ),
            idempotency_key=attr_idem,
            resolved_at=datetime.now(UTC),
        )
        db.add(existing_attr)
        db.flush()

    amount = compute_item_commission(win)
    if amount < 0:
        return None
    if amount == 0 and win.commission_type != COMMISSION_TYPE_REWARD_ONLY:
        return None

    hold_until = datetime.now(UTC) + timedelta(days=max(0, win.hold_period_days))
    entry = ReferralCommissionEntry(
        id=uuid.uuid4(),
        attribution_id=existing_attr.id,
        program_id=win.program_id,
        campaign_id=win.campaign_id,
        rule_id=win.rule_id,
        enrollment_id=win.ambassador.id,
        ambassador_user_id=win.ambassador.user_id,
        order_id=order.id,
        order_item_id=item.id,
        attribution_item_key=item_key,
        event_id=order.event_id,
        host_id=existing_attr.host_id,
        product_type=win.product_type,
        payer_type=win.payer_type,
        entry_type="earning",
        original_entry_id=None,
        gross_item_amount=_q(win.gross_item_amount),
        eligible_commission_base=_q(win.eligible_commission_base),
        commission_mode=win.commission_mode,
        commission_rate=Decimal(win.commission_rate),
        commission_amount=amount,
        currency=getattr(order, "currency", None) or "NGN",
        status="pending",
        idempotency_key=earn_idem,
        source_event_id=f"order-paid:{order.id}",
        payable_at=hold_until,
    )
    db.add(entry)
    db.flush()
    write_audit_log(
        db,
        action="referrals.commission_earning",
        actor_user_id=order.buyer_user_id,
        resource_type="referral_commission_entry",
        resource_id=str(entry.id),
        details={
            "order_id": str(order.id),
            "attribution_item_key": item_key,
            "payer_type": win.payer_type,
            "commission_amount": str(amount),
            "enrollment_id": str(win.ambassador.id),
        },
    )
    return entry


def remaining_reversible_amount(
    db: Session, *, earning: ReferralCommissionEntry
) -> Decimal:
    if earning.entry_type != "earning":
        return Decimal("0")
    reversed_sum = db.scalar(
        select(func.coalesce(func.sum(ReferralCommissionEntry.commission_amount), 0)).where(
            ReferralCommissionEntry.original_entry_id == earning.id,
            ReferralCommissionEntry.entry_type == "reversal",
        )
    )
    already = abs(_q(Decimal(reversed_sum or 0)))
    original = _q(Decimal(earning.commission_amount))
    return max(Decimal("0"), original - already)


def append_reversal_for_earning(
    db: Session,
    *,
    earning: ReferralCommissionEntry,
    amount: Decimal,
    reason: str,
    source_event_id: str,
    actor_user_id: UUID | None = None,
    allocation_id: str | None = None,
) -> ReferralCommissionEntry | None:
    """Append a negative reversal. Never exceeds remaining unreversed earning.

    Idempotency distinguishes refund event + earning + allocation:
    ``referral-reversal:{source_event_id}:{earning.id}:{allocation_id}``
    """
    alloc = allocation_id or "default"
    idem = f"referral-reversal:{source_event_id}:{earning.id}:{alloc}"
    existing = db.scalar(
        select(ReferralCommissionEntry).where(
            ReferralCommissionEntry.idempotency_key == idem
        )
    )
    if existing is not None:
        return existing

    remaining = remaining_reversible_amount(db, earning=earning)
    to_reverse = min(_q(abs(Decimal(amount))), remaining)
    if to_reverse <= 0:
        return None

    ratio = (
        to_reverse / Decimal(earning.commission_amount)
        if Decimal(earning.commission_amount) != 0
        else Decimal("1")
    )
    entry = ReferralCommissionEntry(
        id=uuid.uuid4(),
        attribution_id=earning.attribution_id,
        program_id=earning.program_id,
        campaign_id=earning.campaign_id,
        rule_id=earning.rule_id,
        enrollment_id=earning.enrollment_id,
        ambassador_user_id=earning.ambassador_user_id,
        order_id=earning.order_id,
        order_item_id=earning.order_item_id,
        attribution_item_key=earning.attribution_item_key,
        event_id=earning.event_id,
        host_id=earning.host_id,
        product_type=earning.product_type,
        payer_type=earning.payer_type,
        entry_type="reversal",
        original_entry_id=earning.id,
        gross_item_amount=_q(Decimal(earning.gross_item_amount) * ratio),
        eligible_commission_base=_q(
            Decimal(earning.eligible_commission_base) * ratio
        ),
        commission_mode=earning.commission_mode,
        commission_rate=earning.commission_rate,
        commission_amount=_q(-to_reverse),
        currency=earning.currency,
        status=earning.status if earning.status in {"paid", "payable", "approved"} else "pending",
        idempotency_key=idem,
        source_event_id=source_event_id,
        notes=(reason or "Refund/reversal")[:500],
    )
    db.add(entry)
    db.flush()
    write_audit_log(
        db,
        action="referrals.commission_reversal",
        actor_user_id=actor_user_id,
        resource_type="referral_commission_entry",
        resource_id=str(entry.id),
        details={
            "original_entry_id": str(earning.id),
            "amount": str(entry.commission_amount),
            "source_event_id": source_event_id,
            "allocation_id": alloc,
            "reason": entry.notes,
        },
    )
    return entry


def reverse_commissions_for_order(
    db: Session,
    *,
    order_id: UUID,
    reason: str,
    source_event_id: str | None = None,
    actor_user_id: UUID | None = None,
    refund_fraction: Decimal | None = None,
    allocation_id: str | None = None,
) -> list[ReferralCommissionEntry]:
    """Full or proportional reversal for all earnings on an order.

    refund_fraction: 0–1 of remaining commission to reverse (None = full remaining).
    Prefer line-item allocations via ``refund_allocations`` for mixed carts.
    """
    earnings = list(
        db.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order_id,
                ReferralCommissionEntry.entry_type == "earning",
            )
        ).all()
    )
    src = source_event_id or f"order-refund:{order_id}"
    out: list[ReferralCommissionEntry] = []
    for earning in earnings:
        remaining = remaining_reversible_amount(db, earning=earning)
        if remaining <= 0:
            continue
        if refund_fraction is None:
            amount = remaining
        else:
            frac = max(Decimal("0"), min(Decimal("1"), Decimal(refund_fraction)))
            amount = _q(remaining * frac)
        row = append_reversal_for_earning(
            db,
            earning=earning,
            amount=amount,
            reason=reason,
            source_event_id=src,
            actor_user_id=actor_user_id,
            allocation_id=allocation_id or ("full" if refund_fraction is None else f"frac:{refund_fraction}"),
        )
        if row is not None:
            out.append(row)
    return out


def reverse_commission_for_order_item(
    db: Session,
    *,
    order_id: UUID,
    order_item_id: UUID,
    refunded_base: Decimal,
    reason: str,
    source_event_id: str,
    actor_user_id: UUID | None = None,
    allocation_id: str | None = None,
    refunded_quantity: int | None = None,
) -> ReferralCommissionEntry | None:
    """Proportional reversal for one item using original rate/base snapshot."""
    earning = db.scalar(
        select(ReferralCommissionEntry).where(
            ReferralCommissionEntry.order_id == order_id,
            ReferralCommissionEntry.order_item_id == order_item_id,
            ReferralCommissionEntry.entry_type == "earning",
        )
    )
    if earning is None:
        # Fallback: match attribution_item_key
        earning = db.scalar(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order_id,
                ReferralCommissionEntry.attribution_item_key == str(order_item_id),
                ReferralCommissionEntry.entry_type == "earning",
            )
        )
    if earning is None:
        return None
    base = Decimal(earning.eligible_commission_base or 0)
    alloc = allocation_id or (
        f"{order_item_id}:{refunded_quantity or 0}:{_q(Decimal(refunded_base))}"
    )
    if base <= 0:
        return append_reversal_for_earning(
            db,
            earning=earning,
            amount=remaining_reversible_amount(db, earning=earning),
            reason=reason,
            source_event_id=source_event_id,
            actor_user_id=actor_user_id,
            allocation_id=alloc,
        )
    fraction = min(Decimal("1"), max(Decimal("0"), Decimal(refunded_base) / base))
    target = _q(Decimal(earning.commission_amount) * fraction)
    return append_reversal_for_earning(
        db,
        earning=earning,
        amount=target,
        reason=reason,
        source_event_id=source_event_id,
        actor_user_id=actor_user_id,
        allocation_id=alloc,
    )


def host_funded_net_by_order(
    db: Session, order_ids: list[UUID]
) -> dict[UUID, Decimal]:
    """Net host-funded commission (earnings + reversals) per order for settlement."""
    if not order_ids:
        return {}
    rows = db.scalars(
        select(ReferralCommissionEntry).where(
            ReferralCommissionEntry.order_id.in_(order_ids),
            ReferralCommissionEntry.payer_type == "host",
            ReferralCommissionEntry.entry_type.in_(("earning", "reversal", "adjustment")),
        )
    ).all()
    out: dict[UUID, Decimal] = {}
    for row in rows:
        out[row.order_id] = out.get(row.order_id, Decimal("0")) + _q(
            Decimal(row.commission_amount)
        )
    # Settlement deduction uses positive liability only
    return {oid: max(Decimal("0"), amt) for oid, amt in out.items()}
