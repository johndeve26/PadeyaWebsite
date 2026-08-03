"""Host / admin earnings reports — gross, deductions, net after Pàdéyá fees.

Host gross = item subtotal after discounts (+ shipping), before host-paid deductions.
Buyer-paid platform / service fees never inflate host gross.
Host net = host gross − host-paid fees − ambassador rewards − refunds (floored at 0).
"""

from __future__ import annotations

import csv
import io
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event
from app.finance.earnings_schemas import (
    EarningsOrderRow,
    EarningsSummary,
    HostEarningsReport,
    HostFeeTermPublic,
)
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
from app.finance.fees.fee_calculation_service import FeeCalculationService
from app.finance.fees.models import OrderFeeSnapshot
from app.finance.fees.money import minor_to_major
from app.finance.ledger import get_or_create_host_balance
from app.finance.models import LedgerEntry, Refund
from app.hosts.models import Host
from app.hosts.team_access import require_host_for_permission
from app.payments.models import Order, OrderItem
from app.promos.models import AmbassadorSale
from app.users.models import User
from app.users.service import user_has_permission, user_has_role
from app.vault.models import VaultPurchase


def _is_super_admin(user: User) -> bool:
    return user_has_role(user, "super_admin")

PAID_ORDER_STATUSES = ("paid", "partially_refunded", "refunded")
ACTIVE_AMBASSADOR_STATUSES = (
    "attributed",
    "estimated",
    "approved",
    "payable",
    "paid",
)


def _q(amount: Decimal | int | str | None) -> Decimal:
    return Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _assert_admin_earnings_access(user: User) -> None:
    """Admin/finance staff only — host `payments.view` is not enough."""
    if user_has_role(user, "support_agent") and not (
        user_has_role(user, "finance_admin") or _is_super_admin(user)
    ):
        raise HTTPException(
            status_code=403, detail="Support cannot access earnings reports"
        )
    allowed = (
        _is_super_admin(user)
        or user_has_role(user, "finance_admin")
        or user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "admin.finance.view_fees")
        or user_has_permission(user, "admin.finance.manage_fees")
        or user_has_permission(user, "payouts.review")
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Insufficient permission")


def _host_fee_terms(db: Session, host_id: UUID) -> list[HostFeeTermPublic]:
    calc = FeeCalculationService(db)
    settings = calc.get_active_fee_settings(
        host_id,
        fee_keys=[
            FEE_KEY_TICKET_COMMISSION,
            FEE_KEY_TICKET_FIXED,
            FEE_KEY_MERCH_COMMISSION,
            FEE_KEY_MERCH_FIXED,
            FEE_KEY_VAULT_COMMISSION,
            FEE_KEY_VAULT_FIXED,
            FEE_KEY_BUYER_SERVICE,
            FEE_KEY_PAYMENT_PROCESSING,
        ],
    )
    out: list[HostFeeTermPublic] = []
    for s in settings:
        fixed_major = None
        if s.fixed_value is not None:
            fixed_major = _q(minor_to_major(int(s.fixed_value), currency=s.currency))
        out.append(
            HostFeeTermPublic(
                fee_key=s.fee_key,
                label=s.label,
                category=s.category,
                fee_type=s.fee_type,
                percentage_value=s.percentage_value,
                fixed_value_major=fixed_major,
                currency=s.currency or "NGN",
                payer=s.payer,
                source=s.source,
                enabled=bool(s.enabled),
            )
        )
    return out


def _item_gross_by_kind(items: list[OrderItem]) -> tuple[Decimal, Decimal]:
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


def _item_label(items: list[OrderItem]) -> str:
    if not items:
        return "Order"
    names: list[str] = []
    for item in items[:3]:
        label = (
            item.ticket_type_name
            or item.product_name
            or (getattr(item, "item_kind", None) or "item")
        )
        names.append(f"{label} ×{item.quantity}")
    extra = len(items) - 3
    if extra > 0:
        names.append(f"+{extra} more")
    return ", ".join(names)


