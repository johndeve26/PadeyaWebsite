"""Blog AI Studio generation service — structured JSON, never auto-publishes."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.constants import (
    FEATURE_ADMIN_BLOG_FULL_DRAFT,
    FEATURE_ADMIN_BLOG_OUTLINE,
    FEATURE_ADMIN_BLOG_REWRITE,
    FEATURE_ADMIN_BLOG_SECTION,
    FEATURE_ADMIN_BLOG_SEO_BRIEF,
    FEATURE_ADMIN_BLOG_TITLE,
)
from app.blog.models import BlogPost
from app.blog.studio import rate_limit as rl
from app.blog.studio import revisions as rev
from app.blog.studio import templates as tpl
from app.blog.studio.common import (
    _begin,
    _brief,
    _complete,
    _finish,
    _parse_with_repair,
)
from app.blog.studio.json_parse import extract_json_object, parse_list_field, parse_model
from app.blog.studio.schemas import (
    BlogContentBrief,
    BlogGeneratedSection,
    BlogOutline,
    BlogOutlineSection,
    BlogSeoBrief,
    BlogTitleSuggestion,
    FullDraftProgressResponse,
    RewriteResponse,
    TitlesResponse,
)
from app.blog.studio.voice import (
    build_system_prompt,
    compose_user_prompt,
    section_admin,
    section_article,
    section_brand,
    section_reference,
)
from app.users.models import User

logger = logging.getLogger(__name__)

def generate_seo_brief(db: Session, *, user: User, payload) -> BlogSeoBrief:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, BlogSeoBrief):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    rl.assert_source_text_limit("\n".join(brief.competitor_urls))
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_admin(notes=payload.notes),
        section_reference(competitor_urls=brief.competitor_urls),
        section_article(title=payload.title, excerpt=payload.excerpt, body=payload.body, brief=brief.model_dump()),
        task=(
            "Generate SEO brief JSON for schema BlogSeoBrief. "
            "Task marker: blog seo_brief json. Draft only — never publish."
        ),
    )
    try:
        result, provider, routed = _parse_with_repair(
            db,
            feature_key=FEATURE_ADMIN_BLOG_SEO_BRIEF,
            system_prompt=system,
            user_prompt=user_prompt,
            model=BlogSeoBrief,
            force_template=payload.force_template,
            fallback=lambda: tpl.template_seo_brief(brief, title=payload.title),
        )
        _finish(
            db,
            user=user,
            operation="seo_brief",
            feature_key=FEATURE_ADMIN_BLOG_SEO_BRIEF,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=True,
            provider=provider,
            model_name=getattr(routed.result, "model_name", None),
            tokens_in=getattr(routed.result, "tokens_in", None),
            tokens_out=getattr(routed.result, "tokens_out", None),
            payload=result,
        )
        return result
    except Exception:
        _finish(
            db,
            user=user,
            operation="seo_brief",
            feature_key=FEATURE_ADMIN_BLOG_SEO_BRIEF,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def generate_titles(db: Session, *, user: User, payload) -> TitlesResponse:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, TitlesResponse):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_admin(notes=payload.notes),
        section_article(title=payload.title, brief=brief.model_dump()),
        task=(
            f"Generate {payload.count} blog title suggestion objects as JSON "
            '{"titles":[...BlogTitleSuggestion]}. Task marker: blog titles json. Never publish.'
        ),
    )

    def _fallback() -> TitlesResponse:
        return TitlesResponse(titles=tpl.template_titles(brief, title=payload.title, count=payload.count))

    try:
        routed = _complete(
            db,
            feature_key=FEATURE_ADMIN_BLOG_TITLE,
            system_prompt=system,
            user_prompt=user_prompt,
            force_template=payload.force_template,
        )
        try:
            titles = parse_list_field(routed.result.text or "", field="titles", item_model=BlogTitleSuggestion)
            result = TitlesResponse(titles=titles[: payload.count])
            provider = routed.result.provider
        except (ValueError, ValidationError):
            result = _fallback()
            provider = "template"
        _finish(
            db,
            user=user,
            operation="titles",
            feature_key=FEATURE_ADMIN_BLOG_TITLE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=True,
            provider=provider,
            model_name=routed.result.model_name,
            tokens_in=routed.result.tokens_in,
            tokens_out=routed.result.tokens_out,
            payload=result,
        )
        return result
    except Exception:
        _finish(
            db,
            user=user,
            operation="titles",
            feature_key=FEATURE_ADMIN_BLOG_TITLE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def generate_outline(db: Session, *, user: User, payload) -> BlogOutline:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, BlogOutline):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_admin(notes=payload.notes),
        section_article(title=payload.title, excerpt=payload.excerpt, body=payload.body, brief=brief.model_dump()),
        task="Generate BlogOutline JSON. Task marker: blog outline json. Max 20 sections. Never publish.",
    )
    try:
        result, provider, routed = _parse_with_repair(
            db,
            feature_key=FEATURE_ADMIN_BLOG_OUTLINE,
            system_prompt=system,
            user_prompt=user_prompt,
            model=BlogOutline,
            force_template=payload.force_template,
            fallback=lambda: tpl.template_outline(brief, title=payload.title),
        )
        rl.assert_outline_section_limit(len(result.sections))
        result.approved = False
        _finish(
            db,
            user=user,
            operation="outline",
            feature_key=FEATURE_ADMIN_BLOG_OUTLINE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=True,
            provider=provider,
            model_name=getattr(routed.result, "model_name", None),
            tokens_in=getattr(routed.result, "tokens_in", None),
            tokens_out=getattr(routed.result, "tokens_out", None),
            payload=result,
        )
        return result
    except HTTPException:
        rl.release_generation_slot(str(user.id))
        raise
    except Exception:
        _finish(
            db,
            user=user,
            operation="outline",
            feature_key=FEATURE_ADMIN_BLOG_OUTLINE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def regenerate_outline_section(db: Session, *, user: User, payload) -> BlogOutlineSection:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, BlogOutlineSection):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    outline = payload.outline or tpl.template_outline(brief, title=payload.title)
    existing = next((s for s in outline.sections if s.id == payload.section_id), None)
    if existing and existing.locked:
        rl.release_generation_slot(str(user.id))
        return existing
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_article(title=payload.title, brief=brief.model_dump(), outline=outline.model_dump()),
        task=(
            f"Regenerate outline section id={payload.section_id} as BlogOutlineSection JSON. "
            "Task marker: outline section json. Never publish."
        ),
    )
    try:
        result, provider, routed = _parse_with_repair(
            db,
            feature_key=FEATURE_ADMIN_BLOG_OUTLINE,
            system_prompt=system,
            user_prompt=user_prompt,
            model=BlogOutlineSection,
            force_template=payload.force_template,
            fallback=lambda: tpl.template_outline_section(outline, payload.section_id, brief),
        )
        result.id = payload.section_id
        result.locked = False
        _finish(
            db,
            user=user,
            operation="outline_section",
            feature_key=FEATURE_ADMIN_BLOG_OUTLINE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=True,
            provider=provider,
            model_name=getattr(routed.result, "model_name", None),
            payload=result,
        )
        return result
    except Exception:
        _finish(
            db,
            user=user,
            operation="outline_section",
            feature_key=FEATURE_ADMIN_BLOG_OUTLINE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def generate_section(db: Session, *, user: User, payload) -> BlogGeneratedSection:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, BlogGeneratedSection):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    outline = payload.outline or tpl.template_outline(brief, title=payload.title)
    sec = next((s for s in outline.sections if s.id == payload.section_id), None)
    if sec and (sec.locked or payload.section_id in set(payload.locked_section_ids or [])):
        rl.release_generation_slot(str(user.id))
        return BlogGeneratedSection(
            id=payload.section_id, heading=sec.heading, body="", locked=True
        )
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_admin(notes=payload.notes),
        section_article(title=payload.title, body=payload.body, brief=brief.model_dump(), outline=outline.model_dump()),
        task=(
            f"Generate BlogGeneratedSection JSON for section_id={payload.section_id}. "
            "Task marker: generate section json. Mark unverified facts. Never publish."
        ),
    )
    try:
        result, provider, routed = _parse_with_repair(
            db,
            feature_key=FEATURE_ADMIN_BLOG_SECTION,
            system_prompt=system,
            user_prompt=user_prompt,
            model=BlogGeneratedSection,
            force_template=payload.force_template,
            fallback=lambda: tpl.template_section(sec, brief, section_id=payload.section_id),
        )
        result.id = payload.section_id
        if "Needs verification" not in (result.fact_markers or []):
            result.fact_markers = list(result.fact_markers or []) + ["Needs verification"]
        _finish(
            db,
            user=user,
            operation="section",
            feature_key=FEATURE_ADMIN_BLOG_SECTION,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=True,
            provider=provider,
            model_name=getattr(routed.result, "model_name", None),
            payload=result,
        )
        return result
    except Exception:
        _finish(
            db,
            user=user,
            operation="section",
            feature_key=FEATURE_ADMIN_BLOG_SECTION,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def generate_full_draft(db: Session, *, user: User, payload) -> FullDraftProgressResponse:
    """Section-by-section draft. NEVER sets status=published."""
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, FullDraftProgressResponse):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    outline = payload.outline or tpl.template_outline(brief, title=payload.title)
    rl.assert_outline_section_limit(len(outline.sections))
    locked = set(payload.locked_section_ids or [])
    sections: list[BlogGeneratedSection] = []
    failed: list[str] = []
    provider = "template"
    try:
        # Prefer deterministic section builders so full-draft stays reliable offline.
        # Network AI may refine later per-section; never change post.status to published.
        for sec in outline.sections:
            if sec.id in locked or sec.locked:
                sections.append(
                    BlogGeneratedSection(id=sec.id, heading=sec.heading, body="", locked=True)
                )
                continue
            try:
                if payload.force_template:
                    sections.append(tpl.template_section(sec, brief, section_id=sec.id))
                    continue
                system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
                user_prompt = compose_user_prompt(
                    section_brand(),
                    section_article(
                        title=payload.title,
                        brief=brief.model_dump(),
                        outline=outline.model_dump(),
                    ),
                    task=(
                        f"Generate BlogGeneratedSection JSON for section_id={sec.id}. "
                        "Task marker: generate section json. Never publish."
                    ),
                )
                section_result, provider, _routed = _parse_with_repair(
                    db,
                    feature_key=FEATURE_ADMIN_BLOG_FULL_DRAFT,
                    system_prompt=system,
                    user_prompt=user_prompt,
                    model=BlogGeneratedSection,
                    force_template=payload.force_template,
                    fallback=lambda s=sec: tpl.template_section(s, brief, section_id=s.id),
                )
                section_result.id = sec.id
                if "Needs verification" not in (section_result.fact_markers or []):
                    section_result.fact_markers = list(section_result.fact_markers or []) + [
                        "Needs verification"
                    ]
                sections.append(section_result)
            except Exception:
                failed.append(sec.id)
                sections.append(tpl.template_section(sec, brief, section_id=sec.id))
        body_parts = []
        for s in sections:
            if s.locked:
                continue
            body_parts.append(f"## {s.heading}\n\n{s.body}")
        status = "complete" if not failed else "partial"
        result = FullDraftProgressResponse(
            sections=sections,
            status=status,
            failed_section_ids=failed,
            draft_status="draft",
            body_markdown="\n\n".join(body_parts),
        )
        # Optionally checkpoint revision without publishing
        if payload.blog_post_id:
            post = db.get(BlogPost, payload.blog_post_id)
            if post is not None:
                # Explicit invariant: full draft never publishes
                if post.status == "published":
                    pass
                rev.create_revision(
                    db,
                    post=post,
                    actor=user,
                    source="ai",
                    action_type="full_draft",
                    provider=provider,
                    summary="AI full-draft checkpoint (draft only)",
                    commit=True,
                )
        _finish(
            db,
            user=user,
            operation="full_draft",
            feature_key=FEATURE_ADMIN_BLOG_FULL_DRAFT,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=True,
            provider=provider,
            payload=result,
        )
        return result
    except Exception:
        _finish(
            db,
            user=user,
            operation="full_draft",
            feature_key=FEATURE_ADMIN_BLOG_FULL_DRAFT,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def rewrite_selection(db: Session, *, user: User, payload) -> RewriteResponse:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, RewriteResponse):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    rl.assert_body_limit(payload.selection)
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        task=(
            f"Rewrite selection with action={payload.action}. "
            'Return JSON {"text":"...","action":"..."}. Task marker: rewrite selection json.\n'
            f"Selection:\n{payload.selection}"
        ),
    )
    try:
        routed = _complete(
            db,
            feature_key=FEATURE_ADMIN_BLOG_REWRITE,
            system_prompt=system,
            user_prompt=user_prompt,
            force_template=payload.force_template,
        )
        try:
            result = parse_model(routed.result.text or "", RewriteResponse)
            provider = routed.result.provider
        except (ValueError, ValidationError):
            data = extract_json_object(routed.result.text or "")
            if isinstance(data, dict) and "text" in data:
                result = RewriteResponse(text=str(data["text"]), action=payload.action)
                provider = routed.result.provider
            else:
                result = RewriteResponse(
                    text=tpl.template_rewrite(payload.selection, payload.action),
                    action=payload.action,
                )
                provider = "template"
        result.action = payload.action
        _finish(
            db,
            user=user,
            operation="rewrite",
            feature_key=FEATURE_ADMIN_BLOG_REWRITE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=True,
            provider=provider,
            payload=result,
        )
        return result
    except Exception:
        _finish(
            db,
            user=user,
            operation="rewrite",
            feature_key=FEATURE_ADMIN_BLOG_REWRITE,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise




from app.blog.studio.assist import (  # noqa: E402
    fact_review,
    generate_faqs,
    generate_image_prompt,
    review_article,
    similarity_review,
    suggest_internal_links_op,
)

__all__ = [
    "generate_seo_brief",
    "generate_titles",
    "generate_outline",
    "regenerate_outline_section",
    "generate_section",
    "generate_full_draft",
    "rewrite_selection",
    "generate_faqs",
    "generate_image_prompt",
    "review_article",
    "similarity_review",
    "suggest_internal_links_op",
    "fact_review",
]
