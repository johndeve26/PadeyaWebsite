"""Admin read APIs for push delivery events (append-only)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.notifications.models import PushDeliveryEvent

SUMMARY_STATUSES = ("sent", "failed", "logged", "pending", "revoked")


def delivery_summary(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(PushDeliveryEvent.status, func.count())
        .group_by(PushDeliveryEvent.status)
    ).all()
    out = {status: 0 for status in SUMMARY_STATUSES}
    for status, count in rows:
        key = (status or "pending").lower()
        out[key] = int(count)
    out["total"] = sum(out[s] for s in SUMMARY_STATUSES)
    return out


def list_deliveries(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PushDeliveryEvent], int]:
    stmt = select(PushDeliveryEvent)
    count_stmt = select(func.count()).select_from(PushDeliveryEvent)
    if status:
        status_norm = status.strip().lower()
        stmt = stmt.where(PushDeliveryEvent.status == status_norm)
        count_stmt = count_stmt.where(PushDeliveryEvent.status == status_norm)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(PushDeliveryEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return rows, total


def serialize_delivery(row: PushDeliveryEvent) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "subscription_id": row.subscription_id,
        "notification_id": row.notification_id,
        "kind": row.kind,
        "status": row.status,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "sent_at": row.sent_at,
    }
