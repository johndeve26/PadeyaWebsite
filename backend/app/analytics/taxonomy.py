"""Pàdéyá analytics tracking taxonomy.

Naming rule
-----------
Product objects called "events" (nights, concerts, etc.) must not be confused with
analytics signal names. Prefer:

- ``analytics_event_name`` / ``tracked_action`` — what happened in analytics
- ``target_event_id`` — which product event the action relates to
- ``event_listing_id`` — optional alias when the surface is a listing card

The DB column ``analytics_events.event_name`` stores the taxonomy
``tracked_action`` value (historical column name kept for compatibility).
"""

from __future__ import annotations

from typing import Final, Literal

TrustLevel = Literal["client", "trusted", "either"]
FunnelGroup = Literal[
    "discovery",
    "detail",
    "ticket_intent",
    "checkout",
    "post_purchase",
    "vault_legacy",
    "sponsorship",
    "commerce",
    "admin_finance",
    "legacy_compat",
]


class TrackedAction:
    """Canonical tracked_action / analytics_event_name values."""

    # Discovery / reach
    EVENT_CARD_IMPRESSION = "event_card_impression"
    EVENT_CARD_CLICK = "event_card_click"
    EVENT_LIST_VIEW = "event_list_view"
    EVENT_SEARCH_PERFORMED = "event_search_performed"
    CATEGORY_FILTER_USED = "category_filter_used"
    CITY_FILTER_USED = "city_filter_used"
    LOCATION_FILTER_USED = "location_filter_used"
    COUNTRY_PAGE_VIEW = "country_page_view"
    STATE_PAGE_VIEW = "state_page_view"
    CITY_PAGE_VIEW = "city_page_view"
    AREA_PAGE_VIEW = "area_page_view"
    FEATURED_EVENT_IMPRESSION = "featured_event_impression"
    FEATURED_EVENT_CLICK = "featured_event_click"
    PADEYA_PICK_IMPRESSION = "padeya_pick_impression"
    PADEYA_PICK_CLICK = "padeya_pick_click"
    FEATURED_PLACEMENT_IMPRESSION = "featured_placement_impression"
    FEATURED_PLACEMENT_CLICK = "featured_placement_click"
    NOT_FOUND_VIEW = "not_found_view"

    # Event detail
    EVENT_DETAIL_VIEW = "event_detail_view"
    EVENT_GALLERY_VIEW = "event_gallery_view"
    EVENT_SHARE_CLICK = "event_share_click"
    HOST_PROFILE_CLICK_FROM_EVENT = "host_profile_click_from_event"
    LEGACY_PAGE_CLICK_FROM_EVENT = "legacy_page_click_from_event"
    SAVE_EVENT_CLICK = "save_event_click"
    FOLLOW_HOST_CLICK_FROM_EVENT = "follow_host_click_from_event"
    REFUND_POLICY_VIEW = "refund_policy_view"
    VENUE_REVEAL_INFO_VIEW = "venue_reveal_info_view"

    # Ticket intent
    TICKET_PANEL_VIEW = "ticket_panel_view"
    TICKET_TYPE_IMPRESSION = "ticket_type_impression"
    TICKET_TYPE_SELECTED = "ticket_type_selected"
    TICKET_QUANTITY_CHANGED = "ticket_quantity_changed"
    CHECKOUT_START_CLICK = "checkout_start_click"
    PROMO_CODE_ENTERED = "promo_code_entered"
    PROMO_CODE_APPLIED = "promo_code_applied"
    PROMO_CODE_FAILED = "promo_code_failed"
    AMBASSADOR_REFERRAL_DETECTED = "ambassador_referral_detected"

    # Checkout
    CHECKOUT_PAGE_VIEW = "checkout_page_view"
    CHECKOUT_STEP_STARTED = "checkout_step_started"
    CHECKOUT_PAYMENT_STARTED = "checkout_payment_started"
    CHECKOUT_ABANDONED = "checkout_abandoned"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    TICKET_ISSUED = "ticket_issued"

    # Post-purchase
    TICKET_VIEWED = "ticket_viewed"
    TICKET_DOWNLOADED = "ticket_downloaded"
    TICKET_TRANSFER_STARTED = "ticket_transfer_started"
    TICKET_TRANSFER_COMPLETED = "ticket_transfer_completed"
    CHECKIN_SUCCESS = "checkin_success"
    REVIEW_PROMPT_VIEWED = "review_prompt_viewed"
    REVIEW_SUBMITTED = "review_submitted"

    # Vault / Legacy
    VAULT_PREVIEW_CLICK_FROM_EVENT = "vault_preview_click_from_event"
    VAULT_PAGE_VIEW = "vault_page_view"
    VAULT_ITEM_IMPRESSION = "vault_item_impression"
    VAULT_ITEM_CLICK = "vault_item_click"
    VAULT_ITEM_VIEW = "vault_item_view"
    VAULT_UNLOCK_CLICK = "vault_unlock_click"
    VAULT_UNLOCK_SUCCESS = "vault_unlock_success"
    VAULT_UNLOCK_FAILED = "vault_unlock_failed"
    VAULT_FOLLOW_UNLOCK = "vault_follow_unlock"
    VAULT_TICKET_UNLOCK = "vault_ticket_unlock"
    VAULT_MEDIA_OPEN = "vault_media_open"
    VAULT_DOWNLOAD_CLICK = "vault_download_click"
    LEGACY_PAGE_VIEW_FROM_EVENT = "legacy_page_view_from_event"
    HOST_FOLLOWED_FROM_EVENT = "host_followed_from_event"
    HOST_CARD_IMPRESSION = "host_card_impression"
    HOST_CARD_CLICK = "host_card_click"
    LEGACY_LOOKUP_SUBMIT = "legacy_lookup_submit"
    HOST_FOLLOW_CLICK = "host_follow_click"
    HOST_FILTER_USED = "host_filter_used"

    # Fan Passport Directory (opt-in public profiles only)
    FAN_DIRECTORY_VIEW = "fan_directory_view"
    FAN_DIRECTORY_SEARCH = "fan_directory_search"
    FAN_DIRECTORY_FILTER_USED = "fan_directory_filter_used"
    FAN_CARD_IMPRESSION = "fan_card_impression"
    FAN_CARD_CLICK = "fan_card_click"
    FAN_PASSPORT_VIEW = "fan_passport_view"
    FAN_DIRECTORY_OPT_IN = "fan_directory_opt_in"
    FAN_DIRECTORY_OPT_OUT = "fan_directory_opt_out"

    # Messaging (no message bodies in analytics)
    MESSAGE_THREAD_CREATED = "message_thread_created"
    MESSAGE_SENT = "message_sent"
    MESSAGE_READ = "message_read"
    MESSAGE_CTA_CLICKED = "message_cta_clicked"
    MESSAGE_REQUEST_RECEIVED = "message_request_received"
    MESSAGE_REQUEST_ACCEPTED = "message_request_accepted"
    MESSAGE_BLOCKED_USER = "message_blocked_user"
    MESSAGE_REPORTED = "message_reported"
    HOST_MESSAGE_FAN_CLICKED = "host_message_fan_clicked"

    # Fan Connect (no private attendance, venues, tickets, spend, PII, Vault)
    FAN_CONNECT_PAGE_VIEW = "fan_connect_page_view"
    FAN_CONNECT_SETTINGS_UPDATED = "fan_connect_settings_updated"
    FAN_CONNECT_ENABLED = "fan_connect_enabled"
    FAN_CONNECT_DISABLED = "fan_connect_disabled"
    FAN_CONNECT_SUGGESTION_IMPRESSION = "fan_connect_suggestion_impression"
    FAN_CONNECT_SUGGESTION_CLICKED = "fan_connect_suggestion_clicked"
    FAN_CONNECT_REQUEST_SENT = "fan_connect_request_sent"
    FAN_CONNECT_REQUEST_ACCEPTED = "fan_connect_request_accepted"
    FAN_CONNECT_REQUEST_DECLINED = "fan_connect_request_declined"
    FAN_CONNECT_CONNECTION_REMOVED = "fan_connect_connection_removed"
    FAN_CONNECT_BLOCKED = "fan_connect_blocked"
    FAN_CONNECT_REPORTED = "fan_connect_reported"
    FAN_FAN_MESSAGE_THREAD_CREATED = "fan_fan_message_thread_created"
    FAN_FAN_MESSAGE_SENT = "fan_fan_message_sent"

    # Sponsorship / admin
    SPONSOR_SLOT_CLICK_FROM_EVENT = "sponsor_slot_click_from_event"
    SPONSOR_INQUIRY_FROM_EVENT = "sponsor_inquiry_from_event"

    # Event merch (client intent + trusted outcomes)
    MERCH_SECTION_VIEWED = "merch_section_viewed"  # event-page panel (legacy surface)
    MERCH_STOREFRONT_VIEW = "merch_storefront_view"
    MERCH_PRODUCT_VIEW = "merch_product_view"
    MERCH_VARIANT_SELECTED = "merch_variant_selected"
    MERCH_SIZE_CHART_OPENED = "merch_size_chart_opened"
    MERCH_ADDED_TO_CART = "merch_added_to_cart"
    MERCH_REMOVED_FROM_CART = "merch_removed_from_cart"
    MERCH_CHECKOUT_STARTED = "merch_checkout_started"
    MERCH_DISCOUNT_APPLIED = "merch_discount_applied"
    MERCH_BUNDLE_SELECTED = "merch_bundle_selected"
    MERCH_PAYMENT_CONFIRMED = "merch_payment_confirmed"
    MERCH_PURCHASE_COMPLETED = "merch_purchase_completed"
    MERCH_QR_VIEWED = "merch_qr_viewed"
    MERCH_QR_SCANNED = "merch_qr_scanned"
    MERCH_PICKED_UP = "merch_picked_up"
    MERCH_SHIPPED = "merch_shipped"
    MERCH_DELIVERED = "merch_delivered"
    MERCH_REVIEW_SUBMITTED = "merch_review_submitted"
    MERCH_ABANDONED_CART_CREATED = "merch_abandoned_cart_created"
    MERCH_ABANDONED_CART_RECOVERED = "merch_abandoned_cart_recovered"
    MERCH_POST_EVENT_DROP_VIEWED = "merch_post_event_drop_viewed"
    MERCH_VAULT_EXCLUSIVE_VIEWED = "merch_vault_exclusive_viewed"
    MERCH_BADGE_AWARDED = "merch_badge_awarded"
    MERCH_PICKUP_VIEWED = "merch_pickup_viewed"  # buyer list page
    MERCH_SOLD_OUT = "merch_sold_out"
    HOST_MERCH_PRODUCT_CREATED = "host_merch_product_created"
    HOST_MERCH_PRODUCT_UPDATED = "host_merch_product_updated"
    HOST_MERCH_PRODUCT_PAUSED = "host_merch_product_paused"
    HOST_MERCH_REVENUE_REPORT_VIEWED = "host_merch_revenue_report_viewed"
    ADMIN_MERCH_HIDDEN = "admin_merch_hidden"
    SPONSOR_SALE = "sponsor_sale"
    # Legacy string constants (aliases normalize to canonical names above)
    MERCH_PRODUCT_VIEWED = MERCH_PRODUCT_VIEW
    MERCH_ADDED_TO_CHECKOUT = MERCH_ADDED_TO_CART
    MERCH_REMOVED_FROM_CHECKOUT = MERCH_REMOVED_FROM_CART
    MERCH_MARKED_PICKED_UP = MERCH_PICKED_UP

    # Trusted commerce / finance (server-only)
    REFUND_APPROVED = "refund_approved"
    VAULT_PURCHASE = "vault_purchase"
    PROMO_REDEMPTION = "promo_redemption"
    AMBASSADOR_SALE = "ambassador_sale"
    PAYOUT_COMPLETED = "payout_completed"


