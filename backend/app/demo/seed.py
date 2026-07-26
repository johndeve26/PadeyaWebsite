"""Idempotent demo content seeder for local Pàdéyá development."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.checkins.models import EventStaffAssignment
from app.checkins.schemas import CheckInRequest, ManualOverrideRequest, StartSessionRequest
from app.checkins.service import check_in_ticket, override_check_in, start_scanner_session
from app.core.security import hash_password
from app.crm.models import HostAnnouncement, HostFollower
from app.crm.schemas import AnnouncementCreate, FollowRequest
from app.crm.service import (
    create_announcement,
    ensure_system_segments,
    follow_host,
    update_marketing_opt_in,
)
from app.demo import assets
from app.demo.analytics_seed import seed_event_analytics_traffic
from app.demo.constants import (
    DEMO_PERSONA_CONTEXT,
    AMBASSADORS,
    DEMO_ACCOUNTS,
    DEMO_CATEGORY_EXTRAS,
    DEMO_EMAIL_DOMAIN,
    DEMO_EVENT_SLUG_PREFIX,
    DEMO_FAN_PERSONAS,
    DEMO_HOSTS,
    DEMO_PASSWORD,
    DEMO_SHOWCASE_EVENTS,
    DEMO_TEAM_ACCOUNTS,
    EXTRA_HOST_ACCOUNTS,
    FAN_PERSONA_BY_EMAIL,
    PROMO_CODES,
    SHOWCASE_COMPLETED_KEYS,
    SHOWCASE_EVENT_KEYS,
    SHOWCASE_UPCOMING_KEYS,
)
from app.demo.guards import assert_demo_ops_allowed
from app.demo.models import DemoEntityMarker, DemoSupportCase
from app.demo.progress import log_seed_phase
from app.demo.sponsorship_seed import (
    create_demo_sponsorship_slot,
    ensure_demo_host_sponsorship_settings,
)
from app.demo.reset import reset_demo_data
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
from app.finance.ledger import get_or_create_host_balance
from app.finance.schemas import (
    BankDetails,
    PayoutMarkPaid,
    PayoutRequestCreate,
    PayoutReview,
    RefundRequestCreate,
    RefundReview,
)
from app.finance.service import (
    create_payout_request,
    create_refund_request,
    mark_payout_paid,
    review_payout_request,
    review_refund_request,
)
from app.hosts.models import Host, HostProfile, HostVerification
from app.legacy.models import (
    HostContactSettings,
    HostLegacyContentBlock,
    HostLegacyFeaturedItem,
    HostLegacyScore,
    HostLegacyScoreHistory,
    HostSocialLink,
    LegacyTier,
)
from app.legacy.seed import seed_legacy_tiers
from app.legacy.studio import ensure_default_blocks, ensure_legacy_page
from app.memories.models import EventMemory
from app.memories.models import EventMemoryMedia
from app.memories.service import ensure_event_memory
from app.passport.seed import seed_fan_badges
from app.passport.service import ensure_passport, refresh_loyalty_and_badges
from app.payments.models import Order, Payment
from app.payments.schemas import CheckoutAnswerIn, OrderCreate, OrderItemCreate
from app.payments.service import create_order, get_order_by_id, initialize_checkout
from app.payments.webhook import finalize_successful_payment
from app.promos.models import Ambassador, AmbassadorSale, PromoClick, PromoCode
from app.promos.schemas import AmbassadorCreate, PromoCodeCreate
from app.promos.service import create_ambassador, create_promo
from app.reviews.models import ReviewReply, ReviewReport, VerifiedReview
from app.reviews.schemas import ReviewCreate
from app.reviews.service import submit_review
from app.sponsorships.models import (
    Sponsor,
    SponsorshipInquiry,
    SponsorshipPlacement,
    SponsorshipSlot,
)
from app.taxonomy.demo_seed import apply_demo_taxonomy
from app.tickets.models import Ticket
from app.tickets.schemas import TicketTransferRequest
from app.tickets.service import transfer_ticket
from app.users.models import User
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_role_by_name, get_user_by_email
from app.vault.lifecycle import apply_admin_hide
from app.vault.models import VaultItem, VaultPurchase, VaultView
from app.vault.schemas import VaultAccessRuleInput, VaultItemCreate, VaultMediaInput
from app.vault.service import (
    create_vault_item,
    finalize_vault_purchase,
    redeem_vault_invite,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _mark(
    db: Session,
    entity_type: str,
    entity_key: str,
    entity_id: Any = None,
    **meta: Any,
) -> None:
    existing = db.scalar(
        select(DemoEntityMarker).where(
            DemoEntityMarker.entity_type == entity_type,
            DemoEntityMarker.entity_key == entity_key,
        )
    )
    if existing:
        if entity_id is not None:
            existing.entity_id = str(entity_id)
        if meta:
            existing.meta = {**(existing.meta or {}), **meta}
        return
    db.add(
        DemoEntityMarker(
            entity_type=entity_type,
            entity_key=entity_key,
            entity_id=str(entity_id) if entity_id is not None else None,
            meta=meta or None,
        )
    )


def _seeded(db: Session) -> bool:
    return (
        db.scalar(
            select(DemoEntityMarker).where(
                DemoEntityMarker.entity_type == "seed",
                DemoEntityMarker.entity_key == "complete",
            )
        )
        is not None
    )


def _ensure_user(db: Session, *, email: str, full_name: str, role: str) -> User:
    user = get_user_by_email(db, email)
    role_obj = get_role_by_name(db, role)
    buyer = get_role_by_name(db, "buyer")
    if user is None:
        user = User(
            email=email.lower(),
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=full_name,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = full_name
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.is_active = True
        user.is_verified = True
    if buyer and buyer not in user.roles:
        user.roles.append(buyer)
    if role_obj and role_obj not in user.roles:
        user.roles.append(role_obj)
    _mark(db, "user", email, user.id)
    return user


def _ensure_categories(db: Session) -> dict[str, EventCategory]:
    seed_event_categories(db)
    for name, slug, description in DEMO_CATEGORY_EXTRAS:
        cat = db.scalar(select(EventCategory).where(EventCategory.slug == slug))
        if cat is None:
            db.add(
                EventCategory(
                    name=name, slug=slug, description=description, is_active=True
                )
            )
        else:
            cat.name = name
            cat.description = description
            cat.is_active = True
    db.flush()
    return {c.slug: c for c in db.scalars(select(EventCategory)).all()}


def _ensure_hosts(db: Session, users: dict[str, User]) -> dict[str, Host]:
    hosts: dict[str, Host] = {}
    admin = users[f"admin@{DEMO_EMAIL_DOMAIN}"]
    for spec in DEMO_HOSTS:
        owner = users[spec["owner_email"]]
        host = db.scalar(select(Host).where(Host.slug == spec["slug"]))
        if host is None:
            host = Host(
                user_id=owner.id,
                display_name=spec["display_name"],
                slug=spec["slug"],
                status="active",
            )
            db.add(host)
            db.flush()
            db.add(
                HostProfile(
                    host_id=host.id,
                    bio=spec["bio"],
                    city=spec["city"],
                    state=spec["state"],
                    country="Nigeria",
                    website=f"https://demo.padeye.test/{spec['slug']}",
                    avatar_url=assets.host_avatar(spec["slug"]),
                    cover_url=assets.host_cover(spec["slug"]),
                    social_links={"instagram": f"@{spec['slug']}"},
                )
            )
        else:
            host.display_name = spec["display_name"]
            host.status = "active"
            if host.profile is not None:
                host.profile.bio = spec["bio"]
                host.profile.city = spec["city"]
                host.profile.state = spec["state"]
                host.profile.avatar_url = assets.host_avatar(spec["slug"])
                host.profile.cover_url = assets.host_cover(spec["slug"])
        verified = db.scalar(
            select(HostVerification).where(
                HostVerification.host_id == host.id,
                HostVerification.status == "verified",
            )
        )
        if verified is None:
            db.add(
                HostVerification(
                    host_id=host.id,
                    status="verified",
                    notes="Demo verified host",
                    reviewed_by=admin.id,
                    reviewed_at=_now(),
                )
            )
        _mark(db, "host", spec["slug"], host.id)
        hosts[spec["slug"]] = host
    db.flush()
    return hosts


def _ticket_blueprints(*, free: bool, include_hidden: bool) -> list[dict[str, Any]]:
    if free:
        return [
            {
                "name": "Free RSVP",
                "type": "free",
                "price": Decimal("0"),
                "quantity": 300,
                "visibility": "public",
                "description": "Reserve your seat — no payment required.",
                "benefits": "Entry confirmation\nEvent updates via WhatsApp\nNetworking lounge access",
            },
            {
                "name": "VIP Guest",
                "type": "vip",
                "price": Decimal("15000"),
                "quantity": 40,
                "visibility": "public",
                "description": "Priority seating and a welcome drink.",
                "benefits": "Priority check-in\nReserved seating\nOne welcome drink\nSpeaker Q&A access",
            },
        ]
    types: list[dict[str, Any]] = [
        {
            "name": "Early Bird",
            "type": "early_bird",
            "price": Decimal("3500"),
            "quantity": 120,
            "visibility": "public",
            "description": "Best price for early movers.",
            "benefits": "Standard entry\nEvent playlist drop\nDigital receipt + QR ticket",
        },
        {
            "name": "Regular",
            "type": "regular",
            "price": Decimal("7000"),
            "quantity": 400,
            "visibility": "public",
            "description": "General admission for the main floor.",
            "benefits": "Main floor access\nCloakroom\nQR check-in",
        },
        {
            "name": "VIP",
            "type": "vip",
            "price": Decimal("25000"),
            "quantity": 80,
            "visibility": "public",
            "description": "Elevated view, faster doors, and lounge access.",
            "benefits": "Fast-track entry\nVIP lounge\nOne drink token\nDedicated restrooms",
        },
        {
            "name": "VVIP",
            "type": "vvip",
            "price": Decimal("90000"),
            "quantity": 30,
            "visibility": "public",
            "description": "Front-row experience with host greeting.",
            "benefits": "Front-row / rails access\nMeet-and-greet window\nComplimentary bottle\nPersonal hostess",
        },
        {
            "name": "Table for 5",
            "type": "table",
            "price": Decimal("300000"),
            "quantity": 15,
            "visibility": "public",
            "seats_per_unit": 5,
            "max_per_order": 2,
            "description": "Reserved table package for five guests.",
            "benefits": "Reserved table for 5\nBottle service starter\nDedicated server\nPriority re-entry",
            "table_perks": "Booth seating · Mixologist pour · Photo backdrop access · Late checkout hold 30 min",
            "reservation_hold_minutes": 45,
        },
    ]
    if include_hidden:
        types.append(
            {
                "name": "Private Invite",
                "type": "hidden",
                "price": Decimal("12000"),
                "quantity": 25,
                "visibility": "hidden",
                "description": "Invite-link tier for press and partners.",
                "benefits": "Side entrance\nBackstage corridor access\nGuest list recognition",
                "access_code": "PADEYA-DEMO",
            }
        )
    return types


def _privacy_for_mode(privacy: str, *, city: str = "Lagos") -> dict[str, Any]:
    """Build location privacy fields. Showcase events use full_public / area_only only."""
    loc_vis = "full_public"
    event_type = "public"
    online_url = None
    public_label = None
    reveal_timing = "immediately"
    reveal_note = None
    online_rule = "after_payment"
    area_default = "Bodija" if city == "Ibadan" else "Victoria Island"

    if privacy == "hidden_until_payment":
        loc_vis = "hidden_until_payment"
        public_label = f"{area_default}, {city} — exact venue revealed after purchase."
        reveal_timing = "after_payment"
        reveal_note = "Exact venue revealed after purchase."
    elif privacy == "area_only":
        loc_vis = "area_only"
        public_label = f"{area_default}, {city}"
        reveal_timing = "after_payment"
        reveal_note = "Street address shared with ticket holders."
    elif privacy == "hidden_until_24h_before":
        loc_vis = "hidden_until_24h_before"
        public_label = f"{city} — exact venue 24 hours before start."
        reveal_timing = "twenty_four_hours_before"
        reveal_note = "Exact venue revealed 24 hours before the event."
    elif privacy == "online_only":
        loc_vis = "online_only"
        event_type = "online"
        online_url = "https://meet.padeya.demo/live"
        public_label = "Online Event — join link revealed after payment."
        reveal_timing = "after_payment"
        reveal_note = "Online link revealed after payment."
        online_rule = "after_payment"
    elif privacy == "hybrid":
        loc_vis = "area_only"
        event_type = "hybrid"
        online_url = "https://meet.padeya.demo/hybrid"
        public_label = f"{area_default}, {city} + livestream"
        reveal_timing = "after_payment"
        reveal_note = "In-person address and stream link follow your ticket."
        online_rule = "twenty_four_hours_before"
    elif privacy == "secret_bundle":
        loc_vis = "hidden_until_manual_approval"
        event_type = "secret_location"
        public_label = "Secret location — full details sent to approved attendees."
        reveal_timing = "manual_approval"
        reveal_note = "Full details sent to approved attendees."
    elif privacy == "full_public":
        public_label = f"{area_default}, {city}"

    map_fields: dict[str, Any] = {
        "country": "Nigeria",
        "latitude": None,
        "longitude": None,
        "approximate_latitude": None,
        "approximate_longitude": None,
        "approximate_map_label": None,
        "google_maps_share_url": None,
        "area": None,
    }
    if privacy == "full_public":
        if city == "Ibadan":
            map_fields.update(
                {
                    "latitude": "7.4010",
                    "longitude": "3.9170",
                    "area": "Bodija",
                    "google_maps_share_url": "https://maps.google.com/?q=7.4010,3.9170",
                }
            )
        else:
            map_fields.update(
                {
                    "latitude": "6.4281",
                    "longitude": "3.4219",
                    "area": "Victoria Island",
                    "google_maps_share_url": "https://maps.google.com/?q=6.4281,3.4219",
                }
            )
    elif privacy == "online_only":
        pass
    else:
        # Approximate / area pins only — exact street stays host/buyer scoped via privacy.
        map_fields.update(
            {
                "latitude": "7.3775" if city == "Ibadan" else "6.4698",
                "longitude": "3.9470" if city == "Ibadan" else "3.5852",
                "approximate_latitude": "7.38" if city == "Ibadan" else "6.45",
                "approximate_longitude": "3.95" if city == "Ibadan" else "3.48",
                "approximate_map_label": public_label or f"{city} area",
                "area": area_default,
                "google_maps_share_url": None,
            }
        )

    return {
        "location_visibility": loc_vis,
        "event_type": event_type,
        "public_location_label": public_label,
        "online_event_url": online_url,
        "reveal_timing": reveal_timing,
        "reveal_note": reveal_note,
        "online_url_reveal_rule": online_rule,
        "privacy_key": privacy,
        **map_fields,
    }


def _privacy_for_index(i: int) -> dict[str, Any]:
    """Rotate location privacy / event types so demos cover every Studio surface."""
    cycle = [
        "full_public",
        "hidden_until_payment",
        "area_only",
        "hidden_until_24h_before",
        "online_only",
        "hybrid",
        "secret_bundle",
        "area_only",
    ]
    return _privacy_for_mode(cycle[i % len(cycle)])


def _event_specs() -> list[dict[str, Any]]:
    now = _now()
    specs: list[dict[str, Any]] = []
    showcase_keys = set(SHOWCASE_EVENT_KEYS)

    # Named showcase events (messaging + QA). Public-safe location modes only.
    for i, row in enumerate(DEMO_SHOWCASE_EVENTS):
        city = str(row["city"])
        lifecycle = str(row["lifecycle"])
        if lifecycle == "completed":
            start = now - timedelta(days=18 + i * 5, hours=19)
            status = "completed"
        else:
            start = now + timedelta(days=6 + i * 2, hours=18)
            status = "published"
        privacy = _privacy_for_mode(str(row["location_mode"]), city=city)
        specs.append(
            {
                "key": row["key"],
                "title": row["title"],
                "host_slug": row["host_slug"],
                "category_slug": row["category_slug"],
                "status": status,
                "featured": bool(row.get("featured")),
                "start": start,
                "end": start + timedelta(hours=5),
                "free": False,
                "city": city,
                "enrich_studio": True,
                "showcase": True,
                **privacy,
            }
        )

    # Extra upcoming / lifecycle coverage (non-showcase)
    upcoming = [
        ("campus-fest-2026", "Campus Fest 2026", "mainlandvibes", "campus", False),
        ("rooftop-games-night", "Rooftop Games Night", "mainlandvibes", "lifestyle", False),
        ("product-builders-meetup", "Product Builders Meetup", "techconnectafrica", "tech", False),
        ("mainland-vibes-2025", "Mainland Vibes Recap Night", "mainlandvibes", "lifestyle", False),
    ]
    for i, (key, title, host, cat, featured) in enumerate(upcoming):
        if key in showcase_keys:
            continue
        start = now + timedelta(days=28 + i * 3, hours=18)
        privacy = _privacy_for_index(i + 1)
        specs.append(
            {
                "key": key,
                "title": title,
                "host_slug": host,
                "category_slug": cat,
                "status": "published",
                "featured": featured,
                "start": start,
                "end": start + timedelta(hours=5),
                "free": key == "product-builders-meetup",
                "city": "Lagos",
                "enrich_studio": True,
                **privacy,
            }
        )

    extras = [
        ("draft-secret-session", "Secret Session Draft", "djmaze", "music", "draft"),
        ("draft-open-mic", "Open Mic Draft Night", "lagoscomedyhub", "comedy", "draft"),
        ("draft-founder-lab", "Founder Lab Draft", "techconnectafrica", "tech", "draft"),
        ("pending-neon-nights", "Neon Nights Review", "djmaze", "nightlife", "pending_review"),
        ("pending-gospel-choir", "Choir Night Review", "praiseexperience", "gospel", "pending_review"),
        ("cancelled-beach-bash", "Beach Bash Cancelled", "mainlandvibes", "lifestyle", "cancelled"),
        ("rejected-stadium-show", "Stadium Show Rejected", "djmaze", "music", "rejected"),
        ("art-walk-lagos", "Art Walk Lagos", "lagoscomedyhub", "art-culture", "published"),
        ("sports-sunday", "Sports Sunday Kickoff", "mainlandvibes", "sports", "published"),
    ]
    for i, (key, title, host, cat, status) in enumerate(extras):
        if key in showcase_keys:
            continue
        start = now + timedelta(days=40 + i)
        if status in {"cancelled", "rejected"}:
            start = now + timedelta(days=25 + i)
        privacy = _privacy_for_index(i + 1)
        if key == "draft-secret-session":
            privacy = _privacy_for_mode("secret_bundle")
        specs.append(
            {
                "key": key,
                "title": title,
                "host_slug": host,
                "category_slug": cat,
                "status": status,
                "featured": False,
                "start": start,
                "end": start + timedelta(hours=4),
                "free": False,
                "city": "Lagos",
                "rejection_reason": "Incomplete safety plan" if status == "rejected" else None,
                "enrich_studio": True,
                **privacy,
            }
        )
    return specs


def _ensure_events(
    db: Session,
    hosts: dict[str, Host],
    categories: dict[str, EventCategory],
) -> dict[str, Event]:
    events: dict[str, Event] = {}
    for spec in _event_specs():
        slug = f"{DEMO_EVENT_SLUG_PREFIX}{spec['key']}"
        host = hosts[spec["host_slug"]]
        cat = categories.get(spec["category_slug"])
        banner = assets.event_banner(spec["key"])
        event = db.scalar(select(Event).where(Event.slug == slug))
        # Commerce needs published first for completed events
        initial_status = (
            "published" if spec["status"] == "completed" else spec["status"]
        )
        loc_vis = spec.get("location_visibility") or "full_public"
        is_online = loc_vis == "online_only" or spec.get("event_type") == "online"
        # Public-safe naming: never brand a hidden venue with a street-like public name.
        if is_online:
            venue_name = "Online"
            street = None
        elif loc_vis == "full_public":
            venue_name = f"{spec['title']} Hall"
            street = (
                "15 Awolowo Avenue"
                if spec["city"] == "Ibadan"
                else "12 Admiralty Way"
            )
        elif loc_vis == "area_only":
            venue_name = spec.get("public_location_label") or f"{spec['city']} area"
            street = "Ticket-holder address on file"
        else:
            venue_name = spec.get("public_location_label") or "Venue details later"
            street = "Exact address held for approved attendees"
        if event is None:
            event = Event(
                title=spec["title"],
                slug=slug,
                description=(
                    f"{spec['title']} is a Pàdéyá demo event hosted by {host.display_name}. "
                    "Verified tickets, Legacy trust, and local vibes — built to exercise "
                    "every Event Studio section from privacy to publish."
                ),
                short_tagline=f"{spec['title']} — curated on Pàdéyá",
                vibe=(
                    "Afrobeats energy"
                    if spec["category_slug"] in {"music", "nightlife"}
                    else "Community"
                ),
                event_type=spec.get("event_type") or "public",
                visibility="listed",
                category_id=cat.id if cat else None,
                host_id=host.id,
                start_datetime=spec["start"],
                end_datetime=spec["end"],
                doors_open_datetime=spec["start"] - timedelta(minutes=45),
                timezone="Africa/Lagos",
                venue_name=venue_name,
                address=street,
                city=spec["city"],
                state="Oyo" if spec["city"] == "Ibadan" else "Lagos",
                country=spec.get("country") or "Nigeria",
                area=spec.get("area"),
                latitude=spec.get("latitude"),
                longitude=spec.get("longitude"),
                google_maps_share_url=spec.get("google_maps_share_url"),
                approximate_latitude=spec.get("approximate_latitude"),
                approximate_longitude=spec.get("approximate_longitude"),
                approximate_map_label=spec.get("approximate_map_label"),
                public_location_label=spec.get("public_location_label"),
                location_visibility=loc_vis,
                reveal_timing=spec.get("reveal_timing") or "immediately",
                reveal_note=spec.get("reveal_note"),
                online_event_url=spec.get("online_event_url"),
                online_url_reveal_rule=spec.get("online_url_reveal_rule")
                or "after_payment",
                banner_url=banner,
                mobile_banner_url=banner,
                capacity=500,
                refund_policy="admin_controlled",
                refund_policy_type="admin_controlled",
                age_restriction="18+",
                dress_code="Smart casual",
                what_to_expect="Arrive early, scan your Pàdéyá ticket, enjoy the night.",
                what_to_bring="Valid ID and your ticket QR.",
                prohibited_items="No outside drinks or professional cameras without clearance.",
                status=initial_status,
                featured=bool(spec.get("featured")),
                seo_title=f"{spec['title']} | Pàdéyá",
                seo_description=f"Get tickets for {spec['title']} on Pàdéyá.",
                hashtags=["Padeya", "LagosEvents"],
                discoverable_keywords=["lagos", spec["category_slug"]],
                rejection_reason=spec.get("rejection_reason"),
                published_at=_now()
                if initial_status in {"published", "cancelled"}
                else None,
            )
            db.add(event)
            db.flush()
            db.add(
                EventVenue(
                    event_id=event.id,
                    name=event.venue_name or "Venue",
                    address=event.address,
                    city=event.city,
                    state=event.state,
                    country=event.country or "Nigeria",
                    latitude=event.latitude,
                    longitude=event.longitude,
                )
            )
            db.add(
                EventMedia(
                    event_id=event.id, url=banner, media_type="banner", sort_order=0
                )
            )
        else:
            event.title = spec["title"]
            event.banner_url = banner
            event.mobile_banner_url = banner
            event.start_datetime = spec["start"]
            event.end_datetime = spec["end"]
            event.doors_open_datetime = spec["start"] - timedelta(minutes=45)
            event.featured = bool(spec.get("featured"))
            event.location_visibility = loc_vis
            event.public_location_label = spec.get("public_location_label")
            event.event_type = spec.get("event_type") or event.event_type
            event.reveal_timing = spec.get("reveal_timing") or event.reveal_timing
            event.reveal_note = spec.get("reveal_note")
            event.online_event_url = spec.get("online_event_url")
            event.online_url_reveal_rule = (
                spec.get("online_url_reveal_rule") or event.online_url_reveal_rule
            )
            event.country = spec.get("country") or event.country or "Nigeria"
            event.area = spec.get("area")
            event.latitude = spec.get("latitude")
            event.longitude = spec.get("longitude")
            event.google_maps_share_url = spec.get("google_maps_share_url")
            event.approximate_latitude = spec.get("approximate_latitude")
            event.approximate_longitude = spec.get("approximate_longitude")
            event.approximate_map_label = spec.get("approximate_map_label")
            event.venue_name = venue_name
            event.address = street
            event.city = spec["city"]
            event.state = "Oyo" if spec["city"] == "Ibadan" else "Lagos"
            if is_online:
                event.venue_name = "Online"
                event.address = None
                event.latitude = None
                event.longitude = None
                event.google_maps_share_url = None
            if event.status not in {"completed"}:
                event.status = initial_status
            elif spec["status"] == "completed" and event.status == "published":
                # Fresh seed path marks completed after check-ins; keep published until then.
                pass

        needs_tickets = initial_status in {
            "published",
            "cancelled",
            "pending_review",
            "draft",
            "rejected",
            "paused",
        }
        if needs_tickets and not event.ticket_types:
            for tt in _ticket_blueprints(
                free=bool(spec.get("free")),
                include_hidden=spec["key"]
                in {"afrobeats-night-live", "draft-secret-session"},
            ):
                db.add(
                    TicketType(
                        event_id=event.id,
                        name=tt["name"],
                        type=tt["type"],
                        description=tt.get("description"),
                        price=tt["price"],
                        quantity=tt["quantity"],
                        visibility=tt["visibility"],
                        status="active",
                        seats_per_unit=tt.get("seats_per_unit", 1),
                        min_per_order=1,
                        max_per_order=tt.get("max_per_order", 10),
                        benefits=tt.get("benefits"),
                        table_perks=tt.get("table_perks"),
                        reservation_hold_minutes=tt.get("reservation_hold_minutes"),
                        access_code=tt.get("access_code"),
                        transfer_allowed=True,
                        refund_allowed=tt["type"] not in {"free", "free_rsvp"},
                        waitlist_enabled=tt["type"] in {"vip", "vvip", "table"},
                    )
                )
            db.flush()

        if spec.get("enrich_studio"):
            _apply_studio_enrichment(db, event=event, spec=spec, host=host)
        else:
            _sync_demo_event_asset_urls(event)

        _mark(db, "event", slug, event.id)
        events[spec["key"]] = event
    db.flush()
    return events


def _sync_demo_event_asset_urls(event: Event) -> None:
    """Point stored demo media at the current FRONTEND_URL (domain migrations)."""
    event.banner_url = assets.normalize_demo_asset_url(event.banner_url)
    event.mobile_banner_url = assets.normalize_demo_asset_url(event.mobile_banner_url)
    event.social_share_image_url = assets.normalize_demo_asset_url(
        event.social_share_image_url
    )
    for media in list(event.media or []):
        normalized = assets.normalize_demo_asset_url(media.url)
        if normalized:
            media.url = normalized


def _apply_studio_enrichment(
    db: Session,
    *,
    event: Event,
    spec: dict[str, Any],
    host: Host,
) -> None:
    """Fill Studio-facing fields so every demo section has something to show."""
    _sync_demo_event_asset_urls(event)
    start: datetime = spec["start"]
    end: datetime = spec["end"]
    key = spec["key"]
    cat = spec.get("category_slug") or "lifestyle"
    place = (
        spec.get("public_location_label")
        or event.public_location_label
        or event.city
        or "Lagos"
    )

    event.short_tagline = event.short_tagline or f"{spec['title']} — curated on Pàdéyá"
    event.vibe = event.vibe or (
        "Afrobeats energy" if cat in {"music", "nightlife"} else "Community night"
    )
    event.dress_code = "All black smart" if cat in {"nightlife", "music"} else "Smart casual"
    event.entry_requirements = (
        "Valid government ID matching the ticket name. No re-entry after 11pm for VIP floor."
        if cat in {"nightlife", "music"}
        else "Bring your Pàdéyá QR ticket and a valid ID."
    )
    event.accessibility_notes = (
        "Step-free entrance on the side gate · Accessible restrooms on ground floor · "
        "Staff can arrange seating near the aisle — message the host after purchase."
    )
    event.parking_info = (
        "Paid valet at the main gate (₦2,000). Street parking fills early — rideshare recommended."
        if event.location_visibility != "online_only"
        else "Fully online — no venue parking required."
    )
    event.what_to_expect = (
        f"Doors open early for check-in, followed by a paced run-of-show. "
        f"Expect a full {cat.replace('-', ' ')} experience hosted by {host.display_name}."
    )
    event.what_to_bring = "Valid ID, charged phone for your QR ticket, and light jacket for outdoor areas."
    event.prohibited_items = (
        "No outside drinks, glass bottles, drones, or professional cameras without clearance."
    )
    event.age_restriction = "21+" if cat == "nightlife" else "18+"
    event.id_required = True
    event.safety_notice = (
        "Security screening at the door. Look after your belongings. "
        "Medical / welfare desk is marked near check-in."
    )
    event.cancellation_policy = (
        "If the host cancels or postpones, eligible buyers receive a full refund or credit "
        "to a rescheduled date."
    )
    event.refund_policy_type = (
        "refund_until_24_hours_before"
        if cat in {"tech", "business", "campus"}
        else "admin_controlled"
    )
    event.refund_policy = event.refund_policy_type
    event.refund_policy_text = (
        "Full refunds available until 24 hours before doors when eligible. "
        "Table packages follow the host review window."
        if event.refund_policy_type == "refund_until_24_hours_before"
        else "Refunds are reviewed by Pàdéyá support under the host policy."
    )
    event.terms_acknowledgement = (
        "I confirm I meet the age and dress code rules and will follow door staff instructions."
    )
    event.door_sales_allowed = cat not in {"tech", "business"}
    event.re_entry_allowed = cat in {"lifestyle", "campus", "gospel", "food-drink"}
    event.check_in_start_time = start - timedelta(minutes=60)
    event.check_in_end_time = end
    event.capacity = event.capacity or 500
    event.brand_accent_override = "#8EF012" if cat in {"music", "nightlife"} else None
    event.sponsor_logo_urls = [
        assets.sponsor_logo("acme-events"),
        assets.sponsor_logo("nova-sips"),
        assets.sponsor_logo("greenline-media"),
    ]
    event.social_share_image_url = assets.event_gallery(key)
    event.teaser_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    event.seo_title = f"{spec['title']} in {place} | Tickets on Pàdéyá"
    event.seo_description = (
        f"Get verified tickets for {spec['title']}. "
        f"{place}. Agenda, lineup, and door policies on Pàdéyá."
    )
    event.social_share_title = f"{spec['title']} — tickets on Pàdéyá"
    event.social_share_description = (
        f"Join {host.display_name} for {spec['title']}. Secure checkout and QR tickets."
    )
    event.hashtags = ["Padeya", "LagosEvents", cat.replace("-", "").title()]
    event.discoverable_keywords = [
        "lagos",
        cat,
        host.slug,
        "tickets",
        "nigeria",
    ]

    # Agenda (upgrade thin demo rows so re-seed fills Studio schedule)
    if len(list(event.agenda_items or [])) < 3:
        for row in list(event.agenda_items or []):
            db.delete(row)
        db.flush()
        agenda = [
            ("Doors Open", "doors_open", -45, 0, "Wristbands and bag check."),
            ("Welcome / Host intro", "speech", 0, 20, "House rules and vibe check."),
            ("Main Set", "performance", 30, 150, "Headliner block."),
            ("Intermission", "break", 150, 170, "Merch and photos."),
            ("Encore / Closing", "performance", 170, 220, "Final set and shout-outs."),
        ]
        if cat in {"tech", "business"}:
            agenda = [
                ("Registration", "doors_open", -30, 0, "Badge pickup and wifi."),
                ("Keynote", "speech", 0, 40, "Opening keynote."),
                ("Panel", "panel", 45, 90, "Founders panel."),
                ("Networking break", "break", 90, 120, "Coffee and intros."),
                ("Lightning demos", "other", 120, 180, "Product demos."),
            ]
        for index, (title, typ, start_off, end_off, desc) in enumerate(agenda):
            db.add(
                EventAgendaItem(
                    event_id=event.id,
                    title=title,
                    type=typ,
                    description=desc,
                    start_time=start + timedelta(minutes=start_off),
                    end_time=start + timedelta(minutes=end_off),
                    sort_order=index,
                )
            )

    # People / lineup
    if len(list(event.people or [])) < 2:
        for row in list(event.people or []):
            db.delete(row)
        db.flush()
        people = [
            (
                f"{host.display_name.split()[0]} Host",
                "Host",
                f"Your host for {spec['title']}.",
                10,
            ),
            (
                "Guest Headliner",
                "Artist" if cat in {"music", "nightlife", "gospel"} else "Speaker",
                "Featured name on the bill — bio for lineup testing.",
                45,
            ),
            (
                "Support Act",
                "DJ" if cat in {"music", "nightlife"} else "Panelist",
                "Opens the night and keeps energy high.",
                25,
            ),
        ]
        for index, (name, role, bio, perf_off) in enumerate(people):
            db.add(
                EventPerson(
                    event_id=event.id,
                    name=name,
                    role=role,
                    bio=bio,
                    image_url=assets.host_avatar(spec["host_slug"]),
                    social_url="https://instagram.com/padeya.demo",
                    performance_time=start + timedelta(minutes=perf_off),
                    sort_order=index,
                )
            )

    # Checkout questions
    active_questions = [
        q
        for q in list(event.checkout_questions or [])
        if getattr(q, "status", "active") == "active"
    ]
    if len(active_questions) < 2:
        for row in list(event.checkout_questions or []):
            if getattr(row, "status", "active") == "active":
                db.delete(row)
        db.flush()
        db.add(
            EventCheckoutQuestion(
                event_id=event.id,
                label="WhatsApp number for venue updates",
                type="phone",
                required=True,
                help_text="Include country code (e.g. +234…).",
                sort_order=0,
                status="active",
            )
        )
        db.add(
            EventCheckoutQuestion(
                event_id=event.id,
                label="How did you hear about this event?",
                type="dropdown",
                required=False,
                options=["Instagram", "Friend", "Pàdéyá browse", "Host newsletter"],
                help_text="Optional — helps the host plan promos.",
                sort_order=1,
                status="active",
            )
        )
        db.add(
            EventCheckoutQuestion(
                event_id=event.id,
                label="Accessibility or seating notes",
                type="long_text",
                required=False,
                help_text="Tell the host if you need aisle seating or assistance.",
                sort_order=2,
                status="active",
            )
        )
        if cat in {"food-drink", "lifestyle"}:
            db.add(
                EventCheckoutQuestion(
                    event_id=event.id,
                    label="Dietary preferences",
                    type="checkbox",
                    required=False,
                    options=["Vegetarian", "Vegan", "Halal", "No alcohol"],
                    sort_order=3,
                    status="active",
                )
            )

    # Gallery + social media rows
    gallery_urls = [
        assets.event_gallery(key),
        assets.sponsor_logo("acme-events"),
        assets.memory_image("detty-friday-memory")
        if key != "detty-friday-live"
        else assets.event_gallery("mainland-vibes-summer"),
    ]
    existing_gallery = {
        m.url for m in (event.media or []) if m.media_type == "gallery"
    }
    sort_base = max(
        (m.sort_order for m in (event.media or []) if m.media_type == "gallery"),
        default=0,
    )
    for offset, url in enumerate(gallery_urls, start=1):
        if url in existing_gallery:
            continue
        db.add(
            EventMedia(
                event_id=event.id,
                url=url,
                media_type="gallery",
                alt_text=f"{spec['title']} gallery",
                sort_order=sort_base + offset,
            )
        )
    banner_media = next(
        (m for m in (event.media or []) if m.media_type == "banner"),
        None,
    )
    banner_url = event.banner_url or assets.event_banner(key)
    if banner_media is None:
        db.add(
            EventMedia(
                event_id=event.id,
                url=banner_url,
                media_type="banner",
                sort_order=0,
            )
        )
    else:
        banner_media.url = banner_url
    social_media = next(
        (m for m in (event.media or []) if m.media_type == "social_share"),
        None,
    )
    if event.social_share_image_url:
        if social_media is None:
            db.add(
                EventMedia(
                    event_id=event.id,
                    url=event.social_share_image_url,
                    media_type="social_share",
                    sort_order=20,
                )
            )
        else:
            social_media.url = event.social_share_image_url

    # Ticket benefits for already-created tiers
    for ticket in list(event.ticket_types or []):
        if ticket.benefits:
            continue
        if ticket.type == "table":
            ticket.description = ticket.description or "Reserved table package."
            ticket.benefits = (
                "Reserved table\nBottle service starter\nDedicated server\nPriority re-entry"
            )
            ticket.table_perks = (
                ticket.table_perks
                or "Booth seating · Mixologist pour · Photo backdrop · Hold 30 min"
            )
            ticket.reservation_hold_minutes = ticket.reservation_hold_minutes or 45
        elif ticket.type in {"vip", "vvip"}:
            ticket.benefits = (
                "Fast-track entry\nLounge access\nDrink token\nPriority support"
            )
        elif ticket.type in {"free", "free_rsvp"}:
            ticket.benefits = "Entry confirmation\nEvent updates\nQR ticket"
        else:
            ticket.benefits = "Standard entry\nQR check-in\nDigital receipt"


def _pay_order(db: Session, order: Order, buyer: User) -> list[Ticket]:
    order = get_order_by_id(db, order.id)
    assert order is not None
    if order.status == "paid":
        return list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)).all())
    if order.total_amount <= 0:
        initialize_checkout(db, user=buyer, order_id=order.id)
        return list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)).all())
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        reference=order.reference,
        amount=order.total_amount,
        currency=order.currency,
        status="pending",
    )
    db.add(payment)
    db.flush()
    tickets = finalize_successful_payment(
        db,
        order=order,
        payment=payment,
        provider_payment_id=f"demo_{order.reference}",
        raw_payload={"demo": True, "reference": order.reference},
        actor_user_id=buyer.id,
    )
    return list(tickets)


def _safe_call(db: Session, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        db.rollback()
        return None


def _demo_checkout_answers(event: Event, *, buyer_index: int = 0) -> list[CheckoutAnswerIn]:
    """Satisfy required Studio checkout questions so demo commerce can issue tickets."""
    answers: list[CheckoutAnswerIn] = []
    for question in list(event.checkout_questions or []):
        if getattr(question, "status", "active") != "active" or not question.required:
            continue
        if question.type == "phone":
            value: str | list[str] = f"+234801{buyer_index:07d}"[:14]
        elif question.type == "email":
            value = f"fan{buyer_index}@{DEMO_EMAIL_DOMAIN}"
        elif question.type == "dropdown":
            opts = list(question.options or [])
            value = opts[buyer_index % len(opts)] if opts else "Pàdéyá browse"
        elif question.type == "checkbox":
            opts = list(question.options or [])
            value = [opts[0]] if opts else ["None"]
        else:
            value = "Demo attendee note"
        answers.append(CheckoutAnswerIn(question_id=question.id, value=value))
    return answers


def _ensure_demo_fan_users(db: Session) -> dict[str, User]:
    """Create fan1–fan20 demo buyers (idempotent). Used by full seed and repair."""
    fans: dict[str, User] = {}
    for i in range(1, 21):
        email = f"fan{i}@{DEMO_EMAIL_DOMAIN}"
        persona = FAN_PERSONA_BY_EMAIL.get(email)
        full_name = persona["full_name"] if persona else f"Demo Fan {i}"
        fans[email] = _ensure_user(
            db, email=email, full_name=full_name, role="buyer"
        )
    db.flush()
    return fans


def _seed_commerce(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> list[User]:
    buyer = users[f"buyer@{DEMO_EMAIL_DOMAIN}"]
    fans_dict = _ensure_demo_fan_users(db)
    fans = list(fans_dict.values())
    db.commit()
    pool = [buyer, *fans]
    staff = users[f"staff@{DEMO_EMAIL_DOMAIN}"]
    admin = users[f"admin@{DEMO_EMAIL_DOMAIN}"]
    host_user = users[f"host@{DEMO_EMAIL_DOMAIN}"]

    # All showcase events + a few extras for volume
    commerce_keys = [
        *SHOWCASE_EVENT_KEYS,
        "product-builders-meetup",
        "art-walk-lagos",
        "mainland-vibes-2025",
    ]

    for idx, key in enumerate(commerce_keys):
        base = events.get(key)
        if base is None:
            continue
        event = db.scalar(
            select(Event)
            .where(Event.id == base.id)
            .options(
                selectinload(Event.ticket_types),
                selectinload(Event.checkout_questions),
            )
        )
        if event is None:
            continue
        if event.status != "published":
            event.status = "published"
            event.published_at = event.published_at or _now()
            db.commit()
        publics = [
            t
            for t in event.ticket_types
            if t.visibility == "public" and t.status == "active"
        ]
        if not publics:
            continue
        for j in range(5):
            user = pool[(idx * 5 + j) % len(pool)]
            tt = publics[j % len(publics)]
            order = _safe_call(
                db,
                create_order,
                db,
                user=user,
                payload=OrderCreate(
                    event_id=event.id,
                    items=[OrderItemCreate(ticket_type_id=tt.id, quantity=1)],
                    promo_code="MAZE20" if key == "afrobeats-night-live" and j == 0 else None,
                    referral_code="tola-demo" if key == "detty-friday-live" and j == 1 else None,
                    checkout_answers=_demo_checkout_answers(event, buyer_index=idx * 5 + j),
                ),
            )
            if order is None:
                continue
            _safe_call(db, _pay_order, db, order, user)

        # Failed payment example
        fail_user = pool[(idx + 2) % len(pool)]
        fail_order = _safe_call(
            db,
            create_order,
            db,
            user=fail_user,
            payload=OrderCreate(
                event_id=event.id,
                items=[OrderItemCreate(ticket_type_id=publics[0].id, quantity=1)],
                checkout_answers=_demo_checkout_answers(event, buyer_index=idx + 2),
            ),
        )
        if fail_order is not None:
            db.add(
                Payment(
                    order_id=fail_order.id,
                    provider="paystack",
                    reference=f"{fail_order.reference}-FAIL",
                    amount=fail_order.total_amount,
                    currency="NGN",
                    status="failed",
                )
            )
            db.commit()

    # Persona tickets for messaging + Passport context (while events are still published)
    for row in DEMO_PERSONA_CONTEXT:
        persona = get_user_by_email(db, str(row["email"]))
        if persona is None:
            continue
        for event_key in list(row.get("upcoming") or []) + list(row.get("attended") or []):
            event = events.get(str(event_key))
            if event is None:
                continue
            _ensure_demo_ticket(db, buyer=persona, event=event, vip=False)
        for event_key in list(row.get("vip_events") or []):
            event = events.get(str(event_key))
            if event is None:
                continue
            _ensure_demo_ticket(db, buyer=persona, event=event, vip=True)

    # Top up global tickets to 50+ across showcase upcoming events (keep ~5–20 feel per event)
    filler_events: list[Event] = []
    for key in SHOWCASE_UPCOMING_KEYS or SHOWCASE_EVENT_KEYS:
        ev = db.scalar(
            select(Event)
            .where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}{key}")
            .options(
                selectinload(Event.ticket_types),
                selectinload(Event.checkout_questions),
            )
        )
        if ev is not None and ev.ticket_types:
            filler_events.append(ev)
    if filler_events:
        for ev in filler_events:
            for tt in ev.ticket_types:
                if tt.visibility == "public" and tt.status == "active":
                    tt.quantity = max(tt.quantity, 120)
        db.commit()
        for n in range(40):
            count = db.scalar(
                select(func.count())
                .select_from(Ticket)
                .join(Event)
                .where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
            )
            if (count or 0) >= 55:
                break
            filler = filler_events[n % len(filler_events)]
            regular = next(
                (
                    t
                    for t in filler.ticket_types
                    if t.visibility == "public"
                    and t.status == "active"
                    and t.type == "regular"
                ),
                next(
                    (
                        t
                        for t in filler.ticket_types
                        if t.visibility == "public" and t.status == "active"
                    ),
                    None,
                ),
            )
            if regular is None:
                continue
            user = pool[n % len(pool)]
            order = _safe_call(
                db,
                create_order,
                db,
                user=user,
                payload=OrderCreate(
                    event_id=filler.id,
                    items=[OrderItemCreate(ticket_type_id=regular.id, quantity=1)],
                    checkout_answers=_demo_checkout_answers(
                        filler, buyer_index=100 + n
                    ),
                ),
            )
            if order:
                _safe_call(db, _pay_order, db, order, user)

    # Staff assignments for completed + key upcoming scanner demos
    completed_keys = list(SHOWCASE_COMPLETED_KEYS)
    scanner_keys = [*completed_keys, "afrobeats-night-live", "lagos-comedy-jam"]
    for key in scanner_keys:
        event = events.get(key)
        if event is None:
            continue
        host_owner = db.get(User, db.get(Host, event.host_id).user_id)  # type: ignore[arg-type]
        exists = db.scalar(
            select(EventStaffAssignment).where(
                EventStaffAssignment.event_id == event.id,
                EventStaffAssignment.user_id == staff.id,
            )
        )
        if exists is None:
            db.add(
                EventStaffAssignment(
                    event_id=event.id,
                    user_id=staff.id,
                    assigned_by_user_id=(host_owner.id if host_owner else host_user.id),
                    role_label="scanner",
                )
            )
    db.commit()

    # Check-ins (target 20+ successful)
    for key in completed_keys:
        event = events.get(key)
        if event is None:
            continue
        session = _safe_call(
            db,
            start_scanner_session,
            db,
            user=staff,
            payload=StartSessionRequest(event_id=event.id, device_label="Demo Gate Scanner"),
            ip_address="127.0.0.1",
        )
        scanner = staff if session is not None else admin
        if session is None:
            session = _safe_call(
                db,
                start_scanner_session,
                db,
                user=admin,
                payload=StartSessionRequest(
                    event_id=event.id, device_label="Demo Admin Scanner"
                ),
                ip_address="127.0.0.1",
            )
        if session is None:
            continue
        tickets = list(
            db.scalars(
                select(Ticket).where(
                    Ticket.event_id == event.id, Ticket.status == "active"
                )
            ).all()
        )
        for ticket in tickets[:8]:
            _safe_call(
                db,
                check_in_ticket,
                db,
                user=scanner,
                payload=CheckInRequest(
                    event_id=event.id,
                    public_code=ticket.public_code,
                    session_id=session.id,
                ),
            )
        # duplicate
        checked = db.scalar(
            select(Ticket).where(
                Ticket.event_id == event.id, Ticket.status == "checked_in"
            )
        )
        if checked:
            _safe_call(
                db,
                check_in_ticket,
                db,
                user=scanner,
                payload=CheckInRequest(
                    event_id=event.id,
                    public_code=checked.public_code,
                    session_id=session.id,
                ),
            )
        remaining = list(
            db.scalars(
                select(Ticket).where(
                    Ticket.event_id == event.id, Ticket.status == "active"
                )
            ).all()
        )
        if remaining:
            _safe_call(
                db,
                override_check_in,
                db,
                user=admin,
                payload=ManualOverrideRequest(
                    event_id=event.id,
                    ticket_id=remaining[0].id,
                    reason="Demo admin override — guest list confirmed",
                    session_id=session.id,
                ),
            )

    # Conv 4: Chidi checked in to a past Tech Connect event (Product Demo Night)
    chidi = get_user_by_email(db, f"fan3@{DEMO_EMAIL_DOMAIN}")
    past_tech = events.get("startup-demo-evening")
    if chidi is not None and past_tech is not None:
        chidi_ticket = db.scalar(
            select(Ticket).where(
                Ticket.buyer_user_id == chidi.id,
                Ticket.event_id == past_tech.id,
                Ticket.status.in_(("active", "checked_in")),
            )
        )
        if chidi_ticket is not None and chidi_ticket.status != "checked_in":
            _ensure_demo_check_in(
                db,
                ticket=chidi_ticket,
                event=past_tech,
                scanner=staff if staff is not None else admin,
            )

    for key in completed_keys:
        if key in events:
            events[key].status = "completed"
    db.commit()

    # Transfers
    transfer_count = 0
    upcoming = list(
        db.scalars(
            select(Ticket)
            .join(Event)
            .where(
                Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX),
                Ticket.status == "active",
                Event.status == "published",
            )
            .limit(30)
        ).all()
    )
    for ticket in upcoming:
        if transfer_count >= 5:
            break
        recipient = next((u for u in pool if u.id != ticket.buyer_user_id), None)
        owner = db.get(User, ticket.buyer_user_id)
        if not recipient or not owner:
            continue
        # EmailStr rejects reserved .test TLDs; demo emails stay @demo.padeye.test.
        transfer_payload = TicketTransferRequest.model_construct(
            to_email=recipient.email,
            note="Demo transfer",
        )
        result = _safe_call(
            db,
            transfer_ticket,
            db,
            user=owner,
            ticket_id=ticket.id,
            payload=transfer_payload,
        )
        if result is not None:
            transfer_count += 1

    # Cancelled ticket for invalid scan
    cancel_ticket = db.scalar(
        select(Ticket)
        .join(Event)
        .where(
            Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}afrobeats-night-live",
            Ticket.status == "active",
        )
    )
    if cancel_ticket:
        cancel_ticket.status = "cancelled"
        db.commit()
        session = _safe_call(
            db,
            start_scanner_session,
            db,
            user=staff,
            payload=StartSessionRequest(
                event_id=cancel_ticket.event_id, device_label="Invalid scan demo"
            ),
        )
        if session:
            _safe_call(
                db,
                check_in_ticket,
                db,
                user=staff,
                payload=CheckInRequest(
                    event_id=cancel_ticket.event_id,
                    public_code=cancel_ticket.public_code,
                    session_id=session.id,
                ),
            )

    return fans


def _seed_reviews(db: Session, events: dict[str, Event]) -> int:
    texts = [
        "Amazing night — sound was crisp and the crowd was electric.",
        "Great host energy. Check-in was smooth with Pàdéyá QR.",
        "Worth every naira. VIP section felt premium.",
        "Loved the setlist and venue lighting.",
        "Solid comedy line-up, will definitely come again.",
        "Networking was top-tier; met three founders.",
        "Worship night was powerful and well organized.",
        "Mainland vibes delivered — games were fun.",
        "Food options were good; music kept everyone dancing.",
        "Slight queue at entry but overall excellent experience.",
    ]
    admin = get_user_by_email(db, f"admin@{DEMO_EMAIL_DOMAIN}")
    count = 0
    for event in events.values():
        if event.status != "completed":
            continue
        host = db.get(Host, event.host_id)
        host_owner = db.get(User, host.user_id) if host else None
        tickets = list(
            db.scalars(
                select(Ticket).where(
                    Ticket.event_id == event.id, Ticket.status == "checked_in"
                )
            ).all()
        )
        for i, ticket in enumerate(tickets):
            if count >= 28:
                return count
            user = db.get(User, ticket.buyer_user_id)
            if user is None:
                continue
            if db.scalar(select(VerifiedReview).where(VerifiedReview.ticket_id == ticket.id)):
                count += 1
                continue
            review = _safe_call(
                db,
                submit_review,
                db,
                user=user,
                payload=ReviewCreate(
                    ticket_id=ticket.id,
                    rating=3 + (i % 3),
                    title="Verified attendee take",
                    body=texts[i % len(texts)],
                ),
            )
            if review is None:
                continue
            count += 1
            if i % 4 == 0 and host_owner is not None:
                if not db.scalar(
                    select(ReviewReply).where(ReviewReply.review_id == review.id)
                ):
                    db.add(
                        ReviewReply(
                            review_id=review.id,
                            host_id=event.host_id,
                            author_user_id=host_owner.id,
                            body="Thank you for rocking with us on Pàdéyá!",
                        )
                    )
                    db.commit()
            if i == 1 and admin:
                review.status = "hidden"
                review.moderation_reason = "Demo moderation — policy review"
                review.moderated_by_user_id = admin.id
                review.moderated_at = _now()
                db.commit()
            if i == 2 and admin:
                reporter = get_user_by_email(db, f"support@{DEMO_EMAIL_DOMAIN}")
                if reporter and not db.scalar(
                    select(ReviewReport).where(ReviewReport.review_id == review.id)
                ):
                    db.add(
                        ReviewReport(
                            review_id=review.id,
                            reporter_user_id=reporter.id,
                            reason="Demo report for admin moderation queue",
                            status="open",
                        )
                    )
                    db.commit()
    return count


def _seed_legacy_studio(db: Session, hosts: dict[str, Host]) -> None:
    """Give each demo host a complete Legacy Content Studio config."""
    host_specs = {h["slug"]: h for h in DEMO_HOSTS}
    for slug, host in hosts.items():
        spec = host_specs.get(slug, {})
        sponsor_ready = bool(spec.get("sponsor_ready", True))
        vault_enabled = bool(spec.get("vault_enabled", True))
        page = ensure_legacy_page(db, host.id)
        page.tagline = f"{host.display_name.split()[0]} nights · verified on Pàdéyá"
        page.primary_category_slug = spec.get("primary_category_slug") or "nightlife"
        page.host_type_slug = spec.get("host_type_slug") or "promoter"
        page.service_areas = [host.profile.city] if host.profile and host.profile.city else ["Lagos"]
        page.sponsorship_available = sponsor_ready
        page.sponsorship_note = (
            f"Partner with {host.display_name} for brand nights on Pàdéyá."
            if sponsor_ready
            else None
        )
        if vault_enabled:
            page.primary_cta_label = "Visit Vault"
            page.primary_cta_type = "vault"
            page.primary_cta_value = f"/@{host.slug}/vault"
        else:
            page.primary_cta_label = "View events"
            page.primary_cta_type = "events"
            page.primary_cta_value = "#upcoming-events"
        page.secondary_cta_label = "View events"
        page.secondary_cta_type = "events"
        page.secondary_cta_value = "#upcoming-events"

        ensure_default_blocks(db, host.id)
        # Customize a couple of titles for demo polish
        for block in db.scalars(
            select(HostLegacyContentBlock).where(HostLegacyContentBlock.host_id == host.id)
        ).all():
            if block.block_type == "upcoming_events":
                block.title_override = "Upcoming nights"
                block.layout_style = "premium_cards"
                block.item_limit = 3
            elif block.block_type == "verified_reviews":
                block.title_override = "What verified attendees say"
                block.layout_style = "verified_quotes"
                block.item_limit = 5
            elif block.block_type == "vault_preview":
                block.title_override = "Vault"
                block.layout_style = "locked_cards"
                block.item_limit = 3

        # Social links
        existing_social = db.scalars(
            select(HostSocialLink).where(HostSocialLink.host_id == host.id)
        ).all()
        if not existing_social:
            db.add(
                HostSocialLink(
                    host_id=host.id,
                    platform="instagram",
                    url=f"https://instagram.com/{slug}",
                    label="Instagram",
                    sort_order=0,
                    is_visible=True,
                )
            )

        contact = db.scalar(
            select(HostContactSettings).where(HostContactSettings.host_id == host.id)
        )
        if contact is None:
            contact = HostContactSettings(host_id=host.id)
            db.add(contact)
        contact.preference = "email"
        contact.public_email = f"bookings+{slug}@{DEMO_EMAIL_DOMAIN}"
        contact.show_contact_form = True
        contact.preferred_channel = "email"
        contact.note = "For brand partnerships and press — respond within 2 business days."

        # Featured items
        def _set_featured(placement: str, item_type: str, item_id: Any) -> None:
            if item_id is None:
                return
            existing = db.scalar(
                select(HostLegacyFeaturedItem).where(
                    HostLegacyFeaturedItem.host_id == host.id,
                    HostLegacyFeaturedItem.placement == placement,
                )
            )
            if existing:
                existing.item_type = item_type
                existing.item_id = item_id
            else:
                db.add(
                    HostLegacyFeaturedItem(
                        host_id=host.id,
                        item_type=item_type,
                        item_id=item_id,
                        placement=placement,
                        sort_order=0,
                    )
                )

        upcoming = db.scalar(
            select(Event)
            .where(
                Event.host_id == host.id,
                Event.status == "published",
                Event.end_datetime >= _now(),
            )
            .order_by(Event.start_datetime.asc())
        )
        past = db.scalar(
            select(Event)
            .where(
                Event.host_id == host.id,
                Event.status.in_(["completed", "published"]),
                Event.end_datetime < _now(),
            )
            .order_by(Event.end_datetime.desc())
        )
        review = db.scalar(
            select(VerifiedReview)
            .where(
                VerifiedReview.host_id == host.id,
                VerifiedReview.status == "visible",
            )
            .order_by(VerifiedReview.created_at.desc())
        )
        vault = db.scalar(
            select(VaultItem)
            .where(
                VaultItem.host_id == host.id,
                VaultItem.status == "published",
            )
            .order_by(VaultItem.created_at.desc())
        )
        memory = db.scalar(
            select(EventMemory)
            .where(EventMemory.host_id == host.id, EventMemory.status == "published")
            .order_by(EventMemory.created_at.desc())
        )
        _set_featured(
            "featured_upcoming_event",
            "event",
            upcoming.id if upcoming else None,
        )
        _set_featured("featured_past_event", "event", past.id if past else None)
        _set_featured("featured_review", "review", review.id if review else None)
        _set_featured("featured_vault_item", "vault_item", vault.id if vault else None)
        _set_featured("featured_memory", "memory", memory.id if memory else None)
    db.commit()


def _force_legacy_tiers(db: Session, hosts: dict[str, Host]) -> None:
    metrics = {
        "icon": (Decimal("92"), 18, 2200, 1200, Decimal("4.70"), 45),
        "certified": (Decimal("78"), 10, 900, 500, Decimal("4.50"), 28),
        "established": (Decimal("62"), 7, 450, 260, Decimal("4.30"), 18),
        "rising": (Decimal("48"), 4, 180, 90, Decimal("4.20"), 10),
    }
    for spec in DEMO_HOSTS:
        host = hosts[spec["slug"]]
        tier = db.scalar(select(LegacyTier).where(LegacyTier.slug == spec["tier_slug"]))
        composite, completed, sold, checkins, rating, reviews = metrics[spec["tier_slug"]]
        follower_rows = list(
            db.scalars(select(HostFollower).where(HostFollower.host_id == host.id))
        )
        from app.hosts.fan_self_abuse import is_user_owner_of_host

        follower_count = sum(
            1
            for row in follower_rows
            if not is_user_owner_of_host(
                db, user_id=row.user_id, host_profile_id=host.id
            )
        )
        score = db.scalar(select(HostLegacyScore).where(HostLegacyScore.host_id == host.id))
        if score is None:
            score = HostLegacyScore(host_id=host.id)
            db.add(score)
        score.tier_id = tier.id if tier else None
        score.events_hosted = completed + 3
        score.completed_events = completed
        score.tickets_sold = sold
        score.verified_checkins = checkins
        score.average_verified_rating = rating
        score.review_count = reviews
        score.followers = int(follower_count)
        score.composite_score = composite
        score.legacy_status = tier.name if tier else "New Host"
        score.factor_scores = {"demo_forced_tier": True, "tier": spec["tier_slug"]}
        db.add(
            HostLegacyScoreHistory(
                host_id=host.id,
                tier_id=tier.id if tier else None,
                tier_slug=spec["tier_slug"],
                composite_score=composite,
                factor_scores={"demo": True},
                metrics_snapshot={"tickets_sold": sold},
                reason="demo_seed",
            )
        )
    db.commit()


def _seed_promos_ambassadors(db: Session, hosts: dict[str, Host]) -> None:
    for p in PROMO_CODES:
        host = hosts[p["host_slug"]]
        owner = db.get(User, host.user_id)
        if owner is None:
            continue
        if db.scalar(
            select(PromoCode).where(
                PromoCode.host_id == host.id, PromoCode.code == p["code"]
            )
        ):
            continue
        value = Decimal(str(p["discount_value"]))
        if p["code"] == "TECHFREE":
            value = Decimal("100")
        _safe_call(
            db,
            create_promo,
            db,
            user=owner,
            payload=PromoCodeCreate(
                code=p["code"],
                discount_type=p["discount_type"],
                discount_value=value,
                usage_limit=100,
                max_per_user=2,
                expires_at=_now() + timedelta(days=60),
                status=p.get("status", "active"),
            ),
        )

    maze = hosts["djmaze"]
    maze_owner = db.get(User, maze.user_id)
    detty = db.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}detty-friday-live")
    )
    for i, amb in enumerate(AMBASSADORS):
        if db.scalar(
            select(Ambassador).where(Ambassador.referral_code == amb["referral_code"].lower())
        ) or db.scalar(
            select(Ambassador).where(Ambassador.referral_code == amb["referral_code"])
        ):
            row = db.scalar(
                select(Ambassador).where(
                    Ambassador.referral_code.in_(
                        [amb["referral_code"].lower(), amb["referral_code"]]
                    )
                )
            )
        else:
            created = _safe_call(
                db,
                create_ambassador,
                db,
                user=maze_owner,
                payload=AmbassadorCreate(
                    display_name=amb["display_name"],
                    referral_code=amb["referral_code"],
                    email=f"{amb['display_name'].lower()}@{DEMO_EMAIL_DOMAIN}",
                    commission_rate_percent=Decimal("5"),
                ),
            )
            row = None
            if created is not None:
                row = db.scalar(
                    select(Ambassador).where(
                        Ambassador.referral_code == amb["referral_code"].lower()
                    )
                )
        if row is None:
            continue
        for _ in range(3 + i):
            db.add(
                PromoClick(
                    ambassador_id=row.id,
                    event_id=detty.id if detty else None,
                    landing_path=f"/events/{DEMO_EVENT_SLUG_PREFIX}detty-friday-live",
                    ip_hash=f"demo{i}",
                )
            )
        db.commit()

    db.commit()


def _seed_ambassador_sales(db: Session, hosts: dict[str, Host]) -> None:
    maze = hosts["djmaze"]
    orders = list(
        db.scalars(
            select(Order)
            .join(Event)
            .where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX), Order.status == "paid")
            .limit(12)
        ).all()
    )
    ambs = list(
        db.scalars(select(Ambassador).where(Ambassador.host_id == maze.id)).all()
    )
    for i, order in enumerate(orders):
        if i >= len(ambs):
            break
        if db.scalar(select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)):
            continue
        db.add(
            AmbassadorSale(
                ambassador_id=ambs[i % len(ambs)].id,
                order_id=order.id,
                event_id=order.event_id,
                tickets_sold=1,
                revenue_amount=order.total_amount,
                commission_owed=(order.total_amount * Decimal("0.05")).quantize(
                    Decimal("0.01")
                ),
                status="attributed",
            )
        )
    db.commit()


def _seed_crm(db: Session, hosts: dict[str, Host], pool: list[User]) -> None:
    announcements = [
        ("New event drop", "We just published a new Pàdéyá event. Grab tickets early."),
        ("Early-bird ticket drop", "Early bird pricing is live for 48 hours only."),
        ("Event reminder", "See you tomorrow — bring your Pàdéyá QR ticket."),
        ("Thank you", "Thank you for rocking with us. Leave a verified review."),
        ("Vault drop", "New Vault content just unlocked for superfans."),
    ]
    for slug, host in hosts.items():
        owner = db.get(User, host.user_id)
        if owner is None:
            continue
        ensure_system_segments(db, host.id)
        for i, user in enumerate(pool[:12]):
            if user.id == host.user_id:
                continue
            _safe_call(
                db,
                follow_host,
                db,
                user=user,
                payload=FollowRequest(host_slug=slug),
            )
            if i % 2 == 0:
                _safe_call(
                    db,
                    update_marketing_opt_in,
                    db,
                    user=user,
                    host_id=host.id,
                    marketing_opt_in=True,
                )
        existing = db.scalar(
            select(func.count())
            .select_from(HostAnnouncement)
            .where(HostAnnouncement.host_id == host.id)
        )
        if (existing or 0) >= 5:
            continue
        for title, body in announcements:
            _safe_call(
                db,
                create_announcement,
                db,
                user=owner,
                payload=AnnouncementCreate(
                    title=title,
                    body_email=body,
                    body_whatsapp=body,
                    channel="email",
                    segment_key="followers",
                ),
            )


def _seed_finance(db: Session, users: dict[str, User], hosts: dict[str, Host]) -> None:
    buyer = users[f"buyer@{DEMO_EMAIL_DOMAIN}"]
    finance = users[f"finance@{DEMO_EMAIL_DOMAIN}"]
    admin = users[f"admin@{DEMO_EMAIL_DOMAIN}"]
    maze_owner = users[f"host@{DEMO_EMAIL_DOMAIN}"]
    maze = hosts["djmaze"]
    get_or_create_host_balance(db, maze.id)
    db.commit()

    bank = BankDetails(
        bank_name="Demo Bank NG",
        account_name="DJ Maze",
        account_number="0123456789",
    )
    orders = list(
        db.scalars(
            select(Order)
            .join(Event)
            .where(
                Event.slug.in_(
                    [
                        f"{DEMO_EVENT_SLUG_PREFIX}afrobeats-night-live",
                        f"{DEMO_EVENT_SLUG_PREFIX}lagos-comedy-jam",
                        f"{DEMO_EVENT_SLUG_PREFIX}mainland-vibes-summer",
                        f"{DEMO_EVENT_SLUG_PREFIX}food-and-flow",
                    ]
                ),
                Order.status == "paid",
            )
            .limit(5)
        ).all()
    )
    if len(orders) < 3:
        orders = list(
            db.scalars(
                select(Order)
                .join(Event)
                .where(
                    Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX),
                    Order.status == "paid",
                )
                .limit(5)
            ).all()
        )
    if orders:
        _safe_call(
            db,
            create_refund_request,
            db,
            user=db.get(User, orders[0].buyer_user_id) or buyer,
            payload=RefundRequestCreate(
                order_id=orders[0].id, reason="Demo refund pending review"
            ),
        )
    if len(orders) > 1:
        r2 = _safe_call(
            db,
            create_refund_request,
            db,
            user=db.get(User, orders[1].buyer_user_id) or buyer,
            payload=RefundRequestCreate(
                order_id=orders[1].id, reason="Demo refund approve path"
            ),
        )
        if isinstance(r2, dict) and r2.get("id"):
            _safe_call(
                db,
                review_refund_request,
                db,
                user=finance,
                refund_request_id=r2["id"],
                payload=RefundReview(action="approve", note="Demo approved"),
            )
    if len(orders) > 2:
        r3 = _safe_call(
            db,
            create_refund_request,
            db,
            user=db.get(User, orders[2].buyer_user_id) or buyer,
            payload=RefundRequestCreate(
                order_id=orders[2].id, reason="Demo refund reject path"
            ),
        )
        if isinstance(r3, dict) and r3.get("id"):
            _safe_call(
                db,
                review_refund_request,
                db,
                user=finance,
                refund_request_id=r3["id"],
                payload=RefundReview(action="reject", note="Outside policy window"),
            )

    _safe_call(
        db,
        create_payout_request,
        db,
        user=maze_owner,
        payload=PayoutRequestCreate(
            amount=Decimal("50000"), bank=bank, note="Demo payout pending"
        ),
    )
    p2 = _safe_call(
        db,
        create_payout_request,
        db,
        user=maze_owner,
        payload=PayoutRequestCreate(
            amount=Decimal("25000"), bank=bank, note="Demo payout under review"
        ),
    )
    if isinstance(p2, dict) and p2.get("id"):
        _safe_call(
            db,
            review_payout_request,
            db,
            user=finance,
            payout_id=p2["id"],
            payload=PayoutReview(action="under_review", note="Checking ledger"),
        )
    p3 = _safe_call(
        db,
        create_payout_request,
        db,
        user=maze_owner,
        payload=PayoutRequestCreate(
            amount=Decimal("40000"), bank=bank, note="Demo payout paid"
        ),
    )
    if isinstance(p3, dict) and p3.get("id"):
        _safe_call(
            db,
            review_payout_request,
            db,
            user=finance,
            payout_id=p3["id"],
            payload=PayoutReview(action="approve", note="Approved for payment"),
        )
        _safe_call(
            db,
            mark_payout_paid,
            db,
            user=admin,
            payout_id=p3["id"],
            payload=PayoutMarkPaid(
                bank_transfer_reference="DEMO-PAYOUT-001",
                evidence_file_url=assets.sponsor_logo("acme-events"),
                admin_note="Demo bank transfer receipt",
            ),
        )


def _demo_event(events: dict[str, Event], key: str) -> Event | None:
    return events.get(key)


def _ensure_demo_ticket(
    db: Session,
    *,
    buyer: User,
    event: Event,
    vip: bool = False,
) -> Ticket | None:
    """Ensure Demo Buyer holds an active/checked-in ticket (VIP when requested)."""
    event = db.scalar(
        select(Event)
        .where(Event.id == event.id)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.checkout_questions),
        )
    )
    if event is None:
        return None

    q = select(Ticket).where(
        Ticket.event_id == event.id,
        Ticket.buyer_user_id == buyer.id,
        Ticket.status.in_(("active", "checked_in")),
    )
    if vip:
        q = q.join(TicketType, TicketType.id == Ticket.ticket_type_id).where(
            TicketType.type.in_(("vip", "vvip"))
        )
    existing = db.scalar(q.limit(1))
    if existing is not None:
        return existing

    publics = [
        t
        for t in event.ticket_types
        if t.visibility == "public" and t.status == "active"
    ]
    if vip:
        publics = [t for t in publics if t.type in {"vip", "vvip"}]
    if not publics:
        return None
    tt = publics[0]
    order = _safe_call(
        db,
        create_order,
        db,
        user=buyer,
        payload=OrderCreate(
            event_id=event.id,
            items=[OrderItemCreate(ticket_type_id=tt.id, quantity=1)],
            checkout_answers=_demo_checkout_answers(event, buyer_index=900),
        ),
    )
    if order is None:
        return None
    tickets = _safe_call(db, _pay_order, db, order, buyer) or []
    return tickets[0] if tickets else None


def _ensure_demo_check_in(
    db: Session,
    *,
    ticket: Ticket,
    event: Event,
    scanner: User,
) -> None:
    if ticket.status == "checked_in":
        return
    session = _safe_call(
        db,
        start_scanner_session,
        db,
        user=scanner,
        payload=StartSessionRequest(
            event_id=event.id, device_label="Demo Vault Gate"
        ),
        ip_address="127.0.0.1",
    )
    if session is None:
        return
    _safe_call(
        db,
        check_in_ticket,
        db,
        user=scanner,
        payload=CheckInRequest(
            event_id=event.id,
            public_code=ticket.public_code,
            session_id=session.id,
        ),
    )


def _finalize_demo_vault_purchase(
    db: Session,
    *,
    item: VaultItem,
    buyer: User,
    amount: Decimal | None = None,
) -> None:
    existing = db.scalar(
        select(VaultPurchase).where(
            VaultPurchase.vault_item_id == item.id,
            VaultPurchase.user_id == buyer.id,
            VaultPurchase.status == "paid",
        )
    )
    if existing is not None:
        return
    purchase = VaultPurchase(
        vault_item_id=item.id,
        host_id=item.host_id,
        user_id=buyer.id,
        amount=amount if amount is not None else item.price,
        currency="NGN",
        payment_reference=f"DEMO-VAULT-{secrets.token_hex(4).upper()}",
        status="pending",
    )
    db.add(purchase)
    db.flush()
    result = _safe_call(
        db,
        finalize_vault_purchase,
        db,
        purchase=purchase,
        provider_payment_id=purchase.payment_reference,
        raw_payload={"demo": True},
    )
    if result is None:
        purchase = db.scalar(
            select(VaultPurchase).where(
                VaultPurchase.payment_reference == purchase.payment_reference
            )
        )
        if purchase and purchase.status != "paid":
            purchase.status = "paid"
            purchase.paid_at = _now()
            db.commit()


def _seed_vault_views(
    db: Session,
    *,
    buyer: User,
    items: dict[str, VaultItem],
) -> None:
    """Seed a mix of unlocked and locked catalog views for demo analytics."""
    view_specs: list[tuple[str, bool]] = [
        ("unreleased-set", True),
        ("bts-afrobeats", True),
        ("vip-gallery", True),
        ("comedy-early", True),
        ("backstage-comedy", True),
        ("recap-video", True),
        ("secret-location", False),
        ("founder-deck", True),
        ("product-demo-replay", True),
        ("product-demo-deck", True),
        ("worship-rehearsal", True),
        ("vip-choir-backstage", False),
    ]
    for slug, had_access in view_specs:
        item = items.get(slug)
        if item is None:
            continue
        already = db.scalar(
            select(VaultView.id).where(
                VaultView.vault_item_id == item.id,
                VaultView.user_id == buyer.id,
            )
        )
        if already is not None:
            continue
        db.add(
            VaultView(
                vault_item_id=item.id,
                user_id=buyer.id,
                had_access=had_access,
            )
        )
    # Anonymous teaser impressions on locked paid drops
    for slug in ("secret-location", "unreleased-set", "vip-choir-backstage"):
        item = items.get(slug)
        if item is None:
            continue
        anon_count = (
            db.scalar(
                select(func.count())
                .select_from(VaultView)
                .where(
                    VaultView.vault_item_id == item.id,
                    VaultView.user_id.is_(None),
                )
            )
            or 0
        )
        for _ in range(max(0, 3 - int(anon_count))):
            db.add(
                VaultView(
                    vault_item_id=item.id,
                    user_id=None,
                    had_access=False,
                )
            )
    db.commit()


def _seed_vault(
    db: Session,
    hosts: dict[str, Host],
    users: dict[str, User],
    events: dict[str, Event],
) -> None:
    """Seed host Vault catalogs with mixed access, buyer unlocks, views, and earnings."""
    buyer = users[f"buyer@{DEMO_EMAIL_DOMAIN}"]
    admin = users[f"admin@{DEMO_EMAIL_DOMAIN}"]
    staff = users[f"staff@{DEMO_EMAIL_DOMAIN}"]
    fan = get_user_by_email(db, f"fan1@{DEMO_EMAIL_DOMAIN}")

    afrobeats = _demo_event(events, "afrobeats-night-live")
    comedy_jam = _demo_event(events, "lagos-comedy-jam")
    mainland = _demo_event(events, "food-and-flow") or _demo_event(
        events, "mainland-vibes-summer"
    )
    startup = _demo_event(events, "startup-demo-evening")
    worship = _demo_event(events, "worship-under-stars")
    after_dark = _demo_event(events, "mainland-after-dark")

    # Entitlements Demo Buyer needs for ticket / VIP / check-in unlocks
    if afrobeats is not None:
        _ensure_demo_ticket(db, buyer=buyer, event=afrobeats, vip=True)
    if after_dark is not None:
        _ensure_demo_ticket(db, buyer=buyer, event=after_dark, vip=False)
    if comedy_jam is not None:
        _ensure_demo_ticket(db, buyer=buyer, event=comedy_jam, vip=False)
    if mainland is not None:
        _ensure_demo_ticket(db, buyer=buyer, event=mainland, vip=False)
    if startup is not None:
        ticket = _ensure_demo_ticket(db, buyer=buyer, event=startup, vip=False)
        if ticket is not None:
            _ensure_demo_check_in(
                db, ticket=ticket, event=startup, scanner=staff or admin
            )

    # (host_slug, title, slug, content_type, access_type, price, cover_key, event_key)
    specs: list[tuple[str, str, str, str, str, Decimal, str, str | None]] = [
        (
            "djmaze",
            "Unreleased Afrobeats DJ Set",
            "unreleased-set",
            "audio",
            "one_time_unlock",
            Decimal("5000"),
            "unreleased-set",
            "afrobeats-night-live",
        ),
        (
            "djmaze",
            "Behind the Scenes: Afrobeats Night Live",
            "bts-afrobeats",
            "video",
            "followers_only",
            Decimal("0"),
            "bts-mainland",
            "afrobeats-night-live",
        ),
        (
            "djmaze",
            "VIP Photo Gallery",
            "vip-gallery",
            "image_gallery",
            "vip_ticket_holder_only",
            Decimal("0"),
            "vip-gallery",
            "afrobeats-night-live",
        ),
        (
            "djmaze",
            "Mainland After Dark Teaser",
            "after-dark-teaser",
            "video",
            "followers_only",
            Decimal("0"),
            "bts-mainland",
            "mainland-after-dark",
        ),
        (
            "djmaze",
            "Detty Friday Ticket-holder Recap",
            "detty-friday-recap",
            "ticket_holder_recap",
            "ticket_holder_only",
            Decimal("0"),
            "vip-gallery",
            "detty-friday-live",
        ),
        (
            "lagoscomedyhub",
            "Early Access: Laugh Lagos Live",
            "comedy-early",
            "early_access",
            "ticket_holder_only",
            Decimal("0"),
            "comedy-early",
            "lagos-comedy-jam",
        ),
        (
            "lagoscomedyhub",
            "Backstage: Sunday Comedy Room",
            "backstage-comedy",
            "video",
            "invite_only",
            Decimal("0"),
            "comedy-early",
            "island-comedy-night",
        ),
        (
            "mainlandvibes",
            "Food & Culture Fest Recap",
            "recap-video",
            "ticket_holder_recap",
            "ticket_holder_only",
            Decimal("0"),
            "bts-mainland",
            "food-and-flow",
        ),
        (
            "mainlandvibes",
            "Creative Market Teaser",
            "secret-location",
            "announcement",
            "one_time_unlock",
            Decimal("3500"),
            "bts-mainland",
            "mainland-vibes-summer",
        ),
        (
            "techconnectafrica",
            "Founder Mixer Slide Deck",
            "founder-deck",
            "file_download",
            "free",
            Decimal("0"),
            "founder-deck",
            "founders-mixer-lagos",
        ),
        (
            "techconnectafrica",
            "Product Demo Night Replay",
            "product-demo-replay",
            "video",
            "checked_in_attendee_only",
            Decimal("0"),
            "founder-deck",
            "startup-demo-evening",
        ),
        (
            "techconnectafrica",
            "Product Demo Night Slide Deck",
            "product-demo-deck",
            "file_download",
            "checked_in_attendee_only",
            Decimal("0"),
            "founder-deck",
            "startup-demo-evening",
        ),
        (
            "praiseexperience",
            "Worship Night Ibadan Rehearsal",
            "worship-rehearsal",
            "video",
            "free",
            Decimal("0"),
            "worship-rehearsal",
            "worship-under-stars",
        ),
        (
            "praiseexperience",
            "Choir & Community Backstage",
            "vip-choir-backstage",
            "vip_content",
            "vip_ticket_holder_only",
            Decimal("0"),
            "worship-rehearsal",
            "praise-experience-live",
        ),
        # Admin moderation sample — not publicly listable after hide
        (
            "djmaze",
            "Admin Hidden Demo Drop",
            "admin-hidden-drop",
            "text_post",
            "free",
            Decimal("0"),
            "unreleased-set",
            None,
        ),
    ]

    seeded: dict[str, VaultItem] = {}
    for (
        host_slug,
        title,
        slug,
        content_type,
        access_type,
        price,
        cover_key,
        event_key,
    ) in specs:
        host = hosts[host_slug]
        owner = db.get(User, host.user_id)
        if owner is None:
            continue
        existing_item = db.scalar(
            select(VaultItem).where(VaultItem.host_id == host.id, VaultItem.slug == slug)
        )
        if existing_item is not None:
            seeded[slug] = existing_item
            continue

        related = _demo_event(events, event_key) if event_key else None
        # Prefer host-owned event; fall back to any host event for ticket gates
        event_id = related.id if related is not None else None
        if event_id is None and access_type in {
            "ticket_holder_only",
            "vip_ticket_holder_only",
            "checked_in_attendee_only",
        }:
            for e in events.values():
                if e.host_id == host.id:
                    event_id = e.id
                    break

        require_check_in = access_type == "checked_in_attendee_only"
        created = _safe_call(
            db,
            create_vault_item,
            db,
            user=owner,
            payload=VaultItemCreate(
                title=title,
                slug=slug,
                content_type=content_type,
                description=f"Public description for {title}.",
                preview_text=f"Preview for {title}",
                body=f"LOCKED DEMO BODY for {title} — must not leak without access.",
                cover_url=assets.vault_cover(cover_key),
                file_url=(
                    "/demo/vault/founder-deck.svg"
                    if content_type == "file_download"
                    else None
                ),
                external_url=(
                    "https://example.com/demo-secret-location"
                    if slug == "secret-location"
                    else None
                ),
                related_event_id=event_id,
                tags=["demo", content_type.replace("_", "-"), access_type],
                price=price,
                status="published",
                access=VaultAccessRuleInput(
                    access_type=access_type,
                    price=price,
                    currency="NGN",
                    required_event_id=event_id,
                    require_check_in=require_check_in,
                    access_code="DEMO-INVITE" if access_type == "invite_only" else None,
                ),
                media=[
                    VaultMediaInput(
                        url=assets.vault_cover(cover_key),
                        media_type="image",
                        label="Cover",
                        is_preview=True,
                    )
                ],
            ),
        )
        row = db.scalar(
            select(VaultItem).where(VaultItem.host_id == host.id, VaultItem.slug == slug)
        )
        if row is not None:
            seeded[slug] = row
        _ = created

    # Admin-hidden sample for /admin/vault
    hidden = seeded.get("admin-hidden-drop")
    if hidden is not None and hidden.status != "hidden_by_admin":
        apply_admin_hide(hidden, user_id=admin.id, now=_now())
        hidden.moderation_note = "Demo admin-hidden Vault drop for moderation QA"
        hidden.moderated_by_user_id = admin.id
        hidden.moderated_at = _now()
        db.commit()

    # Paid unlock + earnings: Demo Buyer buys Maze set; named fans unlock via persona context
    paid_buyer = seeded.get("unreleased-set")
    if paid_buyer is not None:
        _finalize_demo_vault_purchase(db, item=paid_buyer, buyer=buyer)

    paid_fan_item = seeded.get("secret-location")
    if paid_fan_item is not None and fan is not None:
        _finalize_demo_vault_purchase(db, item=paid_fan_item, buyer=fan)

    # Persona Vault unlocks (Amaka vault-member, Kunle VIP, etc.)
    for row in DEMO_PERSONA_CONTEXT:
        persona_user = get_user_by_email(db, str(row["email"]))
        if persona_user is None:
            continue
        for slug in list(row.get("vault_paid_slugs") or []):
            item = seeded.get(str(slug))
            if item is not None:
                _finalize_demo_vault_purchase(db, item=item, buyer=persona_user)

    # Invite unlock for Demo Buyer (Backstage Comedy Clips)
    invite_item = seeded.get("backstage-comedy")
    if invite_item is not None:
        _safe_call(
            db,
            redeem_vault_invite,
            db,
            user=buyer,
            item_id=invite_item.id,
            access_code="DEMO-INVITE",
        )

    # Refresh seeded rows after grants/purchases
    for slug in list(seeded.keys()):
        host_id = seeded[slug].host_id
        row = db.scalar(
            select(VaultItem).where(
                VaultItem.host_id == host_id, VaultItem.slug == slug
            )
        )
        if row is not None:
            seeded[slug] = row

    _seed_vault_views(db, buyer=buyer, items=seeded)

    # Ensure Maze host balance reflects vault_sale earnings path
    maze = hosts.get("djmaze")
    if maze is not None:
        get_or_create_host_balance(db, maze.id)
        db.commit()


def _ensure_persona_review(
    db: Session,
    *,
    buyer: User,
    event: Event,
    body: str,
) -> None:
    """Idempotent verified review for a checked-in persona ticket."""
    ticket = db.scalar(
        select(Ticket)
        .where(
            Ticket.event_id == event.id,
            Ticket.buyer_user_id == buyer.id,
            Ticket.status == "checked_in",
        )
        .limit(1)
    )
    if ticket is None:
        return
    if db.scalar(select(VerifiedReview).where(VerifiedReview.ticket_id == ticket.id)):
        return
    _safe_call(
        db,
        submit_review,
        db,
        user=buyer,
        payload=ReviewCreate(
            ticket_id=ticket.id,
            rating=5,
            title="Verified attendee take",
            body=body[:2000],
        ),
    )


def _seed_persona_product_context(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> dict[str, int]:
    """Wire fan personas to tickets, check-ins, reviews, and Vault for messaging QA."""
    staff = users.get(f"staff@{DEMO_EMAIL_DOMAIN}")
    admin = users.get(f"admin@{DEMO_EMAIL_DOMAIN}")
    scanner = staff or admin
    tickets_n = 0
    checkins_n = 0
    reviews_n = 0

    for row in DEMO_PERSONA_CONTEXT:
        persona = get_user_by_email(db, str(row["email"]))
        if persona is None:
            continue

        for event_key in list(row.get("upcoming") or []):
            event = events.get(str(event_key))
            if event is None:
                continue
            if _ensure_demo_ticket(db, buyer=persona, event=event, vip=False):
                tickets_n += 1

        for event_key in list(row.get("vip_events") or []):
            event = events.get(str(event_key))
            if event is None:
                continue
            if _ensure_demo_ticket(db, buyer=persona, event=event, vip=True):
                tickets_n += 1

        for event_key in list(row.get("attended") or []):
            event = events.get(str(event_key))
            if event is None:
                continue
            ticket = _ensure_demo_ticket(db, buyer=persona, event=event, vip=False)
            if ticket is None:
                continue
            tickets_n += 1
            if scanner is not None and ticket.status != "checked_in":
                before = ticket.status
                _ensure_demo_check_in(
                    db, ticket=ticket, event=event, scanner=scanner
                )
                ticket = db.get(Ticket, ticket.id) or ticket
                if before != "checked_in" and ticket.status == "checked_in":
                    checkins_n += 1

        review_key = row.get("review_event")
        review_body = row.get("review_body")
        if review_key and review_body:
            event = events.get(str(review_key))
            if event is not None:
                before = db.scalar(
                    select(func.count())
                    .select_from(VerifiedReview)
                    .where(VerifiedReview.reviewer_user_id == persona.id)
                )
                _ensure_persona_review(
                    db,
                    buyer=persona,
                    event=event,
                    body=str(review_body),
                )
                after = db.scalar(
                    select(func.count())
                    .select_from(VerifiedReview)
                    .where(VerifiedReview.reviewer_user_id == persona.id)
                )
                if (after or 0) > (before or 0):
                    reviews_n += 1

        refresh_loyalty_and_badges(db, persona)

    db.commit()
    return {
        "persona_tickets": tickets_n,
        "persona_checkins": checkins_n,
        "persona_reviews": reviews_n,
    }


def _award_demo_badges(db: Session, user: User, badge_slugs: list[str]) -> None:
    """Idempotently award named demo badges (supplements activity-based refresh)."""
    from app.passport.models import FanBadge, UserBadge

    if not badge_slugs:
        return
    badges = {
        b.slug: b
        for b in db.scalars(select(FanBadge).where(FanBadge.slug.in_(badge_slugs))).all()
    }
    existing = {
        ub.badge_id
        for ub in db.scalars(select(UserBadge).where(UserBadge.user_id == user.id)).all()
    }
    for slug in badge_slugs:
        badge = badges.get(slug)
        if badge is None or badge.id in existing:
            continue
        db.add(
            UserBadge(
                user_id=user.id,
                badge_id=badge.id,
                meta={"source": "demo_seed", "criteria_key": badge.criteria_key},
            )
        )
        existing.add(badge.id)


def _seed_passport(db: Session, buyer: User) -> None:
    """Demo Fan Passports across private / unlisted / public + directory opt-in."""
    from app.passport.models import FanPassport
    from app.passport.privacy import (
        VISIBILITY_PRIVATE,
        VISIBILITY_PUBLIC,
        VISIBILITY_UNLISTED,
    )

    visibility_map = {
        "private": VISIBILITY_PRIVATE,
        "public": VISIBILITY_PUBLIC,
        "unlisted": VISIBILITY_UNLISTED,
    }

    ensure_passport(db, buyer)
    refresh_loyalty_and_badges(db, buyer)
    buyer_pp = db.scalar(select(FanPassport).where(FanPassport.user_id == buyer.id))
    if buyer_pp:
        buyer_pp.username = "demobuyer"
        buyer_pp.display_name = buyer.full_name or "Demo Buyer"
        buyer_pp.tagline = "Private Fan Passport — nights stamped on Pàdéyá."
        buyer_pp.visibility = VISIBILITY_PRIVATE
        buyer_pp.appear_in_directory = False
        buyer_pp.hide_private_events_always = True

    # Named personas (fan1–fan8) + a few volume extras for directory/messaging coverage
    extra_passports: list[dict] = [
        {
            "email": f"fan9@{DEMO_EMAIL_DOMAIN}",
            "username": "yemidirect",
            "display_name": "Yemi Direct Link",
            "tagline": "Public Passport — share the link, not the directory.",
            "visibility": VISIBILITY_PUBLIC,
            "appear_in_directory": False,
            "city": "Lagos",
            "categories": ["Music"],
            "badge_slugs": [],
            "full_name": "Yemi Direct Link",
        },
        {
            "email": f"fan10@{DEMO_EMAIL_DOMAIN}",
            "username": "kofiul",
            "display_name": "Kofi Unlisted",
            "tagline": "Unlisted Fan Passport — direct link only.",
            "visibility": VISIBILITY_UNLISTED,
            "appear_in_directory": False,
            "city": "Lagos",
            "categories": ["Tech"],
            "badge_slugs": [],
            "full_name": "Kofi Unlisted",
        },
        {
            "email": f"fan11@{DEMO_EMAIL_DOMAIN}",
            "username": "zainabquiet",
            "display_name": "Zainab Quiet Nights",
            "tagline": "Private by choice.",
            "visibility": VISIBILITY_PRIVATE,
            "appear_in_directory": False,
            "city": "Ibadan",
            "categories": ["Worship"],
            "badge_slugs": [],
            "full_name": "Zainab Quiet Nights",
        },
        {
            "email": f"fan12@{DEMO_EMAIL_DOMAIN}",
            "username": "bodefoodie",
            "display_name": "Bode Food & Flow",
            "tagline": "Taste trails and public scene stamps on Pàdéyá.",
            "visibility": VISIBILITY_PUBLIC,
            "appear_in_directory": True,
            "city": "Lagos",
            "categories": ["Food", "Nightlife"],
            "badge_slugs": [],
            "full_name": "Bode Food & Flow",
        },
    ]

    demo_passports: list[dict] = []
    for persona in DEMO_FAN_PERSONAS:
        demo_passports.append(
            {
                **persona,
                "visibility": visibility_map.get(
                    str(persona["visibility"]), VISIBILITY_PRIVATE
                ),
            }
        )
    demo_passports.extend(extra_passports)

    for spec in demo_passports:
        fan = get_user_by_email(db, spec["email"])
        if fan is None:
            fan = _ensure_user(
                db,
                email=spec["email"],
                full_name=str(spec.get("full_name") or spec["display_name"]),
                role="buyer",
            )
        else:
            fan.full_name = str(spec.get("full_name") or spec["display_name"])
        ensure_passport(db, fan)
        refresh_loyalty_and_badges(db, fan)
        pp = db.scalar(select(FanPassport).where(FanPassport.user_id == fan.id))
        if pp is None:
            continue
        pp.username = spec["username"]
        pp.display_name = spec["display_name"]
        pp.tagline = spec["tagline"]
        city = spec.get("city") or "Lagos"
        # City is public-scene metadata only — never store login email on Passport
        pp.bio = f"Based in {city}. Demo Fan Passport on Pàdéyá."
        pp.visibility = spec["visibility"]
        pp.appear_in_directory = bool(spec["appear_in_directory"])
        pp.favorite_categories = list(spec["categories"])
        pp.avatar_url = assets.fan_avatar(str(spec["username"]))
        pp.show_attended_events = True
        pp.show_badges = True
        pp.show_followed_hosts = True
        pp.show_reviews = True
        pp.show_vault_unlocks = True
        pp.show_city_category_stats = True
        pp.hide_private_events_always = True
        if pp.visibility != VISIBILITY_PUBLIC:
            pp.appear_in_directory = False
        _award_demo_badges(db, fan, list(spec.get("badge_slugs") or []))

    db.commit()


def _seed_messaging(
    db: Session,
    *,
    users: dict[str, User],
    hosts: dict[str, Host],
    events: dict[str, Event],
) -> dict[str, int]:
    """Rich privacy-safe messaging demo (idempotent)."""
    from app.demo.messaging_seed import seed_messaging_demo

    return seed_messaging_demo(db, users=users, hosts=hosts, events=events)


def _seed_memories(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> dict:
    """Rich Event Memories albums (idempotent). See app.demo.memories_seed."""
    from app.demo.memories_seed import seed_demo_memories

    return seed_demo_memories(db, users=users, events=events)

def _seed_analytics(db: Session, events: dict[str, Event]) -> None:
    """Seed 90 days of funnel analytics (raw stream + rollups) for demo dashboards."""
    seed_event_analytics_traffic(db, events=events)


def _seed_sponsorships(db: Session, hosts: dict[str, Host]) -> int:
    """Seed demo sponsorship settings, slots, and minimal marketplace rows."""
    sponsors_spec = [
        ("Acme Events", "acme-events", "ada@acme.demo.padeye.test"),
        ("Greenline Media", "greenline-media", "leo@greenline.demo.padeye.test"),
        ("Nova Sips", "nova-sips", "nova@sips.demo.padeye.test"),
    ]
    sponsor_rows: list[Sponsor] = []
    for name, key, email in sponsors_spec:
        row = db.scalar(select(Sponsor).where(Sponsor.contact_email == email))
        if row is None:
            row = Sponsor(
                company_name=name,
                contact_name=name.split()[0],
                contact_email=email,
                logo_url=assets.sponsor_logo(key),
                status="active",
            )
            db.add(row)
            db.flush()
        sponsor_rows.append(row)

    slot_types = [
        ("logo_event_page", "Logo on event page"),
        ("logo_ticket_email", "Logo on ticket email"),
        ("banner_legacy_page", "Banner on Legacy Page"),
        ("booth_at_event", "Booth at event"),
        ("sponsored_vault_content", "Sponsored Vault drop"),
        ("sponsored_memory_page", "Sponsored Event Memory page"),
    ]
    host_specs = {h["slug"]: h for h in DEMO_HOSTS}
    created = 0
    for slug, host in hosts.items():
        owner = db.get(User, host.user_id)
        if owner is None:
            continue
        sponsor_ready = bool(host_specs.get(slug, {}).get("sponsor_ready", True))
        ensure_demo_host_sponsorship_settings(
            db,
            host=host,
            accepting_sponsors=sponsor_ready,
            pitch=(
                f"Partner with {host.display_name} on Pàdéyá." if sponsor_ready else None
            ),
            contact_email=owner.email if sponsor_ready else None,
        )
        if not sponsor_ready:
            continue
        chosen = slot_types if slug == "djmaze" else slot_types[:3]
        for stype, title in chosen:
            before = db.scalar(
                select(SponsorshipSlot.id).where(
                    SponsorshipSlot.host_id == host.id,
                    SponsorshipSlot.title == title,
                )
            )
            slot = create_demo_sponsorship_slot(
                db,
                host=host,
                slot_type=stype,
                title=title,
                description=f"{title} for {host.display_name} on Pàdéyá demo.",
                price=Decimal("150000"),
                status="published",
                moderation_status="approved",
            )
            if slot is not None and before is None:
                created += 1
        if slug == "djmaze":
            before_disabled = db.scalar(
                select(SponsorshipSlot.id).where(
                    SponsorshipSlot.host_id == host.id,
                    SponsorshipSlot.title == "Disabled Booth Listing",
                )
            )
            slot_dis = create_demo_sponsorship_slot(
                db,
                host=host,
                slot_type="booth_at_event",
                title="Disabled Booth Listing",
                description="Flagged demo listing for admin testing on Pàdéyá.",
                price=Decimal("500000"),
                status="draft",
                moderation_status="flagged",
            )
            if slot_dis is not None:
                slot_dis.status = "disabled"
                slot_dis.moderation_status = "flagged"
                slot_dis.moderation_note = "Demo flagged listing"
                if before_disabled is None:
                    created += 1
            slot = db.scalar(
                select(SponsorshipSlot).where(
                    SponsorshipSlot.host_id == host.id,
                    SponsorshipSlot.title == "Logo on event page",
                )
            )
            if slot and sponsor_rows:
                if not db.scalar(
                    select(SponsorshipInquiry).where(
                        SponsorshipInquiry.slot_id == slot.id
                    )
                ):
                    db.add(
                        SponsorshipInquiry(
                            slot_id=slot.id,
                            sponsor_id=sponsor_rows[0].id,
                            company_name=sponsor_rows[0].company_name,
                            contact_name=sponsor_rows[0].contact_name,
                            contact_email=sponsor_rows[0].contact_email,
                            message="We want to sponsor Afrobeats Night Live on Pàdéyá.",
                            status="new",
                        )
                    )
                if not db.scalar(
                    select(SponsorshipPlacement).where(
                        SponsorshipPlacement.slot_id == slot.id
                    )
                ):
                    db.add(
                        SponsorshipPlacement(
                            slot_id=slot.id,
                            sponsor_id=sponsor_rows[0].id,
                            status="active",
                            asset_url=sponsor_rows[0].logo_url,
                        )
                    )
    db.flush()
    published = int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipSlot)
            .where(
                SponsorshipSlot.host_id.in_([h.id for h in hosts.values()]),
                SponsorshipSlot.status == "published",
            )
        )
        or 0
    )
    return published if published >= created else created


def _seed_support_cases(db: Session) -> None:
    cases = [
        ("ticket-missing", "Ticket not received", "ticketing", "open", "buyer"),
        ("payment-no-ticket", "Payment confirmed but ticket missing", "payments", "pending", "buyer"),
        ("refund-help", "Refund request", "refunds", "open", "buyer"),
        ("vault-access", "Vault access issue", "vault", "open", "buyer"),
        ("review-dispute", "Review dispute", "reviews", "escalated", "host"),
        ("event-postponed", "Event postponed complaint", "events", "open", "buyer"),
        ("payout-question", "Payout question from host", "payouts", "resolved", "host"),
    ]
    for key, subject, category, status, who in cases:
        if db.scalar(select(DemoSupportCase).where(DemoSupportCase.case_key == key)):
            continue
        requester = (
            f"buyer@{DEMO_EMAIL_DOMAIN}"
            if who == "buyer"
            else f"host@{DEMO_EMAIL_DOMAIN}"
        )
        db.add(
            DemoSupportCase(
                case_key=key,
                subject=subject,
                category=category,
                status=status,
                requester_email=requester,
                assignee_email=f"support@{DEMO_EMAIL_DOMAIN}",
                body=(
                    f"Demo support case: {subject}. "
                    "Local Pàdéyá demo only — no real emails sent."
                ),
                internal_notes="Internal note: demo escalation path for support_agent.",
                escalation="finance" if category in {"refunds", "payouts"} else None,
                meta={"messages": [{"from": "support", "text": "We're looking into this."}]},
            )
        )
    db.commit()


def _seed_merch(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> dict[str, int]:
    """Seed rich event merch catalog + persona pickups (local demo)."""
    from app.demo.merch_seed import seed_demo_merch

    return seed_demo_merch(db, users=users, events=events)


def _demo_partial(db: Session) -> bool:
    """True when demo-scoped rows exist without a completion marker."""
    if _seeded(db):
        return False
    return (
        db.scalar(
            select(User.id)
            .where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
            .limit(1)
        )
        is not None
    )


def _demo_needs_sponsorship_repair(db: Session, hosts: dict[str, Host]) -> bool:
    published = int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipSlot)
            .where(
                SponsorshipSlot.host_id.in_([h.id for h in hosts.values()]),
                SponsorshipSlot.status == "published",
            )
        )
        or 0
    )
    return published < 8


def repair_demo_data(db: Session) -> dict[str, Any]:
    """Complete missing demo rows after a partial seed — demo-scoped only."""
    assert_demo_ops_allowed(operation="demo seed repair")
    log_seed_phase("starting repair", script="demo")

    log_seed_phase("starting roles/permissions", script="demo")
    seed_roles_and_permissions(db)
    log_seed_phase("completed roles/permissions", script="demo")

    log_seed_phase("starting users", script="demo")
    users: dict[str, User] = {}
    for acct in [*DEMO_ACCOUNTS, *EXTRA_HOST_ACCOUNTS, *DEMO_TEAM_ACCOUNTS]:
        users[acct["email"]] = _ensure_user(
            db,
            email=acct["email"],
            full_name=acct["full_name"],
            role=acct["role"],
        )
    db.flush()

    log_seed_phase("starting hosts", script="demo")
    hosts = _ensure_hosts(db, users)
    db.flush()

    log_seed_phase("starting events", script="demo")
    categories = _ensure_categories(db)
    events = _ensure_events(db, hosts, categories)
    db.flush()

    log_seed_phase("starting taxonomy", script="demo")
    apply_demo_taxonomy(db)

    log_seed_phase("starting sponsorship slots", script="demo")
    slot_count = _seed_sponsorships(db, hosts)

    log_seed_phase("starting fans", script="demo")
    fan_users = _ensure_demo_fan_users(db)
    users.update(fan_users)
    _seed_passport(db, users[f"buyer@{DEMO_EMAIL_DOMAIN}"])

    _mark(db, "seed", "complete", meta={"version": 1, "repaired": True})
    db.commit()

    log_seed_phase("completed seed", script="demo")
    return {
        "status": "repaired",
        "reset": False,
        "repair": True,
        "users": len(users),
        "hosts": len(hosts),
        "events": len(events),
        "fans": len(fan_users),
        "sponsorship_slots_published": slot_count,
        "password": DEMO_PASSWORD,
    }


def seed_demo_data(
    db: Session, *, reset: bool = False, repair: bool = False
) -> dict[str, Any]:
    """Seed rich local demo content. Idempotent unless reset=True."""
    from app.placements.demo_seed import apply_demo_featured_placements

    assert_demo_ops_allowed(operation="demo seed")

    if repair:
        return repair_demo_data(db)

    if reset:
        reset_demo_data(db)

    if _demo_partial(db):
        return repair_demo_data(db)

    if _seeded(db) and not reset:
        # Refresh Event Studio + idempotent passport/messaging top-ups.
        # Do NOT re-run commerce (orders/tickets) — that would duplicate sales.
        seed_fan_badges(db)
        categories = _ensure_categories(db)
        users: dict[str, User] = {}
        for acct in [*DEMO_ACCOUNTS, *EXTRA_HOST_ACCOUNTS, *DEMO_TEAM_ACCOUNTS]:
            users[acct["email"]] = _ensure_user(
                db,
                email=acct["email"],
                full_name=acct["full_name"],
                role=acct["role"],
            )
        hosts = _ensure_hosts(db, users)
        events = _ensure_events(db, hosts, categories)
        db.commit()
        apply_demo_taxonomy(db)
        placement_counts = apply_demo_featured_placements(db)
        _force_legacy_tiers(db, hosts)
        _seed_legacy_studio(db, hosts)
        log_seed_phase("starting sponsorship slots", script="demo")
        slot_count = _seed_sponsorships(db, hosts)
        fan_users = _ensure_demo_fan_users(db)
        users.update(fan_users)
        _seed_passport(db, users[f"buyer@{DEMO_EMAIL_DOMAIN}"])
        _seed_vault(db, hosts, users, events)
        persona_ctx = _seed_persona_product_context(
            db, users=users, events=events
        )
        _seed_passport(db, users[f"buyer@{DEMO_EMAIL_DOMAIN}"])
        messaging_counts = _seed_messaging(
            db, users=users, hosts=hosts, events=events
        )
        for i in range(1, 21):
            email = f"fan{i}@{DEMO_EMAIL_DOMAIN}"
            fan_row = get_user_by_email(db, email)
            if fan_row is not None:
                users[email] = fan_row
        from app.demo.ambassadors_seed import seed_demo_open_ambassadors
        from app.demo.fan_connect_seed import seed_fan_connect_demo
        from app.demo.team_seed import seed_host_team_demo

        fan_connect_counts = seed_fan_connect_demo(
            db, hosts=hosts, events=events
        )
        team_counts = seed_host_team_demo(
            db, users=users, hosts=hosts, events=events
        )
        merch_counts = _seed_merch(db, users=users, events=events)
        open_amb_counts = seed_demo_open_ambassadors(
            db, users=users, hosts=hosts, events=events
        )
        memories_summary = _seed_memories(db, users=users, events=events)
        db.commit()
        return {
            "status": "already_seeded",
            "reset": False,
            "events_refreshed": len(events),
            "sponsorship_slots_published": slot_count,
            "message_threads_created": messaging_counts.get("threads", 0),
            "messages_created": messaging_counts.get("messages", 0),
            "message_attachments": messaging_counts.get("attachments", 0),
            "merch_products_created": merch_counts.get("products", 0),
            "merch_fulfillments_created": merch_counts.get("fulfillments", 0),
            "memories": memories_summary,
            **fan_connect_counts,
            **team_counts,
            **open_amb_counts,
            **persona_ctx,
            **placement_counts,
        }

    log_seed_phase("starting roles/permissions", script="demo")
    seed_roles_and_permissions(db)
    log_seed_phase("completed roles/permissions", script="demo")
    seed_legacy_tiers(db)
    seed_fan_badges(db)
    categories = _ensure_categories(db)

    log_seed_phase("starting users", script="demo")
    users: dict[str, User] = {}
    for acct in [*DEMO_ACCOUNTS, *EXTRA_HOST_ACCOUNTS, *DEMO_TEAM_ACCOUNTS]:
        users[acct["email"]] = _ensure_user(
            db,
            email=acct["email"],
            full_name=acct["full_name"],
            role=acct["role"],
        )
    db.commit()

    log_seed_phase("starting hosts", script="demo")
    hosts = _ensure_hosts(db, users)
    db.commit()
    log_seed_phase("starting events", script="demo")
    events = _ensure_events(db, hosts, categories)
    db.commit()
    apply_demo_taxonomy(db)
    placement_counts = apply_demo_featured_placements(db)

    # Promos/ambassadors before commerce so checkout attribution works
    _seed_promos_ambassadors(db, hosts)

    fans = _seed_commerce(db, users=users, events=events)
    # Persona merch flows (abandoned carts, reviews, QR, shipping) need fan1–fan20.
    for fan in fans:
        users[fan.email] = fan
    for key in list(events.keys()):
        events[key] = db.get(Event, events[key].id)  # type: ignore[index]

    review_count = _seed_reviews(db, events)
    _seed_ambassador_sales(db, hosts)
    pool = [users[f"buyer@{DEMO_EMAIL_DOMAIN}"], *fans]
    _seed_crm(db, hosts, pool)
    _seed_finance(db, users, hosts)
    # Vault before merch so Vault-exclusive catalog + unlocked purchases can seed.
    _seed_vault(db, hosts, users, events)
    merch_counts = _seed_merch(db, users=users, events=events)
    persona_ctx = _seed_persona_product_context(
        db, users=users, events=events
    )
    _seed_passport(db, users[f"buyer@{DEMO_EMAIL_DOMAIN}"])
    messaging_counts = _seed_messaging(db, users=users, hosts=hosts, events=events)
    from app.demo.fan_connect_seed import seed_fan_connect_demo
    from app.demo.team_seed import seed_host_team_demo

    fan_connect_counts = seed_fan_connect_demo(
        db, hosts=hosts, events=events
    )
    team_counts = seed_host_team_demo(
        db, users=users, hosts=hosts, events=events
    )
    from app.demo.ambassadors_seed import seed_demo_open_ambassadors

    open_amb_counts = seed_demo_open_ambassadors(
        db, users=users, hosts=hosts, events=events
    )
    memories_summary = _seed_memories(db, users=users, events=events)
    _seed_analytics(db, events)
    log_seed_phase("starting sponsorship slots", script="demo")
    slot_count = _seed_sponsorships(db, hosts)
    _seed_support_cases(db)
    _force_legacy_tiers(db, hosts)
    _seed_legacy_studio(db, hosts)

    _mark(db, "seed", "complete", meta={"version": 1})
    db.commit()

    log_seed_phase("completed seed", script="demo")

    tickets = list(
        db.scalars(
            select(Ticket)
            .join(Event)
            .where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
        ).all()
    )
    return {
        "status": "seeded",
        "reset": reset,
        "users": len(users) + len(fans),
        "hosts": len(hosts),
        "events": len(events),
        "sponsorship_slots_published": slot_count,
        **persona_ctx,
        "tickets": len(tickets),
        "checked_in": sum(1 for t in tickets if t.status == "checked_in"),
        "reviews": review_count,
        "message_threads": messaging_counts.get("threads", 0),
        "messages": messaging_counts.get("messages", 0),
        "message_reports": messaging_counts.get("reports", 0),
        "message_attachments": messaging_counts.get("attachments", 0),
        "merch_products_created": merch_counts.get("products", 0),
        "merch_fulfillments_created": merch_counts.get("fulfillments", 0),
        "memories": memories_summary,
        "password": DEMO_PASSWORD,
        **fan_connect_counts,
        **team_counts,
        **open_amb_counts,
        **placement_counts,
    }
