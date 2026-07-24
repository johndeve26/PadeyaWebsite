"""Legacy tier score weights and default tier catalog."""

from decimal import Decimal

# Composite score factor weights (must sum to 1.0)
SCORE_WEIGHTS: dict[str, Decimal] = {
    "verified_rating": Decimal("0.30"),
    "completed_events": Decimal("0.15"),
    "tickets_sold": Decimal("0.15"),
    "verified_checkins": Decimal("0.15"),
    "refund_dispute_rate": Decimal("0.10"),
    "consistency": Decimal("0.10"),
    "repeat_buyers_followers": Decimal("0.05"),
}

# Caps used to normalize raw metrics into 0–100 factor scores
SCORE_CAPS = {
    "completed_events": 20,
    "tickets_sold": 5000,
    "verified_checkins": 3000,
    "followers": 2000,
}

# Content Studio block catalog (defaults for hosts without custom config)
BLOCK_TYPES = (
    "about",
    "upcoming_events",
    "past_events",
    "event_memories",
    "verified_reviews",
    "vault_preview",
    "sponsor_packages",
    "photo_gallery",
    "featured_video",
    "faq",
    "contact_cta",
    "related_discovery",
)

FEATURED_ITEM_TYPES = (
    "event",
    "review",
    "vault_item",
    "memory",
    "sponsor_slot",
    "media",
)

FEATURED_PLACEMENTS = (
    "featured_upcoming_event",
    "featured_past_event",
    "featured_review",
    "featured_vault_item",
    "featured_memory",
    "gallery",
    "featured_video",
)

DEFAULT_CONTENT_BLOCKS: list[dict] = [
    {
        "block_type": "about",
        "title_override": "About",
        "description_override": "Who this host is and the nights they put on.",
        "is_visible": True,
        "sort_order": 0,
        "layout_style": "prose",
        "source_type": "automatic",
        "item_limit": None,
    },
    {
        "block_type": "upcoming_events",
        "title_override": "Upcoming events",
        "description_override": "Published nights you can book now on Pàdéyá.",
        "is_visible": True,
        "sort_order": 1,
        "layout_style": "premium_cards",
        "source_type": "automatic",
        "item_limit": 3,
    },
    {
        "block_type": "past_events",
        "title_override": "Past events",
        "description_override": "Nights already in the books — open memories when available.",
        "is_visible": True,
        "sort_order": 2,
        "layout_style": "premium_cards",
        "source_type": "automatic",
        "item_limit": 6,
    },
    {
        "block_type": "event_memories",
        "title_override": "Event Memories",
        "description_override": "Verified ratings and stories from completed nights.",
        "is_visible": True,
        "sort_order": 3,
        "layout_style": "memory_cards",
        "source_type": "automatic",
        "item_limit": 6,
    },
    {
        "block_type": "verified_reviews",
        "title_override": "What verified attendees say",
        "description_override": "Only checked-in buyers can leave these reviews.",
        "is_visible": True,
        "sort_order": 4,
        "layout_style": "verified_quotes",
        "source_type": "automatic",
        "item_limit": 5,
    },
    {
        "block_type": "vault_preview",
        "title_override": "Vault",
        "description_override": "Exclusive drops fans unlock by follow, ticket, attendance, VIP, or purchase.",
        "is_visible": True,
        "sort_order": 5,
        "layout_style": "locked_cards",
        "source_type": "automatic",
        "item_limit": 3,
        "config": {"vault_item_ids": []},
    },
    {
        "block_type": "sponsor_packages",
        "title_override": "Sponsorship",
        "description_override": "Partner with this host on Pàdéyá.",
        "is_visible": True,
        "sort_order": 6,
        "layout_style": "cta_panel",
        "source_type": "automatic",
        "item_limit": 3,
    },
    {
        "block_type": "related_discovery",
        "title_override": "Keep exploring",
        "description_override": "Related hosts, cities, and scenes on Pàdéyá.",
        "is_visible": True,
        "sort_order": 7,
        "layout_style": "discovery_row",
        "source_type": "automatic",
        "item_limit": 6,
    },
    {
        "block_type": "photo_gallery",
        "title_override": "Gallery",
        "description_override": None,
        "is_visible": False,
        "sort_order": 8,
        "layout_style": "gallery_grid",
        "source_type": "manual",
        "item_limit": 12,
    },
    {
        "block_type": "featured_video",
        "title_override": "Featured video",
        "description_override": None,
        "is_visible": False,
        "sort_order": 9,
        "layout_style": "video_embed",
        "source_type": "manual",
        "item_limit": 1,
    },
    {
        "block_type": "faq",
        "title_override": "FAQ",
        "description_override": None,
        "is_visible": False,
        "sort_order": 10,
        "layout_style": "accordion",
        "source_type": "manual",
        "item_limit": None,
    },
    {
        "block_type": "contact_cta",
        "title_override": "Get in touch",
        "description_override": "Reach this host for bookings, collabs, or press.",
        "is_visible": True,
        "sort_order": 11,
        "layout_style": "cta_panel",
        "source_type": "automatic",
        "item_limit": None,
    },
]

# Layout styles hosts can pick for the Vault Preview block on Legacy
VAULT_PREVIEW_LAYOUTS = (
    "locked_cards",
    "featured_spotlight",
    "compact_row",
)

DEFAULT_TIERS: list[dict] = [
    {
        "slug": "new-host",
        "name": "New Host",
        "rank": 0,
        "min_score": Decimal("0"),
        "description": "Just getting started on Pàdéyá.",
        "requirements": {
            "min_completed_events": 0,
            "min_tickets_sold": 0,
            "min_verified_checkins": 0,
            "min_average_rating": None,
            "min_review_count": 0,
        },
    },
    {
        "slug": "rising",
        "name": "Rising",
        "rank": 1,
        "min_score": Decimal("20"),
        "description": "Early traction with real check-ins and reviews.",
        "requirements": {
            "min_completed_events": 1,
            "min_tickets_sold": 25,
            "min_verified_checkins": 10,
            "min_average_rating": 3.5,
            "min_review_count": 1,
        },
    },
    {
        "slug": "established",
        "name": "Established",
        "rank": 2,
        "min_score": Decimal("40"),
        "description": "Consistent host with solid verified feedback.",
        "requirements": {
            "min_completed_events": 3,
            "min_tickets_sold": 150,
            "min_verified_checkins": 75,
            "min_average_rating": 4.0,
            "min_review_count": 5,
        },
    },
    {
        "slug": "certified",
        "name": "Certified",
        "rank": 3,
        "min_score": Decimal("55"),
        "description": "Trusted host with strong attendance and ratings.",
        "requirements": {
            "min_completed_events": 6,
            "min_tickets_sold": 500,
            "min_verified_checkins": 250,
            "min_average_rating": 4.2,
            "min_review_count": 12,
        },
    },
    {
        "slug": "icon",
        "name": "Icon",
        "rank": 4,
        "min_score": Decimal("70"),
        "description": "Standout reputation across many completed events.",
        "requirements": {
            "min_completed_events": 12,
            "min_tickets_sold": 1500,
            "min_verified_checkins": 800,
            "min_average_rating": 4.4,
            "min_review_count": 30,
        },
    },
    {
        "slug": "legend",
        "name": "Legend",
        "rank": 5,
        "min_score": Decimal("85"),
        "description": "Top-tier Legacy — rare and hard-earned.",
        "requirements": {
            "min_completed_events": 25,
            "min_tickets_sold": 5000,
            "min_verified_checkins": 2500,
            "min_average_rating": 4.6,
            "min_review_count": 75,
        },
    },
]
