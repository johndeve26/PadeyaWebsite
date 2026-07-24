"""Authentication business logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import RefreshToken
from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.users.constants import DEFAULT_REGISTER_ROLE
from app.users.models import User
from app.users.service import (
    get_role_by_name,
    get_user_by_email,
    get_user_by_id,
    serialize_user,
    user_permission_codes,
    user_role_names,
)

settings = get_settings()


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    username: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, dict[str, str]]:
    from app.auth.register_username import (
        assert_username_available_for_registration,
        display_name_from_username,
    )

    normalized = email.lower().strip()
    if get_user_by_email(db, normalized):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already registered. Log in or use a different email.",
        )

    assert_username_available_for_registration(db, username)

    display = display_name_from_username(username)

    role = get_role_by_name(db, DEFAULT_REGISTER_ROLE)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default role is not seeded",
        )

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        full_name=display,
        roles=[role],
    )
    db.add(user)
    db.flush()

    from app.fan_connect.eligibility import ensure_connect_settings
    from app.passport.service import ensure_passport

    ensure_passport(db, user, preferred_username=username, display_name=display)
    # Connect + directory discoverability default on; fans can untick later.
    ensure_connect_settings(db, user)

    write_audit_log(
        db,
        action="auth.register",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "username": username},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    from app.email.service import send_template

    send_template(
        db,
        template="welcome",
        to=user.email,
        recipient_user_id=user.id,
        context={"full_name": user.full_name},
        dedupe_key=f"user:{user.id}:welcome",
        deliver_now=True,
    )
    from app.auth.email_verification import queue_email_verification_email

    queue_email_verification_email(db, user, ip_address=ip_address, user_agent=user_agent)
    from app.email.admin_triggers import admin_notify_user_registered
    from datetime import UTC, datetime

    admin_notify_user_registered(
        db,
        user_id=user.id,
        user_name=user.full_name,
        user_email=user.email,
        username=username,
        registered_at=datetime.now(UTC).isoformat(),
    )
    tokens = issue_token_pair(
        db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(user)
    return user, tokens


PASSWORD_RESET_REQUEST_MESSAGE = (
    "If an account exists for that email, we sent a 6-character reset code."
)


def request_password_reset(
    db: Session,
    *,
    email: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Always completes without revealing whether the email is registered."""
    from app.auth.password_reset import (
        assert_password_reset_request_allowed,
        queue_password_reset_email,
    )

    user = get_user_by_email(db, email)
    if user is not None and user.is_active:
        assert_password_reset_request_allowed(db, user)
        queue_password_reset_email(db, user)
        write_audit_log(
            db,
            action="auth.password_reset_requested",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    db.commit()


def verify_password_reset_code(
    db: Session,
    *,
    email: str,
    code: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Check code without consuming it — user proceeds to set a new password."""
    from app.auth.password_reset import find_valid_password_reset_token

    user, _ = find_valid_password_reset_token(db, email=email, code=code)
    write_audit_log(
        db,
        action="auth.password_reset_code_verified",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()


def authenticate_user(
    db: Session,
    *,
    login: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, dict[str, str]]:
    from app.auth.login_identity import get_user_for_login

    user = get_user_for_login(db, login)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username, email, or password",
        )
    if not user.is_active:
        from app.users.account_status_service import effective_account_status
        from app.users.account_status_constants import ACCOUNT_STATUS_SUSPENDED

        # Suspended users may sign in to view status + submit an appeal.
        if effective_account_status(user) != ACCOUNT_STATUS_SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

    write_audit_log(
        db,
        action="auth.login",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    # Admin-team login audit is best-effort. Wrap in a SAVEPOINT so a failed
    # SELECT/INSERT (e.g. migration 20260720_0101 not applied → missing
    # admin_team_members / admin_audit_logs) cannot abort the outer Postgres
    # transaction and break refresh_token issue + commit.
    try:
        from app.admin_team.service import record_admin_login_if_applicable

        with db.begin_nested():
            record_admin_login_if_applicable(
                db,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
            )
    except Exception:
        pass
    tokens = issue_token_pair(
        db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return user, tokens


def issue_token_pair(
    db: Session,
    *,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, str]:
    roles = user_role_names(user)
    permissions = user_permission_codes(user)
    access_token = create_access_token(
        subject=user.id,
        roles=roles,
        permissions=permissions,
    )
    raw_refresh = generate_refresh_token()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(UTC)
        + timedelta(days=settings.refresh_token_expire_days),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(refresh)
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


def refresh_access_token(
    db: Session,
    *,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, str]:
    token_row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if token_row is None or token_row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    expires_at = token_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    user = get_user_by_id(db, token_row.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if not user.is_active:
        from app.users.account_status_service import effective_account_status
        from app.users.account_status_constants import ACCOUNT_STATUS_SUSPENDED

        if effective_account_status(user) != ACCOUNT_STATUS_SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

    # Rotate refresh token; new refresh token gets a full refresh_token_expire_days window.
    token_row.revoked_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="auth.refresh",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    tokens = issue_token_pair(
        db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return tokens


def logout_user(
    db: Session,
    *,
    refresh_token: str,
    actor_user_id: UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    token_row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if token_row is None:
        return

    if token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(UTC)
        write_audit_log(
            db,
            action="auth.logout",
            actor_user_id=actor_user_id or token_row.user_id,
            resource_type="refresh_token",
            resource_id=str(token_row.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()


def build_user_public(user: User, db: Session | None = None) -> dict:
    from sqlalchemy.orm import object_session

    from app.admin.impersonation_service import build_impersonation_public
    from app.auth.impersonation_context import get_impersonation_context

    session = db or object_session(user)
    data = serialize_user(user, db=session)

    ctx = get_impersonation_context()
    if ctx is None:
        data["impersonation"] = None
        return data

    impersonator = get_user_by_id(session, ctx.impersonator_id) if session else None
    expires_at = getattr(user, "_impersonation_expires_at", None)
    data["impersonation"] = build_impersonation_public(
        ctx=ctx,
        impersonator=impersonator,
        expires_at=expires_at,
        target=user,
    )
    return data

