"""Idempotent Event Memories demo seed (photo albums).

Uses existing frontend/public/demo SVG assets and real ticket relationships.
Never runs unless invoked via demo seed CLI (guards in seed_demo_data).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo import assets
from app.demo.constants import DEMO_EMAIL_DOMAIN
from app.events.models import Event
from app.hosts.models import Host
from app.memories.models import EventMemory, EventMemoryMedia
from app.memories.service import ensure_event_memory, invalidate_memory_caches
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PRIVATE, VISIBILITY_PUBLIC
from app.users.models import User
from app.users.service import get_user_by_email

# Stable storage_key prefix — reruns upsert by key, never duplicate.
_KEY_PREFIX = "demo-mem"


def _sk(event_key: str, role: str, idx: int) -> str:
    return f"{_KEY_PREFIX}:{event_key}:{role}:{idx:02d}"


def _now() -> datetime:
    return datetime.now(UTC)


def _upsert_photo(
    db: Session,
    *,
    memory: EventMemory,
    storage_key: str,
    url: str,
    uploader_user_id,
    uploader_role: str,
    caption: str | None,
    sort_order: int,
    is_cover: bool = False,
    status: str = "active",
) -> EventMemoryMedia:
    row = db.scalar(
        select(EventMemoryMedia).where(EventMemoryMedia.storage_key == storage_key)
    )
    if row is None:
        row = EventMemoryMedia(
            memory_id=memory.id,
            storage_key=storage_key,
            media_type="image",
            url=url,
            thumbnail_url=url,
            uploader_user_id=uploader_user_id,
            uploader_role=uploader_role,
            caption=caption,
            label=caption,
            sort_order=sort_order,
            is_cover=is_cover,
            status=status,
            mime_type="image/svg+xml",
        )
        db.add(row)
        db.flush()
    else:
        row.memory_id = memory.id
        row.url = url
        row.thumbnail_url = url
        row.uploader_user_id = uploader_user_id
        row.uploader_role = uploader_role
        row.caption = caption
        row.label = caption
        row.sort_order = sort_order
        row.is_cover = is_cover
        row.status = status
        row.media_type = "image"
        row.mime_type = "image/svg+xml"
    return row


def _clear_other_covers(db: Session, memory_id, keep_key: str) -> None:
    rows = db.scalars(
        select(EventMemoryMedia).where(
            EventMemoryMedia.memory_id == memory_id,
            EventMemoryMedia.is_cover.is_(True),
        )
    ).all()
    for row in rows:
        if row.storage_key != keep_key:
            row.is_cover = False


def _remove_legacy_unkeyed_demo_media(db: Session, memory: EventMemory) -> None:
    """Drop pre-v2 single gallery rows that lack demo-mem storage keys."""
    rows = list(
        db.scalars(
            select(EventMemoryMedia).where(EventMemoryMedia.memory_id == memory.id)
        ).all()
    )
    for row in rows:
        key = row.storage_key or ""
        if key.startswith(_KEY_PREFIX):
            continue
        # Only remove obvious legacy demo URLs / empty keys from old seed.
        url = row.url or ""
        if "/demo/" in url or not key:
            db.delete(row)


def _host_user_for_event(db: Session, event: Event) -> User | None:
    host = db.get(Host, event.host_id)
    if host is None:
        return None
    return db.get(User, host.user_id)


def _ensure_ticket(db: Session, buyer: User, event: Event) -> bool:
    """Ensure a real eligible ticket for memory uploads (works on completed events).

    Normal checkout rejects completed events ("not available for purchase").
    Memories showcase needs historical paid tickets, so we insert a paid demo
    order + active ticket that still satisfies `user_holds_event_memory_ticket`.
    """
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy.orm import selectinload

    from app.events.models import TicketType
    from app.memories.eligibility import user_holds_event_memory_ticket
    from app.payments.models import Order, OrderItem
    from app.tickets.models import Ticket
    from app.tickets.qr import new_public_ticket_code

    if user_holds_event_memory_ticket(db, event_id=event.id, user_id=buyer.id):
        return True

    event = db.scalar(
        select(Event)
        .where(Event.id == event.id)
        .options(selectinload(Event.ticket_types))
    )
    if event is None:
        return False

    publics = [
        t
        for t in event.ticket_types
        if t.visibility == "public" and t.status in {"active", "sold_out"}
    ]
    if not publics:
        # Fall back to any ticket type on the event (completed demo albums).
        publics = list(event.ticket_types or [])
    if not publics:
        return False
    tt: TicketType = publics[0]
    price = Decimal(str(tt.price or "0"))
    ref = f"PDY-MEM-{uuid4().hex[:10].upper()}"
    order = Order(
        reference=ref,
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency=getattr(tt, "currency", None) or "NGN",
        subtotal_amount=price,
        discount_amount=Decimal("0"),
        total_amount=price,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or buyer.email.split("@")[0],
        paid_at=_now(),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=price,
        line_total=price,
        ticket_type_name=tt.name,
    )
    db.add(item)
    db.flush()
    ticket = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_user_id=buyer.id,
        status="active",
        ticket_type_name=tt.name,
        holder_name=buyer.full_name or buyer.email.split("@")[0],
        holder_email=buyer.email,
    )
    db.add(ticket)
    db.flush()
    return user_holds_event_memory_ticket(db, event_id=event.id, user_id=buyer.id)


def _refresh_event(db: Session, event_id) -> Event | None:
    return db.get(Event, event_id)


def _food_and_flow_host_specs() -> list[dict[str, Any]]:
    captions = [
        "Doors open at Food & Flow.",
        "Mainland energy all night.",
        "Food, music and good people.",
        "The crowd came ready.",
        "A moment from the main stage.",
        "Good food. Better company.",
        "One for the books.",
        "Until the next Food & Flow.",
        "Night lights over the fest floor.",
    ]
    urls = [
        assets.memory_image("mainland-2025-memory"),
        assets.event_banner("food-and-flow"),
        assets.event_gallery("food-and-flow"),
        assets.vault_cover("bts-mainland"),
        assets.host_cover("mainlandvibes"),
        assets.event_banner("mainland-vibes-summer"),
        assets.event_gallery("mainland-vibes-summer"),
        assets.event_banner("mainland-vibes-2025"),
        assets.event_gallery("mainland-vibes-2025"),
    ]
    specs = []
    for i, (caption, url) in enumerate(zip(captions, urls, strict=True)):
        specs.append(
            {
                "idx": i,
                "caption": caption,
                "url": url,
                "is_cover": i == 0,
            }
        )
    return specs


def _seed_food_and_flow(
    db: Session,
    *,
    event: Event,
    users: dict[str, User],
) -> dict[str, int]:
    host_user = _host_user_for_event(db, event)
    if host_user is None:
        return {"host": 0, "community": 0, "contributors": 0, "total": 0}

    event_id = event.id
    event.status = "completed"
    db.flush()

    # Organic fan distribution: 4, 3, 5, 2 (and one private-passport contributor)
    fan_plans: list[tuple[str, list[str], list[str]]] = [
        (
            f"fan3@{DEMO_EMAIL_DOMAIN}",
            [
                "The jollof line was worth it.",
                "Caught this from the back — still fire.",
                "Met so many good people tonight.",
                "Mainland forever.",
            ],
            [
                assets.event_gallery("food-and-flow"),
                assets.vault_cover("bts-mainland"),
                assets.event_banner("food-and-flow"),
                assets.memory_image("mainland-2025-memory"),
            ],
        ),
        (
            f"fan6@{DEMO_EMAIL_DOMAIN}",  # miralagos — keep private attribution
            [
                "Quiet corner, loud vibes.",
                "Saved this for the memories.",
                "Already planning the next one.",
            ],
            [
                assets.host_cover("mainlandvibes"),
                assets.event_banner("mainland-vibes-summer"),
                assets.event_gallery("mainland-vibes-2025"),
            ],
        ),
        (
            f"fan1@{DEMO_EMAIL_DOMAIN}",
            [
                "Doors to dancefloor in one shot.",
                "Food & Flow did not miss.",
                "Crowd was locked in.",
                "Stage lights hit different.",
                "Last song energy.",
            ],
            [
                assets.event_banner("detty-friday-live"),
                assets.event_gallery("detty-friday-live"),
                assets.memory_image("detty-friday-memory"),
                assets.event_banner("afrobeats-night-live"),
                assets.event_gallery("afrobeats-night-live"),
            ],
        ),
        (
            f"fan5@{DEMO_EMAIL_DOMAIN}",
            [
                "VIP rail view.",
                "One for the group chat.",
            ],
            [
                assets.vault_cover("vip-gallery"),
                assets.event_gallery("mainland-vibes-summer"),
            ],
        ),
    ]

    # Tickets first — before EventMemory writes — so _safe_call rollbacks
    # cannot drop the album row mid-seed.
    eligible_fans: list[tuple[User, list[str], list[str]]] = []
    for email, captions, urls in fan_plans:
        fan = users.get(email) or get_user_by_email(db, email)
        event = _refresh_event(db, event_id)
        if fan is None or event is None:
            continue
        if not _ensure_ticket(db, fan, event):
            continue
        eligible_fans.append((fan, captions, urls))

    event = _refresh_event(db, event_id)
    host_user = _host_user_for_event(db, event) if event else None
    if event is None or host_user is None:
        return {"host": 0, "community": 0, "contributors": 0, "total": 0}

    event.status = "completed"
    memory = ensure_event_memory(db, event)
    memory.host_recap_note = (
        "Thank you for joining Mainland Food & Culture Fest on Pàdéyá. "
        "Food, music, and mainland energy — see you at the next Food & Flow."
    )
    memory.status = "published"
    memory.moderation_status = "none"
    memory.external_gallery_url = None
    memory.external_gallery_label = None
    if memory.published_at is None:
        memory.published_at = _now()

    _remove_legacy_unkeyed_demo_media(db, memory)
    db.flush()

    cover_key = _sk("food-and-flow", "host", 0)
    for spec in _food_and_flow_host_specs():
        _upsert_photo(
            db,
            memory=memory,
            storage_key=_sk("food-and-flow", "host", spec["idx"]),
            url=spec["url"],
            uploader_user_id=host_user.id,
            uploader_role="host",
            caption=spec["caption"],
            sort_order=spec["idx"],
            is_cover=spec["is_cover"],
        )
    _clear_other_covers(db, memory.id, cover_key)

    community = 0
    contributors = 0
    for fan, captions, urls in eligible_fans:
        contributors += 1
        email_local = (fan.email or "fan").split("@")[0]
        for i, (caption, url) in enumerate(zip(captions, urls, strict=True)):
            _upsert_photo(
                db,
                memory=memory,
                storage_key=_sk("food-and-flow", f"fan-{email_local}", i),
                url=url,
                uploader_user_id=fan.id,
                uploader_role="fan",
                caption=caption,
                sort_order=100 + community,
                is_cover=False,
            )
            community += 1

    # Ensure fan6 stays private for attribution fallback QA
    mira = users.get(f"fan6@{DEMO_EMAIL_DOMAIN}") or get_user_by_email(
        db, f"fan6@{DEMO_EMAIL_DOMAIN}"
    )
    if mira is not None:
        passport = db.scalar(
            select(FanPassport).where(FanPassport.user_id == mira.id)
        )
        if passport is not None and passport.visibility == VISIBILITY_PUBLIC:
            # Demo intent: Mira is a privacy-sensitive contributor
            passport.visibility = VISIBILITY_PRIVATE

    # Fan8 has no Food & Flow ticket on purpose (ineligible upload QA)
    # Do not create a ticket here.

    host_n = len(_food_and_flow_host_specs())
    invalidate_memory_caches(event)
    return {
        "host": host_n,
        "community": community,
        "contributors": contributors,
        "total": host_n + community,
    }


def _seed_secondary_album(
    db: Session,
    *,
    event_key: str,
    event: Event,
    users: dict[str, User],
    host_captions: list[str],
    host_urls: list[str],
    fan_email: str,
    fan_captions: list[str],
    fan_urls: list[str],
    recap: str,
    hide_album: bool = False,
) -> dict[str, int]:
    host_user = _host_user_for_event(db, event)
    if host_user is None:
        return {"host": 0, "community": 0, "contributors": 0, "total": 0}

    event_id = event.id
    event.status = "completed"
    db.flush()

    fan = users.get(fan_email) or get_user_by_email(db, fan_email)
    fan_ok = False
    if fan is not None:
        event = _refresh_event(db, event_id)
        if event is not None:
            fan_ok = _ensure_ticket(db, fan, event)

    event = _refresh_event(db, event_id)
    host_user = _host_user_for_event(db, event) if event else None
    if event is None or host_user is None:
        return {"host": 0, "community": 0, "contributors": 0, "total": 0}

    event.status = "completed"
    memory = ensure_event_memory(db, event)
    memory.host_recap_note = recap
    memory.status = "hidden" if hide_album else "published"
    if hide_album:
        memory.moderation_status = "removed"
        memory.moderation_note = "Demo admin-hidden memory"
    else:
        memory.moderation_status = "none"
    if memory.published_at is None:
        memory.published_at = _now()

    _remove_legacy_unkeyed_demo_media(db, memory)
    db.flush()

    cover_key = _sk(event_key, "host", 0)
    for i, (caption, url) in enumerate(zip(host_captions, host_urls, strict=True)):
        _upsert_photo(
            db,
            memory=memory,
            storage_key=_sk(event_key, "host", i),
            url=url,
            uploader_user_id=host_user.id,
            uploader_role="host",
            caption=caption,
            sort_order=i,
            is_cover=i == 0,
        )
    _clear_other_covers(db, memory.id, cover_key)

    community = 0
    contributors = 0
    if fan is not None and fan_ok:
        contributors = 1
        for i, (caption, url) in enumerate(zip(fan_captions, fan_urls, strict=True)):
            _upsert_photo(
                db,
                memory=memory,
                storage_key=_sk(event_key, f"fan-{fan_email.split('@')[0]}", i),
                url=url,
                uploader_user_id=fan.id,
                uploader_role="fan",
                caption=caption,
                sort_order=50 + i,
                is_cover=False,
            )
            community += 1

    if not hide_album:
        invalidate_memory_caches(event)
    return {
        "host": len(host_captions),
        "community": community,
        "contributors": contributors,
        "total": len(host_captions) + community,
    }


def load_demo_users_and_events(db: Session) -> tuple[dict[str, User], dict[str, Event]]:
    """Load existing demo users/events for memories-only seeding."""
    from app.demo.constants import DEMO_EVENT_SLUG_PREFIX

    users: dict[str, User] = {}
    for row in db.scalars(
        select(User).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
    ).all():
        users[row.email] = row

    events: dict[str, Event] = {}
    for row in db.scalars(
        select(Event).where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
    ).all():
        key = row.slug.removeprefix(DEMO_EVENT_SLUG_PREFIX)
        events[key] = row
    return users, events


def verify_memories_integrity(db: Session) -> dict[str, Any]:
    """DB checks: limits, tickets, cover uniqueness, orphan refs, demo-key counts."""
    from collections import defaultdict

    from app.memories.constants import FAN_MEMORY_PHOTO_LIMIT, HOST_MEMORY_PHOTO_LIMIT
    from app.memories.eligibility import user_holds_event_memory_ticket

    issues: list[str] = []
    demo_rows = list(
        db.scalars(
            select(EventMemoryMedia).where(
                EventMemoryMedia.storage_key.like(f"{_KEY_PREFIX}:%")
            )
        ).all()
    )
    by_key = defaultdict(int)
    for row in demo_rows:
        by_key[row.storage_key] += 1
    dup_keys = [k for k, n in by_key.items() if n > 1]
    if dup_keys:
        issues.append(f"duplicate storage_keys: {dup_keys[:5]}")

    host_counts: dict[tuple, int] = defaultdict(int)
    fan_counts: dict[tuple, int] = defaultdict(int)
    covers: dict[Any, int] = defaultdict(int)
    for row in demo_rows:
        mem = db.get(EventMemory, row.memory_id)
        if mem is None:
            issues.append(f"orphan memory_id on {row.storage_key}")
            continue
        event = db.get(Event, mem.event_id)
        if event is None:
            issues.append(f"orphan event for {row.storage_key}")
            continue
        if row.uploader_user_id is None or db.get(User, row.uploader_user_id) is None:
            issues.append(f"orphan uploader on {row.storage_key}")
        if row.status != "active":
            continue
        if row.uploader_role == "host":
            host_counts[mem.event_id] += 1
        elif row.uploader_role == "fan":
            fan_counts[(mem.event_id, row.uploader_user_id)] += 1
            if row.uploader_user_id and not user_holds_event_memory_ticket(
                db, event_id=mem.event_id, user_id=row.uploader_user_id
            ):
                issues.append(f"fan memory without ticket: {row.storage_key}")
        if row.is_cover:
            covers[mem.id] += 1

    for event_id, n in host_counts.items():
        if n > HOST_MEMORY_PHOTO_LIMIT:
            issues.append(f"host over limit event={event_id} count={n}")
    for key, n in fan_counts.items():
        if n > FAN_MEMORY_PHOTO_LIMIT:
            issues.append(f"fan over limit {key} count={n}")
    for memory_id, n in covers.items():
        if n != 1:
            issues.append(f"cover count != 1 for memory={memory_id} covers={n}")

    food = db.scalar(
        select(Event).where(Event.slug == "demo-food-and-flow")
    )
    food_stats = {"host": 0, "community": 0, "covers": 0, "demo_keys": 0}
    if food is not None:
        mem = db.scalar(
            select(EventMemory).where(EventMemory.event_id == food.id)
        )
        if mem is not None:
            rows = list(
                db.scalars(
                    select(EventMemoryMedia).where(
                        EventMemoryMedia.memory_id == mem.id,
                        EventMemoryMedia.status == "active",
                    )
                ).all()
            )
            food_stats["host"] = sum(1 for r in rows if r.uploader_role == "host")
            food_stats["community"] = sum(1 for r in rows if r.uploader_role == "fan")
            food_stats["covers"] = sum(1 for r in rows if r.is_cover)
            food_stats["demo_keys"] = sum(
                1 for r in rows if (r.storage_key or "").startswith(_KEY_PREFIX)
            )

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "demo_media_rows": len(demo_rows),
        "unique_demo_keys": len(by_key),
        "food_and_flow": food_stats,
    }


def seed_memories_only(db: Session) -> dict[str, Any]:
    """Explicit memories-only seed (CLI). Requires existing demo events/users."""
    from app.demo.guards import assert_demo_ops_allowed

    assert_demo_ops_allowed(operation="demo memories seed")
    users, events = load_demo_users_and_events(db)
    if "food-and-flow" not in events:
        return {
            "status": "error",
            "message": "demo-food-and-flow missing — run full seed_demo_data first",
        }
    summary = seed_demo_memories(db, users=users, events=events)
    integrity = verify_memories_integrity(db)
    summary["integrity"] = integrity
    summary["status"] = "ok" if integrity.get("ok") else "integrity_failed"
    return summary


def seed_demo_memories(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> dict[str, Any]:
    """Seed rich photo albums for completed showcase events. Idempotent."""
    summary: dict[str, Any] = {"albums": {}}

    food = events.get("food-and-flow")
    if food is not None:
        summary["albums"]["food-and-flow"] = _seed_food_and_flow(
            db, event=food, users=users
        )

    detty = events.get("detty-friday-live")
    if detty is not None:
        summary["albums"]["detty-friday-live"] = _seed_secondary_album(
            db,
            event_key="detty-friday-live",
            event=detty,
            users=users,
            host_captions=[
                "Rooftop open.",
                "DJ Maze locked in.",
                "Friday never sleeps.",
                "Crowd from the rail.",
                "Skyline + bass.",
            ],
            host_urls=[
                assets.memory_image("detty-friday-memory"),
                assets.event_banner("detty-friday-live"),
                assets.event_gallery("detty-friday-live"),
                assets.host_cover("djmaze"),
                assets.event_banner("afrobeats-night-live"),
            ],
            fan_email=f"fan2@{DEMO_EMAIL_DOMAIN}",
            fan_captions=["View from upstairs.", "That drop though."],
            fan_urls=[
                assets.event_gallery("afrobeats-night-live"),
                assets.memory_image("detty-friday-memory"),
            ],
            recap="Detty Friday on the roof — thank you for dancing with us.",
        )

    comedy = events.get("island-comedy-night")
    if comedy is not None:
        summary["albums"]["island-comedy-night"] = _seed_secondary_album(
            db,
            event_key="island-comedy-night",
            event=comedy,
            users=users,
            host_captions=[
                "Sunday set warm-up.",
                "Room was packed.",
                "Mic check energy.",
                "Closing bit landed.",
            ],
            host_urls=[
                assets.memory_image("island-comedy-memory"),
                assets.event_banner("island-comedy-night"),
                assets.event_gallery("island-comedy-night"),
                assets.host_cover("lagoscomedyhub"),
            ],
            fan_email=f"fan4@{DEMO_EMAIL_DOMAIN}",
            fan_captions=["Could not stop laughing.", "Best seat in the room."],
            fan_urls=[
                assets.event_gallery("lagos-comedy-jam"),
                assets.event_banner("lagos-comedy-jam"),
            ],
            recap="Sunday Comedy Room — thank you for the laughs.",
        )

    worship = events.get("worship-under-stars")
    if worship is not None:
        summary["albums"]["worship-under-stars"] = _seed_secondary_album(
            db,
            event_key="worship-under-stars",
            event=worship,
            users=users,
            host_captions=[
                "Under the Ibadan sky.",
                "Voices lifted.",
                "Quiet before the set.",
            ],
            host_urls=[
                assets.event_banner("worship-under-stars"),
                assets.event_gallery("worship-under-stars"),
                assets.host_cover("praiseexperience"),
            ],
            fan_email=f"fan8@{DEMO_EMAIL_DOMAIN}",
            fan_captions=["Grateful for the night."],
            fan_urls=[assets.vault_cover("worship-rehearsal")],
            recap="Worship Night Ibadan — grateful for every voice.",
        )

    startup = events.get("startup-demo-evening")
    if startup is not None:
        summary["albums"]["startup-demo-evening"] = _seed_secondary_album(
            db,
            event_key="startup-demo-evening",
            event=startup,
            users=users,
            host_captions=["Demo night board.", "Builders in the room."],
            host_urls=[
                assets.event_banner("startup-demo-evening"),
                assets.event_gallery("startup-demo-evening"),
            ],
            fan_email=f"fan3@{DEMO_EMAIL_DOMAIN}",
            fan_captions=["Pitch notes."],
            fan_urls=[assets.vault_cover("founder-deck")],
            recap="Product Demo Night — see you at the next build.",
            hide_album=True,
        )

    db.commit()

    # Flatten summary totals for CLI print
    food_stats = summary["albums"].get("food-and-flow") or {}
    summary["food_and_flow"] = food_stats
    summary["status"] = "ok"
    return summary
