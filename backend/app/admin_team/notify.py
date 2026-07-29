"""Email (+ optional in-app) notifications for admin team lifecycle."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.admin_team.models import AdminInvite, AdminRole, AdminTeamMember
from app.email.service import enqueue_template
from app.users.models import User

logger = logging.getLogger(__name__)


def _safe_notify_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    kind: str,
    title: str,
    body: str,
    link_path: str,
    dedupe_key: str,
) -> None:
    try:
        from app.notifications.service import notify_user

        notify_user(
            db,
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            link_path=link_path,
            dedupe_key=dedupe_key,
            send_push=True,
        )
    except Exception:  # noqa: BLE001 — never block team flows on notify failures
        logger.exception("admin team notify failed kind=%s user=%s", kind, user_id)


def enqueue_admin_team_invite_email(
    db: Session,
    *,
    invite: AdminInvite,
    role: AdminRole,
    raw_token: str,
) -> None:
    """Pending invite — email includes accept link with one-time token."""
    path = f"/admin/team/invites/{raw_token}"
    role_label = role.name or "admin team"
    enqueue_template(
        db,
        template="admin_team_invite",
        to=invite.email,
        dedupe_key=f"admin_team_invite:{invite.id}:{invite.token_hash}",
        context={
            "role": role.system_key or role.name,
            "role_label": role_label,
            "invite_path": path,
            "cta_path": path,
            "expires_at": invite.expires_at.isoformat() if invite.expires_at else "",
            "provisioned": False,
        },
        force=True,
    )


def enqueue_admin_team_provisioned_email(
    db: Session,
    *,
    user: User,
    member: AdminTeamMember,
    role: AdminRole,
) -> None:
    """Existing account was added immediately — notify them to open admin."""
    if not user.email:
        return
    path = "/admin"
    role_label = role.name or "admin team"
    enqueue_template(
        db,
        template="admin_team_invite",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"admin_team_provisioned:{member.id}:{member.admin_role_id}",
        context={
            "role": role.system_key or role.name,
            "role_label": role_label,
            "invite_path": path,
            "cta_path": path,
            "provisioned": True,
        },
        force=True,
    )
    _safe_notify_user(
        db,
        user_id=user.id,
        kind="admin_team.invite",
        title="Pàdéyá admin team",
        body=f"You’ve been added to the Pàdéyá admin team as {role_label}.",
        link_path=path,
        dedupe_key=f"admin_team_provisioned:{member.id}:{member.admin_role_id}",
    )
