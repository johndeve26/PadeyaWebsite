"""Canonical admin user management API — `/api/v1/admin/users*`."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.auth.service import build_user_public
from app.core.database import get_db
from app.users import account_status_service, admin_actions_service
from app.users import lifecycle_service
from app.users import restrictions_service
from app.users.admin_activity_detail_service import (
    ACTIVITY_KINDS,
    list_user_activity_detail,
)
from app.users.admin_detail_service import get_admin_user_detail
from app.users.admin_list_service import list_admin_users
from app.users.admin_user_audit import (
    client_request_meta,
    record_admin_user_activity_detail_view,
    record_admin_user_view,
)
from app.users.models import User
from app.users.schemas import (
    AdminAccountStatusChangeBody,
    AdminPasswordResetForcedResponse,
    AdminSensitiveReasonBody,
    AdminSessionsRevokeResponse,
    AdminUserActivityDetailListPublic,
    AdminUserDetailPublic,
    AdminUserFlagCreate,
    AdminUserFlagPatchBody,
    AdminUserFlagPublic,
    AdminUserListPublic,
    AdminUserNoteCreate,
    AdminUserNotePublic,
    AdminUserRestrictionPatchBody,
    AdminUserRestrictionPublic,
    AdminUserRestrictionRevokeBody,
    AdminUserRestrictionsApplyBody,
    AdminUserRestrictionsListPublic,
    UserPublic,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

_VIEW = require_permission("admin.users.view")
_VIEW_ACTIVITY = require_permission("admin.users.view_activity")
_VIEW_AUDIT = require_permission("admin.users.view_audit")
_ADD_NOTE = require_permission("admin.users.add_note")
_FLAG = require_permission("admin.users.flag")
_VIEW_RESTRICTIONS = require_permission(
    "admin.users.view_restrictions", "admin.users.view", "admin.users.restrict"
)
_ADD_RESTRICTION = require_permission(
    "admin.users.add_restriction", "admin.users.restrict"
)
_REVOKE_RESTRICTION = require_permission(
    "admin.users.revoke_restriction", "admin.users.restrict"
)
_RESTRICT_OR_SUSPEND = require_permission(
    "admin.users.restrict", "admin.users.suspend", "admin.users.ban"
)
_FORCE_LOGOUT = require_permission("admin.users.force_logout")
_FORCE_PASSWORD_RESET = require_permission("admin.users.force_password_reset")
_FORCE_DELETE = require_permission("admin.users.force_delete")


@router.get("", response_model=AdminUserListPublic)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(_VIEW)],
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    role: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=40, ge=1, le=100),
) -> AdminUserListPublic:
    return AdminUserListPublic.model_validate(
        list_admin_users(
            db, q=q, status=status_filter, role=role, page=page, limit=limit
        )
    )


@router.get("/{user_id}", response_model=AdminUserDetailPublic)
def get_user(
    user_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW)],
) -> AdminUserDetailPublic:
    ip, ua = client_request_meta(request)
    detail = get_admin_user_detail(db, user_id, viewer=admin)
    record_admin_user_view(
        db,
        admin_user_id=admin.id,
        target_user_id=user_id,
        # Admin detail always returns the real email (directory parity).
        showed_private_contact=True,
        ip_address=ip,
        user_agent=ua,
    )
    return AdminUserDetailPublic.model_validate(detail)


@router.get("/{user_id}/activity")
def get_user_activity(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW_ACTIVITY)],
) -> dict:
    return get_admin_user_detail(db, user_id, viewer=admin)["activity"]


@router.get(
    "/{user_id}/activity/{kind}",
    response_model=AdminUserActivityDetailListPublic,
)
def get_user_activity_detail(
    user_id: UUID,
    kind: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW_ACTIVITY)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> AdminUserActivityDetailListPublic:
    """Paginated Activity drill-down (tickets, orders, merch, …)."""
    if kind not in ACTIVITY_KINDS:
        raise HTTPException(status_code=404, detail="Unknown activity kind")
    ip, ua = client_request_meta(request)
    payload = list_user_activity_detail(
        db,
        user_id=user_id,
        viewer=admin,
        kind=kind,
        page=page,
        limit=limit,
    )
    record_admin_user_activity_detail_view(
        db,
        admin_user_id=admin.id,
        target_user_id=user_id,
        activity_kind=kind,
        page=page,
        finance_fields_included=bool(payload.get("finance_fields_included")),
        ip_address=ip,
        user_agent=ua,
    )
    return AdminUserActivityDetailListPublic.model_validate(payload)


@router.get("/{user_id}/audit")
def get_user_audit(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW_AUDIT)],
) -> list:
    return get_admin_user_detail(db, user_id, viewer=admin)["recent_audit"]


@router.post("/{user_id}/flags", response_model=AdminUserFlagPublic)
def create_flag(
    user_id: UUID,
    payload: AdminUserFlagCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FLAG)],
) -> AdminUserFlagPublic:
    ip, ua = client_request_meta(request)
    return AdminUserFlagPublic.model_validate(
        admin_actions_service.add_flag(
            db,
            admin=admin,
            user_id=user_id,
            flag_type=payload.flag_type,
            severity=payload.severity,
            reason=payload.reason,
            internal_note=payload.internal_note,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.patch("/{user_id}/flags/{flag_id}", response_model=AdminUserFlagPublic)
def patch_flag(
    user_id: UUID,
    flag_id: UUID,
    payload: AdminUserFlagPatchBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FLAG)],
) -> AdminUserFlagPublic:
    ip, ua = client_request_meta(request)
    return AdminUserFlagPublic.model_validate(
        admin_actions_service.patch_flag(
            db,
            admin=admin,
            user_id=user_id,
            flag_id=flag_id,
            status=payload.status,
            reason=payload.reason,
            resolution_note=payload.resolution_note,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post("/{user_id}/notes", response_model=AdminUserNotePublic)
def create_note(
    user_id: UUID,
    payload: AdminUserNoteCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_ADD_NOTE)],
) -> AdminUserNotePublic:
    ip, ua = client_request_meta(request)
    return AdminUserNotePublic.model_validate(
        admin_actions_service.add_note(
            db,
            admin=admin,
            user_id=user_id,
            body=payload.body,
            note_type=payload.note_type,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.get("/{user_id}/notes", response_model=list[AdminUserNotePublic])
def list_notes(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW)],
) -> list[AdminUserNotePublic]:
    rows = admin_actions_service.list_notes(db, admin=admin, user_id=user_id)
    return [AdminUserNotePublic.model_validate(r) for r in rows]


@router.post("/{user_id}/status", response_model=UserPublic)
def change_status(
    user_id: UUID,
    payload: AdminAccountStatusChangeBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_RESTRICT_OR_SUSPEND)],
) -> UserPublic:
    ip, ua = client_request_meta(request)
    target = account_status_service.change_account_status(
        db,
        admin=admin,
        user_id=user_id,
        new_status=payload.status,
        reason=payload.reason,
        restrictions=payload.restrictions,
        reason_category=payload.reason_category,
        ends_at=payload.ends_at,
        ip_address=ip,
        user_agent=ua,
    )
    return UserPublic.model_validate(build_user_public(target, db=db))


@router.get("/{user_id}/restrictions", response_model=AdminUserRestrictionsListPublic)
def list_restrictions(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW_RESTRICTIONS)],
) -> AdminUserRestrictionsListPublic:
    return AdminUserRestrictionsListPublic.model_validate(
        restrictions_service.list_user_restrictions(db, admin=admin, user_id=user_id)
    )


@router.post("/{user_id}/restrictions", response_model=AdminUserRestrictionsListPublic)
def add_restrictions(
    user_id: UUID,
    payload: AdminUserRestrictionsApplyBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_ADD_RESTRICTION)],
) -> AdminUserRestrictionsListPublic:
    """Primary moderation path: selective restriction keys → status=restricted.

    Full suspension is available only via ``preset=full_suspension`` (or
    ``force_full_suspension``) — not the default.
    """
    ip, ua = client_request_meta(request)
    return AdminUserRestrictionsListPublic.model_validate(
        restrictions_service.apply_restrictions(
            db,
            admin=admin,
            user_id=user_id,
            restriction_keys=payload.restriction_keys,
            reason=payload.reason,
            internal_note=payload.internal_note,
            ends_at=payload.ends_at,
            preset=payload.preset,
            force_full_suspension=payload.force_full_suspension,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.patch(
    "/{user_id}/restrictions/{restriction_id}",
    response_model=AdminUserRestrictionPublic,
)
def patch_restriction(
    user_id: UUID,
    restriction_id: UUID,
    payload: AdminUserRestrictionPatchBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_ADD_RESTRICTION)],
) -> AdminUserRestrictionPublic:
    ip, ua = client_request_meta(request)
    return AdminUserRestrictionPublic.model_validate(
        restrictions_service.extend_restriction(
            db,
            admin=admin,
            user_id=user_id,
            restriction_id=restriction_id,
            reason=payload.reason,
            ends_at=payload.ends_at,
            internal_note=payload.internal_note,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post(
    "/{user_id}/restrictions/{restriction_id}/revoke",
    response_model=AdminUserRestrictionPublic,
)
def revoke_restriction(
    user_id: UUID,
    restriction_id: UUID,
    payload: AdminUserRestrictionRevokeBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_REVOKE_RESTRICTION)],
) -> AdminUserRestrictionPublic:
    ip, ua = client_request_meta(request)
    return AdminUserRestrictionPublic.model_validate(
        restrictions_service.revoke_restriction(
            db,
            admin=admin,
            user_id=user_id,
            restriction_id=restriction_id,
            reason=payload.reason,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post("/{user_id}/force-delete", response_model=UserPublic)
def force_delete_user(
    user_id: UUID,
    payload: AdminSensitiveReasonBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FORCE_DELETE)],
) -> UserPublic:
    """Soft EOL for suspended accounts (test cleanup, etc.). Row retained."""
    ip, ua = client_request_meta(request)
    target = lifecycle_service.force_delete_user(
        db,
        admin=admin,
        user_id=user_id,
        reason=payload.reason,
        ip_address=ip,
        user_agent=ua,
    )
    return UserPublic.model_validate(build_user_public(target, db=db))


@router.post(
    "/{user_id}/force-password-reset",
    response_model=AdminPasswordResetForcedResponse,
)
def force_password_reset(
    user_id: UUID,
    payload: AdminSensitiveReasonBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FORCE_PASSWORD_RESET)],
) -> AdminPasswordResetForcedResponse:
    ip, ua = client_request_meta(request)
    return AdminPasswordResetForcedResponse.model_validate(
        admin_actions_service.force_password_reset_email(
            db,
            admin=admin,
            user_id=user_id,
            reason=payload.reason,
            require_reason=True,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post(
    "/{user_id}/force-logout",
    response_model=AdminSessionsRevokeResponse,
)
def force_logout(
    user_id: UUID,
    payload: AdminSensitiveReasonBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FORCE_LOGOUT)],
) -> AdminSessionsRevokeResponse:
    ip, ua = client_request_meta(request)
    return AdminSessionsRevokeResponse.model_validate(
        admin_actions_service.revoke_all_sessions(
            db,
            admin=admin,
            user_id=user_id,
            reason=payload.reason,
            require_reason=True,
            ip_address=ip,
            user_agent=ua,
        )
    )
