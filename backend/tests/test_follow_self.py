"""Fan↔fan follow self-rule."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.social.follows import SELF_FOLLOW_DETAIL, assert_not_self_follow, follow_user
from app.users.models import User


def test_assert_not_self_follow_blocks_same_user():
    uid = uuid4()
    with pytest.raises(HTTPException) as exc:
        assert_not_self_follow(follower_user_id=uid, target_user_id=uid)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELF_FOLLOW_DETAIL


def test_assert_not_self_follow_allows_other_user():
    assert_not_self_follow(follower_user_id=uuid4(), target_user_id=uuid4())


def test_follow_user_self_returns_exact_error(db_session: Session):
    user = User(
        email="follow-self@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Follow Self",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        follow_user(db_session, follower=user, target_user_id=user.id)
    assert exc.value.status_code == 400
    assert exc.value.detail == SELF_FOLLOW_DETAIL

    # Other target still hits not-implemented (self check passed).
    other = User(
        email="follow-other@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Follow Other",
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    with pytest.raises(HTTPException) as exc2:
        follow_user(db_session, follower=user, target_user_id=other.id)
    assert exc2.value.status_code == 501
