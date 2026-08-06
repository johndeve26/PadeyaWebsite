"""AI Copilot constants, feature catalogs, and Phase 1 standardized keys."""

from __future__ import annotations

# Canonical Phase 1 Event Studio keys
FEATURE_HOST_EVENT_TITLE = "host.event.title"
FEATURE_HOST_EVENT_DESCRIPTION = "host.event.description"

# Canonical Phase 1 Merch Studio keys
FEATURE_HOST_MERCH_TITLE = "host.merch.title"
FEATURE_HOST_MERCH_DESCRIPTION = "host.merch.description"
FEATURE_HOST_MERCH_TAGS = "host.merch.tags"
FEATURE_HOST_MERCH_CATEGORY = "host.merch.category"

# Canonical Phase 1 Host announcement draft (CRM composer — never auto-send)
FEATURE_HOST_ANNOUNCEMENTS_DRAFT = "host.announcements.draft"

# Canonical Phase 1 Host sponsorship pitch (marketplace — never auto-send)
FEATURE_HOST_SPONSORSHIP_PITCH = "host.sponsorship.pitch"

# Canonical Phase 1 Fan Passport bio (opt-in draft — never auto-publish)
FEATURE_FAN_PASSPORT_BIO = "fan.passport.bio"

# Canonical Phase 1 Support AI keys (staff-only)
FEATURE_SUPPORT_TRIAGE = "support.ticket.triage"
FEATURE_SUPPORT_SUMMARY = "support.ticket.summary"
FEATURE_SUPPORT_REPLY_DRAFT = "support.ticket.reply_draft"
FEATURE_SUPPORT_PRIORITY = "support.ticket.priority"
FEATURE_SUPPORT_ARTICLES = "support.ticket.article_suggestions"

# Canonical Phase 1 Admin AI summary keys (advisory only)
FEATURE_ADMIN_SUPPORT_QUEUE = "admin.support.queue_summary"
FEATURE_ADMIN_REVENUE_SUMMARY = "admin.analytics.revenue_summary"
FEATURE_ADMIN_REPORTS_SUMMARY = "admin.reports.summary"
FEATURE_ADMIN_DAILY_OPS = "admin.operations.daily_summary"

# Conversational site assistant (Ask Pàdéyá / Pàdéyá Copilot)
FEATURE_PLATFORM_ASSISTANT_CHAT = "platform.assistant.chat"

# Canonical Phase 1 Blog CMS AI keys (draft-only; never auto-publish)
FEATURE_ADMIN_BLOG_TITLE = "admin.blog.title"
FEATURE_ADMIN_BLOG_OUTLINE = "admin.blog.outline"
FEATURE_ADMIN_BLOG_EXCERPT = "admin.blog.excerpt"
FEATURE_ADMIN_BLOG_SEO = "admin.blog.seo_meta"
FEATURE_ADMIN_BLOG_SOCIAL = "admin.blog.social_snippets"
FEATURE_ADMIN_BLOG_TAGS = "admin.blog.tags"

# Blog AI Studio keys (structured JSON; draft-only; never auto-publish)
FEATURE_ADMIN_BLOG_SEO_BRIEF = "admin.blog.seo_brief"
FEATURE_ADMIN_BLOG_SECTION = "admin.blog.section"
FEATURE_ADMIN_BLOG_FULL_DRAFT = "admin.blog.full_draft"
FEATURE_ADMIN_BLOG_REWRITE = "admin.blog.rewrite"
FEATURE_ADMIN_BLOG_REVIEW = "admin.blog.review"
FEATURE_ADMIN_BLOG_FAQS = "admin.blog.faqs"
FEATURE_ADMIN_BLOG_IMAGE_PROMPT = "admin.blog.image_prompt"
FEATURE_ADMIN_BLOG_INTERNAL_LINKS = "admin.blog.internal_links"
FEATURE_ADMIN_BLOG_FACT_REVIEW = "admin.blog.fact_review"
FEATURE_ADMIN_BLOG_SIMILARITY = "admin.blog.similarity"

BLOG_STUDIO_FEATURES = frozenset(
    {
        FEATURE_ADMIN_BLOG_SEO_BRIEF,
        FEATURE_ADMIN_BLOG_SECTION,
        FEATURE_ADMIN_BLOG_FULL_DRAFT,
        FEATURE_ADMIN_BLOG_REWRITE,
        FEATURE_ADMIN_BLOG_REVIEW,
        FEATURE_ADMIN_BLOG_FAQS,
        FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
        FEATURE_ADMIN_BLOG_INTERNAL_LINKS,
        FEATURE_ADMIN_BLOG_FACT_REVIEW,
        FEATURE_ADMIN_BLOG_SIMILARITY,
    }
)