# Metadata: funnel group + who may emit the signal.
TRACKED_ACTION_META: Final[dict[str, tuple[FunnelGroup, TrustLevel]]] = {
    # Discovery
    TrackedAction.EVENT_CARD_IMPRESSION: ("discovery", "client"),
    TrackedAction.EVENT_CARD_CLICK: ("discovery", "client"),
    TrackedAction.EVENT_LIST_VIEW: ("discovery", "client"),
    TrackedAction.EVENT_SEARCH_PERFORMED: ("discovery", "client"),
    TrackedAction.CATEGORY_FILTER_USED: ("discovery", "client"),
    TrackedAction.CITY_FILTER_USED: ("discovery", "client"),
    TrackedAction.LOCATION_FILTER_USED: ("discovery", "client"),
    TrackedAction.COUNTRY_PAGE_VIEW: ("discovery", "client"),
    TrackedAction.STATE_PAGE_VIEW: ("discovery", "client"),
    TrackedAction.CITY_PAGE_VIEW: ("discovery", "client"),
    TrackedAction.AREA_PAGE_VIEW: ("discovery", "client"),
    TrackedAction.FEATURED_EVENT_IMPRESSION: ("discovery", "client"),
    TrackedAction.FEATURED_EVENT_CLICK: ("discovery", "client"),
    TrackedAction.PADEYA_PICK_IMPRESSION: ("discovery", "client"),
    TrackedAction.PADEYA_PICK_CLICK: ("discovery", "client"),
    TrackedAction.FEATURED_PLACEMENT_IMPRESSION: ("discovery", "client"),
    TrackedAction.FEATURED_PLACEMENT_CLICK: ("discovery", "client"),
    TrackedAction.NOT_FOUND_VIEW: ("discovery", "client"),
    # Detail
    TrackedAction.EVENT_DETAIL_VIEW: ("detail", "client"),
    TrackedAction.EVENT_GALLERY_VIEW: ("detail", "client"),
    TrackedAction.EVENT_SHARE_CLICK: ("detail", "client"),
    TrackedAction.HOST_PROFILE_CLICK_FROM_EVENT: ("detail", "client"),
    TrackedAction.LEGACY_PAGE_CLICK_FROM_EVENT: ("detail", "client"),
    TrackedAction.SAVE_EVENT_CLICK: ("detail", "client"),
    TrackedAction.FOLLOW_HOST_CLICK_FROM_EVENT: ("detail", "client"),
    TrackedAction.REFUND_POLICY_VIEW: ("detail", "client"),
    TrackedAction.VENUE_REVEAL_INFO_VIEW: ("detail", "client"),
    # Ticket intent
    TrackedAction.TICKET_PANEL_VIEW: ("ticket_intent", "client"),
    TrackedAction.TICKET_TYPE_IMPRESSION: ("ticket_intent", "client"),
    TrackedAction.TICKET_TYPE_SELECTED: ("ticket_intent", "client"),
    TrackedAction.TICKET_QUANTITY_CHANGED: ("ticket_intent", "client"),
    TrackedAction.CHECKOUT_START_CLICK: ("ticket_intent", "client"),
    TrackedAction.PROMO_CODE_ENTERED: ("ticket_intent", "client"),
    TrackedAction.PROMO_CODE_APPLIED: ("ticket_intent", "either"),
    TrackedAction.PROMO_CODE_FAILED: ("ticket_intent", "either"),
    TrackedAction.AMBASSADOR_REFERRAL_DETECTED: ("ticket_intent", "either"),
    # Checkout
    TrackedAction.CHECKOUT_PAGE_VIEW: ("checkout", "client"),
    TrackedAction.CHECKOUT_STEP_STARTED: ("checkout", "client"),
    TrackedAction.CHECKOUT_PAYMENT_STARTED: ("checkout", "client"),
    TrackedAction.CHECKOUT_ABANDONED: ("checkout", "client"),
    TrackedAction.PAYMENT_SUCCESS: ("checkout", "trusted"),
    TrackedAction.PAYMENT_FAILED: ("checkout", "trusted"),
    TrackedAction.TICKET_ISSUED: ("checkout", "trusted"),
    # Post-purchase
    TrackedAction.TICKET_VIEWED: ("post_purchase", "client"),
    TrackedAction.TICKET_DOWNLOADED: ("post_purchase", "client"),
    TrackedAction.TICKET_TRANSFER_STARTED: ("post_purchase", "client"),
    TrackedAction.TICKET_TRANSFER_COMPLETED: ("post_purchase", "either"),
    TrackedAction.CHECKIN_SUCCESS: ("post_purchase", "trusted"),
    TrackedAction.REVIEW_PROMPT_VIEWED: ("post_purchase", "client"),
    TrackedAction.REVIEW_SUBMITTED: ("post_purchase", "trusted"),
    # Vault / Legacy
    TrackedAction.VAULT_PREVIEW_CLICK_FROM_EVENT: ("vault_legacy", "client"),
    TrackedAction.VAULT_PAGE_VIEW: ("vault_legacy", "client"),
    TrackedAction.VAULT_ITEM_IMPRESSION: ("vault_legacy", "client"),
    TrackedAction.VAULT_ITEM_CLICK: ("vault_legacy", "client"),
    TrackedAction.VAULT_ITEM_VIEW: ("vault_legacy", "client"),
    TrackedAction.VAULT_UNLOCK_CLICK: ("vault_legacy", "client"),
    TrackedAction.VAULT_UNLOCK_SUCCESS: ("vault_legacy", "either"),
    TrackedAction.VAULT_UNLOCK_FAILED: ("vault_legacy", "client"),
    TrackedAction.VAULT_FOLLOW_UNLOCK: ("vault_legacy", "client"),
    TrackedAction.VAULT_TICKET_UNLOCK: ("vault_legacy", "client"),
    TrackedAction.VAULT_MEDIA_OPEN: ("vault_legacy", "client"),
    TrackedAction.VAULT_DOWNLOAD_CLICK: ("vault_legacy", "client"),
    TrackedAction.LEGACY_PAGE_VIEW_FROM_EVENT: ("vault_legacy", "client"),
    TrackedAction.HOST_FOLLOWED_FROM_EVENT: ("vault_legacy", "either"),
    TrackedAction.HOST_CARD_IMPRESSION: ("discovery", "client"),
    TrackedAction.HOST_CARD_CLICK: ("discovery", "client"),
    TrackedAction.LEGACY_LOOKUP_SUBMIT: ("discovery", "client"),
    TrackedAction.HOST_FOLLOW_CLICK: ("vault_legacy", "client"),
    TrackedAction.HOST_FILTER_USED: ("discovery", "client"),
    TrackedAction.FAN_DIRECTORY_VIEW: ("discovery", "client"),
    TrackedAction.FAN_DIRECTORY_SEARCH: ("discovery", "client"),
    TrackedAction.FAN_DIRECTORY_FILTER_USED: ("discovery", "client"),
    TrackedAction.FAN_CARD_IMPRESSION: ("discovery", "client"),
    TrackedAction.FAN_CARD_CLICK: ("discovery", "client"),
    TrackedAction.FAN_PASSPORT_VIEW: ("vault_legacy", "client"),
    TrackedAction.FAN_DIRECTORY_OPT_IN: ("vault_legacy", "client"),
    TrackedAction.FAN_DIRECTORY_OPT_OUT: ("vault_legacy", "client"),
    TrackedAction.MESSAGE_THREAD_CREATED: ("discovery", "client"),
    TrackedAction.MESSAGE_SENT: ("discovery", "client"),
    TrackedAction.MESSAGE_READ: ("discovery", "client"),
    TrackedAction.MESSAGE_CTA_CLICKED: ("discovery", "client"),
    TrackedAction.MESSAGE_REQUEST_RECEIVED: ("discovery", "client"),
    TrackedAction.MESSAGE_REQUEST_ACCEPTED: ("discovery", "client"),
    TrackedAction.MESSAGE_BLOCKED_USER: ("discovery", "client"),
    TrackedAction.MESSAGE_REPORTED: ("discovery", "client"),
    TrackedAction.HOST_MESSAGE_FAN_CLICKED: ("discovery", "client"),
    TrackedAction.FAN_CONNECT_PAGE_VIEW: ("discovery", "client"),
    TrackedAction.FAN_CONNECT_SETTINGS_UPDATED: ("discovery", "client"),
    TrackedAction.FAN_CONNECT_ENABLED: ("discovery", "trusted"),
    TrackedAction.FAN_CONNECT_DISABLED: ("discovery", "trusted"),
    TrackedAction.FAN_CONNECT_SUGGESTION_IMPRESSION: ("discovery", "client"),
    TrackedAction.FAN_CONNECT_SUGGESTION_CLICKED: ("discovery", "client"),
    TrackedAction.FAN_CONNECT_REQUEST_SENT: ("discovery", "trusted"),
    TrackedAction.FAN_CONNECT_REQUEST_ACCEPTED: ("discovery", "trusted"),
    TrackedAction.FAN_CONNECT_REQUEST_DECLINED: ("discovery", "trusted"),
    TrackedAction.FAN_CONNECT_CONNECTION_REMOVED: ("discovery", "trusted"),
    TrackedAction.FAN_CONNECT_BLOCKED: ("discovery", "trusted"),
    TrackedAction.FAN_CONNECT_REPORTED: ("discovery", "trusted"),
    TrackedAction.FAN_FAN_MESSAGE_THREAD_CREATED: ("discovery", "trusted"),
    TrackedAction.FAN_FAN_MESSAGE_SENT: ("discovery", "trusted"),
    # Sponsorship
    TrackedAction.SPONSOR_SLOT_CLICK_FROM_EVENT: ("sponsorship", "client"),
    TrackedAction.SPONSOR_INQUIRY_FROM_EVENT: ("sponsorship", "either"),
    # Event merch
    TrackedAction.MERCH_SECTION_VIEWED: ("detail", "client"),
    TrackedAction.MERCH_STOREFRONT_VIEW: ("detail", "client"),
    TrackedAction.MERCH_PRODUCT_VIEW: ("detail", "client"),
    TrackedAction.MERCH_VARIANT_SELECTED: ("ticket_intent", "client"),
    TrackedAction.MERCH_SIZE_CHART_OPENED: ("ticket_intent", "client"),
    TrackedAction.MERCH_ADDED_TO_CART: ("checkout", "client"),
    TrackedAction.MERCH_REMOVED_FROM_CART: ("checkout", "client"),
    TrackedAction.MERCH_CHECKOUT_STARTED: ("checkout", "client"),
    TrackedAction.MERCH_DISCOUNT_APPLIED: ("checkout", "client"),
    TrackedAction.MERCH_BUNDLE_SELECTED: ("checkout", "client"),
    TrackedAction.MERCH_PAYMENT_CONFIRMED: ("checkout", "trusted"),
    TrackedAction.MERCH_PURCHASE_COMPLETED: ("checkout", "trusted"),
    TrackedAction.MERCH_QR_VIEWED: ("post_purchase", "client"),
    TrackedAction.MERCH_QR_SCANNED: ("post_purchase", "trusted"),
    TrackedAction.MERCH_PICKED_UP: ("post_purchase", "trusted"),
    TrackedAction.MERCH_SHIPPED: ("post_purchase", "trusted"),
    TrackedAction.MERCH_DELIVERED: ("post_purchase", "trusted"),
    TrackedAction.MERCH_REVIEW_SUBMITTED: ("post_purchase", "trusted"),
    TrackedAction.MERCH_ABANDONED_CART_CREATED: ("commerce", "trusted"),
    TrackedAction.MERCH_ABANDONED_CART_RECOVERED: ("commerce", "trusted"),
    TrackedAction.MERCH_POST_EVENT_DROP_VIEWED: ("detail", "client"),
    TrackedAction.MERCH_VAULT_EXCLUSIVE_VIEWED: ("detail", "client"),
    TrackedAction.MERCH_BADGE_AWARDED: ("commerce", "trusted"),
    TrackedAction.MERCH_PICKUP_VIEWED: ("post_purchase", "client"),
    TrackedAction.MERCH_SOLD_OUT: ("commerce", "trusted"),
    TrackedAction.HOST_MERCH_PRODUCT_CREATED: ("commerce", "trusted"),
    TrackedAction.HOST_MERCH_PRODUCT_UPDATED: ("commerce", "trusted"),
    TrackedAction.HOST_MERCH_PRODUCT_PAUSED: ("commerce", "trusted"),
    TrackedAction.HOST_MERCH_REVENUE_REPORT_VIEWED: ("commerce", "client"),
    TrackedAction.ADMIN_MERCH_HIDDEN: ("admin_finance", "trusted"),
    TrackedAction.SPONSOR_SALE: ("commerce", "trusted"),
    # Commerce / finance (server-only)
    TrackedAction.REFUND_APPROVED: ("commerce", "trusted"),
    TrackedAction.VAULT_PURCHASE: ("commerce", "trusted"),
    TrackedAction.PROMO_REDEMPTION: ("commerce", "trusted"),
    TrackedAction.AMBASSADOR_SALE: ("commerce", "trusted"),
    TrackedAction.PAYOUT_COMPLETED: ("admin_finance", "trusted"),
}

