"""Read-only account and host analytics tools (aggregates only — no PII exports)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.users.models import User
from app.users.service import user_has_permission, user_has_role


def _resolve_host_event(
    db: Session,
    *,
    user: User,
    args: dict[str, Any],
    page_context: dict[str, Any] | None,
    query: str,
) -> tuple[UUID | None, Any | None]:
    """Resolve an owned event by id, slug, page context, or title match."""
    from app.events.service import get_event_by_id, get_event_by_slug
    from app.assistant.tools.host import list_my_events

    raw_id = (
        args.get("event_id")
        or args.get("id")
        or (page_context or {}).get("entity_public_id")
    )
    if raw_id:
        try:
            event = get_event_by_id(db, UUID(str(raw_id)))
            if event is not None:
                return event.id, event
        except (ValueError, TypeError):
            pass

    slug = str(args.get("slug") or args.get("event_slug") or "").strip()
    if slug:
        event = get_event_by_slug(db, slug)
        if event is not None:
            return event.id, event

    ql = (query or "").lower()
    tokens = [t for t in ql.replace("?", " ").split() if len(t) >= 4]
    skip = {
        "many",
        "tickets",
        "ticket",
        "sold",
        "sales",
        "event",
        "hosting",
        "have",
        "been",
        "does",
        "what",
        "show",
        "tell",
        "count",
        "total",
        "padeya",
        "padeyá",
    }
    tokens = [t for t in tokens if t not in skip]

    for item in (list_my_events(db, user=user, args={"limit": 40}).get("results") or []):
        title = (item.get("title") or "").lower()
        item_slug = (item.get("slug") or "").lower()
        if item_slug and item_slug in ql:
            event = get_event_by_slug(db, item_slug)
            return (event.id, event) if event else (None, None)
        if tokens and any(tok in title for tok in tokens):
            try:
                event = get_event_by_id(db, UUID(str(item["id"])))
                if event is not None:
                    return event.id, event
            except (ValueError, TypeError, KeyError):
                continue
    return None, None


def get_my_following_summary(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    try:
        from app.crm.service import list_my_following

        rows = list_my_following(db, user)
    except Exception:
        rows = []
    opted_in = sum(1 for row in rows if row.get("marketing_opt_in"))
    sample = [
        {
            "display_name": row.get("display_name"),
            "username": row.get("username"),
            "marketing_opt_in": bool(row.get("marketing_opt_in")),
        }
        for row in rows[:8]
    ]
    count = len(rows)
    summary = (
        f"You follow {count} host(s)."
        if count != 1
        else "You follow 1 host."
    )
    if opted_in:
        summary += f" {opted_in} with marketing updates enabled."
    return {
        "ok": True,
        "following_count": count,
        "marketing_opt_in_count": opted_in,
        "hosts_sample": sample,
        "summary": summary,
    }


def get_my_fan_connect_summary(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_permission(user, "fan_connect.use"):
        return {
            "ok": False,
            "error": "forbidden",
            "detail": "Fan Connect is not enabled for your account.",
        }
    try:
        from app.fan_connect.service import list_connections

        data = list_connections(db, user)
        count = len(data.get("items") or [])
    except Exception:
        count = 0
    return {
        "ok": True,
        "connection_count": count,
        "summary": (
            f"You have {count} Fan Connect connection(s)."
            if count != 1
            else "You have 1 Fan Connect connection."
        ),
    }


def get_my_audience_summary(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "host", "super_admin"):
        return {
            "ok": False,
            "error": "forbidden",
            "detail": "Host profile required for audience metrics.",
        }
    try:
        from app.crm.service import host_audience_dashboard

        stats = host_audience_dashboard(db, user)
    except HTTPException as exc:
        return {
            "ok": False,
            "error": "forbidden" if exc.status_code == 403 else "not_found",
            "detail": str(getattr(exc, "detail", "") or ""),
        }
    except Exception:
        return {"ok": False, "error": "lookup_failed"}

    return {
        "ok": True,
        "stats": stats,
        "summary": (
            f"You have {stats['followers']} followers, "
            f"{stats['marketing_opted_in']} marketing opt-ins, "
            f"{stats['past_buyers']} past buyers, "
            f"{stats['repeat_buyers']} repeat buyers, and "
            f"{stats['checked_in_attendees']} checked-in attendees."
        ),
    }


def get_my_event_analytics(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    page_context: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "host", "super_admin") and not user_has_permission(
        user, "analytics.view_events", "analytics.view_own", "admin.full_access"
    ):
        return {
            "ok": False,
            "error": "forbidden",
            "detail": "Analytics permission required.",
        }

    args = args or {}
    query = str(args.get("query") or args.get("q") or "")
    event_id, event = _resolve_host_event(
        db,
        user=user,
        args=args,
        page_context=page_context,
        query=query,
    )
    if event_id is None or event is None:
        return {
            "ok": False,
            "error": "event_not_found",
            "detail": "Name the event or open its page so I can look up sales metrics.",
        }

    try:
        from app.analytics.event_detail_reports import build_event_overview
        from app.analytics.event_filters import EventAnalyticsFilters
        from app.hosts.team_access import require_host_event_permission

        host, owned = require_host_event_permission(
            db,
            user=user,
            event_id=event_id,
            permission="analytics.view_events",
        )
        start = getattr(owned, "created_at", None) or datetime(2020, 1, 1, tzinfo=UTC)
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        filters = EventAnalyticsFilters.from_query(
            date_from=start,
            date_to=datetime.now(UTC),
        )
        overview = build_event_overview(
            db,
            event_id=owned.id,
            filters=filters,
            host_id=host.id,
        )
    except HTTPException as exc:
        return {
            "ok": False,
            "error": "forbidden" if exc.status_code == 403 else "not_found",
            "detail": str(getattr(exc, "detail", "") or ""),
        }
    except Exception:
        return {"ok": False, "error": "lookup_failed"}

    title = overview.get("title") or getattr(owned, "title", "Event")
    tickets_sold = int(overview.get("tickets_sold") or 0)
    check_ins = int(overview.get("check_in_count") or 0)
    purchases = int(overview.get("purchases") or 0)
    unique_visitors = int(overview.get("unique_visitors") or 0)

    return {
        "ok": True,
        "event": {
            "id": str(owned.id),
            "slug": owned.slug,
            "title": title,
        },
        "tickets_sold": tickets_sold,
        "purchases": purchases,
        "check_ins": check_ins,
        "unique_visitors": unique_visitors,
        "impressions": int(overview.get("impressions") or 0),
        "checkout_starts": int(overview.get("checkout_starts") or 0),
        "summary": (
            f"{title}: {tickets_sold} tickets sold, "
            f"{check_ins} check-ins, {unique_visitors} unique visitors."
        ),
    }


def get_my_fan_connect_inbox_summary(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_permission(user, "fan_connect.use"):
        return {"ok": False, "error": "forbidden", "detail": "Fan Connect not enabled."}
    incoming = outgoing = 0
    try:
        from app.fan_connect.service import list_connections, list_requests

        incoming = len((list_requests(db, user, box="incoming") or {}).get("items") or [])
        outgoing = len((list_requests(db, user, box="outgoing") or {}).get("items") or [])
        connected = len((list_connections(db, user) or {}).get("items") or [])
    except Exception:
        connected = 0
    return {
        "ok": True,
        "incoming_requests": incoming,
        "outgoing_requests": outgoing,
        "connection_count": connected,
        "summary": (
            f"Fan Connect: {connected} connection(s), "
            f"{incoming} incoming request(s), {outgoing} outgoing request(s)."
        ),
    }


def list_my_audience_segments(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    if not user_has_role(user, "host", "super_admin"):
        return {"ok": False, "error": "forbidden", "results": []}
    results: list[dict[str, Any]] = []
    try:
        from app.crm.service import list_segments

        for row in list_segments(db, user):
            results.append(
                {
                    "name": row.get("name"),
                    "segment_key": row.get("segment_key"),
                    "member_count": int(row.get("member_count") or 0),
                    "is_system": bool(row.get("is_system")),
                }
            )
    except Exception:
        results = []
    total_members = sum(int(r.get("member_count") or 0) for r in results)
    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "summary": f"You have {len(results)} audience segment(s) ({total_members} total segment memberships).",
    }


def get_my_announcements_summary(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "host", "super_admin"):
        return {"ok": False, "error": "forbidden"}
    rows: list[dict[str, Any]] = []
    try:
        from app.crm.service import list_announcements

        for row in list_announcements(db, user)[:20]:
            rows.append(
                {
                    "title": row.get("title"),
                    "status": row.get("status"),
                    "delivery_status": row.get("delivery_status"),
                    "recipient_count": int(row.get("recipient_count") or 0),
                    "channel": row.get("channel"),
                }
            )
    except Exception:
        rows = []
    sent = sum(int(r.get("recipient_count") or 0) for r in rows)
    return {
        "ok": True,
        "announcements": rows,
        "count": len(rows),
        "total_recipients": sent,
        "summary": f"You have {len(rows)} announcement(s) reaching {sent} recipients in total.",
    }


def get_my_host_ambassador_analytics(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "host", "super_admin"):
        return {"ok": False, "error": "forbidden"}
    try:
        from app.ambassadors.host_service import host_analytics

        stats = host_analytics(db, user)
    except HTTPException as exc:
        return {
            "ok": False,
            "error": "forbidden" if exc.status_code == 403 else "not_found",
            "detail": str(getattr(exc, "detail", "") or ""),
        }
    except Exception:
        return {"ok": False, "error": "lookup_failed"}

    campaigns = int(stats.get("campaigns") or 0)
    participants = int(stats.get("active_participants") or 0)
    clicks = int(stats.get("clicks") or stats.get("total_clicks") or 0)
    conversions = int(stats.get("conversions") or 0)
    return {
        "ok": True,
        "stats": stats,
        "summary": (
            f"Ambassador program: {campaigns} campaign(s), {participants} active participant(s), "
            f"{clicks} clicks, {conversions} conversion(s)."
        ),
    }