# Shipped host AI (canonical Phase 1 — Control Center + product UI)
CANONICAL_HOST_AI_FEATURES: frozenset[str] = frozenset(
    {
        FEATURE_HOST_EVENT_TITLE,
        FEATURE_HOST_EVENT_DESCRIPTION,
        FEATURE_HOST_MERCH_TITLE,
        FEATURE_HOST_MERCH_DESCRIPTION,
        FEATURE_HOST_MERCH_CATEGORY,
        FEATURE_HOST_MERCH_TAGS,
        FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
        FEATURE_HOST_SPONSORSHIP_PITCH,
    }
)

# Legacy host slugs — templates may exist; not production-safe (generic context/validation)
LEGACY_HOST_AI_FEATURES: frozenset[str] = frozenset(
    {
        "generate_ticket_tier_copy",
        "generate_instagram_captions",
        "generate_whatsapp_broadcast",
        "generate_email_announcement",
        "suggest_ticket_pricing",
        "suggest_promo_strategy",
        "summarize_event_performance",
        "suggest_legacy_tier_path",
        "generate_event_recap_draft",
    }
)

# Admin placeholder keys — not allowlisted for production generation
ADMIN_QUARANTINED_AI_FEATURES: frozenset[str] = frozenset(
    {
        "recommend_featured_events",
        "identify_high_risk_hosts",
        "fraud_risk_summary",
    }
)

# Host catalog API + generate allowlist (canonical + title/description aliases only)
HOST_FEATURES_PUBLIC = tuple(CANONICAL_HOST_AI_FEATURES)

HOST_FEATURES = HOST_FEATURES_PUBLIC + (
    "generate_event_title",
    "generate_event_description",
)

ANNOUNCEMENT_FEATURES = frozenset({FEATURE_HOST_ANNOUNCEMENTS_DRAFT})

SPONSORSHIP_FEATURES = frozenset({FEATURE_HOST_SPONSORSHIP_PITCH})

FAN_FEATURES_PUBLIC = (FEATURE_FAN_PASSPORT_BIO,)

FAN_FEATURES = FAN_FEATURES_PUBLIC

PASSPORT_FEATURES = frozenset({FEATURE_FAN_PASSPORT_BIO})

ADMIN_FEATURES = (
    FEATURE_SUPPORT_TRIAGE,
    FEATURE_SUPPORT_SUMMARY,
    FEATURE_SUPPORT_REPLY_DRAFT,
    FEATURE_SUPPORT_PRIORITY,
    FEATURE_SUPPORT_ARTICLES,
    FEATURE_ADMIN_SUPPORT_QUEUE,
    FEATURE_ADMIN_REVENUE_SUMMARY,
    FEATURE_ADMIN_REPORTS_SUMMARY,
    FEATURE_ADMIN_DAILY_OPS,
    FEATURE_ADMIN_BLOG_TITLE,
    FEATURE_ADMIN_BLOG_OUTLINE,
    FEATURE_ADMIN_BLOG_EXCERPT,
    FEATURE_ADMIN_BLOG_SEO,
    FEATURE_ADMIN_BLOG_SOCIAL,
    FEATURE_ADMIN_BLOG_TAGS,
    FEATURE_ADMIN_BLOG_SEO_BRIEF,
    FEATURE_ADMIN_BLOG_SECTION,
    FEATURE_ADMIN_BLOG_FULL_DRAFT,
    FEATURE_ADMIN_BLOG_REWRITE,
    FEATURE_ADMIN_BLOG_REVIEW,
    FEATURE_ADMIN_BLOG_FAQS,
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS,
    FEATURE_ADMIN_BLOG_FACT_REVIEW,
    FEATURE_ADMIN_BLOG_SIMILARITY,
)

SUPPORT_FEATURES = frozenset(
    {
        FEATURE_SUPPORT_TRIAGE,
        FEATURE_SUPPORT_SUMMARY,
        FEATURE_SUPPORT_REPLY_DRAFT,
        FEATURE_SUPPORT_PRIORITY,
        FEATURE_SUPPORT_ARTICLES,
    }
)

ADMIN_SUMMARY_FEATURES = frozenset(
    {
        FEATURE_ADMIN_SUPPORT_QUEUE,
        FEATURE_ADMIN_REVENUE_SUMMARY,
        FEATURE_ADMIN_REPORTS_SUMMARY,
        FEATURE_ADMIN_DAILY_OPS,
    }
)

BLOG_FEATURES = frozenset(
    {
        FEATURE_ADMIN_BLOG_TITLE,
        FEATURE_ADMIN_BLOG_OUTLINE,
        FEATURE_ADMIN_BLOG_EXCERPT,
        FEATURE_ADMIN_BLOG_SEO,
        FEATURE_ADMIN_BLOG_SOCIAL,
        FEATURE_ADMIN_BLOG_TAGS,
    }
) | BLOG_STUDIO_FEATURES

