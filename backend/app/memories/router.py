"""Event Memories API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.core.database import get_db
from app.memories.schemas import (
    EventMemoryPublic,
    EventMemoryUpdate,
    MemoryMediaCreate,
    MemoryModerateRequest,
)
from app.memories.service import (
    add_memory_media,
    delete_memory_media,
    get_host_memory,
    get_public_memory,
    list_admin_memories,
    moderate_memory,
    update_host_memory,
)
from app.users.models import User

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("/health")
def memories_health() -> dict[str, str]:
    return {"module": "memories", "status": "ok"}


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


@router.post("/host/events/{event_id}/media", response_model=EventMemoryPublic)
def host_add_media(
    event_id: UUID,
    payload: MemoryMediaCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventMemoryPublic:
    return EventMemoryPublic.model_validate(
        add_memory_media(db, user=user, event_id=event_id, payload=payload)
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
        delete_memory_media(
            db, user=user, event_id=event_id, media_id=media_id
        )
    )


@router.get("/admin", response_model=list[EventMemoryPublic])
def admin_list(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("memories.moderate", "admin.full_access"))
    ],
) -> list[EventMemoryPublic]:
    return [EventMemoryPublic.model_validate(r) for r in list_admin_memories(db, user)]


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
