"""Structured audit trail for Ambassador reward status changes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog, write_audit_log
from app.promos.models import Ambassador, AmbassadorSale
from app.teams.permissions import is_host_owner
from app.users.models import User
from app.users.service import user_has_permission, user_has_role

REWARD_AUDIT_ACTIONS = frozenset(
    {
        "ambassador_reward_approved",
        "ambassador_reward_rejected",
        "ambassador_reward_marked_paid",
        "ambassador_reward_reversed",
        "ambassador_reward_status_changed_by_admin",
    }
)

_STATUS_ACTIONS = {
    "approved": "ambassador_reward_approved",
    "rejected": "ambassador_reward_rejected",
    "paid": "ambassador_reward_marked_paid",
    "reversed": "ambassador_reward_reversed",
}


def is_platform_admin(user: User) -> bool:
    return user_has_role(user, "super_admin") or user_has_permission(
        user, "admin.full_access"
    )


def resolve_actor_type(
    db: Session, *, actor: User, host_profile_id: UUID | None
) -> str:
    if is_platform_admin(actor):
        return "platform_admin"
    if host_profile_id is not None and is_host_owner(
        db, actor.id, host_profile_id
    ):
        return "host_owner"
    return "team_member"


def action_for_reward_change(*, status: str, actor_type: str) -> str:
    if actor_type == "platform_admin":
        return "ambassador_reward_status_changed_by_admin"
    action = _STATUS_ACTIONS.get(status)
    if action is None:
        return "ambassador_reward_status_changed_by_admin"
    return action


def write_reward_audit(
    db: Session,
    *,
    actor: User,
    actor_type: str,
    host_profile_id: UUID | None,
    campaign_id: UUID | None,
    conversion_id: UUID,
    old_status: str,
    new_status: str,
    reason: str | None = None,
    payout_reference: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    action = action_for_reward_change(status=new_status, actor_type=actor_type)
    return write_audit_log(
        db,
        action=action,
        actor_user_id=actor.id,
        resource_type="ambassador_sale",
        resource_id=str(conversion_id),
        ip_address=(ip_address or "")[:64] or None,
        user_agent=(user_agent or "")[:512] or None,
        details={
            "actor_type": actor_type,
            "host_profile_id": str(host_profile_id) if host_profile_id else None,
            "campaign_id": str(campaign_id) if campaign_id else None,
            "conversion_id": str(conversion_id),
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason or None,
            "payout_reference": payout_reference or None,
        },
    )


def serialize_reward_audit(row: AuditLog) -> dict[str, Any]:
    details = row.details or {}
    return {
        "id": row.id,
        "action": row.action,
        "actor_user_id": row.actor_user_id,
        "actor_type": details.get("actor_type"),
        "host_profile_id": details.get("host_profile_id"),
        "campaign_id": details.get("campaign_id"),
        "conversion_id": details.get("conversion_id") or row.resource_id,
        "old_status": details.get("old_status"),
        "new_status": details.get("new_status"),
        "reason": details.get("reason"),
        "payout_reference": details.get("payout_reference"),
        "timestamp": row.created_at,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "details": details,
    }


def list_reward_audits_for_conversion(
    db: Session,
    *,
    conversion_id: UUID,
) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.resource_type == "ambassador_sale",
                AuditLog.resource_id == str(conversion_id),
                AuditLog.action.in_(tuple(REWARD_AUDIT_ACTIONS)),
            )
            .order_by(AuditLog.created_at.desc())
        ).all()
    )
    # Include legacy reward audits written before structured action names.
    if not rows:
        legacy = list(
            db.scalars(
                select(AuditLog)
                .where(
                    AuditLog.resource_type == "ambassador_sale",
                    AuditLog.resource_id == str(conversion_id),
                )
                .order_by(AuditLog.created_at.desc())
            ).all()
        )
        return [serialize_reward_audit(r) for r in legacy]
    return [serialize_reward_audit(r) for r in rows]


def list_host_reward_audits(
    db: Session,
    *,
    host_id: UUID,
    campaign_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sale_q = (
        select(AmbassadorSale.id)
        .join(Ambassador, Ambassador.id == AmbassadorSale.ambassador_id)
        .where(Ambassador.host_id == host_id)
    )
    if campaign_id is not None:
        sale_q = sale_q.where(Ambassador.campaign_id == campaign_id)
    sale_ids = [str(i) for i in db.scalars(sale_q).all()]
    if not sale_ids:
        return []
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.resource_type == "ambassador_sale",
                AuditLog.resource_id.in_(sale_ids),
                AuditLog.action.in_(tuple(REWARD_AUDIT_ACTIONS)),
            )
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return [serialize_reward_audit(r) for r in rows]


def list_admin_reward_audits(
    db: Session,
    *,
    host_id: UUID | None = None,
    campaign_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if host_id is not None or campaign_id is not None:
        sale_q = select(AmbassadorSale.id).join(
            Ambassador, Ambassador.id == AmbassadorSale.ambassador_id
        )
        if host_id is not None:
            sale_q = sale_q.where(Ambassador.host_id == host_id)
        if campaign_id is not None:
            sale_q = sale_q.where(Ambassador.campaign_id == campaign_id)
        sale_ids = [str(i) for i in db.scalars(sale_q).all()]
        if not sale_ids:
            return []
        q = select(AuditLog).where(
            AuditLog.resource_type == "ambassador_sale",
            AuditLog.resource_id.in_(sale_ids),
            AuditLog.action.in_(tuple(REWARD_AUDIT_ACTIONS)),
        )
    else:
        q = select(AuditLog).where(
            AuditLog.action.in_(tuple(REWARD_AUDIT_ACTIONS)),
        )
    rows = list(
        db.scalars(
            q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return [serialize_reward_audit(r) for r in rows]
