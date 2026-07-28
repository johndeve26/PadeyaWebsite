"""Blog AI Studio assist ops — FAQs, review, links, facts, images."""

from __future__ import annotations

import logging
import time

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.constants import (
    FEATURE_ADMIN_BLOG_FACT_REVIEW,
    FEATURE_ADMIN_BLOG_FAQS,
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS,
    FEATURE_ADMIN_BLOG_REVIEW,
    FEATURE_ADMIN_BLOG_SIMILARITY,
)
from app.blog.models import BlogPost
from app.blog.studio import rate_limit as rl
from app.blog.studio import templates as tpl
from app.blog.studio.common import (
    _begin,
    _brief,
    _complete,
    _finish,
    _parse_with_repair,
    _slug_guess,
)
from app.blog.studio.internal_links import suggest_internal_links
from app.blog.studio.json_parse import parse_list_field, parse_model
from app.blog.studio.schemas import (
    BlogFactClaim,
    BlogFaqItem,
    BlogImagePrompt,
    BlogInternalLinkSuggestion,
    BlogQualityReview,
    BlogSimilarityReview,
    FactReviewResponse,
    FaqsResponse,
    InternalLinksResponse,
)
from app.blog.studio.voice import (
    build_system_prompt,
    compose_user_prompt,
    section_article,
    section_brand,
)
from app.users.models import User

logger = logging.getLogger(__name__)

def generate_faqs(db: Session, *, user: User, payload) -> FaqsResponse:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, FaqsResponse):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_article(title=payload.title, body=payload.body, brief=brief.model_dump()),
        task='Generate FAQ JSON {"faqs":[...BlogFaqItem]}. Task marker: faq json. Never publish.',
    )
    try:
        routed = _complete(
            db,
            feature_key=FEATURE_ADMIN_BLOG_FAQS,
            system_prompt=system,
            user_prompt=user_prompt,
            force_template=payload.force_template,
        )
        try:
            faqs = parse_list_field(routed.result.text or "", field="faqs", item_model=BlogFaqItem)
            result = FaqsResponse(faqs=faqs[: payload.count])
            provider = routed.result.provider
        except (ValueError, ValidationError):
            result = FaqsResponse(faqs=tpl.template_faqs(brief, count=payload.count))
            provider = "template"
        _finish(
            db,
            user=user,
            operation="faqs",
            feature_key=FEATURE_ADMIN_BLOG_FAQS,
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
            operation="faqs",
            feature_key=FEATURE_ADMIN_BLOG_FAQS,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def generate_image_prompt(db: Session, *, user: User, payload) -> BlogImagePrompt:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, BlogImagePrompt):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_article(title=payload.title, brief=brief.model_dump()),
        task="Generate BlogImagePrompt JSON. Task marker: image prompt json.",
    )
    try:
        result, provider, routed = _parse_with_repair(
            db,
            feature_key=FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
            system_prompt=system,
            user_prompt=user_prompt,
            model=BlogImagePrompt,
            force_template=payload.force_template,
            fallback=lambda: tpl.template_image_prompt(brief, title=payload.title),
        )
        _finish(
            db,
            user=user,
            operation="image_prompt",
            feature_key=FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
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
            operation="image_prompt",
            feature_key=FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def review_article(db: Session, *, user: User, payload) -> BlogQualityReview:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, BlogQualityReview):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    rl.assert_body_limit(payload.body)
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_article(title=payload.title, body=payload.body, brief=brief.model_dump()),
        task="Generate BlogQualityReview JSON. Task marker: review article json.",
    )
    try:
        result, provider, routed = _parse_with_repair(
            db,
            feature_key=FEATURE_ADMIN_BLOG_REVIEW,
            system_prompt=system,
            user_prompt=user_prompt,
            model=BlogQualityReview,
            force_template=payload.force_template,
            fallback=lambda: tpl.template_review(body=payload.body),
        )
        _finish(
            db,
            user=user,
            operation="review",
            feature_key=FEATURE_ADMIN_BLOG_REVIEW,
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
            operation="review",
            feature_key=FEATURE_ADMIN_BLOG_REVIEW,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise


def similarity_review(db: Session, *, user: User, payload) -> BlogSimilarityReview:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, BlogSimilarityReview):
        return cached
    started = time.monotonic()
    # Prefer deterministic inventory-based similarity; AI optional enrichment via template
    from sqlalchemy import select

    rows = db.scalars(
        select(BlogPost).where(
            BlogPost.status == "published",
            BlogPost.archived_at.is_(None),
        ).limit(20)
    ).all()
    title = (payload.title or "").strip().lower()
    similar = []
    conflicts = []
    for row in rows:
        if payload.blog_post_id and row.id == payload.blog_post_id:
            continue
        if title and title in (row.title or "").lower():
            similar.append(
                {
                    "post_id": str(row.id),
                    "title": row.title,
                    "slug": row.slug,
                    "url": f"/blog/{row.slug}",
                    "overlap_note": "Similar title",
                }
            )
        if payload.title and _slug_guess(payload.title) == row.slug:
            conflicts.append(row.slug)
    result = BlogSimilarityReview(
        duplicated_headings=[],
        repeated_paragraphs=[],
        similar_posts=similar,
        cannibalization_risks=[],
        conflicting_slugs=conflicts,
    )
    _finish(
        db,
        user=user,
        operation="similarity",
        feature_key=FEATURE_ADMIN_BLOG_SIMILARITY,
        started=started,
        client_request_id=payload.client_request_id,
        post_id=payload.blog_post_id,
        success=True,
        provider="local",
        payload=result,
    )
    return result


