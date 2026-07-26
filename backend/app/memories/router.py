"""Event Memories API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.memories.albums import list_public_albums
from app.memories.photos import (
    add_memory_media_url,
    admin_moderate_photo,
    host_moderate_photo,
    patch_photo,
    upload_fan_photo,
    upload_host_photo,
)
from app.memories.schemas import (
    AdminMemoryPhoto,
    EventMemoryPublic,
    EventMemoryUpdate,
    MemoryAlbumsResponse,
    MemoryEligibility,
    MemoryMediaCreate,
    MemoryModerateRequest,
    MemoryPhotoModerateRequest,
    MemoryPhotoPatch,
)
from app.memories.service import (
    delete_memory_media,
    get_eligibility_for_slug,
    get_host_memory,
    get_public_memory,
    get_public_memory_by_slug,
    list_admin_memories,
    list_admin_photos,
    moderate_memory,
    update_host_memory,
)
from app.users.models import User

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("/health")
def memories_health() -> dict[str, str]:
    return {"module": "memories", "status": "ok"}


@router.get("/albums", response_model=MemoryAlbumsResponse)
def public_albums(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=48)] = 24,
    cursor: str | None = None,
    city: str | None = None,
) -> MemoryAlbumsResponse:
    return MemoryAlbumsResponse.model_validate(
        list_public_albums(db, limit=limit, cursor=cursor, city=city)
    )


@router.get("/events/{event_slug}", response_model=EventMemoryPublic)
def public_memory_by_event_slug(
    event_slug: str,
    db: Annotated[Session, Depends(get_db)],
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        get_public_memory_by_slug(db, event_slug=event_slug)
    )


@router.get("/events/{event_slug}/eligibility", response_model=MemoryEligibility)
def memory_eligibility(
    event_slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> MemoryEligibility:
    return MemoryEligibility.model_validate(
        get_eligibility_for_slug(db, user=user, event_slug=event_slug)
    )


@router.get("/public/{username}/{event_slug}", response_model=EventMemoryPublic)
def public_memory(
    username: str,
    event_slug: str,
    db: Annotated[Session, Depends(get_db)],
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        get_public_memory(db, username=username, event_slug=event_slug)
    )


@router.get("/host/events/{event_id}", response_model=EventMemoryPublic)
def host_get_memory(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        get_host_memory(db, user=user, event_id=event_id)
    )


@router.patch("/host/events/{event_id}", response_model=EventMemoryPublic)
def host_update_memory(
    event_id: UUID,
    payload: EventMemoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        update_host_memory(db, user=user, event_id=event_id, payload=payload)
    )


@router.post("/host/events/{event_id}/photos", response_model=EventMemoryPublic)
async def host_upload_photo(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form()] = None,
    is_cover: Annotated[bool, Form()] = False,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        await upload_host_photo(
            db,
            user=user,
            event_id=event_id,
            file=file,
            caption=caption,
            is_cover=is_cover,
        )
    )


@router.post("/host/events/{event_id}/media", response_model=EventMemoryPublic)
def host_add_media(
    event_id: UUID,
    payload: MemoryMediaCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        add_memory_media_url(db, user=user, event_id=event_id, payload=payload)
    )


@router.patch(
    "/host/events/{event_id}/photos/{media_id}",
    response_model=EventMemoryPublic,
)
def host_patch_photo(
    event_id: UUID,
    media_id: UUID,
    payload: MemoryPhotoPatch,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        patch_photo(
            db, user=user, event_id=event_id, media_id=media_id, payload=payload
        )
    )


@router.post(
    "/host/events/{event_id}/photos/{media_id}/moderate",
    response_model=EventMemoryPublic,
)
def host_photo_moderate(
    event_id: UUID,
    media_id: UUID,
    payload: MemoryPhotoModerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        host_moderate_photo(
            db,
            user=user,
            event_id=event_id,
            media_id=media_id,
            action=payload.action,
            note=payload.note,
        )
    )


@router.delete(
    "/host/events/{event_id}/media/{media_id}",
    response_model=EventMemoryPublic,
)
def host_delete_media(
    event_id: UUID,
    media_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        delete_memory_media(db, user=user, event_id=event_id, media_id=media_id)
    )


@router.post("/events/{event_id}/photos", response_model=EventMemoryPublic)
async def fan_upload_photo(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form()] = None,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        await upload_fan_photo(
            db, user=user, event_id=event_id, file=file, caption=caption
        )
    )


@router.patch(
    "/events/{event_id}/photos/{media_id}",
    response_model=EventMemoryPublic,
)
def fan_patch_photo(
    event_id: UUID,
    media_id: UUID,
    payload: MemoryPhotoPatch,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        patch_photo(
            db, user=user, event_id=event_id, media_id=media_id, payload=payload
        )
    )


@router.delete(
    "/events/{event_id}/photos/{media_id}",
    response_model=EventMemoryPublic,
)
def fan_delete_photo(
    event_id: UUID,
    media_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        delete_memory_media(db, user=user, event_id=event_id, media_id=media_id)
    )


@router.get("/admin", response_model=list[EventMemoryPublic])
def admin_list(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("memories.moderate", "admin.full_access"))
    ],
) -> list[EventMemoryPublic]:
    return [EventMemoryPublic.model_validate(r) for r in list_admin_memories(db, user)]


@router.get("/admin/photos", response_model=list[AdminMemoryPhoto])
def admin_list_photos(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("memories.moderate", "admin.full_access"))
    ],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[AdminMemoryPhoto]:
    return [
        AdminMemoryPhoto.model_validate(r)
        for r in list_admin_photos(db, user, limit=limit)
    ]


@router.post("/admin/{memory_id}/moderate", response_model=EventMemoryPublic)
def admin_moderate(
    memory_id: UUID,
    payload: MemoryModerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("memories.moderate", "admin.full_access"))
    ],
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        moderate_memory(db, user=user, memory_id=memory_id, payload=payload)
    )


@router.post("/admin/photos/{media_id}/moderate", response_model=EventMemoryPublic)
def admin_photo_moderate(
    media_id: UUID,
    payload: MemoryPhotoModerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("memories.moderate", "admin.full_access"))
    ],
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        admin_moderate_photo(
            db, user=user, media_id=media_id, action=payload.action, note=payload.note
        )
    )
