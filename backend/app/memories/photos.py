"""Photo contribution upload, patch, delete, and moderation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.media import (
    MediaStorageError,
    delete_media_keys,
    get_public_media_storage,
    storage_key_from_url,
)
from app.core.media_folders import memory_public_folder
from app.events.models import Event
from app.memories.constants import (
    FAN_MEMORY_PHOTO_LIMIT,
    HOST_MEMORY_PHOTO_LIMIT,
)
from app.memories.eligibility import (
    count_active_photos,
    event_memory_upload_window_open,
    user_holds_event_memory_ticket,
)
from app.memories.image_processing import (
    MemoryImageError,
    ProcessedMemoryImage,
    process_memory_image,
)
from app.memories.models import EventMemory, EventMemoryMedia
from app.memories.schemas import MemoryMediaCreate, MemoryPhotoPatch
from app.memories.service import (
    _require_host_owns_event,
    ensure_event_memory,
    get_memory_by_event_id,
    invalidate_memory_caches,
    serialize_memory,
)
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PUBLIC
from app.users.models import User
from app.users.service import user_has_permission


def _assert_photo_slot_available(
    db: Session,
    *,
    memory_id: UUID,
    uploader_role: str,
    uploader_user_id: UUID | None,
    limit: int,
) -> int:
    """Lock memory row and enforce per-role photo limits (CC-007). Returns used count."""
    locked = db.scalar(
        select(EventMemory.id).where(EventMemory.id == memory_id).with_for_update()
    )
    if locked is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    used = count_active_photos(
        db,
        memory_id=memory_id,
        uploader_role=uploader_role,
        uploader_user_id=uploader_user_id,
    )
    if used >= limit:
        if uploader_role == "host":
            detail = f"Host memory limit is {limit} photos"
        else:
            detail = f"Fan memory limit is {limit} photos per event"
        raise HTTPException(status_code=400, detail=detail)
    return used


def _soft_check_photo_limit(
    db: Session,
    *,
    memory_id: UUID,
    uploader_role: str,
    uploader_user_id: UUID | None,
    limit: int,
) -> None:
    """Fast unlocked pre-check to reject obvious overflows before image processing."""
    used = count_active_photos(
        db,
        memory_id=memory_id,
        uploader_role=uploader_role,
        uploader_user_id=uploader_user_id,
    )
    if used >= limit:
        if uploader_role == "host":
            detail = f"Host memory limit is {limit} photos"
        else:
            detail = f"Fan memory limit is {limit} photos per event"
        raise HTTPException(status_code=400, detail=detail)


def _next_sort_order(db: Session, memory_id: UUID) -> int:
    max_order = db.scalar(
        select(func.max(EventMemoryMedia.sort_order)).where(
            EventMemoryMedia.memory_id == memory_id
        )
    )
    return int(max_order or 0) + 1


def _clear_other_covers(db: Session, *, memory_id: UUID, keep_id: UUID | None) -> None:
    stmt = (
        update(EventMemoryMedia)
        .where(
            EventMemoryMedia.memory_id == memory_id,
            EventMemoryMedia.is_cover.is_(True),
        )
        .values(is_cover=False)
    )
    if keep_id is not None:
        stmt = stmt.where(EventMemoryMedia.id != keep_id)
    db.execute(stmt)


def _attribution_for_user(db: Session, user_id: UUID | None) -> tuple[str | None, bool]:
    if user_id is None:
        return None, True
    passport = db.scalar(
        select(FanPassport).where(FanPassport.user_id == user_id)
    )
    if passport is not None and passport.visibility == VISIBILITY_PUBLIC:
        name = (passport.display_name or "").strip()
        if name:
            return name, True
    return None, True


def serialize_photo(
    db: Session,
    media: EventMemoryMedia,
    *,
    include_private: bool = False,
) -> dict:
    attribution: str | None = None
    verified = False
    if media.uploader_role == "fan":
        attribution, verified = _attribution_for_user(db, media.uploader_user_id)
    return {
        "id": media.id,
        "media_type": media.media_type,
        "url": media.url,
        "thumbnail_url": media.thumbnail_url or media.url,
        "storage_key": media.storage_key if include_private else None,
        "label": media.label,
        "caption": media.caption,
        "sort_order": media.sort_order,
        "uploader_role": media.uploader_role,
        "is_cover": bool(media.is_cover),
        "status": media.status,
        "width": media.width,
        "height": media.height,
        "mime_type": media.mime_type,
        "size_bytes": media.size_bytes if include_private else None,
        "attribution": attribution,
        "verified_attendee": verified and media.uploader_role == "fan",
        "created_at": media.created_at,
    }


def _cleanup_processed_uploads(processed: ProcessedMemoryImage) -> None:
    delete_media_keys(processed.display_key, processed.thumbnail_key)


def _delete_photo_storage_objects(media: EventMemoryMedia) -> None:
    """Remove display + thumbnail objects for permanent deletion paths."""
    thumb_key = storage_key_from_url(media.thumbnail_url)
    delete_media_keys(media.storage_key, thumb_key)


async def _read_upload(file: UploadFile, *, max_bytes: int = 10 * 1024 * 1024) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 256)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image must be 10MB or smaller",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _create_photo_row(
    db: Session,
    *,
    memory: EventMemory,
    event: Event,
    user: User,
    role: str,
    processed,
    caption: str | None,
    make_cover: bool,
) -> EventMemoryMedia:
    if make_cover:
        _clear_other_covers(db, memory_id=memory.id, keep_id=None)

    media = EventMemoryMedia(
        memory_id=memory.id,
        media_type="image",
        url=processed.display_url,
        storage_key=processed.display_key,
        thumbnail_url=processed.thumbnail_url,
        caption=(caption or "").strip() or None,
        sort_order=_next_sort_order(db, memory.id),
        uploader_user_id=user.id,
        uploader_role=role,
        width=processed.width,
        height=processed.height,
        mime_type=processed.mime_type,
        size_bytes=processed.size_bytes,
        is_cover=make_cover,
        status="active",
    )
    db.add(media)
    db.flush()
    return media


async def upload_host_photo(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    file: UploadFile,
    caption: str | None = None,
    is_cover: bool = False,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)

    if event.status not in {"published", "paused", "completed"}:
        raise HTTPException(
            status_code=400,
            detail="Memories uploads require a published, paused, or completed event",
        )

    memory = ensure_event_memory(db, event)
    if memory.status == "hidden":
        raise HTTPException(status_code=403, detail="This memory was hidden by moderation")

    _soft_check_photo_limit(
        db,
        memory_id=memory.id,
        uploader_role="host",
        uploader_user_id=None,
        limit=HOST_MEMORY_PHOTO_LIMIT,
    )

    raw = await _read_upload(file)
    try:
        processed = process_memory_image(
            data=raw,
            declared_content_type=file.content_type,
            event_id=event.id,
        )
    except MemoryImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MediaStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media storage temporarily unavailable",
        ) from exc

    try:
        used = _assert_photo_slot_available(
            db,
            memory_id=memory.id,
            uploader_role="host",
            uploader_user_id=None,
            limit=HOST_MEMORY_PHOTO_LIMIT,
        )
        make_cover = is_cover or used == 0
        _create_photo_row(
            db,
            memory=memory,
            event=event,
            user=user,
            role="host",
            processed=processed,
            caption=caption,
            make_cover=make_cover,
        )
        write_audit_log(
            db,
            action="memories.host.photo_upload",
            actor_user_id=user.id,
            resource_type="event_memory",
            resource_id=str(memory.id),
            details={
                "original_bytes": processed.original_bytes,
                "stored_bytes": processed.size_bytes,
            },
        )
        db.commit()
    except HTTPException:
        db.rollback()
        _cleanup_processed_uploads(processed)
        raise
    except Exception:
        db.rollback()
        _cleanup_processed_uploads(processed)
        raise
    db.refresh(memory)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=True)


async def upload_fan_photo(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    file: UploadFile,
    caption: str | None = None,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if not user_holds_event_memory_ticket(db, event_id=event.id, user_id=user.id):
        raise HTTPException(
            status_code=403,
            detail="A valid ticket for this event is required to upload memories",
        )
    if not event_memory_upload_window_open(event):
        raise HTTPException(
            status_code=400,
            detail="Fan memories open once the event has started",
        )

    memory = ensure_event_memory(db, event)
    if memory.status == "hidden":
        raise HTTPException(status_code=403, detail="This memory was hidden by moderation")

    _soft_check_photo_limit(
        db,
        memory_id=memory.id,
        uploader_role="fan",
        uploader_user_id=user.id,
        limit=FAN_MEMORY_PHOTO_LIMIT,
    )

    raw = await _read_upload(file)
    try:
        processed = process_memory_image(
            data=raw,
            declared_content_type=file.content_type,
            event_id=event.id,
        )
    except MemoryImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MediaStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media storage temporarily unavailable",
        ) from exc

    try:
        _assert_photo_slot_available(
            db,
            memory_id=memory.id,
            uploader_role="fan",
            uploader_user_id=user.id,
            limit=FAN_MEMORY_PHOTO_LIMIT,
        )
        _create_photo_row(
            db,
            memory=memory,
            event=event,
            user=user,
            role="fan",
            processed=processed,
            caption=caption,
            make_cover=False,
        )
        write_audit_log(
            db,
            action="memories.fan.photo_upload",
            actor_user_id=user.id,
            resource_type="event_memory",
            resource_id=str(memory.id),
            details={
                "original_bytes": processed.original_bytes,
                "stored_bytes": processed.size_bytes,
            },
        )
        db.commit()
    except HTTPException:
        db.rollback()
        _cleanup_processed_uploads(processed)
        raise
    except Exception:
        db.rollback()
        _cleanup_processed_uploads(processed)
        raise
    db.refresh(memory)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=False)


def patch_photo(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    media_id: UUID,
    payload: MemoryPhotoPatch,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    memory = get_memory_by_event_id(db, event.id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    media = db.get(EventMemoryMedia, media_id)
    if media is None or media.memory_id != memory.id:
        raise HTTPException(status_code=404, detail="Photo not found")
    if media.status == "removed":
        raise HTTPException(status_code=400, detail="Photo was removed")

    is_host = False
    try:
        _require_host_owns_event(db, user, event)
        is_host = True
    except HTTPException:
        is_host = False

    is_owner = media.uploader_user_id == user.id
    if media.uploader_role == "host":
        if not is_host:
            raise HTTPException(status_code=403, detail="Not allowed")
        if payload.is_cover is not None and payload.is_cover:
            _clear_other_covers(db, memory_id=memory.id, keep_id=media.id)
            media.is_cover = True
        elif payload.is_cover is False:
            media.is_cover = False
        if payload.sort_order is not None:
            media.sort_order = payload.sort_order
        if payload.caption is not None:
            media.caption = payload.caption.strip() or None
    elif media.uploader_role == "fan":
        if not is_owner:
            raise HTTPException(status_code=403, detail="Not allowed")
        # Fans may only edit their own caption; hosts cannot rewrite fan captions.
        if payload.caption is not None:
            media.caption = payload.caption.strip() or None
        if payload.is_cover is not None or payload.sort_order is not None:
            if not is_host:
                raise HTTPException(
                    status_code=403,
                    detail="Only hosts can reorder or set cover",
                )
            # Host still cannot set fan photo as cover? Plan says host set cover —
            # allow host cover from any active photo including fan.
            if is_host and payload.is_cover:
                _clear_other_covers(db, memory_id=memory.id, keep_id=media.id)
                media.is_cover = True
            if is_host and payload.sort_order is not None:
                media.sort_order = payload.sort_order
            if not is_owner and payload.caption is not None:
                raise HTTPException(
                    status_code=403,
                    detail="Hosts cannot edit attendee captions",
                )
    else:
        raise HTTPException(status_code=400, detail="Unknown uploader role")

    write_audit_log(
        db,
        action="memories.photo.patch",
        actor_user_id=user.id,
        resource_type="event_memory_media",
        resource_id=str(media.id),
    )
    db.commit()
    db.refresh(memory)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=is_host)


def delete_own_or_host_photo(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    media_id: UUID,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    memory = get_memory_by_event_id(db, event.id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    media = db.get(EventMemoryMedia, media_id)
    if media is None or media.memory_id != memory.id:
        raise HTTPException(status_code=404, detail="Photo not found")

    is_host = False
    try:
        _require_host_owns_event(db, user, event)
        is_host = True
    except HTTPException:
        pass

    remove_objects = False
    storage_key = media.storage_key
    thumb_key = storage_key_from_url(media.thumbnail_url)
    if media.uploader_role == "host":
        if not is_host:
            raise HTTPException(status_code=403, detail="Not allowed")
        remove_objects = True
        db.delete(media)
    elif media.uploader_user_id == user.id:
        # Fan permanent removal — drop storage objects; keep soft status for audit.
        media.status = "removed"
        remove_objects = True
    elif is_host:
        # Host soft-hides attendee photos rather than hard-deleting objects.
        media.status = "hidden"
        media.hidden_by = "host"
        media.hidden_at = datetime.now(UTC)
    else:
        raise HTTPException(status_code=403, detail="Not allowed")

    write_audit_log(
        db,
        action="memories.photo.delete",
        actor_user_id=user.id,
        resource_type="event_memory_media",
        resource_id=str(media_id),
    )
    db.commit()
    if remove_objects:
        delete_media_keys(storage_key, thumb_key)
    if memory.id:
        db.refresh(memory)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=is_host)


def host_moderate_photo(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    media_id: UUID,
    action: str,
    note: str | None = None,
) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)
    memory = get_memory_by_event_id(db, event.id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    media = db.get(EventMemoryMedia, media_id)
    if media is None or media.memory_id != memory.id:
        raise HTTPException(status_code=404, detail="Photo not found")
    if media.uploader_role != "fan":
        raise HTTPException(status_code=400, detail="Only attendee photos can be moderated here")

    now = datetime.now(UTC)
    if action == "hide":
        media.status = "hidden"
        media.hidden_by = "host"
        media.hidden_at = now
        media.moderation_note = note
    elif action == "restore":
        media.status = "active"
        media.hidden_by = None
        media.hidden_at = None
        media.moderation_note = note
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")

    write_audit_log(
        db,
        action=f"memories.host.photo_{action}",
        actor_user_id=user.id,
        resource_type="event_memory_media",
        resource_id=str(media.id),
        details={"note": note},
    )
    db.commit()
    db.refresh(memory)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=True)


def admin_moderate_photo(
    db: Session,
    *,
    user: User,
    media_id: UUID,
    action: str,
    note: str | None = None,
) -> dict:
    if not user_has_permission(user, "memories.moderate") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")

    media = db.get(EventMemoryMedia, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    memory = db.get(EventMemory, media.memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    event = db.get(Event, memory.event_id)

    now = datetime.now(UTC)
    remove_objects = False
    if action == "hide":
        # Moderation hide — keep storage objects for possible restore.
        media.status = "hidden"
        media.hidden_by = "admin"
        media.hidden_at = now
    elif action == "restore":
        media.status = "active"
        media.hidden_by = None
        media.hidden_at = None
    elif action == "remove":
        media.status = "removed"
        media.hidden_by = "admin"
        media.hidden_at = now
        remove_objects = True
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")
    media.moderation_note = note

    write_audit_log(
        db,
        action=f"memories.admin.photo_{action}",
        actor_user_id=user.id,
        resource_type="event_memory_media",
        resource_id=str(media.id),
        details={"note": note},
    )
    storage_key = media.storage_key
    thumb_key = storage_key_from_url(media.thumbnail_url)
    db.commit()
    if remove_objects:
        delete_media_keys(storage_key, thumb_key)
    db.refresh(memory)
    if event is not None:
        invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=True)


def add_memory_media_url(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    payload: MemoryMediaCreate,
) -> dict:
    """Legacy URL-based host add — counts toward host limit."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    _require_host_owns_event(db, user, event)

    if event.status not in {"published", "paused", "completed"}:
        raise HTTPException(
            status_code=400,
            detail="Only published, paused, or completed events can have memory media",
        )

    memory = ensure_event_memory(db, event)
    if memory.status == "hidden":
        raise HTTPException(status_code=403, detail="This memory was hidden by moderation")

    _soft_check_photo_limit(
        db,
        memory_id=memory.id,
        uploader_role="host",
        uploader_user_id=None,
        limit=HOST_MEMORY_PHOTO_LIMIT,
    )

    try:
        stored = get_public_media_storage().store_remote_url(
            url=payload.url, folder=memory_public_folder(event.id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sort_order = payload.sort_order
    if sort_order is None:
        sort_order = _next_sort_order(db, memory.id)

    caption = payload.caption or payload.label
    try:
        used = _assert_photo_slot_available(
            db,
            memory_id=memory.id,
            uploader_role="host",
            uploader_user_id=None,
            limit=HOST_MEMORY_PHOTO_LIMIT,
        )
        media = EventMemoryMedia(
            memory_id=memory.id,
            media_type=payload.media_type.strip().lower(),
            url=stored.url,
            storage_key=stored.key,
            thumbnail_url=stored.url,
            label=payload.label,
            caption=(caption or "").strip() or None,
            sort_order=sort_order,
            uploader_user_id=user.id,
            uploader_role="host",
            is_cover=used == 0,
            status="active",
        )
        if used == 0:
            _clear_other_covers(db, memory_id=memory.id, keep_id=None)
        db.add(media)
        write_audit_log(
            db,
            action="memories.host.media_add",
            actor_user_id=user.id,
            resource_type="event_memory",
            resource_id=str(memory.id),
            details={"media_id": str(media.id)},
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    db.refresh(memory)
    invalidate_memory_caches(event)
    return serialize_memory(db, memory, include_private=True)