def suggest_internal_links_op(db: Session, *, user: User, payload) -> InternalLinksResponse:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, InternalLinksResponse):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    query = brief.primary_keyword or brief.topic or payload.title
    raw = suggest_internal_links(db, query=query, exclude_post_id=payload.blog_post_id)
    links = [
        BlogInternalLinkSuggestion.model_validate(x)
        for x in tpl.template_internal_links(raw)
    ]
    # Hard filter — only real absolute-path URLs
    links = [ln for ln in links if ln.target_url.startswith("/") and "://" not in ln.target_url]
    result = InternalLinksResponse(links=links)
    _finish(
        db,
        user=user,
        operation="internal_links",
        feature_key=FEATURE_ADMIN_BLOG_INTERNAL_LINKS,
        started=started,
        client_request_id=payload.client_request_id,
        post_id=payload.blog_post_id,
        success=True,
        provider="local",
        payload=result,
    )
    return result


def fact_review(db: Session, *, user: User, payload) -> FactReviewResponse:
    cached = _begin(user, payload.client_request_id)
    if isinstance(cached, FactReviewResponse):
        return cached
    started = time.monotonic()
    brief = _brief(payload.brief)
    system = build_system_prompt(tone=brief.tone, custom_tone=brief.custom_tone)
    user_prompt = compose_user_prompt(
        section_brand(),
        section_article(title=payload.title, body=payload.body, brief=brief.model_dump()),
        task=(
            'Generate fact review JSON {"claims":[...BlogFactClaim]}. '
            "Never invent verified citations. Task marker: fact review json."
        ),
    )
    try:
        routed = _complete(
            db,
            feature_key=FEATURE_ADMIN_BLOG_FACT_REVIEW,
            system_prompt=system,
            user_prompt=user_prompt,
            force_template=payload.force_template,
        )
        try:
            claims = parse_list_field(
                routed.result.text or "", field="claims", item_model=BlogFactClaim
            )
            provider = routed.result.provider
        except (ValueError, ValidationError):
            claims = tpl.template_fact_review(body=payload.body)
            provider = "template"
        # Enforce safety: always Needs verification + source_required
        cleaned: list[BlogFactClaim] = []
        for c in claims:
            cleaned.append(
                BlogFactClaim(
                    claim=c.claim,
                    section=c.section,
                    confidence="low" if c.confidence == "high" else c.confidence,
                    source_required=True,
                    review_status="Needs verification",
                    source_urls=[],  # never invent sources
                )
            )
        result = FactReviewResponse(claims=cleaned)
        _finish(
            db,
            user=user,
            operation="fact_review",
            feature_key=FEATURE_ADMIN_BLOG_FACT_REVIEW,
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
            operation="fact_review",
            feature_key=FEATURE_ADMIN_BLOG_FACT_REVIEW,
            started=started,
            client_request_id=payload.client_request_id,
            post_id=payload.blog_post_id,
            success=False,
            error_code="generation_failed",
        )
        raise
