"""Month-grouped public event calendar for discovery."""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.events.models import Event
from app.events.service import list_published_events, serialize_event


def parse_month(raw: str) -> tuple[int, int]:
    """Parse ``YYYY-MM`` → (year, month). Raises ValueError on bad input."""
    parts = (raw or "").strip().split("-")
    if len(parts) != 2:
        raise ValueError("month must be YYYY-MM")
    year = int(parts[0])
    month = int(parts[1])
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        raise ValueError("month out of range")
    return year, month


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Inclusive UTC window covering the calendar month (local dates via start_datetime date)."""
    start = datetime(year, month, 1, tzinfo=UTC)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)
    return start, end


def _min_public_price(event: Event) -> Decimal | None:
    prices: list[Decimal] = []
    for tt in event.ticket_types or []:
        if getattr(tt, "visibility", "public") != "public":
            continue
        try:
            prices.append(Decimal(str(tt.price)))
        except Exception:  # noqa: BLE001
            continue
    if not prices:
        return None
    return min(prices)


def compact_calendar_event(event: Event) -> dict:
    """Compact fields for calendar cells — not full EventPublic."""
    data = serialize_event(event, access="public")
    min_price = _min_public_price(event)
    return {
        "id": data["id"],
        "slug": data["slug"],
        "title": data["title"],
        "start_datetime": data["start_datetime"],
        "end_datetime": data.get("end_datetime"),
        "banner_url": data.get("banner_url") or data.get("mobile_banner_url"),
        "city": data.get("city"),
        "public_location_label": data.get("public_location_label"),
        "featured": bool(data.get("featured")),
        "host_display_name": data.get("host_display_name"),
        "host_id": data.get("host_id"),
        "category_name": (
            event.category.name if event.category is not None else None
        ),
        "category_slug": (
            event.category.slug if event.category is not None else None
        ),
        "min_price": float(min_price) if min_price is not None else None,
        "is_free": min_price is not None and min_price == 0,
    }


def list_calendar_month(
    db: Session,
    *,
    month: str,
    category_slug: str | None = None,
    city_slug: str | None = None,
    location_kind: str | None = None,
    location_slug: str | None = None,
    paid: str | None = None,
    host_id: UUID | None = None,
    include_featured: bool = True,
    max_per_day: int = 8,
) -> dict:
    """
    Group published upcoming-or-in-month events by local calendar date (YYYY-MM-DD).

    Uses the same discovery filters as the public list where applicable.
    Events are keyed by ``start_datetime.date()`` in the event's stored timezone date
    (date component of start_datetime).
    """
    year, mon = parse_month(month)
    month_start, month_end = month_bounds(year, mon)
    label = f"{year:04d}-{mon:02d}"

    rows = list_published_events(
        db,
        category_slug=category_slug,
        city_slug=city_slug,
        location_kind=location_kind,
        location_slug=location_slug,
        paid=paid,
        sort="soonest",
    )

    # Include events that start in this month (even if list_published filters "upcoming"
    # by end_datetime — still fine for current/future months).
    by_day: dict[str, list[Event]] = defaultdict(list)
    featured_pick: Event | None = None

    for event in rows:
        start = event.start_datetime
        if start is None:
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if start < month_start - timedelta(days=1) or start > month_end + timedelta(
            days=1
        ):
            # Soft window; precise day filter below
            pass
        day_key = start.date().isoformat()
        try:
            d = date.fromisoformat(day_key)
        except ValueError:
            continue
        if d.year != year or d.month != mon:
            continue
        if host_id is not None and event.host_id != host_id:
            continue
        by_day[day_key].append(event)
        if include_featured and featured_pick is None and event.featured:
            featured_pick = event

    days_out: list[dict] = []
    for day_key in sorted(by_day.keys()):
        day_events = by_day[day_key]
        day_events.sort(
            key=lambda e: (
                not bool(e.featured),
                e.start_datetime or month_start,
            )
        )
        compact = [
            compact_calendar_event(e) for e in day_events[: max(1, max_per_day)]
        ]
        days_out.append(
            {
                "date": day_key,
                "event_count": len(day_events),
                "events": compact,
            }
        )

    featured_payload = None
    if include_featured:
        pick = featured_pick
        if pick is None:
            # Nearest upcoming in month
            flat = [e for evs in by_day.values() for e in evs]
            flat.sort(key=lambda e: e.start_datetime or month_end)
            pick = flat[0] if flat else None
        if pick is not None:
            featured_payload = compact_calendar_event(pick)

    return {
        "month": label,
        "days": days_out,
        "featured_event": featured_payload,
        "total_events": sum(d["event_count"] for d in days_out),
    }
