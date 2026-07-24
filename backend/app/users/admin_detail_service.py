"""Admin user detail — safe aggregated account view (no secrets)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import RefreshToken
from app.core.audit import AuditLog
from app.fan_connect.models import FanConnectSettings
from app.finance.models import RefundRequest
from app.hosts.models import Host, HostTeamMember
from app.merch.models import MerchFulfillment
from app.passport.models import FanPassport
from app.payments.models import Order
from app.promos.ambassador_domain import AmbassadorParticipant, AmbassadorProfile
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.users.account_status_service import (
    effective_account_status,
    stored_restrictions,
)
from app.users.admin_actions_service import serialize_flag, serialize_note
from app.users.admin_response_safety import (
    assert_admin_user_payload_safe,
    mask_email,
    scrub_admin_user_payload,
)
from app.users.flag_constants import (
    FLAG_SEVERITY_CRITICAL,
    FLAG_SEVERITY_HIGH,
    FLAG_SEVERITY_LOW,
    FLAG_SEVERITY_MEDIUM,
    FLAG_STATUS_ACTIVE,
)
from app.users.models import User, UserAdminFlag, UserAdminNote
from app.users.service import get_user_by_id, user_has_permission, user_role_names

_SEVERITY_RANK = {
    FLAG_SEVERITY_LOW: 1,
    FLAG_SEVERITY_MEDIUM: 2,
    FLAG_SEVERITY_HIGH: 3,
    FLAG_SEVERITY_CRITICAL: 4,
}


def _mask_email(email: str) -> str:
    return mask_email(email)


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def _risk(
    *,
    is_active: bool,
    security_locked: bool,
    under_review: bool,
    ambassadors_blocked: bool,
    passport_hidden: bool,
    ambassador_status: str | None,
    active_flags: int,
    max_flag_severity: str | None,
) -> tuple[str, str]:
    if (
        security_locked
        or not is_active
        or max_flag_severity == "critical"
    ):
        return "high", "High"
    if (
        under_review
        or ambassadors_blocked
        or passport_hidden
        or active_flags > 0
        or max_flag_severity in {"high", "medium"}
        or ambassador_status in {"suspended", "blocked"}
    ):
        return "medium", "Medium"
    return "low", "Low"


def get_admin_user_detail(
    db: Session, user_id: uuid.UUID, *, viewer: User | None = None
) -> dict:
    """Compose a safe admin detail payload. Never returns secrets or private bodies."""
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == user.id)
    )
    fc = db.scalar(
        select(FanConnectSettings).where(FanConnectSettings.user_id == user.id)
    )
    amb_profile = db.scalar(
        select(AmbassadorProfile).where(AmbassadorProfile.user_id == user.id)
    )

    last_active = db.scalar(
        select(func.max(RefreshToken.created_at)).where(
            RefreshToken.user_id == user.id
        )
    )
    active_sessions = _count(
        db,
        select(func.count(RefreshToken.id)).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        ),
    )

    tickets_count = _count(
        db, select(func.count(Ticket.id)).where(Ticket.buyer_user_id == user.id)
    )
    orders_count = _count(
        db, select(func.count(Order.id)).where(Order.buyer_user_id == user.id)
    )
    merch_count = _count(
        db,
        select(func.count(MerchFulfillment.id)).where(
            MerchFulfillment.buyer_user_id == user.id
        ),
    )
    refunds_count = _count(
        db,
        select(func.count(RefundRequest.id)).where(
            RefundRequest.buyer_user_id == user.id
        ),
    )
    reviews_count = _count(
        db,
        select(func.count(VerifiedReview.id)).where(
            VerifiedReview.reviewer_user_id == user.id
        ),
    )
    hosts_owned = _count(
        db, select(func.count(Host.id)).where(Host.user_id == user.id)
    )
    teams_joined = _count(
        db,
        select(func.count(HostTeamMember.id)).where(
            HostTeamMember.user_id == user.id,
            HostTeamMember.status == "active",
            HostTeamMember.removed_at.is_(None),
        ),
    )
    campaigns_joined = _count(
        db,
        select(func.count(AmbassadorParticipant.id)).where(
            AmbassadorParticipant.user_id == user.id,
            AmbassadorParticipant.status.in_(("active", "paused")),
        ),
    )

    security_locked = user.security_locked_at is not None
    under_review = getattr(user, "under_review_at", None) is not None
    passport_hidden = bool(passport and passport.admin_hidden_at is not None)
    amb_status = amb_profile.status if amb_profile else None

    note_rows = list(
        db.scalars(
            select(UserAdminNote)
            .where(UserAdminNote.user_id == user.id)
            .order_by(UserAdminNote.created_at.desc())
            .limit(50)
        ).all()
    )
    flag_rows = list(
        db.scalars(
            select(UserAdminFlag)
            .where(UserAdminFlag.user_id == user.id)
            .order_by(UserAdminFlag.created_at.desc())
            .limit(50)
        ).all()
    )
    active_flag_rows = [f for f in flag_rows if f.status == FLAG_STATUS_ACTIVE]
    active_flags = len(active_flag_rows)
    max_flag_severity: str | None = None
    if active_flag_rows:
        max_flag_severity = max(
            active_flag_rows,
            key=lambda f: _SEVERITY_RANK.get(f.severity, 0),
        ).severity

    risk_level, risk_label = _risk(
        is_active=user.is_active,
        security_locked=security_locked,
        under_review=under_review,
        ambassadors_blocked=bool(user.ambassadors_blocked),
        passport_hidden=passport_hidden,
        ambassador_status=amb_status,
        active_flags=active_flags,
        max_flag_severity=max_flag_severity,
    )

    if fc is None:
        fan_connect_status = "not_configured"
        fan_connect_enabled = False
    elif fc.fan_connect_enabled:
        fan_connect_status = "enabled"
        fan_connect_enabled = True
    else:
        fan_connect_status = "disabled"
        fan_connect_enabled = False

    account_status = effective_account_status(user)

    flags: list[str] = []
    restrictions: list[str] = list(stored_restrictions(user))
    suspensions: list[str] = []
    if security_locked:
        flags.append("security_locked")
        restrictions.append(
            user.security_lock_reason or "Account under security lock"
        )
    if under_review:
        flags.append("under_review")
        restrictions.append(
            getattr(user, "under_review_reason", None) or "Account marked under review"
        )
    if not user.is_active:
        suspensions.append("account_suspended")
    if user.ambassadors_blocked:
        flags.append("ambassadors_program_blocked")
        if "cannot_promote_as_ambassador" not in restrictions:
            restrictions.append("cannot_promote_as_ambassador")
        if "cannot_join_ambassador_campaigns" not in restrictions:
            restrictions.append("cannot_join_ambassador_campaigns")
        restrictions.append("Blocked from Ambassadors programs")
    if passport_hidden:
        flags.append("passport_admin_hidden")
        restrictions.append(
            passport.admin_hidden_reason
            if passport and passport.admin_hidden_reason
            else "Fan Passport hidden by admin"
        )
    for f in flag_rows:
        if f.status == FLAG_STATUS_ACTIVE:
            flags.append(f"flag:{f.flag_type}")
    if amb_status == "suspended":
        suspensions.append("ambassador_profile_suspended")
    if amb_status == "blocked":
        suspensions.append("ambassador_profile_blocked")
    if fan_connect_status == "disabled" and fc is not None:
        if "cannot_use_fan_connect" not in restrictions:
            restrictions.append("cannot_use_fan_connect")
        restrictions.append("Fan Connect disabled")

    display_name = (
        (passport.display_name if passport and passport.display_name else None)
        or user.full_name
    )

    audit_rows = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.resource_type == "user",
                AuditLog.resource_id == str(user.id),
            )
            .order_by(AuditLog.created_at.desc())
            .limit(25)
        ).all()
    )

    payload = {
        "id": user.id,
        "email": user.email,
        "email_masked": _mask_email(user.email),
        "full_name": user.full_name,
        "display_name": display_name,
        "username": passport.username if passport else None,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "account_status": account_status,
        "verification_status": "verified" if user.is_verified else "unverified",
        "created_at": user.created_at,
        "deactivated_at": user.deactivated_at,
        "last_active_at": last_active,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "security_locked": security_locked,
        "security_lock_reason": user.security_lock_reason,
        "ambassadors_blocked": bool(user.ambassadors_blocked),
        "under_review": under_review,
        "under_review_reason": getattr(user, "under_review_reason", None),
        "under_review_at": getattr(user, "under_review_at", None),
        "account_restrictions": stored_restrictions(user),
        "roles": user_role_names(user),
        "profile": {
            "avatar_url": passport.avatar_url if passport else None,
            "tagline": passport.tagline if passport else None,
            "bio": passport.bio if passport else None,
            "passport_visibility": passport.visibility if passport else None,
            "passport_admin_hidden": passport_hidden,
            "fan_connect_enabled": fan_connect_enabled,
            "fan_connect_status": fan_connect_status,
            "ambassador_profile_status": amb_status,
            "ambassadors_program_blocked": bool(user.ambassadors_blocked),
            "campaigns_joined": campaigns_joined,
        },
        "account": {
            "email_verified": user.is_verified,
            "auth_provider": "password",
            "roles": user_role_names(user),
            "phone_masked": None,
            "phone_available": False,
            "two_factor_status": "not_implemented",
            "active_sessions": active_sessions,
            "last_active_at": last_active,
        },
        "activity": {
            "tickets_count": tickets_count,
            "orders_count": orders_count,
            "merch_count": merch_count,
            "refunds_count": refunds_count,
            "reviews_count": reviews_count,
            "host_workspaces_owned": hosts_owned,
            "host_teams_joined": teams_joined,
            "ambassador_campaigns_joined": campaigns_joined,
        },
        "moderation": {
            "flags": flags,
            "restrictions": restrictions,
            "suspensions": suspensions,
            "internal_notes": [serialize_note(n) for n in note_rows],
            "admin_flags": [serialize_flag(f) for f in flag_rows],
            "under_review": under_review,
            "under_review_reason": getattr(user, "under_review_reason", None),
            "under_review_at": getattr(user, "under_review_at", None),
        },
        "recent_audit": [
            {
                "id": row.id,
                "action": row.action,
                "actor_user_id": row.actor_user_id,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "details": scrub_admin_user_payload(row.details),
                "created_at": row.created_at,
            }
            for row in audit_rows
        ],
    }
    if viewer is not None:
        # Email is always the real address on admin detail (same as the
        # directory list). `email_masked` remains for secondary/banner use.
        # `view_private_contact` still gates phone and related private fields.
        if not user_has_permission(viewer, "admin.users.view_private_contact"):
            payload["account"] = {
                **payload["account"],
                "phone_masked": None,
                "phone_available": False,
            }
        if not user_has_permission(viewer, "admin.users.view_security"):
            payload["security_lock_reason"] = None
            payload["account"] = {
                **payload["account"],
                "active_sessions": 0,
            }
        if not user_has_permission(viewer, "admin.users.view_activity"):
            payload["activity"] = {
                "tickets_count": 0,
                "orders_count": 0,
                "merch_count": 0,
                "refunds_count": 0,
                "reviews_count": 0,
                "host_workspaces_owned": 0,
                "host_teams_joined": 0,
                "ambassador_campaigns_joined": 0,
            }
        if not user_has_permission(viewer, "admin.users.view_audit"):
            payload["recent_audit"] = []
    safe = scrub_admin_user_payload(payload)
    assert_admin_user_payload_safe(safe)
    return safe
