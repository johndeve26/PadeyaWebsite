"""Fan-scoped tools — own tickets/orders/saved only."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User


def get_my_ticket_summary(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    try:
        from app.events.models import Event
        from app.tickets.service import list_buyer_tickets

        tickets = list_buyer_tickets(db, user)
    except Exception:
        return {
            "ok": True,
            "total_tickets": 0,
            "upcoming_count": 0,
            "past_count": 0,
            "summary": "You have 0 tickets on your account.",
        }

    event_ids = {t.event_id for t in tickets if getattr(t, "event_id", None)}
    events_by_id: dict[Any, Any] = {}
    if event_ids:
        events_by_id = {
            row.id: row
            for row in db.scalars(select(Event).where(Event.id.in_(event_ids))).all()
        }

    now = datetime.now(UTC)
    upcoming = 0
    past = 0
    for ticket in tickets:
        event = events_by_id.get(getattr(ticket, "event_id", None))
        start = getattr(event, "start_datetime", None) if event else None
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if start is not None and start < now:
            past += 1
        else:
            upcoming += 1

    total = len(tickets)
    if total == 0:
        summary = "You have 0 tickets on your account."
    elif total == 1:
        summary = f"You have 1 ticket ({upcoming} upcoming, {past} past)."
    else:
        summary = f"You have {total} tickets ({upcoming} upcoming, {past} past)."

    return {
        "ok": True,
        "total_tickets": total,
        "upcoming_count": upcoming,
        "past_count": past,
        "summary": summary,
    }


def list_my_upcoming_tickets(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    limit = min(int((args or {}).get("limit") or 10), 25)
    try:
        from app.tickets.service import list_buyer_tickets

        tickets = list_buyer_tickets(db, user)
    except Exception:
        return {"ok": True, "results": [], "count": 0}
    now = datetime.now(UTC)
    results = []
    for ticket in tickets:
        # Best-effort upcoming filter via related event if present
        event = getattr(ticket, "event", None)
        start = getattr(event, "start_datetime", None) if event else None
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if start is not None and start < now:
            continue
        results.append(
            {
                "ticket_id": str(ticket.id),
                "status": getattr(ticket, "status", None),
                "event_title": getattr(event, "title", None) if event else None,
                "event_slug": getattr(event, "slug", None) if event else None,
                "start_datetime": start.isoformat() if start else None,
            }
        )
        if len(results) >= limit:
            break
    return {"ok": True, "results": results, "count": len(results)}


def get_my_order_summary(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    limit = min(int((args or {}).get("limit") or 5), 15)
    results: list[dict[str, Any]] = []
    try:
        from app.payments.models import Order

        stmt = (
            select(Order)
            .where(Order.buyer_user_id == user.id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        orders = list(db.scalars(stmt).all())
        for order in orders:
            results.append(
                {
                    "order_id": str(order.id),
                    "status": getattr(order, "status", None),
                    "created_at": (
                        order.created_at.isoformat()
                        if getattr(order, "created_at", None)
                        else None
                    ),
                    # No payment refs, emails, or amounts breakdown secrets
                    "currency": getattr(order, "currency", None),
                }
            )
    except Exception:
        results = []
    return {"ok": True, "results": results, "count": len(results)}


def list_my_saved_events(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    """Best-effort saved/followed hosts — empty list if no saved-events module."""
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        from app.crm.models import HostFollower

        stmt = (
            select(HostFollower)
            .where(HostFollower.user_id == user.id)
            .limit(limit)
        )
        rows = list(db.scalars(stmt).all())
        for row in rows:
            results.append(
                {
                    "host_id": str(getattr(row, "host_id", "")),
                    "followed_at": (
                        row.created_at.isoformat()
                        if getattr(row, "created_at", None)
                        else None
                    ),
                }
            )
    except Exception:
        results = []
    return {"ok": True, "results": results, "count": len(results)}
