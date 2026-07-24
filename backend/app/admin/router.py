"""Admin platform routes — audit logs and user impersonation."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.admin.audit_service import list_audit_logs
from app.admin.impersonation_service import (
    can_start_impersonation,
    end_impersonation,
    list_impersonation_history,
    start_impersonation,
)
from app.admin.schemas import (
    AuditLogPublic,
    ImpersonationEndResponse,
    ImpersonationHistoryItem,
    ImpersonationStartRequest,
    ImpersonationStartResponse,
)
from app.auth.dependencies import (
    CurrentUser,
    require_not_impersonating,
    require_permission,
)
from app.auth.impersonation_context import get_impersonation_context
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_impersonation_capability(
    admin: Annotated[User, Depends(require_not_impersonating)],
) -> User:
    """Require platform impersonation eligibility (permission + operator role)."""
    if not can_start_impersonation(admin):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permission",
        )
    return admin


def _require_impersonation_start(
    admin: Annotated[User, Depends(require_not_impersonating)],
) -> User:
    """Block nested impersonation first, then require platform impersonate eligibility."""
    return _require_impersonation_capability(admin)


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("/health")
async def admin_module_health() -> dict[str, str]:
    return {"module": "admin", "status": "ok"}


@router.get("/audit-logs", response_model=list[AuditLogPublic])
def get_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLogPublic]:
    rows = list_audit_logs(
        db,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
    )
    return [AuditLogPublic.model_validate(r) for r in rows]


@router.post(
    "/users/{user_id}/impersonation/start",
    response_model=ImpersonationStartResponse,
)
def impersonation_start(
    user_id: UUID,
    payload: ImpersonationStartRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_require_impersonation_start)],
) -> ImpersonationStartResponse:
    """Start an audited impersonation session as a specific user.

    Issues a short-lived access token only. Does not expose passwords, does not
    reuse or revoke the target user's refresh tokens, and is not a real login.
    """
    ip, ua = _client_meta(request)
    result = start_impersonation(
        db,
        admin=admin,
        target_user_id=user_id,
        reason=payload.reason,
        support_ticket_id=payload.support_ticket_id,
        duration_minutes=payload.duration_minutes,
        ip_address=ip,
        user_agent=ua,
    )
    return ImpersonationStartResponse.model_validate(result)


@router.get(
    "/users/{user_id}/impersonation/history",
    response_model=list[ImpersonationHistoryItem],
)
def impersonation_history(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(_require_impersonation_capability)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ImpersonationHistoryItem]:
    """List impersonation sessions for a user (newest first)."""
    rows = list_impersonation_history(
        db,
        target_user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return [ImpersonationHistoryItem.model_validate(r) for r in rows]


@router.post("/impersonation/end", response_model=ImpersonationEndResponse)
def impersonation_end(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ImpersonationEndResponse:
    """End the current impersonation session (client restores admin tokens)."""
    ctx = get_impersonation_context()
    if ctx is None:
        raise HTTPException(
            status_code=400,
            detail="Not currently impersonating",
        )
    ip, ua = _client_meta(request)
    result = end_impersonation(
        db,
        ctx=ctx,
        target=user,
        ip_address=ip,
        user_agent=ua,
    )
    return ImpersonationEndResponse.model_validate(result)