def _snapshot_host_processing(db: Session, order_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not order_ids:
        return {}
    rows = db.scalars(
        select(OrderFeeSnapshot).where(
            OrderFeeSnapshot.order_id.in_(order_ids),
            OrderFeeSnapshot.fee_key == FEE_KEY_PAYMENT_PROCESSING,
            OrderFeeSnapshot.payer == "host",
        )
    ).all()
    out: dict[UUID, Decimal] = {}
    for row in rows:
        out[row.order_id] = out.get(row.order_id, Decimal("0")) + _q(
            minor_to_major(int(row.amount), currency=row.currency or "NGN")
        )
    return out


def _ambassador_by_order(
    db: Session, order_ids: list[UUID]
) -> dict[UUID, Decimal]:
    """Host-funded referral commission liability from the append-only ledger."""
    from app.promos.ledger_service import host_funded_net_by_order

    return host_funded_net_by_order(db, order_ids)


def _refunds_by_order(db: Session, host_id: UUID, order_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not order_ids:
        return {}
    rows = db.scalars(
        select(Refund).where(
            Refund.host_id == host_id,
            Refund.order_id.in_(order_ids),
            Refund.status == "completed",
        )
    ).all()
    out: dict[UUID, Decimal] = {}
    for row in rows:
        out[row.order_id] = out.get(row.order_id, Decimal("0")) + _q(row.amount)
    return out


def _sale_credited_order_ids(db: Session, host_id: UUID, order_ids: list[UUID]) -> set[UUID]:
    if not order_ids:
        return set()
    id_strs = {str(oid): oid for oid in order_ids}
    rows = db.scalars(
        select(LedgerEntry).where(
            LedgerEntry.host_id == host_id,
            LedgerEntry.entry_type == "sale_credit",
            LedgerEntry.reference_type == "order",
            LedgerEntry.reference_id.in_(list(id_strs.keys())),
        )
    ).all()
    credited: set[UUID] = set()
    for row in rows:
        oid = id_strs.get(str(row.reference_id))
        if oid is not None:
            credited.add(oid)
    return credited


def _vault_credited_ids(db: Session, host_id: UUID, purchase_ids: list[UUID]) -> set[UUID]:
    if not purchase_ids:
        return set()
    id_strs = {str(pid): pid for pid in purchase_ids}
    rows = db.scalars(
        select(LedgerEntry).where(
            LedgerEntry.host_id == host_id,
            LedgerEntry.entry_type == "vault_sale",
            LedgerEntry.reference_type.in_(("vault_purchase", "purchase")),
            LedgerEntry.reference_id.in_(list(id_strs.keys())),
        )
    ).all()
    credited: set[UUID] = set()
    for row in rows:
        pid = id_strs.get(str(row.reference_id))
        if pid is not None:
            credited.add(pid)
    return credited


def _split_host_fees(
    host_fee_total: Decimal, processing_host: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (commission, processing_host, other)."""
    remaining = max(Decimal("0"), _q(host_fee_total) - _q(processing_host))
    # Treat remaining host fees as Pàdéyá commission (pct + fixed product fees).
    return remaining, _q(processing_host), Decimal("0")


def build_host_earnings_report(
    db: Session,
    *,
    host_id: UUID,
    event_id: UUID | None = None,
) -> HostEarningsReport:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")

    event_title: str | None = None
    if event_id is not None:
        event = db.get(Event, event_id)
        if event is None or event.host_id != host_id:
            raise HTTPException(status_code=404, detail="Event not found")
        event_title = event.title

    order_q = (
        select(Order)
        .join(Event, Event.id == Order.event_id)
        .where(
            Event.host_id == host_id,
            Order.status.in_(PAID_ORDER_STATUSES),
        )
        .options(selectinload(Order.items))
        .order_by(Order.paid_at.desc().nullslast(), Order.created_at.desc())
    )
    if event_id is not None:
        order_q = order_q.where(Order.event_id == event_id)
    orders = list(db.scalars(order_q).all())
    order_ids = [o.id for o in orders]

    event_ids = {o.event_id for o in orders}
    events_by_id: dict[UUID, Event] = {}
    if event_ids:
        for ev in db.scalars(select(Event).where(Event.id.in_(event_ids))).all():
            events_by_id[ev.id] = ev

    processing_host_map = _snapshot_host_processing(db, order_ids)
    ambassador_map = _ambassador_by_order(db, order_ids)
    refund_map = _refunds_by_order(db, host_id, order_ids)
    credited_orders = _sale_credited_order_ids(db, host_id, order_ids)

    rows: list[EarningsOrderRow] = []
    gross_ticket = Decimal("0")
    gross_merch = Decimal("0")
    discounts_total = Decimal("0")
    shipping_total = Decimal("0")
    host_gross_total = Decimal("0")
    padeya_commission = Decimal("0")
    processing_host_total = Decimal("0")
    other_host_fees = Decimal("0")
    ambassador_total = Decimal("0")
    refunds_total = Decimal("0")
    buyer_fees_total = Decimal("0")
    platform_revenue_total = Decimal("0")
    net_from_rows = Decimal("0")

    for order in orders:
        ticket_g, merch_g = _item_gross_by_kind(list(order.items or []))
        discount = _q(order.discount_amount) + _q(
            getattr(order, "merch_discount_amount", None)
        )
        shipping = _q(getattr(order, "shipping_amount", None))
        # After discounts, before host-paid deductions; exclude buyer fees.
        merchandise_net = max(
            Decimal("0"),
            _q(order.subtotal_amount) - discount,
        )
        host_gross = _q(merchandise_net + shipping)
        buyer_fees = _q(getattr(order, "buyer_fee_total", None))
        host_fees = _q(getattr(order, "host_fee_total", None))
        processing_host = _q(processing_host_map.get(order.id))
        commission, proc_h, other = _split_host_fees(host_fees, processing_host)
        amb = _q(ambassador_map.get(order.id))
        refunded = _q(refund_map.get(order.id))
        host_net_base = _q(getattr(order, "host_net_estimate", None))
        if host_net_base == 0 and host_gross > 0 and host_fees == 0 and buyer_fees == 0:
            host_net_base = host_gross
        host_net = max(Decimal("0"), host_net_base - amb - refunded)
        platform_rev = _q(getattr(order, "platform_revenue_total", None))
        if platform_rev == 0:
            platform_rev = _q(buyer_fees + host_fees)

        payout_status = "credited" if order.id in credited_orders else "pending_credit"
        if order.status == "refunded":
            payout_status = "refunded"
        elif refunded > 0:
            payout_status = "partially_refunded"

        ev = events_by_id.get(order.event_id)
        rows.append(
            EarningsOrderRow(
                row_kind="order",
                order_id=order.id,
                reference=order.reference,
                event_id=order.event_id,
                event_title=ev.title if ev else None,
                item_label=_item_label(list(order.items or [])),
                paid_at=order.paid_at,
                payment_status=order.status,
                payout_status=payout_status,
                buyer_paid_total=_q(order.total_amount),
                item_subtotal=_q(order.subtotal_amount),
                discount_total=discount,
                shipping_amount=shipping,
                host_gross=host_gross,
                buyer_fee_total=buyer_fees,
                host_fee_total=host_fees,
                processing_fee_host=proc_h,
                ambassador_reward=amb,
                refund_amount=refunded,
                platform_revenue=platform_rev,
                host_net=host_net,
            )
        )

        gross_ticket += ticket_g
        gross_merch += merch_g
        discounts_total += discount
        shipping_total += shipping
        host_gross_total += host_gross
        padeya_commission += commission
        processing_host_total += proc_h
        other_host_fees += other
        ambassador_total += amb
        refunds_total += refunded
        buyer_fees_total += buyer_fees
        platform_revenue_total += platform_rev
        net_from_rows += host_net

    # Vault unlocks (host-scoped; optional event filter skips vault — vault is host-level)
    vault_sales = Decimal("0")
    vault_count = 0
    if event_id is None:
        purchases = list(
            db.scalars(
                select(VaultPurchase)
                .where(
                    VaultPurchase.host_id == host_id,
                    VaultPurchase.status == "paid",
                )
                .order_by(VaultPurchase.paid_at.desc().nullslast())
            ).all()
        )
        vault_count = len(purchases)
        credited_vault = _vault_credited_ids(db, host_id, [p.id for p in purchases])
        for purchase in purchases:
            fee_meta = {}
            raw = purchase.raw_response if isinstance(purchase.raw_response, dict) else {}
            if isinstance(raw.get("checkout_fees"), dict):
                fee_meta = raw["checkout_fees"]
            amount = _q(purchase.amount)
            buyer_fees = _q(fee_meta.get("buyer_fee_total"))
            host_fees = _q(fee_meta.get("host_fee_total"))
            host_net_est = fee_meta.get("host_net_estimate")
            host_gross = max(Decimal("0"), amount - buyer_fees) if buyer_fees else amount
            if host_net_est is not None:
                host_net_base = _q(host_net_est)
                host_gross = host_net_base + host_fees
            else:
                host_net_base = max(Decimal("0"), host_gross - host_fees)
            platform_rev = _q(fee_meta.get("platform_revenue_total"))
            if platform_rev == 0:
                platform_rev = _q(buyer_fees + host_fees)
            commission, proc_h, other = _split_host_fees(host_fees, Decimal("0"))
            host_net = host_net_base
            payout_status = (
                "credited" if purchase.id in credited_vault else "pending_credit"
            )
            rows.append(
                EarningsOrderRow(
                    row_kind="vault",
                    order_id=None,
                    reference=purchase.payment_reference,
                    event_id=None,
                    event_title=None,
                    item_label="Vault unlock",
                    paid_at=purchase.paid_at,
                    payment_status=purchase.status,
                    payout_status=payout_status,
                    buyer_paid_total=amount,
                    item_subtotal=host_gross,
                    discount_total=Decimal("0"),
                    shipping_amount=Decimal("0"),
                    host_gross=host_gross,
                    buyer_fee_total=buyer_fees,
                    host_fee_total=host_fees,
                    processing_fee_host=proc_h,
                    ambassador_reward=Decimal("0"),
                    refund_amount=Decimal("0"),
                    platform_revenue=platform_rev,
                    host_net=host_net,
                )
            )
            vault_sales += host_gross
            host_gross_total += host_gross
            padeya_commission += commission
            processing_host_total += proc_h
            other_host_fees += other
            buyer_fees_total += buyer_fees
            platform_revenue_total += platform_rev
            net_from_rows += host_net

    balance = get_or_create_host_balance(db, host_id)
    # Event-scoped reports use row nets; host-wide also surface ledger balances.
    if event_id is None:
        # Prefer ledger lifetime for overall truth; row net already subtracts amb+refund.
        # Keep row-computed net so fee transparency matches the table.
        net_earnings = net_from_rows
        pending = _q(balance.pending_payout_balance)
        paid_out = _q(balance.lifetime_paid_out)
        available = _q(balance.available_balance)
        # If ledger refunds exceed row map (edge), prefer max for display.
        ledger_refunds = _q(balance.lifetime_refunded)
        if ledger_refunds > refunds_total:
            refunds_total = ledger_refunds
            # Recompute net when ledger has more refunds than order map.
            net_earnings = max(
                Decimal("0"),
                host_gross_total
                - padeya_commission
                - processing_host_total
                - other_host_fees
                - ambassador_total
                - refunds_total,
            )
    else:
        net_earnings = net_from_rows
        pending = Decimal("0")
        paid_out = Decimal("0")
        available = Decimal("0")

    deductions = _q(
        padeya_commission
        + processing_host_total
        + other_host_fees
        + ambassador_total
        + refunds_total
    )

    summary = EarningsSummary(
        host_id=host_id,
        host_display_name=host.display_name,
        event_id=event_id,
        event_title=event_title,
        currency=balance.currency or "NGN",
        gross_ticket_sales=_q(gross_ticket),
        gross_merch_sales=_q(gross_merch),
        gross_vault_sales=_q(vault_sales),
        discounts_total=_q(discounts_total),
        shipping_total=_q(shipping_total),
        host_gross=_q(host_gross_total),
        padeya_commission=_q(padeya_commission),
        processing_fees_host_paid=_q(processing_host_total),
        other_host_paid_fees=_q(other_host_fees),
        ambassador_rewards=_q(ambassador_total),
        refunds_total=_q(refunds_total),
        deductions_total=deductions,
        buyer_platform_fees=_q(buyer_fees_total),
        platform_revenue_total=_q(platform_revenue_total),
        net_earnings=_q(net_earnings),
        pending_payout=_q(pending),
        paid_out=_q(paid_out),
        available_balance=_q(available),
        paid_order_count=len(orders),
        vault_sale_count=vault_count,
    )

    return HostEarningsReport(
        summary=summary,
        fee_terms=_host_fee_terms(db, host_id),
        rows=rows,
    )


def earnings_report_csv(report: HostEarningsReport) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "kind",
            "reference",
            "event",
            "item",
            "payment_status",
            "payout_status",
            "buyer_paid_total",
            "item_subtotal",
            "discount_total",
            "host_gross",
            "buyer_fees",
            "host_fees_deducted",
            "ambassador_reward",
            "refunds",
            "platform_revenue",
            "host_net",
            "paid_at",
        ]
    )
    for row in report.rows:
        writer.writerow(
            [
                row.row_kind,
                row.reference,
                row.event_title or "",
                row.item_label,
                row.payment_status,
                row.payout_status,
                str(row.buyer_paid_total),
                str(row.item_subtotal),
                str(row.discount_total),
                str(row.host_gross),
                str(row.buyer_fee_total),
                str(row.host_fee_total),
                str(row.ambassador_reward),
                str(row.refund_amount),
                str(row.platform_revenue),
                str(row.host_net),
                row.paid_at.isoformat() if row.paid_at else "",
            ]
        )
    return buf.getvalue()


def get_host_earnings_for_user(
    db: Session,
    user: User,
    *,
    event_id: UUID | None = None,
) -> HostEarningsReport:
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=None,
        permission=("finance.view_sales_summary", "finance.view_payouts"),
    )
    if event_id is not None:
        event = db.get(Event, event_id)
        if event is None or event.host_id != host.id:
            raise HTTPException(status_code=404, detail="Event not found")
    return build_host_earnings_report(db, host_id=host.id, event_id=event_id)


def get_admin_earnings(
    db: Session,
    user: User,
    *,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
) -> HostEarningsReport:
    _assert_admin_earnings_access(user)
    if event_id is not None:
        event = db.get(Event, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        if host_id is not None and event.host_id != host_id:
            raise HTTPException(status_code=400, detail="Event does not belong to host")
        return build_host_earnings_report(
            db, host_id=event.host_id, event_id=event_id
        )
    if host_id is None:
        raise HTTPException(
            status_code=400,
            detail="host_id or event_id is required for admin earnings",
        )
    return build_host_earnings_report(db, host_id=host_id, event_id=None)


def list_admin_host_earnings_overview(db: Session, user: User) -> list[dict]:
    """Lightweight per-host balance snapshot for admin earnings index."""
    _assert_admin_earnings_access(user)
    hosts = list(db.scalars(select(Host).order_by(Host.display_name.asc())).all())
    rows: list[dict] = []
    for host in hosts:
        balance = get_or_create_host_balance(db, host.id)
        if (
            balance.lifetime_earned == 0
            and balance.lifetime_paid_out == 0
            and balance.available_balance == 0
            and balance.pending_payout_balance == 0
        ):
            continue
        rows.append(
            {
                "host_id": host.id,
                "host_display_name": host.display_name,
                "currency": balance.currency or "NGN",
                "net_earnings": _q(balance.lifetime_earned),
                "refunds_total": _q(balance.lifetime_refunded),
                "pending_payout": _q(balance.pending_payout_balance),
                "paid_out": _q(balance.lifetime_paid_out),
                "available_balance": _q(balance.available_balance),
            }
        )
    return rows
