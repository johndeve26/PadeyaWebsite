"""Platform revenue reporting from append-only platform ledger."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.finance.ledger import get_or_create_host_balance
from app.finance.models import HostBalance, PlatformLedgerEntry, PayoutRequest
from app.finance.platform_ledger import mask_payment_reference
from app.users.models import User
from app.users.service import user_has_permission, user_has_role


def _q(amount: Decimal | int | float | None) -> Decimal:
    return Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _is_super_admin(user: User) -> bool:
    return user_has_role(user, "super_admin")


def assert_platform_finance_access(user: User) -> None:
    if user_has_role(user, "support_agent") and not (
        user_has_role(user, "finance_admin") or _is_super_admin(user)
    ):
        raise HTTPException(
            status_code=403, detail="Support cannot access platform finance reports"
        )
    allowed = (
        _is_super_admin(user)
        or user_has_role(user, "finance_admin")
        or user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "admin.finance.view_fees")
        or user_has_permission(user, "admin.finance.export_event_sales")
        or user_has_permission(user, "payouts.review")
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Insufficient finance permission")


def assert_platform_finance_export(user: User) -> None:
    assert_platform_finance_access(user)
    allowed_export = (
        _is_super_admin(user)
        or user_has_role(user, "finance_admin")
        or user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "admin.finance.export_event_sales")
        or user_has_permission(user, "admin.finance.view_fees")
    )
    if not allowed_export:
        raise HTTPException(status_code=403, detail="Finance export permission required")


def _signed_sum(rows: list[PlatformLedgerEntry]) -> Decimal:
    total = Decimal("0")
    for row in rows:
        amt = _q(row.amount)
        if row.direction == "debit":
            total -= amt
        else:
            total += amt
    return _q(total)


def _filter_entries(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
    entry_types: list[str] | None = None,
) -> list[PlatformLedgerEntry]:
    q = select(PlatformLedgerEntry).order_by(PlatformLedgerEntry.created_at.desc())
    if date_from is not None:
        q = q.where(PlatformLedgerEntry.created_at >= date_from)
    if date_to is not None:
        q = q.where(PlatformLedgerEntry.created_at <= date_to)
    if host_id is not None:
        q = q.where(PlatformLedgerEntry.host_id == host_id)
    if event_id is not None:
        q = q.where(PlatformLedgerEntry.event_id == event_id)
    if entry_types:
        q = q.where(PlatformLedgerEntry.entry_type.in_(entry_types))
    return list(db.scalars(q.limit(5000)).all())


def build_platform_revenue_report(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
    revenue_type: str | None = None,
) -> dict:
    type_filter: list[str] | None = None
    if revenue_type:
        mapping = {
            "buyer_fee": ["buyer_platform_fee"],
            "ticket_commission": ["host_commission"],
            "merch_commission": ["host_commission"],
            "vault_commission": ["host_commission"],
            "processing": ["processing_fee"],
            "payments": ["buyer_payment"],
            "refunds": ["refund", "chargeback"],
            "payouts": ["host_payout"],
        }
        type_filter = mapping.get(revenue_type)

    entries = _filter_entries(
        db,
        date_from=date_from,
        date_to=date_to,
        host_id=host_id,
        event_id=event_id,
        entry_types=type_filter,
    )

    by_type: dict[str, list[PlatformLedgerEntry]] = {}
    for row in entries:
        by_type.setdefault(row.entry_type, []).append(row)

    def net_type(entry_type: str) -> Decimal:
        return _signed_sum(by_type.get(entry_type, []))

    # Commission split from metadata category.
    ticket_commission = Decimal("0")
    merch_commission = Decimal("0")
    vault_commission = Decimal("0")
    for row in by_type.get("host_commission", []):
        meta = row.metadata_json or {}
        cat = str(meta.get("category") or "ticket")
        signed = _q(row.amount) if row.direction == "credit" else -_q(row.amount)
        if cat == "merch":
            merch_commission += signed
        elif cat == "vault":
            vault_commission += signed
        else:
            ticket_commission += signed

    # Adjustments that reverse commissions
    for row in by_type.get("adjustment", []):
        meta = row.metadata_json or {}
        if meta.get("reverses") == "host_commission":
            ticket_commission -= _q(row.amount) if row.direction == "debit" else -_q(
                row.amount
            )

    buyer_fee_rev = net_type("buyer_platform_fee")
    for row in by_type.get("adjustment", []):
        meta = row.metadata_json or {}
        if meta.get("reverses") == "buyer_platform_fee" and row.direction == "debit":
            buyer_fee_rev -= _q(row.amount)

    platform_revenue = _q(
        buyer_fee_rev
        + ticket_commission
        + merch_commission
        + vault_commission
        + net_type("processing_fee")
    )

    # Host payable from balances (filtered host or platform-wide).
    if host_id is not None:
        bal = get_or_create_host_balance(db, host_id)
        host_net_payable = _q(bal.available_balance + bal.pending_payout_balance)
        pending_payouts = _q(bal.pending_payout_balance)
        payouts_completed = _q(bal.lifetime_paid_out)
    else:
        balances = list(db.scalars(select(HostBalance)).all())
        host_net_payable = _q(
            sum(
                (b.available_balance + b.pending_payout_balance for b in balances),
                Decimal("0"),
            )
        )
        pending_payouts = _q(
            sum((b.pending_payout_balance for b in balances), Decimal("0"))
        )
        payouts_completed = _q(
            sum((b.lifetime_paid_out for b in balances), Decimal("0"))
        )

    open_payout_q = select(func.count()).select_from(PayoutRequest).where(
        PayoutRequest.status.in_(["requested", "under_review", "approved"])
    )
    if host_id is not None:
        open_payout_q = open_payout_q.where(PayoutRequest.host_id == host_id)
    open_payout_count = int(db.scalar(open_payout_q) or 0)

    summary = {
        "currency": "NGN",
        "gross_payment_volume": net_type("buyer_payment"),
        "platform_revenue": platform_revenue,
        "ticket_commission_revenue": _q(ticket_commission),
        "buyer_service_fee_revenue": _q(buyer_fee_rev),
        "merch_commission_revenue": _q(merch_commission),
        "vault_commission_revenue": _q(vault_commission),
        "processing_fee_revenue": net_type("processing_fee"),
        "ticket_revenue": net_type("ticket_revenue"),
        "merch_revenue": net_type("merch_revenue"),
        "vault_revenue": net_type("vault_revenue"),
        "refunds": abs(net_type("refund")) + abs(net_type("chargeback")),
        "ambassador_rewards": abs(net_type("ambassador_reward")),
        "host_net_payable": host_net_payable,
        "payouts_completed": payouts_completed
        if host_id is not None
        else abs(net_type("host_payout")) or payouts_completed,
        "pending_payouts": pending_payouts,
        "open_payout_requests": open_payout_count,
        "entry_count": len(entries),
    }

    # Apply revenue_type filter for commission category display
    if revenue_type == "ticket_commission":
        summary["platform_revenue"] = _q(ticket_commission)
    elif revenue_type == "merch_commission":
        summary["platform_revenue"] = _q(merch_commission)
    elif revenue_type == "vault_commission":
        summary["platform_revenue"] = _q(vault_commission)

    entry_rows = [
        {
            "id": str(e.id),
            "entry_type": e.entry_type,
            "direction": e.direction,
            "amount": e.amount,
            "currency": e.currency,
            "order_id": str(e.order_id) if e.order_id else None,
            "host_id": str(e.host_id) if e.host_id else None,
            "event_id": str(e.event_id) if e.event_id else None,
            "description": e.description,
            "reference_type": e.reference_type,
            "reference_id": e.reference_id,
            "payment_reference_masked": (
                (e.metadata_json or {}).get("payment_reference")
                if isinstance(e.metadata_json, dict)
                else None
            )
            or mask_payment_reference(None),
            "category": (e.metadata_json or {}).get("category")
            if isinstance(e.metadata_json, dict)
            else None,
            "created_at": e.created_at,
        }
        for e in entries[:500]
    ]

    return {
        "summary": summary,
        "filters": {
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "host_id": str(host_id) if host_id else None,
            "event_id": str(event_id) if event_id else None,
            "revenue_type": revenue_type,
        },
        "entries": entry_rows,
    }


def platform_revenue_csv(report: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "amount"])
    for key, value in report["summary"].items():
        writer.writerow([key, value])
    writer.writerow([])
    writer.writerow(
        [
            "entry_type",
            "direction",
            "amount",
            "currency",
            "order_id",
            "host_id",
            "event_id",
            "description",
            "payment_reference_masked",
            "category",
            "created_at",
        ]
    )
    for row in report.get("entries") or []:
        writer.writerow(
            [
                row.get("entry_type"),
                row.get("direction"),
                row.get("amount"),
                row.get("currency"),
                row.get("order_id") or "",
                row.get("host_id") or "",
                row.get("event_id") or "",
                row.get("description") or "",
                row.get("payment_reference_masked") or "",
                row.get("category") or "",
                row.get("created_at").isoformat()
                if hasattr(row.get("created_at"), "isoformat")
                else row.get("created_at") or "",
            ]
        )
    return buf.getvalue()
