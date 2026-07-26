"""Signed-in credential updates (email and password)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import RefreshToken
from app.auth.schemas import _normalize_auth_email
from app.core.audit import write_audit_log
from app.core.security import hash_password, verify_password
from app.email.service import send_template
from app.users.models import User
from app.users.restrictions import assert_no_restriction
from app.users.service import get_user_by_email
from app.auth.verified_email import assert_verified_email


def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
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

    now = datetime.now(UTC)
    user.password_hash = hash_password(password)
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
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
        deliver_now=True,
    )
    db.commit()


def change_email(
    db: Session,
    *,
    user: User,
    new_email: str,
    current_password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
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

    previous = user.email
    user.email = normalized
    user.is_verified = False
    now = datetime.now(UTC)
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
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
                    "impersonation_id": str(ctx.impersonation_id),
                    "actor_admin_id": str(ctx.actor_admin_id),
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
        deliver_now=True,
    )
    send_template(
        db,
        template="security_alert",
        to=normalized,
        recipient_user_id=user.id,
        context={
            "detail": "This address is now the email for your Pàdéyá account.",
        },
        force=True,
        deliver_now=True,
    )
    from app.auth.email_verification import queue_email_verification_email

    queue_email_verification_email(db, user, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(user)
    return user
