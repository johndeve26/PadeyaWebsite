"""Default taxonomy vocabulary seeds."""

from __future__ import annotations

# Expanded catalog: all countries + full Nigeria states/cities/areas (+ key markets).
# State/city may share the same slug (e.g. lagos); resolve with kind + slug.
from app.taxonomy.location_catalog import DEFAULT_LOCATIONS

# (name, slug, description)
DEFAULT_TAGS: list[tuple[str, str, str]] = [
    ("Live Music", "live-music", "Live performances and concerts"),
    ("Open Mic", "open-mic", "Open mic and amateur nights"),
    ("Networking", "networking", "Meetups and networking"),
    ("Outdoor", "outdoor", "Outdoor and open-air events"),
    ("Free Entry", "free-entry", "Free or RSVP-only entry"),
    ("VIP", "vip", "VIP and premium experiences"),
    ("After Party", "after-party", "After-parties and late sessions"),
    ("Workshop", "workshop", "Hands-on workshops"),
    ("Worship", "worship", "Worship and faith gatherings"),
    ("Founders", "founders", "Founder and startup community"),
]

DEFAULT_VIBES: list[tuple[str, str, str]] = [
    ("Afrobeats Energy", "afrobeats-energy", "High-energy Afrobeats nights"),
    ("Chill", "chill", "Relaxed and low-key"),
    ("High Energy", "high-energy", "Loud, dance-forward energy"),
    ("Intimate", "intimate", "Small and close-knit"),
    ("Family Friendly", "family-friendly", "Welcoming for families"),
    ("Late Night", "late-night", "Late-night club and party vibes"),
    ("Community", "community", "Community-first gatherings"),
    ("Inspirational", "inspirational", "Uplifting and faith-forward"),
]

DEFAULT_AUDIENCE_TYPES: list[tuple[str, str, str]] = [
    ("Adults 18+", "adults-18", "Adult audiences"),
    ("Students", "students", "Campus and student crowds"),
    ("Professionals", "professionals", "Working professionals"),
    ("Families", "families", "Family audiences"),
    ("Couples", "couples", "Date-night crowds"),
    ("Faith Community", "faith-community", "Faith and gospel audiences"),
]

DEFAULT_HOST_TYPES: list[tuple[str, str, str]] = [
    ("DJ / Artist", "dj-artist", "DJs and performing artists"),
    ("Promoter", "promoter", "Event promoters"),
    ("Venue Operator", "venue-operator", "Venues that host events"),
    ("Faith Organization", "faith-organization", "Churches and faith orgs"),
    ("Comedy Collective", "comedy-collective", "Comedy clubs and collectives"),
    ("Tech Community", "tech-community", "Tech meetups and founder groups"),
    ("Lifestyle Brand", "lifestyle-brand", "Lifestyle and social brands"),
]

DEFAULT_VENUE_TYPES: list[tuple[str, str, str]] = [
    ("Club", "club", "Nightclubs and party venues"),
    ("Outdoor", "outdoor", "Parks, beaches, open spaces"),
    ("Rooftop", "rooftop", "Rooftop venues"),
    ("Church / Hall", "church-hall", "Churches and worship halls"),
    ("Conference Hall", "conference-hall", "Conference and meeting halls"),
    ("Campus", "campus", "Campus venues"),
    ("Restaurant / Lounge", "restaurant-lounge", "Restaurants and lounges"),
]

# Legacy state slugs renamed for kind-prefixed public hubs (/events/state/lagos).
LEGACY_LOCATION_SLUG_RENAMES: list[tuple[str, str, str]] = [
    ("state", "lagos-state", "lagos"),
    ("state", "oyo-state", "oyo"),
]

# Popular shortcuts for /events location filter (kind, slug, label).
POPULAR_LOCATION_SHORTCUTS: list[tuple[str, str, str]] = [
    ("city", "lagos", "Lagos"),
    ("city", "ibadan", "Ibadan"),
    ("city", "abuja", "Abuja"),
    ("city", "akure", "Akure"),
    ("area", "victoria-island", "Victoria Island"),
    ("area", "lekki", "Lekki"),
    ("area", "ikeja", "Ikeja"),
    ("area", "yaba", "Yaba"),
    ("area", "mainland", "Lagos Mainland"),
]

