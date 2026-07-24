"""Fan Connect statuses, policies, and limits."""

# Connection statuses (stored on fan_connections.status)
STATUS_SUGGESTED = "suggested"
STATUS_REQUEST_SENT = "request_sent"
STATUS_REQUEST_RECEIVED = "request_received"  # viewer-facing alias; prefer request_sent in DB
STATUS_CONNECTED = "connected"
STATUS_DECLINED = "declined"
STATUS_BLOCKED = "blocked"
STATUS_REMOVED = "removed"

# Open request statuses (DB stores request_sent for both parties)
OPEN_REQUEST_STATUSES = frozenset({STATUS_REQUEST_SENT, STATUS_REQUEST_RECEIVED})
CONNECTED_STATUSES = frozenset({STATUS_CONNECTED})
TERMINAL_STATUSES = frozenset(
    {STATUS_DECLINED, STATUS_BLOCKED, STATUS_REMOVED}
)

# Request policies (fan_connect_settings.request_policy / request_policies)
POLICY_SAME_EVENT = "same_event"
POLICY_SAME_HOST = "same_host"
POLICY_PUBLIC_PASSPORTS = "public_passports"
POLICY_NOBODY = "nobody"
REQUEST_POLICIES = frozenset(
    {
        POLICY_SAME_EVENT,
        POLICY_SAME_HOST,
        POLICY_PUBLIC_PASSPORTS,
        POLICY_NOBODY,
    }
)
REQUEST_POLICY_OPTIONS = (
    POLICY_SAME_EVENT,
    POLICY_SAME_HOST,
    POLICY_PUBLIC_PASSPORTS,
)
REQUEST_POLICY_RANK = {
    POLICY_NOBODY: 0,
    POLICY_SAME_EVENT: 1,
    POLICY_SAME_HOST: 2,
    POLICY_PUBLIC_PASSPORTS: 3,
}

# Report statuses
REPORT_OPEN = "open"
REPORT_REVIEWING = "reviewing"
REPORT_RESOLVED = "resolved"
REPORT_DISMISSED = "dismissed"

SELF_CONNECT_DETAIL = "You can’t connect with yourself."
SELF_REPORT_DETAIL = "You can’t report yourself."
SELF_BLOCK_DETAIL = "You can’t block yourself."

MAX_INTRO_LENGTH = 280
REQUESTS_PER_HOUR = 10
SUGGESTIONS_CAP = 12
DECLINE_COOLDOWN_DAYS = 14

# Matching score (FanConnectScoringService) — range 0–100
SCORE_MAX = 100
SCORE_MIN_SHOW = 40
SCORE_LABEL_STRONG = 80
SCORE_LABEL_GOOD = 60
LABEL_STRONG = "Strong connection"
LABEL_GOOD = "Good connection"
LABEL_SIMILAR = "Similar interests"

SCORE_BAND_STRONG = "strong"
SCORE_BAND_GOOD = "good"
SCORE_BAND_SIMILAR = "similar"
SCORE_BAND_HIDDEN = "hidden"

CTA_CONNECT = "connect"
CTA_REQUEST_PENDING = "request_pending"
CTA_MESSAGE = "message"
CTA_BLOCKED = "blocked"
CTA_UNAVAILABLE = "unavailable"
CTA_DECLINE_COOLDOWN = "decline_cooldown"

# --- Exact weighted model (product) ---
# Core event / social
SCORE_SAME_UPCOMING_EVENT = 35
SCORE_SHARED_CHECKED_IN = 25
# FoF = shared accepted neighbors (connection-of-connection). When FoF fires,
# do NOT also add SCORE_MUTUAL_CONNECTION — same graph signal, avoid double-count.
SCORE_FRIEND_OF_FRIEND = 20
# Reserved for a distinct reciprocal-interest signal; unused while FoF covers overlap.
SCORE_MUTUAL_CONNECTION = 15
SCORE_SHARED_HOST = 10
SCORE_SHARED_CATEGORY = 15  # passport favorite categories ∩
SCORE_PASSPORT_COMPLETE = 5
SCORE_BOTH_RECENTLY_ACTIVE = 5

# Geolocation (actor-only lat/lng vs privacy-safe discovery points / city centroids)
SCORE_NEARBY_WITHIN_2KM = 25
SCORE_NEARBY_WITHIN_5KM = 20
SCORE_NEARBY_WITHIN_10KM = 15
SCORE_NEARBY_WITHIN_25KM = 10
SCORE_SHARED_CITY = 10
SCORE_SHARED_AREA_OR_ZONE = 10

# Personalized place matching (public-safe ticket/event signals)
SCORE_SIMILAR_ATTENDED_CATEGORIES = 15
SCORE_SIMILAR_VENUE_TYPES = 10
SCORE_SIMILAR_HOST_TYPES = 10
SCORE_OFTEN_SAME_AREA_CITY = 10
SCORE_SAME_SCENE = 10

# Feedback
SCORE_PENALTY_DISMISSED = 30
SCORE_PENALTY_REPEATEDLY_IGNORED = 10
SCORE_SIMILAR_PROFILE_VIEWS = 5
SCORE_SIMILAR_PROFILE_CONNECTS = 10

# Safety / trust soft penalties (hard excludes stay in hard_exclusions)
SCORE_PENALTY_RECENTLY_DECLINED = 40
SCORE_PENALTY_TOO_MANY_OUTGOING = 25
SCORE_PENALTY_LOW_TRUST = 15
SCORE_PENALTY_REPORT_RISK = 30

# Caps for multi-count signals (host follow still capped)
SCORE_SHARED_HOST_MAX = 20

