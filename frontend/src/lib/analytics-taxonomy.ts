/**
 * Pàdéyá analytics tracking taxonomy (frontend).
 *
 * Product “events” (nights) ≠ analytics signals.
 * Prefer:
 * - trackedAction / analyticsEventName
 * - targetEventId
 * - eventListingId (listing card; usually same as targetEventId)
 */

export const TrackedAction = {
  // Discovery / reach
  EVENT_CARD_IMPRESSION: "event_card_impression",
  EVENT_CARD_CLICK: "event_card_click",
  EVENT_LIST_VIEW: "event_list_view",
  EVENT_SEARCH_PERFORMED: "event_search_performed",
  CATEGORY_FILTER_USED: "category_filter_used",
  CITY_FILTER_USED: "city_filter_used",
  LOCATION_FILTER_USED: "location_filter_used",
  COUNTRY_PAGE_VIEW: "country_page_view",
  STATE_PAGE_VIEW: "state_page_view",
  CITY_PAGE_VIEW: "city_page_view",
  AREA_PAGE_VIEW: "area_page_view",
  FEATURED_EVENT_IMPRESSION: "featured_event_impression",
  FEATURED_EVENT_CLICK: "featured_event_click",
  PADEYA_PICK_IMPRESSION: "padeya_pick_impression",
  PADEYA_PICK_CLICK: "padeya_pick_click",
  FEATURED_PLACEMENT_IMPRESSION: "featured_placement_impression",
  FEATURED_PLACEMENT_CLICK: "featured_placement_click",
  /** Branded App Router 404 recovery page */
  NOT_FOUND_VIEW: "not_found_view",

  // Event detail
  EVENT_DETAIL_VIEW: "event_detail_view",
  EVENT_GALLERY_VIEW: "event_gallery_view",
  MEMORIES_PAGE_VIEW: "memories_page_view",
  EVENT_MEMORIES_VIEW: "event_memories_view",
  MEMORY_UPLOAD_STARTED: "memory_upload_started",
  MEMORY_UPLOAD_COMPLETED: "memory_upload_completed",
  MEMORY_UPLOAD_FAILED: "memory_upload_failed",
  EXTERNAL_GALLERY_CLICKED: "external_gallery_clicked",
  EVENT_SHARE_CLICK: "event_share_click",
  HOST_PROFILE_CLICK_FROM_EVENT: "host_profile_click_from_event",
  LEGACY_PAGE_CLICK_FROM_EVENT: "legacy_page_click_from_event",
  SAVE_EVENT_CLICK: "save_event_click",
  FOLLOW_HOST_CLICK_FROM_EVENT: "follow_host_click_from_event",
  REFUND_POLICY_VIEW: "refund_policy_view",
  VENUE_REVEAL_INFO_VIEW: "venue_reveal_info_view",

  // Ticket intent
  TICKET_PANEL_VIEW: "ticket_panel_view",
  TICKET_TYPE_IMPRESSION: "ticket_type_impression",
  TICKET_TYPE_SELECTED: "ticket_type_selected",
  TICKET_QUANTITY_CHANGED: "ticket_quantity_changed",
  CHECKOUT_START_CLICK: "checkout_start_click",
  PROMO_CODE_ENTERED: "promo_code_entered",
  PROMO_CODE_APPLIED: "promo_code_applied",
  PROMO_CODE_FAILED: "promo_code_failed",
  AMBASSADOR_REFERRAL_DETECTED: "ambassador_referral_detected",

  // Checkout
  CHECKOUT_PAGE_VIEW: "checkout_page_view",
  CHECKOUT_STEP_STARTED: "checkout_step_started",
  CHECKOUT_PAYMENT_STARTED: "checkout_payment_started",
  CHECKOUT_ABANDONED: "checkout_abandoned",
  PAYMENT_SUCCESS: "payment_success",
  PAYMENT_FAILED: "payment_failed",
  TICKET_ISSUED: "ticket_issued",

  // Post-purchase
  TICKET_VIEWED: "ticket_viewed",
  TICKET_DOWNLOADED: "ticket_downloaded",
  TICKET_TRANSFER_STARTED: "ticket_transfer_started",
  TICKET_TRANSFER_COMPLETED: "ticket_transfer_completed",
  BUYER_TICKETS_PAGE_VIEW: "buyer_tickets_page_view",
  TICKET_TAB_CHANGED: "ticket_tab_changed",
  TICKET_GROUP_EXPANDED: "ticket_group_expanded",
  TICKET_QR_CLICKED: "ticket_qr_clicked",
  TICKET_DETAILS_CLICKED: "ticket_details_clicked",
  TICKET_EVENT_CLICKED: "ticket_event_clicked",
  CHECKIN_SUCCESS: "checkin_success",
  REVIEW_PROMPT_VIEWED: "review_prompt_viewed",
  REVIEW_SUBMITTED: "review_submitted",

  // Vault / Legacy
  VAULT_PREVIEW_CLICK_FROM_EVENT: "vault_preview_click_from_event",
  VAULT_PAGE_VIEW: "vault_page_view",
  VAULT_ITEM_IMPRESSION: "vault_item_impression",
  VAULT_ITEM_CLICK: "vault_item_click",
  VAULT_ITEM_VIEW: "vault_item_view",
  VAULT_UNLOCK_CLICK: "vault_unlock_click",
  VAULT_UNLOCK_SUCCESS: "vault_unlock_success",
  VAULT_UNLOCK_FAILED: "vault_unlock_failed",
  VAULT_FOLLOW_UNLOCK: "vault_follow_unlock",
  VAULT_TICKET_UNLOCK: "vault_ticket_unlock",
  VAULT_MEDIA_OPEN: "vault_media_open",
  VAULT_DOWNLOAD_CLICK: "vault_download_click",
  LEGACY_PAGE_VIEW_FROM_EVENT: "legacy_page_view_from_event",
  HOST_FOLLOWED_FROM_EVENT: "host_followed_from_event",
  HOST_CARD_IMPRESSION: "host_card_impression",
  HOST_CARD_CLICK: "host_card_click",
  LEGACY_LOOKUP_SUBMIT: "legacy_lookup_submit",
  HOST_FOLLOW_CLICK: "host_follow_click",
  HOST_FILTER_USED: "host_filter_used",

  // Fan Passport Directory
  FAN_DIRECTORY_VIEW: "fan_directory_view",
  FAN_DIRECTORY_SEARCH: "fan_directory_search",
  FAN_DIRECTORY_FILTER_USED: "fan_directory_filter_used",
  FAN_CARD_IMPRESSION: "fan_card_impression",
  FAN_CARD_CLICK: "fan_card_click",
  FAN_PASSPORT_VIEW: "fan_passport_view",
  FAN_DIRECTORY_OPT_IN: "fan_directory_opt_in",
  FAN_DIRECTORY_OPT_OUT: "fan_directory_opt_out",

  // Messaging
  MESSAGE_THREAD_CREATED: "message_thread_created",
  MESSAGE_SENT: "message_sent",
  MESSAGE_READ: "message_read",
  MESSAGE_CTA_CLICKED: "message_cta_clicked",
  MESSAGE_REQUEST_RECEIVED: "message_request_received",
  MESSAGE_REQUEST_ACCEPTED: "message_request_accepted",
  MESSAGE_BLOCKED_USER: "message_blocked_user",
  MESSAGE_REPORTED: "message_reported",
  HOST_MESSAGE_FAN_CLICKED: "host_message_fan_clicked",

  // Fan Connect (no private attendance, venues, tickets, spend, PII, Vault)
  FAN_CONNECT_PAGE_VIEW: "fan_connect_page_view",
  FAN_CONNECT_SETTINGS_UPDATED: "fan_connect_settings_updated",
  FAN_CONNECT_ENABLED: "fan_connect_enabled",
  FAN_CONNECT_DISABLED: "fan_connect_disabled",
  FAN_CONNECT_SUGGESTION_IMPRESSION: "fan_connect_suggestion_impression",
  FAN_CONNECT_SUGGESTION_CLICKED: "fan_connect_suggestion_clicked",
  FAN_CONNECT_REQUEST_SENT: "fan_connect_request_sent",
  FAN_CONNECT_REQUEST_ACCEPTED: "fan_connect_request_accepted",
  FAN_CONNECT_REQUEST_DECLINED: "fan_connect_request_declined",
  FAN_CONNECT_CONNECTION_REMOVED: "fan_connect_connection_removed",
  FAN_CONNECT_BLOCKED: "fan_connect_blocked",
  FAN_CONNECT_REPORTED: "fan_connect_reported",
  FAN_FAN_MESSAGE_THREAD_CREATED: "fan_fan_message_thread_created",
  FAN_FAN_MESSAGE_SENT: "fan_fan_message_sent",

  // Sponsorship
  SPONSOR_SLOT_CLICK_FROM_EVENT: "sponsor_slot_click_from_event",
  SPONSOR_INQUIRY_FROM_EVENT: "sponsor_inquiry_from_event",

  // Event merch
  MERCH_SECTION_VIEWED: "merch_section_viewed",
  MERCH_STOREFRONT_VIEW: "merch_storefront_view",
  MERCH_PRODUCT_VIEW: "merch_product_view",
  MERCH_VARIANT_SELECTED: "merch_variant_selected",
  MERCH_SIZE_CHART_OPENED: "merch_size_chart_opened",
  MERCH_ADDED_TO_CART: "merch_added_to_cart",
  MERCH_REMOVED_FROM_CART: "merch_removed_from_cart",
  MERCH_CHECKOUT_STARTED: "merch_checkout_started",
  MERCH_DISCOUNT_APPLIED: "merch_discount_applied",
  MERCH_BUNDLE_SELECTED: "merch_bundle_selected",
  MERCH_PAYMENT_CONFIRMED: "merch_payment_confirmed",
  MERCH_PURCHASE_COMPLETED: "merch_purchase_completed",
  MERCH_QR_VIEWED: "merch_qr_viewed",
  MERCH_QR_SCANNED: "merch_qr_scanned",
  MERCH_PICKED_UP: "merch_picked_up",
  MERCH_SHIPPED: "merch_shipped",
  MERCH_DELIVERED: "merch_delivered",
  MERCH_REVIEW_SUBMITTED: "merch_review_submitted",
  MERCH_ABANDONED_CART_CREATED: "merch_abandoned_cart_created",
  MERCH_ABANDONED_CART_RECOVERED: "merch_abandoned_cart_recovered",
  MERCH_POST_EVENT_DROP_VIEWED: "merch_post_event_drop_viewed",
  MERCH_VAULT_EXCLUSIVE_VIEWED: "merch_vault_exclusive_viewed",
  MERCH_BADGE_AWARDED: "merch_badge_awarded",
  MERCH_PICKUP_VIEWED: "merch_pickup_viewed",
  MERCH_SOLD_OUT: "merch_sold_out",
  HOST_MERCH_PRODUCT_CREATED: "host_merch_product_created",
  HOST_MERCH_PRODUCT_UPDATED: "host_merch_product_updated",
  HOST_MERCH_PRODUCT_PAUSED: "host_merch_product_paused",
  HOST_MERCH_REVENUE_REPORT_VIEWED: "host_merch_revenue_report_viewed",
  ADMIN_MERCH_HIDDEN: "admin_merch_hidden",
  SPONSOR_SALE: "sponsor_sale",
  /** @deprecated Use MERCH_PRODUCT_VIEW */
  MERCH_PRODUCT_VIEWED: "merch_product_view",
  /** @deprecated Use MERCH_ADDED_TO_CART */
  MERCH_ADDED_TO_CHECKOUT: "merch_added_to_cart",
  /** @deprecated Use MERCH_REMOVED_FROM_CART */
  MERCH_REMOVED_FROM_CHECKOUT: "merch_removed_from_cart",
  /** @deprecated Use MERCH_PICKED_UP */
  MERCH_MARKED_PICKED_UP: "merch_picked_up",

  // Trusted commerce / finance (server-only)
  REFUND_APPROVED: "refund_approved",
  VAULT_PURCHASE: "vault_purchase",
  PROMO_REDEMPTION: "promo_redemption",
  AMBASSADOR_SALE: "ambassador_sale",
  PAYOUT_COMPLETED: "payout_completed",
} as const;

