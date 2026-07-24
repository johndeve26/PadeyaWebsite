"""Per-sponsor demo events, hosts, slots, and public placements for rich profiles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo import assets
from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_EVENT_SLUG_PREFIX
from app.demo.seed import _ensure_user, _mark
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile, HostVerification
from app.sponsorships.models import (
    Sponsor,
    SponsorCampaign,
    SponsorshipDeal,
    SponsorshipDeliverable,
    SponsorshipInquiry,
    SponsorshipInvoice,
    SponsorshipPlacement,
    SponsorshipSlot,
)
from app.sponsorships.service import get_or_create_settings
from app.users.models import User
from app.users.service import get_role_by_name

SPONSOR_EVENT_MARKER = "sponsor_demo_event_pack"
SPONSOR_PACK_EMAIL_DOMAIN = "demo.padeya.test"


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)


def _pack_host_user(db: Session, *, email: str, full_name: str) -> User:
    user = _ensure_user(db, email=email, full_name=full_name, role="host")
    host_role = get_role_by_name(db, "host")
    if host_role and host_role not in user.roles:
        user.roles.append(host_role)
    return user


@dataclass(frozen=True)
class PackHostSpec:
    slug: str
    display_name: str
    city: str
    category_slug: str


@dataclass(frozen=True)
class PackEventSpec:
    key: str
    title: str
    host_slug: str
    category_slug: str
    placement: str  # active | completed | planned | none
    slot_type: str = "booth_space"


# Hosts referenced across sponsor packs (fictional brands for QA only).
PACK_HOSTS: list[PackHostSpec] = [
    PackHostSpec("spn-neon-lagos-nightlife", "Lagos Nightlife Collective", "Lagos", "nightlife"),
    PackHostSpec("spn-neon-beachside", "Beachside Events NG", "Lagos", "beach"),
    PackHostSpec("spn-neon-campus-rhythm", "Campus Rhythm House", "Lagos", "music"),
    PackHostSpec("spn-kora-creator-circle", "Creator Circle Lagos", "Lagos", "creator"),
    PackHostSpec("spn-kora-founders-mixer", "Founders Mixer Africa", "Lagos", "business"),
    PackHostSpec("spn-kora-tech-lounge", "Tech Lounge NG", "Lagos", "tech"),
    PackHostSpec("spn-jollof-tastefest", "TasteFest Lagos", "Lagos", "food"),
    PackHostSpec("spn-jollof-family-fun", "Family Fun Events", "Lagos", "family"),
    PackHostSpec("spn-jollof-comedy-yard", "Comedy Yard NG", "Lagos", "comedy"),
    PackHostSpec("spn-campus-connect", "Campus Connect Events", "Lagos", "campus"),
    PackHostSpec("spn-campus-youth-vibes", "Youth Vibes NG", "Ibadan", "youth"),
    PackHostSpec("spn-campus-student-awards", "Student Awards Africa", "Lagos", "campus"),
    PackHostSpec("spn-nova-fashion-house", "Fashion House Lagos", "Lagos", "fashion"),
    PackHostSpec("spn-nova-beauty-club", "Beauty Creators Club", "Lagos", "beauty"),
    PackHostSpec("spn-nova-lifestyle-brunch", "Lifestyle Brunch NG", "Lagos", "lifestyle"),
    PackHostSpec("spn-pulse-stage", "Pulse Stage Events", "Lagos", "media"),
    PackHostSpec("spn-pulse-creator-awards", "Creator Awards NG", "Lagos", "music"),
    PackHostSpec("spn-pulse-culture-fest", "Culture Fest Africa", "Abuja", "festival"),
]

SPONSOR_EVENT_PACKS: dict[str, list[PackEventSpec]] = {
    "neonpalm-drinks": [
        PackEventSpec("neon-nights-lekki", "Neon Nights at Lekki Beach", "spn-neon-lagos-nightlife", "nightlife", "active", "booth_space"),
        PackEventSpec("mainland-afterdark", "Mainland Afterdark Festival", "spn-neon-lagos-nightlife", "nightlife", "completed", "stage_mention"),
        PackEventSpec("detty-rooftop-jam", "Detty December Rooftop Jam", "spn-neon-beachside", "beach", "completed", "product_sampling"),
        PackEventSpec("campus-glow-party", "Campus Glow Party", "spn-neon-campus-rhythm", "music", "completed", "social_post"),
        PackEventSpec("island-soundwave", "Island Soundwave", "spn-neon-beachside", "music", "active", "logo_placement"),
    ],
    "korawave-pay": [
        PackEventSpec("creator-economy-mixer", "Creator Economy Mixer Lagos", "spn-kora-creator-circle", "creator", "active", "booth_space"),
        PackEventSpec("startup-founders-night", "Startup Founders Night", "spn-kora-founders-mixer", "business", "completed", "logo_placement"),
        PackEventSpec("tech-talent-social", "Tech Talent Social", "spn-kora-tech-lounge", "tech", "completed", "stage_mention"),
        PackEventSpec("business-builders-brunch", "Business Builders Brunch", "spn-kora-founders-mixer", "business", "completed", "email_feature"),
        PackEventSpec("digital-payments-meetup", "Digital Payments Meetup", "spn-kora-tech-lounge", "tech", "completed", "social_post"),
    ],
    "jollof-republic": [
        PackEventSpec("jollof-comedy-night", "Jollof & Comedy Night", "spn-jollof-comedy-yard", "comedy", "planned", "booth_space"),
        PackEventSpec("family-picnic-lagos", "Family Picnic Lagos", "spn-jollof-family-fun", "family", "planned", "product_sampling"),
        PackEventSpec("food-truck-festival", "Food Truck Festival", "spn-jollof-tastefest", "food", "none", "banner_ad"),
        PackEventSpec("outdoor-movie-meals", "Outdoor Movie & Meals", "spn-jollof-family-fun", "family", "none", "booth_space"),
        PackEventSpec("sunday-vibes-market", "Sunday Vibes Market", "spn-jollof-tastefest", "food", "planned", "social_post"),
    ],
    "campuswave": [
        PackEventSpec("freshers-welcome-fest", "Freshers Welcome Fest", "spn-campus-connect", "campus", "planned", "booth_space"),
        PackEventSpec("campus-awards-night", "Campus Awards Night", "spn-campus-student-awards", "campus", "none", "stage_mention"),
        PackEventSpec("student-creator-fair", "Student Creator Fair", "spn-campus-connect", "campus", "planned", "banner_ad"),
        PackEventSpec("youth-sound-clash", "Youth Sound Clash", "spn-campus-youth-vibes", "youth", "none", "social_post"),
        PackEventSpec("final-year-hangout", "Final Year Hangout", "spn-campus-youth-vibes", "campus", "planned", "product_sampling"),
    ],
    "novaskin-beauty": [
        PackEventSpec("glow-night-popup", "Glow Night Pop-up", "spn-nova-beauty-club", "beauty", "active", "product_sampling"),
        PackEventSpec("beauty-creator-brunch", "Beauty Creator Brunch", "spn-nova-lifestyle-brunch", "lifestyle", "completed", "banner_ad"),
        PackEventSpec("fashion-skin-showcase", "Fashion & Skin Showcase", "spn-nova-fashion-house", "fashion", "completed", "logo_placement"),
        PackEventSpec("women-lifestyle-mixer", "Women in Lifestyle Mixer", "spn-nova-lifestyle-brunch", "lifestyle", "completed", "social_post"),
        PackEventSpec("soft-glam-rooftop", "Soft Glam Rooftop Social", "spn-nova-fashion-house", "fashion", "active", "merch_collab"),
    ],
    "pulseframe-media": [
        PackEventSpec("creator-awards-recap", "Creator Awards Recap", "spn-pulse-creator-awards", "media", "completed", "custom"),
        PackEventSpec("live-concert-coverage", "Live Concert Coverage Night", "spn-pulse-stage", "music", "completed", "social_post"),
        PackEventSpec("business-summit-lounge", "Business Summit Media Lounge", "spn-pulse-stage", "business", "completed", "email_feature"),
        PackEventSpec("fashion-week-interviews", "Fashion Week Interviews", "spn-pulse-culture-fest", "fashion", "completed", "logo_placement"),
        PackEventSpec("culture-fest-doc-booth", "Culture Fest Documentary Booth", "spn-pulse-culture-fest", "festival", "completed", "custom"),
    ],
}

SPONSOR_DELIVERABLE_PACKS: dict[str, list[tuple[str, str]]] = {
    "neonpalm-drinks": [
        ("booth_space", "completed"),
        ("stage_mention", "approved"),
        ("product_sampling", "submitted"),
        ("social_post", "completed"),
        ("logo_placement", "pending"),
    ],
    "korawave-pay": [
        ("booth_space", "completed"),
        ("logo_placement", "completed"),
        ("email_feature", "submitted"),
        ("stage_mention", "approved"),
        ("social_post", "pending"),
    ],
    "jollof-republic": [
        ("booth_space", "pending"),
        ("product_sampling", "in_progress"),
        ("banner_ad", "pending"),
        ("social_post", "pending"),
    ],
    "campuswave": [
        ("booth_space", "pending"),
        ("banner_ad", "pending"),
        ("social_post", "pending"),
    ],
    "novaskin-beauty": [
        ("product_sampling", "completed"),
        ("banner_ad", "submitted"),
        ("social_post", "rejected"),
        ("merch_collab", "pending"),
        ("logo_placement", "approved"),
    ],
    "pulseframe-media": [
        ("custom", "completed"),
        ("social_post", "completed"),
        ("email_feature", "completed"),
        ("logo_placement", "completed"),
        ("custom", "completed"),
    ],
}


def _admin_user(db: Session) -> User | None:
    return db.scalar(select(User).where(User.email == f"admin@{DEMO_EMAIL_DOMAIN}"))


def ensure_sponsor_portfolio_catalog(
    db: Session,
) -> tuple[dict[str, Host], dict[str, Event], list[SponsorshipSlot]]:
    """Create fictional hosts, five events per sponsor, and published slots."""
    admin = _admin_user(db)
    categories = {c.slug: c for c in db.scalars(select(EventCategory)).all()}
    hosts: dict[str, Host] = {}
    events: dict[str, Event] = {}
    now = _now()

    for hspec in PACK_HOSTS:
        email = f"{hspec.slug}@{SPONSOR_PACK_EMAIL_DOMAIN}"
        owner = _pack_host_user(db, email=email, full_name=hspec.display_name)
        host = db.scalar(select(Host).where(Host.slug == hspec.slug))
        if host is None:
            host = Host(
                user_id=owner.id,
                display_name=hspec.display_name,
                slug=hspec.slug,
                status="active",
            )
            db.add(host)
            db.flush()
            db.add(
                HostProfile(
                    host_id=host.id,
                    bio=f"{hspec.display_name} — fictional Pàdéyá demo host for sponsor QA.",
                    city=hspec.city,
                    state="Lagos" if hspec.city == "Lagos" else "Oyo",
                    country="Nigeria",
                    avatar_url=assets.host_avatar("djmaze"),
                    cover_url=assets.host_cover("djmaze"),
                )
            )
        else:
            host.display_name = hspec.display_name
            host.status = "active"
        if admin and not db.scalar(
            select(HostVerification.id).where(
                HostVerification.host_id == host.id,
                HostVerification.status == "verified",
            )
        ):
            db.add(
                HostVerification(
                    host_id=host.id,
                    status="verified",
                    notes="Demo sponsor-pack host",
                    reviewed_by=admin.id,
                    reviewed_at=now,
                )
            )
        settings = get_or_create_settings(db, host.id)
        settings.accepting_sponsors = True
        settings.pitch = f"Partner with {hspec.display_name} on Pàdéyá."
        _mark(db, SPONSOR_EVENT_MARKER, hspec.slug, host.id)
        hosts[hspec.slug] = host

    slot_rows: list[SponsorshipSlot] = []
    from app.demo.sponsor_demo_seed import SPONSOR_SPECS

    for spec in SPONSOR_SPECS:
        pack = SPONSOR_EVENT_PACKS.get(spec.slug, [])
        for i, evspec in enumerate(pack):
            host = hosts.get(evspec.host_slug)
            if host is None:
                continue
            slug = f"{DEMO_EVENT_SLUG_PREFIX}spn-{spec.slug}-{evspec.key}"
            cat = categories.get(evspec.category_slug)
            start = now + timedelta(days=14 + i * 9)
            if evspec.placement == "completed":
                start = now - timedelta(days=30 + i * 5)
            event = db.scalar(select(Event).where(Event.slug == slug))
            if event is None:
                event = Event(
                    title=evspec.title,
                    slug=slug,
                    description=f"{evspec.title} — fictional demo event for {spec.company_name}.",
                    short_tagline=evspec.title,
                    vibe="Demo",
                    event_type="public",
                    visibility="listed",
                    status="published",
                    category_id=cat.id if cat else None,
                    host_id=host.id,
                    start_datetime=start,
                    end_datetime=start + timedelta(hours=5),
                    doors_open_datetime=start - timedelta(minutes=30),
                    timezone="Africa/Lagos",
                    venue_name=f"{evspec.title} Venue",
                    address="12 Admiralty Way",
                    city=host.profile.city if host.profile else "Lagos",
                    state="Lagos",
                    country="Nigeria",
                    location_visibility="full_public",
                )
                db.add(event)
                db.flush()
            else:
                event.title = evspec.title
                event.status = "published"
                event.visibility = "listed"
                event.host_id = host.id
            events[f"{spec.slug}:{evspec.key}"] = event
            _mark(db, SPONSOR_EVENT_MARKER, slug, event.id)

            slot_title = f"{spec.company_name} · {evspec.title}"
            slot = db.scalar(
                select(SponsorshipSlot).where(
                    SponsorshipSlot.host_id == host.id,
                    SponsorshipSlot.title == slot_title,
                )
            )
            if slot is None:
                slot = SponsorshipSlot(
                    host_id=host.id,
                    event_id=event.id,
                    slot_type=evspec.slot_type,
                    title=slot_title,
                    description=f"Demo slot for {evspec.title}.",
                    price=Decimal("750000") + Decimal(i * 100000),
                    status="published",
                    moderation_status="approved",
                )
                db.add(slot)
                db.flush()
            else:
                slot.event_id = event.id
                slot.status = "published"
            slot_rows.append(slot)

    db.flush()
    return hosts, events, slot_rows


def _deal_title(sponsor_slug: str, event_key: str) -> str:
    return f"Demo deal · {sponsor_slug} · {event_key}"


def _upsert_deliverables(
    db: Session,
    *,
    deal: SponsorshipDeal,
    pack: list[tuple[str, str]],
) -> None:
    existing = {
        row.deliverable_type: row
        for row in db.scalars(
            select(SponsorshipDeliverable).where(
                SponsorshipDeliverable.deal_id == deal.id
            )
        )
    }
    for idx, (dtype, status) in enumerate(pack):
        title = dtype.replace("_", " ").title()
        row = existing.get(dtype)
        if row is None:
            row = SponsorshipDeliverable(
                deal_id=deal.id,
                deliverable_type=dtype,
                title=title,
                status=status,
            )
            db.add(row)
        else:
            row.status = status
        if status == "rejected":
            row.rejection_reason = "Demo revision requested."
        if status in {"submitted", "completed", "approved"}:
            row.submitted_at = _now() - timedelta(days=2)
        if status == "completed":
            row.approved_at = _now() - timedelta(days=1)


def _sync_demo_deal_for_public_profile(
    db: Session,
    *,
    deal: SponsorshipDeal,
    sponsor: Sponsor,
    spec_slug: str,
    placement_mode: str,
    slot: SponsorshipSlot,
    inq_id: uuid.UUID | None,
    event: Event,
    is_public_verified: bool,
    deliverable_pack: list[tuple[str, str]],
    pack_index: int,
) -> None:
    """Idempotent: align placement/deal status for public profile visibility."""
    from app.demo.sponsor_demo_seed import (
        _apply_demo_paid,
        _demo_paystack_ref,
        _invoice_number,
    )

    if placement_mode == "none":
        return
    if not is_public_verified and placement_mode in {"active", "completed"}:
        placement_mode = "planned"

    placement = (
        db.get(SponsorshipPlacement, deal.placement_id)
        if deal.placement_id
        else None
    )
    if placement is None:
        placement = SponsorshipPlacement(
            slot_id=slot.id,
            sponsor_id=sponsor.id,
            inquiry_id=inq_id,
            status="planned",
            starts_at=event.start_datetime,
            ends_at=event.end_datetime,
        )
        db.add(placement)
        db.flush()
        deal.placement_id = placement.id

    if placement_mode == "active":
        placement.status = "active"
        if deal.status in ("proposed", "invoice_pending", "payment_pending", "draft"):
            deal.status = "invoice_pending"
            inv = db.scalar(
                select(SponsorshipInvoice).where(SponsorshipInvoice.deal_id == deal.id)
            )
            if inv is None:
                inv = SponsorshipInvoice(
                    deal_id=deal.id,
                    sponsor_id=sponsor.id,
                    host_id=deal.host_id,
                    invoice_number=_invoice_number(),
                    amount=deal.amount,
                    status="issued",
                    paystack_reference=_demo_paystack_ref(spec_slug, f"R{pack_index}"),
                )
                db.add(inv)
                db.flush()
            _apply_demo_paid(db, deal=deal, invoice=inv, slug=spec_slug)
    elif placement_mode == "completed":
        placement.status = "completed"
        deal.status = "completed"
        inv = db.scalar(
            select(SponsorshipInvoice).where(SponsorshipInvoice.deal_id == deal.id)
        )
        if inv is None:
            inv = SponsorshipInvoice(
                deal_id=deal.id,
                sponsor_id=sponsor.id,
                host_id=deal.host_id,
                invoice_number=_invoice_number(),
                amount=deal.amount,
                status="paid",
                paystack_reference=_demo_paystack_ref(spec_slug, f"C{pack_index}"),
                paid_at=_now() - timedelta(days=20),
            )
            db.add(inv)
            db.flush()
        else:
            inv.status = "paid"
        _apply_demo_paid(db, deal=deal, invoice=inv, slug=spec_slug)
        deal.status = "completed"
        placement.status = "completed"
    else:
        placement.status = "planned"
        deal.status = "proposed"

    if deliverable_pack and placement_mode in {"active", "completed"}:
        n = len(deliverable_pack)
        slice_pack = [
            deliverable_pack[pack_index % n],
            deliverable_pack[(pack_index + 1) % n],
        ]
        if n > 2:
            slice_pack.append(deliverable_pack[(pack_index + 2) % n])
        _upsert_deliverables(db, deal=deal, pack=slice_pack)


def seed_sponsor_portfolio(
    db: Session,
    *,
    spec_slug: str,
    company_name: str,
    sponsor: Sponsor,
    owner: User,
    campaigns: dict[str, SponsorCampaign],
    pack_hosts: dict[str, Host],
    pack_events: dict[str, Event],
    pack_slots: list[SponsorshipSlot],
) -> None:
    """Placements, deals, inquiries, and saved items for one sponsor pack."""
    from app.demo.sponsor_demo_seed import (
        _apply_demo_paid,
        _demo_paystack_ref,
        _invoice_number,
        _save_item,
    )

    pack = SPONSOR_EVENT_PACKS.get(spec_slug, [])
    if not pack:
        return
    primary_campaign = next(iter(campaigns.values()), None)
    campaign_list = list(campaigns.values())
    deliverable_pack = SPONSOR_DELIVERABLE_PACKS.get(spec_slug, [])
    is_public_verified = spec_slug in {
        "neonpalm-drinks",
        "korawave-pay",
        "novaskin-beauty",
        "pulseframe-media",
    }

    sponsor_slots = [
        s
        for s in pack_slots
        if (s.title or "").startswith(f"{company_name} ·")
    ]
    if not sponsor_slots:
        sponsor_slots = pack_slots

    for i, evspec in enumerate(pack):
        event = pack_events.get(f"{spec_slug}:{evspec.key}")
        host = pack_hosts.get(evspec.host_slug)
        if event is None or host is None:
            continue
        slot = next(
            (
                s
                for s in sponsor_slots
                if s.event_id == event.id or evspec.title in (s.title or "")
            ),
            None,
        )
        if slot is None:
            continue

        _save_item(
            db,
            sponsor=sponsor,
            saved_by_user_id=owner.id,
            item_type="event",
            item_id=event.id,
            note=f"Pack event {i + 1}" if i < 2 else None,
        )
        if i < 2:
            _save_item(
                db,
                sponsor=sponsor,
                saved_by_user_id=owner.id,
                item_type="host",
                item_id=host.id,
            )
        _save_item(
            db,
            sponsor=sponsor,
            saved_by_user_id=owner.id,
            item_type="sponsorship_slot",
            item_id=slot.id,
        )

        pack_campaign = campaign_list[i % len(campaign_list)] if campaign_list else None

        placement_mode = evspec.placement
        if not is_public_verified and placement_mode in {"active", "completed"}:
            placement_mode = "planned"

        if placement_mode == "none":
            continue

        title = _deal_title(spec_slug, evspec.key)
        deal = db.scalar(
            select(SponsorshipDeal).where(
                SponsorshipDeal.sponsor_id == sponsor.id,
                SponsorshipDeal.title == title,
            )
        )
        host_user = db.get(User, host.user_id)
        if host_user is None:
            continue
        if deal is not None:
            _sync_demo_deal_for_public_profile(
                db,
                deal=deal,
                sponsor=sponsor,
                spec_slug=spec_slug,
                placement_mode=placement_mode,
                slot=slot,
                inq_id=deal.inquiry_id,
                event=event,
                is_public_verified=is_public_verified,
                deliverable_pack=deliverable_pack,
                pack_index=i,
            )
            continue

        inq = SponsorshipInquiry(
            slot_id=slot.id,
            sponsor_id=sponsor.id,
            campaign_id=pack_campaign.id if pack_campaign else None,
            company_name=sponsor.company_name,
            contact_name=owner.full_name or "Owner",
            contact_email=sponsor.contact_email,
            message=f"Demo inquiry for {evspec.title}.",
            status="accepted" if placement_mode in {"active", "completed"} else "reviewing",
        )
        db.add(inq)
        db.flush()

        deal_status = "invoice_pending"
        if placement_mode == "planned":
            deal_status = "proposed"
        elif placement_mode == "completed":
            deal_status = "completed"

        deal = SponsorshipDeal(
            sponsor_id=sponsor.id,
            host_id=host.id,
            campaign_id=pack_campaign.id if pack_campaign else None,
            inquiry_id=inq.id,
            slot_id=slot.id,
            title=title,
            package_type="activation",
            deliverables=[{"deliverable_type": evspec.slot_type, "title": evspec.slot_type}],
            amount=Decimal("900000") + Decimal(i * 150000),
            status=deal_status,
            proposed_by_user_id=host_user.id,
            accepted_by_user_id=owner.id if deal_status != "proposed" else None,
            accepted_at=_now() - timedelta(days=10 - i) if deal_status != "proposed" else None,
            starts_at=event.start_datetime,
            ends_at=event.end_datetime,
        )
        db.add(deal)
        db.flush()

        placement_status = "planned"
        if placement_mode == "active":
            placement_status = "active"
        elif placement_mode == "completed":
            placement_status = "completed"

        placement = SponsorshipPlacement(
            slot_id=slot.id,
            sponsor_id=sponsor.id,
            inquiry_id=inq.id,
            status=placement_status,
            starts_at=event.start_datetime,
            ends_at=event.end_datetime,
        )
        db.add(placement)
        db.flush()
        deal.placement_id = placement.id

        if placement_mode in {"active", "completed"} and is_public_verified:
            inv = SponsorshipInvoice(
                deal_id=deal.id,
                sponsor_id=sponsor.id,
                host_id=host.id,
                invoice_number=_invoice_number(),
                amount=deal.amount,
                status="paid" if placement_mode == "completed" else "issued",
                paystack_reference=_demo_paystack_ref(spec_slug, f"P{i}"),
            )
            db.add(inv)
            db.flush()
            if placement_mode == "active":
                _apply_demo_paid(db, deal=deal, invoice=inv, slug=spec_slug)
            else:
                _apply_demo_paid(db, deal=deal, invoice=inv, slug=spec_slug)
                deal.status = "completed"
                placement.status = "completed"
                inv.status = "paid"
                inv.paid_at = _now() - timedelta(days=20)

        if deliverable_pack and placement_mode in {"active", "completed"}:
            n = len(deliverable_pack)
            slice_pack = [
                deliverable_pack[i % n],
                deliverable_pack[(i + 1) % n],
            ]
            if n > 2:
                slice_pack.append(deliverable_pack[(i + 2) % n])
            _upsert_deliverables(db, deal=deal, pack=slice_pack)