# Deprecated — no longer stacked on upcoming
SCORE_BOTH_TICKETED_UPCOMING_EXTRA = 0
# Legacy aliases kept for older imports/tests migrating off caps
SCORE_SHARED_CATEGORY_MAX = SCORE_SHARED_CATEGORY
SCORE_SHARED_AREA_OR_PLACE = SCORE_SHARED_AREA_OR_ZONE
SCORE_SHARED_AREA_OR_PLACE_MAX = SCORE_SHARED_AREA_OR_ZONE
SCORE_NEARBY_SHARED_EVENT = SCORE_NEARBY_WITHIN_10KM
SCORE_NEARBY_PUBLIC_CITY = SCORE_SHARED_CITY
SCORE_SHARED_BADGE = 0
SCORE_SHARED_BADGE_MAX = 0

SCORE_OUTGOING_REQUEST_THRESHOLD = 5
SCORE_NEW_ACCOUNT_DAYS = 7
SCORE_RECENT_ACTIVE_DAYS = 30
SCORE_SERIOUS_REPORT_COUNT = 3
DISMISS_EXCLUDE_DAYS = 60
NEARBY_DEFAULT_RADIUS_KM = 25
FEEDBACK_IGNORE_THRESHOLD = 3  # impressions without click/connect → repeatedly ignored
NEW_PASSPORT_DAYS = 21

# Suggestion modes (GET /fan-connect/suggestions?mode=)
MODE_MIXED = "mixed"
MODE_NEAR_ME = "near_me"
MODE_SAME_EVENT = "same_event"
MODE_CONNECTIONS_OF_CONNECTIONS = "connections_of_connections"
MODE_SAME_INTERESTS = "same_interests"
MODE_NEW_PEOPLE = "new_people"
SUGGESTION_MODES = frozenset(
    {
        MODE_MIXED,
        MODE_NEAR_ME,
        MODE_SAME_EVENT,
        MODE_CONNECTIONS_OF_CONNECTIONS,
        MODE_SAME_INTERESTS,
        MODE_NEW_PEOPLE,
    }
)

# Diversity mixer quotas per page of SUGGESTIONS_CAP (mixed / Best matches)
DIVERSITY_QUOTA_STRONG = 3
DIVERSITY_QUOTA_NEARBY = 3
DIVERSITY_QUOTA_FOF = 2
DIVERSITY_QUOTA_SHARED_EVENT = 2
DIVERSITY_QUOTA_FRESH = 2

# Feedback actions
FEEDBACK_IMPRESSION = "impression"
FEEDBACK_CLICK = "click"
FEEDBACK_DISMISS = "dismiss"
FEEDBACK_MORE_LIKE_THIS = "more_like_this"
FEEDBACK_CONNECT_REQUEST = "connect_request"
FEEDBACK_ACTIONS = frozenset(
    {
        FEEDBACK_IMPRESSION,
        FEEDBACK_CLICK,
        FEEDBACK_DISMISS,
        FEEDBACK_MORE_LIKE_THIS,
        FEEDBACK_CONNECT_REQUEST,
    }
)

# Location preference precision — never store raw browser GPS by default
LOCATION_PRECISION_CITY = "city"
LOCATION_PRECISION_AREA = "area"
LOCATION_PRECISION_APPROXIMATE = "approximate"
LOCATION_PRECISIONS = frozenset(
    {
        LOCATION_PRECISION_CITY,
        LOCATION_PRECISION_AREA,
        LOCATION_PRECISION_APPROXIMATE,
    }
)

SERIOUS_REPORT_KEYWORDS = (
    "harass",
    "threat",
    "sexual",
    "scam",
    "abuse",
    "underage",
    "violence",
    "stalk",
    "assault",
)

# Safe reason codes only — never private venue/ticket/order/payment details.
REASON_SHARED_PUBLIC_EVENT = "shared_public_event"
REASON_SHARED_UPCOMING_EVENT = "shared_upcoming_event"
REASON_SHARED_CHECKED_IN = "shared_checked_in"
REASON_SHARED_HOST = "shared_host"
REASON_SHARED_CATEGORY = "shared_category"
REASON_SHARED_CITY = "shared_city"
REASON_SHARED_BADGE = "shared_badge"
REASON_FRIEND_OF_FRIEND = "friend_of_friend"
REASON_NEARBY = "nearby"
REASON_NEARBY_EVENT = "nearby_shared_event"
REASON_NEARBY_CITY = "nearby_city"
REASON_SHARED_PLACE = "shared_place_or_scene"
SAFE_REASON_CODES = frozenset(
    {
        REASON_SHARED_PUBLIC_EVENT,
        REASON_SHARED_UPCOMING_EVENT,
        REASON_SHARED_CHECKED_IN,
        REASON_SHARED_HOST,
        REASON_SHARED_CATEGORY,
        REASON_SHARED_CITY,
        REASON_SHARED_BADGE,
        REASON_FRIEND_OF_FRIEND,
        REASON_NEARBY,
        REASON_NEARBY_EVENT,
        REASON_NEARBY_CITY,
        REASON_SHARED_PLACE,
    }
)

CONTACT_PATTERNS = (
    "whatsapp",
    "wa.me",
    "telegram",
    "call me",
    "my number",
    "my phone",
    "text me",
    "email me",
    "@gmail",
    "@yahoo",
    "http://",
    "https://",
)

# Legacy aliases used during migration / older tests
STATUS_PENDING = STATUS_REQUEST_SENT
STATUS_ACCEPTED = STATUS_CONNECTED
STATUS_CANCELLED = STATUS_REMOVED
STATUS_WITHDRAWN = STATUS_REMOVED
