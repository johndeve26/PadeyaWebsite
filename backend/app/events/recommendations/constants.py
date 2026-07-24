"""Event recommendation scoring — rules-only, fan-safe signals."""

SCORE_MAX = 100
SCORE_MIN_SHOW = 35

RECOMMENDATIONS_CAP = 12
CANDIDATE_POOL_SIZE = 200
DISMISS_EXCLUDE_DAYS = 60
CATEGORY_HIDE_DAYS = 90
HOST_HIDE_DAYS = 90
FEEDBACK_IGNORE_THRESHOLD = 3

COLD_START_BASELINE = "baseline"
COLD_START_OFF = "off"

# Group caps (spec)
CAP_INTEREST = 30
CAP_HOST = 20
CAP_LOCATION = 20
CAP_SOCIAL = 15
CAP_TRUST = 15
CAP_FRESHNESS = 10

# Interest
PTS_CATEGORY_MATCH = 18
PTS_SIMILAR_ATTENDED = 16
PTS_PASSPORT_CATEGORY = 14

# Host
PTS_FOLLOWED_HOST = 16
PTS_ATTENDED_HOST = 12
PTS_TICKETED_HOST = 10

# Location
PTS_CITY_MATCH = 14
PTS_AREA_MATCH = 10

# Social
PTS_NETWORK_ATTENDING = 10
PTS_NETWORK_HOST_FOLLOWS = 8

# Trust / activity
PTS_VERIFIED_HOST = 6
PTS_FEATURED = 5
PTS_PADEYA_PICK = 6
PTS_UPCOMING_SOON = 8
PTS_RECENTLY_PUBLISHED = 4

# Feedback
SCORE_PENALTY_DISMISSED = 30
SCORE_PENALTY_IGNORED = 12
SCORE_PENALTY_CATEGORY = 16
SCORE_PENALTY_HOST = 14
SCORE_BOOST_MORE_LIKE = 10

UPCOMING_SOON_DAYS = 7
WEEKEND_DAYS = 7

MAX_EVENTS_PER_HOST = 3
MAX_EVENTS_PER_CATEGORY = 4
MAX_EVENTS_PER_CITY = 5

MODES = frozenset(
    {
        "recommended",
        "near_you",
        "similar_to_attended",
        "followed_hosts",
        "friends_going",
        "trending",
    }
)
DEFAULT_MODE = "recommended"

REASON_SIMILAR_ATTENDED = "similar_attended"
REASON_FOLLOWED_HOST = "followed_host"
REASON_CITY = "near_city"
REASON_NETWORK = "network_fans"
REASON_CATEGORY = "category_match"
REASON_WEEKEND = "this_weekend"
REASON_VERIFIED = "verified_host"
REASON_PICK = "padeya_pick"
REASON_FEATURED = "featured"
REASON_POPULAR_CITY = "popular_city"
REASON_UPCOMING = "upcoming_soon"

REASON_LABELS: dict[str, str] = {
    REASON_SIMILAR_ATTENDED: "Similar to events you attended",
    REASON_FOLLOWED_HOST: "From a host you follow",
    REASON_CITY: "Happening near your city",
    REASON_NETWORK: "Popular with fans you’re connected to",
    REASON_CATEGORY: "Matches your interests",
    REASON_WEEKEND: "This weekend",
    REASON_VERIFIED: "From a verified host",
    REASON_PICK: "Pàdéyá Pick",
    REASON_FEATURED: "Featured on Pàdéyá",
    REASON_POPULAR_CITY: "Popular in your city",
    REASON_UPCOMING: "Happening soon",
}

FEEDBACK_VIEWED = "viewed"
FEEDBACK_CLICKED = "clicked"
FEEDBACK_SAVED = "saved"
FEEDBACK_PURCHASED = "purchased"
FEEDBACK_DISMISS = "dismissed"
FEEDBACK_NOT_INTERESTED = "not_interested"
FEEDBACK_HIDE_CATEGORY = "hide_category"
FEEDBACK_HIDE_HOST = "hide_host"
FEEDBACK_MORE_LIKE_THIS = "more_like_this"

FEEDBACK_ACTIONS = frozenset(
    {
        FEEDBACK_VIEWED,
        FEEDBACK_CLICKED,
        FEEDBACK_SAVED,
        FEEDBACK_PURCHASED,
        FEEDBACK_DISMISS,
        FEEDBACK_NOT_INTERESTED,
        FEEDBACK_HIDE_CATEGORY,
        FEEDBACK_HIDE_HOST,
        FEEDBACK_MORE_LIKE_THIS,
    }
)

SURFACE_DASHBOARD = "dashboard_events_for_you"
SURFACE_EVENTS_RAIL = "events_recommended_rail"
SURFACE_EVENTS_SORT = "events_sort_recommended"
SURFACE_EVENT_DETAIL = "event_detail_recommended"
