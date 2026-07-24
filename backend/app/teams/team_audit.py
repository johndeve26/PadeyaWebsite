"""Host team + desk audit helpers — safe metadata, unified feed."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.hosts.models import HostTeamAuditLog
from app.teams.scan_audit import DeskScanAuditLog
from app.users.models import User
from app.users.service import get_user_by_id

# Product-facing team audit actions (plus legacy names kept for BC).
TEAM_AUDIT_ACTIONS: tuple[str, ...] = (
    "hosts.team_invite",
    "hosts.team_accept",
    "hosts.team_member_added",
    "hosts.team_decline",
    "hosts.team_revoke",
    "hosts.team_resend",
    "hosts.team_suspend",
    "hosts.team_permissions_update",
    "hosts.team_scope_update",
    "hosts.team_finance_permission_grant",
    "hosts.team_permission_denied",
    "hosts.team_create",
    "hosts.team_update",
    "hosts.team_archive",
    "hosts.team_remove",
    "hosts.team_restore",
)

ACTION_LABELS: dict[str, str] = {
    "hosts.team_invite": "Invite sent",
    "hosts.team_accept": "Invite accepted",
    "hosts.team_member_added": "Member added",
    "hosts.team_decline": "Invite declined",
    "hosts.team_revoke": "Invite revoked",
    "hosts.team_resend": "Invite resent",
    "hosts.team_suspend": "Member suspended",
    "hosts.team_permissions_update": "Permissions changed",
    "hosts.team_scope_update": "Scope changed",
    "hosts.team_finance_permission_grant": "Payout/finance permission grant",
    "hosts.team_permission_denied": "Denied permission attempt",
    "hosts.team_create": "Member created",
    "hosts.team_update": "Member updated",
    "hosts.team_archive": "Member removed",
    "hosts.team_remove": "Member removed",
    "hosts.team_restore": "Member restored",
    "tickets.scan": "Ticket scanned",
    "merch.scan_pickup": "Merch pickup scanned",
    "merch.pickup_scan": "Merch pickup scanned",
}

# Permissions that should write a denial audit when blocked.
SENSITIVE_PERMISSIONS: frozenset[str] = frozenset(
    {
        "team.invite",
        "team.edit_permissions",
        "team.remove_members",
        "finance.view_payouts",
        "finance.manage_payouts",
        "finance.manage_payout_settings",
        "events.create",
        "events.edit",
        "events.publish",
        "events.cancel",
        "tickets.manage_pricing",
        "tickets.manage_capacity",
        "merch.manage_inventory",
        "merch.manage_shipping",
        "ambassadors.approve_rewards",
        "ambassadors.reject_rewards",
        "ambassadors.mark_rewards_paid",
        "ambassadors.reverse_rewards",
        "ambassadors.export",
    }
)

FINANCE_PERMISSION_KEYS: frozenset[str] = frozenset(
    {
        "finance.view_payouts",
        "finance.manage_payouts",
        "finance.manage_payout_settings",
    }
)

_BLOCKED_KEY_EXACT = frozenset(
    {
        "token",
        "token_hash",
        "raw_token",
        "invite_token",
        "password",
        "secret",
        "api_key",
        "authorization",
        "account_number",
        "account_number_encrypted",
        "account_number_full",
        "card_number",
        "cvv",
        "pin",
        "paystack_reference",
        "payment_reference",
        "payment_ref",
        "provider_reference",
        "authorization_code",
        "access_code",
        "webhook_secret",
    }
)

_BLOCKED_KEY_SUBSTR = (
    "token",
    "secret",
    "password",
    "encrypted",
    "paystack",
    "payment_ref",
    "account_number",
    "card_",
    "authorization",
    "api_key",
    "private_key",
)


def action_label(action: str) -> str:
    if action in ACTION_LABELS:
        return ACTION_LABELS[action]
    # Desk scan with result suffix not needed — label from base action.
    cleaned = action.replace("hosts.", "").replace("_", " ").replace(".", " ")
    return cleaned[:1].upper() + cleaned[1:] if cleaned else action


def sanitize_audit_metadata(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip secrets and private payment references from audit metadata."""
    if not raw:
        return None
    out: dict[str, Any] = {}
    for key, value in raw.items():
        key_l = str(key).lower()
        if key_l in _BLOCKED_KEY_EXACT:
            continue
        if any(part in key_l for part in _BLOCKED_KEY_SUBSTR):
            continue
        if isinstance(value, dict):
            nested = sanitize_audit_metadata(value)
            if nested:
                out[key] = nested
            continue
        if isinstance(value, list):
            safe_list: list[Any] = []
            for item in value:
                if isinstance(item, dict):
                    nested = sanitize_audit_metadata(item)
                    if nested:
                        safe_list.append(nested)
                elif isinstance(item, (str, int, float, bool)) or item is None:
                    # Drop long opaque strings that look like secrets/refs.
                    if isinstance(item, str) and _looks_like_secret(item):
                        continue
                    safe_list.append(item)
            out[key] = safe_list
            continue
        if isinstance(value, str) and _looks_like_secret(value):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        else:
            out[key] = str(value)[:120]
    return out or None


def _looks_like_secret(value: str) -> bool:
    if len(value) >= 40 and re.fullmatch(r"[A-Za-z0-9_\-+/=]+", value or ""):
        return True
    lower = value.lower()
    return any(
        marker in lower
        for marker in ("sk_", "pk_live", "pk_test", "whsec_", "bearer ")
    )


