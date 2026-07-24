"""Public Fan Passport Directory — opt-in listing only."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.passport.models import FanBadge, FanPassport, UserBadge
from app.passport.privacy import VISIBILITY_PUBLIC
from app.passport.public_service import (
    count_fan_connections,
    favorite_cities_for_user,
    public_badges,
    reviews_written_count,
)
from app.users.models import User

DIRECTORY_SORTS = frozenset(
    {
        "recently_active",
        "most_badges",
        "most_events",
        "most_reviews",
        "newest",
    }
)


def is_directory_eligible(passport: FanPassport, user: User | None) -> bool:
    if user is None or not user.is_active:
        return False
    if passport.admin_hidden_at is not None:
        return False
    if passport.visibility != VISIBILITY_PUBLIC:
        return False
    if not passport.appear_in_directory:
        return False
    if not passport.username:
        return False
    return True


def _directory_base_query():
    return (
        select(FanPassport, User)
        .join(User, User.id == FanPassport.user_id)
        .where(
            FanPassport.visibility == VISIBILITY_PUBLIC,
            FanPassport.appear_in_directory.is_(True),
            FanPassport.admin_hidden_at.is_(None),
            FanPassport.username.is_not(None),
            User.is_active.is_(True),
        )
    )


def serialize_directory_card(db: Session, passport: FanPassport) -> dict:
    badges = public_badges(db, passport) if passport.show_badges else []
    cities = (
        favorite_cities_for_user(db, passport.user_id)
        if passport.show_city_category_stats
        else []
    )
    categories = (
        list(passport.favorite_categories or [])
        if passport.show_city_category_stats
        else []
    )
    reviews = (
        reviews_written_count(db, passport.user_id) if passport.show_reviews else 0
    )
    top_badges = [{"slug": b["slug"], "name": b["name"]} for b in badges[:3]]
    latest = badges[0] if badges else None
    return {
        "username": passport.username,
        "user_id": passport.user_id,
        "display_name": passport.display_name or "New Passport",
        "avatar_url": passport.avatar_url,
        "tagline": passport.tagline,
        "city_label": cities[0] if cities else None,
        "favorite_scene": categories[0] if categories else None,
        "top_badges": top_badges,
        "events_attended": (
            passport.events_attended if passport.show_attended_events else 0
        ),
        "hosts_followed": (
            passport.hosts_followed if passport.show_followed_hosts else 0
        ),
        "reviews_written": reviews,
        "cities_explored": len(cities),
        "connections_count": count_fan_connections(db, passport.user_id),
        "badges_earned_count": len(badges),
        "vault_unlocks_count": (
            passport.vault_unlocks if passport.show_vault_unlocks else 0
        ),
        "latest_badge_name": latest["name"] if latest else None,
        "is_superfan": passport.is_superfan,
        "share_path": f"/f/{passport.username}",
        "stats_limited": not (
            passport.show_badges
            or passport.show_attended_events
            or passport.show_followed_hosts
        ),
    }


def list_directory_passports(
    db: Session,
    *,
    q: str | None = None,
    city: str | None = None,
    category: str | None = None,
    badge: str | None = None,
    sort: str = "recently_active",
    page: int = 1,
    limit: int = 24,
    has_reviews: bool | None = None,
    has_vault_unlocks: bool | None = None,
    min_events: int | None = None,
    max_events: int | None = None,
) -> dict:
    page = max(1, page)
    limit = min(max(1, limit), 48)
    sort_key = sort if sort in DIRECTORY_SORTS else "recently_active"

    stmt = _directory_base_query()
    if q:
        needle = q.strip().lstrip("@").lower()
        like = f"%{needle}%"
        raw = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                func.lower(FanPassport.username).like(like),
                FanPassport.display_name.ilike(raw),
            )
        )
    if min_events is not None:
        stmt = stmt.where(FanPassport.events_attended >= min_events)
    if max_events is not None:
        stmt = stmt.where(FanPassport.events_attended <= max_events)
    if has_vault_unlocks is True:
        stmt = stmt.where(
            FanPassport.show_vault_unlocks.is_(True),
            FanPassport.vault_unlocks > 0,
        )

    if badge:
        badge_key = badge.strip().lower()
        badge_row = db.scalar(
            select(FanBadge).where(
                or_(
                    FanBadge.slug == badge_key,
                    func.lower(FanBadge.name) == badge_key,
                ),
                FanBadge.is_active.is_(True),
            )
        )
        if not badge_row:
            return {"items": [], "page": page, "limit": limit, "total": 0}
        awarded_ids = select(UserBadge.user_id).where(
            UserBadge.badge_id == badge_row.id
        )
        stmt = stmt.where(FanPassport.user_id.in_(awarded_ids))

    if sort_key == "most_events":
        stmt = stmt.order_by(
            FanPassport.events_attended.desc(), FanPassport.updated_at.desc()
        )
    elif sort_key == "newest":
        stmt = stmt.order_by(FanPassport.created_at.desc())
    else:
        stmt = stmt.order_by(FanPassport.updated_at.desc())

    rows = list(db.execute(stmt).all())
    items: list[dict] = []
    for passport, user in rows:
        if not is_directory_eligible(passport, user):
            continue
        card = serialize_directory_card(db, passport)
        if city:
            cities = favorite_cities_for_user(db, passport.user_id)
            if city.strip().lower() not in {c.lower() for c in cities}:
                continue
        if category:
            cats = [str(c).lower() for c in (passport.favorite_categories or [])]
            if category.strip().lower() not in cats:
                continue
        if has_reviews is True and card["reviews_written"] < 1:
            continue
        if has_reviews is False and card["reviews_written"] > 0:
            continue
        items.append(card)

    if sort_key == "most_reviews":
        items.sort(key=lambda c: (-c["reviews_written"], c["username"] or ""))
    elif sort_key == "most_badges":
        items.sort(key=lambda c: (-c["badges_earned_count"], c["username"] or ""))

    total = len(items)
    start = (page - 1) * limit
    page_items = items[start : start + limit]
    return {"items": page_items, "page": page, "limit": limit, "total": total}


def list_admin_fans(
    db: Session,
    *,
    q: str | None = None,
    visibility: str | None = None,
    directory_only: bool | None = None,
    include_hidden: bool = True,
    page: int = 1,
    limit: int = 40,
) -> dict:
    page = max(1, page)
    limit = min(max(1, limit), 100)
    stmt = select(FanPassport, User).join(User, User.id == FanPassport.user_id)
    if q:
        raw = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                FanPassport.username.ilike(raw),
                FanPassport.display_name.ilike(raw),
                User.email.ilike(raw),
            )
        )
    if visibility:
        stmt = stmt.where(FanPassport.visibility == visibility.strip().lower())
    if directory_only is True:
        stmt = stmt.where(
            FanPassport.visibility == VISIBILITY_PUBLIC,
            FanPassport.appear_in_directory.is_(True),
        )
    if not include_hidden:
        stmt = stmt.where(FanPassport.admin_hidden_at.is_(None))
    stmt = stmt.order_by(FanPassport.updated_at.desc())
    rows = list(db.execute(stmt).all())
    total = len(rows)
    start = (page - 1) * limit
    page_rows = rows[start : start + limit]
    items = []
    for passport, user in page_rows:
        items.append(
            {
                "user_id": str(user.id),
                "username": passport.username,
                "display_name": passport.display_name,
                "visibility": passport.visibility,
                "appear_in_directory": passport.appear_in_directory,
                "admin_hidden": passport.admin_hidden_at is not None,
                "admin_hidden_at": passport.admin_hidden_at,
                "admin_hidden_reason": passport.admin_hidden_reason,
                "user_active": user.is_active,
                "share_path": (
                    f"/f/{passport.username}" if passport.username else None
                ),
                "events_attended": passport.events_attended,
            }
        )
    return {"items": items, "page": page, "limit": limit, "total": total}


def admin_hide_fan(
    db: Session,
    *,
    actor: User,
    user_id: UUID,
    reason: str,
) -> FanPassport:
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A moderation reason is required.",
        )
    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    passport.admin_hidden_at = datetime.now(UTC)
    passport.admin_hidden_reason = reason[:500]
    write_audit_log(
        db,
        action="passport.admin.hide",
        actor_user_id=actor.id,
        resource_type="fan_passport",
        resource_id=str(passport.id),
        details={"user_id": str(user_id), "reason": reason[:200]},
    )
    db.commit()
    db.refresh(passport)
    try:
        from app.core.cache_invalidation import invalidate_fan_public_caches

        invalidate_fan_public_caches(username=passport.username)
    except Exception:
        pass
    return passport


def admin_restore_fan(
    db: Session,
    *,
    actor: User,
    user_id: UUID,
    reason: str | None = None,
) -> FanPassport:
    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user_id))
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    passport.admin_hidden_at = None
    passport.admin_hidden_reason = None
    write_audit_log(
        db,
        action="passport.admin.restore",
        actor_user_id=actor.id,
        resource_type="fan_passport",
        resource_id=str(passport.id),
        details={
            "user_id": str(user_id),
            "reason": (reason or "").strip()[:200] or None,
        },
    )
    db.commit()
    db.refresh(passport)
    try:
        from app.core.cache_invalidation import invalidate_fan_public_caches

        invalidate_fan_public_caches(username=passport.username)
    except Exception:
        pass
    return passport
