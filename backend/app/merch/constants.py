"""Merch domain constants."""

PRODUCT_TYPES = (
    "t_shirt",
    "cap",
    "hoodie",
    "face_mask",
    "wristband",
    "poster",
    "tote_bag",
    "vip_pack",
    "souvenir",
    "other",
)
PRODUCT_TYPE_LABELS = {
    "t_shirt": "T-shirt",
    "cap": "Cap",
    "hoodie": "Hoodie",
    "face_mask": "Face mask",
    "wristband": "Wristband",
    "poster": "Poster",
    "tote_bag": "Tote bag",
    "vip_pack": "VIP pack",
    "souvenir": "Souvenir",
    "other": "Other",
}

# Marketplace commerce kinds (host required; event optional).
MERCH_KINDS = (
    "standalone",
    "event_addon",
    "event_merch",
    "post_event_drop",
    "vault_exclusive",
    "bundle",
)
MERCH_KIND_LABELS = {
    "standalone": "Standalone",
    "event_addon": "Add-on",
    "event_merch": "Event merch",
    "post_event_drop": "Post-event drop",
    "vault_exclusive": "Vault exclusive",
    "bundle": "Bundle",
}

# Browse categories (seeded in merch_categories; product.category stores slug).
MERCH_CATEGORY_SLUGS = (
    "apparel",
    "wristbands",
    "caps",
    "masks",
    "posters",
    "digital",
    "bundles",
    "collectibles",
    "food_drink",
    "other",
)
MERCH_CATEGORY_LABELS = {
    "apparel": "Apparel",
    "wristbands": "Wristbands",
    "caps": "Caps",
    "masks": "Masks",
    "posters": "Posters",
    "digital": "Digital items",
    "bundles": "Bundles",
    "collectibles": "Collectibles",
    "food_drink": "Food/drink vouchers",
    "other": "Other",
}

PRODUCT_STATUSES = ("draft", "active", "paused", "sold_out", "archived", "hidden")
MARKETPLACE_SORTS = ("featured", "newest", "price_asc", "price_desc", "popular")
# Public marketplace surfaces — never include private_link / event_only / hidden.
MARKETPLACE_PUBLIC_VISIBILITIES = frozenset(
    {"host_storefront", "post_event_drop", "vault_exclusive", "event_only"}
)
VARIANT_STATUSES = ("active", "sold_out", "paused", "archived")
FULFILLMENT_STATUSES = (
    "awaiting_pickup",
    "collect_at_stand",
    "awaiting_shipment",
    "packed",
    "shipped",
    "delivered",
    "fulfilled",
    "cancelled",
)
# Plan aliases → stored fulfillment status
FULFILLMENT_STATUS_ALIASES = {
    "pending": "awaiting_pickup",
    "ready_for_pickup": "collect_at_stand",
    "picked_up": "fulfilled",
    "refunded": "cancelled",
}
FULFILLMENT_EVENT_ACTIONS = (
    "created",
    "ready_for_pickup",
    "picked_up",
    "qr_scanned",
    "packed",
    "shipped",
    "delivered",
    "cancelled",
    "refunded",
    "note_added",
    "status_updated",
)
FULFILLMENT_METHODS = ("pickup", "shipping", "print_on_demand")
STOREFRONT_VISIBILITIES = (
    "event_only",
    "host_storefront",
    "vault_exclusive",
    "post_event_drop",
    "hidden",
    "public",
    "private_link",
)
# Alias map: product visibility request → stored storefront_visibility
VISIBILITY_ALIASES = {
    "public": "host_storefront",
    "event_only": "event_only",
    "vault_only": "vault_exclusive",
    "vault_exclusive": "vault_exclusive",
    "private_link": "private_link",
    "hidden": "hidden",
    "host_storefront": "host_storefront",
    "post_event_drop": "post_event_drop",
}
FULFILLMENT_TYPE_ALIASES = {
    "pickup": "pickup",
    "delivery": "shipping",
    "shipping": "shipping",
    "digital": "print_on_demand",
    "manual": "pickup",
    "print_on_demand": "print_on_demand",
}
# Host profile merch shop (host_profiles.merch_storefront_visibility)
HOST_STOREFRONT_VISIBILITIES = ("public", "unlisted", "hidden")
DISCOUNT_TYPES = ("percent", "fixed_amount", "free_shipping")
DISCOUNT_APPLIES_TO = (
    "merch_only",
    "bundles_only",
    "tickets_and_merch",
    "specific_products",
    "specific_event_merch",
    "host_storefront_merch",
)
DISCOUNT_STATUSES = ("active", "paused", "expired", "archived")
STOCK_ALERT_TYPES = (
    "low_stock",
    "sold_out",
    "restocked",
    "high_reserve",
    "pre_event_risk",
    "selling_fast",
)
REVIEW_STATUSES = ("pending", "published", "hidden_by_admin", "removed_by_user")
CART_STATUSES = ("active", "abandoned", "converted", "expired")
POD_PROVIDERS = ("manual", "printful", "printify", "custom")
POD_INTEGRATION_STATUSES = ("disabled", "connected", "error")
POD_JOB_STATUSES = (
    "pending",
    "manual_required",
    "queued",
    "fulfilled",
    "failed",
    "cancelled",
)
ACCESS_TYPES = (
    "follower",
    "ticket_holder",
    "checked_in_attendee",
    "vip_ticket_holder",
    "paid_vault_member",
    "invite_only",
)
MODERATION_STATUSES = ("clear", "flagged", "hidden", "removed")
REPORT_STATUSES = ("open", "reviewing", "resolved", "dismissed")
OPEN_REPORT_STATUSES = frozenset({"open", "reviewing"})
ITEM_KIND_TICKET = "ticket"
ITEM_KIND_MERCH = "merch"
ITEM_KIND_BUNDLE = "bundle"

MERCH_COLLECTOR_THRESHOLD = 3
DEFAULT_LOW_STOCK_THRESHOLD = 5
MERCH_QR_TYP = "padeya.merch.pickup"

# Hosts in these statuses should not sell public merch.
UNSAFE_HOST_STATUSES = frozenset({"suspended", "banned", "rejected", "inactive"})
UNSAFE_EVENT_STATUSES = frozenset({"cancelled", "paused", "archived"})
