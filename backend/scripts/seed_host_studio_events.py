"""Seed 10 Event Studio showcase events for a specific host user.

Usage (from backend/):
  python -m scripts.seed_host_studio_events --email bankoleabiodun366@gmail.com
  python -m scripts.seed_host_studio_events --email bankoleabiodun366@gmail.com --replace
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import models as auth_models  # noqa: F401
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.demo import assets
from app.demo.guards import DemoEnvironmentError, assert_demo_ops_allowed
from app.events import models as event_models  # noqa: F401
from app.events.models import (
    Event,
    EventAgendaItem,
    EventCategory,
    EventCheckoutQuestion,
    EventMedia,
    EventPerson,
    EventVenue,
    TicketType,
)
from app.events.seed import seed_event_categories
from app.hosts import models as host_models  # noqa: F401
from app.hosts.models import Host, HostProfile, HostVerification
from app.hosts.service import get_host_by_user_id, unique_host_slug
from app.users import models as user_models  # noqa: F401
from app.users.models import User
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_role_by_name, get_user_by_email

SLUG_PREFIX = "studio-ui-"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "event"


def _ensure_host(db: Session, user: User) -> Host:
    host = get_host_by_user_id(db, user.id)
    if host is not None:
        return host

    host_role = get_role_by_name(db, "host")
    if host_role is None:
        raise RuntimeError("Host role is not seeded. Run migrations/seed roles first.")
    if host_role not in user.roles:
        user.roles.append(host_role)

    display = (user.full_name or user.email.split("@")[0]).strip() or "Studio Host"
    host = Host(
        user_id=user.id,
        display_name=display,
        slug=unique_host_slug(db, display),
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(
        HostProfile(
            host_id=host.id,
            bio="Event Studio UI test host",
            city="Lagos",
            state="Lagos",
            country="Nigeria",
        )
    )
    db.add(HostVerification(host_id=host.id, status="verified"))
    db.commit()
    refreshed = get_host_by_user_id(db, user.id)
    if refreshed is None:
        raise RuntimeError("Failed to create host profile")
    return refreshed


def _categories(db: Session) -> dict[str, EventCategory]:
    seed_event_categories(db)
    rows = list(db.scalars(select(EventCategory).where(EventCategory.is_active.is_(True))))
    return {c.slug: c for c in rows}


def _event_blueprints(now: datetime) -> list[dict[str, Any]]:
    """Ten events covering Event Studio selection surfaces."""
    return [
        {
            "key": "public-full",
            "title": "Studio Public Night — Full Address",
            "status": "published",
            "event_type": "public",
            "visibility": "listed",
            "location_visibility": "full_public",
            "reveal_timing": "immediately",
            "category": "music",
            "vibe": "Afrobeats rooftop",
            "banner_key": "afrobeats-night-live",
            "start": now + timedelta(days=8, hours=19),
            "tickets": [
                {"name": "Regular", "type": "regular", "price": "7000", "qty": 200},
                {"name": "VIP", "type": "vip", "price": "25000", "qty": 40},
            ],
            "enrich": True,
        },
        {
            "key": "private-hidden-pay",
            "title": "Studio Private — Hidden Until Payment",
            "status": "published",
            "event_type": "private",
            "visibility": "unlisted",
            "location_visibility": "hidden_until_payment",
            "reveal_timing": "after_payment",
            "public_location_label": "Lekki Phase 1, Lagos — exact venue revealed after purchase.",
            "reveal_note": "Exact venue revealed after purchase.",
            "category": "nightlife",
            "vibe": "Members only",
            "banner_key": "detty-friday-live",
            "start": now + timedelta(days=10, hours=20),
            "tickets": [
                {"name": "Guest List", "type": "invite_only", "price": "15000", "qty": 80},
                {"name": "Hidden Drop", "type": "hidden", "price": "12000", "qty": 20},
            ],
            "enrich": True,
        },
        {
            "key": "invite-area",
            "title": "Studio Invite Only — Area Label",
            "status": "published",
            "event_type": "invite_only",
            "visibility": "approval_required",
            "location_visibility": "area_only",
            "reveal_timing": "manual_approval",
            "public_location_label": "Victoria Island, Lagos",
            "category": "comedy",
            "vibe": "Intimate comedy",
            "banner_key": "lagos-comedy-jam",
            "start": now + timedelta(days=12, hours=18),
            "tickets": [
                {"name": "Early Bird", "type": "early_bird", "price": "3500", "qty": 100},
                {"name": "Regular", "type": "regular", "price": "5000", "qty": 150},
            ],
            "enrich": True,
        },
        {
            "key": "secret-manual",
            "title": "Studio Secret Location Night",
            "status": "published",
            "event_type": "secret_location",
            "visibility": "password_protected",
            "location_visibility": "hidden_until_manual_approval",
            "reveal_timing": "manual_approval",
            "public_location_label": "Secret location — full details sent to approved attendees.",
            "reveal_note": "Full details sent to approved attendees.",
            "category": "lifestyle",
            "vibe": "Whisper network",
            "banner_key": "draft-secret-session",
            "start": now + timedelta(days=14, hours=21),
            "tickets": [
                {"name": "Approved Entry", "type": "invite_only", "price": "20000", "qty": 60},
                {"name": "Backstage Pass", "type": "backstage_pass", "price": "45000", "qty": 15},
            ],
            "enrich": True,
        },
        {
            "key": "online-only",
            "title": "Studio Online Summit",
            "status": "published",
            "event_type": "online",
            "visibility": "listed",
            "location_visibility": "online_only",
            "reveal_timing": "after_payment",
            "online_event_url": "https://meet.padeya.demo/studio-online",
            "online_url_reveal_rule": "after_payment",
            "public_location_label": "Online event — link revealed after payment.",
            "category": "tech",
            "vibe": "Founder energy",
            "banner_key": "product-builders-meetup",
            "start": now + timedelta(days=9, hours=16),
            "tickets": [
                {"name": "Free RSVP", "type": "free_rsvp", "price": "0", "qty": 300},
                {"name": "Supporter", "type": "donation", "price": "5000", "qty": 100},
            ],
            "enrich": True,
        },
        {
            "key": "hybrid-24h",
            "title": "Studio Hybrid — Reveal 24h Before",
            "status": "published",
            "event_type": "hybrid",
            "visibility": "listed",
            "location_visibility": "hidden_until_24h_before",
            "reveal_timing": "twenty_four_hours_before",
            "online_event_url": "https://meet.padeya.demo/studio-hybrid",
            "online_url_reveal_rule": "twenty_four_hours_before",
            "public_location_label": "Lagos hub + livestream — venue 24h before.",
            "category": "business",
            "vibe": "Hybrid networking",
            "banner_key": "founders-mixer-lagos",
            "start": now + timedelta(days=16, hours=17),
            "tickets": [
                {"name": "In-Person", "type": "regular", "price": "10000", "qty": 120},
                {"name": "Virtual", "type": "regular", "price": "2500", "qty": 400},
                {
                    "name": "Founders Table",
                    "type": "table",
                    "price": "250000",
                    "qty": 8,
                    "seats": 5,
                },
            ],
            "enrich": True,
        },
        {
            "key": "draft-rich",
            "title": "Studio Draft — Rich Ticket Mix",
            "status": "draft",
            "event_type": "public",
            "visibility": "listed",
            "location_visibility": "full_public",
            "reveal_timing": "immediately",
            "category": "food-drink",
            "vibe": "Tasting night",
            "banner_key": "food-and-flow",
            "start": now + timedelta(days=20, hours=18),
            "tickets": [
                {"name": "Group of 4", "type": "group", "price": "20000", "qty": 40, "seats": 4},
                {"name": "VVIP Lounge", "type": "vvip", "price": "90000", "qty": 20},
                {"name": "Custom Chef Table", "type": "chef_table", "price": "120000", "qty": 10},
            ],
            "enrich": True,
        },
        {
            "key": "pending-review",
            "title": "Studio Pending Review Showcase",
            "status": "pending_review",
            "event_type": "public",
            "visibility": "listed",
            "location_visibility": "area_only",
            "reveal_timing": "after_payment",
            "public_location_label": "Yaba, Lagos",
            "category": "gospel",
            "vibe": "Worship night",
            "banner_key": "praise-experience-live",
            "start": now + timedelta(days=22, hours=18),
            "tickets": [
                {"name": "General", "type": "regular", "price": "0", "qty": 500},
                {"name": "Reserved Seat", "type": "vip", "price": "5000", "qty": 80},
            ],
            "enrich": True,
        },
        {
            "key": "paused-policies",
            "title": "Studio Paused — Policies & Safety",
            "status": "paused",
            "event_type": "public",
            "visibility": "listed",
            "location_visibility": "full_public",
            "reveal_timing": "immediately",
            "category": "sports",
            "vibe": "Watch party",
            "banner_key": "sports-sunday",
            "start": now + timedelta(days=25, hours=15),
            "refund_policy_type": "refund_until_24_hours_before",
            "tickets": [
                {"name": "Fan Zone", "type": "regular", "price": "3000", "qty": 300},
                {"name": "Free Kids Entry", "type": "free", "price": "0", "qty": 50},
            ],
            "enrich": True,
        },
        {
            "key": "rejected-seo",
            "title": "Studio Rejected — SEO & Discovery",
            "status": "rejected",
            "event_type": "private",
            "visibility": "unlisted",
            "location_visibility": "hidden_until_payment",
            "reveal_timing": "after_payment",
            "public_location_label": "Ikeja, Lagos — exact venue after purchase.",
            "category": "arts-culture",
            "vibe": "Gallery walk",
            "banner_key": "art-walk-lagos",
            "start": now + timedelta(days=28, hours=16),
            "rejection_reason": "Incomplete safety plan for demo UI testing.",
            "tickets": [
                {"name": "Walk Pass", "type": "regular", "price": "4000", "qty": 150},
            ],
            "enrich": True,
        },
    ]


def _upsert_event(
    db: Session,
    *,
    host: Host,
    categories: dict[str, EventCategory],
    spec: dict[str, Any],
) -> Event:
    slug = f"{SLUG_PREFIX}{spec['key']}"
    event = db.scalar(
        select(Event)
        .where(Event.slug == slug)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.agenda_items),
            selectinload(Event.people),
            selectinload(Event.checkout_questions),
            selectinload(Event.media),
            selectinload(Event.venue),
        )
    )
    cat = categories.get(spec["category"])
    start: datetime = spec["start"]
    end = start + timedelta(hours=4)
    banner = assets.event_banner(spec["banner_key"])
    description = (
        f"{spec['title']} is an Event Studio UI showcase listing for {host.display_name}. "
        "Use it to verify steppers, privacy, tickets, agenda, lineup, policies, and publish states."
    )
    if event is None:
        event = Event(
            title=spec["title"],
            slug=slug,
            description=description,
            host_id=host.id,
            status=spec["status"],
            start_datetime=start,
            end_datetime=end,
            doors_open_datetime=start - timedelta(minutes=45),
            timezone="Africa/Lagos",
            category_id=cat.id if cat else None,
            event_type=spec["event_type"],
            visibility=spec["visibility"],
            location_visibility=spec["location_visibility"],
            banner_url=banner,
        )
        db.add(event)
        db.flush()

    event.title = spec["title"]
    event.short_tagline = f"{spec['title'].split('—')[0].strip()} · Studio UI kit"
    event.description = description
    event.vibe = spec.get("vibe")
    event.event_type = spec["event_type"]
    event.visibility = spec["visibility"]
    event.category_id = cat.id if cat else None
    event.start_datetime = start
    event.end_datetime = end
    event.doors_open_datetime = start - timedelta(minutes=45)
    event.timezone = "Africa/Lagos"
    event.venue_name = f"{spec['title']} Venue"
    event.address = "14 Admiralty Way"
    event.city = "Lagos"
    event.state = "Lagos"
    event.public_location_label = spec.get("public_location_label")
    event.location_visibility = spec["location_visibility"]
    event.reveal_timing = spec.get("reveal_timing") or "immediately"
    event.reveal_note = spec.get("reveal_note")
    event.online_event_url = spec.get("online_event_url")
    event.online_url_reveal_rule = spec.get("online_url_reveal_rule") or "after_payment"
    event.banner_url = banner
    event.mobile_banner_url = banner
    event.social_share_image_url = banner
    event.capacity = 400
    event.refund_policy_type = spec.get("refund_policy_type") or "admin_controlled"
    event.refund_policy = event.refund_policy_type
    event.refund_policy_text = "Demo refund policy for Event Studio testing."
    event.cancellation_policy = "Host may pause or cancel; buyers are notified in-app."
    event.age_restriction = "18+"
    event.id_required = True
    event.safety_notice = "Follow steward instructions. No re-entry after midnight on demo nights."
    event.terms_acknowledgement = "I agree to Pàdéyá and host house rules."
    event.door_sales_allowed = True
    event.re_entry_allowed = False
    event.check_in_start_time = start - timedelta(hours=1)
    event.check_in_end_time = end
    event.dress_code = "Smart casual"
    event.accessibility_notes = "Ground-floor access available for this showcase listing."
    event.parking_info = "Paid parking nearby — arrive early."
    event.what_to_expect = "Scan your Pàdéyá ticket, settle in, enjoy the program."
    event.what_to_bring = "Valid ID and your ticket QR."
    event.prohibited_items = "No outside drinks or professional cameras without clearance."
    event.entry_requirements = "Ticket + matching ID for VIP/VVIP tiers."
    event.status = spec["status"]
    event.featured = spec["key"] in {"public-full", "online-only"}
    event.seo_title = f"{spec['title']} | Pàdéyá"
    event.seo_description = f"Event Studio showcase — {spec['title']} on Pàdéyá."
    event.social_share_title = spec["title"]
    event.social_share_description = "Preview privacy, tickets, and publish states."
    event.hashtags = ["Padeya", "EventStudio", "Lagos"]
    event.discoverable_keywords = [spec["category"], spec["event_type"], "studio-ui"]
    event.rejection_reason = spec.get("rejection_reason")
    event.published_at = (
        now_utc()
        if spec["status"] in {"published", "paused", "cancelled", "completed"}
        else None
    )

    if event.venue is None:
        event.venue = EventVenue(
            event_id=event.id,
            name=event.venue_name or "Venue",
            address=event.address,
            city=event.city,
            state=event.state,
            country="Nigeria",
        )
    else:
        event.venue.name = event.venue_name or "Venue"
        event.venue.address = event.address
        event.venue.city = event.city
        event.venue.state = event.state

    if not event.media:
        db.add(
            EventMedia(
                event_id=event.id, url=banner, media_type="banner", sort_order=0
            )
        )
        db.add(
            EventMedia(
                event_id=event.id,
                url=assets.event_gallery(spec["banner_key"]),
                media_type="gallery",
                sort_order=1,
            )
        )

    if not event.ticket_types:
        for tt in spec.get("tickets") or []:
            db.add(
                TicketType(
                    event_id=event.id,
                    name=tt["name"],
                    type=tt["type"],
                    description=f"{tt['name']} showcase tier",
                    price=Decimal(tt["price"]),
                    quantity=int(tt["qty"]),
                    seats_per_unit=int(tt.get("seats") or 1),
                    min_per_order=1,
                    max_per_order=4 if tt["type"] == "table" else 10,
                    visibility="hidden" if tt["type"] == "hidden" else "public",
                    benefits="Studio UI demo benefits",
                    transfer_allowed=True,
                    refund_allowed=False,
                    waitlist_enabled=tt["type"] in {"vip", "vvip"},
                    table_perks="Bottle service demo" if tt["type"] == "table" else None,
                    reservation_hold_minutes=15 if tt["type"] == "table" else None,
                    status="active",
                )
            )

    if spec.get("enrich") and not event.agenda_items:
        db.add(
            EventAgendaItem(
                event_id=event.id,
                title="Doors Open",
                type="doors_open",
                start_time=start - timedelta(minutes=45),
                end_time=start,
                sort_order=0,
            )
        )
        db.add(
            EventAgendaItem(
                event_id=event.id,
                title="Main Program",
                type="performance" if spec["category"] in {"music", "nightlife"} else "speaker",
                description="Headliner / keynote block for UI preview.",
                start_time=start + timedelta(minutes=30),
                end_time=start + timedelta(hours=2),
                sort_order=1,
            )
        )
        db.add(
            EventAgendaItem(
                event_id=event.id,
                title="Networking",
                type="networking",
                start_time=start + timedelta(hours=2),
                end_time=end,
                sort_order=2,
            )
        )
        db.add(
            EventPerson(
                event_id=event.id,
                name="Studio Headliner",
                role="Performer" if spec["category"] in {"music", "nightlife"} else "Speaker",
                bio="Showcase artist/speaker for Event Studio lineup UI.",
                image_url=assets.host_avatar("djmaze"),
                social_url="https://instagram.com/padeya",
                performance_time=start + timedelta(hours=1),
                sort_order=0,
            )
        )
        db.add(
            EventPerson(
                event_id=event.id,
                name="Host MC",
                role="Host",
                bio="Keeps the night moving.",
                sort_order=1,
            )
        )
        db.add(
            EventCheckoutQuestion(
                event_id=event.id,
                label="WhatsApp number for venue updates",
                type="phone",
                required=True,
                sort_order=0,
            )
        )
        db.add(
            EventCheckoutQuestion(
                event_id=event.id,
                label="Dietary preference",
                type="dropdown",
                required=False,
                options=["None", "Vegetarian", "Halal", "Other"],
                sort_order=1,
            )
        )

    db.flush()
    return event


def now_utc() -> datetime:
    return datetime.now(UTC)


def seed_host_studio_events(
    db: Session,
    *,
    email: str,
    replace: bool = False,
) -> dict[str, Any]:
    assert_demo_ops_allowed(operation="demo seed")
    seed_roles_and_permissions(db)

    user = get_user_by_email(db, email.strip().lower())
    if user is None:
        raise RuntimeError(
            f"User {email} not found. Register/login once in the app, then re-run."
        )

    host = _ensure_host(db, user)
    categories = _categories(db)

    if replace:
        existing = list(
            db.scalars(
                select(Event).where(
                    Event.host_id == host.id,
                    Event.slug.startswith(SLUG_PREFIX),
                )
            )
        )
        for event in existing:
            db.delete(event)
        db.commit()

    created = 0
    updated = 0
    slugs: list[str] = []
    for spec in _event_blueprints(now_utc()):
        before = db.scalar(select(Event.id).where(Event.slug == f"{SLUG_PREFIX}{spec['key']}"))
        event = _upsert_event(db, host=host, categories=categories, spec=spec)
        slugs.append(event.slug)
        if before is None:
            created += 1
        else:
            updated += 1
    db.commit()

    return {
        "email": email,
        "host_id": str(host.id),
        "host_slug": host.slug,
        "created": created,
        "updated": updated,
        "events": len(slugs),
        "slugs": slugs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Event Studio UI events for a host")
    parser.add_argument(
        "--email",
        default="bankoleabiodun366@gmail.com",
        help="Host user email",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help=f"Delete existing {SLUG_PREFIX}* events for this host before reseeding",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.is_production:
        print("ERROR: Refusing to seed in production.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = seed_host_studio_events(db, email=args.email, replace=args.replace)
    except (DemoEnvironmentError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Studio UI event seed result:")
    for key, value in result.items():
        if key == "slugs":
            print("  slugs:")
            for slug in value:
                print(f"    - {slug}")
        else:
            print(f"  {key}: {value}")
    print("Open /host/events while logged in as that user to review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