# Demo host → taxonomy assignments
DEMO_HOST_TAXONOMY: dict[str, dict[str, object]] = {
    "djmaze": {
        "host_types": ["dj-artist", "promoter"],
        "categories": ["nightlife", "music"],
        "tags": ["live-music", "vip", "after-party"],
        "vibes": ["afrobeats-energy", "late-night", "high-energy"],
        "audience": ["adults-18"],
        "location_slugs": ["lagos", "lekki", "victoria-island"],
        "primary_location": "lagos",
        "sponsor_ready": True,
    },
    "lagoscomedyhub": {
        "host_types": ["comedy-collective", "promoter"],
        "categories": ["comedy"],
        "tags": ["open-mic"],
        "vibes": ["community", "intimate"],
        "audience": ["adults-18", "professionals"],
        "location_slugs": ["lagos", "victoria-island"],
        "primary_location": "lagos",
        "sponsor_ready": True,
    },
    "techconnectafrica": {
        "host_types": ["tech-community"],
        "categories": ["tech", "business"],
        "tags": ["networking", "founders", "workshop"],
        "vibes": ["community"],
        "audience": ["professionals"],
        "location_slugs": ["lagos", "yaba"],
        "primary_location": "lagos",
        "sponsor_ready": True,
    },
    "praiseexperience": {
        "host_types": ["faith-organization"],
        "categories": ["gospel"],
        "tags": ["worship"],
        "vibes": ["inspirational", "community"],
        "audience": ["faith-community", "families"],
        "location_slugs": ["ibadan"],
        "primary_location": "ibadan",
        "sponsor_ready": False,
    },
    "mainlandvibes": {
        "host_types": ["lifestyle-brand", "promoter"],
        "categories": ["lifestyle", "art-culture"],
        "tags": ["outdoor", "free-entry"],
        "vibes": ["community", "high-energy"],
        "audience": ["students", "adults-18"],
        "location_slugs": ["lagos", "mainland", "yaba"],
        "primary_location": "lagos",
        "sponsor_ready": True,
    },
}

# Event category slug → default tags / vibes / audience for demo dual-write
DEMO_CATEGORY_TAXONOMY: dict[str, dict[str, list[str]]] = {
    "music": {
        "tags": ["live-music", "vip"],
        "vibes": ["afrobeats-energy", "high-energy"],
        "audience": ["adults-18"],
    },
    "nightlife": {
        "tags": ["after-party", "vip"],
        "vibes": ["late-night", "high-energy"],
        "audience": ["adults-18"],
    },
    "comedy": {
        "tags": ["open-mic"],
        "vibes": ["community", "intimate"],
        "audience": ["adults-18"],
    },
    "tech": {
        "tags": ["networking", "founders", "workshop"],
        "vibes": ["community"],
        "audience": ["professionals"],
    },
    "gospel": {
        "tags": ["worship"],
        "vibes": ["inspirational"],
        "audience": ["faith-community"],
    },
    "lifestyle": {
        "tags": ["outdoor", "free-entry"],
        "vibes": ["community", "high-energy"],
        "audience": ["students", "adults-18"],
    },
    "campus": {
        "tags": ["free-entry"],
        "vibes": ["community"],
        "audience": ["students"],
    },
    "business": {
        "tags": ["networking", "founders"],
        "vibes": ["community"],
        "audience": ["professionals"],
    },
    "food-drink": {
        "tags": ["outdoor"],
        "vibes": ["chill", "community"],
        "audience": ["adults-18"],
    },
    "art-culture": {
        "tags": ["outdoor"],
        "vibes": ["chill", "community"],
        "audience": ["adults-18", "families"],
    },
    "sports": {
        "tags": ["outdoor"],
        "vibes": ["high-energy", "community"],
        "audience": ["adults-18", "families"],
    },
}

CITY_TO_LOCATION_SLUG: dict[str, str] = {
    "Lagos": "lagos",
    "Ibadan": "ibadan",
    "Akure": "akure",
    "Abuja": "abuja",
    "Lagos Mainland": "mainland",
    "Mainland": "mainland",
    "Lekki": "lekki",
    "Victoria Island": "victoria-island",
    "Yaba": "yaba",
    "Ikeja": "ikeja",
}

# Demo event key (without demo- prefix) → taxonomy location (kind, slug).
# Leaf nodes preferred so country/state/city/area discovery all resolve via ancestry.
DEMO_EVENT_LOCATIONS: dict[str, tuple[str, str]] = {
    "mainland-vibes-summer": ("area", "mainland"),
    "afrobeats-night-live": ("area", "lekki"),
    "lagos-comedy-jam": ("area", "victoria-island"),
    "founders-mixer-lagos": ("area", "yaba"),
    "praise-experience-live": ("city", "ibadan"),
    "campus-fest-2026": ("area", "yaba"),
    "rooftop-games-night": ("area", "ikeja"),
    "product-builders-meetup": ("area", "yaba"),
    "detty-friday-live": ("area", "lekki"),
    "island-comedy-night": ("area", "victoria-island"),
    "mainland-vibes-2025": ("area", "mainland"),
    "worship-under-stars": ("city", "ibadan"),
    "startup-demo-evening": ("area", "ikeja"),
    "draft-secret-session": ("area", "lekki"),
    "draft-open-mic": ("area", "victoria-island"),
    "draft-founder-lab": ("area", "yaba"),
    "pending-neon-nights": ("area", "lekki"),
    "pending-gospel-choir": ("city", "akure"),
    "cancelled-beach-bash": ("area", "lekki"),
    "rejected-stadium-show": ("city", "lagos"),
    "food-and-flow": ("area", "mainland"),
    "art-walk-lagos": ("area", "lekki"),
    "sports-sunday": ("city", "abuja"),
}

LOCATION_PARENT_KIND: dict[str, str] = {
    "state": "country",
    "city": "state",
    "area": "city",
}