TRACKED_ACTIONS: Final[frozenset[str]] = frozenset(TRACKED_ACTION_META.keys())

# Legacy names still accepted on write; normalized to taxonomy values.
LEGACY_ACTION_ALIASES: Final[dict[str, str]] = {
    "page_view": TrackedAction.EVENT_DETAIL_VIEW,  # when tied to a product event; else kept via normalize path
    "event_impression": TrackedAction.EVENT_CARD_IMPRESSION,
    "event_click": TrackedAction.EVENT_CARD_CLICK,
    "checkout_start": TrackedAction.CHECKOUT_PAGE_VIEW,
    "checkout_complete": TrackedAction.PAYMENT_SUCCESS,
    "payment_failed": TrackedAction.PAYMENT_FAILED,
    "impression": TrackedAction.EVENT_CARD_IMPRESSION,
    "click": TrackedAction.EVENT_CARD_CLICK,
    # Older plan names
    "checkout_pay_click": TrackedAction.CHECKOUT_PAYMENT_STARTED,
    "ticket_select": TrackedAction.TICKET_TYPE_SELECTED,
    "share": TrackedAction.EVENT_SHARE_CLICK,
    "legacy_open": TrackedAction.LEGACY_PAGE_CLICK_FROM_EVENT,
    # Merch renames (exact names are canonical)
    "merch_product_viewed": TrackedAction.MERCH_PRODUCT_VIEW,
    "merch_added_to_checkout": TrackedAction.MERCH_ADDED_TO_CART,
    "merch_removed_from_checkout": TrackedAction.MERCH_REMOVED_FROM_CART,
    "merch_marked_picked_up": TrackedAction.MERCH_PICKED_UP,
}