# Future keys — Control Center only; disabled by default
FUTURE_AI_FEATURES: tuple[str, ...] = (
    "fan.connect.explanation",
    "discovery.why_recommended",
)

HIGH_RISK_HUMAN_REVIEW_LOCKED: frozenset[str] = frozenset(
    {
        FEATURE_SUPPORT_REPLY_DRAFT,
        FEATURE_ADMIN_BLOG_SEO,
        FEATURE_ADMIN_BLOG_SOCIAL,
        FEATURE_ADMIN_BLOG_SEO_BRIEF,
        FEATURE_ADMIN_BLOG_FULL_DRAFT,
        FEATURE_ADMIN_BLOG_REVIEW,
        FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
        FEATURE_HOST_SPONSORSHIP_PITCH,
        FEATURE_FAN_PASSPORT_BIO,
    }
)

# Phase 1 keys managed on /admin/ai/features (no deferred product features)
ADMIN_CONTROL_FEATURES: tuple[str, ...] = (
    FEATURE_HOST_EVENT_TITLE,
    FEATURE_HOST_EVENT_DESCRIPTION,
    FEATURE_HOST_MERCH_TITLE,
    FEATURE_HOST_MERCH_DESCRIPTION,
    FEATURE_HOST_MERCH_CATEGORY,
    FEATURE_HOST_MERCH_TAGS,
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
    FEATURE_HOST_SPONSORSHIP_PITCH,
    FEATURE_FAN_PASSPORT_BIO,
    FEATURE_SUPPORT_TRIAGE,
    FEATURE_SUPPORT_SUMMARY,
    FEATURE_SUPPORT_REPLY_DRAFT,
    FEATURE_SUPPORT_PRIORITY,
    FEATURE_SUPPORT_ARTICLES,
    FEATURE_ADMIN_SUPPORT_QUEUE,
    FEATURE_ADMIN_REVENUE_SUMMARY,
    FEATURE_ADMIN_REPORTS_SUMMARY,
    FEATURE_ADMIN_DAILY_OPS,
    FEATURE_ADMIN_BLOG_TITLE,
    FEATURE_ADMIN_BLOG_OUTLINE,
    FEATURE_ADMIN_BLOG_EXCERPT,
    FEATURE_ADMIN_BLOG_SEO,
    FEATURE_ADMIN_BLOG_SOCIAL,
    FEATURE_ADMIN_BLOG_TAGS,
    FEATURE_ADMIN_BLOG_SEO_BRIEF,
    FEATURE_ADMIN_BLOG_SECTION,
    FEATURE_ADMIN_BLOG_FULL_DRAFT,
    FEATURE_ADMIN_BLOG_REWRITE,
    FEATURE_ADMIN_BLOG_REVIEW,
    FEATURE_ADMIN_BLOG_FAQS,
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS,
    FEATURE_ADMIN_BLOG_FACT_REVIEW,
    FEATURE_ADMIN_BLOG_SIMILARITY,
    FEATURE_PLATFORM_ASSISTANT_CHAT,
)

DEFAULT_FEATURE_PERMISSIONS: dict[str, list[str]] = {
    FEATURE_HOST_EVENT_TITLE: ["ai.use_own"],
    FEATURE_HOST_EVENT_DESCRIPTION: ["ai.use_own"],
    FEATURE_HOST_MERCH_TITLE: ["ai.use_own"],
    FEATURE_HOST_MERCH_DESCRIPTION: ["ai.use_own"],
    FEATURE_HOST_MERCH_CATEGORY: ["ai.use_own"],
    FEATURE_HOST_MERCH_TAGS: ["ai.use_own"],
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT: ["ai.use_own"],
    FEATURE_HOST_SPONSORSHIP_PITCH: ["ai.use_own"],
    FEATURE_FAN_PASSPORT_BIO: [],
    FEATURE_SUPPORT_TRIAGE: ["ai.use_platform", "admin.support.view"],
    FEATURE_SUPPORT_SUMMARY: ["ai.use_platform", "admin.support.view"],
    FEATURE_SUPPORT_REPLY_DRAFT: ["ai.use_platform", "admin.support.view"],
    FEATURE_SUPPORT_PRIORITY: ["ai.use_platform", "admin.support.view"],
    FEATURE_SUPPORT_ARTICLES: ["ai.use_platform", "admin.support.view"],
    FEATURE_ADMIN_SUPPORT_QUEUE: ["ai.use_platform", "admin.support.view"],
    FEATURE_ADMIN_REVENUE_SUMMARY: ["ai.use_platform", "analytics.view_platform"],
    FEATURE_ADMIN_REPORTS_SUMMARY: ["ai.use_platform", "reviews.moderate"],
    FEATURE_ADMIN_DAILY_OPS: ["ai.use_platform"],
    FEATURE_ADMIN_BLOG_TITLE: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_OUTLINE: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_EXCERPT: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_SEO: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_SOCIAL: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_TAGS: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_SEO_BRIEF: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_SECTION: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_FULL_DRAFT: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_REWRITE: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_REVIEW: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_FAQS: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_FACT_REVIEW: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_ADMIN_BLOG_SIMILARITY: ["ai.use_platform", "admin.blog.edit", "admin.blog.create"],
    FEATURE_PLATFORM_ASSISTANT_CHAT: [],
}


