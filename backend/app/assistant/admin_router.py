"""Admin assistant knowledge sync endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.assistant.knowledge.sync import knowledge_status, sync_knowledge
from app.assistant.schemas import KnowledgeStatus, KnowledgeSyncReport
from app.auth.dependencies import require_permission
from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/admin/assistant", tags=["admin-assistant"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/knowledge/sync", response_model=KnowledgeSyncReport)
def admin_knowledge_sync(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[
        User,
        Depends(
            require_permission("admin.ai.manage_settings", "admin.full_access")
        ),
    ],
) -> KnowledgeSyncReport:
    settings = get_settings()
    if not bool(getattr(settings, "assistant_knowledge_sync_enabled", False)):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Assistant knowledge sync is not enabled",
        )

    report = sync_knowledge(db)
    ip, ua = _client_meta(request)
    write_audit_log(
        db,
        action="assistant.knowledge_sync",
        actor_user_id=actor.id,
        resource_type="assistant_knowledge",
        resource_id="sync",
        details={
            "urls_seen": report.urls_seen,
            "documents_created": report.documents_created,
            "documents_updated": report.documents_updated,
            "documents_archived": report.documents_archived,
            "documents_failed": report.documents_failed,
            "chunks_upserted": report.chunks_upserted,
        },
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return report


@router.get("/knowledge/status", response_model=KnowledgeStatus)
def admin_knowledge_status(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[
        User,
        Depends(
            require_permission("admin.ai.manage_settings", "admin.full_access")
        ),
    ],
) -> KnowledgeStatus:
    return KnowledgeStatus(**knowledge_status(db))
