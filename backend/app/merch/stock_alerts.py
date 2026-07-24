"""Persisted stock alerts — richer than one-shot low_stock notify."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.merch.constants import DEFAULT_LOW_STOCK_THRESHOLD
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchStockAlert
from app.merch.service import available_variant_stock

PRE_EVENT_RISK_HOURS = 72
HIGH_RESERVE_RATIO = 0.7


def _threshold(product: EventMerchProduct, variant: EventMerchVariant) -> int:
    if variant.low_stock_threshold is not None:
        return int(variant.low_stock_threshold)
    return int(product.low_stock_threshold or DEFAULT_LOW_STOCK_THRESHOLD)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _event_starts_soon(db: Session, product: EventMerchProduct) -> bool:
    if product.event_id is None:
        return False
    event = db.get(Event, product.event_id)
    if event is None or event.start_datetime is None:
        return False
    start = _aware(event.start_datetime)
    now = datetime.now(UTC)
    if start <= now:
        return False
    return (start - now) <= timedelta(hours=PRE_EVENT_RISK_HOURS)


def _open_alert(
    db: Session,
    *,
    host_id: uuid.UUID,
    product_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    alert_type: str,
) -> MerchStockAlert | None:
    return db.scalar(
        select(MerchStockAlert).where(
            MerchStockAlert.host_id == host_id,
            MerchStockAlert.product_id == product_id,
            MerchStockAlert.variant_id == variant_id,
            MerchStockAlert.alert_type == alert_type,
            MerchStockAlert.status == "open",
        )
    )


def evaluate_variant_stock_alerts(
    db: Session,
    *,
    product: EventMerchProduct,
    variant: EventMerchVariant,
    previous_available: int | None = None,
) -> list[MerchStockAlert]:
    """Idempotent: open/resolve alerts after inventory changes. No PII."""
    available = available_variant_stock(variant)
    threshold = _threshold(product, variant)
    created: list[MerchStockAlert] = []
    now = datetime.now(UTC)

    def open_alert(alert_type: str) -> None:
        existing = _open_alert(
            db,
            host_id=product.host_id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type=alert_type,
        )
        if existing:
            existing.available_snapshot = available
            existing.threshold = threshold
            return
        row = MerchStockAlert(
            host_id=product.host_id,
            event_id=product.event_id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type=alert_type,
            threshold=threshold,
            available_snapshot=available,
            status="open",
            triggered_at=now,
        )
        db.add(row)
        created.append(row)

    def resolve_type(alert_type: str) -> None:
        existing = _open_alert(
            db,
            host_id=product.host_id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type=alert_type,
        )
        if existing:
            existing.status = "resolved"
            existing.resolved_at = now

    if available <= 0:
        open_alert("sold_out")
        resolve_type("low_stock")
        resolve_type("restocked")
        resolve_type("pre_event_risk")
    elif available <= threshold:
        open_alert("low_stock")
        resolve_type("sold_out")
        resolve_type("restocked")
        if _event_starts_soon(db, product):
            open_alert("pre_event_risk")
        else:
            resolve_type("pre_event_risk")
    else:
        resolve_type("low_stock")
        resolve_type("sold_out")
        resolve_type("pre_event_risk")
        if previous_available is not None and previous_available <= threshold:
            open_alert("restocked")
        else:
            resolve_type("restocked")

    reserved = int(variant.reserved_quantity or 0)
    inventory = int(variant.inventory_count or 0)
    if inventory > 0 and reserved / inventory >= HIGH_RESERVE_RATIO:
        open_alert("high_reserve")
    else:
        resolve_type("high_reserve")

    db.flush()

    if created:
        from app.merch.notifications import notify_host_stock_alerts

        notify_host_stock_alerts(db, product=product, variant=variant, alerts=created)

    return created


def list_host_alerts(
    db: Session,
    *,
    host_id: uuid.UUID,
    status_filter: str | None = "open",
    alert_type: str | None = None,
) -> list[dict]:
    stmt = select(MerchStockAlert).where(MerchStockAlert.host_id == host_id)
    if status_filter:
        stmt = stmt.where(MerchStockAlert.status == status_filter)
    if alert_type:
        stmt = stmt.where(MerchStockAlert.alert_type == alert_type)
    rows = list(db.scalars(stmt.order_by(MerchStockAlert.triggered_at.desc())))
    out = []
    for r in rows:
        product = db.get(EventMerchProduct, r.product_id)
        variant = db.get(EventMerchVariant, r.variant_id) if r.variant_id else None
        current = available_variant_stock(variant) if variant is not None else None
        out.append(
            {
                "id": r.id,
                "host_id": r.host_id,
                "event_id": r.event_id,
                "product_id": r.product_id,
                "variant_id": r.variant_id,
                "alert_type": r.alert_type,
                "threshold": r.threshold,
                "available_snapshot": r.available_snapshot,
                "current_available": current,
                "status": r.status,
                "triggered_at": r.triggered_at,
                "resolved_at": r.resolved_at,
                "product_name": product.name if product else None,
                "variant_label": variant.label if variant else None,
            }
        )
    return out


def resolve_alert(
    db: Session, *, host_id: uuid.UUID, alert_id: uuid.UUID
) -> dict:
    row = db.get(MerchStockAlert, alert_id)
    if row is None or row.host_id != host_id:
        raise HTTPException(status_code=404, detail="Stock alert not found")
    row.status = "resolved"
    row.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "status": row.status,
        "resolved_at": row.resolved_at,
        "alert_type": row.alert_type,
    }
