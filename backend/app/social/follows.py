"""Fan↔fan follow helpers for Pàdéyá.

Host follow remains in ``app.crm`` (``follow_host``). This module owns
user→user follow self-rules for current and future fan-to-fan following.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.users.models import User

SELF_FOLLOW_DETAIL = "You can’t follow yourself."


def assert_not_self_follow(
    *, follower_user_id: UUID, target_user_id: UUID
) -> None:
    """Block follow_user when follower_user_id === target_user_id."""
    if follower_user_id == target_user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=SELF_FOLLOW_DETAIL,
        )


def follow_user(
    db: Session,
    *,
    follower: User,
    target_user_id: UUID,
) -> dict:
    """Create a fan↔fan follow.

    Always denies self-follow. Fan-to-fan following is not product-ready yet;
    once it ships, persist the follow row after this assert.
    """
    from app.users.restrictions import assert_can_follow_fans

    assert_can_follow_fans(db, follower)
    assert_not_self_follow(
        follower_user_id=follower.id, target_user_id=target_user_id
    )
    # Keep unused until fan↔fan follows ship (db reserved for that path).
    _ = db
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        detail="Fan-to-fan following is not available yet.",
    )
