"""Account profile photo upload — available to any signed-in user (fan or host)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.public_media.processor import PublicMediaProcessingError
from app.public_media.roles import MediaRole
from app.public_media.service import process_and_store_public_media, public_media_response
from app.users.models import User
from app.users.unified_profile import apply_unified_avatar


def store_account_avatar_bytes(
    *,
    db: Session,
    user: User,
    data: bytes,
    filename: str,
    content_type: str,
) -> dict[str, Any]:
    """Validate + process avatar variants. Does not commit."""
    _ = filename
    try:
        payload = process_and_store_public_media(
            db,
            data=data,
            declared_content_type=content_type,
            role=MediaRole.AVATAR,
            created_by_user_id=user.id,
            owner_type="user",
            owner_id=user.id,
            store_source=True,
        )
    except PublicMediaProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    public = public_media_response(payload)
    display_url = public.get("display_url") or public.get("url")
    if not display_url:
        raise HTTPException(status_code=400, detail="Failed to process avatar")
    return {
        "url": display_url,
        "thumbnail_url": public.get("thumbnail_url"),
        "display_url": display_url,
        "media": public,
        "media_type": "avatar",
        "event_id": None,
        # legacy key field — prefer media.variants; kept empty for security
        "key": None,
    }


def upload_and_apply_account_avatar(
    db: Session,
    *,
    user: User,
    data: bytes,
    filename: str,
    content_type: str,
) -> dict[str, Any]:
    """Store avatar variants, sync Fan Passport (+ Host Legacy if present), and commit."""
    result = store_account_avatar_bytes(
        db=db,
        user=user,
        data=data,
        filename=filename,
        content_type=content_type,
    )
    apply_unified_avatar(
        db,
        user,
        result["url"],
        media=result.get("media"),
    )
    db.commit()
    return result
