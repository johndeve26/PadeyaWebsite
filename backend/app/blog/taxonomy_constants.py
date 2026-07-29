"""Seed catalogs for blog post types and media roles."""

from __future__ import annotations

# (key, name, description, sort_order)
SYSTEM_POST_TYPES: list[tuple[str, str, str, int]] = [
    ("guide", "Guide", "General how-to or evergreen guide", 10),
    ("how_to", "How-to guide", "Step-by-step instructional article", 20),
    ("list_article", "List article", "Numbered or curated list format", 30),
    ("case_study", "Case study", "Real-world story with outcomes", 40),
    ("product_update", "Product update", "Platform or feature announcements", 50),
    ("news", "News analysis", "Industry news and analysis", 60),
    ("editorial", "Editorial", "Opinion or brand editorial", 70),
    ("interview", "Interview", "Q&A or conversation format", 80),
    ("comparison", "Comparison", "Compare options or approaches", 90),
    ("event_planning", "Event planning guide", "Planning a night or event", 100),
    ("venue_guide", "Venue guide", "Venue-focused guidance", 110),
    ("host_resource", "Host resource", "Resources for hosts", 120),
    ("attendee_guide", "Attendee guide", "Guidance for fans and attendees", 130),
]

# Historical studio_brief.content_type display strings → post type key
CONTENT_TYPE_TO_KEY: dict[str, str] = {
    "guide": "guide",
    "How-to guide": "how_to",
    "how_to": "how_to",
    "how-to": "how_to",
    "Event planning guide": "event_planning",
    "event_planning": "event_planning",
    "Industry insight": "news",
    "industry_insight": "news",
    "Venue guide": "venue_guide",
    "venue_guide": "venue_guide",
    "Host resource": "host_resource",
    "host_resource": "host_resource",
    "Attendee guide": "attendee_guide",
    "attendee_guide": "attendee_guide",
    "Product update": "product_update",
    "product_update": "product_update",
    "Case study": "case_study",
    "case_study": "case_study",
    "List article": "list_article",
    "list_article": "list_article",
    "News analysis": "news",
    "news": "news",
    "Editorial": "editorial",
    "editorial": "editorial",
    "interview": "interview",
    "Interview": "interview",
    "comparison": "comparison",
    "Comparison": "comparison",
    "practical": "guide",
}

# (key, name, description, sort_order, storage_folder, is_required, allowed_contexts)
SYSTEM_MEDIA_ROLES: list[tuple[str, str, str, int, str, bool, list[str]]] = [
    (
        "cover",
        "Featured image",
        "Primary cover image for the post",
        10,
        "covers",
        True,
        ["cover", "featured"],
    ),
    (
        "og",
        "Open Graph image",
        "Social sharing / Open Graph image",
        20,
        "covers",
        True,
        ["og", "social"],
    ),
    (
        "inline",
        "Inline image",
        "Images inside the article body",
        30,
        "content",
        True,
        ["inline", "block"],
    ),
    (
        "gallery",
        "Gallery image",
        "Images in gallery blocks",
        40,
        "content",
        False,
        ["gallery"],
    ),
    (
        "social_share",
        "Social share image",
        "Dedicated social share creative",
        50,
        "covers",
        False,
        ["social_share"],
    ),
    (
        "teaser",
        "Teaser image",
        "Teaser or preview image",
        60,
        "content",
        False,
        ["teaser"],
    ),
]

REQUIRED_MEDIA_ROLE_KEYS = frozenset({"cover", "og", "inline"})

SAFE_STORAGE_FOLDERS = frozenset({"covers", "content"})
