"""Public host discovery for the /hosts marketplace."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event
from app.hosts.models import Host
from app.legacy.models import HostLegacyPage, HostLegacyScore, LegacyTier
from app.sponsorships.models import HostSponsorshipSettings
from app.sponsorships.service import host_is_verified
from app.taxonomy import service as taxonomy_service
from app.users.gender import (
    HIDDEN_GENDER_PAYLOAD,
    host_shows_personal_gender,
    public_cache_safe_gender_payload,
)
from app.users.models import User
from app.vault.models import VaultItem

# Location labels safe to show on discovery cards (never street/venue secrets).
_PUBLIC_LOCATION = frozenset(
    {
        "full_public",
        "approximate_public",
        "city_only",
        "online_only",
    }
)


def _listed_event_clause():
    """Published events visible on the public marketplace."""
    return (
        Event.status == "published",
        Event.visibility.in_(("listed", "approval_required")),
    )


def list_discover_hosts(db: Session, *, limit: int = 60) -> list[dict]:
    """All active hosts for /hosts marketplace cards (including zero upcoming events)."""
    hosts = db.scalars(
        select(Host)
        .where(Host.status == "active")
        .options(selectinload(Host.profile), selectinload(Host.verifications))
        .order_by(Host.display_name.asc())
    ).all()
    if not hosts:
        return []

    host_ids = [h.id for h in hosts]
    now = datetime.now(timezone.utc)

    from app.crm.follower_count import follower_counts_by_host

    live_followers = follower_counts_by_host(db, host_ids)

    scores = {
        row.host_id: row
        for row in db.scalars(
            select(HostLegacyScore).where(HostLegacyScore.host_id.in_(host_ids))
        ).all()
    }
    pages = {
        row.host_id: row
        for row in db.scalars(
            select(HostLegacyPage).where(HostLegacyPage.host_id.in_(host_ids))
        ).all()
    }
    sponsor_settings = {
        row.host_id: row
        for row in db.scalars(
            select(HostSponsorshipSettings).where(
                HostSponsorshipSettings.host_id.in_(host_ids)
            )
        ).all()
    }
    tier_ids = {s.tier_id for s in scores.values() if s.tier_id}
    tiers = {
        t.id: t
        for t in db.scalars(select(LegacyTier).where(LegacyTier.id.in_(tier_ids))).all()
    } if tier_ids else {}

    upcoming_counts = dict(
        db.execute(
            select(Event.host_id, func.count())
            .where(
                Event.host_id.in_(host_ids),
                *_listed_event_clause(),
                Event.end_datetime >= now,
            )
            .group_by(Event.host_id)
        ).all()
    )
    vault_counts = dict(
        db.execute(
            select(VaultItem.host_id, func.count())
            .where(
                VaultItem.host_id.in_(host_ids),
                VaultItem.status == "published",
                VaultItem.moderation_status.in_(["none", "approved", "flagged"]),
            )
            .group_by(VaultItem.host_id)
        ).all()
    )

    next_events = _next_upcoming_by_host(db, host_ids=host_ids, now=now)

    owners = {
        u.id: u
        for u in db.scalars(
            select(User).where(User.id.in_([h.user_id for h in hosts]))
        ).all()
    }
    host_type_by_host: dict[UUID, list[str]] = {}
    for host in hosts:
        tax = taxonomy_service.get_host_taxonomy(db, host.id)
        host_type_by_host[host.id] = list(tax.get("host_type_slugs") or [])

    out: list[dict] = []
    for host in hosts:
        profile = host.profile
        score = scores.get(host.id)
        page = pages.get(host.id)
        sponsor = sponsor_settings.get(host.id)
        tier = tiers.get(score.tier_id) if score and score.tier_id else None
        verified = host_is_verified(db, host.id)
        upcoming = int(upcoming_counts.get(host.id) or 0)
        completed = int(score.completed_events) if score else 0
        vault_n = int(vault_counts.get(host.id) or 0)
        sponsor_ready = bool(
            (sponsor and sponsor.accepting_sponsors)
            or (page and page.sponsorship_available)
        )
        next_ev = next_events.get(host.id)
        type_slugs = host_type_by_host.get(host.id) or []
        shows_personal = host_shows_personal_gender(type_slugs)
        owner = owners.get(host.user_id)
        if not shows_personal or owner is None:
            gender_payload = dict(HIDDEN_GENDER_PAYLOAD)
        else:
            gender_payload = public_cache_safe_gender_payload(owner)

        out.append(
            {
                "host_id": host.id,
                "display_name": host.display_name,
                "username": host.slug,
                "verified": verified,
                "legacy_tier": tier.name if tier else (score.legacy_status if score else "New Host"),
                "legacy_status": score.legacy_status if score else "New Host",
                "bio": profile.bio if profile else None,
                "tagline": page.tagline if page else None,
                "avatar_url": profile.avatar_url if profile else None,
                "cover_url": profile.cover_url if profile else None,
                "primary_city": profile.city if profile else None,
                "primary_category": page.primary_category_slug if page else None,
                "host_type": page.host_type_slug if page else None,
                "upcoming_events_count": upcoming,
                "completed_events_count": completed,
                "verified_checkins_count": int(score.verified_checkins) if score else 0,
                "tickets_sold_count": int(score.tickets_sold) if score else 0,
                "average_rating": (
                    float(score.average_verified_rating)
                    if score and score.average_verified_rating is not None
                    else None
                ),
                "review_count": int(score.review_count) if score else 0,
                "followers_count": int(live_followers.get(host.id, 0)),
                "vault_items_count": vault_n,
                "sponsor_ready": sponsor_ready,
                "shows_personal_gender": shows_personal,
                **gender_payload,
                "next_upcoming_event": next_ev,
                "share_path": f"/@{host.slug}",
            }
        )

    # Featured-first: verified + activity, then name.
    out.sort(
        key=lambda h: (
            0 if h["verified"] else 1,
            -(h["upcoming_events_count"] or 0),
            -(h["verified_checkins_count"] or 0),
            h["display_name"].lower(),
        )
    )
    cap = max(1, min(limit, 120))
    return out[:cap]


def _next_upcoming_by_host(
    db: Session, *, host_ids: list[UUID], now: datetime
) -> dict[UUID, dict]:
    """One public next event per host — title/time only; city only when location is public."""
    if not host_ids:
        return {}
    rows = db.scalars(
        select(Event)
        .where(
            Event.host_id.in_(host_ids),
            *_listed_event_clause(),
            Event.end_datetime >= now,
        )
        .order_by(Event.start_datetime.asc())
    ).all()
    out: dict[UUID, dict] = {}
    for event in rows:
        if event.host_id in out:
            continue
        loc_vis = (event.location_visibility or "full_public").lower()
        city = event.city if loc_vis in _PUBLIC_LOCATION else None
        out[event.host_id] = {
            "title": event.title,
            "slug": event.slug,
            "start_datetime": event.start_datetime,
            "city": city,
        }
    return out
