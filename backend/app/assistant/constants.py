"""Constants for the Pàdéyá conversational assistant."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Product naming
# ---------------------------------------------------------------------------
PRODUCT_NAME = "Pàdéyá"
PUBLIC_PRODUCT_NAME = "Ask Pàdéyá"
AUTH_PRODUCT_NAME = "Pàdéyá Copilot"

# ---------------------------------------------------------------------------
# Safety levels (0 = read public, 5 = never execute)
# ---------------------------------------------------------------------------
SAFETY_LEVEL_PUBLIC_READ = 0
SAFETY_LEVEL_AUTH_READ = 1
SAFETY_LEVEL_NAVIGATE = 2
SAFETY_LEVEL_DRAFT = 3
SAFETY_LEVEL_MUTATE_CONFIRM = 4
SAFETY_LEVEL_FORBIDDEN = 5

SAFETY_LEVELS = frozenset(range(0, 6))

# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
MODE_PUBLIC = "public"
MODE_AUTHENTICATED = "authenticated"
ASSISTANT_MODES = frozenset({MODE_PUBLIC, MODE_AUTHENTICATED})

# ---------------------------------------------------------------------------
# Feature flag setting attribute names (on Settings)
# ---------------------------------------------------------------------------
FLAG_ASSISTANT_ENABLED = "assistant_enabled"
FLAG_ASSISTANT_PUBLIC_ENABLED = "assistant_public_enabled"
FLAG_ASSISTANT_AUTHENTICATED_ENABLED = "assistant_authenticated_enabled"
FLAG_ASSISTANT_ACTIONS_ENABLED = "assistant_actions_enabled"
FLAG_ASSISTANT_EVENT_SEARCH_ENABLED = "assistant_event_search_enabled"
FLAG_ASSISTANT_SUPPORT_DRAFTS_ENABLED = "assistant_support_drafts_enabled"
FLAG_ASSISTANT_ADMIN_ENABLED = "assistant_admin_enabled"
FLAG_ASSISTANT_KNOWLEDGE_SYNC_ENABLED = "assistant_knowledge_sync_enabled"

# ---------------------------------------------------------------------------
# Prompt version
# ---------------------------------------------------------------------------
PROMPT_VERSION = "assistant-system-v1"

# ---------------------------------------------------------------------------
# Session retention defaults (overridable via Settings)
# ---------------------------------------------------------------------------
DEFAULT_SESSION_RETENTION_DAYS = 30
DEFAULT_PUBLIC_SESSION_RETENTION_HOURS = 24
ANONYMOUS_COOKIE_NAME = "padeya_assistant_sid"
ANONYMOUS_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24  # 24h

# ---------------------------------------------------------------------------
# Sitemap forbidden path prefixes (mirror frontend SITEMAP_FORBIDDEN_PATH_PREFIXES)
# ---------------------------------------------------------------------------
SITEMAP_FORBIDDEN_PATH_PREFIXES: tuple[str, ...] = (
    "/admin",
    "/dashboard",
    "/host",
    "/sponsor",
    "/connect",
    "/messages",
    "/staff",
    "/ambassador",
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/checkout",
    "/team/invite",
    "/demo",
    "/account/appeal",
    "/api",
)

SITEMAP_FORBIDDEN_EXACT_PATHS: frozenset[str] = frozenset({"/events/search"})

# Allowed same-origin hosts for knowledge fetch
ALLOWED_KNOWLEDGE_HOST_SUFFIXES: tuple[str, ...] = (
    "padeya.com",
    "localhost",
    "127.0.0.1",
)

# ---------------------------------------------------------------------------
# Intent enum strings
# ---------------------------------------------------------------------------
INTENT_NAVIGATE = "navigate"
INTENT_SEARCH_EVENTS = "search_events"
INTENT_SEARCH_HOSTS = "search_hosts"
INTENT_SEARCH_PAGES = "search_pages"
INTENT_SEARCH_RESOURCES = "search_resources"
INTENT_SEARCH_PRODUCTS = "search_products"
INTENT_SEARCH_MEMORIES = "search_memories"
INTENT_EXPLAIN_PAGE = "explain_page"
INTENT_ACCOUNT = "account"
INTENT_TICKETS = "tickets"
INTENT_ORDERS = "orders"
INTENT_HOST_EVENTS = "host_events"
INTENT_SUPPORT = "support"
INTENT_PRICING = "pricing"
INTENT_INSIGHTS = "insights"
INTENT_CREATE_DRAFT = "create_draft"
INTENT_CONFIRM_ACTION = "confirm_action"
INTENT_HIGH_RISK = "high_risk"
INTENT_ABUSE = "abuse"
INTENT_INJECTION = "injection"
INTENT_CHITCHAT = "chitchat"
INTENT_UNKNOWN = "unknown"

INTENT_VALUES = frozenset(
    {
        INTENT_NAVIGATE,
        INTENT_SEARCH_EVENTS,
        INTENT_SEARCH_HOSTS,
        INTENT_SEARCH_PAGES,
        INTENT_SEARCH_RESOURCES,
        INTENT_SEARCH_PRODUCTS,
        INTENT_SEARCH_MEMORIES,
        INTENT_EXPLAIN_PAGE,
        INTENT_ACCOUNT,
        INTENT_TICKETS,
        INTENT_ORDERS,
        INTENT_HOST_EVENTS,
        INTENT_SUPPORT,
        INTENT_PRICING,
        INTENT_INSIGHTS,
        INTENT_CREATE_DRAFT,
        INTENT_CONFIRM_ACTION,
        INTENT_HIGH_RISK,
        INTENT_ABUSE,
        INTENT_INJECTION,
        INTENT_CHITCHAT,
        INTENT_UNKNOWN,
    }
)

# ---------------------------------------------------------------------------
# Soft high-risk tools — safety level 5, never execute
# ---------------------------------------------------------------------------
SOFT_HIGH_RISK_TOOLS: frozenset[str] = frozenset(
    {
        "publish_event",
        "delete_event",
        "refund_payment",
        "approve_payout",
        "reject_payout",
        "transfer_funds",
        "change_bank_account",
        "impersonate_user",
        "ban_user",
        "delete_user",
        "modify_ledger",
        "export_pii",
        "reveal_private_message",
        "reveal_qr_secret",
        "execute_sql",
        "run_shell",
    }
)

# ---------------------------------------------------------------------------
# Message / confirmation statuses
# ---------------------------------------------------------------------------
MESSAGE_ROLES = frozenset({"user", "assistant", "system", "tool"})
TOOL_CALL_STATUSES = frozenset(
    {"pending", "running", "completed", "failed", "skipped", "confirmation_required"}
)
CONFIRMATION_STATUSES = frozenset(
    {"pending", "confirmed", "cancelled", "expired", "failed"}
)
KNOWLEDGE_DOC_STATUSES = frozenset({"active", "archived", "failed"})

# ---------------------------------------------------------------------------
# Knowledge / retrieval defaults
# ---------------------------------------------------------------------------
CHUNK_TARGET_CHARS = 2000
CHUNK_TARGET_TOKENS_APPROX = 500
RETRIEVAL_TOP_K = 6
DEFAULT_TOOL_TIMEOUT_SECONDS = 8
DEFAULT_MAX_TOOL_STEPS = 4
DEFAULT_MAX_OUTPUT_TOKENS = 800
DEFAULT_RECENT_TURN_LIMIT = 6
DEFAULT_RECENT_HISTORY_TOKEN_BUDGET = 4000
DEFAULT_SESSION_SUMMARY_TOKEN_BUDGET = 800
DEFAULT_KNOWLEDGE_TOP_K = 4
DEFAULT_KNOWLEDGE_MAX = 6
ABSOLUTE_MAX_OUTPUT_TOKENS = 2000
MAX_CONVERSATION_RESULT_ITEMS = 10

# Roles excluded from provider history replay
HISTORY_EXCLUDED_MESSAGE_ROLES = frozenset({"system", "tool"})
HISTORY_EXCLUDED_SAFETY_STATUSES = frozenset(
    {"deleted", "unsafe_partial", "injection", "abuse"}
)
