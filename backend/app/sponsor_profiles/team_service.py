"""Sponsor org team invites, members, and audit."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.email.service import enqueue_template
from app.sponsor_profiles.constants import (
    DEFAULT_ROLE_PERMISSIONS,
    SPONSOR_TEAM_INVITE_ROLES,
)
from app.sponsor_profiles.service import get_sponsor_by_id, require_sponsor_access
from app.sponsor_profiles.team_schemas import SponsorTeamInviteCreate, SponsorTeamMemberUpdate
from app.sponsorships.models import (
    Sponsor,
    SponsorTeamAuditLog,
    SponsorTeamInvite,
    SponsorTeamMember,
)
from app.users.models import User
from app.users.service import get_user_by_email, get_user_by_id

INVITE_TTL_DAYS = 7


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_invite_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, _hash_token(raw)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _write_audit(
    db: Session,
    *,
    sponsor_id: uuid.UUID,
    action: str,
    actor_user_id: uuid.UUID | None,
    target_user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        SponsorTeamAuditLog(
            sponsor_id=sponsor_id,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata,
        )
    )


def _is_sponsor_owner(sponsor: Sponsor, user_id: uuid.UUID) -> bool:
    return sponsor.owner_user_id == user_id


def require_sponsor_team_manage(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
) -> tuple[Sponsor, bool]:
    """Owner or admin with sponsors.manage_team may invite/remove."""
    sponsor, perms = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.manage_team"
    )
    is_owner = _is_sponsor_owner(sponsor, user.id)
    membership = db.scalar(
        select(SponsorTeamMember).where(
            SponsorTeamMember.sponsor_id == sponsor.id,
            SponsorTeamMember.user_id == user.id,
            SponsorTeamMember.status == "active",
            SponsorTeamMember.removed_at.is_(None),
        )
    )
    is_admin = is_owner or (membership is not None and membership.role == "admin")
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sponsor owner or admin can manage team",
        )
    if not is_owner and not perms.get("sponsors.manage_team"):
        raise HTTPException(status_code=403, detail="Permission denied")
    return sponsor, is_owner


def _serialize_owner(db: Session, sponsor: Sponsor) -> dict[str, Any]:
    owner = get_user_by_id(db, sponsor.owner_user_id) if sponsor.owner_user_id else None
    email = owner.email if owner else None
    name = owner.full_name if owner else sponsor.display_name
    return {
        "id": None,
        "sponsor_id": sponsor.id,
        "user_id": sponsor.owner_user_id,
        "email": email,
        "display_name": name or sponsor.display_name,
        "role": "owner",
        "status": "active",
        "is_owner": True,
        "permissions": DEFAULT_ROLE_PERMISSIONS["owner"],
        "invited_at": None,
        "joined_at": sponsor.created_at,
        "created_at": sponsor.created_at,
    }


def _serialize_member(db: Session, row: SponsorTeamMember) -> dict[str, Any]:
    user = get_user_by_id(db, row.user_id)
    perms = row.permissions_json or DEFAULT_ROLE_PERMISSIONS.get(row.role, {})
    return {
        "id": row.id,
        "sponsor_id": row.sponsor_id,
        "user_id": row.user_id,
        "email": user.email if user else None,
        "display_name": user.full_name if user else None,
        "role": row.role,
        "status": row.status,
        "is_owner": False,
        "permissions": perms,
        "invited_at": None,
        "joined_at": row.created_at,
        "created_at": row.created_at,
    }


def _serialize_invite(row: SponsorTeamInvite) -> dict[str, Any]:
    return {
        "id": row.id,
        "sponsor_id": row.sponsor_id,
        "email": row.email,
        "role": row.role,
        "status": row.status,
        "invite_expires_at": row.expires_at,
        "invited_at": row.created_at,
        "display_name": row.email,
    }


def list_sponsor_team(db: Session, *, user: User, sponsor_id: uuid.UUID) -> dict[str, Any]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    members: list[dict[str, Any]] = [_serialize_owner(db, sponsor)]
    rows = list(
        db.scalars(
            select(SponsorTeamMember).where(
                SponsorTeamMember.sponsor_id == sponsor.id,
                SponsorTeamMember.status == "active",
                SponsorTeamMember.removed_at.is_(None),
            )
        )
    )
    members.extend(_serialize_member(db, r) for r in rows)

    invites = list(
        db.scalars(
            select(SponsorTeamInvite).where(
                SponsorTeamInvite.sponsor_id == sponsor.id,
                SponsorTeamInvite.status == "pending",
            )
        )
    )
    now = datetime.now(UTC)
    for inv in invites:
        exp = _as_utc(inv.expires_at)
        if exp is not None and exp < now:
            inv.status = "expired"
    db.flush()
    pending = [i for i in invites if i.status == "pending"]
    return {
        "members": members,
        "invites": [_serialize_invite(i) for i in pending],
    }


def _enqueue_invite_email(
    db: Session, *, sponsor: Sponsor, invite: SponsorTeamInvite, raw_token: str
) -> None:
    enqueue_template(
        db,
        template="team_invite",
        to=invite.email,
        dedupe_key=f"sponsor_team_invite:{invite.id}:{raw_token[:8]}",
        context={
            "workspace_name": sponsor.display_name or sponsor.company_name,
            "role_label": invite.role.replace("_", " ").title(),
            "accept_url_path": f"/sponsor/team/invite/{raw_token}",
        },
    )


def create_team_invite(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    payload: SponsorTeamInviteCreate,
) -> tuple[dict[str, Any], str]:
    sponsor, _ = require_sponsor_team_manage(db, user=user, sponsor_id=sponsor_id)
    email = str(payload.email).strip().lower()
    role = payload.role
    if role not in SPONSOR_TEAM_INVITE_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    if email == (user.email or "").strip().lower():
        raise HTTPException(status_code=400, detail="Cannot invite yourself")
    owner = get_user_by_id(db, sponsor.owner_user_id) if sponsor.owner_user_id else None
    if owner and email == (owner.email or "").strip().lower():
        raise HTTPException(status_code=400, detail="Cannot invite the sponsor owner")

    existing_user = get_user_by_email(db, email)
    if existing_user:
        active = db.scalar(
            select(SponsorTeamMember).where(
                SponsorTeamMember.sponsor_id == sponsor.id,
                SponsorTeamMember.user_id == existing_user.id,
                SponsorTeamMember.status == "active",
                SponsorTeamMember.removed_at.is_(None),
            )
        )
        if active:
            raise HTTPException(status_code=409, detail="User already on team")

    existing_invite = db.scalar(
        select(SponsorTeamInvite).where(
            SponsorTeamInvite.sponsor_id == sponsor.id,
            func.lower(SponsorTeamInvite.email) == email,
            SponsorTeamInvite.status.in_(("pending", "expired", "revoked")),
        )
    )
    raw_token, token_hash = _new_invite_token()
    now = datetime.now(UTC)
    expires = now + timedelta(days=INVITE_TTL_DAYS)
    perms = DEFAULT_ROLE_PERMISSIONS.get(role, {})

    if existing_invite:
        row = existing_invite
        row.status = "pending"
        row.role = role
        row.permissions_json = perms
        row.token_hash = token_hash
        row.expires_at = expires
        row.revoked_at = None
        row.invited_by_user_id = user.id
        row.invited_user_id = existing_user.id if existing_user else None
        action = "sponsors.team_resend"
    else:
        row = SponsorTeamInvite(
            sponsor_id=sponsor.id,
            email=email,
            role=role,
            permissions_json=perms,
            token_hash=token_hash,
            status="pending",
            invited_by_user_id=user.id,
            invited_user_id=existing_user.id if existing_user else None,
            expires_at=expires,
        )
        db.add(row)
        action = "sponsors.team_invite"

    db.flush()
    _enqueue_invite_email(db, sponsor=sponsor, invite=row, raw_token=raw_token)
    _write_audit(
        db,
        sponsor_id=sponsor.id,
        action=action,
        actor_user_id=user.id,
        target_user_id=existing_user.id if existing_user else None,
        entity_type="sponsor_team_invite",
        entity_id=str(row.id),
        metadata={"email": email, "role": role},
    )
    db.commit()
    db.refresh(row)
    accept_path = f"/sponsor/team/invite/{raw_token}"
    return _serialize_invite(row), accept_path


def resend_team_invite(
    db: Session, *, user: User, sponsor_id: uuid.UUID, invite_id: uuid.UUID
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_team_manage(db, user=user, sponsor_id=sponsor_id)
    row = db.get(SponsorTeamInvite, invite_id)
    if row is None or row.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Invite not found")
    if row.status not in {"pending", "expired", "revoked"}:
        raise HTTPException(status_code=400, detail="Only pending invites can be resent")
    raw_token, token_hash = _new_invite_token()
    row.status = "pending"
    row.token_hash = token_hash
    row.expires_at = datetime.now(UTC) + timedelta(days=INVITE_TTL_DAYS)
    row.revoked_at = None
    row.invited_by_user_id = user.id
    db.flush()
    _enqueue_invite_email(db, sponsor=sponsor, invite=row, raw_token=raw_token)
    _write_audit(
        db,
        sponsor_id=sponsor.id,
        action="sponsors.team_resend",
        actor_user_id=user.id,
        entity_type="sponsor_team_invite",
        entity_id=str(row.id),
        metadata={"email": row.email},
    )
    db.commit()
    db.refresh(row)
    return _serialize_invite(row)


def cancel_team_invite(
    db: Session, *, user: User, sponsor_id: uuid.UUID, invite_id: uuid.UUID
) -> None:
    sponsor, _ = require_sponsor_team_manage(db, user=user, sponsor_id=sponsor_id)
    row = db.get(SponsorTeamInvite, invite_id)
    if row is None or row.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Invite not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending invites can be cancelled")
    row.status = "revoked"
    row.revoked_at = datetime.now(UTC)
    _write_audit(
        db,
        sponsor_id=sponsor.id,
        action="sponsors.team_invite_cancel",
        actor_user_id=user.id,
        entity_type="sponsor_team_invite",
        entity_id=str(row.id),
    )
    db.commit()


def update_team_member(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: SponsorTeamMemberUpdate,
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_team_manage(db, user=user, sponsor_id=sponsor_id)
    row = db.get(SponsorTeamMember, member_id)
    if row is None or row.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Member not found")
    if row.user_id == sponsor.owner_user_id:
        raise HTTPException(status_code=400, detail="Cannot change owner role via team member")
    if payload.role not in SPONSOR_TEAM_INVITE_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    old_role = row.role
    row.role = payload.role
    row.permissions_json = DEFAULT_ROLE_PERMISSIONS.get(payload.role, {})
    _write_audit(
        db,
        sponsor_id=sponsor.id,
        action="sponsors.team_role_change",
        actor_user_id=user.id,
        target_user_id=row.user_id,
        entity_type="sponsor_team_member",
        entity_id=str(row.id),
        metadata={"from": old_role, "to": payload.role},
    )
    db.commit()
    db.refresh(row)
    return _serialize_member(db, row)


def remove_team_member(
    db: Session, *, user: User, sponsor_id: uuid.UUID, member_id: uuid.UUID
) -> None:
    sponsor, _ = require_sponsor_team_manage(db, user=user, sponsor_id=sponsor_id)
    row = db.get(SponsorTeamMember, member_id)
    if row is None or row.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Member not found")
    if row.user_id == sponsor.owner_user_id:
        raise HTTPException(
            status_code=400,
            detail="The sponsor owner cannot be removed from the team",
        )
    row.status = "removed"
    row.removed_at = datetime.now(UTC)
    _write_audit(
        db,
        sponsor_id=sponsor.id,
        action="sponsors.team_remove",
        actor_user_id=user.id,
        target_user_id=row.user_id,
        entity_type="sponsor_team_member",
        entity_id=str(row.id),
    )
    db.commit()


def preview_team_invite(db: Session, *, token: str) -> dict[str, Any]:
    token_hash = _hash_token(token)
    row = db.scalar(
        select(SponsorTeamInvite).where(SponsorTeamInvite.token_hash == token_hash)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    sponsor = get_sponsor_by_id(db, row.sponsor_id)
    if sponsor is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Invite is no longer valid")
    exp = _as_utc(row.expires_at)
    if exp is not None and exp < datetime.now(UTC):
        row.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Invite expired")
    return {
        "sponsor_display_name": sponsor.display_name or sponsor.company_name,
        "role": row.role,
        "status": row.status,
        "expires_at": row.expires_at,
    }


def accept_team_invite(db: Session, *, user: User, token: str) -> dict[str, Any]:
    token_hash = _hash_token(token)
    row = db.scalar(
        select(SponsorTeamInvite).where(SponsorTeamInvite.token_hash == token_hash)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Invite is no longer valid")
    exp = _as_utc(row.expires_at)
    if exp is not None and exp < datetime.now(UTC):
        row.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Invite expired")

    email = (user.email or "").strip().lower()
    if email != row.email.strip().lower():
        raise HTTPException(
            status_code=403,
            detail="Sign in with the email address that received this invite",
        )

    sponsor = get_sponsor_by_id(db, row.sponsor_id)
    if sponsor is None:
        raise HTTPException(status_code=404, detail="Sponsor not found")

    existing = db.scalar(
        select(SponsorTeamMember).where(
            SponsorTeamMember.sponsor_id == sponsor.id,
            SponsorTeamMember.user_id == user.id,
            SponsorTeamMember.status == "active",
            SponsorTeamMember.removed_at.is_(None),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already on this sponsor team")

    member = SponsorTeamMember(
        sponsor_id=sponsor.id,
        user_id=user.id,
        role=row.role,
        permissions_json=row.permissions_json or DEFAULT_ROLE_PERMISSIONS.get(row.role, {}),
        invited_by_user_id=row.invited_by_user_id,
        status="active",
    )
    db.add(member)
    row.status = "accepted"
    row.accepted_at = datetime.now(UTC)
    row.invited_user_id = user.id
    _write_audit(
        db,
        sponsor_id=sponsor.id,
        action="sponsors.team_accept",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="sponsor_team_member",
        entity_id=str(member.id),
    )
    db.commit()
    db.refresh(member)
    return _serialize_member(db, member)


def list_team_audit(
    db: Session, *, user: User, sponsor_id: uuid.UUID, limit: int = 50
) -> list[dict[str, Any]]:
    sponsor, _ = require_sponsor_team_manage(db, user=user, sponsor_id=sponsor_id)
    rows = list(
        db.scalars(
            select(SponsorTeamAuditLog)
            .where(SponsorTeamAuditLog.sponsor_id == sponsor.id)
            .order_by(SponsorTeamAuditLog.created_at.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": r.id,
            "action": r.action,
            "actor_user_id": r.actor_user_id,
            "target_user_id": r.target_user_id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "metadata": r.metadata_json,
            "created_at": r.created_at,
        }
        for r in rows
    ]
