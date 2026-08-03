"""Authoritative line-item referral commission reversals on refund.

Fixed-commission refund policy
------------------------------
Original earning snapshots are immutable. Fixed / flat rules that were applied as
``rate × quantity`` reverse proportionally to the refunded quantity (or to the
refunded eligible base when provided):

  reversal = original_commission × (refunded_qty / original_qty)

When ``refunded_item_subtotal`` is provided it is treated as the refunded eligible
commission base and:

  reversal = original_commission × (refunded_base / original_eligible_base)

Later rule edits never affect reversals — only the earning snapshot is used.

Legacy orders without line allocations
--------------------------------------
- Full refunds reverse remaining commission on every earning.
- Partial refunds without allocations are allowed only when every earning on the
  order shares the same payer_type, commission_mode, and commission_rate
  (homogeneous). Otherwise finance must supply explicit line allocations; we set
  ``requires_referral_refund_allocation`` and refuse silent order-total spreading
  across mixed host/platform earnings.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.payments.models import Order, OrderItem
from app.promos.ledger_service import (
    append_reversal_for_earning,
    remaining_reversible_amount,
)
from app.promos.referral_ledger import ReferralCommissionEntry


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineRefundAllocation:
    """One refunded order line (authoritative commission-reversal input)."""

    order_item_id: UUID
    refunded_quantity: int
    refunded_item_subtotal: Decimal
    allocation_id: str | None = None
    provider_refund_reference: str | None = None


class ReferralRefundAllocationError(Exception):
    """Controlled validation failure for line-item referral refunds."""

    def __init__(self, detail: str, *, code: str = "referral_refund_invalid"):
        super().__init__(detail)
        self.detail = detail
        self.code = code


def _earnings_for_item(
    db: Session, *, order_id: UUID, order_item_id: UUID
) -> list[ReferralCommissionEntry]:
    earnings = list(
        db.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order_id,
                ReferralCommissionEntry.order_item_id == order_item_id,
                ReferralCommissionEntry.entry_type == "earning",
            )
        ).all()
    )
    if earnings:
        return earnings
    return list(
        db.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order_id,
                ReferralCommissionEntry.attribution_item_key == str(order_item_id),
                ReferralCommissionEntry.entry_type == "earning",
            )
        ).all()
    )


def _earning_for_item(
    db: Session, *, order_id: UUID, order_item_id: UUID
) -> ReferralCommissionEntry | None:
    """Back-compat: first earning for an item (prefer host when dual)."""
    rows = _earnings_for_item(db, order_id=order_id, order_item_id=order_item_id)
    if not rows:
        return None
    for row in rows:
        if row.payer_type == "host":
            return row
    return rows[0]


def _prior_refunded_quantity(db: Session, *, earning: ReferralCommissionEntry) -> int:
    """Estimate previously refunded units from prior reversals vs original qty snapshot."""
    item = (
        db.get(OrderItem, earning.order_item_id) if earning.order_item_id else None
    )
    if item is None or int(item.quantity or 0) <= 0:
        return 0
    original_qty = int(item.quantity)
    remaining = remaining_reversible_amount(db, earning=earning)
    original = _q(Decimal(earning.commission_amount))
    if original <= 0:
        return original_qty
    remaining_ratio = remaining / original
    remaining_qty = int(
        (Decimal(original_qty) * remaining_ratio).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )
    return max(0, original_qty - remaining_qty)


def _prior_refunded_base(db: Session, *, earning: ReferralCommissionEntry) -> Decimal:
    original_base = _q(Decimal(earning.eligible_commission_base or 0))
    if original_base <= 0:
        return Decimal("0")
    remaining_amt = remaining_reversible_amount(db, earning=earning)
    original_amt = _q(Decimal(earning.commission_amount))
    if original_amt <= 0:
        return original_base
    remaining_base = _q(original_base * (remaining_amt / original_amt))
    return max(Decimal("0"), original_base - remaining_base)


def validate_line_allocations(
    db: Session,
    *,
    order: Order,
    allocations: list[LineRefundAllocation],
    currency: str | None = None,
) -> list[tuple[LineRefundAllocation, OrderItem, list[ReferralCommissionEntry]]]:
    if not allocations:
        raise ReferralRefundAllocationError(
            "line_allocations required for this refund",
            code="referral_refund_allocations_required",
        )

    order_currency = (getattr(order, "currency", None) or "NGN").upper()
    if currency and currency.upper() != order_currency:
        raise ReferralRefundAllocationError(
            f"Currency mismatch: expected {order_currency}",
            code="referral_refund_currency_mismatch",
        )

    items_by_id = {item.id: item for item in list(order.items or [])}
    seen: set[UUID] = set()
    out: list[tuple[LineRefundAllocation, OrderItem, list[ReferralCommissionEntry]]] = []

    for alloc in allocations:
        if alloc.order_item_id in seen:
            raise ReferralRefundAllocationError(
                f"Duplicate allocation for order item {alloc.order_item_id}",
                code="referral_refund_duplicate_item",
            )
        seen.add(alloc.order_item_id)

        if alloc.refunded_quantity <= 0:
            raise ReferralRefundAllocationError(
                "refunded_quantity must be positive",
                code="referral_refund_bad_quantity",
            )
        if Decimal(alloc.refunded_item_subtotal) <= 0:
            raise ReferralRefundAllocationError(
                "refunded_item_subtotal must be positive",
                code="referral_refund_bad_amount",
            )
        if Decimal(alloc.refunded_item_subtotal) < 0:
            raise ReferralRefundAllocationError(
                "refunded_item_subtotal cannot be negative",
                code="referral_refund_negative_amount",
            )

        item = items_by_id.get(alloc.order_item_id)
        if item is None:
            # Confirm existence but wrong order
            orphan = db.get(OrderItem, alloc.order_item_id)
            if orphan is None:
                raise ReferralRefundAllocationError(
                    f"Unknown order item {alloc.order_item_id}",
                    code="referral_refund_unknown_item",
                )
            raise ReferralRefundAllocationError(
                f"Order item {alloc.order_item_id} does not belong to this order",
                code="referral_refund_item_order_mismatch",
            )

        purchased = int(item.quantity or 0)
        earnings = _earnings_for_item(db, order_id=order.id, order_item_id=item.id)
        earning = earnings[0] if earnings else None
        already_qty = _prior_refunded_quantity(db, earning=earning) if earning else 0
        if alloc.refunded_quantity + already_qty > purchased:
            raise ReferralRefundAllocationError(
                f"refunded_quantity exceeds remaining purchasable quantity for item {item.id}",
                code="referral_refund_quantity_exceeded",
            )

        line_total = _q(Decimal(item.line_total or 0))
        already_base = _prior_refunded_base(db, earning=earning) if earning else Decimal("0")
        refunded_sub = _q(Decimal(alloc.refunded_item_subtotal))
        if already_base + refunded_sub > line_total + Decimal("0.01"):
            # Allow eligible-base which may be <= line_total; cap vs line_total
            if already_base + refunded_sub > line_total:
                # Still allow if within eligible base remaining
                if earning is not None:
                    orig_base = _q(Decimal(earning.eligible_commission_base or 0))
                    if already_base + refunded_sub > orig_base + Decimal("0.01"):
                        raise ReferralRefundAllocationError(
                            f"Cumulative refunded subtotal exceeds item eligible base for {item.id}",
                            code="referral_refund_subtotal_exceeded",
                        )
                else:
                    raise ReferralRefundAllocationError(
                        f"Cumulative refunded subtotal exceeds item subtotal for {item.id}",
                        code="referral_refund_subtotal_exceeded",
                    )

        out.append((alloc, item, earnings))
    return out


def earnings_are_homogeneous(earnings: list[ReferralCommissionEntry]) -> bool:
    if len(earnings) <= 1:
        return True
    first = earnings[0]
    for row in earnings[1:]:
        if (
            row.payer_type != first.payer_type
            or row.commission_mode != first.commission_mode
            or _q(Decimal(row.commission_rate or 0))
            != _q(Decimal(first.commission_rate or 0))
        ):
            return False
    return True


def compute_reversal_amount_for_allocation(
    *,
    earning: ReferralCommissionEntry,
    item: OrderItem,
    alloc: LineRefundAllocation,
) -> Decimal:
    """Proportional reversal from immutable earning snapshot."""
    original = _q(Decimal(earning.commission_amount))
    if original <= 0:
        return Decimal("0")

    original_base = _q(Decimal(earning.eligible_commission_base or 0))
    refunded_base = _q(Decimal(alloc.refunded_item_subtotal))
    if original_base > 0 and refunded_base > 0:
        fraction = min(Decimal("1"), max(Decimal("0"), refunded_base / original_base))
        return _q(original * fraction)

    # Fixed / zero-base fallback: quantity share of the original line
    qty = int(item.quantity or 0)
    if qty <= 0:
        return Decimal("0")
    fraction = min(
        Decimal("1"),
        max(Decimal("0"), Decimal(alloc.refunded_quantity) / Decimal(qty)),
    )
    return _q(original * fraction)


def apply_line_item_referral_reversals(
    db: Session,
    *,
    order: Order,
    allocations: list[LineRefundAllocation],
    refund_event_id: str,
    reason: str,
    actor_user_id: UUID | None = None,
    currency: str | None = None,
) -> list[ReferralCommissionEntry]:
    """Reverse commission only for allocated lines. Never mutates original earnings."""
    validated = validate_line_allocations(
        db, order=order, allocations=allocations, currency=currency
    )
    out: list[ReferralCommissionEntry] = []
    for alloc, item, earnings in validated:
        if not earnings:
            # Excluded / unattributed line — no ledger work
            continue
        for earning in earnings:
            amount = compute_reversal_amount_for_allocation(
                earning=earning, item=item, alloc=alloc
            )
            remaining = remaining_reversible_amount(db, earning=earning)
            if amount > remaining:
                amount = remaining
            if amount <= 0:
                continue
            allocation_id = (
                alloc.allocation_id
                or f"{alloc.order_item_id}:{alloc.refunded_quantity}:{_q(Decimal(alloc.refunded_item_subtotal))}:{earning.payer_type}"
            )
            row = append_reversal_for_earning(
                db,
                earning=earning,
                amount=amount,
                reason=reason,
                source_event_id=refund_event_id,
                actor_user_id=actor_user_id,
                allocation_id=allocation_id,
            )
            if row is not None:
                out.append(row)
    return out


def apply_referral_reversals_for_finance_refund(
    db: Session,
    *,
    order: Order,
    refund_id: UUID,
    requested_amount: Decimal,
    reason: str,
    actor_user_id: UUID | None,
    allocations: list[LineRefundAllocation] | None,
    is_full_refund: bool,
) -> tuple[list[ReferralCommissionEntry], bool]:
    """Finance approve hook.

    Returns (reversals, requires_referral_refund_allocation).
    Raises HTTPException for malformed partials without a safe path.
    """
    refund_event_id = f"finance-refund:{refund_id}"
    earnings = list(
        db.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order.id,
                ReferralCommissionEntry.entry_type == "earning",
            )
        ).all()
    )
    if not earnings:
        return [], False

    if allocations:
        rows = apply_line_item_referral_reversals(
            db,
            order=order,
            allocations=allocations,
            refund_event_id=refund_event_id,
            reason=reason,
            actor_user_id=actor_user_id,
            currency=getattr(order, "currency", None),
        )
        return rows, False

    if is_full_refund:
        from app.promos.ledger_service import reverse_commissions_for_order

        rows = reverse_commissions_for_order(
            db,
            order_id=order.id,
            reason=reason,
            source_event_id=refund_event_id,
            actor_user_id=actor_user_id,
            refund_fraction=None,
            allocation_id="full",
        )
        return rows, False

    # Partial without allocations — conservative legacy path
    if not earnings_are_homogeneous(earnings):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "requires_referral_refund_allocation",
                "message": (
                    "Partial refund on mixed referral earnings requires explicit "
                    "line_allocations (order_item_id, refunded_quantity, "
                    "refunded_item_subtotal). Order-total fraction allocation is not allowed."
                ),
            },
        )

    # Homogeneous: distribute by eligible base share of requested vs order total
    # only when every earning shares payer/rate/mode — still item-proportional by base.
    order_total = _q(Decimal(order.total_amount or 0))
    requested = _q(Decimal(requested_amount or 0))
    if order_total <= 0 or requested <= 0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "requires_referral_refund_allocation",
                "message": "Cannot derive referral reversal without line_allocations",
            },
        )
    # Deterministic: reverse the same fraction of each earning's remaining amount
    # because payer/rate/basis match — NOT mixed host/platform spreading.
    frac = min(Decimal("1"), max(Decimal("0"), requested / order_total))
    from app.promos.ledger_service import reverse_commissions_for_order

    rows = reverse_commissions_for_order(
        db,
        order_id=order.id,
        reason=reason + " (homogeneous legacy allocation)",
        source_event_id=refund_event_id,
        actor_user_id=actor_user_id,
        refund_fraction=frac,
        allocation_id=f"homogeneous:{frac}",
    )
    return rows, False


def parse_allocation_payloads(
    raw: list[dict] | None,
) -> list[LineRefundAllocation] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ReferralRefundAllocationError(
            "line_allocations must be a list",
            code="referral_refund_bad_payload",
        )
    out: list[LineRefundAllocation] = []
    for idx, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ReferralRefundAllocationError(
                f"line_allocations[{idx}] must be an object",
                code="referral_refund_bad_payload",
            )
        try:
            oid = UUID(str(row["order_item_id"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise ReferralRefundAllocationError(
                f"line_allocations[{idx}].order_item_id is required",
                code="referral_refund_bad_payload",
            ) from exc
        try:
            qty = int(row.get("refunded_quantity") or 0)
        except (TypeError, ValueError) as exc:
            raise ReferralRefundAllocationError(
                f"line_allocations[{idx}].refunded_quantity invalid",
                code="referral_refund_bad_quantity",
            ) from exc
        try:
            sub = Decimal(str(row.get("refunded_item_subtotal", "0")))
        except Exception as exc:
            raise ReferralRefundAllocationError(
                f"line_allocations[{idx}].refunded_item_subtotal invalid",
                code="referral_refund_bad_amount",
            ) from exc
        alloc_id = row.get("allocation_id")
        provider_ref = row.get("provider_refund_reference")
        out.append(
            LineRefundAllocation(
                order_item_id=oid,
                refunded_quantity=qty,
                refunded_item_subtotal=sub,
                allocation_id=str(alloc_id) if alloc_id else None,
                provider_refund_reference=(
                    str(provider_ref) if provider_ref else None
                ),
            )
        )
    return out


def new_allocation_row_id() -> str:
    return str(uuid.uuid4())


def sum_prior_allocation_subtotals(
    db: Session, *, order_item_id: UUID
) -> Decimal:
    """Optional helper for callers tracking JSON allocations on refund requests."""
    # Reversals already encode remaining; this is a no-op placeholder for finance UIs.
    _ = db
    _ = order_item_id
    return Decimal("0")
