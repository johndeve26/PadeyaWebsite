"""Safe context for host.sponsorship.pitch — public host metrics only."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.context_scrubber import scrub_context, venue_allowed_for_ai
from app.events.models import Event
from app.hosts.models import HostProfile
from app.hosts.service import require_actor_host
from app.legacy.models import HostLegacyPage
from app.legacy.service import collect_host_metrics, get_my_tier_progress
from app.sponsorships.constants import SLOT_TYPE_LABELS
from app.users.models import User


SPONSORSHIP_SAFE_KEYS = frozenset(
    {
        "host_name",
        "host_category",
        "host_city",
        "legacy_tier",
        "follower_count",
        "verified_checkins",
        "average_rating",
        "review_count",
        "events_hosted",
        "public_events_summary",
        "aggregate_stats",
        "slot_type",
        "slot_type_label",
        "host_notes",
    }
)


def _public_events_summary(db: Session, *, host_id: UUID, limit: int = 5) -> str:
    rows = db.scalars(
        select(Event)
        .where(
            Event.host_id == host_id,
            Event.status.in_(["published", "completed"]),
        )
        .order_by(Event.start_datetime.desc().nullslast())
        .limit(limit)
    ).all()
    items: list[dict[str, str]] = []
    for ev in rows:
        visibility = getattr(ev, "location_visibility", None) or "full_public"
        city = ev.city or ""
        if not venue_allowed_for_ai(str(visibility)):
            city = city or "public area"
        cat = ev.category.name if ev.category else ""
        items.append(
            {
                "title": (ev.title or "")[:120],
                "date": ev.start_datetime.isoformat() if ev.start_datetime else "",
                "category": cat[:80],
                "city": city[:80],
            }
        )
    return json.dumps(items, default=str)[:2000]


def build_host_sponsorship_context(
    db: Session,
    *,
    user: User,
    notes: str | None,
    extra: dict[str, Any] | None,
) -> tuple[dict[str, str], UUID, list[str]]:
    host = require_actor_host(db, user, permission="sponsorships.manage")
    profile = db.scalar(select(HostProfile).where(HostProfile.host_id == host.id))
    page = db.scalar(select(HostLegacyPage).where(HostLegacyPage.host_id == host.id))

    tier_name = ""
    try:
        progress = get_my_tier_progress(db, user)
        current = progress.get("current_tier") or {}
        if isinstance(current, dict):
            tier_name = str(current.get("name") or "")
    except Exception:
        tier_name = ""

    metrics = collect_host_metrics(db, host.id)
    follower_count = str(metrics.followers or 0)
    checkins = str(metrics.verified_checkins or 0)
    rating = (
        str(round(float(metrics.average_verified_rating), 2))
        if metrics.average_verified_rating is not None
        else ""
    )
    review_count = str(metrics.review_count or 0)
    events_hosted = str(metrics.events_hosted or 0)

    category = ""
    if page and page.primary_category_slug:
        category = page.primary_category_slug
    city = (profile.city if profile else None) or ""
    if page and page.service_areas and isinstance(page.service_areas, list):
        areas = [str(a) for a in page.service_areas[:3] if a]
        if areas and not city:
            city = areas[0][:80]

    slot_type = ""
    slot_label = ""
    if extra:
        slot_type = str(extra.get("slot_type") or extra.get("sponsorship_slot_type") or "")
        slot_label = str(extra.get("slot_type_label") or "")

    if slot_type and not slot_label:
        slot_label = SLOT_TYPE_LABELS.get(slot_type, slot_type)

    aggregate = json.dumps(
        {
            "tickets_sold_aggregate": metrics.tickets_sold,
            "completed_events": metrics.completed_events,
            "followers": metrics.followers,
            "verified_checkins": metrics.verified_checkins,
            "review_count": metrics.review_count,
        },
        default=str,
    )[:1500]

    raw: dict[str, Any] = {
        "host_name": host.display_name or "",
        "host_category": category,
        "host_city": city,
        "legacy_tier": tier_name,
        "follower_count": follower_count,
        "verified_checkins": checkins,
        "average_rating": rating,
        "review_count": review_count,
        "events_hosted": events_hosted,
        "public_events_summary": _public_events_summary(db, host_id=host.id),
        "aggregate_stats": aggregate,
        "slot_type": slot_type,
        "slot_type_label": slot_label,
        "host_notes": (notes or "").strip(),
    }
    if extra:
        for key in SPONSORSHIP_SAFE_KEYS:
            if key in extra and extra[key] is not None and key not in (
                "host_name",
                "follower_count",
                "verified_checkins",
                "average_rating",
                "review_count",
                "events_hosted",
                "public_events_summary",
                "aggregate_stats",
                "legacy_tier",
                "host_category",
                "host_city",
            ):
                raw[key] = extra[key]

    scrubbed, redactions = scrub_context(
        raw,
        location_visibility="full_public",
        allowlist=SPONSORSHIP_SAFE_KEYS,
    )
    scrubbed["host_name"] = host.display_name or ""
    return scrubbed, redactions, host.id
