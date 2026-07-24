"""Selective restriction enforcement helpers (table-backed).

Primitive: ``user_has_restriction(db, user_id, key)`` — only ACTIVE rows where
``ends_at`` is null or in the future. Expired/revoked never block.

Suspended/banned accounts remain globally blocked by auth; these helpers are
for selective activity gates (403 naming the restriction key).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.users.account_status_constants import (
    ACCOUNT_RESTRICTION_LABELS,
    ACCOUNT_STATUS_BANNED,
    ACCOUNT_STATUS_SUSPENDED,
    AMBASSADOR_RESTRICTION_KEYS,
    canonicalize_restriction_key,
)
from app.users.models import User, UserRestriction

RESTRICTION_STATUS_ACTIVE = "active"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def user_has_restriction(
    db: Session, user_id: uuid.UUID, restriction_key: str
) -> bool:
    """True iff an ACTIVE row exists for key with ends_at null or future."""
    key = canonicalize_restriction_key(restriction_key)
    if not key:
        return False
    now = _utcnow()
    row = db.scalar(
        select(UserRestriction.id).where(
            UserRestriction.user_id == user_id,
            UserRestriction.restriction_key == key,
            UserRestriction.status == RESTRICTION_STATUS_ACTIVE,
            or_(
                UserRestriction.ends_at.is_(None),
                UserRestriction.ends_at > now,
            ),
        )
    )
    return row is not None


def active_restriction_keys(db: Session, user_id: uuid.UUID) -> list[str]:
    now = _utcnow()
    rows = list(
        db.scalars(
            select(UserRestriction.restriction_key).where(
                UserRestriction.user_id == user_id,
                UserRestriction.status == RESTRICTION_STATUS_ACTIVE,
                or_(
                    UserRestriction.ends_at.is_(None),
                    UserRestriction.ends_at > now,
                ),
            )
        ).all()
    )
    # Preserve order, unique
    seen: set[str] = set()
    out: list[str] = []
    for key in rows:
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def assert_no_restriction(
    db: Session,
    user_id: uuid.UUID,
    restriction_key: str,
    *,
    detail: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    record_audit: bool = True,
) -> None:
    key = canonicalize_restriction_key(restriction_key)
    if not user_has_restriction(db, user_id, key):
        return
    label = ACCOUNT_RESTRICTION_LABELS.get(key, key)
    if record_audit:
        try:
            from app.core.audit import write_audit_log
            from app.users.admin_user_audit import RESTRICTED_USER_BLOCKED_FROM_ACTION

            write_audit_log(
                db,
                action=RESTRICTED_USER_BLOCKED_FROM_ACTION,
                actor_user_id=user_id,
                resource_type="user",
                resource_id=str(user_id),
                details={
                    "target_user_id": str(user_id),
                    "restriction_keys": [key],
                    "action_attempted": key,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            # Never fail the gate because audit write failed.
            pass
    raise HTTPException(
        status_code=403,
        detail=detail or f"Account restricted ({key}): {label}",
    )


def assert_none_of(
    db: Session,
    user_id: uuid.UUID,
    keys: list[str] | tuple[str, ...],
) -> None:
    for key in keys:
        assert_no_restriction(db, user_id, key)


def _user_globally_blocked(user: User) -> bool:
    status = (getattr(user, "account_status", None) or "").strip().lower()
    if status in {ACCOUNT_STATUS_SUSPENDED, ACCOUNT_STATUS_BANNED}:
        return True
    if not user.is_active:
        return True
    return False


def can_user_checkout(db: Session, user: User) -> bool:
    if _user_globally_blocked(user):
        return False
    return not user_has_restriction(db, user.id, "cannot_checkout")


def can_user_buy_tickets(db: Session, user: User) -> bool:
    if _user_globally_blocked(user):
        return False
    return not (
        user_has_restriction(db, user.id, "cannot_buy_tickets")
        or user_has_restriction(db, user.id, "cannot_checkout")
    )


def can_user_buy_merch(db: Session, user: User) -> bool:
    if _user_globally_blocked(user):
        return False
    return not (
        user_has_restriction(db, user.id, "cannot_buy_merch")
        or user_has_restriction(db, user.id, "cannot_checkout")
    )


def can_user_message(db: Session, user: User) -> bool:
    if _user_globally_blocked(user):
        return False
    return not user_has_restriction(db, user.id, "cannot_message")


def can_user_use_fan_connect(db: Session, user: User) -> bool:
    if _user_globally_blocked(user):
        return False
    return not user_has_restriction(db, user.id, "cannot_use_fan_connect")


def can_user_submit_review(db: Session, user: User) -> bool:
    if _user_globally_blocked(user):
        return False
    return not user_has_restriction(db, user.id, "cannot_submit_reviews")


def can_user_manage_host(db: Session, user: User, host_id: uuid.UUID) -> bool:
    """Host manage gate — any manage-level host restriction blocks."""
    _ = host_id
    if _user_globally_blocked(user):
        return False
    manage_keys = (
        "cannot_manage_events",
        "cannot_create_events",
        "cannot_publish_events",
        "cannot_manage_tickets",
        "cannot_manage_merch",
        "cannot_fulfill_merch",
        "cannot_invite_host_team",
        "cannot_manage_sponsorships",
        "cannot_manage_host_ambassadors",
        "cannot_view_host_finance",
        "read_only_account",
    )
    return not any(user_has_restriction(db, user.id, k) for k in manage_keys)


def can_user_scan(db: Session, user: User, event_id: uuid.UUID) -> bool:
    _ = event_id
    if _user_globally_blocked(user):
        return False
    return not user_has_restriction(db, user.id, "cannot_scan_tickets")


def can_user_promote_as_ambassador(db: Session, user: User) -> bool:
    if _user_globally_blocked(user):
        return False
    if getattr(user, "ambassadors_blocked", False):
        return False
    return not any(
        user_has_restriction(db, user.id, k) for k in AMBASSADOR_RESTRICTION_KEYS
    )


# --- Assert variants used at choke points (403) ---


def assert_can_checkout(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_checkout")


def assert_can_buy_tickets(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_checkout")
    assert_no_restriction(db, user.id, "cannot_buy_tickets")


def assert_can_buy_merch(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_checkout")
    assert_no_restriction(db, user.id, "cannot_buy_merch")


def assert_can_transfer_tickets(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_transfer_tickets")


def assert_can_request_refunds(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_request_refunds")


def assert_can_submit_review(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_submit_reviews")


def assert_can_message(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_message")


def assert_can_use_fan_connect(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_use_fan_connect")


def assert_can_follow_hosts(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_follow_hosts")


def assert_can_follow_fans(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_follow_fans")


def assert_can_edit_passport(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_edit_passport")
    assert_no_restriction(db, user.id, "read_only_account")


def assert_can_use_vault(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_use_vault")


def assert_can_create_events(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_create_events")
    assert_no_restriction(db, user.id, "read_only_account")


def assert_can_publish_events(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_publish_events")
    assert_no_restriction(db, user.id, "read_only_account")


def assert_can_manage_events(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_manage_events")
    assert_no_restriction(db, user.id, "read_only_account")


def assert_can_manage_tickets(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_manage_tickets")


def assert_can_scan_tickets(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_scan_tickets")


def assert_can_manage_merch(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_manage_merch")


def assert_can_fulfill_merch(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_fulfill_merch")


def assert_can_invite_host_team(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_invite_host_team")


def assert_can_manage_sponsorships(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_manage_sponsorships")


def assert_can_manage_host_ambassadors(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_manage_host_ambassadors")


def assert_can_view_host_finance(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_view_host_finance")


def assert_can_join_ambassador_campaigns(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_join_ambassador_campaigns")


def assert_can_promote_events(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_promote_events")


def assert_can_receive_ambassador_rewards(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_receive_ambassador_rewards")


def assert_can_request_ambassador_payouts(db: Session, user: User) -> None:
    assert_no_restriction(db, user.id, "cannot_request_ambassador_payouts")


def assert_can_promote_as_ambassador(db: Session, user: User) -> None:
    """Join / promote entry — any ambassador-group key or ambassadors_blocked.

    Check catalog keys first so 403 names the specific restriction (e.g.
    ``cannot_promote_events``) before the legacy ``ambassadors_blocked`` flag.
    """
    for key in (
        "cannot_join_ambassador_campaigns",
        "cannot_promote_events",
        "cannot_receive_ambassador_rewards",
        "cannot_request_ambassador_payouts",
    ):
        assert_no_restriction(db, user.id, key)
    if getattr(user, "ambassadors_blocked", False):
        raise HTTPException(
            status_code=403,
            detail="Account restricted (cannot_join_ambassador_campaigns): "
            "Blocked from Ambassadors programs",
        )
