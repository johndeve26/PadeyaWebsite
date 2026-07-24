"""Candidate pool for event recommendations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.events.models import Event
from app.events.service import list_published_events
from app.hosts.models import Host


def list_recommendation_candidates(
    db: Session,
    *,
    limit: int,
    city: str | None = None,
    category: str | None = None,
) -> list[Event]:
    rows = list_published_events(
        db,
        city_slug=city,
        category_slug=category,
    )
    out: list[Event] = []
    for event in rows:
        if event.host_id is None:
            continue
        host = event.host
        if host is None:
            host = db.get(Host, event.host_id)
        if host is not None and host.status != "active":
            continue
        if event.visibility not in ("listed", "approval_required"):
            continue
        out.append(event)
        if len(out) >= limit:
            break
    return out
