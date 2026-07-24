"""Host-as-Fan self-abuse guards for Pàdéyá.

Only the **host owner** is blocked from using Personal/Fan/customer flows
against their own host workspace, profile, or events.

Blocked for own host (owner only)
---------------------------------
- follow own host (+ marketing opt-in / follower counts)
- public event / merch review (+ review prompts / eligibility)
- fan→host messaging from Personal
- buy own-event tickets / merch / checkout
- join own ambassador campaign for reward (unless allow_host_owner_commission)
- earn commission from own host campaign (unless allow_host_owner_commission)
- use own referral / ambassador code to inflate own-host attribution
  (defense-in-depth with checkout block + self-referral + host-owner commission)
- boost public popularity / Legacy ranking via owner self-actions
  (metrics collectors exclude owner tickets, reviews, followers)

Kept existing self-blocks (any actor)
-------------------------------------
- Fan Connect to self
- self-referral commission (buyer == ambassador)
- Vault subscribe to own host
- invite self to host team
- transfer ticket to self

Team members, promoters, ambassadors, scanners, merch staff, volunteers, and
other event staff may buy tickets, follow, review, and message that host
normally when product rules otherwise allow it.

A Host A owner may still fan Host B normally.

Admin / demo / exceptions
-------------------------
- **No production bypasses.** These asserts must not accept admin, impersonation,
  env, or feature-flag overrides in normal product paths.
- **Demo / local seed accounts** sign in and use the product normally (including
  buying from *other* hosts). Seed commerce must not use live Paystack for
  own-host purchases — and ownership already blocks own-host checkout.
- **Dev test orders** (if ever needed) belong in a separate, explicitly marked
  test-order / local-only helper — not real payment checkout, and never counted
  toward public metrics. That helper is intentionally **not** implemented here.
- **Admin impersonation** uses the target user's identity. Product ownership
  rules still apply. Sensitive money paths are also blocked by impersonation
  guards. A future admin-only test mode may exist only if it is explicit,
  audited, and excluded from public rankings / trust / commissions.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.hosts.models import Host, HostProfile

DEFAULT_DETAIL = (
    "You can’t use Personal/Fan actions on your own host workspace. "
    "Interact with other hosts on Pàdéyá instead."
)

CHECKOUT_OWN_HOST_DETAIL = (
    "You can’t buy tickets or merch from your own host workspace."
)

REVIEW_OWN_HOST_DETAIL = (
    "You can’t publicly review your own host workspace."
)

MESSAGING_OWN_HOST_DETAIL = (
    "You can’t message your own host workspace from your Personal account."
)

FOLLOW_OWN_HOST_DETAIL = (
    "You can’t follow your own host profile."
)


def is_user_owner_of_host(
    db: Session, *, user_id: UUID, host_profile_id: UUID
) -> bool:
    """True only when ``user_id`` is the actual owner of this host workspace.

    ``host_profile_id`` is the host workspace id (``hosts.id``). A
    ``host_profiles.id`` is also accepted and resolved to its host.

    Returns true when ``hosts.user_id == user_id`` for that workspace.

    Never true for:
    - ambassador / promoter
    - scanner / merch / event staff / volunteer
    - ordinary host team member
    - buyer / fan / follower
    - Host A owner checking Host B
    """
    host = db.get(Host, host_profile_id)
    if host is not None:
        return host.user_id == user_id

    profile = db.get(HostProfile, host_profile_id)
    if profile is None:
        return False
    host = db.get(Host, profile.host_id)
    return host is not None and host.user_id == user_id


def is_user_affiliated_with_host(
    db: Session, *, user_id: UUID, host_profile_id: UUID
) -> bool:
    """Deprecated alias for :func:`is_user_owner_of_host` (owner-only)."""
    return is_user_owner_of_host(
        db, user_id=user_id, host_profile_id=host_profile_id
    )


def user_is_host_owner_or_team(
    db: Session, *, user_id: UUID, host_id: UUID
) -> bool:
    """Deprecated alias — self-abuse is owner-only; does not include team."""
    return is_user_owner_of_host(db, user_id=user_id, host_profile_id=host_id)


def order_excluded_from_public_metrics(order: object | None) -> bool:
    """True for future admin/dev test orders that must never inflate public stats.

    Production orders have no exclusion flag. When a dedicated test-order helper
    is added later, mark rows with ``is_test_order`` and/or
    ``exclude_from_public_metrics`` so Legacy / discover / Passport trust inputs
    ignore them even if ownership checks were skipped in that helper.
    """
    if order is None:
        return False
    if bool(getattr(order, "exclude_from_public_metrics", False)):
        return True
    if bool(getattr(order, "is_test_order", False)):
        return True
    return False


def assert_not_own_host_as_fan(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
    detail: str | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> None:
    """Raise when the host **owner** uses Personal/Fan actions on their own host.

    Intentionally has no admin / impersonation / env bypass parameters.
    """
    if is_user_owner_of_host(db, user_id=user_id, host_profile_id=host_id):
        raise HTTPException(
            status_code=status_code,
            detail=detail or DEFAULT_DETAIL,
        )


def assert_owner_not_buying_own_host(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
) -> None:
    """Block production checkout when the buyer owns the event's host."""
    assert_not_own_host_as_fan(
        db,
        user_id=user_id,
        host_id=host_id,
        detail=CHECKOUT_OWN_HOST_DETAIL,
        status_code=status.HTTP_403_FORBIDDEN,
    )


def assert_buyer_not_affiliated_with_event_host(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
) -> None:
    """Deprecated alias for :func:`assert_owner_not_buying_own_host`."""
    assert_owner_not_buying_own_host(db, user_id=user_id, host_id=host_id)


def assert_not_own_host_public_review(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
) -> None:
    """Block public event/merch reviews when the user owns the host."""
    assert_not_own_host_as_fan(
        db,
        user_id=user_id,
        host_id=host_id,
        detail=REVIEW_OWN_HOST_DETAIL,
        status_code=status.HTTP_403_FORBIDDEN,
    )


def assert_not_own_host_follow(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
) -> None:
    """Block follow / marketing opt-in when the user owns the host."""
    assert_not_own_host_as_fan(
        db,
        user_id=user_id,
        host_id=host_id,
        detail=FOLLOW_OWN_HOST_DETAIL,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def assert_not_own_host_fan_messaging(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
) -> None:
    """Block Personal fan↔host messaging when the fan owns the host."""
    assert_not_own_host_as_fan(
        db,
        user_id=user_id,
        host_id=host_id,
        detail=MESSAGING_OWN_HOST_DETAIL,
        status_code=status.HTTP_403_FORBIDDEN,
    )
