"""Email + in-app/push notifications for host team lifecycle."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.email.service import enqueue_template
from app.hosts.models import Host, HostTeamInvite, HostTeamMember
from app.users.models import User
from app.users.service import get_user_by_email, get_user_by_id

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
    push_context: dict | None = None,
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
            push_context=push_context,
        )
    except Exception:  # noqa: BLE001 — never block team flows on notify failures
        logger.exception("team notify failed kind=%s user=%s", kind, user_id)


def enqueue_team_invite_email(
    db: Session,
    *,
    host: Host,
    invite: HostTeamInvite,
    raw_token: str,
) -> None:
    path = f"/team/invite/{raw_token}"
    method = (getattr(invite, "invite_method", None) or "email").strip().lower()
    username = (getattr(invite, "invited_username", None) or "").strip().lstrip("@")
    enqueue_template(
        db,
        template="team_invite",
        to=invite.email,
        recipient_user_id=invite.invited_user_id,
        dedupe_key=f"team_invite:{invite.id}:{invite.token_hash}",
        context={
            "host_display_name": host.display_name,
            "role": invite.role,
            "role_label": invite.role_label,
            "invite_method": method,
            "invited_username": username,
            "invite_path": path,
            "cta_path": path,
            "expires_at": (invite.expires_at.isoformat() if invite.expires_at else ""),
        },
        force=True,
    )
    # Username invites (and known-email users) get in-app + push when enabled.
    if invite.invited_user_id is not None:
        if method == "username" and username:
            body = (
                f"{host.display_name} invited your Pàdéyá account @{username} "
                "to join their team."
            )
        else:
            body = (
                f"You’ve been invited to join {host.display_name}’s Pàdéyá team."
            )
        _safe_notify_user(
            db,
            user_id=invite.invited_user_id,
            kind="team.invite",
            title="Pàdéyá team invite",
            body=body,
            link_path=path,
            dedupe_key=f"team_invite:{invite.id}:{invite.token_hash}",
            push_context={
                "host_display_name": host.display_name,
                "invite_method": method,
                "invited_username": username,
            },
        )


def notify_host_invite_accepted(
    db: Session,
    *,
    host: Host,
    invite: HostTeamInvite,
    member_user: User,
) -> None:
    member_name = member_user.full_name or member_user.email
    owner = get_user_by_id(db, host.user_id)
    if owner is not None and owner.email:
        enqueue_template(
            db,
            template="team_invite_accepted",
            to=owner.email,
            recipient_user_id=owner.id,
            dedupe_key=f"team_invite_accepted:{invite.id}",
            context={
                "host_display_name": host.display_name,
                "member_name": member_name,
                "member_email": member_user.email,
                "role": invite.role,
                "role_label": invite.role_label,
                "cta_path": "/host/team",
            },
            force=True,
        )
    _safe_notify_user(
        db,
        user_id=host.user_id,
        kind="team.invite_accepted",
        title="Team invite accepted",
        body=f"{member_name} joined {host.display_name} as {invite.role_label or invite.role}.",
        link_path="/host/team",
        dedupe_key=f"team_invite_accepted:{invite.id}",
        push_context={
            "host_display_name": host.display_name,
            "member_name": member_name,
        },
    )


def notify_invite_revoked(
    db: Session,
    *,
    host: Host,
    invite: HostTeamInvite,
) -> None:
    enqueue_template(
        db,
        template="team_invite_revoked",
        to=invite.email,
        recipient_user_id=invite.invited_user_id,
        dedupe_key=f"team_invite_revoked:{invite.id}",
        context={
            "host_display_name": host.display_name,
            "role": invite.role,
            "role_label": invite.role_label,
        },
        force=True,
    )
    user_id = invite.invited_user_id
    if user_id is None:
        existing = get_user_by_email(db, invite.email)
        user_id = existing.id if existing is not None else None
    if user_id is not None:
        _safe_notify_user(
            db,
            user_id=user_id,
            kind="team.invite_revoked",
            title="Team invite revoked",
            body=f"Your invite to {host.display_name} was revoked.",
            link_path="/dashboard",
            dedupe_key=f"team_invite_revoked:{invite.id}",
        )


def notify_member_removed(
    db: Session,
    *,
    host: Host,
    member: HostTeamMember,
) -> None:
    target = get_user_by_id(db, member.user_id)
    if target is None or not target.email:
        return
    enqueue_template(
        db,
        template="team_member_removed",
        to=target.email,
        recipient_user_id=target.id,
        dedupe_key=f"team_member_removed:{member.id}:{member.removed_at}",
        context={
            "host_display_name": host.display_name,
            "role": member.role,
            "role_label": member.role_label,
        },
        force=True,
    )
    _safe_notify_user(
        db,
        user_id=target.id,
        kind="team.member_removed",
        title="Removed from host team",
        body=f"You were removed from {host.display_name} on Pàdéyá.",
        link_path="/dashboard",
        dedupe_key=f"team_member_removed:{member.id}",
    )


def notify_member_suspended(
    db: Session,
    *,
    host: Host,
    member: HostTeamMember,
) -> None:
    target = get_user_by_id(db, member.user_id)
    if target is None or not target.email:
        return
    detail = (
        f"Your access on {host.display_name} was suspended. "
        "Desk and host tools are unavailable until the owner restores you."
    )
    enqueue_template(
        db,
        template="team_security_alert",
        to=target.email,
        recipient_user_id=target.id,
        dedupe_key=f"team_security_alert:suspend:{member.id}:{member.suspended_at}",
        context={
            "host_display_name": host.display_name,
            "detail": detail,
            "role": member.role,
            "role_label": member.role_label,
        },
        force=True,
    )
    _safe_notify_user(
        db,
        user_id=target.id,
        kind="team.security_alert",
        title="Team access suspended",
        body=detail,
        link_path="/dashboard",
        dedupe_key=f"team_security_alert:suspend:{member.id}",
    )


def notify_member_permissions_updated(
    db: Session,
    *,
    host: Host,
    member: HostTeamMember,
) -> None:
    target = get_user_by_id(db, member.user_id)
    if target is None or not target.email:
        return
    enqueue_template(
        db,
        template="team_permission_updated",
        to=target.email,
        recipient_user_id=target.id,
        dedupe_key=f"team_permission_updated:{member.id}:{member.updated_at}",
        context={
            "host_display_name": host.display_name,
            "role": member.role,
            "role_label": member.role_label,
            "cta_path": "/host",
        },
        force=True,
    )
    _safe_notify_user(
        db,
        user_id=target.id,
        kind="team.permission_updated",
        title="Team permissions updated",
        body=(
            f"Your role on {host.display_name} is now "
            f"{member.role_label or member.role}."
        ),
        link_path="/host",
        dedupe_key=f"team_permission_updated:{member.id}:{member.updated_at}",
    )
