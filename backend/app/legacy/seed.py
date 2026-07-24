"""Seed default Legacy tiers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.legacy.constants import DEFAULT_TIERS
from app.legacy.models import LegacyTier

# Known misspellings → canonical product name (Pàdéyá).
_BRAND_CORRECTIONS = (
    ("Pàdéyé", "Pàdéyá"),
    ("Padéyé", "Pàdéyá"),
    ("Padéyá", "Pàdéyá"),
)


def _normalize_brand_copy(text: str) -> str:
    for wrong, right in _BRAND_CORRECTIONS:
        text = text.replace(wrong, right)
    return text


def seed_legacy_tiers(db: Session) -> None:
    for item in DEFAULT_TIERS:
        existing = db.scalar(select(LegacyTier).where(LegacyTier.slug == item["slug"]))
        if existing is None:
            db.add(
                LegacyTier(
                    slug=item["slug"],
                    name=item["name"],
                    rank=item["rank"],
                    min_score=item["min_score"],
                    description=item["description"],
                    requirements=item["requirements"],
                    is_active=True,
                )
            )
            continue

        # Keep admin-edited thresholds; fill gaps and correct brand spelling only.
        if existing.description is None:
            existing.description = item["description"]
        else:
            normalized = _normalize_brand_copy(existing.description)
            if normalized != existing.description:
                existing.description = normalized

        if existing.requirements is None:
            existing.requirements = item["requirements"]

    db.commit()