def feature_group(feature_key: str) -> str:
    if feature_key.startswith("platform."):
        return "platform"
    if feature_key.startswith("fan."):
        return "fan"
    if feature_key.startswith("host."):
        return "host"
    if feature_key.startswith("support."):
        return "support"
    if feature_key.startswith("admin.blog."):
        return "blog"
    if feature_key.startswith("admin."):
        return "admin"
    return "other"

# Map aliases → canonical feature key used for toggles / audit / usage
FEATURE_CANONICAL: dict[str, str] = {
    "generate_event_title": FEATURE_HOST_EVENT_TITLE,
    "generate_event_description": FEATURE_HOST_EVENT_DESCRIPTION,
    FEATURE_HOST_EVENT_TITLE: FEATURE_HOST_EVENT_TITLE,
    FEATURE_HOST_EVENT_DESCRIPTION: FEATURE_HOST_EVENT_DESCRIPTION,
    FEATURE_HOST_MERCH_TITLE: FEATURE_HOST_MERCH_TITLE,
    FEATURE_HOST_MERCH_DESCRIPTION: FEATURE_HOST_MERCH_DESCRIPTION,
    FEATURE_HOST_MERCH_TAGS: FEATURE_HOST_MERCH_TAGS,
    FEATURE_HOST_MERCH_CATEGORY: FEATURE_HOST_MERCH_CATEGORY,
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT: FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
    FEATURE_HOST_SPONSORSHIP_PITCH: FEATURE_HOST_SPONSORSHIP_PITCH,
    FEATURE_FAN_PASSPORT_BIO: FEATURE_FAN_PASSPORT_BIO,
    FEATURE_SUPPORT_TRIAGE: FEATURE_SUPPORT_TRIAGE,
    FEATURE_SUPPORT_SUMMARY: FEATURE_SUPPORT_SUMMARY,
    FEATURE_SUPPORT_REPLY_DRAFT: FEATURE_SUPPORT_REPLY_DRAFT,
    FEATURE_SUPPORT_PRIORITY: FEATURE_SUPPORT_PRIORITY,
    FEATURE_SUPPORT_ARTICLES: FEATURE_SUPPORT_ARTICLES,
    FEATURE_ADMIN_SUPPORT_QUEUE: FEATURE_ADMIN_SUPPORT_QUEUE,
    FEATURE_ADMIN_REVENUE_SUMMARY: FEATURE_ADMIN_REVENUE_SUMMARY,
    FEATURE_ADMIN_REPORTS_SUMMARY: FEATURE_ADMIN_REPORTS_SUMMARY,
    FEATURE_ADMIN_DAILY_OPS: FEATURE_ADMIN_DAILY_OPS,
    FEATURE_ADMIN_BLOG_TITLE: FEATURE_ADMIN_BLOG_TITLE,
    FEATURE_ADMIN_BLOG_OUTLINE: FEATURE_ADMIN_BLOG_OUTLINE,
    FEATURE_ADMIN_BLOG_EXCERPT: FEATURE_ADMIN_BLOG_EXCERPT,
    FEATURE_ADMIN_BLOG_SEO: FEATURE_ADMIN_BLOG_SEO,
    FEATURE_ADMIN_BLOG_SOCIAL: FEATURE_ADMIN_BLOG_SOCIAL,
    FEATURE_ADMIN_BLOG_TAGS: FEATURE_ADMIN_BLOG_TAGS,
    FEATURE_ADMIN_BLOG_SEO_BRIEF: FEATURE_ADMIN_BLOG_SEO_BRIEF,
    FEATURE_ADMIN_BLOG_SECTION: FEATURE_ADMIN_BLOG_SECTION,
    FEATURE_ADMIN_BLOG_FULL_DRAFT: FEATURE_ADMIN_BLOG_FULL_DRAFT,
    FEATURE_ADMIN_BLOG_REWRITE: FEATURE_ADMIN_BLOG_REWRITE,
    FEATURE_ADMIN_BLOG_REVIEW: FEATURE_ADMIN_BLOG_REVIEW,
    FEATURE_ADMIN_BLOG_FAQS: FEATURE_ADMIN_BLOG_FAQS,
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT: FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS: FEATURE_ADMIN_BLOG_INTERNAL_LINKS,
    FEATURE_ADMIN_BLOG_FACT_REVIEW: FEATURE_ADMIN_BLOG_FACT_REVIEW,
    FEATURE_ADMIN_BLOG_SIMILARITY: FEATURE_ADMIN_BLOG_SIMILARITY,
    FEATURE_PLATFORM_ASSISTANT_CHAT: FEATURE_PLATFORM_ASSISTANT_CHAT,
    "summarize_support_complaints": FEATURE_ADMIN_SUPPORT_QUEUE,
    "explain_revenue_trends": FEATURE_ADMIN_REVENUE_SUMMARY,
    "summarize_review_reports": FEATURE_ADMIN_REPORTS_SUMMARY,
}

