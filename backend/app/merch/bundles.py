"""Ticket + merch bundles — expand into order_items on create_order."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import TicketType
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchBundle
from app.merch.service import available_variant_stock, effective_variant_price

BUNDLE_STATUSES = frozenset({"draft", "active", "paused", "archived"})


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (base or "bundle")[:160]


def _validate_status(status: str) -> str:
    value = (status or "").strip().lower()
    if value not in BUNDLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Bundle status must be draft, active, paused, or archived",
        )
    return value


def _validate_merch_rules(
    db: Session, *, event_id: uuid.UUID, merch_variant_rules: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not merch_variant_rules:
        raise HTTPException(status_code=400, detail="Bundle requires merch components")
    normalized: list[dict[str, Any]] = []
    for rule in merch_variant_rules:
        vid = rule.get("variant_id")
        if not vid:
            raise HTTPException(status_code=400, detail="Each rule needs variant_id")
        qty = int(rule.get("quantity") or 1)
        if qty < 1:
            raise HTTPException(status_code=400, detail="Bundle merch quantity must be ≥ 1")
        variant = db.get(EventMerchVariant, uuid.UUID(str(vid)))
        if variant is None or variant.archived_at is not None:
            raise HTTPException(status_code=400, detail="Unknown merch variant in bundle")
        product = db.get(EventMerchProduct, variant.product_id)
        if product is None or product.event_id != event_id:
            raise HTTPException(
                status_code=400, detail="Bundle merch must belong to the same event"
            )
        if product.archived_at is not None:
            raise HTTPException(status_code=400, detail="Bundle merch product is archived")
        normalized.append(
            {
                "product_id": str(product.id),
                "variant_id": str(variant.id),
                "quantity": qty,
            }
        )
    return normalized


def serialize_bundle(db: Session, row: MerchBundle) -> dict:
    component_sum = Decimal("0")
    rules_out: list[dict[str, Any]] = []
    tt = db.get(TicketType, row.ticket_type_id)
    if tt is not None:
        component_sum += Decimal(tt.price)
    for rule in row.merch_variant_rules or []:
        vid = rule.get("variant_id")
        qty = int(rule.get("quantity") or 1)
        variant = db.get(EventMerchVariant, uuid.UUID(str(vid))) if vid else None
        product = (
            db.get(EventMerchProduct, variant.product_id) if variant else None
        )
        unit = (
            effective_variant_price(product, variant)
            if product and variant
            else Decimal("0")
        )
        component_sum += unit * qty
        rules_out.append(
            {
                "product_id": str(product.id) if product else rule.get("product_id"),
                "variant_id": str(variant.id) if variant else vid,
                "quantity": qty,
                "product_name": product.name if product else None,
                "variant_label": variant.label if variant else None,
                "unit_price": unit,
                "is_vault_exclusive": bool(
                    product.is_vault_exclusive or product.requires_vault_access
                )
                if product
                else False,
                "requires_vault_access": bool(
                    getattr(product, "requires_vault_access", False)
                    or getattr(product, "is_vault_exclusive", False)
                )
                if product
                else False,
            }
        )
    savings = max(Decimal("0"), component_sum - Decimal(row.bundle_price))
    available = None
    if row.inventory_limit is not None:
        available = max(
            0,
            int(row.inventory_limit)
            - int(row.quantity_reserved or 0)
            - int(row.quantity_sold or 0),
        )
    return {
        "id": row.id,
        "host_id": row.host_id,
        "event_id": row.event_id,
        "name": row.name,
        "slug": row.slug,
        "description": row.description,
        "status": row.status,
        "bundle_price": row.bundle_price,
        "currency": row.currency,
        "ticket_type_id": row.ticket_type_id,
        "ticket_type_name": tt.name if tt else None,
        "ticket_type_price": Decimal(tt.price) if tt else None,
        "merch_variant_rules": rules_out,
        "component_list_total": component_sum,
        "savings": savings,
        "inventory_limit": row.inventory_limit,
        "available_packs": available,
        "max_per_buyer": row.max_per_buyer,
        "sales_start_at": row.sales_start_at,
        "sales_end_at": row.sales_end_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def create_bundle(
    db: Session,
    *,
    host_id: uuid.UUID,
    event_id: uuid.UUID,
    name: str,
    ticket_type_id: uuid.UUID,
    merch_variant_rules: list[dict[str, Any]],
    bundle_price: Decimal,
    description: str | None = None,
    currency: str = "NGN",
    inventory_limit: int | None = None,
    max_per_buyer: int | None = None,
    sales_start_at: datetime | None = None,
    sales_end_at: datetime | None = None,
    status: str = "draft",
) -> MerchBundle:
    tt = db.get(TicketType, ticket_type_id)
    if tt is None or tt.event_id != event_id:
        raise HTTPException(status_code=400, detail="Invalid ticket type for bundle")
    if Decimal(bundle_price) < 0:
        raise HTTPException(status_code=400, detail="Bundle price must be ≥ 0")
    if inventory_limit is not None and inventory_limit < 1:
        raise HTTPException(status_code=400, detail="inventory_limit must be ≥ 1")
    if max_per_buyer is not None and max_per_buyer < 1:
        raise HTTPException(status_code=400, detail="max_per_buyer must be ≥ 1")
    if (
        sales_start_at is not None
        and sales_end_at is not None
        and sales_end_at <= sales_start_at
    ):
        raise HTTPException(
            status_code=400, detail="sales_end_at must be after sales_start_at"
        )
    rules = _validate_merch_rules(
        db, event_id=event_id, merch_variant_rules=merch_variant_rules
    )
    status_value = _validate_status(status)
    slug = _slugify(name)
    base = slug
    n = 1
    while db.scalar(
        select(MerchBundle.id).where(
            MerchBundle.event_id == event_id, MerchBundle.slug == slug
        )
    ):
        n += 1
        slug = f"{base}-{n}"
    now = datetime.now(UTC)
    row = MerchBundle(
        host_id=host_id,
        event_id=event_id,
        name=name.strip()[:160],
        slug=slug,
        description=description,
        status=status_value,
        bundle_price=Decimal(bundle_price),
        currency=(currency or "NGN").upper()[:8],
        ticket_type_id=ticket_type_id,
        merch_variant_rules=rules,
        inventory_limit=inventory_limit,
        max_per_buyer=max_per_buyer,
        sales_start_at=sales_start_at,
        sales_end_at=sales_end_at,
        archived_at=now if status_value == "archived" else None,
    )
    db.add(row)
    db.flush()
    return row


def get_event_bundle(
    db: Session, *, event_id: uuid.UUID, bundle_id: uuid.UUID
) -> MerchBundle:
    row = db.scalar(
        select(MerchBundle).where(
            MerchBundle.id == bundle_id,
            MerchBundle.event_id == event_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return row


def update_bundle(
    db: Session,
    *,
    bundle: MerchBundle,
    data: dict[str, Any],
) -> MerchBundle:
    if "name" in data and data["name"] is not None:
        bundle.name = str(data["name"]).strip()[:160]
    if "description" in data:
        bundle.description = data["description"]
    if "bundle_price" in data and data["bundle_price"] is not None:
        price = Decimal(data["bundle_price"])
        if price < 0:
            raise HTTPException(status_code=400, detail="Bundle price must be ≥ 0")
        bundle.bundle_price = price
    if "currency" in data and data["currency"] is not None:
        bundle.currency = str(data["currency"]).upper()[:8]
    if "ticket_type_id" in data and data["ticket_type_id"] is not None:
        tt = db.get(TicketType, data["ticket_type_id"])
        if tt is None or tt.event_id != bundle.event_id:
            raise HTTPException(status_code=400, detail="Invalid ticket type for bundle")
        bundle.ticket_type_id = tt.id
    if "merch_variant_rules" in data and data["merch_variant_rules"] is not None:
        bundle.merch_variant_rules = _validate_merch_rules(
            db,
            event_id=bundle.event_id,
            merch_variant_rules=data["merch_variant_rules"],
        )
    if "inventory_limit" in data:
        limit = data["inventory_limit"]
        if limit is not None and int(limit) < 1:
            raise HTTPException(status_code=400, detail="inventory_limit must be ≥ 1")
        bundle.inventory_limit = limit
    if "max_per_buyer" in data:
        max_buyer = data["max_per_buyer"]
        if max_buyer is not None and int(max_buyer) < 1:
            raise HTTPException(status_code=400, detail="max_per_buyer must be ≥ 1")
        bundle.max_per_buyer = max_buyer
    if "sales_start_at" in data:
        bundle.sales_start_at = data["sales_start_at"]
    if "sales_end_at" in data:
        bundle.sales_end_at = data["sales_end_at"]
    if (
        bundle.sales_start_at is not None
        and bundle.sales_end_at is not None
        and bundle.sales_end_at <= bundle.sales_start_at
    ):
        raise HTTPException(
            status_code=400, detail="sales_end_at must be after sales_start_at"
        )
    if "status" in data and data["status"] is not None:
        status_value = _validate_status(str(data["status"]))
        bundle.status = status_value
        if status_value == "archived":
            bundle.archived_at = bundle.archived_at or datetime.now(UTC)
        elif bundle.archived_at is not None and status_value != "archived":
            bundle.archived_at = None
    db.flush()
    return bundle


def archive_bundle(db: Session, *, bundle: MerchBundle) -> MerchBundle:
    bundle.status = "archived"
    bundle.archived_at = datetime.now(UTC)
    db.flush()
    return bundle


def buyer_prior_bundle_quantity(
    db: Session,
    *,
    buyer_user_id: uuid.UUID,
    bundle_id: uuid.UUID,
) -> int:
    """Packs held/purchased by buyer (pending + paid) for max_per_buyer."""
    from app.payments.models import Order, OrderItem

    # Ticket lines carry pack quantity for expanded bundles.
    total = db.scalar(
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.buyer_user_id == buyer_user_id,
            Order.status.in_(("pending", "paid")),
            OrderItem.bundle_id == bundle_id,
            OrderItem.ticket_type_id.is_not(None),
        )
    )
    return int(total or 0)


def list_event_bundles(
    db: Session, *, event_id: uuid.UUID, public_only: bool = False
) -> list[dict]:
    stmt = select(MerchBundle).where(
        MerchBundle.event_id == event_id,
        MerchBundle.archived_at.is_(None),
    )
    if public_only:
        stmt = stmt.where(MerchBundle.status == "active")
    rows = list(db.scalars(stmt.order_by(MerchBundle.created_at.desc())))
    now = datetime.now(UTC)
    out = []
    for row in rows:
        if public_only:
            start = _as_utc(row.sales_start_at)
            end = _as_utc(row.sales_end_at)
            if start and now < start:
                continue
            if end and now > end:
                continue
        out.append(serialize_bundle(db, row))
    return out


def load_active_bundle(
    db: Session, *, event_id: uuid.UUID, bundle_id: uuid.UUID, for_update: bool = False
) -> MerchBundle:
    stmt = select(MerchBundle).where(
        MerchBundle.id == bundle_id,
        MerchBundle.event_id == event_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    row = db.scalar(stmt)
    if row is None or row.status != "active" or row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Bundle is not available")
    now = datetime.now(UTC)
    start = _as_utc(row.sales_start_at)
    end = _as_utc(row.sales_end_at)
    if start and now < start:
        raise HTTPException(status_code=400, detail="Bundle sales have not started")
    if end and now > end:
        raise HTTPException(status_code=400, detail="Bundle sales have ended")
    return row


def reserve_bundle_pack(bundle: MerchBundle, quantity: int) -> None:
    if bundle.inventory_limit is not None:
        available = (
            int(bundle.inventory_limit)
            - int(bundle.quantity_reserved or 0)
            - int(bundle.quantity_sold or 0)
        )
        if available < quantity:
            raise HTTPException(status_code=409, detail="Not enough bundle packs available")
    bundle.quantity_reserved = int(bundle.quantity_reserved or 0) + quantity


def commit_bundle_sale(bundle: MerchBundle, quantity: int) -> None:
    reserved = int(bundle.quantity_reserved or 0)
    take = min(reserved, quantity)
    bundle.quantity_reserved = reserved - take
    bundle.quantity_sold = int(bundle.quantity_sold or 0) + quantity


def release_bundle_reservation(bundle: MerchBundle, quantity: int) -> None:
    bundle.quantity_reserved = max(0, int(bundle.quantity_reserved or 0) - quantity)


def expand_bundle_allocation(
    db: Session, *, bundle: MerchBundle, quantity: int
) -> tuple[
    list[tuple[TicketType, int, Decimal]],
    list[tuple[EventMerchProduct, EventMerchVariant, int, Decimal]],
    Decimal,
]:
    """Allocate bundle_price across ticket + merch lines proportionally.

    Returns ticket lines, merch lines (unit prices already allocated), pack total.
    Never oversells ticket or merch component inventory.
    """
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Bundle quantity must be ≥ 1")

    tt = db.scalar(
        select(TicketType)
        .where(TicketType.id == bundle.ticket_type_id)
        .with_for_update()
    )
    if tt is None:
        raise HTTPException(status_code=400, detail="Bundle ticket type missing")
    if tt.status != "active" or tt.visibility == "hidden":
        raise HTTPException(
            status_code=400, detail=f"Ticket type {tt.name} is unavailable"
        )
    ticket_available = max(
        0, int(tt.quantity) - int(tt.quantity_sold or 0) - int(tt.quantity_reserved or 0)
    )
    if ticket_available < quantity:
        raise HTTPException(
            status_code=409,
            detail=f"Not enough tickets available for {tt.name}",
        )

    components: list[tuple[str, Decimal, Any]] = []
    ticket_list = Decimal(tt.price) * quantity
    components.append(("ticket", ticket_list, tt))

    merch_resolved: list[tuple[EventMerchProduct, EventMerchVariant, int]] = []
    for rule in bundle.merch_variant_rules or []:
        vid = uuid.UUID(str(rule["variant_id"]))
        qty = int(rule.get("quantity") or 1) * quantity
        variant = db.scalar(
            select(EventMerchVariant)
            .where(EventMerchVariant.id == vid)
            .with_for_update()
        )
        if variant is None or variant.archived_at is not None:
            raise HTTPException(status_code=400, detail="Bundle merch variant missing")
        product = db.get(EventMerchProduct, variant.product_id)
        if product is None or product.archived_at is not None:
            raise HTTPException(status_code=400, detail="Bundle merch product missing")
        if available_variant_stock(variant) < qty:
            raise HTTPException(
                status_code=409,
                detail=f"Not enough stock for {product.name} ({variant.label})",
            )
        list_total = effective_variant_price(product, variant) * qty
        components.append(("merch", list_total, (product, variant, qty)))
        merch_resolved.append((product, variant, qty))

    list_sum = sum((c[1] for c in components), Decimal("0"))
    pack_total = Decimal(bundle.bundle_price) * quantity
    if list_sum <= 0:
        raise HTTPException(status_code=400, detail="Invalid bundle pricing")

    # Proportional allocation; remainder on ticket line.
    allocated: dict[str, Decimal] = {}
    running = Decimal("0")
    for i, (kind, list_amt, _) in enumerate(components):
        if i == 0:
            continue
        share = (list_amt / list_sum * pack_total).quantize(Decimal("0.01"))
        allocated[f"{kind}-{i}"] = share
        running += share
    allocated["ticket-0"] = pack_total - running

    ticket_line_total = allocated["ticket-0"]
    ticket_unit = (ticket_line_total / quantity).quantize(Decimal("0.01"))
    ticket_lines = [(tt, quantity, ticket_unit)]

    merch_lines: list[tuple[EventMerchProduct, EventMerchVariant, int, Decimal]] = []
    idx = 1
    for product, variant, qty in merch_resolved:
        line_total = allocated[f"merch-{idx}"]
        unit = (line_total / qty).quantize(Decimal("0.01")) if qty else Decimal("0")
        merch_lines.append((product, variant, qty, unit))
        idx += 1

    return ticket_lines, merch_lines, pack_total
