"""Award / revoke Fan Passport merch badges after verified payment or refund.

Award timing: all current merch badges award after verified payment
(fulfillment row exists). None require pickup/fulfilled today — see
`MERCH_BADGES_REQUIRING_FULFILLMENT` in passport.constants.

Refunds: revoke (delete UserBadge) when criteria no longer met after cancelled
fulfillments. Flush only — callers own the commit.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.passport.badges import evaluate_badge_criteria
from app.passport.constants import MERCH_BADGE_CRITERIA, MERCH_BADGES_REQUIRING_FULFILLMENT
from app.passport.models import FanBadge, UserBadge
from app.passport.seed import seed_fan_badges
from app.users.models import User

# Back-compat alias used by older imports / tests
MERCH_CRITERIA = MERCH_BADGE_CRITERIA


def sync_merch_badges_for_user(db: Session, user_id: uuid.UUID) -> list[FanBadge]:
    """Re-evaluate merch badges: award newly earned, revoke when criteria fail.

    Returns newly awarded FanBadge rows (for optional notifications).
    Meta never includes amounts, order ids, addresses, or payment refs.
    """
    user = db.get(User, user_id)
    if user is None:
        return []
    seed_fan_badges(db)
    criteria = evaluate_badge_criteria(db, user_id)
    badges = list(db.scalars(select(FanBadge).where(FanBadge.is_active.is_(True))))
    existing = {
        ub.badge_id: ub
        for ub in db.scalars(select(UserBadge).where(UserBadge.user_id == user_id))
    }
    newly_awarded: list[FanBadge] = []
    for badge in badges:
        if badge.criteria_key not in MERCH_BADGE_CRITERIA:
            continue
        earned = bool(criteria.get(badge.criteria_key))
        # Optional pickup gate — unused today (empty frozenset).
        if earned and badge.criteria_key in MERCH_BADGES_REQUIRING_FULFILLMENT:
            earned = _fulfillment_complete_for_badge(db, user_id, badge.criteria_key)
        if earned and badge.id not in existing:
            db.add(
                UserBadge(
                    user_id=user_id,
                    badge_id=badge.id,
                    meta={"criteria_key": badge.criteria_key, "source": "merch"},
                )
            )
            newly_awarded.append(badge)
        elif not earned and badge.id in existing:
            # Refund / cancel path: revoke when criteria no longer hold
            db.delete(existing[badge.id])
    db.flush()
    return newly_awarded


def award_merch_badges_for_user(db: Session, user_id: uuid.UUID) -> None:
    """Server-trusted badge award after verified payment. Never encodes spend."""
    newly = sync_merch_badges_for_user(db, user_id)
    if not newly:
        return
    from app.merch.notifications import notify_buyer_merch_badge_earned

    for badge in newly:
        try:
            from app.analytics.trusted import emit_merch_badge_awarded

            emit_merch_badge_awarded(
                db,
                buyer_user_id=user_id,
                badge_key=badge.criteria_key,
            )
        except Exception:  # noqa: BLE001 — analytics must not block badge award
            import logging

            logging.getLogger(__name__).exception(
                "merch_badge_awarded analytics failed for %s", badge.criteria_key
            )
        notify_buyer_merch_badge_earned(db, user_id=user_id, badge=badge)


def revoke_merch_badges_for_user(db: Session, user_id: uuid.UUID) -> None:
    """Re-evaluate and revoke merch badges after refund cancels fulfillments."""
    sync_merch_badges_for_user(db, user_id)


def _fulfillment_complete_for_badge(
    db: Session, user_id: uuid.UUID, criteria_key: str
) -> bool:
    """Pickup/ship gate for badges listed in MERCH_BADGES_REQUIRING_FULFILLMENT."""
    from app.merch.models import MerchFulfillment

    done = ("fulfilled", "delivered", "shipped")
    row = db.scalar(
        select(MerchFulfillment.id).where(
            MerchFulfillment.buyer_user_id == user_id,
            MerchFulfillment.status.in_(done),
        ).limit(1)
    )
    return row is not None
