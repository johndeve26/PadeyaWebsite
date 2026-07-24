"""Merch revenue split snapshots — append-only; money truth stays on orders/payments."""

from __future__ import annotations

import csv
import io
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.constants import PLATFORM_FEE_RATE
from app.events.models import Event
from app.hosts.models import Host
from app.merch.constants import ITEM_KIND_MERCH
from app.merch.models import EventMerchProduct, MerchBundle, MerchFulfillment, MerchRevenueSplit
from app.payments.models import Order, OrderItem

ACTIVE_STATUSES = ("payable", "paid")
TOP_N = 10


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def _empty_money() -> dict:
    return {
        "gross": Decimal("0"),
        "host_amount": Decimal("0"),
        "platform_amount": Decimal("0"),
        "sponsor_amount": Decimal("0"),
        "print_partner_amount": Decimal("0"),
        "units": 0,
        "line_count": 0,
    }


def _quantize_money(bucket: dict) -> dict:
    out = dict(bucket)
    for key in (
        "gross",
        "host_amount",
        "platform_amount",
        "sponsor_amount",
        "print_partner_amount",
        "pending_amount",
        "paid_amount",
        "amount",
    ):
        if key in out and isinstance(out[key], Decimal):
            out[key] = _q(out[key])
    return out


def _add_split(bucket: dict, row: MerchRevenueSplit, units: int) -> None:
    bucket["gross"] += row.gross_amount
    bucket["host_amount"] += row.host_amount
    bucket["platform_amount"] += row.platform_amount
    bucket["sponsor_amount"] += row.sponsor_amount
    bucket["print_partner_amount"] += row.print_partner_amount
    bucket["units"] += units
    bucket["line_count"] += 1


def _item_units(db: Session, order_item_id: uuid.UUID) -> tuple[int, OrderItem | None]:
    item = db.get(OrderItem, order_item_id)
    if item is None:
        return 0, None
    return int(item.quantity or 0), item


def create_splits_for_paid_order(db: Session, order: Order) -> list[MerchRevenueSplit]:
    """Write split snapshots on verified payment only. Idempotent per order_item."""
    created: list[MerchRevenueSplit] = []
    for item in order.items or []:
        kind = getattr(item, "item_kind", None) or (
            ITEM_KIND_MERCH if item.merch_variant_id else "ticket"
        )
        if kind != ITEM_KIND_MERCH:
            continue
        existing = db.scalar(
            select(MerchRevenueSplit).where(
                MerchRevenueSplit.order_item_id == item.id
            )
        )
        if existing:
            created.append(existing)
            continue
        product = (
            db.get(EventMerchProduct, item.merch_product_id)
            if item.merch_product_id
            else None
        )
        fulfillment = db.scalar(
            select(MerchFulfillment).where(MerchFulfillment.order_item_id == item.id)
        )
        gross = _q(Decimal(item.line_total))
        platform = _q(gross * PLATFORM_FEE_RATE)
        sponsor = Decimal("0.00")
        print_partner = Decimal("0.00")
        if product and product.is_sponsor_branded and product.sponsor_split_value:
            if product.sponsor_split_type == "percent":
                sponsor = _q(gross * Decimal(product.sponsor_split_value) / Decimal("100"))
            elif product.sponsor_split_type == "fixed":
                sponsor = min(_q(Decimal(product.sponsor_split_value)), gross - platform)
        if product and product.print_on_demand_enabled:
            # Placeholder partner share — report-only until live POD billing exists.
            print_partner = Decimal("0.00")
        host_amt = _q(gross - platform - sponsor - print_partner)
        if host_amt < 0:
            host_amt = Decimal("0.00")
        host_id = None
        if product is not None:
            host_id = product.host_id
        elif fulfillment is not None:
            host_id = fulfillment.host_id
        else:
            event = db.get(Event, order.event_id)
            host_id = event.host_id if event else None
        if host_id is None:
            continue
        row = MerchRevenueSplit(
            order_id=order.id,
            order_item_id=item.id,
            host_id=host_id,
            event_id=order.event_id,
            product_id=item.merch_product_id,
            currency=order.currency,
            gross_amount=gross,
            platform_amount=platform,
            host_amount=host_amt,
            sponsor_amount=sponsor,
            print_partner_amount=print_partner,
            fulfillment_method=(
                fulfillment.fulfillment_method if fulfillment else None
            ),
            is_sponsor_branded=bool(product and product.is_sponsor_branded),
            bundle_id=getattr(item, "bundle_id", None),
            status="payable",
        )
        db.add(row)
        created.append(row)
    db.flush()
    return created


