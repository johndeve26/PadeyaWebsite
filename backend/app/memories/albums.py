"""Public memory album discovery listings."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, exists, func, select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.hosts.models import Host
from app.memories.constants import SEO_MIN_ACTIVE_PHOTOS
from app.memories.models import EventMemory, EventMemoryMedia


def _photo_counts(db: Session, memory_id: UUID) -> dict[str, int]:
    rows = db.execute(
        select(
            EventMemoryMedia.uploader_role,
            func.count(),
            func.count(func.distinct(EventMemoryMedia.uploader_user_id)),
        )
        .where(
            EventMemoryMedia.memory_id == memory_id,
            EventMemoryMedia.status == "active",
        )
        .group_by(EventMemoryMedia.uploader_role)
    ).all()

    host_count = 0
    community_count = 0
    contributor_ids = 0
    for role, count, distinct_uploaders in rows:
        if role == "host":
            host_count = int(count)
        elif role == "fan":
            community_count = int(count)
            contributor_ids = int(distinct_uploaders or 0)
    return {
        "memory_count": host_count + community_count,
        "host_memory_count": host_count,
        "community_memory_count": community_count,
        "contributor_count": contributor_ids,
    }


def memory_counts(db: Session, memory_id: UUID) -> dict[str, int]:
    return _photo_counts(db, memory_id)


def cover_for_memory(db: Session, memory_id: UUID) -> EventMemoryMedia | None:
    cover = db.scalar(
        select(EventMemoryMedia)
        .where(
            EventMemoryMedia.memory_id == memory_id,
            EventMemoryMedia.status == "active",
            EventMemoryMedia.is_cover.is_(True),
        )
        .limit(1)
    )
    if cover is not None:
        return cover
    return db.scalar(
        select(EventMemoryMedia)
        .where(
            EventMemoryMedia.memory_id == memory_id,
            EventMemoryMedia.status == "active",
        )
        .order_by(
            case((EventMemoryMedia.uploader_role == "host", 0), else_=1),
            EventMemoryMedia.sort_order.asc(),
            EventMemoryMedia.created_at.asc(),
        )
        .limit(1)
    )


def _has_active_photo():
    return exists(
        select(EventMemoryMedia.id).where(
            EventMemoryMedia.memory_id == EventMemory.id,
            EventMemoryMedia.status == "active",
        )
    )


def list_public_albums(
    db: Session,
    *,
    limit: int = 24,
    cursor: str | None = None,
    city: str | None = None,
) -> dict:
    """Paginated event albums that have at least one active photo."""
    lim = max(1, min(int(limit or 24), 48))
    stmt = (
        select(EventMemory, Event, Host)
        .join(Event, Event.id == EventMemory.event_id)
        .join(Host, Host.id == EventMemory.host_id)
        .where(
            EventMemory.status == "published",
            EventMemory.moderation_status != "removed",
            Event.status == "completed",
            Host.status == "active",
            _has_active_photo(),
        )
        .order_by(
            EventMemory.published_at.desc().nullslast(),
            EventMemory.created_at.desc(),
        )
    )
    if city and city.strip():
        stmt = stmt.where(func.lower(Event.city) == city.strip().lower())

    if cursor:
        try:
            published_s, memory_id_s = cursor.split("|", 1)
            published_at = datetime.fromisoformat(published_s)
            memory_uuid = UUID(memory_id_s)
            stmt = stmt.where(
                (EventMemory.published_at < published_at)
                | (
                    (EventMemory.published_at == published_at)
                    & (EventMemory.id < memory_uuid)
                )
            )
        except (ValueError, TypeError):
            pass

    rows = list(db.execute(stmt.limit(lim + 1)).all())
    has_more = len(rows) > lim
    rows = rows[:lim]

    items: list[dict] = []
    for memory, event, host in rows:
        counts = _photo_counts(db, memory.id)
        if counts["memory_count"] < 1:
            continue
        cover = cover_for_memory(db, memory.id)
        items.append(
            {
                "event_id": event.id,
                "event_slug": event.slug,
                "event_title": event.title,
                "start_datetime": event.start_datetime,
                "end_datetime": event.end_datetime,
                "city": event.city,
                "host_display_name": host.display_name,
                "host_username": host.slug,
                "cover_url": cover.url if cover else event.banner_url,
                "cover_thumbnail_url": (
                    (cover.thumbnail_url or cover.url) if cover else event.banner_url
                ),
                "counts": counts,
                "memories_path": f"/events/{event.slug}/memories",
                "share_path": f"/@{host.slug}/memories/{event.slug}",
            }
        )

    next_cursor = None
    if has_more and rows:
        last_memory = rows[-1][0]
        stamp = last_memory.published_at or last_memory.created_at
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        next_cursor = f"{stamp.isoformat()}|{last_memory.id}"

    return {"items": items, "next_cursor": next_cursor}


def album_is_seo_indexable(db: Session, memory: EventMemory, event: Event) -> bool:
    if event.status != "completed":
        return False
    if (event.visibility or "listed") != "listed":
        return False
    if memory.status != "published" or memory.moderation_status == "removed":
        return False
    counts = _photo_counts(db, memory.id)
    return counts["memory_count"] >= SEO_MIN_ACTIVE_PHOTOS
