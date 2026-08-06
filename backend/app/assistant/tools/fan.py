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


def list_my_past_tickets(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        from app.events.models import Event
        from app.tickets.service import list_buyer_tickets

        tickets = list_buyer_tickets(db, user)
        event_ids = {t.event_id for t in tickets if getattr(t, "event_id", None)}
        events_by_id = {
            row.id: row
            for row in db.scalars(select(Event).where(Event.id.in_(event_ids))).all()
        } if event_ids else {}
        now = datetime.now(UTC)
        for ticket in tickets:
            event = events_by_id.get(getattr(ticket, "event_id", None))
            start = getattr(event, "start_datetime", None) if event else None
            if start is not None and start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            if start is None or start >= now:
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
    except Exception:
        results = []
    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "summary": f"You have {len(results)} past ticket(s) in recent history.",
    }


def list_my_saved_events(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    """Followed hosts — delegates to following summary."""
    from app.assistant.tools import insights

    summary = insights.get_my_following_summary(db, user=user, args=args)
    if not summary.get("ok"):
        return {**summary, "results": []}
    sample = summary.get("hosts_sample") or []
    results = [
        {
            "display_name": item.get("display_name"),
            "username": item.get("username"),
            "marketing_opt_in": item.get("marketing_opt_in"),
        }
        for item in sample
    ]
    return {
        "ok": True,
        "results": results,
        "count": summary.get("following_count", len(results)),
        "summary": summary.get("summary"),
    }


def list_upcoming_events_from_followed_hosts(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}

    limit = min(int((args or {}).get("limit") or 10), 25)
    try:
        from app.crm.service import list_my_following
        from app.events.models import Event

        following = list_my_following(db, user)
        host_ids = [row["host_id"] for row in following if row.get("host_id")]
        if not host_ids:
            return {
                "ok": True,
                "results": [],
                "count": 0,
                "following_count": 0,
                "summary": (
                    "You are not following any hosts yet, "
                    "so there are no upcoming events from followed hosts."
                ),
            }

        hosts_by_id = {row["host_id"]: row for row in following}
        now = datetime.now(UTC)
        events = list(
            db.scalars(
                select(Event)
                .where(Event.host_id.in_(host_ids))
                .where(Event.status == "published")
                .where(Event.visibility.in_(("listed", "approval_required")))
                .where(Event.end_datetime.is_not(None))
                .where(Event.end_datetime >= now)
                .order_by(Event.start_datetime.asc())
                .limit(limit)
            ).all()
        )

        results: list[dict[str, Any]] = []
        for event in events:
            host = hosts_by_id.get(event.host_id, {})
            results.append(
                {
                    "event_id": str(event.id),
                    "title": event.title,
                    "slug": event.slug,
                    "host_display_name": host.get("display_name"),
                    "host_slug": host.get("username"),
                    "city": getattr(event, "city", None),
                    "start_datetime": (
                        event.start_datetime.isoformat()
                        if event.start_datetime
                        else None
                    ),
                    "url": f"/events/{event.slug}" if event.slug else None,
                }
            )

        following_count = len(host_ids)
        if not results:
            summary = (
                f"You follow {following_count} host(s), "
                "but none have upcoming published events right now."
            )
        elif len(results) == 1:
            row = results[0]
            host_name = row.get("host_display_name") or "A host you follow"
            summary = f"{host_name} is hosting {row.get('title')} soon."
        else:
            bits = [
                f"{r.get('host_display_name') or 'Host'}: {r.get('title')}"
                for r in results[:3]
            ]
            summary = (
                f"{len(results)} upcoming event(s) from hosts you follow: "
                + "; ".join(bits)
                + "."
            )

        return {
            "ok": True,
            "results": results,
            "count": len(results),
            "following_count": following_count,
            "summary": summary,
        }
    except Exception:
        return {"ok": False, "error": "lookup_failed", "results": []}
