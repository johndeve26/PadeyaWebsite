"""Legacy Page and tier API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.hosts.schemas import HostProfileUpdate
from app.users.models import User
from app.legacy.discover import list_discover_hosts
from app.legacy.schemas import (
    HostDiscoveryPublic,
    HostTierSummary,
    LegacyPagePublic,
    LegacyProfileUpdate,
    LegacyTierPublic,
    LegacyTierUpdate,
    RecalcAllResult,
    ScoreHistoryPublic,
    TierProgressPublic,
)
from app.legacy.service import (
    get_my_legacy_page,
    get_my_tier_progress,
    list_host_score_history,
    list_host_tier_summaries,
    list_tiers,
    recalculate_all_hosts,
    recalculate_host,
    update_my_legacy_profile,
    update_tier,
)
from app.legacy.studio import get_public_legacy_by_username, update_legacy_studio


def _overlay_legacy_gender(
    db: Session,
    payload: LegacyPagePublic,
    *,
    viewer: User | None,
) -> LegacyPagePublic:
    if viewer is None or not payload.shows_personal_gender:
        return payload
    from app.hosts.models import Host
    from app.users.gender import gender_display_payload

    host = db.get(Host, payload.host_id)
    if host is None:
        return payload
    owner = db.get(User, host.user_id)
    if owner is None:
        return payload
    gender = gender_display_payload(
        db,
        viewer=viewer,
        profile_owner=owner,
        relationship_context="profile",
    )
    return payload.model_copy(update=gender)


router = APIRouter(prefix="/legacy", tags=["legacy"])
public_u_router = APIRouter(prefix="/u", tags=["legacy-public"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("/health")
async def legacy_module_health() -> dict[str, str]:
    return {"module": "legacy", "status": "ok"}


@router.get("/discover/hosts", response_model=list[HostDiscoveryPublic])
def discover_hosts(
    db: Annotated[Session, Depends(get_db)],
) -> list[HostDiscoveryPublic]:
    """Public marketplace listing for /hosts — no private contact or venue secrets."""
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            HostDiscoveryPublic.model_validate(row).model_dump(mode="json")
            for row in list_discover_hosts(db)
        ]

    cached = get_or_set(
        cache_key("legacy", "discover", "hosts"), CacheTTL.profile, _produce
    )
    return [HostDiscoveryPublic.model_validate(row) for row in cached]


@router.get("/me", response_model=LegacyPagePublic)
def my_legacy_page(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyPagePublic:
    return LegacyPagePublic.model_validate(get_my_legacy_page(db, user))


@router.get("/me/tier", response_model=TierProgressPublic)
def my_tier_progress(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TierProgressPublic:
    return TierProgressPublic.model_validate(get_my_tier_progress(db, user))


@router.patch("/me", response_model=LegacyPagePublic)
def patch_my_legacy(
    payload: LegacyProfileUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> LegacyPagePublic:
    ip, ua = _client_meta(request)
    data = payload.model_dump(exclude_unset=True)
    # Prefer studio update when Content Studio fields are present
    studio_keys = {
        "username",
        "tagline",
        "sponsorship_available",
        "primary_cta_label",
        "secondary_cta_label",
        "contact",
        "service_areas",
        "host_type_slug",
        "primary_category_slug",
    }
    if studio_keys.intersection(data):
        page = update_legacy_studio(
            db, user=user, payload=data, ip_address=ip, user_agent=ua
        )
    else:
        profile_data = {
            k: v
            for k, v in data.items()
            if k
            in {
                "display_name",
                "bio",
                "website",
                "city",
                "state",
                "country",
                "avatar_url",
                "cover_url",
                "social_links",
                "host_type_slugs",
                "category_slugs",
                "audience_slugs",
                "primary_city_slug",
                "service_area_slugs",
                "niche_positioning",
            }
        }
        if isinstance(profile_data.get("social_links"), list):
            page = update_legacy_studio(
                db, user=user, payload=data, ip_address=ip, user_agent=ua
            )
        else:
            page = update_my_legacy_profile(
                db,
                user=user,
                payload=HostProfileUpdate.model_validate(profile_data),
                ip_address=ip,
                user_agent=ua,
            )
    return LegacyPagePublic.model_validate(page)


@router.get(
    "/admin/hosts",
    response_model=list[HostTierSummary],
    dependencies=[Depends(require_permission("legacy.manage", "admin.full_access"))],
)
def admin_list_hosts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("legacy.manage", "admin.full_access"))],
) -> list[HostTierSummary]:
    return [HostTierSummary.model_validate(h) for h in list_host_tier_summaries(db)]


@router.get(
    "/admin/tiers",
    response_model=list[LegacyTierPublic],
    dependencies=[Depends(require_permission("legacy.manage", "admin.full_access"))],
)
def admin_list_tiers(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("legacy.manage", "admin.full_access"))],
) -> list[LegacyTierPublic]:
    return [LegacyTierPublic.model_validate(t) for t in list_tiers(db)]


@router.patch(
    "/admin/tiers/{tier_id}",
    response_model=LegacyTierPublic,
    dependencies=[Depends(require_permission("legacy.manage", "admin.full_access"))],
)
def admin_update_tier(
    tier_id: UUID,
    payload: LegacyTierUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("legacy.manage", "admin.full_access"))],
) -> LegacyTierPublic:
    ip, ua = _client_meta(request)
    tier = update_tier(
        db,
        user=user,
        tier_id=tier_id,
        payload=payload.model_dump(exclude_unset=True),
        ip_address=ip,
        user_agent=ua,
    )
    return LegacyTierPublic.model_validate(tier)


@router.post(
    "/admin/hosts/{host_id}/recalculate",
    response_model=HostTierSummary,
    dependencies=[Depends(require_permission("legacy.manage", "admin.full_access"))],
)
def admin_recalc_host(
    host_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("legacy.manage", "admin.full_access"))],
) -> HostTierSummary:
    ip, ua = _client_meta(request)
    score = recalculate_host(
        db, user=user, host_id=host_id, ip_address=ip, user_agent=ua
    )
    from app.hosts.models import Host
    from app.legacy.models import LegacyTier

    host = db.get(Host, host_id)
    tier = db.get(LegacyTier, score.tier_id) if score.tier_id else None
    assert host is not None
    return HostTierSummary.model_validate(
        {
            "host_id": host.id,
            "display_name": host.display_name,
            "username": host.slug,
            "composite_score": score.composite_score,
            "tier": tier,
            "legacy_status": score.legacy_status,
            "updated_at": score.updated_at,
        }
    )


@router.post(
    "/admin/recalculate-all",
    response_model=RecalcAllResult,
    dependencies=[Depends(require_permission("legacy.manage", "admin.full_access"))],
)
def admin_recalc_all(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("legacy.manage", "admin.full_access"))],
) -> RecalcAllResult:
    ip, ua = _client_meta(request)
    return RecalcAllResult.model_validate(
        recalculate_all_hosts(db, user=user, ip_address=ip, user_agent=ua)
    )


@router.get(
    "/admin/hosts/{host_id}/history",
    response_model=list[ScoreHistoryPublic],
    dependencies=[Depends(require_permission("legacy.manage", "admin.full_access"))],
)
def admin_host_history(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("legacy.manage", "admin.full_access"))],
) -> list[ScoreHistoryPublic]:
    return [
        ScoreHistoryPublic.model_validate(h) for h in list_host_score_history(db, host_id)
    ]


@router.get("/{username}", response_model=LegacyPagePublic)
def public_legacy_page(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    viewer: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> LegacyPagePublic:
    payload = LegacyPagePublic.model_validate(get_public_legacy_by_username(db, username))
    return _overlay_legacy_gender(db, payload, viewer=viewer)


@public_u_router.get("/{username}/legacy", response_model=LegacyPagePublic)
def public_u_legacy_page(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    viewer: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> LegacyPagePublic:
    payload = LegacyPagePublic.model_validate(get_public_legacy_by_username(db, username))
    return _overlay_legacy_gender(db, payload, viewer=viewer)