# Map canonical → prompt template slug in ai_prompt_templates
FEATURE_TEMPLATE_SLUG: dict[str, str] = {
    FEATURE_HOST_EVENT_TITLE: FEATURE_HOST_EVENT_TITLE,
    FEATURE_HOST_EVENT_DESCRIPTION: FEATURE_HOST_EVENT_DESCRIPTION,
    "generate_event_title": FEATURE_HOST_EVENT_TITLE,
    "generate_event_description": FEATURE_HOST_EVENT_DESCRIPTION,
    FEATURE_HOST_MERCH_TITLE: FEATURE_HOST_MERCH_TITLE,
    FEATURE_HOST_MERCH_DESCRIPTION: FEATURE_HOST_MERCH_DESCRIPTION,
    FEATURE_HOST_MERCH_TAGS: FEATURE_HOST_MERCH_TAGS,
    FEATURE_HOST_MERCH_CATEGORY: FEATURE_HOST_MERCH_CATEGORY,
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT: FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
    FEATURE_HOST_SPONSORSHIP_PITCH: FEATURE_HOST_SPONSORSHIP_PITCH,
    FEATURE_FAN_PASSPORT_BIO: FEATURE_FAN_PASSPORT_BIO,
    FEATURE_SUPPORT_TRIAGE: FEATURE_SUPPORT_TRIAGE,
    FEATURE_SUPPORT_SUMMARY: FEATURE_SUPPORT_SUMMARY,
    FEATURE_SUPPORT_REPLY_DRAFT: FEATURE_SUPPORT_REPLY_DRAFT,
    FEATURE_SUPPORT_PRIORITY: FEATURE_SUPPORT_PRIORITY,
    FEATURE_SUPPORT_ARTICLES: FEATURE_SUPPORT_ARTICLES,
    FEATURE_ADMIN_SUPPORT_QUEUE: FEATURE_ADMIN_SUPPORT_QUEUE,
    FEATURE_ADMIN_REVENUE_SUMMARY: FEATURE_ADMIN_REVENUE_SUMMARY,
    FEATURE_ADMIN_REPORTS_SUMMARY: FEATURE_ADMIN_REPORTS_SUMMARY,
    FEATURE_ADMIN_DAILY_OPS: FEATURE_ADMIN_DAILY_OPS,
    FEATURE_ADMIN_BLOG_TITLE: FEATURE_ADMIN_BLOG_TITLE,
    FEATURE_ADMIN_BLOG_OUTLINE: FEATURE_ADMIN_BLOG_OUTLINE,
    FEATURE_ADMIN_BLOG_EXCERPT: FEATURE_ADMIN_BLOG_EXCERPT,
    FEATURE_ADMIN_BLOG_SEO: FEATURE_ADMIN_BLOG_SEO,
    FEATURE_ADMIN_BLOG_SOCIAL: FEATURE_ADMIN_BLOG_SOCIAL,
    FEATURE_ADMIN_BLOG_TAGS: FEATURE_ADMIN_BLOG_TAGS,
    FEATURE_ADMIN_BLOG_SEO_BRIEF: FEATURE_ADMIN_BLOG_SEO_BRIEF,
    FEATURE_ADMIN_BLOG_SECTION: FEATURE_ADMIN_BLOG_SECTION,
    FEATURE_ADMIN_BLOG_FULL_DRAFT: FEATURE_ADMIN_BLOG_FULL_DRAFT,
    FEATURE_ADMIN_BLOG_REWRITE: FEATURE_ADMIN_BLOG_REWRITE,
    FEATURE_ADMIN_BLOG_REVIEW: FEATURE_ADMIN_BLOG_REVIEW,
    FEATURE_ADMIN_BLOG_FAQS: FEATURE_ADMIN_BLOG_FAQS,
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT: FEATURE_ADMIN_BLOG_IMAGE_PROMPT,
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS: FEATURE_ADMIN_BLOG_INTERNAL_LINKS,
    FEATURE_ADMIN_BLOG_FACT_REVIEW: FEATURE_ADMIN_BLOG_FACT_REVIEW,
    FEATURE_ADMIN_BLOG_SIMILARITY: FEATURE_ADMIN_BLOG_SIMILARITY,
    "summarize_support_complaints": FEATURE_ADMIN_SUPPORT_QUEUE,
    "explain_revenue_trends": FEATURE_ADMIN_REVENUE_SUMMARY,
    "summarize_review_reports": FEATURE_ADMIN_REPORTS_SUMMARY,
}

