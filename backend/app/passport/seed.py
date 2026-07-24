"""Seed Fan Passport badge catalog."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.passport.constants import DEFAULT_BADGES
from app.passport.models import FanBadge


def seed_fan_badges(db: Session) -> None:
    for item in DEFAULT_BADGES:
        existing = db.scalar(select(FanBadge).where(FanBadge.slug == item["slug"]))
        if existing is None:
            db.add(
                FanBadge(
                    slug=item["slug"],
                    name=item["name"],
                    description=item["description"],
                    criteria_key=item["criteria_key"],
                    is_active=True,
                )
            )
        else:
            existing.name = item["name"]
            existing.description = item["description"]
            existing.criteria_key = item["criteria_key"]
            existing.is_active = True
    db.commit()
