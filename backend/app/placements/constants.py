"""Featured Placement Slots / Pàdéyá Picks constants."""

from __future__ import annotations

# Public surface: "Pàdéyá Picks". Admin surface: "Featured Placement Slots".
SLOT_NUMBERS = (1, 2)

SLOT_LABELS: dict[int, str] = {
    1: "Primary Spotlight",
    2: "Secondary Spotlight",
}

# placement_type (surface)
PLACEMENT_HOMEPAGE = "homepage"
PLACEMENT_EVENTS_PAGE = "events_page"
PLACEMENT_COUNTRY_PAGE = "country_page"
PLACEMENT_STATE_PAGE = "state_page"
PLACEMENT_CITY_PAGE = "city_page"
PLACEMENT_AREA_PAGE = "area_page"
PLACEMENT_CATEGORY_PAGE = "category_page"
PLACEMENT_CITY_CATEGORY_PAGE = "city_category_page"

PLACEMENT_TYPES = (
    PLACEMENT_HOMEPAGE,
    PLACEMENT_EVENTS_PAGE,
    PLACEMENT_COUNTRY_PAGE,
    PLACEMENT_STATE_PAGE,
    PLACEMENT_CITY_PAGE,
    PLACEMENT_AREA_PAGE,
    PLACEMENT_CATEGORY_PAGE,
    PLACEMENT_CITY_CATEGORY_PAGE,
)

# context_type (targeting dimension)
CONTEXT_GLOBAL = "global"
CONTEXT_COUNTRY = "country"
CONTEXT_STATE = "state"
CONTEXT_CITY = "city"
CONTEXT_AREA = "area"
CONTEXT_CATEGORY = "category"
CONTEXT_CITY_CATEGORY = "city_category"

CONTEXT_TYPES = (
    CONTEXT_GLOBAL,
    CONTEXT_COUNTRY,
    CONTEXT_STATE,
    CONTEXT_CITY,
    CONTEXT_AREA,
    CONTEXT_CATEGORY,
    CONTEXT_CITY_CATEGORY,
)

STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_SCHEDULED = "scheduled"
STATUS_EXPIRED = "expired"
STATUS_ARCHIVED = "archived"

STATUSES = (
    STATUS_DRAFT,
    STATUS_ACTIVE,
    STATUS_SCHEDULED,
    STATUS_EXPIRED,
    STATUS_ARCHIVED,
)

PUBLIC_LIVE_STATUSES = frozenset({STATUS_ACTIVE, STATUS_SCHEDULED})

PLACEMENT_LABELS: dict[str, str] = {
    PLACEMENT_HOMEPAGE: "Global homepage",
    PLACEMENT_EVENTS_PAGE: "Events page",
    PLACEMENT_COUNTRY_PAGE: "Country page",
    PLACEMENT_STATE_PAGE: "State page",
    PLACEMENT_CITY_PAGE: "City page",
    PLACEMENT_AREA_PAGE: "Area page",
    PLACEMENT_CATEGORY_PAGE: "Category page",
    PLACEMENT_CITY_CATEGORY_PAGE: "City + category page",
}

# Accept legacy public/admin aliases used before featured_placements rename.
LEGACY_CONTEXT_TO_PLACEMENT: dict[str, str] = {
    "global_homepage": PLACEMENT_HOMEPAGE,
    "events": PLACEMENT_EVENTS_PAGE,
    "country": PLACEMENT_COUNTRY_PAGE,
    "state": PLACEMENT_STATE_PAGE,
    "city": PLACEMENT_CITY_PAGE,
    "area": PLACEMENT_AREA_PAGE,
    "category": PLACEMENT_CATEGORY_PAGE,
    "city_category": PLACEMENT_CITY_CATEGORY_PAGE,
    # Already-canonical names
    PLACEMENT_HOMEPAGE: PLACEMENT_HOMEPAGE,
    PLACEMENT_EVENTS_PAGE: PLACEMENT_EVENTS_PAGE,
    PLACEMENT_COUNTRY_PAGE: PLACEMENT_COUNTRY_PAGE,
    PLACEMENT_STATE_PAGE: PLACEMENT_STATE_PAGE,
    PLACEMENT_CITY_PAGE: PLACEMENT_CITY_PAGE,
    PLACEMENT_AREA_PAGE: PLACEMENT_AREA_PAGE,
    PLACEMENT_CATEGORY_PAGE: PLACEMENT_CATEGORY_PAGE,
    PLACEMENT_CITY_CATEGORY_PAGE: PLACEMENT_CITY_CATEGORY_PAGE,
}

# Back-compat aliases for older code paths
SLOT_INDEXES = SLOT_NUMBERS
CONTEXT_GLOBAL_HOMEPAGE = PLACEMENT_HOMEPAGE
CONTEXT_EVENTS = PLACEMENT_EVENTS_PAGE
CONTEXT_TYPES_LEGACY = (
    "global_homepage",
    "events",
    "country",
    "state",
    "city",
    "category",
    "city_category",
)
CONTEXT_LABELS = PLACEMENT_LABELS
LOCATION_CONTEXTS = frozenset(
    {
        PLACEMENT_COUNTRY_PAGE,
        PLACEMENT_STATE_PAGE,
        PLACEMENT_CITY_PAGE,
        PLACEMENT_AREA_PAGE,
        PLACEMENT_CITY_CATEGORY_PAGE,
        "country",
        "state",
        "city",
        "area",
        "city_category",
    }
)
CATEGORY_CONTEXTS = frozenset(
    {
        PLACEMENT_CATEGORY_PAGE,
        PLACEMENT_CITY_CATEGORY_PAGE,
        "category",
        "city_category",
    }
)