# Conversion funnel stages stored on conversion_events.stage (legacy + new).
# Prefer taxonomy tracked_action values going forward; keep short stages for BC.
CONVERSION_STAGES: Final[tuple[str, ...]] = (
    # Legacy short stages (still written by specialized impression/click helpers)
    "impression",
    "click",
    "checkout_start",
    "checkout_complete",
    "payment_failed",
    # Taxonomy-aligned stages
    TrackedAction.EVENT_CARD_IMPRESSION,
    TrackedAction.EVENT_CARD_CLICK,
    TrackedAction.EVENT_DETAIL_VIEW,
    TrackedAction.CHECKOUT_PAGE_VIEW,
    TrackedAction.CHECKOUT_STEP_STARTED,
    TrackedAction.CHECKOUT_PAYMENT_STARTED,
    TrackedAction.CHECKOUT_ABANDONED,
    TrackedAction.PAYMENT_SUCCESS,
    TrackedAction.PAYMENT_FAILED,
    TrackedAction.TICKET_ISSUED,
)

# Map taxonomy actions → conversion_events.stage when writing conversion rows.
ACTION_TO_CONVERSION_STAGE: Final[dict[str, str]] = {
    TrackedAction.EVENT_CARD_IMPRESSION: "impression",
    TrackedAction.FEATURED_EVENT_IMPRESSION: "impression",
    TrackedAction.PADEYA_PICK_IMPRESSION: "impression",
    TrackedAction.FEATURED_PLACEMENT_IMPRESSION: "impression",
    TrackedAction.EVENT_CARD_CLICK: "click",
    TrackedAction.FEATURED_EVENT_CLICK: "click",
    TrackedAction.PADEYA_PICK_CLICK: "click",
    TrackedAction.FEATURED_PLACEMENT_CLICK: "click",
    TrackedAction.EVENT_DETAIL_VIEW: TrackedAction.EVENT_DETAIL_VIEW,
    TrackedAction.CHECKOUT_PAGE_VIEW: "checkout_start",
    TrackedAction.CHECKOUT_STEP_STARTED: TrackedAction.CHECKOUT_STEP_STARTED,
    TrackedAction.CHECKOUT_PAYMENT_STARTED: TrackedAction.CHECKOUT_PAYMENT_STARTED,
    TrackedAction.CHECKOUT_ABANDONED: TrackedAction.CHECKOUT_ABANDONED,
    TrackedAction.PAYMENT_SUCCESS: "checkout_complete",
    TrackedAction.PAYMENT_FAILED: "payment_failed",
    TrackedAction.TICKET_ISSUED: TrackedAction.TICKET_ISSUED,
    TrackedAction.MERCH_CHECKOUT_STARTED: TrackedAction.MERCH_CHECKOUT_STARTED,
    TrackedAction.MERCH_PAYMENT_CONFIRMED: "checkout_complete",
    TrackedAction.MERCH_PURCHASE_COMPLETED: TrackedAction.MERCH_PURCHASE_COMPLETED,
}