def email_hint(email: str | None) -> str | None:
    if not email:
        return None
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    keep = local[:1] if local else "*"
    return f"{keep}***@{domain}"


def user_public_label(user: User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or email_hint(user.email) or str(user.id)


def write_team_audit(
    db: Session,
    *,
    host_id: uuid.UUID,
    action: str,
    actor_user_id: uuid.UUID | None,
    target_user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    safe = sanitize_audit_metadata(metadata)
    entity = entity_type or "host_team_member"
    write_audit_log(
        db,
        action=action,
        actor_user_id=actor_user_id,
        resource_type="host_team_member",
        resource_id=entity_id,
        details={
            "host_id": str(host_id),
            "entity_type": entity,
            **(safe or {}),
        },
    )
    db.add(
        HostTeamAuditLog(
            host_id=host_id,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            entity_type=entity,
            entity_id=entity_id,
            metadata_json=safe,
        )
    )


def finance_keys_granted(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> list[str]:
    prev = before or {}
    nxt = after or {}
    granted: list[str] = []
    for key in FINANCE_PERMISSION_KEYS:
        if not bool(prev.get(key)) and bool(nxt.get(key)):
            granted.append(key)
    return granted


def write_permission_denied_audit(
    db: Session,
    *,
    host_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    permission: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if permission not in SENSITIVE_PERMISSIONS:
        return
    write_team_audit(
        db,
        host_id=host_id,
        action="hosts.team_permission_denied",
        actor_user_id=actor_user_id,
        target_user_id=actor_user_id,
        entity_type="host_permission",
        entity_id=permission,
        metadata={
            "permission": permission,
            **(metadata or {}),
        },
    )


def _serialize_team_row(db: Session, log: HostTeamAuditLog) -> dict[str, Any]:
    actor = get_user_by_id(db, log.actor_user_id) if log.actor_user_id else None
    target = get_user_by_id(db, log.target_user_id) if log.target_user_id else None
    meta = sanitize_audit_metadata(log.metadata_json) or {}
    target_label = user_public_label(target)
    if target_label is None and isinstance(meta.get("invited_email"), str):
        target_label = email_hint(meta["invited_email"])
        meta = {**meta, "invited_email": target_label}
    elif "invited_email" in meta and isinstance(meta["invited_email"], str):
        meta = {**meta, "invited_email": email_hint(meta["invited_email"])}
    return {
        "id": log.id,
        "action": log.action,
        "action_label": action_label(log.action),
        "actor_user_id": log.actor_user_id,
        "actor_label": user_public_label(actor),
        "target_user_id": log.target_user_id,
        "target_label": target_label,
        "resource_type": log.entity_type,
        "resource_id": log.entity_id,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "details": {
            "host_id": str(log.host_id),
            **meta,
        },
        "created_at": log.created_at,
        "source": "team",
    }


def _serialize_desk_row(db: Session, log: DeskScanAuditLog) -> dict[str, Any]:
    actor = get_user_by_id(db, log.actor_user_id) if log.actor_user_id else None
    action = log.action
    label = action_label(action)
    if log.result == "denied":
        label = f"{label} (denied)"
    elif log.result in {"success", "allowed", "duplicate"}:
        pass
    meta = sanitize_audit_metadata(log.metadata_json) or {}
    if log.denial_reason:
        meta = {**meta, "denial_reason": log.denial_reason, "result": log.result}
    else:
        meta = {**meta, "result": log.result}
    entity_type = "ticket" if log.ticket_id else "merch_order_item"
    entity_id = str(log.ticket_id or log.merch_order_item_id or log.event_id or "")
    return {
        "id": log.id,
        "action": action,
        "action_label": label,
        "actor_user_id": log.actor_user_id,
        "actor_label": user_public_label(actor),
        "target_user_id": None,
        "target_label": None,
        "resource_type": entity_type,
        "resource_id": entity_id or None,
        "entity_type": entity_type,
        "entity_id": entity_id or None,
        "details": {
            "host_id": str(log.host_id) if log.host_id else None,
            "event_id": str(log.event_id) if log.event_id else None,
            **meta,
        },
        "created_at": log.created_at,
        "source": "desk_scan",
    }


def list_host_audit_feed(
    db: Session,
    *,
    host_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Unified team lifecycle + desk scan audit for a host workspace."""
    cap = min(max(limit, 1), 100)
    team_logs = list(
        db.scalars(
            select(HostTeamAuditLog)
            .where(
                HostTeamAuditLog.host_id == host_id,
                HostTeamAuditLog.action.in_(TEAM_AUDIT_ACTIONS),
            )
            .order_by(HostTeamAuditLog.created_at.desc())
            .limit(cap)
        )
    )
    desk_logs = list(
        db.scalars(
            select(DeskScanAuditLog)
            .where(DeskScanAuditLog.host_id == host_id)
            .order_by(DeskScanAuditLog.created_at.desc())
            .limit(cap)
        )
    )
    rows = [_serialize_team_row(db, log) for log in team_logs] + [
        _serialize_desk_row(db, log) for log in desk_logs
    ]
    rows.sort(
        key=lambda r: r["created_at"] or datetime.min,
        reverse=True,
    )
    return rows[:cap]