FEATURE_LABELS: dict[str, str] = {
    FEATURE_HOST_EVENT_TITLE: "Generate event title ideas",
    FEATURE_HOST_EVENT_DESCRIPTION: "Generate event description",
    FEATURE_HOST_MERCH_TITLE: "Generate merch title ideas",
    FEATURE_HOST_MERCH_DESCRIPTION: "Generate merch description",
    FEATURE_HOST_MERCH_CATEGORY: "Suggest merch category",
    FEATURE_HOST_MERCH_TAGS: "Suggest merch tags",
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT: "Draft host announcement",
    FEATURE_HOST_SPONSORSHIP_PITCH: "Draft sponsorship pitch",
    FEATURE_FAN_PASSPORT_BIO: "Improve Fan Passport bio",
    FEATURE_SUPPORT_TRIAGE: "Suggest support category",
    FEATURE_SUPPORT_SUMMARY: "Summarize support ticket",
    FEATURE_SUPPORT_REPLY_DRAFT: "Draft support reply",
    FEATURE_SUPPORT_PRIORITY: "Suggest support priority",
    FEATURE_SUPPORT_ARTICLES: "Suggest help articles",
    FEATURE_ADMIN_SUPPORT_QUEUE: "Summarize support queue",
    FEATURE_ADMIN_REVENUE_SUMMARY: "Explain revenue period",
    FEATURE_ADMIN_REPORTS_SUMMARY: "Summarize reports",
    FEATURE_ADMIN_DAILY_OPS: "Daily operations summary",
    FEATURE_ADMIN_BLOG_TITLE: "Generate blog title ideas",
    FEATURE_ADMIN_BLOG_OUTLINE: "Generate blog outline",
    FEATURE_ADMIN_BLOG_EXCERPT: "Generate blog excerpt",
    FEATURE_ADMIN_BLOG_SEO: "Generate SEO meta",
    FEATURE_ADMIN_BLOG_SOCIAL: "Generate social snippets",
    FEATURE_ADMIN_BLOG_TAGS: "Suggest blog tags",
    FEATURE_ADMIN_BLOG_SEO_BRIEF: "Generate SEO content brief",
    FEATURE_ADMIN_BLOG_SECTION: "Generate blog section",
    FEATURE_ADMIN_BLOG_FULL_DRAFT: "Generate full blog draft",
    FEATURE_ADMIN_BLOG_REWRITE: "Rewrite blog selection",
    FEATURE_ADMIN_BLOG_REVIEW: "Review blog article quality",
    FEATURE_ADMIN_BLOG_FAQS: "Generate blog FAQs",
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT: "Generate blog image prompt",
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS: "Suggest blog internal links",
    FEATURE_ADMIN_BLOG_FACT_REVIEW: "Review blog factual claims",
    FEATURE_ADMIN_BLOG_SIMILARITY: "Review blog similarity",
    FEATURE_PLATFORM_ASSISTANT_CHAT: "Conversational assistant chat",
    "generate_event_title": "Generate event title",
    "generate_event_description": "Generate event description",
    "generate_ticket_tier_copy": "Generate ticket tier copy",
    "generate_instagram_captions": "Generate Instagram captions",
    "generate_whatsapp_broadcast": "Generate WhatsApp broadcast copy",
    "generate_email_announcement": "Generate email announcement",
    "suggest_ticket_pricing": "Suggest ticket pricing",
    "suggest_promo_strategy": "Suggest promo strategy",
    "summarize_event_performance": "Summarize event performance",
    "suggest_legacy_tier_path": "Suggest path to next Legacy tier",
    "generate_event_recap_draft": "Generate event recap draft",
    "summarize_support_complaints": "Summarize support queue",
    "summarize_review_reports": "Summarize reports",
    "explain_revenue_trends": "Explain revenue period",
    "recommend_featured_events": "Recommend featured events",
    "identify_high_risk_hosts": "Identify high-risk hosts (placeholder)",
    "fraud_risk_summary": "Fraud risk summary (placeholder)",
    "fan.connect.explanation": "Fan Connect explanation (future)",
    "discovery.why_recommended": "Discovery why recommended (future)",
}

