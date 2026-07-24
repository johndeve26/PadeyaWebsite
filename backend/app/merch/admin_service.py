"""Admin oversight for event merch (moderation, reports, fulfillment issues)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host
from app.merch.constants import (
    MODERATION_STATUSES,
    OPEN_REPORT_STATUSES,
    REPORT_STATUSES,
    UNSAFE_EVENT_STATUSES,
    UNSAFE_HOST_STATUSES,
)
from app.merch.models import EventMerchProduct, MerchFulfillment, MerchProductReport
from app.merch.service import serialize_product
from app.payments.models import Order
from app.users.models import User

MODERATION_ACTIONS = frozenset(
    {"flag", "clear", "hide", "remove", "archive", "restore"}
)
MODERATION_ACTIONS_REQUIRE_NOTE = frozenset(
    {"hide", "remove", "archive", "restore"}
)
ISSUE_FULFILLMENT_STATUSES = frozenset({"awaiting_pickup", "collect_at_stand", "cancelled"})


def _require_admin_view(user: User) -> None:
    from app.users.service import user_has_permission

    if not (
        user_has_permission(user, "merch.view_admin")
        or user_has_permission(user, "merch.moderate")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")


def _require_admin_moderate(user: User) -> None:
    from app.users.service import user_has_permission

    if not (
        user_has_permission(user, "merch.moderate")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")


def serialize_admin_product(
    db: Session,
    product: EventMerchProduct,
    *,
    open_report_count: int | None = None,
    report_count: int | None = None,
) -> dict:
    event = db.get(Event, product.event_id)
    host = db.get(Host, product.host_id)
    base = serialize_product(
        product, event_title=event.title if event else None
    )
    if open_report_count is None:
        open_report_count = db.scalar(
            select(func.count())
            .select_from(MerchProductReport)
            .where(
                MerchProductReport.product_id == product.id,
                MerchProductReport.status.in_(tuple(OPEN_REPORT_STATUSES)),
            )
        ) or 0
    if report_count is None:
        report_count = db.scalar(
            select(func.count())
            .select_from(MerchProductReport)
            .where(MerchProductReport.product_id == product.id)
        ) or 0
    return {
        **base,
        "host_name": host.display_name if host else None,
        "host_status": host.status if host else None,
        "event_status": event.status if event else None,
        "open_report_count": int(open_report_count),
        "report_count": int(report_count),
    }


def get_admin_product(db: Session, *, user: User, product_id: uuid.UUID) -> dict:
    _require_admin_view(user)
    product = db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product_id)
        .options(selectinload(EventMerchProduct.variants))
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Merch product not found")
    return serialize_admin_product(db, product)


def list_admin_products(
    db: Session,
    *,
    user: User,
    moderation_status: str | None = None,
    status: str | None = None,
    event_id: uuid.UUID | None = None,
    host_id: uuid.UUID | None = None,
    q: str | None = None,
    is_sponsor_branded: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    _require_admin_view(user)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    stmt = (
        select(EventMerchProduct)
        .options(selectinload(EventMerchProduct.variants))
        .order_by(EventMerchProduct.updated_at.desc())
    )
    if moderation_status:
        if moderation_status not in MODERATION_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid moderation_status")
        stmt = stmt.where(EventMerchProduct.moderation_status == moderation_status)
    if status:
        stmt = stmt.where(EventMerchProduct.status == status)
    if event_id:
        stmt = stmt.where(EventMerchProduct.event_id == event_id)
    if host_id:
        stmt = stmt.where(EventMerchProduct.host_id == host_id)
    if is_sponsor_branded is not None:
        stmt = stmt.where(EventMerchProduct.is_sponsor_branded.is_(is_sponsor_branded))
    if q:
        from sqlalchemy import or_

        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(EventMerchProduct.name).like(needle),
                func.lower(
                    func.coalesce(EventMerchProduct.sponsor_brand_name, "")
                ).like(needle),
            )
        )

    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    if not rows:
        return []

    product_ids = [r.id for r in rows]
    open_counts = dict(
        db.execute(
            select(MerchProductReport.product_id, func.count())
            .where(
                MerchProductReport.product_id.in_(product_ids),
                MerchProductReport.status.in_(tuple(OPEN_REPORT_STATUSES)),
            )
            .group_by(MerchProductReport.product_id)
        ).all()
    )
    total_counts = dict(
        db.execute(
            select(MerchProductReport.product_id, func.count())
            .where(MerchProductReport.product_id.in_(product_ids))
            .group_by(MerchProductReport.product_id)
        ).all()
    )
    return [
        serialize_admin_product(
            db,
            p,
            open_report_count=int(open_counts.get(p.id, 0)),
            report_count=int(total_counts.get(p.id, 0)),
        )
        for p in rows
    ]


def moderate_product(
    db: Session,
    *,
    user: User,
    product_id: uuid.UUID,
    action: str,
    note: str | None,
) -> dict:
    _require_admin_moderate(user)
    if action not in MODERATION_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid action — use flag, clear, hide, remove, archive, restore",
        )
    requested_action = action
    # Archive is the admin soft-EOL path (same end state as remove).
    effective = "remove" if action == "archive" else action
    note_clean = (note or "").strip() or None
    if effective in MODERATION_ACTIONS_REQUIRE_NOTE and not note_clean:
        raise HTTPException(
            status_code=400,
            detail="Moderation reason is required for this action",
        )

    product = db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product_id)
        .options(selectinload(EventMerchProduct.variants))
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Merch product not found")

    now = datetime.now(UTC)
    product.moderated_by_user_id = user.id
    product.moderated_at = now
    product.moderation_note = note_clean

    if effective == "flag":
        product.moderation_status = "flagged"
    elif effective == "clear":
        product.moderation_status = "clear"
    elif effective == "hide":
        product.moderation_status = "hidden"
        if product.status == "active":
            product.status = "paused"
        from app.analytics.trusted import emit_admin_merch_hidden

        emit_admin_merch_hidden(
            db,
            event_id=product.event_id,
            host_id=product.host_id,
            actor_user_id=user.id,
            merch_product_id=product.id,
        )
    elif effective == "remove":
        product.moderation_status = "removed"
        product.status = "archived"
        if product.archived_at is None:
            product.archived_at = now
    elif effective == "restore":
        product.moderation_status = "clear"
        if product.status == "archived" and product.archived_at is not None:
            # Restore to paused so host must re-activate intentionally
            product.status = "paused"
            product.archived_at = None
        elif product.status == "paused":
            pass

    write_audit_log(
        db,
        action=f"merch.moderate.{requested_action}",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details={
            "note": note_clean,
            "status": product.status,
            "moderation_status": product.moderation_status,
            "event_id": str(product.event_id),
            "host_id": str(product.host_id),
        },
    )
    db.commit()
    product = db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product_id)
        .options(selectinload(EventMerchProduct.variants))
    )
    assert product is not None
    return serialize_admin_product(db, product)


def deactivate_unsafe_product(
    db: Session,
    *,
    user: User,
    product_id: uuid.UUID,
    note: str | None = None,
) -> dict:
    """Pause + hide merch when host/event is in an unsafe lifecycle state."""
    _require_admin_moderate(user)
    product = db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product_id)
        .options(selectinload(EventMerchProduct.variants))
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Merch product not found")

    event = db.get(Event, product.event_id)
    host = db.get(Host, product.host_id)
    host_status = host.status if host else None
    event_status = event.status if event else None
    unsafe = (host_status in UNSAFE_HOST_STATUSES) or (
        event_status in UNSAFE_EVENT_STATUSES
    )
    if not unsafe:
        raise HTTPException(
            status_code=400,
            detail=(
                "Host/event is not suspended or cancelled. "
                "Use moderate hide/remove for policy violations instead."
            ),
        )

    now = datetime.now(UTC)
    note_clean = (note or "").strip() or (
        f"Deactivated: host={host_status}, event={event_status}"
    )
    product.moderation_status = "hidden"
    product.moderation_note = note_clean
    product.moderated_at = now
    product.moderated_by_user_id = user.id
    if product.status not in {"archived"}:
        product.status = "paused"

    write_audit_log(
        db,
        action="merch.moderate.deactivate_unsafe",
        actor_user_id=user.id,
        resource_type="event_merch_product",
        resource_id=str(product.id),
        details={
            "note": note_clean,
            "host_status": host_status,
            "event_status": event_status,
            "status": product.status,
            "moderation_status": product.moderation_status,
        },
    )
    db.commit()
    product = db.scalar(
        select(EventMerchProduct)
        .where(EventMerchProduct.id == product_id)
        .options(selectinload(EventMerchProduct.variants))
    )
    assert product is not None
    return serialize_admin_product(db, product)


def serialize_admin_fulfillment(db: Session, row: MerchFulfillment) -> dict:
    """Ops view — no payment amounts, gateway refs, or payment IDs."""
    event = db.get(Event, row.event_id)
    host = db.get(Host, row.host_id)
    order = db.get(Order, row.order_id)
    is_issue = row.status in ISSUE_FULFILLMENT_STATUSES

    return {
        "id": row.id,
        "order_id": row.order_id,
        "order_reference": order.reference if order else None,
        "order_status": order.status if order else None,
        "event_id": row.event_id,
        "event_title": event.title if event else None,
        "event_status": event.status if event else None,
        "host_id": row.host_id,
        "host_name": host.display_name if host else None,
        "host_status": host.status if host else None,
        "buyer_name": order.buyer_name if order else None,
        "product_name": row.product_name_snapshot,
        "variant_label": row.variant_label_snapshot,
        "quantity": row.quantity,
        "status": row.status,
        "pickup_code": row.pickup_code,
        "fulfilled_at": row.fulfilled_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "is_issue": is_issue,
    }


def list_admin_orders(
    db: Session,
    *,
    user: User,
    status: str | None = None,
    issues_only: bool = False,
    event_id: uuid.UUID | None = None,
    host_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    _require_admin_view(user)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    stmt = select(MerchFulfillment).order_by(MerchFulfillment.created_at.desc())
    if status:
        stmt = stmt.where(MerchFulfillment.status == status)
    elif issues_only:
        stmt = stmt.where(
            MerchFulfillment.status.in_(
                ("awaiting_pickup", "collect_at_stand", "cancelled")
            )
        )
    if event_id:
        stmt = stmt.where(MerchFulfillment.event_id == event_id)
    if host_id:
        stmt = stmt.where(MerchFulfillment.host_id == host_id)

    rows = list(db.scalars(stmt.offset(offset).limit(limit * 3 if q else limit)).all())
    out = [serialize_admin_fulfillment(db, r) for r in rows]
    if q:
        needle = q.strip().lower()
        out = [
            row
            for row in out
            if needle
            in " ".join(
                str(v or "")
                for v in (
                    row.get("order_reference"),
                    row.get("product_name"),
                    row.get("variant_label"),
                    row.get("event_title"),
                    row.get("host_name"),
                    row.get("buyer_name"),
                    row.get("pickup_code"),
                )
            ).lower()
        ][:limit]
    else:
        out = out[:limit]
    return out


def _product_snapshot(product: EventMerchProduct | None) -> dict | None:
    if product is None:
        return None
    return {
        "id": str(product.id),
        "name": product.name,
        "status": product.status,
        "moderation_status": getattr(product, "moderation_status", None) or "clear",
        "product_type": getattr(product, "product_type", None),
        "base_price": str(product.base_price),
        "currency": product.currency,
        "image_url": product.image_url,
        "short_description": getattr(product, "short_description", None),
        "moderation_note": getattr(product, "moderation_note", None),
    }


def serialize_report(db: Session, report: MerchProductReport) -> dict:
    product = db.get(EventMerchProduct, report.product_id)
    event = db.get(Event, product.event_id) if product else None
    host = db.get(Host, product.host_id) if product else None
    reporter = db.get(User, report.reporter_user_id)
    resolver = (
        db.get(User, report.resolved_by_user_id) if report.resolved_by_user_id else None
    )
    return {
        "id": report.id,
        "product_id": report.product_id,
        "product_name": product.name if product else None,
        "product_status": product.status if product else None,
        "moderation_status": (
            getattr(product, "moderation_status", None) if product else None
        ),
        "product_snapshot": _product_snapshot(product),
        "event_id": product.event_id if product else None,
        "event_title": event.title if event else None,
        "host_id": product.host_id if product else None,
        "host_name": host.display_name if host else None,
        "reporter_user_id": report.reporter_user_id,
        "reporter_name": reporter.full_name if reporter else None,
        "reason": report.reason,
        "details": getattr(report, "details", None),
        "status": report.status,
        "admin_notes": getattr(report, "admin_notes", None),
        "resolved_at": report.resolved_at,
        "resolved_by_user_id": report.resolved_by_user_id,
        "resolved_by_name": resolver.full_name if resolver else None,
        "resolution_note": report.resolution_note,
        "created_at": report.created_at,
        "updated_at": getattr(report, "updated_at", None),
    }


def create_product_report(
    db: Session,
    *,
    user: User,
    product_id: uuid.UUID,
    reason: str,
    details: str | None = None,
) -> dict:
    reason_clean = reason.strip()
    if len(reason_clean) < 8:
        raise HTTPException(status_code=400, detail="Report reason is too short")

    product = db.get(EventMerchProduct, product_id)
    if product is None or product.archived_at is not None:
        raise HTTPException(status_code=404, detail="Merch product not found")

    existing = db.scalar(
        select(MerchProductReport).where(
            MerchProductReport.product_id == product_id,
            MerchProductReport.reporter_user_id == user.id,
            MerchProductReport.status.in_(tuple(OPEN_REPORT_STATUSES)),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="You already have an open report")

    report = MerchProductReport(
        product_id=product_id,
        reporter_user_id=user.id,
        reason=reason_clean[:1000],
        details=(details or "").strip() or None,
        status="open",
    )
    db.add(report)
    if getattr(product, "moderation_status", "clear") == "clear":
        product.moderation_status = "flagged"
    write_audit_log(
        db,
        action="merch.report.create",
        actor_user_id=user.id,
        resource_type="merch_product_report",
        resource_id=str(product_id),
        details={"reason": reason_clean[:200]},
    )
    db.commit()
    db.refresh(report)
    return serialize_report(db, report)


def list_admin_reports(
    db: Session,
    *,
    user: User,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    _require_admin_view(user)
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    stmt = select(MerchProductReport).order_by(MerchProductReport.created_at.desc())
    if status:
        if status not in REPORT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid report status")
        stmt = stmt.where(MerchProductReport.status == status)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    return [serialize_report(db, r) for r in rows]


def update_report(
    db: Session,
    *,
    user: User,
    report_id: uuid.UUID,
    status: str | None = None,
    admin_notes: str | None = None,
) -> dict:
    """Move a report into reviewing and/or update admin notes (open queue only)."""
    _require_admin_moderate(user)
    report = db.get(MerchProductReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status not in OPEN_REPORT_STATUSES:
        raise HTTPException(status_code=400, detail="Report is already closed")

    if status is not None:
        if status not in OPEN_REPORT_STATUSES:
            raise HTTPException(
                status_code=400,
                detail="Use resolve endpoint to close reports; status must be open or reviewing",
            )
        report.status = status
    if admin_notes is not None:
        report.admin_notes = admin_notes.strip() or None

    write_audit_log(
        db,
        action="merch.report.update",
        actor_user_id=user.id,
        resource_type="merch_product_report",
        resource_id=str(report.id),
        details={
            "status": report.status,
            "admin_notes_set": admin_notes is not None,
        },
    )
    db.commit()
    db.refresh(report)
    return serialize_report(db, report)


def resolve_report(
    db: Session,
    *,
    user: User,
    report_id: uuid.UUID,
    resolution: str,
    note: str | None = None,
    admin_notes: str | None = None,
    moderate_action: str | None = None,
) -> dict:
    _require_admin_moderate(user)
    if resolution not in {"resolved", "dismissed"}:
        raise HTTPException(
            status_code=400, detail="resolution must be resolved or dismissed"
        )
    report = db.get(MerchProductReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status not in OPEN_REPORT_STATUSES:
        raise HTTPException(status_code=400, detail="Report is already closed")

    note_clean = (note or "").strip() or None
    product_id = report.product_id

    if moderate_action:
        # Commits product moderation; report row is still open until we close it.
        moderate_product(
            db,
            user=user,
            product_id=product_id,
            action=moderate_action,
            note=note_clean or f"Report {resolution}",
        )
        report = db.get(MerchProductReport, report_id)
        assert report is not None

    report.status = resolution
    report.resolved_at = datetime.now(UTC)
    report.resolved_by_user_id = user.id
    report.resolution_note = note_clean
    if admin_notes is not None:
        report.admin_notes = admin_notes.strip() or None
    write_audit_log(
        db,
        action=f"merch.report.{resolution}",
        actor_user_id=user.id,
        resource_type="merch_product_report",
        resource_id=str(report.id),
        details={
            "note": note_clean,
            "product_id": str(product_id),
            "moderate_action": moderate_action,
        },
    )
    db.commit()
    report = db.get(MerchProductReport, report_id)
    assert report is not None
    return serialize_report(db, report)
