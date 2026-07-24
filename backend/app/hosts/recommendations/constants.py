"""Host recommendation scoring — rules-only, fan-safe signals."""

SCORE_MAX = 100
SCORE_MIN_SHOW = 35

LABEL_STRONG = "Great match"
LABEL_GOOD = "Good match"
LABEL_SIMILAR = "Worth a look"
SCORE_LABEL_STRONG = 80
SCORE_LABEL_GOOD = 60

RECOMMENDATIONS_CAP = 12
CANDIDATE_POOL_SIZE = 120
DISMISS_EXCLUDE_DAYS = 60
CATEGORY_HIDE_DAYS = 90
FEEDBACK_IGNORE_THRESHOLD = 3

COLD_START_BASELINE = "baseline"
COLD_START_OFF = "off"

# Interest / attendance
SCORE_ATTENDED_HOST = 26
SCORE_TICKETED_HOST = 20
SCORE_CATEGORY_MATCH = 18
SCORE_SIMILAR_TO_FOLLOWED = 16
SCORE_SIMILAR_TO_FOLLOWED_MAX = 32

# Social graph
SCORE_NETWORK_FOLLOWS = 8
SCORE_NETWORK_FOLLOWS_MAX = 16

# Location
SCORE_CITY_MATCH = 14
SCORE_NEARBY_WITHIN_10KM = 12
SCORE_NEARBY_WITHIN_25KM = 8

# Trust / activity
SCORE_VERIFIED = 8
SCORE_UPCOMING_EVENT = 10
SCORE_UPCOMING_SOON = 10
SCORE_TRUST_CHECKINS = 6
SCORE_TRUST_CHECKINS_CAP = 12
SCORE_TRUST_RATING = 6
SCORE_COLD_START_BASELINE = 22

# Feedback
SCORE_PENALTY_DISMISSED = 30
SCORE_PENALTY_IGNORED = 12
SCORE_PENALTY_CATEGORY = 18
SCORE_BOOST_MORE_LIKE = 10
SCORE_BOOST_CLICK = 5
SCORE_BOOST_FOLLOW = 8

NEARBY_DEFAULT_RADIUS_KM = 25
UPCOMING_SOON_DAYS = 7

MAX_HOSTS_PER_CATEGORY = 3
MAX_HOSTS_PER_CITY = 4

# Safe reason codes
REASON_ATTENDED = "attended_host"
REASON_TICKETED = "ticketed_host"
REASON_SIMILAR_FOLLOWED = "similar_to_followed"
REASON_NETWORK_FOLLOWS = "network_follows"
REASON_CATEGORY = "shared_category"
REASON_CITY = "shared_city"
REASON_NEARBY = "nearby"
REASON_UPCOMING = "upcoming_events"
REASON_UPCOMING_SOON = "upcoming_soon"
REASON_TRUST = "trust_signals"
REASON_VERIFIED = "verified_host"

# User-facing labels (never include private data)
REASON_LABELS: dict[str, str] = {
    REASON_ATTENDED: "You attended similar events",
    REASON_TICKETED: "You attended similar events",
    REASON_SIMILAR_FOLLOWED: "Similar to hosts you follow",
    REASON_NETWORK_FOLLOWS: "Popular with fans you’re connected to",
    REASON_CATEGORY: "Matches your interests",
    REASON_CITY: "Hosting near your city",
    REASON_NEARBY: "Hosting near your city",
    REASON_UPCOMING: "Has upcoming events on Pàdéyá",
    REASON_UPCOMING_SOON: "Upcoming events this week",
    REASON_TRUST: "Strong verified reviews on Pàdéyá",
    REASON_VERIFIED: "Verified host",
}

FEEDBACK_IMPRESSION = "impression"
FEEDBACK_CLICK = "click"
FEEDBACK_DISMISS = "dismiss"
FEEDBACK_NOT_INTERESTED = "not_interested"
FEEDBACK_MORE_LIKE_THIS = "more_like_this"
FEEDBACK_HIDE_CATEGORY = "hide_category"
FEEDBACK_FOLLOW = "follow"
FEEDBACK_ACTIONS = frozenset(
    {
        FEEDBACK_IMPRESSION,
        FEEDBACK_CLICK,
        FEEDBACK_DISMISS,
        FEEDBACK_NOT_INTERESTED,
        FEEDBACK_MORE_LIKE_THIS,
        FEEDBACK_HIDE_CATEGORY,
        FEEDBACK_FOLLOW,
    }
)

SURFACE_DASHBOARD_HOSTS_FOR_YOU = "dashboard_hosts_for_you"
SURFACE_DASHBOARD_OVERVIEW = "dashboard_overview"
SURFACE_HOSTS_RAIL = "hosts_recommended_rail"
SURFACE_HOSTS_SORT = "hosts_sort_recommended"

# Legacy aliases
SURFACE_DASHBOARD = SURFACE_DASHBOARD_OVERVIEW
SURFACE_HOSTS_RAIL_LEGACY = "hosts_rail"