def reverse_splits_on_refund(db: Session, order: Order) -> None:
    """Mark splits reversed — do not mutate original amounts."""
    rows = list(
        db.scalars(
            select(MerchRevenueSplit).where(
                MerchRevenueSplit.order_id == order.id,
                MerchRevenueSplit.status != "reversed",
            )
        )
    )
    for row in rows:
        row.status = "reversed"
    db.flush()


def _load_splits(
    db: Session,
    *,
    host_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    statuses: tuple[str, ...] | None = None,
) -> list[MerchRevenueSplit]:
    stmt = select(MerchRevenueSplit)
    if host_id is not None:
        stmt = stmt.where(MerchRevenueSplit.host_id == host_id)
    if event_id is not None:
        stmt = stmt.where(MerchRevenueSplit.event_id == event_id)
    if statuses is not None:
        stmt = stmt.where(MerchRevenueSplit.status.in_(statuses))
    return list(db.scalars(stmt))


def _discount_impact(db: Session, rows: list[MerchRevenueSplit]) -> Decimal:
    """Sum merch discount on distinct paid orders — no buyer PII."""
    seen: set[uuid.UUID] = set()
    total = Decimal("0")
    for row in rows:
        if row.order_id in seen:
            continue
        seen.add(row.order_id)
        order = db.get(Order, row.order_id)
        if order is None:
            continue
        total += Decimal(getattr(order, "merch_discount_amount", None) or 0)
    return _q(total)


def _payout_status(rows: list[MerchRevenueSplit]) -> dict:
    payable_amt = Decimal("0")
    paid_amt = Decimal("0")
    payable_lines = 0
    paid_lines = 0
    for row in rows:
        if row.status == "payable":
            payable_amt += row.host_amount
            payable_lines += 1
        elif row.status == "paid":
            paid_amt += row.host_amount
            paid_lines += 1
    return {
        "payable": {
            "amount": _q(payable_amt),
            "line_count": payable_lines,
        },
        "paid": {
            "amount": _q(paid_amt),
            "line_count": paid_lines,
        },
        "pending_payout_amount": _q(payable_amt),
        "pending_payout_line_count": payable_lines,
    }


def _top_sorted(buckets: dict[str, dict], *, key: str = "gross", limit: int = TOP_N) -> list[dict]:
    values = [_quantize_money(v) for v in buckets.values()]
    values.sort(key=lambda b: Decimal(b.get(key) or 0), reverse=True)
    return values[:limit]


