"""Registration username validation and availability."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hosts.models import Host
from app.passport.models import FanPassport
from app.passport.privacy import (
    is_valid_passport_username,
    normalize_username,
    slugify_username_from_name,
)


def display_name_from_username(username: str) -> str:
    """Human-readable default for tickets, passport, and profile."""
    pretty = username.replace("_", " ").strip().title()
    return (pretty or username)[:200]


def resolve_register_username(
    *,
    username: str | None,
    full_name: str | None,
) -> str:
    """Prefer explicit username; legacy callers may send full_name only."""
    if username and username.strip():
        key = normalize_username(username)
    elif full_name and full_name.strip():
        key = slugify_username_from_name(full_name.strip())
    else:
        raise ValueError("Username is required.")
    if not is_valid_passport_username(key):
        raise ValueError(
            "Username must be 3–32 characters: lowercase letters, numbers, underscore."
        )
    return key


def assert_username_available_for_registration(db: Session, username: str) -> None:
    taken_passport = db.scalar(
        select(FanPassport.id).where(FanPassport.username == username).limit(1)
    )
    if taken_passport is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken. Choose another username.",
        )
    taken_host = db.scalar(
        select(Host.id).where(Host.slug == username).limit(1)
    )
    if taken_host is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken. Choose another username.",
        )
