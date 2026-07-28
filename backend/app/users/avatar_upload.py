"""Account profile photo upload — available to any signed-in user (fan or host)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.media import get_public_media_storage
from app.core.media_folders import user_public_folder
from app.users.models import User
from app.users.unified_profile import apply_unified_avatar


def store_account_avatar_bytes(
    *,
    user: User,
    data: bytes,
    filename: str,
    content_type: str,
) -> dict[str, Any]:
    """Validate + store raster bytes under users/{id}/avatar. Does not commit."""
    storage = get_public_media_storage()
    try:
        stored = storage.store_bytes(
            data=data,
            filename=filename or "avatar.jpg",
            content_type=content_type or "application/octet-stream",
            folder=user_public_folder(user.id, "avatar"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "url": stored.url,
        "key": stored.key,
        "media_type": "avatar",
        "event_id": None,
    }


def upload_and_apply_account_avatar(
    db: Session,
    *,
    user: User,
    data: bytes,
    filename: str,
    content_type: str,
) -> dict[str, Any]:
    """Store avatar, sync Fan Passport (+ Host Legacy if present), and commit."""
    result = store_account_avatar_bytes(
        user=user,
        data=data,
        filename=filename,
        content_type=content_type,
    )
    apply_unified_avatar(db, user, result["url"])
    db.commit()
    return result
