"""Platform-admin team overview and audit."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.hosts.models import Host, HostTeamAuditLog, HostTeamInvite, HostTeamMember
from app.teams.team_audit import action_label, sanitize_audit_metadata, user_public_label
from app.users.models import User
from app.users.service import get_user_by_id


def list_admin_teams(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    hosts = list(
        db.scalars(
            select(Host)
            .order_by(Host.created_at.desc())
            .offset(max(offset, 0))
            .limit(min(limit, 200))
        )
    )
    if not hosts:
        return []

    host_ids = [h.id for h in hosts]
    member_counts = dict(
        db.execute(
            select(HostTeamMember.host_id, func.count())
            .where(
                HostTeamMember.host_id.in_(host_ids),
                HostTeamMember.status != "removed",
                HostTeamMember.removed_at.is_(None),
            )
            .group_by(HostTeamMember.host_id)
        ).all()
    )
    invite_counts = dict(
        db.execute(
            select(HostTeamInvite.host_id, func.count())
            .where(
                HostTeamInvite.host_id.in_(host_ids),
                HostTeamInvite.status == "pending",
            )
            .group_by(HostTeamInvite.host_id)
        ).all()
    )

    owner_ids = [h.user_id for h in hosts]
    owners = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(owner_ids))).all()
    }

    out: list[dict[str, Any]] = []
    for host in hosts:
        owner = owners.get(host.user_id)
        out.append(
            {
                "host_id": host.id,
                "display_name": host.display_name,
                "slug": host.slug,
                "status": host.status,
                "owner_user_id": host.user_id,
                "owner_email": owner.email if owner else None,
                "member_count": int(member_counts.get(host.id, 0)),
                "pending_invite_count": int(invite_counts.get(host.id, 0)),
                "created_at": host.created_at,
            }
        )
    return out


def list_admin_team_audit(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    host_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    q = select(HostTeamAuditLog).order_by(HostTeamAuditLog.created_at.desc())
    if host_id is not None:
        q = q.where(HostTeamAuditLog.host_id == host_id)
    logs = list(db.scalars(q.offset(max(offset, 0)).limit(min(limit, 200))))
    if not logs:
        return []

    host_ids = {log.host_id for log in logs}
    hosts = {
        h.id: h
        for h in db.scalars(select(Host).where(Host.id.in_(host_ids))).all()
    }
    out: list[dict[str, Any]] = []
    for log in logs:
        actor = get_user_by_id(db, log.actor_user_id) if log.actor_user_id else None
        target = get_user_by_id(db, log.target_user_id) if log.target_user_id else None
        details = sanitize_audit_metadata(log.metadata_json)
        out.append(
            {
                "id": log.id,
                "host_id": log.host_id,
                "host_display_name": (
                    hosts[log.host_id].display_name if log.host_id in hosts else None
                ),
                "action": log.action,
                "action_label": action_label(log.action),
                "actor_user_id": log.actor_user_id,
                "actor_label": user_public_label(actor),
                "target_user_id": log.target_user_id,
                "target_label": user_public_label(target),
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": details,
                "created_at": log.created_at,
            }
        )
    return out
