"""Resolve a login identifier (email or Fan Passport username) to a user."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import _normalize_auth_email
from app.passport.models import FanPassport
from app.passport.privacy import normalize_username
from app.users.models import User
from app.users.service import get_user_by_email, get_user_by_id


def normalize_login_identifier(raw: str) -> str:
    stripped = (raw or "").strip()
    if "@" in stripped:
        return _normalize_auth_email(stripped)
    return normalize_username(stripped)


def get_user_for_login(db: Session, login: str) -> User | None:
    if "@" in login:
        return get_user_by_email(db, login)
    passport_user_id = db.scalar(
        select(FanPassport.user_id).where(FanPassport.username == login).limit(1)
    )
    if passport_user_id is None:
        return None
    return get_user_by_id(db, passport_user_id)