# Specialized table routing hints (documentation + helpers).
ACTION_PRIMARY_TABLE: Final[dict[str, str]] = {
    TrackedAction.EVENT_CARD_IMPRESSION: "event_impressions",
    TrackedAction.FEATURED_EVENT_IMPRESSION: "event_impressions",
    TrackedAction.PADEYA_PICK_IMPRESSION: "event_impressions",
    TrackedAction.FEATURED_PLACEMENT_IMPRESSION: "event_impressions",
    TrackedAction.EVENT_CARD_CLICK: "event_clicks",
    TrackedAction.FEATURED_EVENT_CLICK: "event_clicks",
    TrackedAction.PADEYA_PICK_CLICK: "event_clicks",
    TrackedAction.FEATURED_PLACEMENT_CLICK: "event_clicks",
    TrackedAction.EVENT_DETAIL_VIEW: "page_views",
    TrackedAction.EVENT_LIST_VIEW: "page_views",
    TrackedAction.COUNTRY_PAGE_VIEW: "page_views",
    TrackedAction.STATE_PAGE_VIEW: "page_views",
    TrackedAction.CITY_PAGE_VIEW: "page_views",
    TrackedAction.AREA_PAGE_VIEW: "page_views",
    TrackedAction.CHECKOUT_PAGE_VIEW: "conversion_events",
    TrackedAction.PAYMENT_SUCCESS: "conversion_events",
    TrackedAction.PAYMENT_FAILED: "conversion_events",
    TrackedAction.TICKET_ISSUED: "conversion_events",
}


