"""Seed default event categories."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.constants import DEFAULT_CATEGORIES
from app.events.models import EventCategory


def seed_event_categories(db: Session) -> None:
    for name, slug, description in DEFAULT_CATEGORIES:
        existing = db.scalar(select(EventCategory).where(EventCategory.slug == slug))
        if existing is None:
            db.add(
                EventCategory(
                    name=name,
                    slug=slug,
                    description=description,
                    is_active=True,
                )
            )
    db.commit()
