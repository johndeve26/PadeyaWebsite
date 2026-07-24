"""Public + admin Blog API routes."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.blog import comments as blog_comments
from app.blog import service as blog_service
from app.blog.schemas import (
    AuthorCreate,
    AuthorPublic,
    CategoryCreate,
    CategoryPublic,
    CommentAdmin,
    CommentCreate,
    CommentPublic,
    CommentReplyCreate,
    CommentUpdate,
    PostAdmin,
    PostCreate,
    PostListItem,
    PostPublic,
    PostUpdate,
    SlugCheck,
    TagCreate,
    TagPublic,
)
from app.blog.seed import seed_blog_content
from app.blog.rate_limit import (
    rate_limit_blog_comment_edit,
    rate_limit_blog_comment_reply,
)
from app.core.database import get_db
from app.users.models import User

router = APIRouter(tags=["blog"])


# --- Public ---


@router.get("/blog/posts", response_model=list[PostListItem])
def public_list_posts(
    db: Annotated[Session, Depends(get_db)],
    category: str | None = None,
    tag: str | None = None,
    author: str | None = None,
    featured: bool | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[PostListItem]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    key = cache_key(
        "blog",
        "posts",
        category=category,
        tag=tag,
        author=author,
        featured=featured,
        q=q,
        limit=limit,
    )

    def _produce() -> list[dict]:
        rows = blog_service.list_public_posts(
            db,
            category_slug=category,
            tag_slug=tag,
            author_slug=author,
            featured=featured,
            q=q,
            limit=limit,
        )
        return [
            PostListItem.model_validate(blog_service.serialize_post(r)).model_dump(
                mode="json"
            )
            for r in rows
        ]

    cached = get_or_set(key, CacheTTL.content, _produce)
    return [PostListItem.model_validate(row) for row in cached]


@router.get("/blog/posts/{slug}", response_model=PostPublic)
def public_post_detail(
    slug: str, db: Annotated[Session, Depends(get_db)]
) -> PostPublic:
    from app.core.cache import CacheTTL, cache_get, cache_key, cache_set

    key = cache_key("blog", "post", slug)
    hit = cache_get(key)
    if hit is not None:
        return PostPublic.model_validate(hit)

    row = blog_service.get_public_post(db, slug)
    related = blog_service.related_posts(db, row)
    payload = PostPublic.model_validate(
        blog_service.serialize_post(row, related=related)
    )
    cache_set(key, payload.model_dump(mode="json"), CacheTTL.content)
    return payload


@router.get("/blog/categories", response_model=list[CategoryPublic])
def public_categories(db: Annotated[Session, Depends(get_db)]) -> list[CategoryPublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            CategoryPublic.model_validate(r).model_dump(mode="json")
            for r in blog_service.list_categories(db)
        ]

    cached = get_or_set(cache_key("blog", "categories"), CacheTTL.taxonomy, _produce)
    return [CategoryPublic.model_validate(row) for row in cached]


@router.get("/blog/tags", response_model=list[TagPublic])
def public_tags(db: Annotated[Session, Depends(get_db)]) -> list[TagPublic]:
    return [TagPublic.model_validate(r) for r in blog_service.list_tags(db)]


@router.get("/blog/authors", response_model=list[AuthorPublic])
def public_authors(db: Annotated[Session, Depends(get_db)]) -> list[AuthorPublic]:
    return [AuthorPublic.model_validate(r) for r in blog_service.list_authors(db)]


@router.get("/blog/authors/{slug}", response_model=AuthorPublic)
def public_author(
    slug: str, db: Annotated[Session, Depends(get_db)]
) -> AuthorPublic:
    return AuthorPublic.model_validate(blog_service.get_author_by_slug(db, slug))


@router.get("/blog/categories/{slug}", response_model=CategoryPublic)
def public_category(
    slug: str, db: Annotated[Session, Depends(get_db)]
) -> CategoryPublic:
    return CategoryPublic.model_validate(blog_service.get_category_by_slug(db, slug))


@router.get("/blog/tags/{slug}", response_model=TagPublic)
def public_tag(slug: str, db: Annotated[Session, Depends(get_db)]) -> TagPublic:
    return TagPublic.model_validate(blog_service.get_tag_by_slug(db, slug))


@router.get("/blog/posts/{slug}/comments", response_model=list[CommentPublic])
def public_list_comments(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[CommentPublic]:
    threads = blog_comments.list_public_comments(
        db, post_slug=slug, viewer=user, limit=limit
    )
    return [CommentPublic.model_validate(row) for row in threads]


@router.post(
    "/blog/posts/{slug}/comments",
    response_model=CommentPublic,
    status_code=status.HTTP_201_CREATED,
)
def public_create_comment(
    slug: str,
    payload: CommentCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CommentPublic:
    row = blog_comments.create_comment(
        db, post_slug=slug, payload=payload, user=user
    )
    return CommentPublic.model_validate(
        blog_comments.serialize_comment(db, row, viewer=user)
    )


@router.post(
    "/blog/comments/{comment_id}/reply",
    response_model=CommentPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_blog_comment_reply)],
)
def public_reply_to_comment(
    comment_id: UUID,
    payload: CommentReplyCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CommentPublic:
    _ = request
    row = blog_comments.create_reply(
        db, comment_id=comment_id, payload=payload, user=user
    )
    return CommentPublic.model_validate(
        blog_comments.serialize_comment(db, row, viewer=user)
    )


@router.delete(
    "/blog/comments/{comment_id}",
    status_code=204,
    response_class=Response,
)
def withdraw_own_comment(
    comment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    blog_comments.withdraw_own_comment(db, comment_id=comment_id, user=user)
    return Response(status_code=204)


@router.patch(
    "/blog/comments/{comment_id}",
    response_model=CommentPublic,
    dependencies=[Depends(rate_limit_blog_comment_edit)],
)
def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> CommentPublic:
    _ = request
    row = blog_comments.update_comment(
        db, comment_id=comment_id, payload=payload, user=user
    )
    return CommentPublic.model_validate(
        blog_comments.serialize_comment(db, row, viewer=user)
    )


# --- Admin ---


@router.get("/admin/blog/posts", response_model=list[PostAdmin])
def admin_list_posts(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
    include_archived: bool = Query(default=False),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[PostAdmin]:
    rows = blog_service.list_admin_posts(
        db, user=user, include_archived=include_archived, status_filter=status_filter
    )
    return [
        PostAdmin.model_validate(blog_service.serialize_post(r, admin=True))
        for r in rows
    ]


@router.get("/admin/blog/posts/{post_id}", response_model=PostAdmin)
def admin_get_post(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> PostAdmin:
    row = blog_service.get_admin_post(db, user=user, post_id=post_id)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.post(
    "/admin/blog/posts",
    response_model=PostAdmin,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_post(
    payload: PostCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.create"))],
) -> PostAdmin:
    row = blog_service.create_post(db, user=user, payload=payload)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.patch("/admin/blog/posts/{post_id}", response_model=PostAdmin)
def admin_update_post(
    post_id: UUID,
    payload: PostUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> PostAdmin:
    row = blog_service.update_post(db, user=user, post_id=post_id, payload=payload)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.delete(
    "/admin/blog/posts/{post_id}",
    status_code=204,
    response_class=Response,
)
def admin_delete_post(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.delete"))],
) -> Response:
    blog_service.delete_post(db, user=user, post_id=post_id)
    return Response(status_code=204)


@router.post("/admin/blog/posts/{post_id}/publish", response_model=PostAdmin)
def admin_publish(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.publish"))],
) -> PostAdmin:
    row = blog_service.publish_post(db, user=user, post_id=post_id)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.post("/admin/blog/posts/{post_id}/unpublish", response_model=PostAdmin)
def admin_unpublish(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.publish"))],
) -> PostAdmin:
    row = blog_service.unpublish_post(db, user=user, post_id=post_id)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.get("/admin/blog/slug-check", response_model=SlugCheck)
def admin_slug_check(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
    exclude_id: UUID | None = None,
) -> SlugCheck:
    s = blog_service._slugify(slug)
    return SlugCheck(slug=s, available=blog_service.slug_available(db, s, exclude_id=exclude_id))


@router.get("/admin/blog/categories", response_model=list[CategoryPublic])
def admin_categories(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> list[CategoryPublic]:
    return [CategoryPublic.model_validate(r) for r in blog_service.list_categories(db)]


@router.post(
    "/admin/blog/categories",
    response_model=CategoryPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_category(
    payload: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> CategoryPublic:
    return CategoryPublic.model_validate(
        blog_service.create_category(db, user=user, payload=payload)
    )


@router.get("/admin/blog/tags", response_model=list[TagPublic])
def admin_tags(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> list[TagPublic]:
    return [TagPublic.model_validate(r) for r in blog_service.list_tags(db)]


@router.post(
    "/admin/blog/tags",
    response_model=TagPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_tag(
    payload: TagCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> TagPublic:
    return TagPublic.model_validate(blog_service.create_tag(db, user=user, payload=payload))


@router.get("/admin/blog/authors", response_model=list[AuthorPublic])
def admin_authors(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> list[AuthorPublic]:
    return [
        AuthorPublic.model_validate(r)
        for r in blog_service.list_authors(db, active_only=False)
    ]


@router.post(
    "/admin/blog/authors",
    response_model=AuthorPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_author(
    payload: AuthorCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> AuthorPublic:
    return AuthorPublic.model_validate(
        blog_service.create_author(db, user=user, payload=payload)
    )


@router.post("/admin/blog/seed")
def admin_seed(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.create"))],
) -> dict[str, Any]:
    return {"ok": True, **seed_blog_content(db)}


@router.get("/admin/blog/comments", response_model=list[CommentAdmin])
def admin_list_comments(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
    post_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[CommentAdmin]:
    rows = blog_comments.list_admin_comments(
        db, user=user, post_id=post_id, status_filter=status_filter, limit=limit
    )
    return [
        CommentAdmin.model_validate(
            blog_comments.serialize_comment(db, r, viewer=user, admin=True)
        )
        for r in rows
    ]


@router.post("/admin/blog/comments/{comment_id}/hide", response_model=CommentAdmin)
def admin_hide_comment(
    comment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> CommentAdmin:
    row = blog_comments.hide_comment(db, user=user, comment_id=comment_id)
    return CommentAdmin.model_validate(
        blog_comments.serialize_comment(db, row, viewer=user, admin=True)
    )


@router.post("/admin/blog/comments/{comment_id}/restore", response_model=CommentAdmin)
def admin_restore_comment(
    comment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> CommentAdmin:
    row = blog_comments.restore_comment(db, user=user, comment_id=comment_id)
    return CommentAdmin.model_validate(
        blog_comments.serialize_comment(db, row, viewer=user, admin=True)
    )


@router.delete(
    "/admin/blog/comments/{comment_id}",
    status_code=204,
    response_class=Response,
)
def admin_archive_comment(
    comment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> Response:
    blog_comments.archive_comment(db, user=user, comment_id=comment_id)
    return Response(status_code=204)