# Default feature enablement (overridable via AI_DISABLED_FEATURES env comma-list)
DEFAULT_FEATURE_ENABLED: dict[str, bool] = {
    FEATURE_HOST_EVENT_TITLE: True,
    FEATURE_HOST_EVENT_DESCRIPTION: True,
    FEATURE_HOST_MERCH_TITLE: True,
    FEATURE_HOST_MERCH_DESCRIPTION: True,
    FEATURE_HOST_MERCH_CATEGORY: True,
    FEATURE_HOST_MERCH_TAGS: True,
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT: True,
    FEATURE_HOST_SPONSORSHIP_PITCH: True,
    FEATURE_FAN_PASSPORT_BIO: True,
    FEATURE_SUPPORT_TRIAGE: True,
    FEATURE_SUPPORT_SUMMARY: True,
    FEATURE_SUPPORT_REPLY_DRAFT: True,
    FEATURE_SUPPORT_PRIORITY: True,
    FEATURE_SUPPORT_ARTICLES: True,
    FEATURE_ADMIN_SUPPORT_QUEUE: True,
    FEATURE_ADMIN_REVENUE_SUMMARY: True,
    FEATURE_ADMIN_REPORTS_SUMMARY: True,
    FEATURE_ADMIN_DAILY_OPS: True,
    FEATURE_ADMIN_BLOG_TITLE: True,
    FEATURE_ADMIN_BLOG_OUTLINE: True,
    FEATURE_ADMIN_BLOG_EXCERPT: True,
    FEATURE_ADMIN_BLOG_SEO: True,
    FEATURE_ADMIN_BLOG_SOCIAL: True,
    FEATURE_ADMIN_BLOG_TAGS: True,
    FEATURE_ADMIN_BLOG_SEO_BRIEF: True,
    FEATURE_ADMIN_BLOG_SECTION: True,
    FEATURE_ADMIN_BLOG_FULL_DRAFT: True,
    FEATURE_ADMIN_BLOG_REWRITE: True,
    FEATURE_ADMIN_BLOG_REVIEW: True,
    FEATURE_ADMIN_BLOG_FAQS: True,
    FEATURE_ADMIN_BLOG_IMAGE_PROMPT: True,
    FEATURE_ADMIN_BLOG_INTERNAL_LINKS: True,
    FEATURE_ADMIN_BLOG_FACT_REVIEW: True,
    FEATURE_ADMIN_BLOG_SIMILARITY: True,
    FEATURE_PLATFORM_ASSISTANT_CHAT: True,
    "generate_event_title": True,
    "generate_event_description": True,
    "summarize_support_complaints": True,
    "summarize_review_reports": True,
    "explain_revenue_trends": True,
    # Legacy host AI — disabled by default (see LEGACY_HOST_AI_FEATURES)
    "generate_ticket_tier_copy": False,
    "generate_instagram_captions": False,
    "generate_whatsapp_broadcast": False,
    "generate_email_announcement": False,
    "suggest_ticket_pricing": False,
    "suggest_promo_strategy": False,
    "summarize_event_performance": False,
    "suggest_legacy_tier_path": False,
    "generate_event_recap_draft": False,
    # Admin placeholder / recommendation AI — not production-safe
    "recommend_featured_events": False,
    "identify_high_risk_hosts": False,
    "fraud_risk_summary": False,
    "fan.connect.explanation": False,
    "discovery.why_recommended": False,
}

TITLE_MIN_LEN = 3
TITLE_MAX_LEN = 120
DESCRIPTION_MIN_LEN = 40
DESCRIPTION_MAX_LEN = 4000
TITLE_OPTIONS_MIN = 3
TITLE_OPTIONS_MAX = 5
MERCH_TAG_MAX_LEN = 32
MERCH_TAG_MAX_COUNT = 8

PASSPORT_BIO_MAX_LEN = 2000
PASSPORT_BIO_MIN_LEN = 30
PASSPORT_BIO_OPTIONS_MIN = 2
PASSPORT_BIO_OPTIONS_MAX = 3

DRAFT_DISCLAIMER = (
    "Draft only — review before publishing. AI suggestions can be edited before saving."
)

SUPPORT_DRAFT_DISCLAIMER = (
    "AI suggestions are drafts. Review before applying or sending."
)

ADMIN_SUMMARY_DISCLAIMER = (
    "AI summary is advisory. Review source data before taking action."
)

BLOG_DRAFT_DISCLAIMER = (
    "AI suggestions are drafts. Review before publishing."
)

BLOG_TITLE_MAX_LEN = 120
BLOG_EXCERPT_MAX_LEN = 320
BLOG_SEO_TITLE_MAX_LEN = 70
BLOG_META_DESC_MAX_LEN = 160
BLOG_SLUG_MAX_LEN = 200
BLOG_TAG_MAX_COUNT = 8

ANNOUNCEMENT_DRAFT_DISCLAIMER = (
    "AI announcement drafts are suggestions only. Review before creating or dispatching. "
    "Nothing is sent automatically."
)

