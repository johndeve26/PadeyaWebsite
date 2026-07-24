"""Safe context for host.announcements.draft — no recipient PII or Vault bodies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.context_scrubber import scrub_context, venue_allowed_for_ai
from app.events.models import Event
from app.hosts.service import require_actor_host
from app.users.models import User


ANNOUNCEMENT_SAFE_KEYS = frozenset(
    {
        "host_name",
        "event_title",
        "event_date",
        "event_city",
        "event_area",
        "event_category",
        "announcement_type",
        "channel",
        "audience_label",
        "host_notes",
        "merch_title",
        "vault_label",
        "location_visibility",
    }
)


@dataclass(frozen=True)
class HostAnnouncementContextResult:
    """Named result for host.announcements.draft — avoids tuple unpack mistakes."""

    scrubbed_context: dict[str, str]
    host_id: UUID
    redactions: list[str]


def build_host_announcement_context(
    db: Session,
    *,
    user: User,
    event_id: UUID | None,
    notes: str | None,
    extra: dict[str, Any] | None,
) -> HostAnnouncementContextResult:
    host = require_actor_host(
        db,
        user,
        permission=(
            "announcements.create",
            "announcements.update_draft",
            "events.create",
            "events.manage_own",
        ),
    )
    raw: dict[str, Any] = {
        "host_name": host.display_name or "",
        "event_title": "",
        "event_date": "",
        "event_city": "",
        "event_area": "",
        "event_category": "",
        "announcement_type": "",
        "channel": "",
        "audience_label": "",
        "host_notes": (notes or "").strip(),
        "merch_title": "",
        "vault_label": "",
        "location_visibility": "full_public",
    }
    if extra:
        for key in ANNOUNCEMENT_SAFE_KEYS:
            if key in extra and extra[key] is not None:
                raw[key] = extra[key]
        # Drop any non-allowlisted keys silently (scrubber will also drop forbidden)

    if event_id is not None:
        event = db.get(Event, event_id)
        if event is None or event.host_id != host.id:
            raise HTTPException(status_code=404, detail="Event not found")
        visibility = getattr(event, "location_visibility", None) or "full_public"
        raw["location_visibility"] = visibility
        raw["event_title"] = event.title or ""
        category = ""
        if event.category is not None:
            category = event.category.name or ""
        raw["event_category"] = category
        if event.start_datetime:
            raw["event_date"] = event.start_datetime.isoformat()
        city = getattr(event, "city", None) or ""
        area = getattr(event, "area", None) or ""
        raw["event_city"] = str(city)
        raw["event_area"] = str(area)
        if not venue_allowed_for_ai(str(visibility)):
            raw["event_area"] = area or city or ""

    scrubbed, redactions = scrub_context(
        raw,
        location_visibility=str(raw.get("location_visibility") or "full_public"),
        allowlist=ANNOUNCEMENT_SAFE_KEYS,
    )
    scrubbed["host_name"] = host.display_name or ""
    return HostAnnouncementContextResult(
        scrubbed_context=scrubbed,
        host_id=host.id,
        redactions=redactions,
    )
