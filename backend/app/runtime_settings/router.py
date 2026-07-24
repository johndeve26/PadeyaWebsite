"""Admin Runtime Settings routes under ``/admin/settings/runtime``."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.runtime_settings.registry import CATEGORIES, RESERVED_PATH_NAMES
from app.runtime_settings.schemas import (
    RuntimeSettingUpsertRequest,
    RuntimeSettingsAuditResponse,
    RuntimeSettingsCategoryResponse,
    RuntimeSettingsListResponse,
    RuntimeSettingsStatusResponse,
    RuntimeSettingsTestResponse,
)
from app.runtime_settings.service import runtime_settings_service
from app.runtime_settings.test_actions import test_category
from app.users.models import User
from app.users.service import user_has_permission

router = APIRouter(prefix="/admin/settings", tags=["admin-runtime-settings"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )
    ua = request.headers.get("user-agent")
    return ip, ua


def _require_secret_perm_if_needed(user: User, *, is_secret: bool) -> None:
    if is_secret and not user_has_permission(user, "admin.settings.edit_secrets"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin.settings.edit_secrets required",
        )


@router.get(
    "/runtime",
    response_model=RuntimeSettingsListResponse,
)
def list_runtime_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.settings.view"))],
) -> dict:
    return runtime_settings_service.list_all(db)


@router.get(
    "/runtime/status",
    response_model=RuntimeSettingsStatusResponse,
)
def runtime_system_status(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[
        User,
        Depends(
            require_permission(
                "admin.settings.view_system_status",
                "admin.settings.view",
            )
        ),
    ],
) -> dict:
    ip, ua = _client_meta(request)
    return runtime_settings_service.system_status(
        db,
        actor_user_id=admin.id,
        ip_address=ip,
        user_agent=ua,
        record_view_audit=True,
    )


@router.get(
    "/runtime/audit",
    response_model=RuntimeSettingsAuditResponse,
)
def runtime_settings_audit(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.settings.view_audit"))],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return runtime_settings_service.list_audit(db, limit=limit, offset=offset)


@router.get(
    "/runtime/{category}",
    response_model=RuntimeSettingsCategoryResponse,
)
def list_runtime_settings_category(
    category: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.settings.view"))],
) -> dict:
    if category in RESERVED_PATH_NAMES and category not in CATEGORIES:
        raise HTTPException(status_code=404, detail="Not found")
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
    return runtime_settings_service.list_category(db, category)


@router.put("/runtime/{category}/{key}")
def upsert_runtime_setting(
    category: str,
    key: str,
    payload: RuntimeSettingUpsertRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[
        User, Depends(require_permission("admin.settings.edit_runtime"))
    ],
) -> dict:
    from app.runtime_settings.registry import get_definition

    defn = get_definition(key)
    if defn is not None and defn.is_secret:
        _require_secret_perm_if_needed(admin, is_secret=True)

    ip, ua = _client_meta(request)
    try:
        return runtime_settings_service.upsert(
            db,
            category=category,
            key=key,
            value=payload.resolved_value(),
            clear_secret=bool(payload.clear),
            actor_user_id=admin.id,
            reason=payload.reason,
            ip_address=ip,
            user_agent=ua,
            commit=True,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/runtime/{category}/{key}/override")
def clear_runtime_setting_override(
    category: str,
    key: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[
        User, Depends(require_permission("admin.settings.clear_overrides"))
    ],
) -> dict:
    from app.runtime_settings.registry import get_definition

    defn = get_definition(key)
    if defn is not None and defn.is_secret:
        _require_secret_perm_if_needed(admin, is_secret=True)

    ip, ua = _client_meta(request)
    try:
        return runtime_settings_service.clear_override(
            db,
            category=category,
            key=key,
            actor_user_id=admin.id,
            ip_address=ip,
            user_agent=ua,
            commit=True,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/runtime/{category}/test",
    response_model=RuntimeSettingsTestResponse,
)
def test_runtime_settings_category(
    category: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[
        User, Depends(require_permission("admin.settings.test_integrations"))
    ],
) -> dict:
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
    ip, ua = _client_meta(request)
    result = test_category(
        db,
        category=category,
        actor_user_id=admin.id,
        actor_email=admin.email,
        ip_address=ip,
        user_agent=ua,
    )
    return result
