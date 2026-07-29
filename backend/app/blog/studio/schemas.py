"""Pydantic models for Pàdéyá Blog AI Studio."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BlogContentBrief(BaseModel):
    topic: str = ""
    primary_keyword: str = ""
    secondary_keywords: list[str] = Field(default_factory=list)
    target_audience: str = ""
    search_intent: str = ""
    article_objective: str = ""
    content_type: str = "guide"
    tone: str = "practical"
    custom_tone: str | None = None
    desired_length: str = "medium"
    location_focus: str | None = None
    event_category: str | None = None
    competitor_urls: list[str] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    points_to_avoid: list[str] = Field(default_factory=list)
    call_to_action: str | None = None


class BlogSeoBrief(BaseModel):
    title_options: list[str] = Field(default_factory=list)
    primary_keyword: str = ""
    secondary_keywords: list[str] = Field(default_factory=list)
    search_intent: str = ""
    article_angle: str = ""
    audience_questions: list[str] = Field(default_factory=list)
    recommended_headings: list[str] = Field(default_factory=list)
    faq_questions: list[str] = Field(default_factory=list)
    suggested_word_count: int = 1200
    proposed_slug: str = ""
    meta_title: str = ""
    meta_description: str = ""
    internal_link_topics: list[str] = Field(default_factory=list)
    content_risks: list[str] = Field(default_factory=list)


class BlogTitleSuggestion(BaseModel):
    title: str
    angle: str = ""
    estimated_intent: str = ""
    length: int = 0
    keyword_included: bool = False
    click_appeal: str = "medium"
    warning: str | None = None


class BlogOutlineSection(BaseModel):
    id: str
    heading: str
    level: Literal[2, 3] = 2
    key_point: str = ""
    examples: list[str] = Field(default_factory=list)
    data_source_needs: list[str] = Field(default_factory=list)
    locked: bool = False


class BlogOutline(BaseModel):
    introduction_purpose: str = ""
    sections: list[BlogOutlineSection] = Field(default_factory=list)
    conclusion_direction: str = ""
    cta_placement: str = "end"
    faq_section: bool = True
    approved: bool = False


class BlogGeneratedSection(BaseModel):
    id: str
    heading: str
    body: str = ""
    bullets: list[str] = Field(default_factory=list)
    internal_link_anchor: str | None = None
    fact_markers: list[str] = Field(default_factory=list)
    locked: bool = False


class BlogFaqItem(BaseModel):
    id: str
    question: str
    answer: str


class QualityFinding(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    message: str = ""
    suggestion: str | None = None


class BlogQualityReview(BaseModel):
    clarity: QualityFinding = Field(default_factory=QualityFinding)
    repetition: QualityFinding = Field(default_factory=QualityFinding)
    weak_intro: QualityFinding = Field(default_factory=QualityFinding)
    unsupported_claims: QualityFinding = Field(default_factory=QualityFinding)
    promotional: QualityFinding = Field(default_factory=QualityFinding)
    keyword_stuffing: QualityFinding = Field(default_factory=QualityFinding)
    heading_quality: QualityFinding = Field(default_factory=QualityFinding)
    logical_flow: QualityFinding = Field(default_factory=QualityFinding)
    missing_conclusion: QualityFinding = Field(default_factory=QualityFinding)
    cta_quality: QualityFinding = Field(default_factory=QualityFinding)
    reading_difficulty: QualityFinding = Field(default_factory=QualityFinding)
    accessibility: QualityFinding = Field(default_factory=QualityFinding)
    missing_alt: QualityFinding = Field(default_factory=QualityFinding)
    broken_internal_links: QualityFinding = Field(default_factory=QualityFinding)
    summary: str = ""
    suggested_changes: list[str] = Field(default_factory=list)


class BlogImagePrompt(BaseModel):
    concept: str = ""
    prompt: str = ""
    aspect_ratio: str = "16:9"
    overlay_text: str | None = None
    alt_text: str = ""
    caption: str = ""
    focal_point: str = "center"


class BlogInternalLinkSuggestion(BaseModel):
    target_url: str
    target_title: str
    suggested_anchor: str
    insertion_location: str = ""
    relevance_reason: str = ""


class BlogFactClaim(BaseModel):
    claim: str
    section: str = ""
    confidence: Literal["low", "medium", "high"] = "low"
    source_required: bool = True
    review_status: str = "Needs verification"
    source_urls: list[str] = Field(default_factory=list)


class SimilarPostHit(BaseModel):
    post_id: str | None = None
    title: str = ""
    slug: str = ""
    url: str = ""
    overlap_note: str = ""


class CannibalizationRisk(BaseModel):
    keyword: str = ""
    existing_url: str = ""
    note: str = ""


class BlogSimilarityReview(BaseModel):
    duplicated_headings: list[str] = Field(default_factory=list)
    repeated_paragraphs: list[str] = Field(default_factory=list)
    similar_posts: list[SimilarPostHit] = Field(default_factory=list)
    cannibalization_risks: list[CannibalizationRisk] = Field(default_factory=list)
    conflicting_slugs: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This is an editorial similarity check only — not legal plagiarism detection."
    )


class SeoIndicator(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    message: str = ""


class BlogSeoScore(BaseModel):
    title_length: SeoIndicator = Field(default_factory=SeoIndicator)
    meta_title_length: SeoIndicator = Field(default_factory=SeoIndicator)
    description_length: SeoIndicator = Field(default_factory=SeoIndicator)
    keyword_in_title: SeoIndicator = Field(default_factory=SeoIndicator)
    keyword_in_intro: SeoIndicator = Field(default_factory=SeoIndicator)
    keyword_in_headings: SeoIndicator = Field(default_factory=SeoIndicator)
    slug_quality: SeoIndicator = Field(default_factory=SeoIndicator)
    heading_hierarchy: SeoIndicator = Field(default_factory=SeoIndicator)
    article_length: SeoIndicator = Field(default_factory=SeoIndicator)
    internal_links: SeoIndicator = Field(default_factory=SeoIndicator)
    image_alt: SeoIndicator = Field(default_factory=SeoIndicator)


# --- Request wrappers ---


class StudioRequestBase(BaseModel):
    brief: BlogContentBrief | None = None
    outline: BlogOutline | None = None
    selection: str | None = None
    section_id: str | None = None
    locked_section_ids: list[str] = Field(default_factory=list)
    blog_post_id: UUID | None = None
    client_request_id: str | None = Field(default=None, max_length=120)
    title: str | None = None
    excerpt: str | None = None
    body: str | None = None
    notes: str | None = None
    force_template: bool = False

    @field_validator("body")
    @classmethod
    def limit_body(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 50_000:
            return v[:50_000]
        return v


class SeoBriefRequest(StudioRequestBase):
    pass


class TitlesRequest(StudioRequestBase):
    count: int = Field(default=5, ge=1, le=10)


class OutlineRequest(StudioRequestBase):
    pass


class OutlineSectionRequest(StudioRequestBase):
    section_id: str


class SectionRequest(StudioRequestBase):
    section_id: str


class FullDraftRequest(StudioRequestBase):
    pass


REWRITE_ACTIONS = frozenset(
    {
        "rewrite",
        "clarity",
        "shorter",
        "expand",
        "tone",
        "grammar",
        "engaging",
        "simplify",
        "examples",
        "transition",
        "to_bullets",
        "to_prose",
        "heading",
        "continue",
        "summarize",
    }
)


class RewriteRequest(StudioRequestBase):
    action: str = "rewrite"
    selection: str = Field(min_length=1, max_length=20000)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        a = (v or "rewrite").strip().lower()
        if a not in REWRITE_ACTIONS:
            raise ValueError(f"Unsupported rewrite action: {v}")
        return a


class ReviewRequest(StudioRequestBase):
    pass


class SimilarityRequest(StudioRequestBase):
    pass


class FaqsRequest(StudioRequestBase):
    count: int = Field(default=5, ge=1, le=12)


class ImagePromptRequest(StudioRequestBase):
    pass


class InternalLinksRequest(StudioRequestBase):
    pass


class FactReviewRequest(StudioRequestBase):
    pass


class SeoScoreRequest(BaseModel):
    title: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    slug: str | None = None
    body: str | None = None
    focus_keyword: str | None = None
    cover_url: str | None = None
    blog_post_id: UUID | None = None


class StudioAutosaveRequest(BaseModel):
    title: str | None = None
    excerpt: str | None = None
    body: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    studio_brief: dict[str, Any] | None = None
    studio_outline: dict[str, Any] | None = None
    faqs: list[Any] | None = None
    focus_keyword: str | None = None
    secondary_keywords: list[str] | None = None
    social_share_text: str | None = None
    og_title: str | None = None
    expected_content_version: int
    content_document: dict[str, Any] | None = None
    hero_settings: dict[str, Any] | None = None
    editor_mode: str | None = None


class CheckpointRequest(BaseModel):
    summary: str | None = Field(default=None, max_length=500)


class FullDraftProgressResponse(BaseModel):
    sections: list[BlogGeneratedSection] = Field(default_factory=list)
    status: Literal["complete", "partial", "failed"] = "complete"
    failed_section_ids: list[str] = Field(default_factory=list)
    draft_status: str = "draft"
    body_markdown: str | None = None


class RewriteResponse(BaseModel):
    text: str
    action: str


class TitlesResponse(BaseModel):
    titles: list[BlogTitleSuggestion]


class FaqsResponse(BaseModel):
    faqs: list[BlogFaqItem]


class InternalLinksResponse(BaseModel):
    links: list[BlogInternalLinkSuggestion]


class FactReviewResponse(BaseModel):
    claims: list[BlogFactClaim]


class BlogRevisionPublic(BaseModel):
    id: UUID
    post_id: UUID
    title: str
    excerpt: str | None = None
    body: str = ""
    seo_title: str | None = None
    seo_description: str | None = None
    faqs: list[Any] | None = None
    studio_outline: dict[str, Any] | None = None
    studio_brief: dict[str, Any] | None = None
    content_version: int = 1
    actor_user_id: UUID | None = None
    source: str = "manual"
    action_type: str = "checkpoint"
    provider: str | None = None
    model_name: str | None = None
    summary: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class BlogAiOperationPublic(BaseModel):
    id: UUID
    post_id: UUID | None = None
    actor_user_id: UUID | None = None
    operation: str
    feature_key: str | None = None
    provider: str | None = None
    model_name: str | None = None
    success: bool = False
    duration_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    error_code: str | None = None
    client_request_id: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
