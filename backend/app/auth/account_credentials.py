"""Signed-in credential updates (email and password)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import EmailChangeToken, RefreshToken
from app.auth.schemas import _normalize_auth_email
from app.core.audit import write_audit_log
from app.core.security import (
    generate_password_reset_code,
    hash_password,
    hash_token,
    normalize_password_reset_code,
    verify_password,
)
from app.email.service import send_template
from app.users.models import User
from app.users.restrictions import assert_no_restriction
from app.users.service import get_user_by_email
from app.auth.verified_email import assert_verified_email

EMAIL_CHANGE_TTL = timedelta(hours=1)
EMAIL_CHANGE_CONFIRM_INVALID = "Invalid or expired confirmation code."
EMAIL_CHANGE_PENDING_MESSAGE = (
    "We sent a confirmation code to your new email. Enter it below to finish."
)


def revoke_other_sessions(
    db: Session,
    *,
    user_id,
    keep_refresh_token: str | None = None,
) -> None:
    """Sign out every device except the caller's current refresh session."""
    now = datetime.now(UTC)
    keep = (keep_refresh_token or "").strip()
    stmt = (
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    if keep:
        stmt = stmt.where(RefreshToken.token_hash != hash_token(keep))
    db.execute(stmt)


def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    keep_refresh_token: str | None = None,
) -> None:
    from app.auth.impersonation_context import get_impersonation_context

    assert_no_restriction(db, user.id, "read_only_account")
    assert_verified_email(user)
    current = (current_password or "").strip()
    password = (new_password or "").strip()
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )
    ctx = get_impersonation_context()
    if ctx is None:
        if not current:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required",
            )
        if not verify_password(current, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )
    else:
        from app.admin.impersonation_guards import (
            IMPERSONATION_SENSITIVE_ACTION_DETAIL,
        )
        from app.admin.impersonation_scopes import SCOPE_CREDENTIALS

        if not ctx.has_scope(SCOPE_CREDENTIALS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=IMPERSONATION_SENSITIVE_ACTION_DETAIL,
            )
    if verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a password different from your current one",
        )

    user.password_hash = hash_password(password)
    # Impersonation: sign out all of the target's devices. Own session: keep this device.
    revoke_other_sessions(
        db,
        user_id=user.id,
        keep_refresh_token=None if ctx is not None else keep_refresh_token,
    )
    write_audit_log(
        db,
        action=(
            "auth.password_changed_via_impersonation"
            if ctx is not None
            else "auth.password_changed"
        ),
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
        details=(
            {
                "impersonation_id": str(ctx.impersonation_id),
                "actor_admin_id": str(ctx.actor_admin_id),
            }
            if ctx is not None
            else None
        ),
    )
    send_template(
        db,
        template="security_alert",
        to=user.email,
        recipient_user_id=user.id,
        context={
            "detail": "Your Pàdéyá password was changed. If this was not you, contact support immediately.",
        },
        force=True,
        # Enqueue only — sync SMTP can exceed the FE request timeout.
        deliver_now=False,
    )
    db.commit()


def _validate_email_change_inputs(
    db: Session,
    *,
    user: User,
    new_email: str,
    current_password: str,
) -> tuple[str, object | None]:
    """Shared checks for request + impersonation apply. Returns (normalized, ctx)."""
    from app.auth.impersonation_context import get_impersonation_context

    assert_no_restriction(db, user.id, "read_only_account")
    assert_verified_email(user)
    try:
        normalized = _normalize_auth_email(new_email)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address",
        ) from exc

    current = (current_password or "").strip()
    ctx = get_impersonation_context()
    if ctx is None:
        if not current:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required",
            )
        if not verify_password(current, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )
    else:
        from app.admin.impersonation_guards import (
            IMPERSONATION_SENSITIVE_ACTION_DETAIL,
        )
        from app.admin.impersonation_scopes import SCOPE_CREDENTIALS

        if not ctx.has_scope(SCOPE_CREDENTIALS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=IMPERSONATION_SENSITIVE_ACTION_DETAIL,
            )

    if normalized == user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That is already your email address",
        )

    taken = get_user_by_email(db, normalized)
    if taken is not None and taken.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already registered to another account",
        )
    return normalized, ctx


