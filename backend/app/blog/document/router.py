"""Blog document API — structured content CRUD, templates, reusable sections."""

from __future__ import annotations

import copy
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.blog import service as blog_service
from app.blog.document.conversion import (
    blank_document,
    convert_legacy_markdown,
    document_has_legacy_only,
    new_block_id,
    wrap_legacy_body,
)
from app.blog.document.render import document_to_markdown
from app.blog.document.sync import apply_content_document, resolve_content_mode
from app.blog.document.templates import BUILTIN_REUSABLE_SECTIONS, BUILTIN_TEMPLATES
from app.blog.document.validation import (
    DocumentValidationError,
    validate_document,
    validate_document_or_http,
    validate_hero_settings,
)
from app.blog.markdown import estimate_reading_minutes
from app.blog.models import BlogLayoutTemplate, BlogPost, BlogReusableSection
from app.blog.schemas import PostAdmin
from app.blog.studio import revisions as rev
from app.core.database import get_db
from app.core.http_errors import raise_not_found
from app.users.models import User

router = APIRouter(tags=["blog-document"])


class DocumentPatchRequest(BaseModel):
    content_document: dict[str, Any]
    hero_settings: dict[str, Any] | None = None
    editor_mode: str | None = None
    expected_content_version: int
    sync_body_markdown: bool = True


class DocumentValidateRequest(BaseModel):
    content_document: dict[str, Any]


class DocumentValidateResponse(BaseModel):
    valid: bool
    document: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)


class DocumentConvertResponse(BaseModel):
    content_document: dict[str, Any]
    warning: str | None = None
    revision_id: uuid.UUID | None = None


class LayoutTemplatePublic(BaseModel):
    id: uuid.UUID | None = None
    name: str
    slug: str
    description: str | None = None
    category: str = "general"
    document: dict[str, Any]
    hero_settings: dict[str, Any] | None = None
    is_builtin: bool = False


class ReusableSectionPublic(BaseModel):
    id: uuid.UUID | None = None
    name: str
    slug: str
    description: str | None = None
    section: dict[str, Any]
    is_archived: bool = False


class LayoutTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=180)
    description: str | None = None
    category: str = "general"
    document: dict[str, Any]
    hero_settings: dict[str, Any] | None = None


class ReusableSectionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=180)
    description: str | None = None
    section: dict[str, Any]


