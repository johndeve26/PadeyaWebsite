"""Users API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission, require_role
from app.auth.service import build_user_public
from app.core.database import get_db
from app.users import admin_actions_service, lifecycle_service
from app.users.admin_detail_service import get_admin_user_detail
from app.users.admin_list_service import list_admin_users
from app.users.admin_user_audit import client_request_meta, record_admin_user_view
from app.users.models import User
from app.users.schemas import (
    AdminAccountStatusChangeBody,
    AdminPasswordResetForcedResponse,
    AdminSessionsRevokeResponse,
    AdminUserDetailPublic,
    AdminUserFlagCloseBody,
    AdminUserFlagCreate,
    AdminUserFlagPublic,
    AdminUserListPublic,
    AdminUserNoteCreate,
    AdminUserNotePublic,
    UserLifecycleReasonBody,
    UserPublic,
)
from app.users.service import get_user_by_email, get_user_by_id
from app.users import account_status_service

router = APIRouter(prefix="/users", tags=["users"])

_VIEW = require_permission("admin.users.view")
_VIEW_ACTIVITY = require_permission("admin.users.view_activity")
_VIEW_AUDIT = require_permission("admin.users.view_audit")
_ADD_NOTE = require_permission("admin.users.add_note")
_FLAG = require_permission("admin.users.flag")
_RESTRICT = require_permission("admin.users.restrict")
_SUSPEND = require_permission("admin.users.suspend")
_RESTRICT_OR_SUSPEND = require_permission(
    "admin.users.restrict", "admin.users.suspend"
)
_FORCE_LOGOUT = require_permission("admin.users.force_logout")
_FORCE_PASSWORD_RESET = require_permission("admin.users.force_password_reset")


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    display_name: str | None = Field(default=None, min_length=2, max_length=200)
    username: str | None = Field(default=None, min_length=3, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=500)
    clear_avatar: bool = False
    gender: str | None = Field(default=None, max_length=32)
    gender_visibility: str | None = Field(default=None, max_length=32)

    @field_validator("gender")
    @classmethod
    def valid_gender(cls, value: object) -> str | None:
        from app.users.gender import parse_gender

        if value is None:
            return None
        return parse_gender(value)

    @field_validator("gender_visibility")
    @classmethod
    def valid_visibility(cls, value: object) -> str | None:
        from app.users.gender import parse_gender_visibility

        if value is None:
            return None
        return parse_gender_visibility(value)


@router.get("/health")
async def users_module_health() -> dict[str, str]:
    return {"module": "users", "status": "ok"}


@router.get("/me", response_model=UserPublic)
def read_me(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> UserPublic:
    return UserPublic.model_validate(build_user_public(user, db=db))


@router.patch("/me", response_model=UserPublic)
def patch_me(
    payload: UserProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> UserPublic:
    data = payload.model_dump(exclude_unset=True)
    clear_avatar = bool(data.pop("clear_avatar", False))
    avatar_url: str | None = None
    if "avatar_url" in data:
        avatar_url = data.get("avatar_url")
        if avatar_url is None:
            clear_avatar = True
    updated = lifecycle_service.update_my_profile(
        db,
        user=user,
        full_name=data.get("full_name"),
        display_name=data.get("display_name"),
        username=data.get("username"),
        avatar_url=None if clear_avatar else avatar_url,
        clear_avatar=clear_avatar,
        gender=data["gender"] if "gender" in data else None,
        gender_set="gender" in data,
        gender_visibility=data.get("gender_visibility"),
        gender_visibility_set="gender_visibility" in data,
    )
    return UserPublic.model_validate(build_user_public(updated, db=db))


class UserAvatarUploadPublic(BaseModel):
    url: str


@router.post("/me/avatar", response_model=UserAvatarUploadPublic)
async def upload_my_avatar(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
) -> UserAvatarUploadPublic:
    """Upload a profile photo for any signed-in user (fan or host).

    Stores the image, applies it to Fan Passport (and Host Legacy when present),
    and returns the public URL. No host onboarding required.
    """
    from app.users.avatar_upload import upload_and_apply_account_avatar

    data = await file.read()
    result = upload_and_apply_account_avatar(
        db,
        user=user,
        data=data,
        filename=file.filename or "avatar.jpg",
        content_type=file.content_type or "application/octet-stream",
    )
    return UserAvatarUploadPublic(url=result["url"])


@router.get("/admin", response_model=AdminUserListPublic)
def admin_list_users_route(
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


@router.get("/admin/lookup", response_model=UserPublic)
def admin_lookup_user_by_email(
    email: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[
        User,
        Depends(
            require_permission(
                "admin.users.view",
                "admin.users.impersonate",
            )
        ),
    ],
) -> UserPublic:
    normalized = (email or "").strip().lower()
    if not normalized or "@" not in normalized:
        raise HTTPException(status_code=400, detail="Valid email is required")
    target = get_user_by_email(db, normalized)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic.model_validate(build_user_public(target))


@router.get("/admin/{user_id}", response_model=AdminUserDetailPublic)
def admin_get_user(
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


@router.get("/admin/{user_id}/activity")
def admin_user_activity(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW_ACTIVITY)],
) -> dict:
    detail = get_admin_user_detail(db, user_id, viewer=admin)
    return detail["activity"]


@router.get("/admin/{user_id}/audit")
def admin_user_audit(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW_AUDIT)],
) -> list[dict]:
    detail = get_admin_user_detail(db, user_id, viewer=admin)
    return detail["recent_audit"]


@router.post("/admin/{user_id}/notes", response_model=AdminUserNotePublic)
def admin_add_note(
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


@router.get("/admin/{user_id}/notes", response_model=list[AdminUserNotePublic])
def admin_list_notes(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW)],
) -> list[AdminUserNotePublic]:
    rows = admin_actions_service.list_notes(db, admin=admin, user_id=user_id)
    return [AdminUserNotePublic.model_validate(r) for r in rows]


@router.post("/admin/{user_id}/flags", response_model=AdminUserFlagPublic)
def admin_add_flag(
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


@router.get("/admin/{user_id}/flags", response_model=list[AdminUserFlagPublic])
def admin_list_flags(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_VIEW)],
) -> list[AdminUserFlagPublic]:
    rows = admin_actions_service.list_flags(db, admin=admin, user_id=user_id)
    return [AdminUserFlagPublic.model_validate(r) for r in rows]


@router.post(
    "/admin/{user_id}/flags/{flag_id}/resolve",
    response_model=AdminUserFlagPublic,
)
def admin_resolve_flag(
    user_id: UUID,
    flag_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FLAG)],
    payload: AdminUserFlagCloseBody | None = None,
) -> AdminUserFlagPublic:
    ip, ua = client_request_meta(request)
    return AdminUserFlagPublic.model_validate(
        admin_actions_service.resolve_flag(
            db,
            admin=admin,
            user_id=user_id,
            flag_id=flag_id,
            resolution_note=payload.resolution_note if payload else None,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post(
    "/admin/{user_id}/flags/{flag_id}/dismiss",
    response_model=AdminUserFlagPublic,
)
def admin_dismiss_flag(
    user_id: UUID,
    flag_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FLAG)],
    payload: AdminUserFlagCloseBody | None = None,
) -> AdminUserFlagPublic:
    ip, ua = client_request_meta(request)
    return AdminUserFlagPublic.model_validate(
        admin_actions_service.dismiss_flag(
            db,
            admin=admin,
            user_id=user_id,
            flag_id=flag_id,
            resolution_note=payload.resolution_note if payload else None,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post(
    "/admin/{user_id}/sessions/revoke-all",
    response_model=AdminSessionsRevokeResponse,
)
def admin_revoke_sessions(
    user_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FORCE_LOGOUT)],
    payload: UserLifecycleReasonBody | None = None,
) -> AdminSessionsRevokeResponse:
    ip, ua = client_request_meta(request)
    return AdminSessionsRevokeResponse.model_validate(
        admin_actions_service.revoke_all_sessions(
            db,
            admin=admin,
            user_id=user_id,
            reason=payload.reason if payload else None,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post(
    "/admin/{user_id}/password-reset",
    response_model=AdminPasswordResetForcedResponse,
)
def admin_force_password_reset(
    user_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_FORCE_PASSWORD_RESET)],
    payload: UserLifecycleReasonBody | None = None,
) -> AdminPasswordResetForcedResponse:
    ip, ua = client_request_meta(request)
    return AdminPasswordResetForcedResponse.model_validate(
        admin_actions_service.force_password_reset_email(
            db,
            admin=admin,
            user_id=user_id,
            reason=payload.reason if payload else None,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.post("/admin/{user_id}/account-status", response_model=UserPublic)
def admin_change_account_status(
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
        ip_address=ip,
        user_agent=ua,
    )
    return UserPublic.model_validate(build_user_public(target))


@router.post("/admin/{user_id}/under-review", response_model=UserPublic)
def admin_mark_under_review(
    user_id: UUID,
    payload: UserLifecycleReasonBody,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_RESTRICT)],
) -> UserPublic:
    reason = (payload.reason or "").strip()
    target = admin_actions_service.mark_under_review(
        db, admin=admin, user_id=user_id, reason=reason
    )
    return UserPublic.model_validate(build_user_public(target))


@router.post("/admin/{user_id}/clear-under-review", response_model=UserPublic)
def admin_clear_under_review(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_RESTRICT)],
    payload: UserLifecycleReasonBody | None = None,
) -> UserPublic:
    target = admin_actions_service.clear_under_review(
        db,
        admin=admin,
        user_id=user_id,
        reason=payload.reason if payload else None,
    )
    return UserPublic.model_validate(build_user_public(target))


@router.post("/admin/{user_id}/suspend", response_model=UserPublic)
def admin_suspend_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_SUSPEND)],
    payload: UserLifecycleReasonBody | None = None,
) -> UserPublic:
    target = lifecycle_service.deactivate_user(
        db,
        admin=admin,
        user_id=user_id,
        reason=payload.reason if payload else None,
    )
    return UserPublic.model_validate(build_user_public(target))


@router.post("/admin/{user_id}/deactivate", response_model=UserPublic)
def admin_deactivate_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_SUSPEND)],
    payload: UserLifecycleReasonBody | None = None,
) -> UserPublic:
    return admin_suspend_user(user_id, db, admin, payload)


@router.post("/admin/{user_id}/unsuspend", response_model=UserPublic)
def admin_unsuspend_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_SUSPEND)],
    payload: UserLifecycleReasonBody | None = None,
) -> UserPublic:
    target = lifecycle_service.restore_user(
        db,
        admin=admin,
        user_id=user_id,
        reason=payload.reason if payload else None,
    )
    return UserPublic.model_validate(build_user_public(target))


@router.post("/admin/{user_id}/restore", response_model=UserPublic)
def admin_restore_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_SUSPEND)],
    payload: UserLifecycleReasonBody | None = None,
) -> UserPublic:
    return admin_unsuspend_user(user_id, db, admin, payload)


@router.delete("/admin/{user_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def admin_delete_user() -> None:
    lifecycle_service.delete_user_blocked()


@router.post("/admin/{user_id}/ambassadors/block", response_model=UserPublic)
def admin_block_ambassadors(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_RESTRICT)],
) -> UserPublic:
    target = lifecycle_service.set_ambassadors_blocked(
        db, admin=admin, user_id=user_id, blocked=True
    )
    return UserPublic.model_validate(build_user_public(target))


@router.post("/admin/{user_id}/ambassadors/unblock", response_model=UserPublic)
def admin_unblock_ambassadors(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_RESTRICT)],
) -> UserPublic:
    target = lifecycle_service.set_ambassadors_blocked(
        db, admin=admin, user_id=user_id, blocked=False
    )
    return UserPublic.model_validate(build_user_public(target))


@router.get(
    "/admin-check",
    response_model=UserPublic,
    dependencies=[Depends(require_role("super_admin", "finance_admin"))],
)
def admin_role_check(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(build_user_public(user))


@router.get("/permission-check", response_model=UserPublic)
def permission_check(
    user: Annotated[User, Depends(require_permission("users.read"))],
) -> UserPublic:
    return UserPublic.model_validate(build_user_public(user))
