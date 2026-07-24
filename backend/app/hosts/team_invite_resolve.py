"""Resolve host-team invitee input: email or Pàdéyá username."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.hosts.models import Host
from app.passport.models import FanPassport
from app.passport.privacy import is_valid_passport_username, normalize_username
from app.users.models import User
from app.users.service import get_user_by_email, get_user_by_id


@dataclass(frozen=True)
class ResolvedInvitee:
    """Canonical invite target — always stores/sends by email."""

    email: str
    user: User | None
    kind: str  # "email" | "username"
    username: str | None = None


def looks_like_email(raw: str) -> bool:
    """True for address-shaped values (not bare @username)."""
    value = (raw or "").strip().lower()
    # Bare @username has no domain segment with a dot.
    if value.startswith("@") or value.count("@") != 1 or " " in value:
        return False
    local, _, domain = value.partition("@")
    return bool(local) and bool(domain) and "." in domain


def looks_like_username(raw: str) -> bool:
    """True when input starts with @ or matches passport username format."""
    value = (raw or "").strip()
    if not value:
        return False
    if value.startswith("@"):
        # Leading @ always means username flow (even before format check).
        return is_valid_passport_username(normalize_username(value))
    return is_valid_passport_username(normalize_username(value))


def normalize_invitee_input(raw: str) -> str:
    """
    One invite field: trim spaces, then email vs username.

    - Email-shaped → lowercase email
    - Starts with @ or username format → strip leading @, lowercase (case-insensitive)
    """
    value = (raw or "").strip()
    if not value:
        raise ValueError("Email or Pàdéyá username is required")
    if looks_like_email(value):
        return value.lower()
    if value.startswith("@") or looks_like_username(value):
        key = normalize_username(value)  # strips leading @, lowercases
        if not is_valid_passport_username(key):
            raise ValueError("Enter a valid Pàdéyá username (letters, numbers, underscore)")
        return f"@{key}"
    raise ValueError("Enter an email address or Pàdéyá username (with or without @)")


def _user_by_passport_username(db: Session, username: str) -> User | None:
    key = normalize_username(username)
    passport = db.scalar(
        select(FanPassport).where(func.lower(FanPassport.username) == key)
    )
    if passport is None:
        return None
    return get_user_by_id(db, passport.user_id)


def _user_by_host_slug(db: Session, username: str) -> User | None:
    """Legacy / host slug (@handle) fallback."""
    key = normalize_username(username)
    host = db.scalar(select(Host).where(func.lower(Host.slug) == key))
    if host is None:
        return None
    return get_user_by_id(db, host.user_id)


def preview_invite_identifier(db: Session, raw: str) -> dict:
    """
    Host-safe invitee preview while typing.

    Never returns account email, phone, or private Passport fields.
    """
    from app.passport.privacy import is_publicly_reachable

    value = (raw or "").strip()
    if not value:
        return {
            "invite_method": None,
            "valid": False,
            "found": False,
            "display_name": None,
            "username": None,
            "avatar_url": None,
            "masked_email": None,
            "message": None,
        }

    if looks_like_email(value):
        email = value.lower()
        local, _, domain = email.partition("@")
        keep = local[:1] if local else "*"
        masked = f"{keep}***@{domain}" if domain else "***"
        return {
            "invite_method": "email",
            "valid": True,
            "found": True,
            "display_name": None,
            "username": None,
            "avatar_url": None,
            "masked_email": masked,
            "message": "Invite will be sent to this email.",
        }

    # Username-shaped (with or without @) — wait until format is valid.
    key = normalize_username(value)
    if value.startswith("@") or looks_like_username(value):
        if not is_valid_passport_username(key):
            return {
                "invite_method": "username",
                "valid": False,
                "found": False,
                "display_name": None,
                "username": f"@{key}" if key else None,
                "avatar_url": None,
                "masked_email": None,
                "message": None,
            }

        user = _user_by_passport_username(db, key) or _user_by_host_slug(db, key)
        if user is None:
            return {
                "invite_method": "username",
                "valid": True,
                "found": False,
                "display_name": None,
                "username": f"@{key}",
                "avatar_url": None,
                "masked_email": None,
                "message": "No Pàdéyá user found with that username.",
            }

        passport = db.scalar(
            select(FanPassport).where(FanPassport.user_id == user.id)
        )
        display_name = None
        avatar_url = None
        if passport is not None:
            display_name = passport.display_name or None
            if passport.avatar_url and is_publicly_reachable(passport.visibility):
                avatar_url = passport.avatar_url
        if not display_name:
            display_name = user.full_name or f"@{key}"

        return {
            "invite_method": "username",
            "valid": True,
            "found": True,
            "display_name": display_name,
            "username": f"@{key}",
            "avatar_url": avatar_url,
            "masked_email": None,
            "message": "This user will receive an invite.",
        }

    return {
        "invite_method": None,
        "valid": False,
        "found": False,
        "display_name": None,
        "username": None,
        "avatar_url": None,
        "masked_email": None,
        "message": None,
    }


def resolve_invitee(db: Session, raw: str) -> ResolvedInvitee:
    """
    Resolve invite input to the email used for the pending invite row + outbox.

    - Email → invite that address (user may or may not exist yet)
    - @username / username → must match a Pàdéyá Fan Passport username
      (or host Legacy slug); invite goes to that account's email
    """
    normalized = normalize_invitee_input(raw)
    if looks_like_email(normalized):
        email = normalized.lower()
        return ResolvedInvitee(
            email=email,
            user=get_user_by_email(db, email),
            kind="email",
            username=None,
        )

    username = normalize_username(normalized)
    user = _user_by_passport_username(db, username) or _user_by_host_slug(
        db, username
    )
    if user is None or not (user.email or "").strip():
        raise HTTPException(
            status_code=404,
            detail="No Pàdéyá user found with that username.",
        )
    return ResolvedInvitee(
        email=user.email.strip().lower(),
        user=user,
        kind="username",
        username=username,
    )
