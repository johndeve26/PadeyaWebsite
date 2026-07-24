"""Create password-reset codes and send reset emails."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import PasswordResetToken
from app.core.security import generate_password_reset_code, hash_token
from app.email.config import email_runtime
from app.email.service import send_template
from app.users.models import User

PASSWORD_RESET_TTL = timedelta(minutes=5)
# Minimum wait between reset-code emails per account (30s / 1m / 2m — default 1m).
PASSWORD_RESET_REQUEST_COOLDOWN = timedelta(minutes=1)


def seconds_until_password_reset_request_allowed(
    db: Session, user_id: uuid.UUID
) -> int:
    latest = db.scalar(
        select(PasswordResetToken.created_at)
        .where(PasswordResetToken.user_id == user_id)
        .order_by(PasswordResetToken.created_at.desc())
        .limit(1)
    )
    if latest is None:
        return 0
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    remaining = PASSWORD_RESET_REQUEST_COOLDOWN - (datetime.now(UTC) - latest)
    if remaining.total_seconds() <= 0:
        return 0
    return int(remaining.total_seconds()) + 1


def assert_password_reset_request_allowed(db: Session, user: User) -> None:
    wait = seconds_until_password_reset_request_allowed(db, user.id)
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Wait {wait} seconds before requesting another reset code.",
        )


def find_valid_password_reset_token(
    db: Session, *, email: str, code: str
) -> tuple[User, PasswordResetToken]:
    """Resolve user + active reset row for email/code, or raise 400."""
    from app.core.security import hash_token, normalize_password_reset_code
    from app.users.service import get_user_by_email

    normalized_email = email.lower().strip()
    raw_code = normalize_password_reset_code(code)
    if len(raw_code) != 6:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user = get_user_by_email(db, normalized_email)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    row = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.token_hash == hash_token(raw_code),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .limit(1)
    )
    now = datetime.now(UTC)
    expires_at = row.expires_at if row is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if row is None or row.used_at is not None or expires_at is None or expires_at <= now:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    return user, row


def queue_password_reset_email(db: Session, user: User) -> None:
    """Invalidate unused codes, create a new one, and email the user."""
    now = datetime.now(UTC)
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw = generate_password_reset_code()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=now + PASSWORD_RESET_TTL,
        )
    )
    cfg = email_runtime(db=db)
    reset_path = f"/reset-password?email={quote(user.email)}"
    send_template(
        db,
        template="password_reset",
        to=user.email,
        recipient_user_id=user.id,
        context={
            "reset_code": raw,
            "cta_path": reset_path,
            "cta_url": f"{cfg.app_base_url}{reset_path}",
            "full_name": user.full_name,
        },
        force=True,
        deliver_now=True,
    )
