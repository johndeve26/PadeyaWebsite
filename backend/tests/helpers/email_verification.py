"""Mark a user email verified in tests (bypass outbox)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User


def mark_user_email_verified(db: Session, *, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    assert user is not None, f"user not found: {email}"
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user
