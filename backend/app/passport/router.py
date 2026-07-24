"""Fan Passport API — private dashboard + public /f/{username} + directory."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.core.database import get_db
from app.passport.directory_service import (
    admin_hide_fan,
    admin_restore_fan,
    list_admin_fans,
    list_directory_passports,
)
from app.passport.public_service import (
    build_public_activity,
    build_public_badges,
    build_public_passport_page,
)
from app.passport.schemas import (
    AdminFanActionResult,
    AdminFanListPublic,
    AdminFanModerateBody,
    FanBadgePublic,
    FanDirectoryListPublic,
    FanPassportActivityPublic,
    FanPassportPublic,
    FanPassportPublicPage,
    PassportSettingsPublic,
    PassportSettingsUpdate,
)
from app.passport.service import (
    get_my_passport,
    list_my_badges,
    settings_payload,
    update_passport_settings,
)
from app.users.models import User

router = APIRouter(tags=["passport"])


@router.get("/passport/health")
async def passport_module_health() -> dict[str, str]:
    return {"module": "passport", "status": "ok"}


@router.get("/passport/me", response_model=FanPassportPublic)
@router.get("/dashboard/passport", response_model=FanPassportPublic)
def my_passport(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> FanPassportPublic:
    return FanPassportPublic.model_validate(get_my_passport(db, user))


@router.get("/passport/me/badges", response_model=list[FanBadgePublic])
def my_badges(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[FanBadgePublic]:
    return [FanBadgePublic.model_validate(b) for b in list_my_badges(db, user)]


@router.get("/passport/me/settings", response_model=PassportSettingsPublic)
@router.get("/dashboard/passport/settings", response_model=PassportSettingsPublic)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PassportSettingsPublic:
    from app.passport.service import ensure_passport

    passport = ensure_passport(db, user)
    db.commit()
    return PassportSettingsPublic.model_validate(settings_payload(passport))


@router.patch("/passport/me/settings", response_model=PassportSettingsPublic)
@router.patch("/dashboard/passport/settings", response_model=PassportSettingsPublic)
def patch_settings(
    payload: PassportSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PassportSettingsPublic:
    passport = update_passport_settings(db, user, payload)
    return PassportSettingsPublic.model_validate(settings_payload(passport))


@router.get("/fans", response_model=FanDirectoryListPublic)
def fan_directory(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    city: str | None = None,
    category: str | None = None,
    badge: str | None = None,
    sort: str = Query(default="recently_active"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=48),
    has_reviews: bool | None = None,
    has_vault_unlocks: bool | None = None,
    min_events: int | None = Query(default=None, ge=0),
    max_events: int | None = Query(default=None, ge=0),
) -> FanDirectoryListPublic:
    """Public Fan Passport Directory — opt-in public profiles only."""
    from app.core.cache import CacheTTL, cache_key, get_or_set

    key = cache_key(
        "fans",
        "directory",
        q=q,
        city=city,
        category=category,
        badge=badge,
        sort=sort,
        page=page,
        limit=limit,
        has_reviews=has_reviews,
        has_vault_unlocks=has_vault_unlocks,
        min_events=min_events,
        max_events=max_events,
    )

    def _produce() -> dict:
        return FanDirectoryListPublic.model_validate(
            list_directory_passports(
                db,
                q=q,
                city=city,
                category=category,
                badge=badge,
                sort=sort,
                page=page,
                limit=limit,
                has_reviews=has_reviews,
                has_vault_unlocks=has_vault_unlocks,
                min_events=min_events,
                max_events=max_events,
            )
        ).model_dump(mode="json")

    cached = get_or_set(key, CacheTTL.profile, _produce)
    return FanDirectoryListPublic.model_validate(cached)


@router.get("/f/{username}", response_model=FanPassportPublicPage)
def public_passport(
    username: str,
    db: Annotated[Session, Depends(get_db)],
) -> FanPassportPublicPage:
    from app.core.cache import CacheTTL, cache_get, cache_key, cache_set

    key = cache_key("passport", "public", username)
    hit = cache_get(key)
    if hit is not None:
        return FanPassportPublicPage.model_validate(hit)

    payload = FanPassportPublicPage.model_validate(
        build_public_passport_page(db, username)
    )
    cache_set(key, payload.model_dump(mode="json"), CacheTTL.profile)
    return payload


@router.get(
    "/admin/fans",
    response_model=AdminFanListPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_fans(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    q: str | None = None,
    visibility: str | None = None,
    directory_only: bool | None = None,
    include_hidden: bool = True,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=40, ge=1, le=100),
) -> AdminFanListPublic:
    return AdminFanListPublic.model_validate(
        list_admin_fans(
            db,
            q=q,
            visibility=visibility,
            directory_only=directory_only,
            include_hidden=include_hidden,
            page=page,
            limit=limit,
        )
    )


@router.patch(
    "/admin/fans/{user_id}/hide",
    response_model=AdminFanActionResult,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_hide_fan_route(
    user_id: UUID,
    payload: AdminFanModerateBody,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminFanActionResult:
    passport = admin_hide_fan(db, actor=actor, user_id=user_id, reason=payload.reason)
    return AdminFanActionResult(
        user_id=str(user_id),
        username=passport.username,
        admin_hidden=True,
        appear_in_directory=passport.appear_in_directory,
        visibility=passport.visibility,
    )


@router.patch(
    "/admin/fans/{user_id}/restore",
    response_model=AdminFanActionResult,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_restore_fan_route(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.full_access"))],
    payload: AdminFanModerateBody | None = None,
) -> AdminFanActionResult:
    passport = admin_restore_fan(
        db,
        actor=actor,
        user_id=user_id,
        reason=payload.reason if payload else None,
    )
    return AdminFanActionResult(
        user_id=str(user_id),
        username=passport.username,
        admin_hidden=False,
        appear_in_directory=passport.appear_in_directory,
        visibility=passport.visibility,
    )


@router.get("/f/{username}/activity", response_model=FanPassportActivityPublic)
def public_activity(
    username: str,
    db: Annotated[Session, Depends(get_db)],
) -> FanPassportActivityPublic:
    return FanPassportActivityPublic.model_validate(
        build_public_activity(db, username)
    )


@router.get("/f/{username}/badges", response_model=list[FanBadgePublic])
def public_badges_route(
    username: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[FanBadgePublic]:
    return [FanBadgePublic.model_validate(b) for b in build_public_badges(db, username)]
