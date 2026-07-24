"""Merch access rules — Vault exclusivity, check-in, followers (teasers only for locked)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.merch.constants import ACCESS_TYPES
from app.merch.models import EventMerchProduct
from app.users.models import User
from app.vault.access import (
    evaluate_access,
    user_follows_host,
    user_holds_host_ticket,
)
from app.vault.models import VaultAccessGrant, VaultItem, VaultPurchase

_ACCESS_TYPE_SET = frozenset(ACCESS_TYPES)

_REASON_MESSAGES = {
    "drop_not_started": "This post-event merch drop is not available yet",
    "hidden": "This product is not available",
    "vault_login_required": "Sign in to unlock Vault-exclusive merch",
    "vault_locked": "Vault access required for this exclusive merch",
    "login_required": "Sign in to purchase this merch",
    "follower_required": "Follow this host to purchase this merch",
    "ticket_required": "A qualifying ticket is required for this merch",
    "vip_ticket_required": "A VIP ticket is required for this merch",
    "check_in_required": "Check-in at the event is required for this merch",
    "invite_required": "An invite or Vault unlock is required for this merch",
    "paid_vault_required": "Paid Vault membership is required for this merch",
}

_VAULT_REASON_MAP = {
    "login_required": "vault_login_required",
    "followers_only": "follower_required",
    "ticket_required": "ticket_required",
    "check_in_required": "check_in_required",
    "vip_ticket_required": "vip_ticket_required",
    "purchase_required": "vault_locked",
    "invite_only": "invite_required",
    "admin_hidden": "vault_locked",
    "expired": "vault_locked",
    "not_started": "vault_locked",
    "access_ended": "vault_locked",
    "Item unavailable": "vault_locked",
    "Item not published": "vault_locked",
    "locked": "vault_locked",
}


def product_is_drop_live(product: EventMerchProduct, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    if product.storefront_visibility != "post_event_drop":
        return True
    if product.post_event_drop_at is None:
        return True
    drop_at = product.post_event_drop_at
    if drop_at.tzinfo is None:
        drop_at = drop_at.replace(tzinfo=UTC)
    return current >= drop_at


def product_requires_vault_gate(product: EventMerchProduct) -> bool:
    """True when product is Vault-gated (either flag). Keep flags conceptually aligned."""
    return bool(product.is_vault_exclusive or product.requires_vault_access)


def _normalize_access_type(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    return cleaned if cleaned in _ACCESS_TYPE_SET else None


def _map_vault_reason(reason: str) -> str:
    return _VAULT_REASON_MAP.get(reason, "vault_locked")


def _user_has_any_host_vault_unlock(
    db: Session, *, host_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    host_items = select(VaultItem.id).where(VaultItem.host_id == host_id)
    grant = db.scalar(
        select(VaultAccessGrant.id)
        .where(
            VaultAccessGrant.user_id == user_id,
            VaultAccessGrant.vault_item_id.in_(host_items),
        )
        .limit(1)
    )
    if grant is not None:
        return True
    paid = db.scalar(
        select(VaultPurchase.id)
        .where(
            VaultPurchase.user_id == user_id,
            VaultPurchase.status == "paid",
            VaultPurchase.vault_item_id.in_(host_items),
        )
        .limit(1)
    )
    return paid is not None


def _evaluate_required_vault_item(
    db: Session,
    *,
    vault_item_id: uuid.UUID,
    buyer_user_id: uuid.UUID | None,
) -> tuple[bool, str | None]:
    item = db.get(VaultItem, vault_item_id)
    if item is None:
        return False, "vault_locked"
    user = db.get(User, buyer_user_id) if buyer_user_id else None
    has_access, reason = evaluate_access(db, item=item, user=user)
    if has_access:
        return True, None
    return False, _map_vault_reason(reason)


def buyer_eligible_for_product(
    db: Session,
    *,
    product: EventMerchProduct,
    buyer_user_id: uuid.UUID | None,
    has_ticket_cover: bool = False,
) -> tuple[bool, str | None]:
    """Return (eligible, reason_code). Never leaks Vault payload — reason is coarse.

    has_ticket_cover: True when this checkout already includes tickets for the event
    (or the buyer already holds one) — satisfies ticket_holder-style gates.
    """
    if not product_is_drop_live(product):
        return False, "drop_not_started"
    if product.storefront_visibility == "hidden":
        return False, "hidden"

    exclusive = product_requires_vault_gate(product)
    access = _normalize_access_type(product.required_access_type)
    need_vip = bool(getattr(product, "requires_vip", False) or access == "vip_ticket_holder")
    need_check_in = bool(product.requires_check_in or access == "checked_in_attendee")
    need_ticket = bool(
        product.requires_ticket
        or access == "ticket_holder"
        or need_vip
        or need_check_in
    )

    if exclusive or access or need_ticket:
        if buyer_user_id is None:
            return False, "vault_login_required" if exclusive else "login_required"

    # Specific Vault item — full evaluate_access (follower/ticket/paid/invite/etc.)
    if exclusive and product.required_vault_item_id is not None:
        ok, reason = _evaluate_required_vault_item(
            db,
            vault_item_id=product.required_vault_item_id,
            buyer_user_id=buyer_user_id,
        )
        if not ok:
            return False, reason
    elif exclusive and access == "paid_vault_member":
        assert buyer_user_id is not None
        if not _user_has_any_host_vault_unlock(
            db, host_id=product.host_id, user_id=buyer_user_id
        ):
            return False, "paid_vault_required"
    elif exclusive and access == "invite_only":
        # Invite-only merch without a linked Vault item cannot be redeemed safely.
        return False, "invite_required"
    elif exclusive and access is None and product.required_vault_item_id is None:
        # Bare Vault exclusive — require any paid/granted Vault unlock for this host.
        assert buyer_user_id is not None
        if not _user_has_any_host_vault_unlock(
            db, host_id=product.host_id, user_id=buyer_user_id
        ):
            return False, "paid_vault_required"

    # Merch-level access gates (may stack with Vault item access)
    if access == "follower" and buyer_user_id:
        if not user_follows_host(db, host_id=product.host_id, user_id=buyer_user_id):
            return False, "follower_required"

    if need_vip and buyer_user_id:
        if not user_holds_host_ticket(
            db,
            host_id=product.host_id,
            user_id=buyer_user_id,
            vip_only=True,
            event_id=product.event_id,
            require_check_in=need_check_in,
        ):
            return False, "vip_ticket_required"
    elif need_check_in and buyer_user_id:
        if not user_holds_host_ticket(
            db,
            host_id=product.host_id,
            user_id=buyer_user_id,
            event_id=product.event_id,
            require_check_in=True,
        ):
            return False, "check_in_required"
    elif need_ticket and buyer_user_id:
        # Same-checkout tickets cover plain ticket gates (not VIP/check-in).
        if not has_ticket_cover and not user_holds_host_ticket(
            db,
            host_id=product.host_id,
            user_id=buyer_user_id,
            event_id=product.event_id,
            require_check_in=False,
        ):
            return False, "ticket_required"

    if access == "paid_vault_member" and buyer_user_id and not exclusive:
        if not _user_has_any_host_vault_unlock(
            db, host_id=product.host_id, user_id=buyer_user_id
        ):
            return False, "paid_vault_required"

    if access == "invite_only" and not exclusive:
        if product.required_vault_item_id is None:
            return False, "invite_required"
        ok, reason = _evaluate_required_vault_item(
            db,
            vault_item_id=product.required_vault_item_id,
            buyer_user_id=buyer_user_id,
        )
        if not ok:
            return False, reason

    return True, None


def assert_buyer_can_purchase(
    db: Session,
    *,
    product: EventMerchProduct,
    buyer_user_id: uuid.UUID,
    has_ticket_cover: bool = False,
) -> None:
    ok, reason = buyer_eligible_for_product(
        db,
        product=product,
        buyer_user_id=buyer_user_id,
        has_ticket_cover=has_ticket_cover,
    )
    if ok:
        return
    raise HTTPException(
        status_code=403,
        detail=_REASON_MESSAGES.get(reason or "", "Not eligible for this merch"),
    )


def access_requirements_for_product(product: EventMerchProduct) -> list[str]:
    """Coarse, public-safe unlock steps — never Vault body/media/secrets."""
    requirements: list[str] = []
    exclusive = product_requires_vault_gate(product)
    access = _normalize_access_type(product.required_access_type)

    if exclusive:
        if product.required_vault_item_id is not None:
            requirements.append("Unlock the linked Vault drop")
        elif access == "paid_vault_member" or access is None:
            requirements.append("Become a paid Vault member for this host")
        elif access == "invite_only":
            requirements.append("Redeem a Vault invite for this drop")
        else:
            requirements.append("Unlock Vault access for this host")

    if access == "follower":
        requirements.append("Follow this host")
    elif access == "vip_ticket_holder" or getattr(product, "requires_vip", False):
        requirements.append("Hold a VIP ticket for this event")
    elif access == "checked_in_attendee" or product.requires_check_in:
        requirements.append("Check in at the event")
    elif access == "ticket_holder" or product.requires_ticket:
        requirements.append("Hold a ticket for this event")
    elif access == "invite_only" and "Redeem a Vault invite" not in " ".join(requirements):
        requirements.append("Redeem an invite to unlock")
    elif access == "paid_vault_member" and not any(
        "paid Vault" in r for r in requirements
    ):
        requirements.append("Become a paid Vault member for this host")

    if not requirements and exclusive:
        requirements.append("Unlock Vault access")

    # Dedupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for item in requirements:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def unlock_hint_for_reason(reason: str | None, *, access: str | None = None) -> str | None:
    if not reason:
        return None
    hints = {
        "vault_login_required": "Sign in, then unlock Vault access to purchase.",
        "login_required": "Sign in to see if you can purchase this merch.",
        "vault_locked": "Unlock the required Vault drop to purchase this merch.",
        "paid_vault_required": "Unlock a Vault drop from this host to purchase.",
        "follower_required": "Follow this host to unlock this merch.",
        "ticket_required": "Get a ticket for this event to unlock this merch.",
        "vip_ticket_required": "A VIP ticket unlocks this exclusive merch.",
        "check_in_required": "Check in at the event to unlock this merch.",
        "invite_required": "Redeem your Vault invite to unlock this merch.",
        "drop_not_started": "This drop is not live yet.",
        "hidden": "This product is not available.",
    }
    if reason in hints:
        return hints[reason]
    if access == "follower":
        return "Follow this host to unlock."
    return "View access requirements to learn how to unlock."


def public_teaser_fields(product: EventMerchProduct, *, eligible: bool) -> dict:
    """For locked Vault / exclusive products — teaser only, no locked Vault content."""
    exclusive = product_requires_vault_gate(product)
    access = _normalize_access_type(product.required_access_type)
    requirements = access_requirements_for_product(product)

    flag_locked = bool(
        not eligible
        and not exclusive
        and (
            access
            or product.requires_ticket
            or product.requires_check_in
            or getattr(product, "requires_vip", False)
        )
    )
    if eligible or not exclusive:
        # Non-vault access locks still expose a soft lock state for CTA switching.
        if flag_locked:
            if getattr(product, "requires_vip", False) or access == "vip_ticket_holder":
                label = "VIP ticket holders only"
            elif product.requires_check_in or access == "checked_in_attendee":
                label = "Checked-in attendees only"
            elif product.requires_ticket or access == "ticket_holder":
                label = "Ticket holders only"
            else:
                label = {
                    "follower": "Followers only",
                    "ticket_holder": "Ticket holders only",
                    "vip_ticket_holder": "VIP ticket holders only",
                    "checked_in_attendee": "Checked-in attendees only",
                    "paid_vault_member": "Vault members only",
                    "invite_only": "Invite only",
                }.get(access or "", "Exclusive")
            return {
                "access_locked": True,
                "teaser_only": False,
                "access_label": label,
                "access_requirements": requirements,
                "unlock_hint": unlock_hint_for_reason(None, access=access),
            }
        return {
            "access_locked": False,
            "teaser_only": False,
            "access_label": None,
            "access_requirements": [],
            "unlock_hint": None,
        }

    label = "Vault exclusive"
    if access == "follower":
        label = "Followers only"
    elif getattr(product, "requires_vip", False) or access == "vip_ticket_holder":
        label = "VIP ticket holders only"
    elif product.requires_check_in or access == "checked_in_attendee":
        label = "Checked-in attendees only"
    elif product.requires_ticket or access == "ticket_holder":
        label = "Ticket holders only"
    elif access == "paid_vault_member":
        label = "Vault members only"
    elif access == "invite_only":
        label = "Invite only"

    return {
        "access_locked": True,
        "teaser_only": True,
        "access_label": label,
        "access_requirements": requirements,
        # Scrub rich description for locked vault merch teasers — never Vault body.
        "description": None if exclusive else product.description,
        "unlock_hint": unlock_hint_for_reason("vault_locked", access=access),
    }