def host_revenue_report(
    db: Session,
    *,
    host_id: uuid.UUID,
    event_id: uuid.UUID | None = None,
) -> dict:
    active = _load_splits(
        db, host_id=host_id, event_id=event_id, statuses=ACTIVE_STATUSES
    )
    reversed_rows = _load_splits(
        db, host_id=host_id, event_id=event_id, statuses=("reversed",)
    )

    gross = sum((r.gross_amount for r in active), Decimal("0"))
    host_amt = sum((r.host_amount for r in active), Decimal("0"))
    platform = sum((r.platform_amount for r in active), Decimal("0"))
    sponsor = sum((r.sponsor_amount for r in active), Decimal("0"))
    print_partner = sum((r.print_partner_amount for r in active), Decimal("0"))
    refunds_gross = sum((r.gross_amount for r in reversed_rows), Decimal("0"))
    refunds_host = sum((r.host_amount for r in reversed_rows), Decimal("0"))

    units = 0
    refund_units = 0
    by_product: dict[str, dict] = {}
    by_event: dict[str, dict] = {}
    by_variant: dict[str, dict] = {}
    by_fulfillment: dict[str, dict] = {}
    by_bundle: dict[str, dict] = {}
    sponsor_lines: list[dict] = []
    bundle_gross = Decimal("0")
    sponsor_branded_gross = Decimal("0")

    for r in active:
        qty, item = _item_units(db, r.order_item_id)
        units += qty

        product = db.get(EventMerchProduct, r.product_id) if r.product_id else None
        product_name = (
            product.name if product else (item.product_name if item else None)
        )
        sponsor_brand = product.sponsor_brand_name if product else None

        pkey = str(r.product_id or "unknown")
        pb = by_product.setdefault(
            pkey,
            {
                **_empty_money(),
                "product_id": r.product_id,
                "product_name": product_name,
                "is_sponsor_branded": bool(r.is_sponsor_branded),
                "sponsor_brand_name": sponsor_brand,
            },
        )
        _add_split(pb, r, qty)
        pb["is_sponsor_branded"] = pb["is_sponsor_branded"] or bool(r.is_sponsor_branded)
        if product_name:
            pb["product_name"] = product_name
        if sponsor_brand:
            pb["sponsor_brand_name"] = sponsor_brand

        ekey = str(r.event_id or "none")
        event = db.get(Event, r.event_id) if r.event_id else None
        eb = by_event.setdefault(
            ekey,
            {
                **_empty_money(),
                "event_id": r.event_id,
                "event_title": event.title if event else None,
            },
        )
        _add_split(eb, r, qty)

        variant_id = item.merch_variant_id if item else None
        vkey = str(variant_id or "unknown")
        vb = by_variant.setdefault(
            vkey,
            {
                **_empty_money(),
                "variant_id": variant_id,
                "variant_label": item.variant_label if item else None,
                "product_id": r.product_id,
                "product_name": product_name,
            },
        )
        _add_split(vb, r, qty)

        fkey = r.fulfillment_method or "unknown"
        fb = by_fulfillment.setdefault(
            fkey,
            {**_empty_money(), "fulfillment_method": r.fulfillment_method},
        )
        _add_split(fb, r, qty)

        if r.bundle_id:
            bundle_gross += r.gross_amount
            bundle = db.get(MerchBundle, r.bundle_id)
            bkey = str(r.bundle_id)
            bb = by_bundle.setdefault(
                bkey,
                {
                    **_empty_money(),
                    "bundle_id": r.bundle_id,
                    "bundle_name": bundle.name if bundle else None,
                },
            )
            _add_split(bb, r, qty)

        if r.is_sponsor_branded:
            sponsor_branded_gross += r.gross_amount
            sponsor_lines.append(
                {
                    "product_id": r.product_id,
                    "product_name": product_name,
                    "sponsor_brand_name": sponsor_brand,
                    "gross": _q(r.gross_amount),
                    "sponsor_amount": _q(r.sponsor_amount),
                    "host_amount": _q(r.host_amount),
                }
            )

    for r in reversed_rows:
        qty, _ = _item_units(db, r.order_item_id)
        refund_units += qty

    top_products = _top_sorted(by_product)
    # Preserve full by_product list for FE (quantized)
    by_product_list = _top_sorted(by_product, limit=10_000)

    return {
        "host_id": host_id,
        "event_id": event_id,
        "currency": "NGN",
        "total_gross": _q(gross),
        "total_merch_gmv": _q(gross),
        "host_amount": _q(host_amt),
        "net_revenue": _q(host_amt),
        "platform_amount": _q(platform),
        "sponsor_amount": _q(sponsor),
        "print_partner_amount": _q(print_partner),
        "units_sold": units,
        "line_count": len(active),
        "refunds": {
            "gross": _q(refunds_gross),
            "host_amount": _q(refunds_host),
            "units": refund_units,
            "line_count": len(reversed_rows),
        },
        "refunds_gross": _q(refunds_gross),
        "discount_impact": _discount_impact(db, active),
        "bundle_revenue": _q(bundle_gross),
        "sponsor_branded_revenue": _q(sponsor_branded_gross),
        "sponsor_branded_line_count": len(sponsor_lines),
        "payout_status": _payout_status(active),
        "top_products": top_products,
        "by_product": by_product_list,
        "by_event": _top_sorted(by_event, limit=10_000),
        "by_variant": _top_sorted(by_variant, limit=10_000),
        "by_fulfillment_method": _top_sorted(by_fulfillment, limit=10_000),
        "by_bundle": _top_sorted(by_bundle, limit=10_000),
        "sponsor_branded_lines": sponsor_lines,
        # Never include buyer email/phone/address/payment refs
    }