SPONSORSHIP_DRAFT_DISCLAIMER = (
    "AI sponsorship pitch drafts are suggestions only. Review before saving or contacting "
    "brands. Pàdéyá does not send sponsor messages automatically."
)

SYSTEM_HOST_ANNOUNCEMENT_SAFE = (
    "You are Pàdéyá Host Copilot for CRM announcement drafts. "
    "Output is draft-only — never imply the message was sent, scheduled, or delivered. "
    "Never include recipient emails, phone numbers, or private addresses. "
    "Do not promise refunds, discounts, guaranteed entry, attendance, or sales. "
    "Do not invent urgency or false scarcity. Host must review and send manually. "
    "When personalization is requested, use the literal token {{name}} for the fan's "
    "given name from their profile — never invent names."
)

SYSTEM_HOST_SPONSORSHIP_SAFE = (
    "You are Pàdéyá Host Copilot for sponsorship pitch drafts. "
    "Output is draft-only — never imply messages were sent or sponsorships approved. "
    "Use only aggregate audience/event stats provided; never invent follower counts, "
    "ratings, or ROI. Do not claim Pàdéyá endorses the host unless explicitly stated. "
    "No guaranteed sponsorship, sales, attendance, or brand safety guarantees. "
    "No buyer PII, payment data, private venues, Vault content, or CRM notes. "
    "Host must review and reach out to sponsors manually."
)

PASSPORT_DRAFT_DISCLAIMER = (
    "AI bio suggestions are drafts only. Review and save your Passport manually. "
    "Nothing is published automatically and visibility settings are unchanged."
)

SYSTEM_FAN_PASSPORT_SAFE = (
    "You are Pàdéyá Fan Passport Copilot. Suggest short public bio drafts for event fans. "
    "Output is draft-only — never change visibility or publish. "
    "Use only the public context provided. Do not infer attendance, spend, VIP status, "
    "ticket types, messages, or private traits. "
    "Do not claim verified credentials unless explicitly in visible badges. "
    "Warm, friendly, event-community tone. No harassment or discrimination."
)

SYSTEM_HOST_SAFE = (
    "You are Pàdéyá Host Copilot. Suggest marketing drafts for event hosts. "
    "Output is draft-only and must be human-edited before use. "
    "Never claim to publish events, send messages, or change money. "
    "Never invent official Pàdéyá policy, refund guarantees, or illegal promises. "
    "Do not claim guaranteed sales, attendance, or revenue. "
    "Keep tone vivid and local. Always remind the host to review before using."
)

SYSTEM_HOST_MERCH_SAFE = (
    "You are Pàdéyá Merch Copilot. Suggest product copy drafts for host merchandise. "
    "Output is draft-only and must be human-edited before use. "
    "Never publish products, change prices, inventory, fulfillment, or finance. "
    "Do not invent materials, quality guarantees, scarcity, refunds, medical claims, "
    "celebrity/brand endorsements, or 'official' claims unless the host already stated them. "
    "Never invent categories outside the provided catalog. Keep tone vivid and local."
)

SYSTEM_ADMIN_SAFE = (
    "You are Pàdéyá Admin Copilot. Summarize platform signals for operators. "
    "Never approve refunds or payouts, never modify financial records, "
    "and clearly mark placeholders for fraud/risk. Suggestions only."
)

SYSTEM_ADMIN_SUMMARY_SAFE = (
    "You are Pàdéyá Admin Copilot for advisory summaries only. "
    "Use only the aggregate context provided. Do not invent totals. "
    "Never moderate, refund, suspend, feature, hide, pay out, message, "
    "or change finance. Never claim an action was completed. "
    "Phrase recommendations as suggestions for human review. "
    "Do not expose secrets, buyer PII, payment payloads, QR/ticket secrets, "
    "Vault content, private venues, or impersonation/fraud playbook details."
)

SYSTEM_BLOG_SAFE = (
    "You are Pàdéyá Blog Copilot for CMS editors. "
    "Produce draft writing assists only — never publish posts. "
    "Do not invent legal/policy claims or contradict Pàdéyá Terms, Privacy, "
    "Refund Policy, Ticket Policy, Safety, or Community Guidelines. "
    "Do not guarantee refunds, payouts, safety, attendance, or sales. "
    "Keep tone clear and on-brand. Editors must review before publishing."
)

SYSTEM_SUPPORT_SAFE = (
    "You are Pàdéyá Support Copilot for staff only. "
    "Produce draft suggestions that a human must review. "
    "Never send replies, close tickets, approve refunds, change payouts, "
    "or make moderation/restriction decisions. "
    "Do not promise refunds or payment confirmations unless the provided "
    "context already states them. Be polite, concise, and never expose "
    "internal notes, secrets, or private data beyond the ticket context."
)
