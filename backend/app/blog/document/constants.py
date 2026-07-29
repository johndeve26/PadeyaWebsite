"""Blog content document constants and allowlists."""

from __future__ import annotations

DOCUMENT_VERSION = 1

MAX_BLOCKS = 200
MAX_NESTING_DEPTH = 6
MAX_DOCUMENT_BYTES = 512_000

EDITOR_MODES = frozenset({"standard", "layout"})

CONTENT_WIDTHS = frozenset({"narrow", "standard", "wide", "full"})
SPACING_PRESETS = frozenset({"none", "compact", "normal", "spacious"})
HERO_VARIANTS = frozenset(
    {"standard", "image_led", "minimal", "split", "editorial", "none"}
)
ALIGNMENTS = frozenset({"left", "center", "right"})
BACKGROUNDS = frozenset(
    {"default", "muted", "primary_subtle", "surface", "elevated"}
)

# Block types grouped by category
CONTENT_BLOCKS = frozenset(
    {
        "rich_text",
        "heading",
        "image",
        "image_gallery",
        "video_embed",
        "quote",
        "list",
        "table",
        "faq",
        "divider",
        "spacer",
        "legacy_rich_text",
    }
)
EDITORIAL_BLOCKS = frozenset(
    {
        "key_takeaway",
        "important_note",
        "warning",
        "tip",
        "statistic",
        "pull_quote",
        "sources",
        "author_note",
        "table_of_contents",
    }
)
MARKETING_BLOCKS = frozenset(
    {
        "cta",
        "event_promotion",
        "host_promotion",
        "newsletter_signup",
        "app_promotion",
        "related_posts",
        "featured_event",
        "featured_host",
    }
)
LAYOUT_BLOCKS = frozenset(
    {
        "section",
        "row",
        "column",
        "hero",
        "full_width_section",
        "standard_section",
        "narrow_section",
        "two_column_row",
        "three_column_row",
        "image_text",
        "text_image",
    }
)

ALLOWED_BLOCK_TYPES = CONTENT_BLOCKS | EDITORIAL_BLOCKS | MARKETING_BLOCKS | LAYOUT_BLOCKS

# Block types that have a complete public renderer.
# AI_GENERATABLE_TYPES and template/insertion types must be subsets of this.
PUBLIC_RENDERED_TYPES = frozenset(
    {
        "rich_text",
        "legacy_rich_text",
        "heading",
        "image",
        "quote",
        "list",
        "table",
        "faq",
        "cta",
        "divider",
        "spacer",
        "tip",
        "warning",
        "key_takeaway",
        "important_note",
        "author_note",
        "table_of_contents",
        "two_column_row",
        "three_column_row",
        "standard_section",
        "full_width_section",
        "narrow_section",
        "section",
        "column",
    }
)

# Block types that may appear in newly-created / patched documents (subset of PUBLIC_RENDERED_TYPES).
# Historical documents may still contain other validated types for read/render.
NEW_CONTENT_ALLOWED_TYPES = PUBLIC_RENDERED_TYPES - {"legacy_rich_text"}

# Block types the AI studio may generate.
AI_GENERATABLE_TYPES = frozenset(
    {
        "rich_text",
        "heading",
        "image",
        "quote",
        "list",
        "table",
        "faq",
        "cta",
        "tip",
        "warning",
        "key_takeaway",
        "important_note",
        "author_note",
        "table_of_contents",
    }
)

# Block types allowed inside saved templates / reusable sections.
TEMPLATE_ALLOWED_TYPES = NEW_CONTENT_ALLOWED_TYPES

LAYOUT_CONTAINER_TYPES = frozenset(
    {
        "section",
        "row",
        "column",
        "full_width_section",
        "standard_section",
        "narrow_section",
        "two_column_row",
        "three_column_row",
        "image_text",
        "text_image",
        "hero",
    }
)

MAX_COLUMNS_PER_ROW = 3

ALLOWED_EMBED_PROVIDERS = frozenset({"youtube", "vimeo", "spotify", "twitter"})

SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto"})
