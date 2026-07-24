"""Public Help Center + admin Knowledge Base API routes."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional, require_permission
from app.core.database import get_db
from app.knowledge_base import service as kb_service
from app.knowledge_base.schemas import (
    ArticleAdmin,
    ArticleCreate,
    ArticleListItem,
    ArticlePublic,
    ArticleUpdate,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    FeedbackCreate,
)
from app.knowledge_base.seed import seed_knowledge_base
from app.users.models import User

router = APIRouter(tags=["knowledge-base"])


# --- Public Help Center ---


@router.get("/help/articles", response_model=list[ArticleListItem])
def public_list_articles(
    db: Annotated[Session, Depends(get_db)],
    category: str | None = None,
    tag: str | None = None,
    audience: str | None = None,
    featured: bool | None = None,
    popular: bool = Query(default=False),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> list[ArticleListItem]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _load() -> list[ArticleListItem]:
        rows = kb_service.list_public_articles(
            db,
            category_slug=category,
            tag_slug=tag,
            audience=audience,
            featured=featured,
            popular=popular,
            q=q,
            limit=limit,
            user_id=user.id if user else None,
        )
        return [
            ArticleListItem.model_validate(kb_service.serialize_article(r))
            for r in rows
        ]

    # Authenticated searches may record personalization — skip shared cache.
    if user is not None:
        return _load()

    key = cache_key(
        "help",
        "articles",
        category=category,
        tag=tag,
        audience=audience,
        featured=featured,
        popular=popular,
        q=q,
        limit=limit,
    )

    def _produce() -> list[dict]:
        return [row.model_dump(mode="json") for row in _load()]

    cached = get_or_set(key, CacheTTL.content, _produce)
    return [ArticleListItem.model_validate(row) for row in cached]


@router.get("/help/articles/{slug}", response_model=ArticlePublic)
def public_article_detail(
    slug: str, db: Annotated[Session, Depends(get_db)]
) -> ArticlePublic:
    from app.core.cache import CacheTTL, cache_get, cache_key, cache_set

    key = cache_key("help", "article", slug)
    hit = cache_get(key)
    if hit is not None:
        return ArticlePublic.model_validate(hit)

    row = kb_service.get_public_article(db, slug)
    related = kb_service.related_articles(db, row)
    payload = ArticlePublic.model_validate(
        kb_service.serialize_article(row, related=related)
    )
    cache_set(key, payload.model_dump(mode="json"), CacheTTL.content)
    return payload


@router.get("/help/categories", response_model=list[CategoryPublic])
def public_categories(
    db: Annotated[Session, Depends(get_db)],
) -> list[CategoryPublic]:
    from app.core.cache import CacheTTL, cache_key, get_or_set

    def _produce() -> list[dict]:
        return [
            CategoryPublic.model_validate(c).model_dump(mode="json")
            for c in kb_service.list_categories(db)
        ]

    cached = get_or_set(cache_key("help", "categories"), CacheTTL.taxonomy, _produce)
    return [CategoryPublic.model_validate(row) for row in cached]


@router.get("/help/categories/{slug}", response_model=CategoryPublic)
def public_category(
    slug: str, db: Annotated[Session, Depends(get_db)]
) -> CategoryPublic:
    row = kb_service.get_category_by_slug(db, slug)
    counts = {
        c["slug"]: c["article_count"] for c in kb_service.list_categories(db)
    }
    return CategoryPublic.model_validate(
        {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "description": row.description,
            "group_key": row.group_key,
            "sort_order": row.sort_order,
            "icon_key": row.icon_key,
            "article_count": int(counts.get(row.slug, 0)),
        }
    )


@router.post("/help/articles/{article_id}/feedback")
def public_feedback(
    article_id: UUID,
    payload: FeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> dict[str, Any]:
    return kb_service.submit_feedback(
        db,
        article_id=article_id,
        is_helpful=payload.is_helpful,
        comment=payload.comment,
        user_id=user.id if user else None,
    )


# --- Admin Knowledge Base ---


@router.get("/admin/knowledge-base/articles", response_model=list[ArticleAdmin])
def admin_list_articles(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.knowledge_base.view"))],
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ArticleAdmin]:
    _ = user
    rows = kb_service.list_admin_articles(
        db, status=status_filter, q=q, limit=limit
    )
    return [
        ArticleAdmin.model_validate(kb_service.serialize_article(r, admin=True))
        for r in rows
    ]


@router.get(
    "/admin/knowledge-base/articles/{article_id}",
    response_model=ArticleAdmin,
)
def admin_get_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.knowledge_base.view"))],
) -> ArticleAdmin:
    _ = user
    row = kb_service.get_admin_article(db, article_id)
    return ArticleAdmin.model_validate(
        kb_service.serialize_article(row, admin=True)
    )


@router.post(
    "/admin/knowledge-base/articles",
    response_model=ArticleAdmin,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_article(
    payload: ArticleCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.knowledge_base.create"))],
) -> ArticleAdmin:
    row = kb_service.create_article(db, payload=payload, actor=user)
    row = kb_service.get_admin_article(db, row.id)
    return ArticleAdmin.model_validate(
        kb_service.serialize_article(row, admin=True)
    )


@router.patch(
    "/admin/knowledge-base/articles/{article_id}",
    response_model=ArticleAdmin,
)
def admin_update_article(
    article_id: UUID,
    payload: ArticleUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.knowledge_base.edit"))],
) -> ArticleAdmin:
    row = kb_service.update_article(
        db, article_id=article_id, payload=payload, actor=user
    )
    row = kb_service.get_admin_article(db, row.id)
    return ArticleAdmin.model_validate(
        kb_service.serialize_article(row, admin=True)
    )


@router.delete(
    "/admin/knowledge-base/articles/{article_id}",
    status_code=204,
    response_class=Response,
)
def admin_delete_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.knowledge_base.archive"))
    ],
) -> Response:
    kb_service.delete_article(db, article_id=article_id, actor=user)
    return Response(status_code=204)


@router.post(
    "/admin/knowledge-base/articles/{article_id}/publish",
    response_model=ArticleAdmin,
)
def admin_publish_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.knowledge_base.publish"))
    ],
) -> ArticleAdmin:
    row = kb_service.publish_article(db, article_id=article_id, actor=user)
    row = kb_service.get_admin_article(db, row.id)
    return ArticleAdmin.model_validate(
        kb_service.serialize_article(row, admin=True)
    )


@router.post(
    "/admin/knowledge-base/articles/{article_id}/archive",
    response_model=ArticleAdmin,
)
def admin_archive_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.knowledge_base.archive"))
    ],
) -> ArticleAdmin:
    row = kb_service.archive_article(db, article_id=article_id, actor=user)
    row = kb_service.get_admin_article(db, row.id)
    return ArticleAdmin.model_validate(
        kb_service.serialize_article(row, admin=True)
    )


@router.post(
    "/admin/knowledge-base/articles/{article_id}/unpublish",
    response_model=ArticleAdmin,
)
def admin_unpublish_article(
    article_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.knowledge_base.publish"))
    ],
) -> ArticleAdmin:
    row = kb_service.unpublish_article(db, article_id=article_id, actor=user)
    row = kb_service.get_admin_article(db, row.id)
    return ArticleAdmin.model_validate(
        kb_service.serialize_article(row, admin=True)
    )


@router.get("/admin/knowledge-base/feedback")
def admin_feedback(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.knowledge_base.view"))],
    article_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[dict[str, Any]]:
    _ = user
    return kb_service.list_feedback(db, article_id=article_id, limit=limit)


@router.get("/admin/knowledge-base/search-terms")
def admin_search_terms(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.knowledge_base.view"))],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    _ = user
    return kb_service.list_search_terms(db, limit=limit)


@router.get("/help/suggestions")
def public_topic_suggestions(
    db: Annotated[Session, Depends(get_db)],
    topic: str = Query(min_length=2, max_length=64),
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    rows = kb_service.suggestions_for_topic(db, topic=topic, limit=limit)
    return {
        "topic": topic,
        "articles": [
            ArticleListItem.model_validate(kb_service.serialize_article(r))
            for r in rows
        ],
    }


@router.get(
    "/admin/knowledge-base/categories",
    response_model=list[CategoryPublic],
)
def admin_list_categories(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.knowledge_base.view"))],
    include_archived: bool = Query(default=False),
) -> list[CategoryPublic]:
    _ = user
    return [
        CategoryPublic.model_validate(c)
        for c in kb_service.list_categories(db, include_archived=include_archived)
    ]


@router.post(
    "/admin/knowledge-base/categories",
    response_model=CategoryPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_category(
    payload: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("admin.knowledge_base.manage_categories")),
    ],
) -> CategoryPublic:
    row = kb_service.create_category(db, payload=payload, actor=user)
    return CategoryPublic.model_validate(
        {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "description": row.description,
            "group_key": row.group_key,
            "sort_order": row.sort_order,
            "icon_key": row.icon_key,
            "article_count": 0,
        }
    )


@router.patch(
    "/admin/knowledge-base/categories/{category_id}",
    response_model=CategoryPublic,
)
def admin_update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("admin.knowledge_base.manage_categories")),
    ],
) -> CategoryPublic:
    row = kb_service.update_category(
        db, category_id=category_id, payload=payload, actor=user
    )
    return CategoryPublic.model_validate(
        {
            "id": row.id,
            "name": row.name,
            "slug": row.slug,
            "description": row.description,
            "group_key": row.group_key,
            "sort_order": row.sort_order,
            "icon_key": row.icon_key,
            "article_count": 0,
        }
    )


@router.post("/admin/knowledge-base/seed")
def admin_seed(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.knowledge_base.create"))
    ],
) -> dict[str, Any]:
    _ = user
    return {"ok": True, **seed_knowledge_base(db)}
