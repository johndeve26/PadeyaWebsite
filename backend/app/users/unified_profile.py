"""Unified display name + username across account, Fan Passport, and Host Legacy."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hosts.models import Host
from app.hosts.service import get_host_by_user_id
from app.passport.models import FanPassport
from app.passport.privacy import is_valid_passport_username, normalize_username
from app.passport.service import ensure_passport
from app.users.models import User


def resolve_user_username(db: Session, user: User) -> str | None:
    passport_username = db.scalar(
        select(FanPassport.username).where(FanPassport.user_id == user.id)
    )
    if passport_username:
        return passport_username
    return db.scalar(select(Host.slug).where(Host.user_id == user.id))


def assert_username_available_for_user(
    db: Session, *, user_id: uuid.UUID, username: str
) -> None:
    passport_clash = db.scalar(
        select(FanPassport.id).where(
            FanPassport.username == username,
            FanPassport.user_id != user_id,
        )
    )
    if passport_clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken. Choose another username.",
        )
    host_clash = db.scalar(
        select(Host.id).where(
            Host.slug == username,
            Host.user_id != user_id,
        )
    )
    if host_clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken. Choose another username.",
        )


def apply_unified_username(db: Session, user: User, raw_username: str) -> str:
    username = normalize_username(raw_username)
    if not is_valid_passport_username(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3–32 characters: lowercase letters, numbers, underscore.",
        )
    assert_username_available_for_user(db, user_id=user.id, username=username)

    passport = ensure_passport(db, user)
    previous_username = passport.username
    passport.username = username

    host = get_host_by_user_id(db, user.id)
    if host is not None:
        host.slug = username

    try:
        from app.core.cache_invalidation import invalidate_fan_public_caches

        invalidate_fan_public_caches(
            username=username,
            previous_username=(
                previous_username
                if previous_username and previous_username != username
                else None
            ),
        )
    except Exception:
        pass
    return username


def apply_unified_display_name(db: Session, user: User, raw_name: str) -> str:
    name = raw_name.strip()
    if len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Display name is too short.",
        )
    user.full_name = name

    passport = db.scalar(select(FanPassport).where(FanPassport.user_id == user.id))
    if passport is not None:
        passport.display_name = name

    host = get_host_by_user_id(db, user.id)
    if host is not None:
        host.display_name = name

    return name
