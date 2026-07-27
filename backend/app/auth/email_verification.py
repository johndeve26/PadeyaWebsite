"""Email verification tokens, outbox delivery, and confirmation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import EmailVerificationToken
from app.core.audit import write_audit_log
from app.core.security import (
    generate_password_reset_code,
    generate_password_reset_token,
    hash_token,
    normalize_password_reset_code,
)
from app.email.config import email_runtime
from app.email.service import send_template
from app.users.models import User

EMAIL_VERIFICATION_TTL = timedelta(hours=24)
EMAIL_VERIFICATION_REQUEST_COOLDOWN = timedelta(minutes=1)

EMAIL_VERIFICATION_REQUEST_MESSAGE = (
    "If your account needs verification, we sent an email with instructions."
)
EMAIL_VERIFICATION_SENT_MESSAGE = (
    "We sent a verification code to your email. It expires in 24 hours."
)
EMAIL_VERIFICATION_ALREADY_VERIFIED_MESSAGE = "Your email is already verified."
EMAIL_VERIFICATION_CONFIRM_INVALID = "Invalid or expired verification link or code."
EMAIL_VERIFICATION_CONFIRM_SUCCESS = "Your email is verified."


def seconds_until_verification_request_allowed(db: Session, user_id: uuid.UUID) -> int:
    latest = db.scalar(
        select(EmailVerificationToken.created_at)
        .where(EmailVerificationToken.user_id == user_id)
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    if latest is None:
        return 0
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    remaining = EMAIL_VERIFICATION_REQUEST_COOLDOWN - (datetime.now(UTC) - latest)
    if remaining.total_seconds() <= 0:
        return 0
    return int(remaining.total_seconds()) + 1


def assert_verification_request_allowed(db: Session, user: User) -> None:
    wait = seconds_until_verification_request_allowed(db, user.id)
    if wait > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Wait {wait} seconds before requesting another verification email.",
        )


def queue_email_verification_email(
    db: Session,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    audit_action: str = "auth.email_verification_sent",
    deliver_now: bool = True,
) -> None:
    """Invalidate unused tokens, create link + code, enqueue verify_email."""
    if user.is_verified:
        return

    now = datetime.now(UTC)
    db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw_token = generate_password_reset_token()
    raw_code = generate_password_reset_code()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            code_hash=hash_token(raw_code),
            expires_at=now + EMAIL_VERIFICATION_TTL,
        )
    )

    cfg = email_runtime(db=db)
    verify_path = f"/verify?token={quote(raw_token, safe='')}"
    send_template(
        db,
        template="verify_email",
        to=user.email,
        recipient_user_id=user.id,
        context={
            "full_name": user.full_name,
            "verification_code": raw_code,
            "expiry_hours": str(int(EMAIL_VERIFICATION_TTL.total_seconds() // 3600)),
            "cta_path": verify_path,
            "cta_url": f"{cfg.app_base_url}{verify_path}",
        },
        dedupe_key=f"user:{user.id}:verify_email:{hash_token(raw_token)[:16]}",
        force=True,
        deliver_now=deliver_now,
    )
    write_audit_log(
        db,
        action=audit_action,
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )


def request_email_verification_for_user(
    db: Session,
    *,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Logged-in resend. Returns a user-facing status message."""
    if user.is_verified:
        return EMAIL_VERIFICATION_ALREADY_VERIFIED_MESSAGE
    wait = seconds_until_verification_request_allowed(db, user.id)
    if wait > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Wait {wait} seconds before requesting another verification email.",
        )
    queue_email_verification_email(
        db,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
        audit_action="auth.email_verification_resent",
    )
    db.commit()
    return EMAIL_VERIFICATION_SENT_MESSAGE


def _find_active_verification_row(
    db: Session,
    *,
    user_id: uuid.UUID,
    token_hash: str | None = None,
    code_hash: str | None = None,
) -> EmailVerificationToken | None:
    if not token_hash and not code_hash:
        return None
    q = (
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
        )
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    if token_hash:
        q = q.where(EmailVerificationToken.token_hash == token_hash)
    if code_hash:
        q = q.where(EmailVerificationToken.code_hash == code_hash)
    row = db.scalar(q)
    if row is None:
        return None
    now = datetime.now(UTC)
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        return None
    return row


def confirm_email_verification(
    db: Session,
    *,
    token: str | None = None,
    code: str | None = None,
    user: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    raw_token = (token or "").strip()
    raw_code = normalize_password_reset_code(code or "") if code else ""

    resolved_user: User | None = user
    row: EmailVerificationToken | None = None

    if raw_token:
        token_hash = hash_token(raw_token)
        row = db.scalar(
            select(EmailVerificationToken)
            .where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.used_at.is_(None),
            )
            .order_by(EmailVerificationToken.created_at.desc())
            .limit(1)
        )
        if row is not None:
            now = datetime.now(UTC)
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= now:
                row = None
            else:
                resolved_user = db.get(User, row.user_id)

    if row is None and raw_code and len(raw_code) == 6:
        if resolved_user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=EMAIL_VERIFICATION_CONFIRM_INVALID,
            )
        code_hash = hash_token(raw_code)
        row = _find_active_verification_row(
            db, user_id=resolved_user.id, code_hash=code_hash
        )

    if resolved_user is None or row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_VERIFICATION_CONFIRM_INVALID,
        )

    if not resolved_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_VERIFICATION_CONFIRM_INVALID,
        )

    if resolved_user.is_verified:
        now = datetime.now(UTC)
        row.used_at = now
        db.commit()
        return resolved_user

    now = datetime.now(UTC)
    resolved_user.is_verified = True
    row.used_at = now
    write_audit_log(
        db,
        action="auth.email_verified",
        actor_user_id=resolved_user.id,
        resource_type="user",
        resource_id=str(resolved_user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(resolved_user)
    from app.email.admin_triggers import admin_notify_user_email_verified

    admin_notify_user_email_verified(
        db,
        user_id=resolved_user.id,
        user_name=resolved_user.full_name,
        user_email=resolved_user.email,
        username=resolved_user.email.split("@")[0],
        verified_at=now.isoformat(),
    )
    return resolved_user