export type TrackedActionName =
  (typeof TrackedAction)[keyof typeof TrackedAction];

export type FunnelGroup =
  | "discovery"
  | "detail"
  | "ticket_intent"
  | "checkout"
  | "post_purchase"
  | "vault_legacy"
  | "sponsorship"
  | "commerce"
  | "admin_finance";

/** Client may emit these; trusted ones should be written by the backend. */
export type TrustLevel = "client" | "trusted" | "either";

export const TRACKED_ACTION_META: Record<
  TrackedActionName,
  { group: FunnelGroup; trust: TrustLevel }
> = {
  [TrackedAction.EVENT_CARD_IMPRESSION]: { group: "discovery", trust: "client" },
  [TrackedAction.EVENT_CARD_CLICK]: { group: "discovery", trust: "client" },
  [TrackedAction.EVENT_LIST_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.EVENT_SEARCH_PERFORMED]: { group: "discovery", trust: "client" },
  [TrackedAction.CATEGORY_FILTER_USED]: { group: "discovery", trust: "client" },
  [TrackedAction.CITY_FILTER_USED]: { group: "discovery", trust: "client" },
  [TrackedAction.LOCATION_FILTER_USED]: { group: "discovery", trust: "client" },
  [TrackedAction.COUNTRY_PAGE_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.STATE_PAGE_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.CITY_PAGE_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.AREA_PAGE_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.FEATURED_EVENT_IMPRESSION]: { group: "discovery", trust: "client" },
  [TrackedAction.FEATURED_EVENT_CLICK]: { group: "discovery", trust: "client" },
  [TrackedAction.PADEYA_PICK_IMPRESSION]: { group: "discovery", trust: "client" },
  [TrackedAction.PADEYA_PICK_CLICK]: { group: "discovery", trust: "client" },
  [TrackedAction.FEATURED_PLACEMENT_IMPRESSION]: { group: "discovery", trust: "client" },
  [TrackedAction.FEATURED_PLACEMENT_CLICK]: { group: "discovery", trust: "client" },
  [TrackedAction.NOT_FOUND_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.EVENT_DETAIL_VIEW]: { group: "detail", trust: "client" },
  [TrackedAction.EVENT_GALLERY_VIEW]: { group: "detail", trust: "client" },
  [TrackedAction.MEMORIES_PAGE_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.EVENT_MEMORIES_VIEW]: { group: "detail", trust: "client" },
  [TrackedAction.MEMORY_UPLOAD_STARTED]: { group: "detail", trust: "client" },
  [TrackedAction.MEMORY_UPLOAD_COMPLETED]: { group: "detail", trust: "client" },
  [TrackedAction.MEMORY_UPLOAD_FAILED]: { group: "detail", trust: "client" },
  [TrackedAction.EXTERNAL_GALLERY_CLICKED]: { group: "detail", trust: "client" },
  [TrackedAction.EVENT_SHARE_CLICK]: { group: "detail", trust: "client" },
  [TrackedAction.HOST_PROFILE_CLICK_FROM_EVENT]: { group: "detail", trust: "client" },
  [TrackedAction.LEGACY_PAGE_CLICK_FROM_EVENT]: { group: "detail", trust: "client" },
  [TrackedAction.SAVE_EVENT_CLICK]: { group: "detail", trust: "client" },
  [TrackedAction.FOLLOW_HOST_CLICK_FROM_EVENT]: { group: "detail", trust: "client" },
  [TrackedAction.REFUND_POLICY_VIEW]: { group: "detail", trust: "client" },
  [TrackedAction.VENUE_REVEAL_INFO_VIEW]: { group: "detail", trust: "client" },
  [TrackedAction.TICKET_PANEL_VIEW]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.TICKET_TYPE_IMPRESSION]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.TICKET_TYPE_SELECTED]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.TICKET_QUANTITY_CHANGED]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.CHECKOUT_START_CLICK]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.PROMO_CODE_ENTERED]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.PROMO_CODE_APPLIED]: { group: "ticket_intent", trust: "either" },
  [TrackedAction.PROMO_CODE_FAILED]: { group: "ticket_intent", trust: "either" },
  [TrackedAction.AMBASSADOR_REFERRAL_DETECTED]: { group: "ticket_intent", trust: "either" },
  [TrackedAction.CHECKOUT_PAGE_VIEW]: { group: "checkout", trust: "client" },
  [TrackedAction.CHECKOUT_STEP_STARTED]: { group: "checkout", trust: "client" },
  [TrackedAction.CHECKOUT_PAYMENT_STARTED]: { group: "checkout", trust: "client" },
  [TrackedAction.CHECKOUT_ABANDONED]: { group: "checkout", trust: "client" },
  [TrackedAction.PAYMENT_SUCCESS]: { group: "checkout", trust: "trusted" },
  [TrackedAction.PAYMENT_FAILED]: { group: "checkout", trust: "trusted" },
  [TrackedAction.TICKET_ISSUED]: { group: "checkout", trust: "trusted" },
  [TrackedAction.TICKET_VIEWED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_DOWNLOADED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_TRANSFER_STARTED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_TRANSFER_COMPLETED]: { group: "post_purchase", trust: "either" },
  [TrackedAction.BUYER_TICKETS_PAGE_VIEW]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_TAB_CHANGED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_GROUP_EXPANDED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_QR_CLICKED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_DETAILS_CLICKED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.TICKET_EVENT_CLICKED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.CHECKIN_SUCCESS]: { group: "post_purchase", trust: "trusted" },
  [TrackedAction.REVIEW_PROMPT_VIEWED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.REVIEW_SUBMITTED]: { group: "post_purchase", trust: "trusted" },
  [TrackedAction.VAULT_PREVIEW_CLICK_FROM_EVENT]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_PAGE_VIEW]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_ITEM_IMPRESSION]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_ITEM_CLICK]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_ITEM_VIEW]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_UNLOCK_CLICK]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_UNLOCK_SUCCESS]: { group: "vault_legacy", trust: "either" },
  [TrackedAction.VAULT_UNLOCK_FAILED]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_FOLLOW_UNLOCK]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_TICKET_UNLOCK]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_MEDIA_OPEN]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.VAULT_DOWNLOAD_CLICK]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.LEGACY_PAGE_VIEW_FROM_EVENT]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.HOST_FOLLOWED_FROM_EVENT]: { group: "vault_legacy", trust: "either" },
  [TrackedAction.HOST_CARD_IMPRESSION]: { group: "discovery", trust: "client" },
  [TrackedAction.HOST_CARD_CLICK]: { group: "discovery", trust: "client" },
  [TrackedAction.LEGACY_LOOKUP_SUBMIT]: { group: "discovery", trust: "client" },
  [TrackedAction.HOST_FOLLOW_CLICK]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.HOST_FILTER_USED]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_DIRECTORY_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_DIRECTORY_SEARCH]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_DIRECTORY_FILTER_USED]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_CARD_IMPRESSION]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_CARD_CLICK]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_PASSPORT_VIEW]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.FAN_DIRECTORY_OPT_IN]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.FAN_DIRECTORY_OPT_OUT]: { group: "vault_legacy", trust: "client" },
  [TrackedAction.MESSAGE_THREAD_CREATED]: { group: "discovery", trust: "client" },
  [TrackedAction.MESSAGE_SENT]: { group: "discovery", trust: "client" },
  [TrackedAction.MESSAGE_READ]: { group: "discovery", trust: "client" },
  [TrackedAction.MESSAGE_CTA_CLICKED]: { group: "discovery", trust: "client" },
  [TrackedAction.MESSAGE_REQUEST_RECEIVED]: { group: "discovery", trust: "client" },
  [TrackedAction.MESSAGE_REQUEST_ACCEPTED]: { group: "discovery", trust: "client" },
  [TrackedAction.MESSAGE_BLOCKED_USER]: { group: "discovery", trust: "client" },
  [TrackedAction.MESSAGE_REPORTED]: { group: "discovery", trust: "client" },
  [TrackedAction.HOST_MESSAGE_FAN_CLICKED]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_CONNECT_PAGE_VIEW]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_CONNECT_SETTINGS_UPDATED]: { group: "discovery", trust: "client" },
  [TrackedAction.FAN_CONNECT_ENABLED]: { group: "discovery", trust: "trusted" },
  [TrackedAction.FAN_CONNECT_DISABLED]: { group: "discovery", trust: "trusted" },
  [TrackedAction.FAN_CONNECT_SUGGESTION_IMPRESSION]: {
    group: "discovery",
    trust: "client",
  },
  [TrackedAction.FAN_CONNECT_SUGGESTION_CLICKED]: {
    group: "discovery",
    trust: "client",
  },
  [TrackedAction.FAN_CONNECT_REQUEST_SENT]: { group: "discovery", trust: "trusted" },
  [TrackedAction.FAN_CONNECT_REQUEST_ACCEPTED]: {
    group: "discovery",
    trust: "trusted",
  },
  [TrackedAction.FAN_CONNECT_REQUEST_DECLINED]: {
    group: "discovery",
    trust: "trusted",
  },
  [TrackedAction.FAN_CONNECT_CONNECTION_REMOVED]: {
    group: "discovery",
    trust: "trusted",
  },
  [TrackedAction.FAN_CONNECT_BLOCKED]: { group: "discovery", trust: "trusted" },
  [TrackedAction.FAN_CONNECT_REPORTED]: { group: "discovery", trust: "trusted" },
  [TrackedAction.FAN_FAN_MESSAGE_THREAD_CREATED]: {
    group: "discovery",
    trust: "trusted",
  },
  [TrackedAction.FAN_FAN_MESSAGE_SENT]: { group: "discovery", trust: "trusted" },
  [TrackedAction.SPONSOR_SLOT_CLICK_FROM_EVENT]: { group: "sponsorship", trust: "client" },
  [TrackedAction.SPONSOR_INQUIRY_FROM_EVENT]: { group: "sponsorship", trust: "either" },
  [TrackedAction.MERCH_SECTION_VIEWED]: { group: "detail", trust: "client" },
  [TrackedAction.MERCH_STOREFRONT_VIEW]: { group: "detail", trust: "client" },
  [TrackedAction.MERCH_PRODUCT_VIEW]: { group: "detail", trust: "client" },
  [TrackedAction.MERCH_VARIANT_SELECTED]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.MERCH_SIZE_CHART_OPENED]: { group: "ticket_intent", trust: "client" },
  [TrackedAction.MERCH_ADDED_TO_CART]: { group: "checkout", trust: "client" },
  [TrackedAction.MERCH_REMOVED_FROM_CART]: { group: "checkout", trust: "client" },
  [TrackedAction.MERCH_CHECKOUT_STARTED]: { group: "checkout", trust: "client" },
  [TrackedAction.MERCH_DISCOUNT_APPLIED]: { group: "checkout", trust: "client" },
  [TrackedAction.MERCH_BUNDLE_SELECTED]: { group: "checkout", trust: "client" },
  [TrackedAction.MERCH_PAYMENT_CONFIRMED]: { group: "checkout", trust: "trusted" },
  [TrackedAction.MERCH_PURCHASE_COMPLETED]: { group: "checkout", trust: "trusted" },
  [TrackedAction.MERCH_QR_VIEWED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.MERCH_QR_SCANNED]: { group: "post_purchase", trust: "trusted" },
  [TrackedAction.MERCH_PICKED_UP]: { group: "post_purchase", trust: "trusted" },
  [TrackedAction.MERCH_SHIPPED]: { group: "post_purchase", trust: "trusted" },
  [TrackedAction.MERCH_DELIVERED]: { group: "post_purchase", trust: "trusted" },
  [TrackedAction.MERCH_REVIEW_SUBMITTED]: { group: "post_purchase", trust: "trusted" },
  [TrackedAction.MERCH_ABANDONED_CART_CREATED]: { group: "commerce", trust: "trusted" },
  [TrackedAction.MERCH_ABANDONED_CART_RECOVERED]: { group: "commerce", trust: "trusted" },
  [TrackedAction.MERCH_POST_EVENT_DROP_VIEWED]: { group: "detail", trust: "client" },
  [TrackedAction.MERCH_VAULT_EXCLUSIVE_VIEWED]: { group: "detail", trust: "client" },
  [TrackedAction.MERCH_BADGE_AWARDED]: { group: "commerce", trust: "trusted" },
  [TrackedAction.MERCH_PICKUP_VIEWED]: { group: "post_purchase", trust: "client" },
  [TrackedAction.MERCH_SOLD_OUT]: { group: "commerce", trust: "trusted" },
  [TrackedAction.HOST_MERCH_PRODUCT_CREATED]: { group: "commerce", trust: "trusted" },
  [TrackedAction.HOST_MERCH_PRODUCT_UPDATED]: { group: "commerce", trust: "trusted" },
  [TrackedAction.HOST_MERCH_PRODUCT_PAUSED]: { group: "commerce", trust: "trusted" },
  [TrackedAction.HOST_MERCH_REVENUE_REPORT_VIEWED]: { group: "commerce", trust: "client" },
  [TrackedAction.ADMIN_MERCH_HIDDEN]: { group: "admin_finance", trust: "trusted" },
  [TrackedAction.SPONSOR_SALE]: { group: "commerce", trust: "trusted" },
  [TrackedAction.REFUND_APPROVED]: { group: "commerce", trust: "trusted" },
  [TrackedAction.VAULT_PURCHASE]: { group: "commerce", trust: "trusted" },
  [TrackedAction.PROMO_REDEMPTION]: { group: "commerce", trust: "trusted" },
  [TrackedAction.AMBASSADOR_SALE]: { group: "commerce", trust: "trusted" },
  [TrackedAction.PAYOUT_COMPLETED]: { group: "admin_finance", trust: "trusted" },
};

