"""Taxonomy public + admin API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.taxonomy import service as taxonomy_service
from app.taxonomy.schemas import (
    AreaSuggestCreate,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    CitySuggestCreate,
    LocationCreate,
    LocationDetailPublic,
    LocationPublic,
    LocationUpdate,
    SubcategoryCreate,
    SubcategoryPublic,
    SubcategoryUpdate,
    VenueTypeSuggestCreate,
    VocabCreate,
    VocabPublic,
    VocabUpdate,
)
from app.users.models import User

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])

_ADMIN = Depends(require_permission("admin.full_access", "events.approve"))


def _category_public(db: Session, row) -> CategoryPublic:
    data = CategoryPublic.model_validate(row)
    data.usage_count = taxonomy_service.category_usage_count(db, row)
    return data


@router.get("/health")
async def taxonomy_module_health() -> dict[str, str]:
    return {"module": "taxonomy", "status": "ok"}


@router.get("/categories", response_model=list[CategoryPublic])
def public_list_categories(
    db: Annotated[Session, Depends(get_db)],
) -> list[CategoryPublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        rows = taxonomy_service.list_categories(db, active_only=True)
        return [_category_public(db, r).model_dump(mode="json") for r in rows]

    cached = get_or_set(cache_key("taxonomy", "categories"), CacheTTL.taxonomy, _produce)
    return [CategoryPublic.model_validate(row) for row in cached]


@router.get("/host-types", response_model=list[VocabPublic])
def public_list_host_types(
    db: Annotated[Session, Depends(get_db)],
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_host_types(db, active_only=True)
    ]


@router.get("/audience-types", response_model=list[VocabPublic])
def public_list_audience_types(
    db: Annotated[Session, Depends(get_db)],
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_audience_types(db, active_only=True)
    ]


@router.get("/tags", response_model=list[VocabPublic])
def public_list_tags(
    db: Annotated[Session, Depends(get_db)],
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_tags(db, active_only=True)
    ]


@router.get("/vibes", response_model=list[VocabPublic])
def public_list_vibes(
    db: Annotated[Session, Depends(get_db)],
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_vibes(db, active_only=True)
    ]


@router.get("/venue-types", response_model=list[VocabPublic])
def public_list_venue_types(
    db: Annotated[Session, Depends(get_db)],
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_venue_types(db, active_only=True)
    ]


@router.post(
    "/venue-types/suggest",
    response_model=VocabPublic,
    status_code=status.HTTP_201_CREATED,
)
def suggest_venue_type(
    payload: VenueTypeSuggestCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> VocabPublic:
    """Host suggests a new venue type; saved active for all hosts."""
    return VocabPublic.model_validate(
        taxonomy_service.suggest_venue_type(db, user=user, name=payload.name)
    )


@router.get("/locations", response_model=list[LocationPublic])
def public_list_locations(
    db: Annotated[Session, Depends(get_db)],
    kind: str | None = Query(default=None),
    parent_id: UUID | None = Query(default=None),
) -> list[LocationPublic]:
    return [
        LocationPublic.model_validate(r)
        for r in taxonomy_service.list_locations(
            db, active_only=True, kind=kind, parent_id=parent_id
        )
    ]


@router.get(
    "/locations/{kind}/{slug}",
    response_model=LocationDetailPublic,
)
def public_get_location(
    kind: str,
    slug: str,
    db: Annotated[Session, Depends(get_db)],
) -> LocationDetailPublic:
    resolved = taxonomy_service.resolve_location_detail(db, kind=kind, slug=slug)
    if resolved is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Location not found")
    location, ancestors, children, siblings = resolved
    return LocationDetailPublic(
        location=LocationPublic.model_validate(location),
        ancestors=[LocationPublic.model_validate(a) for a in ancestors],
        children=[LocationPublic.model_validate(c) for c in children],
        siblings=[LocationPublic.model_validate(s) for s in siblings],
    )


@router.post(
    "/locations/suggest-area",
    response_model=LocationPublic,
    status_code=status.HTTP_201_CREATED,
)
def suggest_area(
    payload: AreaSuggestCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> LocationPublic:
    """Host suggests a new area under a city; saved active for all hosts."""
    return LocationPublic.model_validate(
        taxonomy_service.suggest_area(
            db, user=user, city_id=payload.city_id, name=payload.name
        )
    )


@router.post(
    "/locations/suggest-city",
    response_model=LocationPublic,
    status_code=status.HTTP_201_CREATED,
)
def suggest_city(
    payload: CitySuggestCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> LocationPublic:
    """Host suggests a new city under a state; saved active for all hosts."""
    return LocationPublic.model_validate(
        taxonomy_service.suggest_city(
            db, user=user, state_id=payload.state_id, name=payload.name
        )
    )


# --- Admin categories ---


@router.get("/admin/categories", response_model=list[CategoryPublic])
def admin_list_categories(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    include_archived: bool = Query(default=False),
) -> list[CategoryPublic]:
    rows = taxonomy_service.list_categories(db, include_archived=include_archived)
    return [_category_public(db, r) for r in rows]


@router.post(
    "/admin/categories",
    response_model=CategoryPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_category(
    payload: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> CategoryPublic:
    row = taxonomy_service.create_category(db, user=user, payload=payload)
    return _category_public(db, row)


@router.patch("/admin/categories/{category_id}", response_model=CategoryPublic)
def admin_update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> CategoryPublic:
    row = taxonomy_service.update_category(
        db, user=user, category_id=category_id, payload=payload
    )
    return _category_public(db, row)


@router.post("/admin/categories/{category_id}/archive", response_model=CategoryPublic)
def admin_archive_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> CategoryPublic:
    row = taxonomy_service.archive_category(db, user=user, category_id=category_id)
    return _category_public(db, row)


@router.post("/admin/categories/{category_id}/restore", response_model=CategoryPublic)
def admin_restore_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> CategoryPublic:
    row = taxonomy_service.restore_category(db, user=user, category_id=category_id)
    return _category_public(db, row)


@router.delete(
    "/admin/categories/{category_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def admin_delete_category(category_id: UUID) -> None:
    _ = category_id
    taxonomy_service.hard_delete_blocked("taxonomy category")


# --- Subcategories (category hierarchy) ---


@router.get(
    "/categories/{category_slug}/subcategories",
    response_model=list[SubcategoryPublic],
)
def public_list_subcategories(
    category_slug: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[SubcategoryPublic]:
    cats = taxonomy_service.list_categories(db, active_only=True)
    parent = next((c for c in cats if c.slug == category_slug), None)
    if parent is None:
        return []
    return [
        SubcategoryPublic.model_validate(r)
        for r in taxonomy_service.list_subcategories(
            db, category_id=parent.id, active_only=True
        )
    ]


@router.get(
    "/admin/categories/{category_id}/subcategories",
    response_model=list[SubcategoryPublic],
)
def admin_list_subcategories(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    include_archived: bool = Query(default=False),
) -> list[SubcategoryPublic]:
    return [
        SubcategoryPublic.model_validate(r)
        for r in taxonomy_service.list_subcategories(
            db, category_id=category_id, include_archived=include_archived
        )
    ]


@router.post(
    "/admin/categories/{category_id}/subcategories",
    response_model=SubcategoryPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_subcategory(
    category_id: UUID,
    payload: SubcategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> SubcategoryPublic:
    return SubcategoryPublic.model_validate(
        taxonomy_service.create_subcategory(
            db, user=user, category_id=category_id, payload=payload
        )
    )


@router.patch(
    "/admin/subcategories/{subcategory_id}",
    response_model=SubcategoryPublic,
)
def admin_update_subcategory(
    subcategory_id: UUID,
    payload: SubcategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> SubcategoryPublic:
    return SubcategoryPublic.model_validate(
        taxonomy_service.update_subcategory(
            db, user=user, subcategory_id=subcategory_id, payload=payload
        )
    )


@router.post(
    "/admin/subcategories/{subcategory_id}/archive",
    response_model=SubcategoryPublic,
)
def admin_archive_subcategory(
    subcategory_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> SubcategoryPublic:
    return SubcategoryPublic.model_validate(
        taxonomy_service.archive_subcategory(
            db, user=user, subcategory_id=subcategory_id
        )
    )


@router.post(
    "/admin/subcategories/{subcategory_id}/restore",
    response_model=SubcategoryPublic,
)
def admin_restore_subcategory(
    subcategory_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> SubcategoryPublic:
    return SubcategoryPublic.model_validate(
        taxonomy_service.restore_subcategory(
            db, user=user, subcategory_id=subcategory_id
        )
    )


@router.delete(
    "/admin/subcategories/{subcategory_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def admin_delete_subcategory(subcategory_id: UUID) -> None:
    _ = subcategory_id
    taxonomy_service.hard_delete_blocked("taxonomy subcategory")


# --- Tags ---


@router.get("/admin/tags", response_model=list[VocabPublic])
def admin_list_tags(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    include_archived: bool = Query(default=False),
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_tags(db, include_archived=include_archived)
    ]


@router.post(
    "/admin/tags", response_model=VocabPublic, status_code=status.HTTP_201_CREATED
)
def admin_create_tag(
    payload: VocabCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.create_tag(db, user=user, payload=payload)
    )


@router.patch("/admin/tags/{tag_id}", response_model=VocabPublic)
def admin_update_tag(
    tag_id: UUID,
    payload: VocabUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.update_tag(db, user=user, tag_id=tag_id, payload=payload)
    )


@router.post("/admin/tags/{tag_id}/archive", response_model=VocabPublic)
def admin_archive_tag(
    tag_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.archive_tag(db, user=user, tag_id=tag_id)
    )


@router.post("/admin/tags/{tag_id}/restore", response_model=VocabPublic)
def admin_restore_tag(
    tag_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.restore_tag(db, user=user, tag_id=tag_id)
    )


@router.delete(
    "/admin/tags/{tag_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def admin_delete_tag(tag_id: UUID) -> None:
    _ = tag_id
    taxonomy_service.hard_delete_blocked("taxonomy tag")


# --- Locations ---


@router.get("/admin/locations", response_model=list[LocationPublic])
def admin_list_locations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    include_inactive: bool = Query(default=False),
    kind: str | None = Query(default=None),
) -> list[LocationPublic]:
    return [
        LocationPublic.model_validate(r)
        for r in taxonomy_service.list_locations(
            db, include_inactive=include_inactive, kind=kind
        )
    ]


@router.post(
    "/admin/locations",
    response_model=LocationPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_location(
    payload: LocationCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> LocationPublic:
    return LocationPublic.model_validate(
        taxonomy_service.create_location(db, user=user, payload=payload)
    )


@router.patch("/admin/locations/{location_id}", response_model=LocationPublic)
def admin_update_location(
    location_id: UUID,
    payload: LocationUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> LocationPublic:
    return LocationPublic.model_validate(
        taxonomy_service.update_location(
            db, user=user, location_id=location_id, payload=payload
        )
    )


@router.post("/admin/locations/{location_id}/archive", response_model=LocationPublic)
def admin_archive_location(
    location_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> LocationPublic:
    return LocationPublic.model_validate(
        taxonomy_service.archive_location(db, user=user, location_id=location_id)
    )


@router.post("/admin/locations/{location_id}/restore", response_model=LocationPublic)
def admin_restore_location(
    location_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> LocationPublic:
    return LocationPublic.model_validate(
        taxonomy_service.restore_location(db, user=user, location_id=location_id)
    )


@router.post("/admin/seed-vocab")
def admin_seed_taxonomy_vocab(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> dict[str, int]:
    """Upsert default taxonomy vocab + expanded location catalog."""
    _ = user
    return taxonomy_service.seed_taxonomy_vocab(db)


@router.delete(
    "/admin/locations/{location_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def admin_delete_location(location_id: UUID) -> None:
    _ = location_id
    taxonomy_service.hard_delete_blocked("location")


# --- Host types ---


@router.get("/admin/host-types", response_model=list[VocabPublic])
def admin_list_host_types(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    include_archived: bool = Query(default=False),
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_host_types(
            db, include_archived=include_archived
        )
    ]


@router.post(
    "/admin/host-types",
    response_model=VocabPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_host_type(
    payload: VocabCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.create_host_type(db, user=user, payload=payload)
    )


@router.patch("/admin/host-types/{type_id}", response_model=VocabPublic)
def admin_update_host_type(
    type_id: UUID,
    payload: VocabUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.update_host_type(
            db, user=user, type_id=type_id, payload=payload
        )
    )


@router.post("/admin/host-types/{type_id}/archive", response_model=VocabPublic)
def admin_archive_host_type(
    type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.archive_host_type(db, user=user, type_id=type_id)
    )


@router.post("/admin/host-types/{type_id}/restore", response_model=VocabPublic)
def admin_restore_host_type(
    type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.restore_host_type(db, user=user, type_id=type_id)
    )


# --- Venue types ---


@router.get("/admin/venue-types", response_model=list[VocabPublic])
def admin_list_venue_types(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, _ADMIN],
    include_archived: bool = Query(default=False),
) -> list[VocabPublic]:
    return [
        VocabPublic.model_validate(r)
        for r in taxonomy_service.list_venue_types(
            db, include_archived=include_archived
        )
    ]


@router.post(
    "/admin/venue-types",
    response_model=VocabPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_venue_type(
    payload: VocabCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.create_venue_type(db, user=user, payload=payload)
    )


@router.patch("/admin/venue-types/{type_id}", response_model=VocabPublic)
def admin_update_venue_type(
    type_id: UUID,
    payload: VocabUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.update_venue_type(
            db, user=user, type_id=type_id, payload=payload
        )
    )


@router.post("/admin/venue-types/{type_id}/archive", response_model=VocabPublic)
def admin_archive_venue_type(
    type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.archive_venue_type(db, user=user, type_id=type_id)
    )


@router.post("/admin/venue-types/{type_id}/restore", response_model=VocabPublic)
def admin_restore_venue_type(
    type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, _ADMIN],
) -> VocabPublic:
    return VocabPublic.model_validate(
        taxonomy_service.restore_venue_type(db, user=user, type_id=type_id)
    )
