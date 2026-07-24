"""Verified merch product reviews — hosts cannot delete."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.merch.constants import ITEM_KIND_MERCH, REVIEW_STATUSES
from app.merch.models import EventMerchProduct, MerchFulfillment, MerchReview
from app.merch.notifications import notify_host_review_received
from app.passport.models import FanPassport
from app.passport.privacy import is_publicly_reachable
from app.payments.models import Order, OrderItem
from app.users.models import User


def _author_display(db: Session, user_id: uuid.UUID) -> str:
    """Public-safe buyer label. Never email/phone; respect passport display."""
    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    if passport is not None and is_publicly_reachable(passport.visibility):
        name = (passport.display_name or "").strip()
        if name:
            return name
    # Private / missing passport: do not leak account full_name on public surfaces.
    return "Attendee"


def _safe_event_chip(event: Event | None) -> tuple[str | None, str | None]:
    """Title/slug only — never venue, address, or private location fields."""
    if event is None:
        return None, None
    return event.title, event.slug


def serialize_public_review(db: Session, row: MerchReview) -> dict:
    event = db.get(Event, row.event_id) if row.event_id else None
    event_title, event_slug = _safe_event_chip(event)
    return {
        "id": row.id,
        "product_id": row.product_id,
        "rating": row.rating,
        "body": row.body,
        "status": row.status,
        "verified_purchase": True,
        "author_display_name": _author_display(db, row.buyer_user_id),
        "event_title": event_title,
        "event_slug": event_slug,
        "host_reply": row.host_reply,
        "host_replied_at": row.host_replied_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        # Never: order_id, order_item_id, amounts, email, phone, address
    }


def serialize_staff_review(db: Session, row: MerchReview) -> dict:
    """Host/admin list shape — still no order/payment/contact PII."""
    data = serialize_public_review(db, row)
    product = db.get(EventMerchProduct, row.product_id)
    data["product_name"] = product.name if product else None
    data["admin_note"] = row.admin_note
    return data


def create_review(
    db: Session,
    *,
    user: User,
    order_item_id: uuid.UUID,
    rating: int,
    body: str | None = None,
) -> dict:
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1–5")
    item = db.get(OrderItem, order_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Order item not found")
    kind = getattr(item, "item_kind", None) or (
        ITEM_KIND_MERCH if item.merch_variant_id else "ticket"
    )
    if kind != ITEM_KIND_MERCH:
        raise HTTPException(status_code=400, detail="Only merch purchases can be reviewed")
    order = db.get(Order, item.order_id)
    if order is None or order.buyer_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your purchase")
    if order.status != "paid":
        raise HTTPException(
            status_code=400, detail="Reviews require a verified paid purchase"
        )
    fulfillment = db.scalar(
        select(MerchFulfillment).where(MerchFulfillment.order_item_id == item.id)
    )
    if fulfillment is None:
        raise HTTPException(
            status_code=400, detail="Merch must be paid before reviewing"
        )
    existing = db.scalar(
        select(MerchReview).where(MerchReview.order_item_id == item.id)
    )
    if existing and existing.status != "removed_by_user":
        raise HTTPException(status_code=400, detail="You already reviewed this purchase")

    product_id = item.merch_product_id
    if product_id is None:
        raise HTTPException(status_code=400, detail="Missing product on order item")
    product = db.get(EventMerchProduct, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    from app.hosts.fan_self_abuse import assert_not_own_host_public_review

    assert_not_own_host_public_review(
        db, user_id=user.id, host_id=product.host_id
    )

    # Verified purchase reviews publish immediately (pending reserved for future queues).
    if existing and existing.status == "removed_by_user":
        existing.rating = rating
        existing.body = (body or "").strip() or None
        existing.status = "published"
        existing.host_reply = None
        existing.host_replied_at = None
        row = existing
    else:
        row = MerchReview(
            product_id=product.id,
            order_item_id=item.id,
            buyer_user_id=user.id,
            host_id=product.host_id,
            event_id=product.event_id or order.event_id,
            rating=rating,
            body=(body or "").strip() or None,
            status="published",
        )
        db.add(row)
    assert row.status in REVIEW_STATUSES
    db.flush()
    from app.analytics.trusted import emit_merch_review_submitted

    emit_merch_review_submitted(
        db,
        event_id=row.event_id,
        host_id=row.host_id,
        buyer_user_id=user.id,
        merch_product_id=product.id,
        order_item_id=item.id,
    )
    notify_host_review_received(db, review=row)
    db.commit()
    db.refresh(row)
    return serialize_public_review(db, row)


def get_own_review_for_order_item(
    db: Session, *, user: User, order_item_id: uuid.UUID
) -> dict | None:
    row = db.scalar(
        select(MerchReview).where(
            MerchReview.order_item_id == order_item_id,
            MerchReview.buyer_user_id == user.id,
        )
    )
    if row is None or row.status == "removed_by_user":
        return None
    return serialize_public_review(db, row)


def update_own_review(
    db: Session,
    *,
    user: User,
    review_id: uuid.UUID,
    rating: int | None = None,
    body: str | None = None,
) -> dict:
    row = db.get(MerchReview, review_id)
    if row is None or row.buyer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Review not found")
    if row.status == "removed_by_user":
        raise HTTPException(status_code=400, detail="Review was removed")
    if rating is not None:
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be 1–5")
        row.rating = rating
    if body is not None:
        row.body = body.strip() or None
    db.commit()
    db.refresh(row)
    return serialize_public_review(db, row)


def remove_own_review(db: Session, *, user: User, review_id: uuid.UUID) -> dict:
    row = db.get(MerchReview, review_id)
    if row is None or row.buyer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Review not found")
    row.status = "removed_by_user"
    db.commit()
    return {"id": row.id, "status": row.status}


def host_reply(
    db: Session,
    *,
    host_id: uuid.UUID,
    review_id: uuid.UUID,
    reply: str,
    actor_user_id: uuid.UUID,
) -> dict:
    row = db.get(MerchReview, review_id)
    if row is None or row.host_id != host_id:
        raise HTTPException(status_code=404, detail="Review not found")
    # Hosts cannot delete reviews — reply only.
    cleaned = reply.strip()
    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="Reply is too short")
    row.host_reply = cleaned[:4000]
    row.host_replied_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="merch.review_host_reply",
        actor_user_id=actor_user_id,
        resource_type="merch_review",
        resource_id=str(row.id),
        details={"product_id": str(row.product_id)},
    )
    db.commit()
    db.refresh(row)
    return serialize_staff_review(db, row)


def admin_moderate_review(
    db: Session,
    *,
    review_id: uuid.UUID,
    action: str,
    note: str | None,
    actor_user_id: uuid.UUID,
) -> dict:
    row = db.get(MerchReview, review_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if action == "hide":
        row.status = "hidden_by_admin"
    elif action == "restore":
        row.status = "published"
    else:
        raise HTTPException(status_code=400, detail="action must be hide or restore")
    row.admin_note = (note or "").strip()[:1000] or None
    write_audit_log(
        db,
        action=f"merch.review_{action}",
        actor_user_id=actor_user_id,
        resource_type="merch_review",
        resource_id=str(row.id),
        details={"note": (note or "")[:200]},
    )
    db.commit()
    db.refresh(row)
    return serialize_staff_review(db, row)


def list_product_reviews(db: Session, *, product_id: uuid.UUID) -> dict:
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    product = db.get(EventMerchProduct, product_id)
    rows = list(
        db.scalars(
            select(MerchReview)
            .where(
                MerchReview.product_id == product_id,
                MerchReview.status == "published",
            )
            .order_by(MerchReview.created_at.desc())
        )
    )
    if product is not None:
        rows = [
            r
            for r in rows
            if not is_user_owner_of_host(
                db, user_id=r.buyer_user_id, host_profile_id=product.host_id
            )
        ]
    avg = None
    if rows:
        avg = float(sum(r.rating for r in rows) / len(rows))
    return {
        "average_rating": avg,
        "review_count": len(rows),
        "reviews": [serialize_public_review(db, r) for r in rows],
    }


def list_host_reviews(db: Session, *, host_id: uuid.UUID) -> list[dict]:
    rows = list(
        db.scalars(
            select(MerchReview)
            .where(
                MerchReview.host_id == host_id,
                MerchReview.status.in_(("published", "hidden_by_admin", "pending")),
            )
            .order_by(MerchReview.created_at.desc())
        )
    )
    return [serialize_staff_review(db, r) for r in rows]


def list_admin_reviews(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(MerchReview).order_by(MerchReview.created_at.desc())
    if status:
        if status not in REVIEW_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid review status")
        stmt = stmt.where(MerchReview.status == status)
    else:
        stmt = stmt.where(
            MerchReview.status.in_(
                ("pending", "published", "hidden_by_admin")
            )
        )
    rows = list(db.scalars(stmt.offset(offset).limit(min(limit, 200))))
    return [serialize_staff_review(db, r) for r in rows]
