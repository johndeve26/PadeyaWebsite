"""Apply taxonomy assignments onto demo hosts and events."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event, EventCategory
from app.hosts.models import Host
from app.sponsorships.service import get_or_create_settings
from app.taxonomy.constants import (
    CITY_TO_LOCATION_SLUG,
    DEMO_CATEGORY_TAXONOMY,
    DEMO_EVENT_LOCATIONS,
    DEMO_HOST_TAXONOMY,
)
from app.taxonomy.models import (
    ContentRelationship,
    EventTaxonomyLink,
    HostLocationLink,
    HostTaxonomyLink,
    HostType,
    Location,
    TaxonomyAudienceType,
    TaxonomyCategory,
    TaxonomyTag,
    TaxonomyVibe,
)
from app.taxonomy.service import location_ancestors, seed_taxonomy_vocab
from app.demo.constants import DEMO_EVENT_SLUG_PREFIX


def _ensure_host_link(
    db: Session,
    *,
    host_id,
    link_type: str,
    taxonomy_id,
    taxonomy_slug: str,
) -> None:
    existing = db.scalar(
        select(HostTaxonomyLink).where(
            HostTaxonomyLink.host_id == host_id,
            HostTaxonomyLink.link_type == link_type,
            HostTaxonomyLink.taxonomy_id == taxonomy_id,
        )
    )
    if existing is None:
        db.add(
            HostTaxonomyLink(
                host_id=host_id,
                link_type=link_type,
                taxonomy_id=taxonomy_id,
                taxonomy_slug=taxonomy_slug,
            )
        )


def _ensure_event_link(
    db: Session,
    *,
    event_id,
    link_type: str,
    taxonomy_id,
    taxonomy_slug: str,
) -> None:
    existing = db.scalar(
        select(EventTaxonomyLink).where(
            EventTaxonomyLink.event_id == event_id,
            EventTaxonomyLink.link_type == link_type,
            EventTaxonomyLink.taxonomy_id == taxonomy_id,
        )
    )
    if existing is None:
        db.add(
            EventTaxonomyLink(
                event_id=event_id,
                link_type=link_type,
                taxonomy_id=taxonomy_id,
                taxonomy_slug=taxonomy_slug,
            )
        )


def _ensure_host_location(
    db: Session, *, host_id, location_id, is_primary: bool
) -> None:
    existing = db.scalar(
        select(HostLocationLink).where(
            HostLocationLink.host_id == host_id,
            HostLocationLink.location_id == location_id,
        )
    )
    if existing is None:
        db.add(
            HostLocationLink(
                host_id=host_id,
                location_id=location_id,
                is_primary=is_primary,
            )
        )
    else:
        if is_primary:
            existing.is_primary = True


def _ensure_relationship(
    db: Session,
    *,
    source_type: str,
    source_id,
    target_type: str,
    target_id,
    relationship_type: str,
    weight: Decimal = Decimal("1.00"),
    reason: str | None = None,
) -> None:
    existing = db.scalar(
        select(ContentRelationship).where(
            ContentRelationship.source_type == source_type,
            ContentRelationship.source_id == source_id,
            ContentRelationship.target_type == target_type,
            ContentRelationship.target_id == target_id,
            ContentRelationship.relationship_type == relationship_type,
        )
    )
    if existing is None:
        db.add(
            ContentRelationship(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                relationship_type=relationship_type,
                weight=weight,
                reason=reason or "demo_seed",
                created_by="demo_seed",
            )
        )


def apply_demo_taxonomy(db: Session) -> dict[str, int]:
    """Seed vocab and assign taxonomy graph edges for demo hosts/events."""
    counts = seed_taxonomy_vocab(db)

    categories = {
        c.slug: c for c in db.scalars(select(TaxonomyCategory)).all()
    }
    tags = {t.slug: t for t in db.scalars(select(TaxonomyTag)).all()}
    vibes = {v.slug: v for v in db.scalars(select(TaxonomyVibe)).all()}
    audiences = {
        a.slug: a for a in db.scalars(select(TaxonomyAudienceType)).all()
    }
    host_types = {h.slug: h for h in db.scalars(select(HostType)).all()}
    locations_by_kind_slug = {
        (loc.kind, loc.slug): loc for loc in db.scalars(select(Location)).all()
    }
    # Prefer city over state when only a slug is known (shared slugs like lagos).
    locations_by_slug: dict[str, Location] = {}
    for loc in locations_by_kind_slug.values():
        existing = locations_by_slug.get(loc.slug)
        if existing is None or loc.kind == "city" or (
            existing.kind not in {"city", "area"} and loc.kind == "area"
        ):
            locations_by_slug[loc.slug] = loc

    hosts = {
        h.slug: h
        for h in db.scalars(
            select(Host).where(Host.slug.in_(list(DEMO_HOST_TAXONOMY.keys())))
        ).all()
    }

    for slug, spec in DEMO_HOST_TAXONOMY.items():
        host = hosts.get(slug)
        if host is None:
            continue

        for ht_slug in spec.get("host_types", []):  # type: ignore[union-attr]
            ht = host_types.get(ht_slug)  # type: ignore[arg-type]
            if ht:
                _ensure_host_link(
                    db,
                    host_id=host.id,
                    link_type="host_type",
                    taxonomy_id=ht.id,
                    taxonomy_slug=ht.slug,
                )
        for cat_slug in spec.get("categories", []):  # type: ignore[union-attr]
            cat = categories.get(cat_slug)  # type: ignore[arg-type]
            if cat:
                _ensure_host_link(
                    db,
                    host_id=host.id,
                    link_type="category",
                    taxonomy_id=cat.id,
                    taxonomy_slug=cat.slug,
                )
        for tag_slug in spec.get("tags", []):  # type: ignore[union-attr]
            tag = tags.get(tag_slug)  # type: ignore[arg-type]
            if tag:
                _ensure_host_link(
                    db,
                    host_id=host.id,
                    link_type="tag",
                    taxonomy_id=tag.id,
                    taxonomy_slug=tag.slug,
                )
        for vibe_slug in spec.get("vibes", []):  # type: ignore[union-attr]
            vibe = vibes.get(vibe_slug)  # type: ignore[arg-type]
            if vibe:
                _ensure_host_link(
                    db,
                    host_id=host.id,
                    link_type="vibe",
                    taxonomy_id=vibe.id,
                    taxonomy_slug=vibe.slug,
                )
        for aud_slug in spec.get("audience", []):  # type: ignore[union-attr]
            aud = audiences.get(aud_slug)  # type: ignore[arg-type]
            if aud:
                _ensure_host_link(
                    db,
                    host_id=host.id,
                    link_type="audience",
                    taxonomy_id=aud.id,
                    taxonomy_slug=aud.slug,
                )

        primary = spec.get("primary_location")
        for loc_slug in spec.get("location_slugs", []):  # type: ignore[union-attr]
            loc = locations_by_slug.get(loc_slug)  # type: ignore[arg-type]
            if loc:
                _ensure_host_location(
                    db,
                    host_id=host.id,
                    location_id=loc.id,
                    is_primary=loc_slug == primary,
                )

        if spec.get("sponsor_ready"):
            settings = get_or_create_settings(db, host.id)
            settings.accepting_sponsors = True

    events = list(db.scalars(select(Event)).all())
    legacy_cats = {
        c.id: c for c in db.scalars(select(EventCategory)).all()
    }
    events_by_host: dict = {}
    events_located = 0

    for event in events:
        legacy = legacy_cats.get(event.category_id) if event.category_id else None
        cat_slug = legacy.slug if legacy else None
        tax_cat = categories.get(cat_slug) if cat_slug else None
        if tax_cat is not None:
            event.primary_category_id = tax_cat.id
            _ensure_event_link(
                db,
                event_id=event.id,
                link_type="category",
                taxonomy_id=tax_cat.id,
                taxonomy_slug=tax_cat.slug,
            )
            _ensure_relationship(
                db,
                source_type="event",
                source_id=event.id,
                target_type="category",
                target_id=tax_cat.id,
                relationship_type="primary_category",
            )

        location: Location | None = None
        event_key = None
        if event.slug.startswith(DEMO_EVENT_SLUG_PREFIX):
            event_key = event.slug[len(DEMO_EVENT_SLUG_PREFIX) :]
            kind_slug = DEMO_EVENT_LOCATIONS.get(event_key)
            if kind_slug:
                location = locations_by_kind_slug.get(kind_slug)

        if location is None:
            loc_slug = CITY_TO_LOCATION_SLUG.get(event.city or "")
            if loc_slug:
                # Prefer area, then city, for free-text city labels.
                location = (
                    locations_by_kind_slug.get(("area", loc_slug))
                    or locations_by_kind_slug.get(("city", loc_slug))
                    or locations_by_slug.get(loc_slug)
                )

        if location is not None:
            event.location_id = location.id
            by_kind = {a.kind: a for a in location_ancestors(db, location)}
            by_kind[location.kind] = location
            if by_kind.get("state"):
                event.state = by_kind["state"].name
            if location.kind == "area":
                event.city = location.name
            elif by_kind.get("city"):
                event.city = by_kind["city"].name
            elif location.kind == "city":
                event.city = location.name
            if event.venue is not None:
                event.venue.city = event.city
                event.venue.state = event.state
                if by_kind.get("country"):
                    event.venue.country = by_kind["country"].name
            _ensure_relationship(
                db,
                source_type="event",
                source_id=event.id,
                target_type="location",
                target_id=location.id,
                relationship_type="located_in",
            )
            events_located += 1

        meta = DEMO_CATEGORY_TAXONOMY.get(cat_slug or "", {})
        hashtag_slugs: list[str] = []
        vibe_names: list[str] = []

        for tag_slug in meta.get("tags", []):
            tag = tags.get(tag_slug)
            if tag:
                _ensure_event_link(
                    db,
                    event_id=event.id,
                    link_type="tag",
                    taxonomy_id=tag.id,
                    taxonomy_slug=tag.slug,
                )
                hashtag_slugs.append(tag.slug)

        for vibe_slug in meta.get("vibes", []):
            vibe = vibes.get(vibe_slug)
            if vibe:
                _ensure_event_link(
                    db,
                    event_id=event.id,
                    link_type="vibe",
                    taxonomy_id=vibe.id,
                    taxonomy_slug=vibe.slug,
                )
                vibe_names.append(vibe.name)

        for aud_slug in meta.get("audience", []):
            aud = audiences.get(aud_slug)
            if aud:
                _ensure_event_link(
                    db,
                    event_id=event.id,
                    link_type="audience",
                    taxonomy_id=aud.id,
                    taxonomy_slug=aud.slug,
                )

        # Dual-write legacy free-text fields
        if hashtag_slugs:
            existing_tags = list(event.hashtags or [])
            merged = list(dict.fromkeys([*existing_tags, *hashtag_slugs]))
            event.hashtags = merged
        if vibe_names and not event.vibe:
            event.vibe = vibe_names[0]
        elif vibe_names:
            # Keep primary vibe text in sync with first controlled vibe
            event.vibe = vibe_names[0]

        _ensure_relationship(
            db,
            source_type="event",
            source_id=event.id,
            target_type="host",
            target_id=event.host_id,
            relationship_type="hosted_by",
        )
        events_by_host.setdefault(event.host_id, []).append(event)

    # Sample same_host edges between consecutive events per host
    same_host_edges = 0
    for host_events in events_by_host.values():
        ordered = sorted(host_events, key=lambda e: e.start_datetime)
        for i in range(len(ordered) - 1):
            _ensure_relationship(
                db,
                source_type="event",
                source_id=ordered[i].id,
                target_type="event",
                target_id=ordered[i + 1].id,
                relationship_type="same_host",
                weight=Decimal("0.80"),
                reason="demo_same_host",
            )
            same_host_edges += 1

    db.commit()
    counts["hosts_linked"] = len(hosts)
    counts["events_linked"] = len(events)
    counts["events_located"] = events_located
    counts["same_host_edges"] = same_host_edges
    return counts