export type AnalyticsDimensions = {
  anonymousId?: string;
  sessionId?: string;
  requestId?: string;
  idempotencyKey?: string;
  occurredAt?: string;
  source?: string;
  medium?: string;
  campaign?: string;
  term?: string;
  content?: string;
  utmSource?: string;
  utmMedium?: string;
  utmCampaign?: string;
  utmTerm?: string;
  utmContent?: string;
  referrer?: string;
  landingPage?: string;
  path?: string;
  currentPath?: string;
  previousPath?: string;
  userAgent?: string;
  deviceType?: "mobile" | "tablet" | "desktop" | "unknown" | string;
  browser?: string;
  os?: string;
  country?: string;
  city?: string;
  metadata?: AnalyticsEventMetadata;
  isBot?: boolean;
  environment?: string;
  appVersion?: string;
  buildVersion?: string;
};

/** Event-specific metadata — never include email, card data, or private venue address. */
export type AnalyticsEventMetadata = {
  ticket_type_id?: string;
  ticket_type_name?: string;
  ticket_price?: number | string;
  promo_code?: string;
  ambassador_code?: string;
  order_id?: string;
  payment_reference?: string;
  card_position?: number;
  list_context?: string;
  page_section?: string;
  search_query?: string;
  category_filter?: string;
  city_filter?: string;
  country?: string;
  state?: string;
  city?: string;
  area?: string;
  category?: string;
  placement_context?: string;
  slot_number?: number;
  event_id?: string;
  sort_order?: string;
  share_channel?: string;
  conversion_value?: number | string;
  currency?: string;
  click_target?: string;
  quantity?: number;
  method?: string;
  vault_item_id?: string;
  vault_purchase_id?: string;
  access_type?: string;
  related_event_id?: string;
  locked_state?: string | boolean;
  source_page?: string;
  media_id?: string;
  failure_reason?: string;
  /** Sanitized path only — never query strings or tokens */
  path?: string;
  path_kind?: string;
  referrer_path?: string;
  user_agent?: string;
  logged_in?: boolean;
  q_length?: number;
  result_count?: number;
  merch_product_id?: string;
  merch_product_slug?: string;
  product_slug?: string;
  merch_variant_id?: string;
  variant_sku?: string;
  sku?: string;
  merch_item_count?: number;
  fulfillment_id?: string;
  fulfillment_method?: string;
  product_status?: string;
  moderation_status?: string;
  discount_code?: string;
  discount_applied?: boolean;
  bundle_id?: string;
  badge_key?: string;
  cart_id?: string;
  host_username?: string;
  event_slug?: string;
  [key: string]: string | number | boolean | undefined;
};

