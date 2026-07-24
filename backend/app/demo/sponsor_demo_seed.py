"""Rich fictional sponsor demo profiles for local QA (never production)."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo import assets
from app.demo.constants import DEMO_EVENT_SLUG_PREFIX, DEMO_HOSTS, DEMO_PASSWORD
from app.demo.models import DemoEntityMarker
from app.demo.seed import _ensure_user, _mark, _seed_sponsorships
from app.demo.sponsor_demo_guards import assert_sponsor_demo_seed_allowed
from app.events.models import Event
from app.hosts.models import Host
from app.sponsor_profiles.constants import DEFAULT_ROLE_PERMISSIONS
from app.sponsor_profiles.recommendations.constants import (
    FEEDBACK_CLICKED,
    FEEDBACK_DISMISSED,
    FEEDBACK_MORE_LIKE_THIS,
    FEEDBACK_NOT_INTERESTED,
    FEEDBACK_SAVED,
)
from app.sponsor_profiles.recommendations.models import (
    CampaignRecommendationDismissal,
    CampaignRecommendationFeedback,
)
from app.sponsor_profiles.service import list_public_sponsors, serialize_public
from app.sponsorships.deals_constants import PAYSTACK_REF_PREFIX
from app.sponsorships.deals_payment import redact_paystack_payload
from app.sponsorships.deliverables_service import ensure_deliverables_for_active_deal
from app.sponsorships.models import (
    Sponsor,
    SponsorCampaign,
    SponsorSavedItem,
    SponsorTeamMember,
    SponsorshipAnalytics,
    SponsorshipDeal,
    SponsorshipDeliverable,
    SponsorshipInquiry,
    SponsorshipInvoice,
    SponsorshipPaymentEvent,
    SponsorshipPlacement,
    SponsorshipSlot,
)
from app.demo.sponsor_demo_portfolio import (
    ensure_sponsor_portfolio_catalog,
    seed_sponsor_portfolio,
)
from app.users.models import User
from app.users.service import get_role_by_name

SPONSOR_DEMO_EMAIL_DOMAIN = "demo.padeya.test"
MARKER_TYPE = "sponsor_demo"
MARKER_KEY = "rich-v2"

PUBLIC_DIRECTORY_SLUGS = frozenset(
    {
        "neonpalm-drinks",
        "korawave-pay",
        "novaskin-beauty",
        "pulseframe-media",
    }
)


def _now() -> datetime:
    return datetime.now(UTC)


def _demo_email(kind: str, slug: str) -> str:
    return f"sponsor-{kind}-{slug}@{SPONSOR_DEMO_EMAIL_DOMAIN}"


def _marker_done(db: Session) -> bool:
    return (
        db.scalar(
            select(DemoEntityMarker.id).where(
                DemoEntityMarker.entity_type == MARKER_TYPE,
                DemoEntityMarker.entity_key == MARKER_KEY,
            )
        )
        is not None
    )


def _set_marker(db: Session) -> None:
    if _marker_done(db):
        return
    db.add(
        DemoEntityMarker(
            entity_type=MARKER_TYPE,
            entity_key=MARKER_KEY,
            entity_id=None,
            meta={"note": "Rich sponsor demo seed"},
        )
    )


@dataclass
class CampaignSpec:
    name: str
    public_ref: str
    objective: str
    status: str
    target_categories: list[str] = field(default_factory=list)
    visibility: str = "private"
    moderation_status: str = "not_required"


@dataclass
class SponsorSpec:
    company_name: str
    slug: str
    sponsor_type: str
    industry: str
    status: str
    verification_status: str
    visibility: str
    short_bio: str
    description: str
    website_url: str
    budget_range: str
    categories: list[str]
    target_locations: list[str]
    campaign_goals: list[str]
    campaigns: list[CampaignSpec]
    team_roles: tuple[str, ...] = ("owner", "campaign_manager", "viewer")


SPONSOR_SPECS: list[SponsorSpec] = [
    SponsorSpec(
        company_name="NeonPalm Drinks",
        slug="neonpalm-drinks",
        sponsor_type="brand",
        industry="beverages / lifestyle",
        status="active",
        verification_status="verified",
        visibility="public",
        short_bio="Energetic nightlife beverage partner for Pàdéyá hosts.",
        description=(
            "NeonPalm backs Lagos nightlife, beach festivals, and campus concerts "
            "with sampling-led activations and co-branded moments."
        ),
        website_url="https://neonpalm.example.test",
        budget_range="₦500,000–₦3,000,000",
        categories=["music", "nightlife", "beach", "festival"],
        target_locations=["Lagos / Lekki", "Lagos / Victoria Island"],
        campaign_goals=["brand_awareness", "event_activation", "product_sampling"],
        campaigns=[
            CampaignSpec(
                name="Detty December Sampling Tour",
                public_ref="detty-december-sampling",
                objective="event_activation",
                status="active",
                target_categories=["music", "nightlife", "beach", "festival"],
                visibility="public_case_study",
                moderation_status="approved",
            ),
            CampaignSpec(
                name="NeonPalm Campus Nights",
                public_ref="neonpalm-campus-nights",
                objective="brand_awareness",
                status="active",
                target_categories=["music", "campus", "nightlife"],
                visibility="public_case_study",
                moderation_status="approved",
            ),
        ],
    ),
    SponsorSpec(
        company_name="KoraWave Pay",
        slug="korawave-pay",
        sponsor_type="business",
        industry="fintech / payments",
        status="active",
        verification_status="verified",
        visibility="public",
        short_bio="Payments and rewards partner for young professionals on Pàdéyá.",
        description=(
            "KoraWave Pay sponsors tech events, business mixers, and creator summits "
            "with lead-gen friendly packages."
        ),
        website_url="https://korawave.example.test",
        budget_range="₦1,000,000–₦5,000,000",
        categories=["tech", "business", "creator"],
        target_locations=["Lagos / Ikeja", "Abuja"],
        campaign_goals=["lead_generation", "brand_awareness", "community_engagement"],
        campaigns=[
            CampaignSpec(
                name="Creator Economy Payment Push",
                public_ref="creator-economy-push",
                objective="lead_generation",
                status="active",
                target_categories=["tech", "business", "creator"],
                visibility="public_case_study",
                moderation_status="approved",
            ),
            CampaignSpec(
                name="Business Payments Roadshow",
                public_ref="business-payments-roadshow",
                objective="lead_generation",
                status="active",
                target_categories=["business", "tech"],
                visibility="public_case_study",
                moderation_status="approved",
            ),
        ],
    ),
    SponsorSpec(
        company_name="Jollof Republic",
        slug="jollof-republic",
        sponsor_type="business",
        industry="food / quick service",
        status="active",
        verification_status="pending",
        visibility="public",
        short_bio="Food vendor and event catering sponsor for community nights.",
        description=(
            "Jollof Republic runs taste booths at family events, comedy nights, "
            "and outdoor concerts across Nigeria."
        ),
        website_url="https://jollof.example.test",
        budget_range="₦250,000–₦1,500,000",
        categories=["food", "comedy", "family"],
        target_locations=["Lagos / Mainland", "Ibadan"],
        campaign_goals=["product_sampling", "community_engagement"],
        campaigns=[
            CampaignSpec(
                name="Weekend Taste Booths",
                public_ref="weekend-taste-booths",
                objective="community_engagement",
                status="draft",
                target_categories=["food", "comedy"],
            ),
        ],
        team_roles=("owner", "campaign_manager"),
    ),
    SponsorSpec(
        company_name="CampusWave",
        slug="campuswave",
        sponsor_type="community",
        industry="youth / campus activations",
        status="under_review",
        verification_status="pending",
        visibility="unlisted",
        short_bio="Campus lifestyle activation group for student-led events.",
        description=(
            "CampusWave targets campus parties, student awards, and youth concerts "
            "with grassroots activations."
        ),
        website_url="https://campuswave.example.test",
        budget_range="₦150,000–₦800,000",
        categories=["campus", "music", "youth"],
        target_locations=["Lagos / Ikeja", "Ibadan"],
        campaign_goals=["campus_activation", "brand_awareness"],
        campaigns=[
            CampaignSpec(
                name="Campus Freshers Week",
                public_ref="campus-freshers-week",
                objective="campus_activation",
                status="under_review",
                target_categories=["campus"],
                moderation_status="pending",
            ),
        ],
        team_roles=("owner", "viewer"),
    ),
    SponsorSpec(
        company_name="NovaSkin Beauty",
        slug="novaskin-beauty",
        sponsor_type="brand",
        industry="beauty / skincare",
        status="active",
        verification_status="verified",
        visibility="public",
        short_bio="Beauty brand sponsoring lifestyle, fashion, and women-led events.",
        description=(
            "NovaSkin Beauty partners on fashion shows, brunches, and creator meetups "
            "with pop-ups and merch collabs."
        ),
        website_url="https://novaskin.example.test",
        budget_range="₦700,000–₦4,000,000",
        categories=["fashion", "lifestyle", "beauty"],
        target_locations=["Lagos / Victoria Island", "Lagos / Lekki"],
        campaign_goals=["product_launch", "merch_collaboration", "brand_awareness"],
        campaigns=[
            CampaignSpec(
                name="Glow Night Pop-up",
                public_ref="glow-night-popup",
                objective="product_launch",
                status="active",
                target_categories=["fashion", "lifestyle", "beauty"],
                visibility="public_case_study",
                moderation_status="approved",
            ),
            CampaignSpec(
                name="NovaSkin Creator Sampling",
                public_ref="novaskin-creator-sampling",
                objective="product_launch",
                status="active",
                target_categories=["beauty", "fashion"],
            ),
            CampaignSpec(
                name="NovaSkin Case Study 2026",
                public_ref="novaskin-case-study",
                objective="brand_awareness",
                status="active",
                visibility="public_case_study",
                moderation_status="approved",
            ),
        ],
    ),
    SponsorSpec(
        company_name="PulseFrame Media",
        slug="pulseframe-media",
        sponsor_type="media_partner",
        industry="media / content",
        status="active",
        verification_status="verified",
        visibility="public",
        short_bio="Media partner for event coverage, interviews, and recaps.",
        description=(
            "PulseFrame Media delivers recap films, host interviews, and social cuts "
            "for concerts and creator summits."
        ),
        website_url="https://pulseframe.example.test",
        budget_range="₦300,000–₦2,000,000",
        categories=["media", "music", "tech"],
        target_locations=["Lagos / Victoria Island", "Abuja"],
        campaign_goals=["media_partnership", "brand_awareness"],
        campaigns=[
            CampaignSpec(
                name="Event Recap Partnership",
                public_ref="event-recap-partnership",
                objective="media_partnership",
                status="completed",
                target_categories=["media", "music"],
                visibility="public_case_study",
                moderation_status="approved",
            ),
            CampaignSpec(
                name="Media Lounge Collaborations",
                public_ref="media-lounge-collaborations",
                objective="media_partnership",
                status="active",
                target_categories=["media", "business"],
                visibility="public_case_study",
                moderation_status="approved",
            ),
        ],
    ),
]


def _ensure_marketplace(
    db: Session,
) -> tuple[dict[str, Host], list[Event], list[SponsorshipSlot], dict[str, Event], list[SponsorshipSlot]]:
    hosts: dict[str, Host] = {}
    for spec in DEMO_HOSTS:
        host = db.scalar(select(Host).where(Host.slug == spec["slug"]))
        if host is not None:
            hosts[spec["slug"]] = host
    if len(hosts) < 3:
        raise RuntimeError(
            "Demo hosts missing. Run `python -m scripts.seed_demo_data` first."
        )
    users: dict[str, User] = {}
    for spec in DEMO_HOSTS:
        if spec["slug"] in hosts:
            owner = db.get(User, hosts[spec["slug"]].user_id)
            if owner:
                users[spec["owner_email"]] = owner
    _seed_sponsorships(db, hosts)

    events = list(
        db.scalars(
            select(Event).where(Event.slug.like(f"{DEMO_EVENT_SLUG_PREFIX}%"))
        ).all()
    )
    slots = list(
        db.scalars(
            select(SponsorshipSlot).where(SponsorshipSlot.status == "published")
        ).all()
    )
    _ensure_extra_slots(db, hosts, events, slots)
    pack_hosts, pack_events, pack_slots = ensure_sponsor_portfolio_catalog(db)
    hosts = {**hosts, **pack_hosts}
    events = list(events) + list(pack_events.values())
    slots = list(slots) + pack_slots
    db.commit()
    slots = list(
        db.scalars(
            select(SponsorshipSlot).where(SponsorshipSlot.status == "published")
        ).all()
    )
    return hosts, events, slots, pack_events, pack_slots


def _ensure_extra_slots(
    db: Session,
    hosts: dict[str, Host],
    events: list[Event],
    slots: list[SponsorshipSlot],
) -> None:
    if len(slots) >= 8:
        return
    extra_specs = [
        ("djmaze", "booth_space", "NeonPalm Beach Booth", "music", Decimal("800000")),
        ("lagoscomedyhub", "product_sampling", "Jollof Taste Lane", "food", Decimal("350000")),
        ("techconnectafrica", "stage_mention", "KoraWave Stage Shout", "tech", Decimal("1200000")),
        ("mainlandvibes", "banner_ad", "NovaSkin Glow Banner", "fashion", Decimal("650000")),
        ("djmaze", "social_post", "PulseFrame Recap Feature", "media", Decimal("400000")),
        ("techconnectafrica", "email_feature", "Fintech Founder Newsletter", "business", Decimal("900000")),
        ("lagoscomedyhub", "logo_placement", "Comedy Night Title Logo", "comedy", Decimal("500000")),
        ("mainlandvibes", "merch_collab", "CampusWave Merch Drop", "campus", Decimal("280000")),
    ]
    event_by_host: dict[uuid.UUID, Event] = {}
    for ev in events:
        if ev.host_id and ev.host_id not in event_by_host:
            event_by_host[ev.host_id] = ev
    for host_slug, slot_type, title, _cat, price in extra_specs:
        host = hosts.get(host_slug)
        if host is None:
            continue
        exists = db.scalar(
            select(SponsorshipSlot.id).where(
                SponsorshipSlot.host_id == host.id,
                SponsorshipSlot.title == title,
            )
        )
        if exists:
            continue
        ev = event_by_host.get(host.id)
        db.add(
            SponsorshipSlot(
                host_id=host.id,
                event_id=ev.id if ev else None,
                slot_type=slot_type,
                title=title,
                description=f"Demo sponsorship slot: {title} on Pàdéyá.",
                price=price,
                status="published",
                moderation_status="approved",
            )
        )
    db.flush()


def _ensure_sponsor_user(db: Session, *, email: str, full_name: str) -> User:
    user = _ensure_user(db, email=email, full_name=full_name, role="sponsor")
    sponsor_role = get_role_by_name(db, "sponsor")
    if sponsor_role and sponsor_role not in user.roles:
        user.roles.append(sponsor_role)
    return user


def _upsert_sponsor(db: Session, spec: SponsorSpec, owner: User) -> Sponsor:
    row = db.scalar(select(Sponsor).where(Sponsor.slug == spec.slug))
    contact = _demo_email("owner", spec.slug)
    logo = assets.sponsor_logo(spec.slug)
    if row is None:
        row = Sponsor(
            slug=spec.slug,
            company_name=spec.company_name,
            display_name=spec.company_name,
            owner_user_id=owner.id,
            user_id=owner.id,
            sponsor_type=spec.sponsor_type,
            contact_name=owner.full_name or spec.company_name,
            contact_email=contact,
            website_url=spec.website_url,
            website=spec.website_url,
            logo_url=logo,
            cover_image_url=None,
            short_bio=spec.short_bio,
            description=spec.description,
            industry=spec.industry,
            categories=spec.categories,
            target_locations=spec.target_locations,
            budget_range=spec.budget_range,
            campaign_goals=spec.campaign_goals,
            verification_status=spec.verification_status,
            visibility=spec.visibility,
            onboarding_status="active",
            status=spec.status,
            internal_notes=f"Demo-only sponsor seed ({spec.slug}).",
        )
        db.add(row)
        db.flush()
    else:
        row.company_name = spec.company_name
        row.display_name = spec.company_name
        row.owner_user_id = owner.id
        row.user_id = owner.id
        row.sponsor_type = spec.sponsor_type
        row.contact_email = contact
        row.logo_url = logo
        row.cover_image_url = None
        row.short_bio = spec.short_bio
        row.description = spec.description
        row.industry = spec.industry
        row.categories = spec.categories
        row.target_locations = spec.target_locations
        row.budget_range = spec.budget_range
        row.campaign_goals = spec.campaign_goals
        row.verification_status = spec.verification_status
        row.visibility = spec.visibility
        row.status = spec.status
        row.onboarding_status = "active"
    _mark(db, "sponsor_demo", spec.slug, row.id)
    return row


def _ensure_team(
    db: Session,
    *,
    sponsor: Sponsor,
    spec: SponsorSpec,
    owner: User,
) -> None:
    role_map = {
        "owner": owner,
        "campaign_manager": _ensure_sponsor_user(
            db,
            email=_demo_email("manager", spec.slug),
            full_name=f"{spec.company_name} Manager",
        ),
        "viewer": _ensure_sponsor_user(
            db,
            email=_demo_email("viewer", spec.slug),
            full_name=f"{spec.company_name} Viewer",
        ),
    }
    for role in spec.team_roles:
        member_user = role_map.get(role)
        if member_user is None:
            continue
        exists = db.scalar(
            select(SponsorTeamMember.id).where(
                SponsorTeamMember.sponsor_id == sponsor.id,
                SponsorTeamMember.user_id == member_user.id,
            )
        )
        if exists:
            continue
        perms = DEFAULT_ROLE_PERMISSIONS.get(role, DEFAULT_ROLE_PERMISSIONS["viewer"])
        db.add(
            SponsorTeamMember(
                sponsor_id=sponsor.id,
                user_id=member_user.id,
                role=role,
                permissions_json=dict(perms),
                invited_by_user_id=owner.id,
                status="active",
            )
        )
    db.flush()


def _ensure_campaigns(
    db: Session, *, sponsor: Sponsor, owner: User, spec: SponsorSpec
) -> dict[str, SponsorCampaign]:
    out: dict[str, SponsorCampaign] = {}
    for cspec in spec.campaigns:
        row = db.scalar(
            select(SponsorCampaign).where(
                SponsorCampaign.sponsor_id == sponsor.id,
                SponsorCampaign.public_ref == cspec.public_ref,
            )
        )
        if row is None:
            row = SponsorCampaign(
                sponsor_id=sponsor.id,
                created_by_user_id=owner.id,
                name=cspec.name,
                public_ref=cspec.public_ref,
                objective=cspec.objective,
                description=f"Demo campaign for {spec.company_name}.",
                target_categories=cspec.target_categories,
                target_locations=spec.target_locations,
                budget_min=Decimal("150000"),
                budget_max=Decimal("3000000"),
                status=cspec.status,
                visibility=cspec.visibility,
                moderation_status=cspec.moderation_status,
            )
            db.add(row)
            db.flush()
        else:
            row.status = cspec.status
            row.visibility = cspec.visibility
            row.moderation_status = cspec.moderation_status
        out[cspec.public_ref] = row
    return out


def _save_item(
    db: Session,
    *,
    sponsor: Sponsor,
    saved_by_user_id: uuid.UUID,
    item_type: str,
    item_id: uuid.UUID,
    note: str | None = None,
) -> SponsorSavedItem:
    row = db.scalar(
        select(SponsorSavedItem).where(
            SponsorSavedItem.sponsor_id == sponsor.id,
            SponsorSavedItem.item_type == item_type,
            SponsorSavedItem.item_id == item_id,
        )
    )
    if row:
        if note:
            row.note = note
        return row
    row = SponsorSavedItem(
        sponsor_id=sponsor.id,
        saved_by_user_id=saved_by_user_id,
        item_type=item_type,
        item_id=item_id,
        note=note,
    )
    db.add(row)
    db.flush()
    return row


def _invoice_number() -> str:
    return f"SPN-DEMO-{secrets.token_hex(4).upper()}"


def _demo_paystack_ref(slug: str, suffix: str) -> str:
    return f"{PAYSTACK_REF_PREFIX}DEMO-{slug[:8].upper()}-{suffix}"


def _apply_demo_paid(
    db: Session,
    *,
    deal: SponsorshipDeal,
    invoice: SponsorshipInvoice,
    slug: str,
) -> SponsorshipPlacement:
    """Simulate webhook success without notifications or Paystack API."""
    ref = invoice.paystack_reference or _demo_paystack_ref(slug, "PAID")
    invoice.paystack_reference = ref
    payload = {
        "event": "charge.success",
        "data": {
            "id": f"demo-{slug}-001",
            "reference": ref,
            "amount": int(invoice.amount * 100),
            "status": "success",
            "currency": "NGN",
        },
    }
    if not db.scalar(
        select(SponsorshipPaymentEvent.id).where(
            SponsorshipPaymentEvent.provider_reference == payload["data"]["id"]
        )
    ):
        db.add(
            SponsorshipPaymentEvent(
                invoice_id=invoice.id,
                deal_id=deal.id,
                provider="paystack",
                provider_reference=str(payload["data"]["id"]),
                event_type="charge.success",
                status="success",
                amount=invoice.amount,
                currency=invoice.currency,
                raw_payload_redacted=redact_paystack_payload(payload),
            )
        )
    now = _now()
    invoice.status = "paid"
    invoice.paid_at = now
    deal.status = "active"
    placement = None
    if deal.placement_id:
        placement = db.get(SponsorshipPlacement, deal.placement_id)
    if placement is None and deal.slot_id:
        placement = SponsorshipPlacement(
            slot_id=deal.slot_id,
            sponsor_id=deal.sponsor_id,
            inquiry_id=deal.inquiry_id,
            status="active",
            starts_at=deal.starts_at,
            ends_at=deal.ends_at,
        )
        db.add(placement)
        db.flush()
        db.add(SponsorshipAnalytics(placement_id=placement.id, impressions=1200, clicks=84))
        deal.placement_id = placement.id
    elif placement is not None:
        placement.status = "active"
    ensure_deliverables_for_active_deal(db, deal=deal, placement_id=deal.placement_id)
    db.flush()
    return placement  # type: ignore[return-value]


def _seed_sponsor_interactions(
    db: Session,
    *,
    spec: SponsorSpec,
    sponsor: Sponsor,
    owner: User,
    campaigns: dict[str, SponsorCampaign],
    hosts: dict[str, Host],
    events: list[Event],
    slots: list[SponsorshipSlot],
) -> None:
    host_list = list(hosts.values())
    host_by_slug = hosts
    slot_list = slots[:]
    ev_list = events[:]

    for i, hslug in enumerate(["djmaze", "lagoscomedyhub", "techconnectafrica"]):
        h = host_by_slug.get(hslug)
        if h:
            _save_item(
                db,
                sponsor=sponsor,
                saved_by_user_id=owner.id,
                item_type="host",
                item_id=h.id,
                note=f"Shortlist host #{i + 1}" if i == 0 else None,
            )
    for i, ev in enumerate(ev_list[:2]):
        _save_item(
            db,
            sponsor=sponsor,
            saved_by_user_id=owner.id,
            item_type="event",
            item_id=ev.id,
            note=None,
        )
    if slot_list:
        _save_item(
            db,
            sponsor=sponsor,
            saved_by_user_id=owner.id,
            item_type="sponsorship_slot",
            item_id=slot_list[0].id,
            note="High intent slot",
        )

    primary_campaign = next(iter(campaigns.values()), None)
    host = host_by_slug.get("djmaze") or (host_list[0] if host_list else None)
    if host is None or not slot_list:
        return
    slot = next((s for s in slot_list if s.host_id == host.id), slot_list[0])

    if spec.slug == "neonpalm-drinks" and slot and primary_campaign:
        inq = db.scalar(
            select(SponsorshipInquiry).where(
                SponsorshipInquiry.sponsor_id == sponsor.id,
                SponsorshipInquiry.message.like("%NeonPalm%"),
            )
        )
        if inq is None:
            inq = SponsorshipInquiry(
                slot_id=slot.id,
                sponsor_id=sponsor.id,
                campaign_id=primary_campaign.id,
                company_name=sponsor.company_name,
                contact_name=owner.full_name or "Owner",
                contact_email=sponsor.contact_email,
                message="NeonPalm wants sampling on this Pàdéyá slot.",
                proposed_budget=Decimal("1200000"),
                status="accepted",
            )
            db.add(inq)
            db.flush()
        inq2 = db.scalar(
            select(SponsorshipInquiry).where(
                SponsorshipInquiry.sponsor_id == sponsor.id,
                SponsorshipInquiry.status == "new",
            )
        )
        if inq2 is None:
            db.add(
                SponsorshipInquiry(
                    slot_id=slot.id,
                    sponsor_id=sponsor.id,
                    campaign_id=primary_campaign.id,
                    company_name=sponsor.company_name,
                    contact_name=owner.full_name or "Owner",
                    contact_email=sponsor.contact_email,
                    message="Secondary NeonPalm inquiry for QA.",
                    status="new",
                )
            )
        deal = db.scalar(
            select(SponsorshipDeal).where(
                SponsorshipDeal.sponsor_id == sponsor.id,
                SponsorshipDeal.title == "NeonPalm Detty Package",
            )
        )
        host_user = db.get(User, host.user_id)
        if deal is None and host_user:
            deal = SponsorshipDeal(
                sponsor_id=sponsor.id,
                host_id=host.id,
                campaign_id=primary_campaign.id,
                inquiry_id=inq.id,
                slot_id=slot.id,
                title="NeonPalm Detty Package",
                package_type="activation",
                deliverables=[
                    {"title": "Booth space", "deliverable_type": "booth_space"},
                    {"title": "Stage mention", "deliverable_type": "stage_mention"},
                    {"title": "Social post", "deliverable_type": "social_post"},
                ],
                amount=Decimal("1500000"),
                status="invoice_pending",
                proposed_by_user_id=host_user.id,
                accepted_by_user_id=owner.id,
                accepted_at=_now() - timedelta(days=3),
            )
            db.add(deal)
            db.flush()
            inv = SponsorshipInvoice(
                deal_id=deal.id,
                sponsor_id=sponsor.id,
                host_id=host.id,
                invoice_number=_invoice_number(),
                amount=deal.amount,
                status="issued",
                paystack_reference=_demo_paystack_ref(spec.slug, "NEON"),
            )
            db.add(inv)
            db.flush()
            placement = _apply_demo_paid(db, deal=deal, invoice=inv, slug=spec.slug)
            rows = list(
                db.scalars(
                    select(SponsorshipDeliverable).where(
                        SponsorshipDeliverable.deal_id == deal.id
                    )
                )
            )
            for row in rows:
                if row.deliverable_type == "booth_space":
                    row.status = "submitted"
                    row.proof_url = assets.sponsor_logo(spec.slug)
                    row.submitted_at = _now() - timedelta(days=1)
                elif row.deliverable_type == "stage_mention":
                    row.status = "pending"
                elif row.deliverable_type == "social_post":
                    row.status = "approved"
                    row.approved_at = _now()

    if spec.slug == "korawave-pay" and slot and primary_campaign:
        host_tech = host_by_slug.get("techconnectafrica") or host
        slot_t = next((s for s in slot_list if s.host_id == host_tech.id), slot)
        host_user = db.get(User, host_tech.user_id)
        if host_user and not db.scalar(
            select(SponsorshipDeal.id).where(
                SponsorshipDeal.sponsor_id == sponsor.id,
                SponsorshipDeal.title == "KoraWave Proposed Package",
            )
        ):
            inq = SponsorshipInquiry(
                slot_id=slot_t.id,
                sponsor_id=sponsor.id,
                campaign_id=primary_campaign.id,
                company_name=sponsor.company_name,
                contact_name=owner.full_name or "Owner",
                contact_email=sponsor.contact_email,
                message="KoraWave pending acceptance proposal.",
                status="reviewing",
            )
            db.add(inq)
            db.flush()
            db.add(
                SponsorshipDeal(
                    sponsor_id=sponsor.id,
                    host_id=host_tech.id,
                    campaign_id=primary_campaign.id,
                    inquiry_id=inq.id,
                    slot_id=slot_t.id,
                    title="KoraWave Proposed Package",
                    package_type="title_sponsor",
                    deliverables=["Logo on stage", "Email mention"],
                    amount=Decimal("2200000"),
                    status="proposed",
                    proposed_by_user_id=host_user.id,
                )
            )
        if host_user and not db.scalar(
            select(SponsorshipDeal.id).where(
                SponsorshipDeal.sponsor_id == sponsor.id,
                SponsorshipDeal.title == "KoraWave Invoice Pending",
            )
        ):
            inq_paid = SponsorshipInquiry(
                slot_id=slot_t.id,
                sponsor_id=sponsor.id,
                campaign_id=primary_campaign.id,
                company_name=sponsor.company_name,
                contact_name=owner.full_name or "Owner",
                contact_email=sponsor.contact_email,
                message="KoraWave accepted — awaiting payment.",
                status="accepted",
            )
            db.add(inq_paid)
            db.flush()
            deal2 = SponsorshipDeal(
                sponsor_id=sponsor.id,
                host_id=host_tech.id,
                campaign_id=primary_campaign.id,
                inquiry_id=inq_paid.id,
                slot_id=slot_t.id,
                title="KoraWave Invoice Pending",
                package_type="integration",
                deliverables=["Payment kiosk", "Push feature"],
                amount=Decimal("1800000"),
                status="invoice_pending",
                proposed_by_user_id=host_user.id,
                accepted_by_user_id=owner.id,
                accepted_at=_now() - timedelta(days=1),
            )
            db.add(deal2)
            db.flush()
            db.add(
                SponsorshipInvoice(
                    deal_id=deal2.id,
                    sponsor_id=sponsor.id,
                    host_id=host_tech.id,
                    invoice_number=_invoice_number(),
                    amount=deal2.amount,
                    status="issued",
                    paystack_reference=_demo_paystack_ref(spec.slug, "OPEN"),
                    due_at=_now() + timedelta(days=7),
                )
            )

    if spec.slug == "jollof-republic" and slot and primary_campaign:
        if not db.scalar(
            select(SponsorshipInquiry.id).where(
                SponsorshipInquiry.sponsor_id == sponsor.id
            )
        ):
            db.add(
                SponsorshipInquiry(
                    slot_id=slot.id,
                    sponsor_id=sponsor.id,
                    campaign_id=primary_campaign.id,
                    company_name=sponsor.company_name,
                    contact_name=owner.full_name or "Owner",
                    contact_email=sponsor.contact_email,
                    message="Jollof Republic taste booth inquiry.",
                    status="reviewing",
                )
            )

    if spec.slug == "campuswave" and primary_campaign and ev_list:
        camp = campaigns.get("campus-freshers-week")
        if camp:
            ev = ev_list[0]
            _save_item(
                db,
                sponsor=sponsor,
                saved_by_user_id=owner.id,
                item_type="event",
                item_id=ev.id,
                note="Campus target",
            )
            if not db.scalar(
                select(CampaignRecommendationFeedback.id).where(
                    CampaignRecommendationFeedback.campaign_id == camp.id
                )
            ):
                db.add(
                    CampaignRecommendationFeedback(
                        campaign_id=camp.id,
                        sponsor_id=sponsor.id,
                        actor_user_id=owner.id,
                        item_type="event",
                        item_id=ev.id,
                        action=FEEDBACK_DISMISSED,
                    )
                )
                db.add(
                    CampaignRecommendationDismissal(
                        campaign_id=camp.id,
                        item_type="event",
                        item_id=ev.id,
                        expires_at=_now() + timedelta(days=60),
                    )
                )
                if len(ev_list) > 1:
                    db.add(
                        CampaignRecommendationFeedback(
                            campaign_id=camp.id,
                            sponsor_id=sponsor.id,
                            actor_user_id=owner.id,
                            item_type="sponsorship_slot",
                            item_id=slot_list[1].id if len(slot_list) > 1 else slot.id,
                            action=FEEDBACK_NOT_INTERESTED,
                        )
                    )

    if spec.slug == "novaskin-beauty" and slot and primary_campaign:
        host_f = host_by_slug.get("mainlandvibes") or host
        slot_f = next((s for s in slot_list if s.host_id == host_f.id), slot)
        host_user = db.get(User, host_f.user_id)
        if host_user and not db.scalar(
            select(SponsorshipDeal.id).where(
                SponsorshipDeal.sponsor_id == sponsor.id,
                SponsorshipDeal.title == "NovaSkin Glow Package",
            )
        ):
            inq = SponsorshipInquiry(
                slot_id=slot_f.id,
                sponsor_id=sponsor.id,
                campaign_id=primary_campaign.id,
                company_name=sponsor.company_name,
                contact_name=owner.full_name or "Owner",
                contact_email=sponsor.contact_email,
                message="NovaSkin glow activation.",
                status="accepted",
            )
            db.add(inq)
            db.flush()
            deal = SponsorshipDeal(
                sponsor_id=sponsor.id,
                host_id=host_f.id,
                campaign_id=primary_campaign.id,
                inquiry_id=inq.id,
                slot_id=slot_f.id,
                title="NovaSkin Glow Package",
                package_type="pop_up",
                deliverables=[
                    {"title": "Banner ad", "deliverable_type": "banner_ad"},
                    {"title": "Product sampling", "deliverable_type": "product_sampling"},
                    {"title": "Social post", "deliverable_type": "social_post"},
                ],
                amount=Decimal("2100000"),
                status="invoice_pending",
                proposed_by_user_id=host_user.id,
                accepted_by_user_id=owner.id,
                accepted_at=_now() - timedelta(days=4),
            )
            db.add(deal)
            db.flush()
            inv = SponsorshipInvoice(
                deal_id=deal.id,
                sponsor_id=sponsor.id,
                host_id=host_f.id,
                invoice_number=_invoice_number(),
                amount=deal.amount,
                status="issued",
                paystack_reference=_demo_paystack_ref(spec.slug, "GLOW"),
            )
            db.add(inv)
            db.flush()
            _apply_demo_paid(db, deal=deal, invoice=inv, slug=spec.slug)
            for row in db.scalars(
                select(SponsorshipDeliverable).where(
                    SponsorshipDeliverable.deal_id == deal.id
                )
            ):
                if row.deliverable_type == "banner_ad":
                    row.status = "completed"
                elif row.deliverable_type == "product_sampling":
                    row.status = "rejected"
                    row.rejection_reason = "Need clearer sampling plan."
                elif row.deliverable_type == "social_post":
                    row.status = "submitted"
                    row.submitted_at = _now()

    if spec.slug == "pulseframe-media" and slot and primary_campaign:
        host_m = host_by_slug.get("djmaze") or host
        slot_m = next((s for s in slot_list if s.host_id == host_m.id), slot)
        host_user = db.get(User, host_m.user_id)
        if host_user and not db.scalar(
            select(SponsorshipDeal.id).where(
                SponsorshipDeal.sponsor_id == sponsor.id,
                SponsorshipDeal.title == "PulseFrame Recap Deal",
            )
        ):
            inq = SponsorshipInquiry(
                slot_id=slot_m.id,
                sponsor_id=sponsor.id,
                campaign_id=primary_campaign.id,
                company_name=sponsor.company_name,
                contact_name=owner.full_name or "Owner",
                contact_email=sponsor.contact_email,
                message="PulseFrame recap partnership completed.",
                status="accepted",
            )
            db.add(inq)
            db.flush()
            deal = SponsorshipDeal(
                sponsor_id=sponsor.id,
                host_id=host_m.id,
                campaign_id=primary_campaign.id,
                inquiry_id=inq.id,
                slot_id=slot_m.id,
                title="PulseFrame Recap Deal",
                package_type="media",
                deliverables=[
                    {"title": "Recap film", "deliverable_type": "custom"},
                    {"title": "Social post", "deliverable_type": "social_post"},
                ],
                amount=Decimal("950000"),
                status="completed",
                proposed_by_user_id=host_user.id,
                accepted_by_user_id=owner.id,
                accepted_at=_now() - timedelta(days=30),
                starts_at=_now() - timedelta(days=28),
                ends_at=_now() - timedelta(days=7),
            )
            db.add(deal)
            db.flush()
            placement = SponsorshipPlacement(
                slot_id=slot_m.id,
                sponsor_id=sponsor.id,
                inquiry_id=inq.id,
                status="completed",
                starts_at=deal.starts_at,
                ends_at=deal.ends_at,
            )
            db.add(placement)
            db.flush()
            deal.placement_id = placement.id
            inv = SponsorshipInvoice(
                deal_id=deal.id,
                sponsor_id=sponsor.id,
                host_id=host_m.id,
                invoice_number=_invoice_number(),
                amount=deal.amount,
                status="paid",
                paystack_reference=_demo_paystack_ref(spec.slug, "RECAP"),
                paid_at=_now() - timedelta(days=25),
            )
            db.add(inv)
            db.flush()
            _apply_demo_paid(db, deal=deal, invoice=inv, slug=spec.slug)
            deal.status = "completed"
            placement.status = "completed"
            for row in db.scalars(
                select(SponsorshipDeliverable).where(
                    SponsorshipDeliverable.deal_id == deal.id
                )
            ):
                row.status = "completed"

    # Recommendation feedback samples for active campaigns
    if primary_campaign and spec.slug in {"neonpalm-drinks", "korawave-pay"}:
        if ev_list and not db.scalar(
            select(CampaignRecommendationFeedback.id).where(
                CampaignRecommendationFeedback.campaign_id == primary_campaign.id,
                CampaignRecommendationFeedback.action == FEEDBACK_CLICKED,
            )
        ):
            db.add(
                CampaignRecommendationFeedback(
                    campaign_id=primary_campaign.id,
                    sponsor_id=sponsor.id,
                    actor_user_id=owner.id,
                    item_type="host",
                    item_id=host_list[0].id,
                    action=FEEDBACK_CLICKED,
                )
            )
            db.add(
                CampaignRecommendationFeedback(
                    campaign_id=primary_campaign.id,
                    sponsor_id=sponsor.id,
                    actor_user_id=owner.id,
                    item_type="event",
                    item_id=ev_list[0].id,
                    action=FEEDBACK_SAVED,
                )
            )
            db.add(
                CampaignRecommendationFeedback(
                    campaign_id=primary_campaign.id,
                    sponsor_id=sponsor.id,
                    actor_user_id=owner.id,
                    item_type="sponsorship_slot",
                    item_id=slot.id if slot else slot_list[0].id,
                    action=FEEDBACK_MORE_LIKE_THIS,
                )
            )


def seed_rich_sponsor_demo(db: Session, *, force: bool = False) -> dict[str, Any]:
    """Seed six fictional sponsor workspaces. Idempotent unless force=True."""
    assert_sponsor_demo_seed_allowed()
    refresh_only = _marker_done(db) and not force

    hosts, events, slots, pack_events, pack_slots = _ensure_marketplace(db)

    def _refresh_portfolios() -> None:
        for spec in SPONSOR_SPECS:
            sponsor = db.scalar(select(Sponsor).where(Sponsor.slug == spec.slug))
            if sponsor is None:
                continue
            owner = db.get(User, sponsor.owner_user_id)
            if owner is None:
                owner = _ensure_sponsor_user(
                    db,
                    email=_demo_email("owner", spec.slug),
                    full_name=f"{spec.company_name} Owner",
                )
            campaigns = _ensure_campaigns(db, sponsor=sponsor, owner=owner, spec=spec)
            seed_sponsor_portfolio(
                db,
                spec_slug=spec.slug,
                company_name=spec.company_name,
                sponsor=sponsor,
                owner=owner,
                campaigns=campaigns,
                pack_hosts=hosts,
                pack_events=pack_events,
                pack_slots=pack_slots,
            )

    if refresh_only:
        _refresh_portfolios()
        db.commit()
        return {
            "skipped": True,
            "reason": "already_seeded",
            "portfolio_refresh": True,
            "public_directory_slugs": sorted(PUBLIC_DIRECTORY_SLUGS),
        }

    counts = {"sponsors": 0, "campaigns": 0, "deals": 0, "slots": len(slots)}

    for spec in SPONSOR_SPECS:
        owner = _ensure_sponsor_user(
            db,
            email=_demo_email("owner", spec.slug),
            full_name=f"{spec.company_name} Owner",
        )
        sponsor = _upsert_sponsor(db, spec, owner)
        counts["sponsors"] += 1
        _ensure_team(db, sponsor=sponsor, spec=spec, owner=owner)
        campaigns = _ensure_campaigns(db, sponsor=sponsor, owner=owner, spec=spec)
        counts["campaigns"] += len(campaigns)
        seed_sponsor_portfolio(
            db,
            spec_slug=spec.slug,
            company_name=spec.company_name,
            sponsor=sponsor,
            owner=owner,
            campaigns=campaigns,
            pack_hosts=hosts,
            pack_events=pack_events,
            pack_slots=pack_slots,
        )
        _seed_sponsor_interactions(
            db,
            spec=spec,
            sponsor=sponsor,
            owner=owner,
            campaigns=campaigns,
            hosts=hosts,
            events=events,
            slots=slots,
        )

    counts["deals"] = int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipDeal)
            .join(Sponsor, SponsorshipDeal.sponsor_id == Sponsor.id)
            .where(Sponsor.slug.in_([s.slug for s in SPONSOR_SPECS]))
        )
        or 0
    )
    _set_marker(db)
    db.commit()
    counts["skipped"] = False
    counts["password"] = DEMO_PASSWORD
    counts["public_directory_slugs"] = sorted(PUBLIC_DIRECTORY_SLUGS)
    return counts


def public_directory_slugs(db: Session) -> list[str]:
    return sorted(s.slug for s in list_public_sponsors(db) if s.slug)


def public_profile_safe(sponsor: Sponsor) -> dict[str, Any]:
    return serialize_public(sponsor, include_private=False)