def normalize_tracked_action(raw: str | None, *, path: str | None = None) -> str | None:
    """Normalize client/legacy names to a taxonomy tracked_action.

    Returns ``None`` if empty. Unknown names are lowercased/truncated so
    experimental signals can still be stored when the caller allows them.
    """
    if raw is None:
        return None
    name = raw.strip().lower()[:64]
    if not name:
        return None

    if name == "page_view":
        if path:
            cleaned = path.split("?", 1)[0].rstrip("/") or "/"
            if cleaned == "/events" or cleaned.startswith("/events/"):
                # /events/{slug} → detail; bare /events → list
                parts = [p for p in cleaned.split("/") if p]
                if len(parts) >= 2 and parts[0] == "events":
                    return TrackedAction.EVENT_DETAIL_VIEW
                return TrackedAction.EVENT_LIST_VIEW
        return TrackedAction.EVENT_LIST_VIEW

    if name in LEGACY_ACTION_ALIASES:
        return LEGACY_ACTION_ALIASES[name]
    return name


def is_known_tracked_action(name: str) -> bool:
    key = name.strip().lower()
    return key in TRACKED_ACTIONS or key in LEGACY_ACTION_ALIASES


def require_known_tracked_action(raw: str, *, path: str | None = None) -> str:
    """Normalize and require a canonical taxonomy tracked_action."""
    normalized = normalize_tracked_action(raw, path=path)
    if not normalized:
        raise ValueError("tracked_action is required")
    if normalized not in TRACKED_ACTIONS:
        raise ValueError(f"Unknown tracked_action: {raw}")
    return normalized