export function dimensionsToApiBody(dims?: AnalyticsDimensions): Record<string, unknown> {
  if (!dims) return {};
  return {
    anonymous_id: dims.anonymousId,
    session_id: dims.sessionId,
    request_id: dims.requestId ?? dims.idempotencyKey,
    idempotency_key: dims.idempotencyKey ?? dims.requestId,
    occurred_at: dims.occurredAt,
    source: dims.source ?? dims.utmSource,
    medium: dims.medium ?? dims.utmMedium,
    campaign: dims.campaign ?? dims.utmCampaign,
    term: dims.term ?? dims.utmTerm,
    content: dims.content ?? dims.utmContent,
    utm_source: dims.utmSource,
    utm_medium: dims.utmMedium,
    utm_campaign: dims.utmCampaign,
    utm_term: dims.utmTerm,
    utm_content: dims.utmContent,
    referrer: dims.referrer,
    landing_page: dims.landingPage,
    path: dims.path ?? dims.currentPath,
    current_path: dims.currentPath ?? dims.path,
    previous_path: dims.previousPath,
    user_agent: dims.userAgent,
    device_type: dims.deviceType,
    browser: dims.browser,
    os: dims.os,
    country: dims.country,
    city: dims.city,
    metadata: dims.metadata,
    is_bot: dims.isBot,
    environment: dims.environment,
    app_version: dims.appVersion ?? dims.buildVersion,
    build_version: dims.buildVersion ?? dims.appVersion,
  };
}

/** Legacy FE helpers still use older names — map when sending. */
export const LEGACY_ACTION_ALIASES: Record<string, TrackedActionName> = {
  page_view: TrackedAction.EVENT_DETAIL_VIEW,
  event_impression: TrackedAction.EVENT_CARD_IMPRESSION,
  event_click: TrackedAction.EVENT_CARD_CLICK,
  checkout_start: TrackedAction.CHECKOUT_PAGE_VIEW,
  checkout_complete: TrackedAction.PAYMENT_SUCCESS,
  payment_failed: TrackedAction.PAYMENT_FAILED,
  merch_product_viewed: TrackedAction.MERCH_PRODUCT_VIEW,
  merch_added_to_checkout: TrackedAction.MERCH_ADDED_TO_CART,
  merch_removed_from_checkout: TrackedAction.MERCH_REMOVED_FROM_CART,
  merch_marked_picked_up: TrackedAction.MERCH_PICKED_UP,
};

export function normalizeTrackedAction(raw: string): string {
  const key = raw.trim().toLowerCase();
  return LEGACY_ACTION_ALIASES[key] ?? key;
}
