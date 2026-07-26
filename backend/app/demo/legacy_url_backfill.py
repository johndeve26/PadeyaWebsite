"""Idempotent backfill: padeya.smartlancedesigns.com/demo/... → /demo/...

Only rewrites Pàdéyá-owned legacy static demo asset URLs.
Never touches media.padeya.com, R2 keys, or unrelated third-party URLs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.assets import rewrite_legacy_smartlance_demo_url

logger = logging.getLogger(__name__)


@dataclass
class BackfillStats:
    scanned: int = 0
    updated: int = 0
    unchanged: int = 0
    by_table: dict[str, int] = field(default_factory=dict)
    samples: list[str] = field(default_factory=list)

    def note_update(self, table: str, old: str, new: str) -> None:
        self.updated += 1
        self.by_table[table] = self.by_table.get(table, 0) + 1
        if len(self.samples) < 20:
            self.samples.append(f"{table}: {old} → {new}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "by_table": dict(self.by_table),
            "samples": list(self.samples),
        }


def _rewrite_str(value: str | None, stats: BackfillStats, table: str) -> str | None:
    stats.scanned += 1
    new = rewrite_legacy_smartlance_demo_url(value)
    if new != value and new is not None:
        stats.note_update(table, str(value), str(new))
        return new
    stats.unchanged += 1
    return value


def _rewrite_str_list(
    values: list[Any] | None, stats: BackfillStats, table: str
) -> list[Any] | None:
    if not values:
        return values
    changed = False
    out: list[Any] = []
    for item in values:
        if isinstance(item, str):
            stats.scanned += 1
            new = rewrite_legacy_smartlance_demo_url(item)
            if new != item:
                stats.note_update(table, item, str(new))
                changed = True
                out.append(new)
            else:
                stats.unchanged += 1
                out.append(item)
        else:
            out.append(item)
    return out if changed else values


def backfill_legacy_smartlance_demo_urls(
    db: Session,
    *,
    dry_run: bool = True,
) -> BackfillStats:
    """Scan known media URL columns and rewrite legacy Smartlance demo hosts."""
    stats = BackfillStats()

    from app.events.models import Event, EventMedia, EventPerson
    from app.hosts.models import HostProfile
    from app.memories.models import EventMemoryMedia
    from app.merch.models import EventMerchProduct
    from app.passport.models import FanPassport
    from app.sponsorships.models import Sponsor
    from app.vault.models import VaultItem, VaultMedia

    # Events
    for event in db.scalars(select(Event)).all():
        for attr in ("banner_url", "mobile_banner_url", "social_share_image_url"):
            old = getattr(event, attr)
            new = _rewrite_str(old, stats, "events")
            if new != old:
                setattr(event, attr, new)
        logos = _rewrite_str_list(event.sponsor_logo_urls, stats, "events.sponsor_logo_urls")
        if logos is not event.sponsor_logo_urls:
            event.sponsor_logo_urls = logos

    for media in db.scalars(select(EventMedia)).all():
        new = _rewrite_str(media.url, stats, "event_media")
        if new != media.url:
            media.url = new

    for person in db.scalars(select(EventPerson)).all():
        new = _rewrite_str(person.image_url, stats, "event_people")
        if new != person.image_url:
            person.image_url = new

    # Hosts
    for profile in db.scalars(select(HostProfile)).all():
        for attr in ("avatar_url", "cover_url"):
            old = getattr(profile, attr)
            new = _rewrite_str(old, stats, "host_profiles")
            if new != old:
                setattr(profile, attr, new)

    # Memories
    for media in db.scalars(select(EventMemoryMedia)).all():
        for attr in ("url", "thumbnail_url"):
            old = getattr(media, attr)
            new = _rewrite_str(old, stats, "event_memory_media")
            if new != old:
                setattr(media, attr, new)

    # Merch
    for product in db.scalars(select(EventMerchProduct)).all():
        new = _rewrite_str(product.image_url, stats, "event_merch_products")
        if new != product.image_url:
            product.image_url = new
        gallery = _rewrite_str_list(
            product.gallery_urls, stats, "event_merch_products.gallery_urls"
        )
        if gallery is not product.gallery_urls:
            product.gallery_urls = gallery
        if hasattr(product, "sponsor_logo_url"):
            logo = _rewrite_str(product.sponsor_logo_url, stats, "event_merch_products")
            if logo != product.sponsor_logo_url:
                product.sponsor_logo_url = logo

    # Passport
    for passport in db.scalars(select(FanPassport)).all():
        new = _rewrite_str(passport.avatar_url, stats, "fan_passports")
        if new != passport.avatar_url:
            passport.avatar_url = new

    # Sponsorships
    for sponsor in db.scalars(select(Sponsor)).all():
        for attr in ("logo_url", "cover_image_url"):
            if not hasattr(sponsor, attr):
                continue
            old = getattr(sponsor, attr)
            new = _rewrite_str(old, stats, "sponsors")
            if new != old:
                setattr(sponsor, attr, new)

    # Vault
    for item in db.scalars(select(VaultItem)).all():
        new = _rewrite_str(item.cover_url, stats, "vault_items")
        if new != item.cover_url:
            item.cover_url = new
    for media in db.scalars(select(VaultMedia)).all():
        new = _rewrite_str(media.url, stats, "vault_media")
        if new != media.url:
            media.url = new

    if dry_run:
        db.rollback()
        logger.info(
            "legacy_demo_url_backfill dry_run scanned=%s would_update=%s",
            stats.scanned,
            stats.updated,
        )
    else:
        db.commit()
        logger.info(
            "legacy_demo_url_backfill applied scanned=%s updated=%s",
            stats.scanned,
            stats.updated,
        )
    return stats
