"""Blog AI Studio admin API routes — structured JSON, never auto-publish."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.blog import service as blog_service
from app.blog.document.sync import apply_autosave_content
from app.blog.models import BlogPost
from app.blog.schemas import PostAdmin
from app.blog.studio import operations as ops
from app.blog.studio import revisions as rev
from app.blog.studio import service as studio
from app.blog.studio.rate_limit import assert_body_limit
from app.blog.studio.schemas import (
    BlogAiOperationPublic,
    BlogGeneratedSection,
    BlogImagePrompt,
    BlogOutline,
    BlogOutlineSection,
    BlogQualityReview,
    BlogRevisionPublic,
    BlogSeoBrief,
    BlogSeoScore,
    BlogSimilarityReview,
    CheckpointRequest,
    FactReviewRequest,
    FactReviewResponse,
    FaqsRequest,
    FaqsResponse,
    FullDraftProgressResponse,
    FullDraftRequest,
    ImagePromptRequest,
    InternalLinksRequest,
    InternalLinksResponse,
    OutlineRequest,
    OutlineSectionRequest,
    ReviewRequest,
    RewriteRequest,
    RewriteResponse,
    SectionRequest,
    SeoBriefRequest,
    SeoScoreRequest,
    SimilarityRequest,
    StudioAutosaveRequest,
    TitlesRequest,
    TitlesResponse,
)
from app.blog.studio.seo_score import compute_seo_score
from app.core.database import get_db
from app.core.http_errors import raise_not_found
from app.users.models import User

router = APIRouter(tags=["blog-ai-studio"])


@router.post("/admin/blog/ai/seo-brief", response_model=BlogSeoBrief)
def ai_seo_brief(
    payload: SeoBriefRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> BlogSeoBrief:
    return studio.generate_seo_brief(db, user=user, payload=payload)


@router.post("/admin/blog/ai/titles", response_model=TitlesResponse)
def ai_titles(
    payload: TitlesRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TitlesResponse:
    return studio.generate_titles(db, user=user, payload=payload)


@router.post("/admin/blog/ai/outline", response_model=BlogOutline)
def ai_outline(
    payload: OutlineRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> BlogOutline:
    return studio.generate_outline(db, user=user, payload=payload)


@router.post("/admin/blog/ai/outline/section", response_model=BlogOutlineSection)
def ai_outline_section(
    payload: OutlineSectionRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> BlogOutlineSection:
    return studio.regenerate_outline_section(db, user=user, payload=payload)


@router.post("/admin/blog/ai/section", response_model=BlogGeneratedSection)
def ai_section(
    payload: SectionRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> BlogGeneratedSection:
    return studio.generate_section(db, user=user, payload=payload)


@router.post("/admin/blog/ai/full-draft", response_model=FullDraftProgressResponse)
def ai_full_draft(
    payload: FullDraftRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> FullDraftProgressResponse:
    result = studio.generate_full_draft(db, user=user, payload=payload)
    # Invariant: never publish
    if result.draft_status != "draft":
        result.draft_status = "draft"
    return result


@router.post("/admin/blog/ai/rewrite", response_model=RewriteResponse)
def ai_rewrite(
    payload: RewriteRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> RewriteResponse:
    return studio.rewrite_selection(db, user=user, payload=payload)


@router.post("/admin/blog/ai/review", response_model=BlogQualityReview)
def ai_review(
    payload: ReviewRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> BlogQualityReview:
    return studio.review_article(db, user=user, payload=payload)


@router.post("/admin/blog/ai/similarity", response_model=BlogSimilarityReview)
def ai_similarity(
    payload: SimilarityRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> BlogSimilarityReview:
    return studio.similarity_review(db, user=user, payload=payload)


@router.post("/admin/blog/ai/faqs", response_model=FaqsResponse)
def ai_faqs(
    payload: FaqsRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> FaqsResponse:
    return studio.generate_faqs(db, user=user, payload=payload)


@router.post("/admin/blog/ai/image-prompt", response_model=BlogImagePrompt)
def ai_image_prompt(
    payload: ImagePromptRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> BlogImagePrompt:
    return studio.generate_image_prompt(db, user=user, payload=payload)


@router.post("/admin/blog/ai/internal-links", response_model=InternalLinksResponse)
def ai_internal_links(
    payload: InternalLinksRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> InternalLinksResponse:
    return studio.suggest_internal_links_op(db, user=user, payload=payload)


@router.post("/admin/blog/ai/fact-review", response_model=FactReviewResponse)
def ai_fact_review(
    payload: FactReviewRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> FactReviewResponse:
    return studio.fact_review(db, user=user, payload=payload)


@router.post("/admin/blog/ai/seo-score", response_model=BlogSeoScore)
def ai_seo_score(
    payload: SeoScoreRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> BlogSeoScore:
    _ = user
    if payload.blog_post_id:
        post = db.get(BlogPost, payload.blog_post_id)
        if post is None:
            raise_not_found()
        payload = SeoScoreRequest(
            title=payload.title or post.title,
            seo_title=payload.seo_title or post.seo_title,
            seo_description=payload.seo_description or post.seo_description,
            slug=payload.slug or post.slug,
            body=payload.body if payload.body is not None else post.body,
            focus_keyword=payload.focus_keyword or post.focus_keyword,
            cover_url=payload.cover_url or post.cover_url,
            blog_post_id=payload.blog_post_id,
        )
    return compute_seo_score(payload)


@router.get(
    "/admin/blog/posts/{post_id}/revisions",
    response_model=list[BlogRevisionPublic],
)
def list_post_revisions(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> list[BlogRevisionPublic]:
    _ = user
    rows = rev.list_revisions(db, post_id=post_id)
    return [BlogRevisionPublic.model_validate(rev.serialize_revision(r)) for r in rows]


@router.get(
    "/admin/blog/posts/{post_id}/revisions/{revision_id}",
    response_model=BlogRevisionPublic,
)
def get_post_revision(
    post_id: UUID,
    revision_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> BlogRevisionPublic:
    _ = user
    row = rev.get_revision(db, post_id=post_id, revision_id=revision_id)
    return BlogRevisionPublic.model_validate(rev.serialize_revision(row))


@router.post(
    "/admin/blog/posts/{post_id}/revisions/{revision_id}/restore",
    response_model=PostAdmin,
)
def restore_post_revision(
    post_id: UUID,
    revision_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> PostAdmin:
    row = rev.restore_revision(db, user=user, post_id=post_id, revision_id=revision_id)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.post(
    "/admin/blog/posts/{post_id}/revisions/checkpoint",
    response_model=BlogRevisionPublic,
)
def checkpoint_revision(
    post_id: UUID,
    payload: CheckpointRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> BlogRevisionPublic:
    post = blog_service.get_admin_post(db, user=user, post_id=post_id)
    row = rev.create_revision(
        db,
        post=post,
        actor=user,
        source="manual",
        action_type="checkpoint",
        summary=payload.summary,
        commit=True,
    )
    return BlogRevisionPublic.model_validate(rev.serialize_revision(row))


@router.get(
    "/admin/blog/posts/{post_id}/ai-operations",
    response_model=list[BlogAiOperationPublic],
)
def list_ai_operations(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> list[BlogAiOperationPublic]:
    _ = user
    rows = ops.list_operations(db, post_id=post_id)
    return [
        BlogAiOperationPublic.model_validate(ops.serialize_operation(r)) for r in rows
    ]


@router.post("/admin/blog/posts/{post_id}/autosave", response_model=PostAdmin)
def autosave_post(
    post_id: UUID,
    payload: StudioAutosaveRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> PostAdmin:
    post = db.get(BlogPost, post_id)
    if post is None or post.archived_at is not None:
        raise_not_found()
    rev.assert_version_match(post, payload.expected_content_version)
    assert_body_limit(payload.body)
    if payload.title is not None:
        post.title = payload.title.strip()
    if payload.excerpt is not None:
        post.excerpt = payload.excerpt

    apply_autosave_content(
        post,
        body=payload.body,
        content_document=payload.content_document,
    )

    if payload.seo_title is not None:
        post.seo_title = payload.seo_title
    if payload.seo_description is not None:
        post.seo_description = payload.seo_description
    if payload.studio_brief is not None:
        post.studio_brief = payload.studio_brief
    if payload.studio_outline is not None:
        post.studio_outline = payload.studio_outline
    if payload.faqs is not None:
        post.faqs = payload.faqs
    if payload.focus_keyword is not None:
        post.focus_keyword = payload.focus_keyword
    if payload.secondary_keywords is not None:
        post.secondary_keywords = payload.secondary_keywords
    if payload.social_share_text is not None:
        post.social_share_text = payload.social_share_text
    if payload.og_title is not None:
        post.og_title = payload.og_title
    if payload.hero_settings is not None:
        from app.blog.document.validation import validate_hero_settings, DocumentValidationError
        from fastapi import HTTPException

        try:
            post.hero_settings = validate_hero_settings(payload.hero_settings)
        except DocumentValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc
    if payload.editor_mode is not None:
        post.editor_mode = payload.editor_mode
    post.content_version = int(post.content_version or 1) + 1
    post.updated_by = user.id
    # Never change status via autosave
    db.commit()
    row = blog_service.get_admin_post(db, user=user, post_id=post_id)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.get("/admin/blog/preview/{post_id}", response_model=PostAdmin)
def admin_preview_post(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> PostAdmin:
    row = blog_service.get_admin_post(db, user=user, post_id=post_id)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))