def admin_revenue_report(db: Session) -> dict:
    active = _load_splits(db, statuses=ACTIVE_STATUSES)
    reversed_rows = _load_splits(db, statuses=("reversed",))

    by_host: dict[str, dict] = {}
    by_product: dict[str, dict] = {}
    by_event: dict[str, dict] = {}
    units = 0
    refund_units = 0
    sponsor_rows = [r for r in active if r.is_sponsor_branded]

    for r in active:
        qty, item = _item_units(db, r.order_item_id)
        units += qty

        host = db.get(Host, r.host_id)
        hkey = str(r.host_id)
        hb = by_host.setdefault(
            hkey,
            {
                **_empty_money(),
                "host_id": r.host_id,
                "host_name": host.display_name if host else None,
            },
        )
        _add_split(hb, r, qty)

        product = db.get(EventMerchProduct, r.product_id) if r.product_id else None
        pkey = str(r.product_id or "unknown")
        pb = by_product.setdefault(
            pkey,
            {
                **_empty_money(),
                "product_id": r.product_id,
                "product_name": (
                    product.name if product else (item.product_name if item else None)
                ),
                "host_id": r.host_id,
                "is_sponsor_branded": bool(r.is_sponsor_branded),
            },
        )
        _add_split(pb, r, qty)

        event = db.get(Event, r.event_id) if r.event_id else None
        ekey = str(r.event_id or "none")
        eb = by_event.setdefault(
            ekey,
            {
                **_empty_money(),
                "event_id": r.event_id,
                "event_title": event.title if event else None,
                "host_id": r.host_id,
            },
        )
        _add_split(eb, r, qty)

    for r in reversed_rows:
        qty, _ = _item_units(db, r.order_item_id)
        refund_units += qty

    pending = [r for r in active if r.status == "payable"]
    pending_amount = sum((r.host_amount for r in pending), Decimal("0"))

    return {
        "currency": "NGN",
        "total_gross": _q(sum((r.gross_amount for r in active), Decimal("0"))),
        "platform_merch_gmv": _q(
            sum((r.gross_amount for r in active), Decimal("0"))
        ),
        "platform_amount": _q(
            sum((r.platform_amount for r in active), Decimal("0"))
        ),
        "platform_fees": _q(sum((r.platform_amount for r in active), Decimal("0"))),
        "host_amount": _q(sum((r.host_amount for r in active), Decimal("0"))),
        "host_revenue": _q(sum((r.host_amount for r in active), Decimal("0"))),
        "sponsor_amount": _q(sum((r.sponsor_amount for r in active), Decimal("0"))),
        "sponsor_split": _q(sum((r.sponsor_amount for r in active), Decimal("0"))),
        "print_partner_amount": _q(
            sum((r.print_partner_amount for r in active), Decimal("0"))
        ),
        "print_partner_split": _q(
            sum((r.print_partner_amount for r in active), Decimal("0"))
        ),
        "units_sold": units,
        "line_count": len(active),
        "refunds": {
            "gross": _q(sum((r.gross_amount for r in reversed_rows), Decimal("0"))),
            "host_amount": _q(
                sum((r.host_amount for r in reversed_rows), Decimal("0"))
            ),
            "platform_amount": _q(
                sum((r.platform_amount for r in reversed_rows), Decimal("0"))
            ),
            "units": refund_units,
            "line_count": len(reversed_rows),
        },
        "refunds_gross": _q(
            sum((r.gross_amount for r in reversed_rows), Decimal("0"))
        ),
        "discount_impact": _discount_impact(db, active),
        "sponsor_branded_line_count": len(sponsor_rows),
        "sponsor_branded_gross": _q(
            sum((r.gross_amount for r in sponsor_rows), Decimal("0"))
        ),
        "pending_payouts": {
            "amount": _q(pending_amount),
            "line_count": len(pending),
        },
        "payout_status": _payout_status(active),
        "top_hosts": _top_sorted(by_host),
        "top_products": _top_sorted(by_product),
        "top_events": _top_sorted(by_event),
        # Never include buyer email/phone/address/payment refs
    }


