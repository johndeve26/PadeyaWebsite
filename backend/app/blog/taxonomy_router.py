"""Admin + picker APIs for blog categories, tags, post types, and media roles."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.blog import taxonomy_service as tax
from app.blog.schemas import (
    BlogMediaUploadPublic,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    MediaRoleCreate,
    MediaRolePublic,
    MediaRoleUpdate,
    PostTypeCreate,
    PostTypePublic,
    PostTypeUpdate,
    ReorderPayload,
    TagCreate,
    TagPublic,
    TagUpdate,
)
from app.core.database import get_db
from app.users.models import User


def _hard_delete_blocked() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Hard delete blocked; use POST .../archive",
    )


router = APIRouter(tags=["blog-taxonomy"])

ManageUser = Annotated[
    User,
    Depends(require_permission("admin.blog.taxonomy.manage")),
]
ViewUser = Annotated[
    User,
    Depends(
        require_permission(
            "admin.blog.view",
            "admin.blog.edit",
            "admin.blog.taxonomy.manage",
            "admin.blog.create",
        )
    ),
]


def _cats(db: Session, rows: list) -> list[CategoryPublic]:
    usage = tax.category_usage_map(db, [r.id for r in rows])
    return [
        CategoryPublic.model_validate(tax.serialize_category(r, usage=usage.get(r.id, 0)))
        for r in rows
    ]


def _tags(db: Session, rows: list) -> list[TagPublic]:
    usage = tax.tag_usage_map(db, [r.id for r in rows])
    return [
        TagPublic.model_validate(tax.serialize_tag(r, usage=usage.get(r.id, 0)))
        for r in rows
    ]


def _types(db: Session, rows: list) -> list[PostTypePublic]:
    usage = tax.post_type_usage_map(db, [r.id for r in rows])
    return [
        PostTypePublic.model_validate(tax.serialize_post_type(r, usage=usage.get(r.id, 0)))
        for r in rows
    ]


def _roles(db: Session, rows: list) -> list[MediaRolePublic]:
    usage = tax.media_role_usage_map(db)
    return [
        MediaRolePublic.model_validate(
            tax.serialize_media_role(r, usage=usage.get(r.key, 0))
        )
        for r in rows
    ]


# --- Categories ---


@router.get("/admin/blog/categories", response_model=list[CategoryPublic])
def admin_categories(
    db: Annotated[Session, Depends(get_db)],
    user: ViewUser,
    include_archived: bool = Query(default=False),
    active_only: bool = Query(default=False),
) -> list[CategoryPublic]:
    tax.require_taxonomy_view(user)
    rows = tax.list_categories(
        db, include_archived=include_archived, active_only=active_only
    )
    return _cats(db, rows)


@router.post(
    "/admin/blog/categories",
    response_model=CategoryPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_category(
    payload: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> CategoryPublic:
    row = tax.create_category(
        db,
        user=user,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        sort_order=payload.sort_order,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
    )
    return _cats(db, [row])[0]


@router.patch("/admin/blog/categories/{category_id}", response_model=CategoryPublic)
def admin_update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> CategoryPublic:
    row = tax.update_category(
        db,
        user=user,
        category_id=category_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        sort_order=payload.sort_order,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        confirm_slug_change=payload.confirm_slug_change,
    )
    return _cats(db, [row])[0]


@router.post(
    "/admin/blog/categories/{category_id}/archive",
    response_model=CategoryPublic,
)
def admin_archive_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> CategoryPublic:
    return _cats(db, [tax.archive_category(db, user=user, category_id=category_id)])[0]


@router.post(
    "/admin/blog/categories/{category_id}/restore",
    response_model=CategoryPublic,
)
def admin_restore_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> CategoryPublic:
    return _cats(db, [tax.restore_category(db, user=user, category_id=category_id)])[0]


@router.post("/admin/blog/categories/reorder", response_model=list[CategoryPublic])
def admin_reorder_categories(
    payload: ReorderPayload,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> list[CategoryPublic]:
    rows = tax.reorder_categories(db, user=user, ordered_ids=payload.ordered_ids)
    return _cats(db, rows)


@router.delete("/admin/blog/categories/{category_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def admin_delete_category_blocked(category_id: UUID) -> None:
    _ = category_id
    _hard_delete_blocked()


# --- Tags ---


@router.get("/admin/blog/tags", response_model=list[TagPublic])
def admin_tags(
    db: Annotated[Session, Depends(get_db)],
    user: ViewUser,
    include_archived: bool = Query(default=False),
    active_only: bool = Query(default=False),
) -> list[TagPublic]:
    tax.require_taxonomy_view(user)
    rows = tax.list_tags(db, include_archived=include_archived, active_only=active_only)
    return _tags(db, rows)


@router.post(
    "/admin/blog/tags",
    response_model=TagPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_tag(
    payload: TagCreate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> TagPublic:
    row = tax.create_tag(
        db,
        user=user,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    return _tags(db, [row])[0]


@router.patch("/admin/blog/tags/{tag_id}", response_model=TagPublic)
def admin_update_tag(
    tag_id: UUID,
    payload: TagUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> TagPublic:
    row = tax.update_tag(
        db,
        user=user,
        tag_id=tag_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        sort_order=payload.sort_order,
        confirm_slug_change=payload.confirm_slug_change,
    )
    return _tags(db, [row])[0]


@router.post("/admin/blog/tags/{tag_id}/archive", response_model=TagPublic)
def admin_archive_tag(
    tag_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> TagPublic:
    return _tags(db, [tax.archive_tag(db, user=user, tag_id=tag_id)])[0]


@router.post("/admin/blog/tags/{tag_id}/restore", response_model=TagPublic)
def admin_restore_tag(
    tag_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> TagPublic:
    return _tags(db, [tax.restore_tag(db, user=user, tag_id=tag_id)])[0]


@router.post("/admin/blog/tags/reorder", response_model=list[TagPublic])
def admin_reorder_tags(
    payload: ReorderPayload,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> list[TagPublic]:
    return _tags(db, tax.reorder_tags(db, user=user, ordered_ids=payload.ordered_ids))


@router.delete("/admin/blog/tags/{tag_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def admin_delete_tag_blocked(tag_id: UUID) -> None:
    _ = tag_id
    _hard_delete_blocked()


# --- Post types ---


@router.get("/admin/blog/post-types", response_model=list[PostTypePublic])
def admin_post_types(
    db: Annotated[Session, Depends(get_db)],
    user: ViewUser,
    include_archived: bool = Query(default=False),
    active_only: bool = Query(default=False),
) -> list[PostTypePublic]:
    tax.require_taxonomy_view(user)
    rows = tax.list_post_types(
        db, include_archived=include_archived, active_only=active_only
    )
    return _types(db, rows)


@router.post(
    "/admin/blog/post-types",
    response_model=PostTypePublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_post_type(
    payload: PostTypeCreate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> PostTypePublic:
    row = tax.create_post_type(
        db,
        user=user,
        name=payload.name,
        key=payload.key,
        slug=payload.slug,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    return _types(db, [row])[0]


@router.patch("/admin/blog/post-types/{post_type_id}", response_model=PostTypePublic)
def admin_update_post_type(
    post_type_id: UUID,
    payload: PostTypeUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> PostTypePublic:
    row = tax.update_post_type(
        db,
        user=user,
        post_type_id=post_type_id,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        slug=payload.slug,
    )
    return _types(db, [row])[0]


@router.post(
    "/admin/blog/post-types/{post_type_id}/archive",
    response_model=PostTypePublic,
)
def admin_archive_post_type(
    post_type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> PostTypePublic:
    return _types(db, [tax.archive_post_type(db, user=user, post_type_id=post_type_id)])[0]


@router.post(
    "/admin/blog/post-types/{post_type_id}/restore",
    response_model=PostTypePublic,
)
def admin_restore_post_type(
    post_type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> PostTypePublic:
    return _types(db, [tax.restore_post_type(db, user=user, post_type_id=post_type_id)])[0]


@router.post("/admin/blog/post-types/reorder", response_model=list[PostTypePublic])
def admin_reorder_post_types(
    payload: ReorderPayload,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> list[PostTypePublic]:
    return _types(
        db, tax.reorder_post_types(db, user=user, ordered_ids=payload.ordered_ids)
    )


@router.delete(
    "/admin/blog/post-types/{post_type_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def admin_delete_post_type_blocked(post_type_id: UUID) -> None:
    _ = post_type_id
    _hard_delete_blocked()


# --- Media roles ---


@router.get("/admin/blog/media-roles", response_model=list[MediaRolePublic])
def admin_media_roles(
    db: Annotated[Session, Depends(get_db)],
    user: ViewUser,
    include_archived: bool = Query(default=False),
    active_only: bool = Query(default=False),
) -> list[MediaRolePublic]:
    tax.require_taxonomy_view(user)
    rows = tax.list_media_roles(
        db, include_archived=include_archived, active_only=active_only
    )
    return _roles(db, rows)


@router.post(
    "/admin/blog/media-roles",
    response_model=MediaRolePublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_media_role(
    payload: MediaRoleCreate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> MediaRolePublic:
    row = tax.create_media_role(
        db,
        user=user,
        name=payload.name,
        key=payload.key,
        description=payload.description,
        sort_order=payload.sort_order,
        storage_folder=payload.storage_folder,
        allowed_contexts=payload.allowed_contexts,
    )
    return _roles(db, [row])[0]


@router.patch("/admin/blog/media-roles/{role_id}", response_model=MediaRolePublic)
def admin_update_media_role(
    role_id: UUID,
    payload: MediaRoleUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> MediaRolePublic:
    row = tax.update_media_role(
        db,
        user=user,
        role_id=role_id,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        allowed_contexts=payload.allowed_contexts,
    )
    return _roles(db, [row])[0]


@router.post(
    "/admin/blog/media-roles/{role_id}/archive",
    response_model=MediaRolePublic,
)
def admin_archive_media_role(
    role_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> MediaRolePublic:
    return _roles(db, [tax.archive_media_role(db, user=user, role_id=role_id)])[0]


@router.post(
    "/admin/blog/media-roles/{role_id}/restore",
    response_model=MediaRolePublic,
)
def admin_restore_media_role(
    role_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> MediaRolePublic:
    return _roles(db, [tax.restore_media_role(db, user=user, role_id=role_id)])[0]


@router.post("/admin/blog/media-roles/reorder", response_model=list[MediaRolePublic])
def admin_reorder_media_roles(
    payload: ReorderPayload,
    db: Annotated[Session, Depends(get_db)],
    user: ManageUser,
) -> list[MediaRolePublic]:
    return _roles(
        db, tax.reorder_media_roles(db, user=user, ordered_ids=payload.ordered_ids)
    )


@router.delete(
    "/admin/blog/media-roles/{role_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def admin_delete_media_role_blocked(role_id: UUID) -> None:
    _ = role_id
    _hard_delete_blocked()


@router.post(
    "/admin/blog/media/upload",
    response_model=BlogMediaUploadPublic,
    status_code=status.HTTP_201_CREATED,
)
async def admin_upload_blog_media(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.blog.edit",
                "admin.blog.create",
                "admin.blog.taxonomy.manage",
            )
        ),
    ],
    file: Annotated[UploadFile, File(...)],
    media_role_key: Annotated[str, Form()] = "inline",
) -> BlogMediaUploadPublic:
    data = await file.read()
    result = tax.upload_blog_media(
        db,
        user=user,
        data=data,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type or "application/octet-stream",
        role_key=media_role_key,
    )
    return BlogMediaUploadPublic.model_validate(result)
