"""Reusable host size charts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.merch.models import MerchSizeChart


def serialize_chart(row: MerchSizeChart) -> dict:
    return {
        "id": row.id,
        "host_id": row.host_id,
        "name": row.name,
        "product_type": row.product_type,
        "units": row.units,
        "chart_json": row.chart_json,
        "fit_notes": row.fit_notes,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "archived_at": row.archived_at,
    }


def list_charts(db: Session, *, host_id: uuid.UUID) -> list[dict]:
    rows = list(
        db.scalars(
            select(MerchSizeChart).where(
                MerchSizeChart.host_id == host_id,
                MerchSizeChart.archived_at.is_(None),
            ).order_by(MerchSizeChart.name.asc())
        )
    )
    return [serialize_chart(r) for r in rows]


def create_chart(
    db: Session,
    *,
    host_id: uuid.UUID,
    name: str,
    chart_json: dict[str, Any] | list[Any],
    product_type: str | None = None,
    units: str = "cm",
    fit_notes: str | None = None,
) -> MerchSizeChart:
    if units not in {"cm", "inches"}:
        raise HTTPException(status_code=400, detail="units must be cm or inches")
    row = MerchSizeChart(
        host_id=host_id,
        name=name.strip()[:120],
        product_type=product_type,
        units=units,
        chart_json=chart_json or {},
        fit_notes=fit_notes,
        status="active",
    )
    db.add(row)
    db.flush()
    return row


def require_host_chart(
    db: Session, *, host_id: uuid.UUID, chart_id: uuid.UUID
) -> MerchSizeChart:
    row = db.get(MerchSizeChart, chart_id)
    if (
        row is None
        or row.host_id != host_id
        or row.archived_at is not None
        or row.status == "archived"
    ):
        raise HTTPException(status_code=400, detail="Invalid size chart")
    return row


def update_chart(
    db: Session,
    *,
    host_id: uuid.UUID,
    chart_id: uuid.UUID,
    **fields: Any,
) -> MerchSizeChart:
    row = db.get(MerchSizeChart, chart_id)
    if row is None or row.host_id != host_id or row.archived_at is not None:
        raise HTTPException(status_code=404, detail="Size chart not found")
    if "name" in fields and fields["name"] is not None:
        row.name = str(fields["name"]).strip()[:120]
    if "product_type" in fields:
        row.product_type = fields["product_type"]
    if "units" in fields and fields["units"] is not None:
        if fields["units"] not in {"cm", "inches"}:
            raise HTTPException(status_code=400, detail="units must be cm or inches")
        row.units = fields["units"]
    if "chart_json" in fields and fields["chart_json"] is not None:
        row.chart_json = fields["chart_json"]
    if "fit_notes" in fields:
        notes = fields["fit_notes"]
        row.fit_notes = (str(notes).strip() or None) if notes is not None else None
    if "status" in fields and fields["status"] is not None:
        status = str(fields["status"]).strip().lower()
        if status not in {"active", "inactive"}:
            raise HTTPException(status_code=400, detail="status must be active or inactive")
        row.status = status
    db.flush()
    return row


def archive_chart(db: Session, *, host_id: uuid.UUID, chart_id: uuid.UUID) -> MerchSizeChart:
    row = db.get(MerchSizeChart, chart_id)
    if row is None or row.host_id != host_id:
        raise HTTPException(status_code=404, detail="Size chart not found")
    row.status = "archived"
    row.archived_at = datetime.now(UTC)
    db.flush()
    return row


def get_public_chart(db: Session, chart_id: uuid.UUID | None) -> dict | None:
    if chart_id is None:
        return None
    row = db.get(MerchSizeChart, chart_id)
    if row is None or row.status != "active" or row.archived_at is not None:
        return None
    return serialize_chart(row)
