"""CMS public + admin API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.cms import service as cms_service
from app.cms.schemas import (
    BannerCreate,
    BannerPublic,
    BannerUpdate,
    BlogPostCreate,
    BlogPostPublic,
    BlogPostUpdate,
    BrowseTileCreate,
    BrowseTilePublic,
    BrowseTileUpdate,
    FaqCreate,
    FaqPublic,
    FaqUpdate,
)
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/cms", tags=["cms"])


@router.get("/health")
async def cms_module_health() -> dict[str, str]:
    return {"module": "cms", "status": "ok"}


# --- Public ---


@router.get("/blog", response_model=list[BlogPostPublic])
def public_blog_list(db: Annotated[Session, Depends(get_db)]) -> list[BlogPostPublic]:
    return [BlogPostPublic.model_validate(r) for r in cms_service.list_public_posts(db)]


@router.get("/blog/{slug}", response_model=BlogPostPublic)
def public_blog_detail(
    slug: str, db: Annotated[Session, Depends(get_db)]
) -> BlogPostPublic:
    return BlogPostPublic.model_validate(cms_service.get_public_post(db, slug))


@router.get("/faqs", response_model=list[FaqPublic])
def public_faqs(db: Annotated[Session, Depends(get_db)]) -> list[FaqPublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            FaqPublic.model_validate(r).model_dump(mode="json")
            for r in cms_service.list_public_faqs(db)
        ]

    cached = get_or_set(cache_key("cms", "faqs"), CacheTTL.content, _produce)
    return [FaqPublic.model_validate(row) for row in cached]


@router.get("/banners", response_model=list[BannerPublic])
def public_banners(db: Annotated[Session, Depends(get_db)]) -> list[BannerPublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            BannerPublic.model_validate(r).model_dump(mode="json")
            for r in cms_service.list_public_banners(db)
        ]

    cached = get_or_set(cache_key("cms", "banners"), CacheTTL.content, _produce)
    return [BannerPublic.model_validate(row) for row in cached]


@router.get("/browse-tiles", response_model=list[BrowseTilePublic])
def public_browse_tiles(
    db: Annotated[Session, Depends(get_db)],
) -> list[BrowseTilePublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            BrowseTilePublic.model_validate(r).model_dump(mode="json")
            for r in cms_service.list_public_browse_tiles(db)
        ]

    cached = get_or_set(cache_key("cms", "browse-tiles"), CacheTTL.taxonomy, _produce)
    return [BrowseTilePublic.model_validate(row) for row in cached]


# --- Admin blog ---


@router.get(
    "/admin/blog",
    response_model=list[BlogPostPublic],
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_list_blog(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> list[BlogPostPublic]:
    rows = cms_service.list_admin_posts(
        db, user=user, include_archived=include_archived
    )
    return [BlogPostPublic.model_validate(r) for r in rows]


@router.post(
    "/admin/blog",
    response_model=BlogPostPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_blog(
    payload: BlogPostCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BlogPostPublic:
    return BlogPostPublic.model_validate(
        cms_service.create_post(db, user=user, payload=payload)
    )


@router.patch("/admin/blog/{post_id}", response_model=BlogPostPublic)
def admin_update_blog(
    post_id: UUID,
    payload: BlogPostUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BlogPostPublic:
    return BlogPostPublic.model_validate(
        cms_service.update_post(db, user=user, post_id=post_id, payload=payload)
    )


@router.delete(
    "/admin/blog/{post_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED
)
def admin_delete_blog() -> None:
    cms_service.delete_cms_blocked()


@router.post("/admin/blog/{post_id}/publish", response_model=BlogPostPublic)
def admin_publish_blog(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BlogPostPublic:
    return BlogPostPublic.model_validate(
        cms_service.publish_post(db, user=user, post_id=post_id)
    )


@router.post("/admin/blog/{post_id}/archive", response_model=BlogPostPublic)
def admin_archive_blog(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BlogPostPublic:
    return BlogPostPublic.model_validate(
        cms_service.archive_post(db, user=user, post_id=post_id)
    )


@router.post("/admin/blog/{post_id}/restore", response_model=BlogPostPublic)
def admin_restore_blog(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BlogPostPublic:
    return BlogPostPublic.model_validate(
        cms_service.restore_post(db, user=user, post_id=post_id)
    )


# --- Admin FAQs ---


@router.get(
    "/admin/faqs",
    response_model=list[FaqPublic],
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_list_faqs(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> list[FaqPublic]:
    return [
        FaqPublic.model_validate(r)
        for r in cms_service.list_admin_faqs(
            db, user=user, include_archived=include_archived
        )
    ]


@router.post(
    "/admin/faqs",
    response_model=FaqPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_faq(
    payload: FaqCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> FaqPublic:
    return FaqPublic.model_validate(cms_service.create_faq(db, user=user, payload=payload))


@router.patch("/admin/faqs/{faq_id}", response_model=FaqPublic)
def admin_update_faq(
    faq_id: UUID,
    payload: FaqUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> FaqPublic:
    return FaqPublic.model_validate(
        cms_service.update_faq(db, user=user, faq_id=faq_id, payload=payload)
    )


@router.delete("/admin/faqs/{faq_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def admin_delete_faq() -> None:
    cms_service.delete_cms_blocked()


@router.post("/admin/faqs/{faq_id}/publish", response_model=FaqPublic)
def admin_publish_faq(
    faq_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> FaqPublic:
    return FaqPublic.model_validate(cms_service.publish_faq(db, user=user, faq_id=faq_id))


@router.post("/admin/faqs/{faq_id}/archive", response_model=FaqPublic)
def admin_archive_faq(
    faq_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> FaqPublic:
    return FaqPublic.model_validate(cms_service.archive_faq(db, user=user, faq_id=faq_id))


@router.post("/admin/faqs/{faq_id}/restore", response_model=FaqPublic)
def admin_restore_faq(
    faq_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> FaqPublic:
    return FaqPublic.model_validate(cms_service.restore_faq(db, user=user, faq_id=faq_id))


# --- Admin banners ---


@router.get(
    "/admin/banners",
    response_model=list[BannerPublic],
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_list_banners(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> list[BannerPublic]:
    return [
        BannerPublic.model_validate(r)
        for r in cms_service.list_admin_banners(
            db, user=user, include_archived=include_archived
        )
    ]


@router.post(
    "/admin/banners",
    response_model=BannerPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_banner(
    payload: BannerCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BannerPublic:
    return BannerPublic.model_validate(
        cms_service.create_banner(db, user=user, payload=payload)
    )


@router.patch("/admin/banners/{banner_id}", response_model=BannerPublic)
def admin_update_banner(
    banner_id: UUID,
    payload: BannerUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BannerPublic:
    return BannerPublic.model_validate(
        cms_service.update_banner(db, user=user, banner_id=banner_id, payload=payload)
    )


@router.delete(
    "/admin/banners/{banner_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED
)
def admin_delete_banner() -> None:
    cms_service.delete_cms_blocked()


@router.post("/admin/banners/{banner_id}/publish", response_model=BannerPublic)
def admin_publish_banner(
    banner_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BannerPublic:
    return BannerPublic.model_validate(
        cms_service.publish_banner(db, user=user, banner_id=banner_id)
    )


@router.post("/admin/banners/{banner_id}/archive", response_model=BannerPublic)
def admin_archive_banner(
    banner_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BannerPublic:
    return BannerPublic.model_validate(
        cms_service.archive_banner(db, user=user, banner_id=banner_id)
    )


@router.post("/admin/banners/{banner_id}/restore", response_model=BannerPublic)
def admin_restore_banner(
    banner_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BannerPublic:
    return BannerPublic.model_validate(
        cms_service.restore_banner(db, user=user, banner_id=banner_id)
    )


# --- Admin browse tiles ---


@router.get(
    "/admin/browse-tiles",
    response_model=list[BrowseTilePublic],
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_list_browse_tiles(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> list[BrowseTilePublic]:
    return [
        BrowseTilePublic.model_validate(r)
        for r in cms_service.list_admin_browse_tiles(
            db, user=user, include_archived=include_archived
        )
    ]


@router.post(
    "/admin/browse-tiles",
    response_model=BrowseTilePublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_browse_tile(
    payload: BrowseTileCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BrowseTilePublic:
    return BrowseTilePublic.model_validate(
        cms_service.create_browse_tile(db, user=user, payload=payload)
    )


@router.post(
    "/admin/browse-tiles/seed-defaults",
    response_model=dict,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_seed_browse_tiles(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, int | str]:
    created = cms_service.seed_default_browse_tiles(db, actor_user_id=user.id)
    return {"created": created, "status": "ok"}


@router.patch("/admin/browse-tiles/{tile_id}", response_model=BrowseTilePublic)
def admin_update_browse_tile(
    tile_id: UUID,
    payload: BrowseTileUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BrowseTilePublic:
    return BrowseTilePublic.model_validate(
        cms_service.update_browse_tile(db, user=user, tile_id=tile_id, payload=payload)
    )


@router.delete(
    "/admin/browse-tiles/{tile_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def admin_delete_browse_tile() -> None:
    cms_service.delete_cms_blocked()


@router.post("/admin/browse-tiles/{tile_id}/publish", response_model=BrowseTilePublic)
def admin_publish_browse_tile(
    tile_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BrowseTilePublic:
    return BrowseTilePublic.model_validate(
        cms_service.publish_browse_tile(db, user=user, tile_id=tile_id)
    )


@router.post("/admin/browse-tiles/{tile_id}/archive", response_model=BrowseTilePublic)
def admin_archive_browse_tile(
    tile_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BrowseTilePublic:
    return BrowseTilePublic.model_validate(
        cms_service.archive_browse_tile(db, user=user, tile_id=tile_id)
    )


@router.post("/admin/browse-tiles/{tile_id}/restore", response_model=BrowseTilePublic)
def admin_restore_browse_tile(
    tile_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> BrowseTilePublic:
    return BrowseTilePublic.model_validate(
        cms_service.restore_browse_tile(db, user=user, tile_id=tile_id)
    )