_CSV_HEADERS = [
    "created_at",
    "event_id",
    "product_id",
    "gross",
    "host_amount",
    "platform_amount",
    "sponsor_amount",
    "print_partner_amount",
    "fulfillment_method",
    "status",
    "bundle_id",
    "is_sponsor_branded",
    "currency",
]

_ADMIN_CSV_HEADERS = ["host_id", *_CSV_HEADERS]

# Explicit denylist — export must never emit these column names
_PII_COLUMNS = frozenset(
    {
        "email",
        "buyer_email",
        "phone",
        "phone_number",
        "recipient_name",
        "buyer_name",
        "full_name",
        "address",
        "line1",
        "line2",
        "shipping_address",
        "payment_reference",
        "authorization_code",
        "card_last4",
    }
)


def _assert_no_pii_headers(headers: list[str]) -> None:
    lowered = {h.lower() for h in headers}
    overlap = lowered & _PII_COLUMNS
    if overlap:
        raise ValueError(f"CSV export must not include PII columns: {sorted(overlap)}")


def export_host_revenue_csv(db: Session, *, host_id: uuid.UUID) -> str:
    """Line-level host export — IDs and amounts only; no buyer/payment PII."""
    _assert_no_pii_headers(_CSV_HEADERS)
    rows = _load_splits(db, host_id=host_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_HEADERS)
    for r in rows:
        writer.writerow(
            [
                r.created_at.isoformat() if r.created_at else "",
                str(r.event_id or ""),
                str(r.product_id or ""),
                str(r.gross_amount),
                str(r.host_amount),
                str(r.platform_amount),
                str(r.sponsor_amount),
                str(r.print_partner_amount),
                r.fulfillment_method or "",
                r.status,
                str(r.bundle_id or ""),
                "1" if r.is_sponsor_branded else "0",
                r.currency or "NGN",
            ]
        )
    return buf.getvalue()


def export_admin_revenue_csv(db: Session) -> str:
    """Platform export — host/event/product IDs and amounts; no buyer/payment PII."""
    _assert_no_pii_headers(_ADMIN_CSV_HEADERS)
    rows = _load_splits(db)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_ADMIN_CSV_HEADERS)
    for r in rows:
        writer.writerow(
            [
                str(r.host_id),
                r.created_at.isoformat() if r.created_at else "",
                str(r.event_id or ""),
                str(r.product_id or ""),
                str(r.gross_amount),
                str(r.host_amount),
                str(r.platform_amount),
                str(r.sponsor_amount),
                str(r.print_partner_amount),
                r.fulfillment_method or "",
                r.status,
                str(r.bundle_id or ""),
                "1" if r.is_sponsor_branded else "0",
                r.currency or "NGN",
            ]
        )
    return buf.getvalue()
