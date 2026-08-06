"""Host-scoped tools — owned events only; never publish."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.users.models import User
from app.users.service import user_has_permission, user_has_role


def _user_hosts(db: Session, user: User) -> list[Any]:
    from sqlalchemy import select

    from app.hosts.models import Host

    return list(db.scalars(select(Host).where(Host.user_id == user.id)).all())


def list_my_events(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    if not user_has_role(user, "host", "super_admin"):
        return {"ok": False, "error": "forbidden", "results": []}
    limit = min(int((args or {}).get("limit") or 15), 40)
    results: list[dict[str, Any]] = []
    try:
        from app.events.service import list_host_events

        for host in _user_hosts(db, user):
            for event in list_host_events(db, host)[:limit]:
                results.append(
                    {
                        "id": str(event.id),
                        "slug": event.slug,
                        "title": event.title,
                        "status": event.status,
                        "start_datetime": (
                            event.start_datetime.isoformat()
                            if event.start_datetime
                            else None
                        ),
                    }
                )
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
    except Exception:
        results = []
    return {"ok": True, "results": results, "count": len(results)}


def get_my_event_summary(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "host", "super_admin"):
        return {"ok": False, "error": "forbidden"}
    args = args or {}
    event_id = str(args.get("event_id") or "").strip()
    slug = str(args.get("slug") or "").strip()
    try:
        from uuid import UUID

        from app.events.service import get_event_by_id, get_event_by_slug

        event = None
        if event_id:
            event = get_event_by_id(db, UUID(event_id))
        elif slug:
            event = get_event_by_slug(db, slug)
        if event is None:
            return {"ok": False, "error": "not_found"}
        host_ids = {h.id for h in _user_hosts(db, user)}
        if event.host_id not in host_ids and not user_has_role(user, "super_admin"):
            return {"ok": False, "error": "forbidden"}
        return {
            "ok": True,
            "event": {
                "id": str(event.id),
                "slug": event.slug,
                "title": event.title,
                "status": event.status,
                "visibility": getattr(event, "visibility", None),
                "start_datetime": (
                    event.start_datetime.isoformat() if event.start_datetime else None
                ),
                "city": getattr(event, "city", None),
            },
        }
    except Exception:
        return {"ok": False, "error": "lookup_failed"}


def create_event_draft(
    db: Session,
    *,
    user: User | None,
    args: dict[str, Any] | None = None,
    confirmed: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """Create draft only after confirmation. Never publishes."""
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "host", "super_admin"):
        return {"ok": False, "error": "forbidden"}
    if not user_has_permission(user, "events.create") and not user_has_role(
        user, "super_admin"
    ):
        return {"ok": False, "error": "forbidden"}
    if not confirmed:
        return {
            "ok": False,
            "error": "confirmation_required",
            "message": "Confirm to create an event draft. Publishing is never done by the assistant.",
        }
    args = args or {}
    title = str(args.get("title") or "Untitled event").strip()[:160]
    if len(title) < 3:
        title = "Untitled event"
    description = str(
        args.get("description")
        or f"Draft event created via Pàdéyá Copilot for {title}."
    ).strip()
    if len(description) < 10:
        description = f"Draft event created via Pàdéyá Copilot for {title}."
    try:
        from datetime import UTC, datetime, timedelta

        from app.events.schemas import EventCreate
        from app.events.service import create_event

        start = datetime.now(UTC) + timedelta(days=14)
        end = start + timedelta(hours=4)
        # Allow ISO overrides when provided
        if args.get("start_datetime"):
            start = datetime.fromisoformat(str(args["start_datetime"]).replace("Z", "+00:00"))
        if args.get("end_datetime"):
            end = datetime.fromisoformat(str(args["end_datetime"]).replace("Z", "+00:00"))
        payload = EventCreate(
            title=title,
            description=description,
            start_datetime=start,
            end_datetime=end,
            visibility="unlisted",
        )
        event = create_event(db, user=user, payload=payload)
        if getattr(event, "status", None) != "draft":
            return {"ok": False, "error": "refused_non_draft"}
        return {
            "ok": True,
            "event": {
                "id": str(event.id),
                "slug": event.slug,
                "title": event.title,
                "status": event.status,
                "url": f"/host/events/{event.id}",
            },
            "note": "Draft created. Publish only from Host Studio after adding ticket types.",
        }
    except Exception as exc:
        return {"ok": False, "error": "create_failed", "detail": type(exc).__name__}


def draft_event_description(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "host", "super_admin"):
        return {"ok": False, "error": "forbidden"}
    args = args or {}
    title = str(args.get("title") or "your event").strip()[:160]
    vibe = str(args.get("vibe") or args.get("notes") or "").strip()[:400]
    city = str(args.get("city") or "").strip()[:80]
    lines = [
        f"Join us for {title}" + (f" in {city}" if city else "") + ".",
        "Expect a warm, well-hosted night with community energy.",
    ]
    if vibe:
        lines.append(vibe)
    lines.append("Tickets available on Pàdéyá — see you there.")
    return {
        "ok": True,
        "draft": "\n\n".join(lines),
        "note": "Suggestion only — edit and save in Host Studio. The assistant will not publish.",
    }