def _clone_block_ids(block: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy a block tree with fresh IDs (for template/section insert)."""
    out = copy.deepcopy(block)
    out["id"] = new_block_id()

    def _walk(node: dict[str, Any]) -> None:
        node["id"] = new_block_id()
        for child in node.get("children") or []:
            _walk(child)

    for child in out.get("children") or []:
        _walk(child)
    return out


def _clone_document(doc: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(doc)
    out["blocks"] = [_clone_block_ids(b) for b in out.get("blocks") or []]
    return out


@router.get("/admin/blog/posts/{post_id}/document")
def get_post_document(
    post_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> dict[str, Any]:
    _ = user
    post = db.get(BlogPost, post_id)
    if post is None or post.archived_at is not None:
        raise_not_found()
    doc = post.content_document
    if doc is None and post.body:
        doc = wrap_legacy_body(post.body)
    elif doc is None:
        doc = blank_document()
    return {
        "content_document": doc,
        "content_document_version": int(post.content_document_version or 1),
        "content_version": int(post.content_version or 1),
        "content_mode": resolve_content_mode(post),
        "editor_mode": post.editor_mode,
        "hero_settings": post.hero_settings,
        "has_legacy_body_only": post.content_document is None and bool(post.body),
    }


@router.patch("/admin/blog/posts/{post_id}/document", response_model=PostAdmin)
def patch_post_document(
    post_id: uuid.UUID,
    payload: DocumentPatchRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> PostAdmin:
    post = db.get(BlogPost, post_id)
    if post is None or post.archived_at is not None:
        raise_not_found()
    rev.assert_version_match(post, payload.expected_content_version)

    doc = validate_document_or_http(payload.content_document)
    hero = None
    if payload.hero_settings is not None:
        try:
            hero = validate_hero_settings(payload.hero_settings)
        except DocumentValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc
    if payload.editor_mode is not None and payload.editor_mode not in ("standard", "layout"):
        raise HTTPException(status_code=422, detail="Invalid editor_mode")

    apply_content_document(
        post,
        doc,
        editor_mode=payload.editor_mode,
        hero_settings=hero,
    )
    post.content_version = int(post.content_version or 1) + 1
    post.updated_by = user.id
    db.commit()
    row = blog_service.get_admin_post(db, user=user, post_id=post_id)
    return PostAdmin.model_validate(blog_service.serialize_post(row, admin=True))


@router.post("/admin/blog/posts/{post_id}/document/validate", response_model=DocumentValidateResponse)
def validate_post_document(
    post_id: uuid.UUID,
    payload: DocumentValidateRequest,
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> DocumentValidateResponse:
    _ = post_id
    _ = user
    try:
        doc = validate_document(payload.content_document)
        return DocumentValidateResponse(valid=True, document=doc)
    except DocumentValidationError as exc:
        return DocumentValidateResponse(valid=False, errors=[exc.message])


@router.post("/admin/blog/posts/{post_id}/document/convert", response_model=DocumentConvertResponse)
def convert_post_document(
    post_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> DocumentConvertResponse:
    post = db.get(BlogPost, post_id)
    if post is None or post.archived_at is not None:
        raise_not_found()

    warning = None
    if post.content_document and not document_has_legacy_only(post.content_document):
        raise HTTPException(status_code=409, detail="Post already uses block editor")

    revision = rev.create_revision(
        db,
        post=post,
        actor=user,
        source="manual",
        action_type="pre_layout_conversion",
        summary="Checkpoint before legacy-to-block conversion",
        commit=False,
    )

    if post.content_document and document_has_legacy_only(post.content_document):
        doc = convert_legacy_markdown(
            (post.content_document.get("blocks") or [{}])[0]
            .get("content", {})
            .get("markdown", post.body or "")
        )
        warning = "Converted from legacy_rich_text wrapper."
    else:
        doc = convert_legacy_markdown(post.body or "")
        warning = "Converted markdown body to block structure. Review layout before publishing."

    doc = validate_document(doc)
    apply_content_document(post, doc)
    post.content_version = int(post.content_version or 1) + 1
    post.updated_by = user.id
    db.commit()
    db.refresh(revision)
    return DocumentConvertResponse(
        content_document=doc,
        warning=warning,
        revision_id=revision.id,
    )


@router.get("/admin/blog/layout-templates", response_model=list[LayoutTemplatePublic])
def list_layout_templates(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> list[LayoutTemplatePublic]:
    _ = user
    rows = db.scalars(
        select(BlogLayoutTemplate)
        .where(BlogLayoutTemplate.is_archived.is_(False))
        .order_by(BlogLayoutTemplate.name)
    ).all()
    out = [
        LayoutTemplatePublic(
            id=r.id,
            name=r.name,
            slug=r.slug,
            description=r.description,
            category=r.category,
            document=r.document,
            hero_settings=r.hero_settings,
            is_builtin=r.is_builtin,
        )
        for r in rows
    ]
    if not out:
        out = [
            LayoutTemplatePublic(
                name=t["name"],
                slug=t["slug"],
                description=t.get("description"),
                category=t.get("category", "general"),
                document=t["document"],
                hero_settings=t.get("hero_settings"),
                is_builtin=True,
            )
            for t in BUILTIN_TEMPLATES
        ]
    return out


@router.post("/admin/blog/layout-templates", response_model=LayoutTemplatePublic)
def create_layout_template(
    payload: LayoutTemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> LayoutTemplatePublic:
    doc = validate_document_or_http(payload.document)
    slug = payload.slug or blog_service._slugify(payload.name)  # noqa: SLF001
    existing = db.scalar(select(BlogLayoutTemplate).where(BlogLayoutTemplate.slug == slug))
    if existing:
        raise HTTPException(status_code=409, detail="Template slug already exists")
    row = BlogLayoutTemplate(
        name=payload.name,
        slug=slug,
        description=payload.description,
        category=payload.category,
        document=doc,
        hero_settings=payload.hero_settings,
        is_builtin=False,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return LayoutTemplatePublic(
        id=row.id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        category=row.category,
        document=row.document,
        hero_settings=row.hero_settings,
        is_builtin=False,
    )


@router.get("/admin/blog/reusable-sections", response_model=list[ReusableSectionPublic])
def list_reusable_sections(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.view"))],
) -> list[ReusableSectionPublic]:
    _ = user
    rows = db.scalars(
        select(BlogReusableSection)
        .where(BlogReusableSection.is_archived.is_(False))
        .order_by(BlogReusableSection.name)
    ).all()
    out = [
        ReusableSectionPublic(
            id=r.id,
            name=r.name,
            slug=r.slug,
            description=r.description,
            section=r.section,
        )
        for r in rows
    ]
    if not out:
        out = [
            ReusableSectionPublic(
                name=s["name"],
                slug=s["slug"],
                description=s.get("description"),
                section=s["section"],
            )
            for s in BUILTIN_REUSABLE_SECTIONS
        ]
    return out


@router.post("/admin/blog/reusable-sections", response_model=ReusableSectionPublic)
def create_reusable_section(
    payload: ReusableSectionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.blog.edit"))],
) -> ReusableSectionPublic:
    section = payload.section
    if not isinstance(section, dict):
        raise HTTPException(status_code=422, detail="section must be an object")
    slug = payload.slug or blog_service._slugify(payload.name)  # noqa: SLF001
    existing = db.scalar(
        select(BlogReusableSection).where(BlogReusableSection.slug == slug)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Section slug already exists")
    row = BlogReusableSection(
        name=payload.name,
        slug=slug,
        description=payload.description,
        section=section,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReusableSectionPublic(
        id=row.id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        section=row.section,
    )


def clone_template_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Public helper for seeding new posts from templates."""
    return validate_document(_clone_document(doc))
