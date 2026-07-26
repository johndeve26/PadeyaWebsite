"""Secure, audited admin user impersonation (not a real login as the user)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.admin.impersonation_audit import (
    ADMIN_IMPERSONATION_ENDED,
    ADMIN_IMPERSONATION_STARTED,
    record_impersonation_audit,
)
from app.admin.impersonation_scopes import (
    pack_label,
    resolve_impersonation_scopes,
)
from app.admin.impersonation_store import (
    create_impersonation_session,
    end_impersonation_session,
    expire_stale_active_sessions,
    list_active_sessions_for_admin,
    list_impersonation_sessions_for_target,
    revoke_impersonation_session,
)
from app.admin.impersonation_models import (
    IMPERSONATION_STATUS_ACTIVE,
    AdminImpersonationSession,
)
from app.auth.impersonation_context import ImpersonationContext, get_impersonation_context
from app.core.security import create_impersonation_access_token
from app.users.account_status_constants import (
    ACCOUNT_STATUS_BANNED,
    ACCOUNT_STATUS_DELETED,
    ACCOUNT_STATUS_SUSPENDED,
)
from app.users.account_status_service import effective_account_status
from app.users.models import User
from app.users.service import (
    get_user_by_id,
    user_has_permission,
    user_permission_codes,
    user_role_names,
)

ALLOWED_DURATIONS = frozenset({15, 30, 60})
DEFAULT_DURATION_MINUTES = 30
MAX_DURATION_MINUTES = 60

# Actors must be platform operators. Hosts / host staff / buyers never impersonate,
# even if admin.users.impersonate were mistakenly granted.
_PLATFORM_OPERATOR_ROLES = frozenset(
    {
        "super_admin",
        "admin",
        "admin_staff",
        "support_agent",
        "finance_admin",
        "moderation",
        "operations",
        "marketing",
    }
)


def _exact_roles(user: User) -> set[str]:
    """Role names without super_admin wildcard matching."""
    return set(user_role_names(user))


def can_start_impersonation(admin: User) -> bool:
    """True when the caller may start impersonation.

    Requires ``admin.users.impersonate`` (satisfied by ``admin.full_access`` /
    ``super_admin``). Support and finance need an explicit grant. Buyers, host
    owners, and host team members never qualify — even with a mistaken grant.
    """
    if not user_has_permission(admin, "admin.users.impersonate"):
        return False
    if "admin.full_access" in set(user_permission_codes(admin)):
        return True
    if _exact_roles(admin) & _PLATFORM_OPERATOR_ROLES:
        return True
    # Custom admin team members with an explicit impersonate grant.
    try:
        from sqlalchemy.orm import object_session

        from app.admin_team.service import get_active_team_member

        session = object_session(admin)
        if session is not None and get_active_team_member(session, admin.id):
            return True
    except Exception:
        pass
    return False


def _require_can_impersonate(admin: User) -> None:
    if not can_start_impersonation(admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permission",
        )


def _is_super_admin(user: User) -> bool:
    return "super_admin" in _exact_roles(user) or "admin.full_access" in set(
        user_permission_codes(user)
    )


def _assert_target_allowed(
    *,
    admin: User,
    target: User,
    reason_clean: str,
) -> None:
    roles = _exact_roles(target)
    codes = set(user_permission_codes(target))
    account_status = effective_account_status(target)

    if account_status == ACCOUNT_STATUS_DELETED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or deleted",
        )

    if account_status == ACCOUNT_STATUS_BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate a banned user",
        )

    if "super_admin" in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate a super administrator",
        )

    if "finance_admin" in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate a finance administrator",
        )

    # Platform admin operators (support agents, or anyone with full admin access).
    if "support_agent" in roles or "admin.full_access" in codes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate a platform administrator",
        )

    if getattr(target, "security_locked_at", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate a user under security lock",
        )

    suspended = (
        account_status == ACCOUNT_STATUS_SUSPENDED
        or (not target.is_active)
        or target.deactivated_at is not None
    )
    if suspended:
        if not _is_super_admin(admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot impersonate a suspended user",
            )
        if len(reason_clean) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A reason is required to impersonate a suspended user",
            )


def _normalize_duration_minutes(duration_minutes: int) -> int:
    if duration_minutes > MAX_DURATION_MINUTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duration cannot exceed {MAX_DURATION_MINUTES} minutes",
        )
    if duration_minutes not in ALLOWED_DURATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duration must be 15, 30, or 60 minutes",
        )
    return duration_minutes


def _assert_no_active_admin_session(db: Session, *, admin: User) -> None:
    """One active impersonation per admin — end the current session before starting another."""
    expire_stale_active_sessions(db, actor_admin_id=admin.id)
    active = list_active_sessions_for_admin(db, actor_admin_id=admin.id)
    if active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End your current impersonation session before starting another",
        )


def revoke_impersonation_for_safety(
    db: Session,
    *,
    ctx: ImpersonationContext,
    cause: str,
    detail: str,
) -> None:
    """Force-end an active session (disabled accounts, safety checks)."""
    revoke_impersonation_session(
        db,
        session_id=ctx.impersonation_id,
        ended_by_admin_id=ctx.actor_admin_id,
    )
    record_impersonation_audit(
        db,
        action=ADMIN_IMPERSONATION_ENDED,
        impersonation_id=ctx.impersonation_id,
        actor_admin_id=ctx.actor_admin_id,
        target_user_id=ctx.actual_user_id,
        reason=ctx.reason,
        support_ticket_id=ctx.support_ticket_id,
        method=None,
        path=None,
        status_code=401,
        action_attempted=cause,
        metadata={"safety_end": True, "cause": cause, "detail": detail},
        ip_address=None,
        user_agent=None,
    )
    db.commit()


def start_impersonation(
    db: Session,
    *,
    admin: User,
    target_user_id: UUID,
    reason: str,
    support_ticket_id: str | None = None,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Issue a short-lived impersonation access token for the target user.

    Does not touch the target's password, refresh tokens, or live sessions.
    """
    if get_impersonation_context() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already impersonating; end the current session first",
        )

    _require_can_impersonate(admin)
    if not admin.is_active or admin.deactivated_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is disabled",
        )

    reason_clean = reason.strip()
    if len(reason_clean) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A reason of at least 3 characters is required",
        )
    if len(reason_clean) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason is too long",
        )

    ticket_clean: str | None = None
    if support_ticket_id is not None:
        ticket_clean = support_ticket_id.strip() or None
        if ticket_clean and len(ticket_clean) > 128:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Support ticket ID is too long",
            )

    duration_minutes = _normalize_duration_minutes(duration_minutes)
    _assert_no_active_admin_session(db, admin=admin)

    if target_user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate yourself",
        )

    target = get_user_by_id(db, target_user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or deleted",
        )

    _assert_target_allowed(admin=admin, target=target, reason_clean=reason_clean)

    scopes = resolve_impersonation_scopes(admin)
    if not scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation is not allowed for this account",
        )
    pack = pack_label(scopes)

    expires_at = datetime.now(UTC) + timedelta(minutes=duration_minutes)
    started_at = datetime.now(UTC)
    impersonation_id = uuid4()
    suspended = (
        effective_account_status(target) == ACCOUNT_STATUS_SUSPENDED
        or (not target.is_active)
        or target.deactivated_at is not None
    )

    # Target roles/permissions only — admin privileges must not appear in the token.
    target_roles = user_role_names(target)
    target_permissions = user_permission_codes(target)

    access_token = create_impersonation_access_token(
        actual_user_id=target.id,
        actor_admin_id=admin.id,
        impersonation_id=impersonation_id,
        roles=target_roles,
        permissions=target_permissions,
        started_at=started_at,
        expires_at=expires_at,
        reason=reason_clean,
        support_ticket_id=ticket_clean,
        scopes=scopes,
    )

    create_impersonation_session(
        db,
        session_id=impersonation_id,
        actor_admin_id=admin.id,
        target_user_id=target.id,
        reason=reason_clean,
        support_ticket_id=ticket_clean,
        started_at=started_at,
        expires_at=expires_at,
        scopes=scopes,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    email = (target.email or "").strip().lower()
    demo_seed_target = email.endswith("@demo.padeye.test")
    record_impersonation_audit(
        db,
        action=ADMIN_IMPERSONATION_STARTED,
        impersonation_id=impersonation_id,
        actor_admin_id=admin.id,
        target_user_id=target.id,
        reason=reason_clean,
        support_ticket_id=ticket_clean,
        method="POST",
        path=f"/api/v1/admin/users/{target.id}/impersonation/start",
        status_code=200,
        action_attempted="start_impersonation",
        metadata={
            "duration_minutes": duration_minutes,
            "target_suspended": suspended,
            "expires_at": expires_at.isoformat(),
            "started_at": started_at.isoformat(),
            # Informational only — auditing is never skipped for demo seeds.
            "demo_seed_target": demo_seed_target,
            "scopes": scopes,
            "pack": pack,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()

    return {
        "impersonation_id": impersonation_id,
        "target_user_id": target.id,
        "expires_at": expires_at,
        "redirect_to": "/dashboard",
        "access_token": access_token,
        "token_type": "bearer",
        "scopes": scopes,
        "pack": pack,
        # Extra session metadata for clients that need it immediately.
        "impersonation": {
            "active": True,
            "is_impersonating": True,
            "impersonation_id": impersonation_id,
            "actual_user_id": target.id,
            "actor_admin_id": admin.id,
            "impersonator_id": admin.id,
            "impersonator_email": admin.email,
            "impersonator_full_name": admin.full_name,
            "target_user_id": target.id,
            "target_email": target.email,
            "target_full_name": target.full_name,
            "reason": reason_clean,
            "support_ticket_id": ticket_clean,
            "duration_minutes": duration_minutes,
            "started_at": started_at,
            "expires_at": expires_at,
            "scopes": scopes,
            "pack": pack,
        },
    }


def end_impersonation(
    db: Session,
    *,
    ctx: ImpersonationContext,
    target: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """End an impersonation session (audit only; admin restores their own tokens client-side)."""
    row = end_impersonation_session(
        db,
        session_id=ctx.impersonation_id,
        ended_by_admin_id=ctx.actor_admin_id,
    )
    ended_at = row.ended_at if row is not None else datetime.now(UTC)
    expires_at = row.expires_at if row is not None else ctx.expires_at
    started_at = row.started_at if row is not None else ctx.started_at
    ticket = (
        row.support_ticket_id
        if row is not None
        else ctx.support_ticket_id
    )
    record_impersonation_audit(
        db,
        action=ADMIN_IMPERSONATION_ENDED,
        impersonation_id=ctx.impersonation_id,
        actor_admin_id=ctx.actor_admin_id,
        target_user_id=target.id,
        reason=ctx.reason,
        support_ticket_id=ticket,
        method="POST",
        path="/api/v1/admin/impersonation/end",
        status_code=200,
        action_attempted="end_impersonation",
        metadata={
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": ended_at.isoformat() if ended_at else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return {
        "ended": True,
        "return_to": f"/admin/users/{target.id}",
    }


# Backwards-compatible alias used by older call sites / tests.
stop_impersonation = end_impersonation


def end_impersonation_on_logout(
    db: Session,
    *,
    ctx: ImpersonationContext,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """End the active impersonation session when the caller logs out."""
    end_impersonation_session(
        db,
        session_id=ctx.impersonation_id,
        ended_by_admin_id=ctx.actor_admin_id,
    )
    record_impersonation_audit(
        db,
        action=ADMIN_IMPERSONATION_ENDED,
        impersonation_id=ctx.impersonation_id,
        actor_admin_id=ctx.actor_admin_id,
        target_user_id=ctx.actual_user_id,
        reason=ctx.reason,
        support_ticket_id=ctx.support_ticket_id,
        method="POST",
        path="/api/v1/auth/logout",
        status_code=200,
        action_attempted="end_impersonation_on_logout",
        metadata={"cause": "logout"},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()


def _effective_session_status(row: AdminImpersonationSession) -> str:
    if row.status != IMPERSONATION_STATUS_ACTIVE:
        return row.status
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        return "expired"
    return row.status


def list_impersonation_history(
    db: Session,
    *,
    target_user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return impersonation sessions for a target user (newest first)."""
    rows = list_impersonation_sessions_for_target(
        db,
        target_user_id=target_user_id,
        limit=limit,
        offset=offset,
    )
    out: list[dict] = []
    for row in rows:
        actor = get_user_by_id(db, row.actor_admin_id)
        out.append(
            {
                "id": row.id,
                "actor_admin_id": row.actor_admin_id,
                "started_by": (
                    (actor.full_name or actor.email) if actor else str(row.actor_admin_id)
                ),
                "started_by_email": actor.email if actor else None,
                "target_user_id": row.target_user_id,
                "reason": row.reason,
                "support_ticket_id": row.support_ticket_id,
                "started_at": row.started_at,
                "ended_at": row.ended_at,
                "expires_at": row.expires_at,
                "status": _effective_session_status(row),
                "scopes": list(getattr(row, "scopes", None) or []),
                "pack": pack_label(getattr(row, "scopes", None)),
            }
        )
    return out


def build_impersonation_public(
    *,
    ctx: ImpersonationContext,
    impersonator: User | None,
    expires_at: datetime | None,
    target: User | None = None,
) -> dict:
    scopes = list(ctx.scopes) if ctx.scopes else ["view"]
    return {
        "active": True,
        "is_impersonating": True,
        "impersonation_id": ctx.impersonation_id,
        "actual_user_id": ctx.actual_user_id,
        "actor_admin_id": ctx.actor_admin_id,
        "impersonator_id": ctx.actor_admin_id,
        "impersonator_email": impersonator.email if impersonator else None,
        "impersonator_full_name": impersonator.full_name if impersonator else None,
        "target_user_id": ctx.actual_user_id,
        "target_email": target.email if target else None,
        "target_full_name": target.full_name if target else None,
        "reason": ctx.reason,
        "support_ticket_id": ctx.support_ticket_id,
        "started_at": ctx.started_at,
        "expires_at": expires_at or ctx.expires_at,
        "scopes": scopes,
        "pack": pack_label(scopes),
    }