def _apply_email_change(
    db: Session,
    *,
    user: User,
    normalized: str,
    ctx: object | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    keep_refresh_token: str | None = None,
) -> User:
    previous = user.email
    user.email = normalized
    user.is_verified = False
    # Impersonation: revoke all. Own session: keep this device signed in.
    revoke_other_sessions(
        db,
        user_id=user.id,
        keep_refresh_token=None if ctx is not None else keep_refresh_token,
    )
    write_audit_log(
        db,
        action=(
            "auth.email_changed_via_impersonation"
            if ctx is not None
            else "auth.email_changed"
        ),
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        details={
            "previous_email": previous,
            "new_email": normalized,
            **(
                {
                    "impersonation_id": str(getattr(ctx, "impersonation_id")),
                    "actor_admin_id": str(getattr(ctx, "actor_admin_id")),
                }
                if ctx is not None
                else {}
            ),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    send_template(
        db,
        template="security_alert",
        to=previous,
        recipient_user_id=user.id,
        context={
            "detail": f"Your Pàdéyá sign-in email was changed to {normalized}. If this was not you, contact support immediately.",
        },
        force=True,
        deliver_now=False,
    )
    send_template(
        db,
        template="security_alert",
        to=normalized,
        recipient_user_id=user.id,
        context={
            "detail": "This address is now the email for your Pàdéyá account. Verify it to keep using your dashboard.",
        },
        force=True,
        deliver_now=False,
    )
    from app.auth.email_verification import queue_email_verification_email

    queue_email_verification_email(
        db,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
        deliver_now=False,
    )
    db.commit()
    db.refresh(user)
    return user


def request_email_change(
    db: Session,
    *,
    user: User,
    new_email: str,
    current_password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str] | User:
    """Start email change.

    Normal sessions: send a code to the new address and leave the current email
    unchanged until ``confirm_email_change``.

    Impersonation with credentials scope: apply immediately (support recovery).
    """
    normalized, ctx = _validate_email_change_inputs(
        db,
        user=user,
        new_email=new_email,
        current_password=current_password,
    )
    if ctx is not None:
        return _apply_email_change(
            db,
            user=user,
            normalized=normalized,
            ctx=ctx,
            ip_address=ip_address,
            user_agent=user_agent,
            keep_refresh_token=None,
        )

    now = datetime.now(UTC)
    db.execute(
        update(EmailChangeToken)
        .where(
            EmailChangeToken.user_id == user.id,
            EmailChangeToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw_code = generate_password_reset_code()
    db.add(
        EmailChangeToken(
            user_id=user.id,
            new_email=normalized,
            code_hash=hash_token(raw_code),
            expires_at=now + EMAIL_CHANGE_TTL,
        )
    )
    write_audit_log(
        db,
        action="auth.email_change_requested",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        details={"pending_email": normalized},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    send_template(
        db,
        template="confirm_email_change",
        to=normalized,
        recipient_user_id=user.id,
        context={
            "full_name": user.full_name,
            "verification_code": raw_code,
            "expiry_hours": "1",
            "pending_email": normalized,
            "cta_path": "/dashboard/settings",
        },
        force=True,
        deliver_now=False,
    )
    send_template(
        db,
        template="security_alert",
        to=user.email,
        recipient_user_id=user.id,
        context={
            "detail": (
                f"A request was made to change your Pàdéyá sign-in email to {normalized}. "
                "If this was not you, change your password immediately and contact support."
            ),
        },
        force=True,
        deliver_now=False,
    )
    db.commit()
    return EMAIL_CHANGE_PENDING_MESSAGE, normalized


def confirm_email_change(
    db: Session,
    *,
    user: User,
    code: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    keep_refresh_token: str | None = None,
) -> User:
    """Apply a pending email change after the user enters the code."""
    from app.auth.impersonation_context import get_impersonation_context

    assert_no_restriction(db, user.id, "read_only_account")
    if get_impersonation_context() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirm email change from the account owner's session.",
        )

    raw_code = normalize_password_reset_code(code or "")
    if len(raw_code) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_CHANGE_CONFIRM_INVALID,
        )

    code_hash = hash_token(raw_code)
    row = db.scalar(
        select(EmailChangeToken)
        .where(
            EmailChangeToken.user_id == user.id,
            EmailChangeToken.code_hash == code_hash,
            EmailChangeToken.used_at.is_(None),
        )
        .order_by(EmailChangeToken.created_at.desc())
        .limit(1)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_CHANGE_CONFIRM_INVALID,
        )
    now = datetime.now(UTC)
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_CHANGE_CONFIRM_INVALID,
        )

    taken = get_user_by_email(db, row.new_email)
    if taken is not None and taken.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already registered to another account",
        )

    row.used_at = now
    return _apply_email_change(
        db,
        user=user,
        normalized=row.new_email,
        ctx=None,
        ip_address=ip_address,
        user_agent=user_agent,
        keep_refresh_token=keep_refresh_token,
    )
