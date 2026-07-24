"""Public sponsor partnership profile — public-safe aggregates only."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile, HostVerification
from app.sponsor_profiles.service import is_public_unlisted, serialize_public
from app.sponsorships.deliverables_constants import DELIVERABLE_TYPES
from app.sponsorships.models import (
    HostSponsorshipSettings,
    Sponsor,
    SponsorCampaign,
    SponsorshipDeal,
    SponsorshipDeliverable,
    SponsorshipPlacement,
    SponsorshipSlot,
)

_DELIVERABLE_LABELS: dict[str, str] = {
    "logo_placement": "Logo placement",
    "stage_mention": "Stage mention",
    "booth_space": "Booth space",
    "social_post": "Social post",
    "email_feature": "Email feature",
    "push_feature": "Push feature",
    "merch_collab": "Merch collab",
    "banner_ad": "Banner ad",
    "product_sampling": "Product sampling",
    "custom": "Custom activation",
}

_OBJECTIVE_PHRASES: dict[str, str] = {
    "brand_awareness": "Open to brand awareness partnerships",
    "product_launch": "Interested in product launch activations",
    "event_activation": "Focused on on-site event activations",
    "lead_generation": "Open to lead-generation partnerships",
    "community_engagement": "Supports community engagement programs",
    "campus_activation": "Targets campus and youth activations",
    "merch_collaboration": "Open to merch and collab partnerships",
    "media_partnership": "Interested in media and content partnerships",
    "other": "Open to custom partnership formats",
}

_SPONSOR_TYPE_LABELS: dict[str, str] = {
    "brand": "Brand sponsor",
    "business": "Business partner",
    "agency": "Agency partner",
    "creator": "Creator partner",
    "media_partner": "Media partner",
    "community": "Community partner",
    "ngo": "NGO partner",
    "government": "Public sector partner",
    "other": "Sponsor partner",
}


def _cover_is_usable(sponsor: Sponsor) -> bool:
    cover = (sponsor.cover_image_url or "").strip()
    if not cover:
        return False
    if cover == (sponsor.logo_url or "").strip():
        return False
    # Demo placeholders copied from Acme template — never use as hero art.
    if re.search(r"acme-events\.svg", cover, re.I):
        return False
    if re.search(r"/demo/sponsors/.*\.svg", cover, re.I):
        return False
    if re.search(r"Acme Events", cover, re.I):
        return False
    return True


def _public_cover_url(sponsor: Sponsor) -> str | None:
    return sponsor.cover_image_url if _cover_is_usable(sponsor) else None


def _summary_cards(sponsor: Sponsor) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    st = sponsor.sponsor_type or "other"
    cards.append(
        {
            "label": "Sponsor type",
            "value": _SPONSOR_TYPE_LABELS.get(st, "Sponsor partner"),
        }
    )
    if sponsor.industry:
        cards.append({"label": "Industry", "value": sponsor.industry})
    cats = [str(c) for c in (sponsor.categories or []) if c]
    if cats:
        cards.append(
            {
                "label": "Categories",
                "value": ", ".join(c.title() for c in cats[:5]),
            }
        )
    locs = [str(x) for x in (sponsor.target_locations or []) if x]
    if locs:
        cards.append(
            {
                "label": "Target locations",
                "value": ", ".join(locs[:4]),
            }
        )
    goals = [str(g) for g in (sponsor.campaign_goals or []) if g]
    if goals:
        phrases = [_OBJECTIVE_PHRASES.get(g, g.replace("_", " ")) for g in goals[:3]]
        cards.append({"label": "Objectives", "value": "; ".join(phrases)})
    style_bits: list[str] = []
    if cats:
        style_bits.append(f"Supports {', '.join(cats[:3])} experiences")
    if st == "media_partner":
        style_bits.append("Media and recap partnerships")
    elif st == "brand":
        style_bits.append("Brand activations and visibility")
    if style_bits:
        cards.append(
            {"label": "Partnership style", "value": ". ".join(style_bits)}
        )
    if sponsor.verification_status == "verified" and sponsor.status == "active":
        cards.append({"label": "Inquiries", "value": "Accepting inquiries"})
    return cards


def _partnership_blurb(sponsor: Sponsor) -> str | None:
    goals = sponsor.campaign_goals or []
    cats = sponsor.categories or []
    locs = sponsor.target_locations or []
    bits: list[str] = []
    if sponsor.display_name or sponsor.company_name:
        name = sponsor.display_name or sponsor.company_name
        bits.append(f"{name} partners with hosts on Pàdéyá")
    if cats:
        bits.append(f"across {', '.join(str(c) for c in cats[:4])} events")
    if locs:
        bits.append(f"with interest in {', '.join(str(x) for x in locs[:3])}")
    if goals:
        bits.append(
            "to support "
            + ", ".join(g.replace("_", " ") for g in goals[:3])
        )
    if not bits:
        return None
    text = " ".join(bits)
    return text if text.endswith(".") else f"{text}."


def _list_public_campaigns(
    db: Session,
    sponsor_id: UUID,
    sponsored: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(SponsorCampaign).where(
                SponsorCampaign.sponsor_id == sponsor_id,
                SponsorCampaign.visibility == "public_case_study",
                SponsorCampaign.moderation_status == "approved",
            )
        )
    )
    deal_campaign_ids: dict[UUID, int] = {}
    for pl_row in sponsored:
        cid = pl_row.get("campaign_id")
        if cid:
            deal_campaign_ids[cid] = deal_campaign_ids.get(cid, 0) + 1

    def _linked_count(campaign: SponsorCampaign) -> int:
        direct = deal_campaign_ids.get(campaign.id, 0)
        if direct:
            return direct
        targets = {str(c).lower() for c in (campaign.target_categories or [])}
        if not targets:
            return 0
        return sum(
            1
            for s in sponsored
            if s.get("category")
            and any(t in str(s["category"]).lower() for t in targets)
        )

    out: list[dict[str, Any]] = []
    for row in rows:
        linked = _linked_count(row)
        out.append(
            {
                "id": row.id,
                "name": row.name,
                "objective": row.objective,
                "objective_label": _OBJECTIVE_PHRASES.get(
                    row.objective, row.objective.replace("_", " ")
                ),
                "status": row.status,
                "status_label": row.status.replace("_", " ").title(),
                "target_categories": list(row.target_categories or []),
                "target_locations": list(row.target_locations or []),
                "description": row.description,
                "linked_sponsored_events_count": linked,
            }
        )
    return out


def _event_is_public(event: Event | None) -> bool:
    if event is None:
        return True
    if event.status != "published":
        return False
    vis = getattr(event, "visibility", None) or "listed"
    return vis in ("listed", "approval_required")


def _host_is_public(db: Session, host: Host | None, profile: HostProfile | None) -> bool:
    if host is None or host.status != "active":
        return False
    if host.status in ("suspended", "archived", "disabled"):
        return False
    verification = db.scalar(
        select(HostVerification).where(
            HostVerification.host_id == host.id,
            HostVerification.status == "verified",
        )
    )
    if verification is None:
        return False
    settings = db.scalar(
        select(HostSponsorshipSettings).where(
            HostSponsorshipSettings.host_id == host.id
        )
    )
    if settings is not None and not settings.accepting_sponsors:
        return False
    return True


def _slot_is_public(slot: SponsorshipSlot | None) -> bool:
    if slot is None:
        return False
    if slot.status != "published":
        return False
    mod = getattr(slot, "moderation_status", None) or "approved"
    return mod in ("approved", "not_required")


def _event_category_label(db: Session, event: Event | None) -> str | None:
    if event is None or not event.category_id:
        return None
    cat = db.get(EventCategory, event.category_id)
    if cat:
        return cat.name
    return None


def _event_area(event: Event | None, profile: HostProfile | None) -> str | None:
    if event is None:
        return profile.city if profile else None
    if event.area:
        return str(event.area)
    if event.city and event.area is None:
        return event.city
    return profile.city if profile else event.city


def _coerce_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _list_sponsored_events(db: Session, sponsor_id: UUID) -> list[dict[str, Any]]:
    placements = list(
        db.scalars(
            select(SponsorshipPlacement).where(
                SponsorshipPlacement.sponsor_id == sponsor_id,
                SponsorshipPlacement.status.in_(("active", "completed")),
            )
        )
    )
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for pl in placements:
        if str(pl.id) in seen:
            continue
        slot = db.get(SponsorshipSlot, pl.slot_id)
        if not _slot_is_public(slot):
            continue
        host = db.get(Host, slot.host_id)
        profile = (
            db.scalar(select(HostProfile).where(HostProfile.host_id == host.id))
            if host
            else None
        )
        if not _host_is_public(db, host, profile):
            continue

        event: Event | None = None
        if slot.event_id:
            event = db.get(Event, slot.event_id)
            if not _event_is_public(event):
                continue

        deal = db.scalar(
            select(SponsorshipDeal).where(
                SponsorshipDeal.sponsor_id == sponsor_id,
                SponsorshipDeal.placement_id == pl.id,
            )
        )
        if deal is None:
            deal = db.scalar(
                select(SponsorshipDeal).where(
                    SponsorshipDeal.sponsor_id == sponsor_id,
                    SponsorshipDeal.slot_id == slot.id,
                )
            )
        if deal and deal.status in (
            "cancelled",
            "rejected",
            "draft",
            "proposed",
            "invoice_pending",
            "payment_pending",
        ):
            continue

        deliverable_labels: list[str] = []
        campaign_id: UUID | None = None
        if deal:
            campaign_id = deal.campaign_id
            for d in db.scalars(
                select(SponsorshipDeliverable).where(
                    SponsorshipDeliverable.deal_id == deal.id
                )
            ):
                if d.deliverable_type in DELIVERABLE_TYPES:
                    label = _DELIVERABLE_LABELS.get(d.deliverable_type, d.title)
                    if label not in deliverable_labels:
                        deliverable_labels.append(label)
        deliverable_labels = deliverable_labels[:4]

        event_title = event.title if event else slot.title
        seen.add(str(pl.id))

        verification = (
            db.scalar(
                select(HostVerification).where(HostVerification.host_id == host.id)
            )
            if host
            else None
        )
        cat_label = _event_category_label(db, event)
        out.append(
            {
                "event_id": event.id if event else None,
                "event_title": event_title,
                "event_slug": event.slug if event else None,
                "host_id": host.id,
                "host_slug": host.slug,
                "host_display_name": host.display_name,
                "host_verified": verification is not None
                and verification.status == "verified",
                "category": cat_label,
                "city": profile.city if profile else None,
                "area": _event_area(event, profile),
                "starts_at": event.start_datetime if event else None,
                "placement_status": pl.status,
                "placement_status_label": pl.status.replace("_", " ").title(),
                "deliverable_labels": deliverable_labels,
                "campaign_id": campaign_id,
            }
        )
    out.sort(key=lambda row: _coerce_utc(row.get("starts_at")), reverse=True)
    return out


def _list_partner_hosts(
    db: Session, sponsor_id: UUID, sponsored: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id: dict[UUID, dict[str, Any]] = {}
    for row in sponsored:
        hid = row["host_id"]
        host = db.get(Host, hid)
        profile = db.scalar(select(HostProfile).where(HostProfile.host_id == hid))
        verification = db.scalar(
            select(HostVerification).where(HostVerification.host_id == hid)
        )
        if hid not in by_id:
            by_id[hid] = {
                "host_id": hid,
                "slug": host.slug if host else row["host_slug"],
                "display_name": row["host_display_name"],
                "city": row.get("area") or row.get("city"),
                "categories": [],
                "verified": row.get("host_verified", False)
                or (verification is not None and verification.status == "verified"),
                "sponsored_events_together": 0,
            }
        entry = by_id[hid]
        entry["sponsored_events_together"] += 1
        cat = row.get("category")
        if cat and cat not in entry["categories"]:
            entry["categories"].append(cat)
    return sorted(
        by_id.values(),
        key=lambda h: h["sponsored_events_together"],
        reverse=True,
    )


def _related_sponsors(db: Session, sponsor: Sponsor, *, limit: int = 3) -> list[dict[str, Any]]:
    from app.sponsor_profiles.service import list_public_sponsors

    peers = list_public_sponsors(db)
    cats = {str(c).lower() for c in (sponsor.categories or [])}
    locs = {str(x).lower() for x in (sponsor.target_locations or [])}
    industry = (sponsor.industry or "").lower()

    scored: list[tuple[int, Sponsor]] = []
    for p in peers:
        if p.id == sponsor.id or not p.slug:
            continue
        score = 0
        pc = {str(c).lower() for c in (p.categories or [])}
        pl = {str(x).lower() for x in (p.target_locations or [])}
        if cats and pc.intersection(cats):
            score += 3
        if locs and pl.intersection(locs):
            score += 2
        if industry and (p.industry or "").lower() == industry:
            score += 2
        elif industry and industry in (p.industry or "").lower():
            score += 1
        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda t: t[0], reverse=True)
    related = [p for _, p in scored[:limit]]
    if len(related) < limit:
        for p in peers:
            if p.id == sponsor.id or not p.slug:
                continue
            if p in related:
                continue
            related.append(p)
            if len(related) >= limit:
                break

    return [
        {
            "slug": p.slug or "",
            "display_name": p.display_name or p.company_name,
            "industry": p.industry,
            "logo_url": p.logo_url,
            "categories": list(p.categories or [])[:4],
        }
        for p in related[:limit]
    ]


def _logo_is_usable(sponsor: Sponsor) -> bool:
    logo = (sponsor.logo_url or "").strip()
    if not logo:
        return False
    if re.search(r"acme-events\.svg", logo, re.I):
        return False
    if re.search(r"/demo/sponsors/.*\.svg", logo, re.I):
        return False
    if re.search(r"Acme Events", logo, re.I):
        return False
    return True


def build_directory_item(db: Session, sponsor: Sponsor) -> dict[str, Any]:
    """Public-safe sponsor directory card with partnership highlights."""
    sponsored = _list_sponsored_events(db, sponsor.id)
    campaigns = _list_public_campaigns(db, sponsor.id, sponsored)
    hosts = _list_partner_hosts(db, sponsor.id, sponsored)
    cats = [str(c) for c in (sponsor.categories or []) if c]
    locs = [str(x) for x in (sponsor.target_locations or []) if x]
    hint_parts: list[str] = []
    if sponsored:
        hint_parts.append(f"{len(sponsored)} public placement{'s' if len(sponsored) != 1 else ''}")
    if campaigns:
        hint_parts.append(f"{len(campaigns)} case stud{'ies' if len(campaigns) != 1 else 'y'}")
    if cats:
        hint_parts.append(f"Supports {', '.join(cats[:3])}")
    return {
        "id": sponsor.id,
        "display_name": sponsor.display_name or sponsor.company_name,
        "slug": sponsor.slug or "",
        "sponsor_type": sponsor.sponsor_type,
        "logo_url": sponsor.logo_url if _logo_is_usable(sponsor) else None,
        "use_logo_fallback": not _logo_is_usable(sponsor),
        "industry": sponsor.industry,
        "categories": cats,
        "short_bio": sponsor.short_bio,
        "verified": sponsor.verification_status == "verified",
        "target_locations": locs,
        "accepting_inquiries": bool(
            sponsor.verification_status == "verified"
            and sponsor.visibility == "public"
            and sponsor.status == "active"
        ),
        "public_campaigns_count": len(campaigns),
        "sponsored_events_count": len(sponsored),
        "partnered_hosts_count": len(hosts),
        "partnership_hint": " · ".join(hint_parts) if hint_parts else None,
    }


def build_public_sponsor_profile(db: Session, sponsor: Sponsor) -> dict[str, Any]:
    if not is_public_unlisted(sponsor):
        raise ValueError("Sponsor is not public")

    base = serialize_public(sponsor, include_private=False)
    base["slug"] = sponsor.slug or ""
    base["cover_image_url"] = _public_cover_url(sponsor)
    base["use_cover_fallback"] = not _cover_is_usable(sponsor)
    base["target_locations"] = list(sponsor.target_locations or [])
    base["campaign_goals"] = list(sponsor.campaign_goals or [])
    base["partnership_blurb"] = _partnership_blurb(sponsor)
    base["accepting_inquiries"] = bool(
        sponsor.verification_status == "verified"
        and sponsor.visibility == "public"
        and sponsor.status == "active"
    )
    base["summary_cards"] = _summary_cards(sponsor)
    sponsored = _list_sponsored_events(db, sponsor.id)
    base["sponsored_events"] = sponsored
    base["public_campaigns"] = _list_public_campaigns(db, sponsor.id, sponsored)
    base["partnered_hosts"] = _list_partner_hosts(db, sponsor.id, sponsored)
    base["related_sponsors"] = _related_sponsors(db, sponsor)
    return base