def trust_level(action: str) -> TrustLevel | None:
    meta = TRACKED_ACTION_META.get(action)
    return meta[1] if meta else None


# Actions that must never be accepted from public/client track endpoints.
SERVER_ONLY_ACTIONS: Final[frozenset[str]] = frozenset(
    {
        TrackedAction.PAYMENT_SUCCESS,
        TrackedAction.PAYMENT_FAILED,
        TrackedAction.TICKET_ISSUED,
        TrackedAction.CHECKIN_SUCCESS,
        TrackedAction.REVIEW_SUBMITTED,
        TrackedAction.REFUND_APPROVED,
        TrackedAction.VAULT_PURCHASE,
        TrackedAction.PROMO_REDEMPTION,
        TrackedAction.AMBASSADOR_SALE,
        TrackedAction.PAYOUT_COMPLETED,
        TrackedAction.MERCH_PAYMENT_CONFIRMED,
        TrackedAction.MERCH_PURCHASE_COMPLETED,
        TrackedAction.MERCH_QR_SCANNED,
        TrackedAction.MERCH_PICKED_UP,
        TrackedAction.MERCH_SHIPPED,
        TrackedAction.MERCH_DELIVERED,
        TrackedAction.MERCH_REVIEW_SUBMITTED,
        TrackedAction.MERCH_ABANDONED_CART_CREATED,
        TrackedAction.MERCH_ABANDONED_CART_RECOVERED,
        TrackedAction.MERCH_BADGE_AWARDED,
        TrackedAction.MERCH_SOLD_OUT,
        TrackedAction.HOST_MERCH_PRODUCT_CREATED,
        TrackedAction.HOST_MERCH_PRODUCT_UPDATED,
        TrackedAction.HOST_MERCH_PRODUCT_PAUSED,
        TrackedAction.ADMIN_MERCH_HIDDEN,
        TrackedAction.SPONSOR_SALE,
        TrackedAction.FAN_CONNECT_ENABLED,
        TrackedAction.FAN_CONNECT_DISABLED,
        TrackedAction.FAN_CONNECT_REQUEST_SENT,
        TrackedAction.FAN_CONNECT_REQUEST_ACCEPTED,
        TrackedAction.FAN_CONNECT_REQUEST_DECLINED,
        TrackedAction.FAN_CONNECT_CONNECTION_REMOVED,
        TrackedAction.FAN_CONNECT_BLOCKED,
        TrackedAction.FAN_CONNECT_REPORTED,
        TrackedAction.FAN_FAN_MESSAGE_THREAD_CREATED,
        TrackedAction.FAN_FAN_MESSAGE_SENT,
    }
)

# Client payloads must not set these metadata keys (revenue / sales inflation).
FORBIDDEN_CLIENT_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "conversion_value",
        "amount",
        "tickets_sold",
        "gross_revenue",
        "net_revenue",
        "revenue",
    }
)


def is_server_only_action(action: str) -> bool:
    return action.strip().lower() in SERVER_ONLY_ACTIONS


def funnel_group(action: str) -> FunnelGroup | None:
    meta = TRACKED_ACTION_META.get(action)
    return meta[0] if meta else None


def conversion_stage_for_action(action: str) -> str | None:
    return ACTION_TO_CONVERSION_STAGE.get(action)


# Backward-compatible export used by older imports / docs.
ANALYTICS_EVENT_NAMES: Final[tuple[str, ...]] = tuple(sorted(TRACKED_ACTIONS)) + (
    "page_view",
    "event_impression",
    "event_click",
    "checkout_start",
    "checkout_complete",
    "custom",
    "demo_heartbeat",
)
