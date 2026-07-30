"""Fan Passport badge catalog and thresholds."""

from __future__ import annotations

# Checked-in events for one host required for Superfan
SUPERFAN_CHECKIN_THRESHOLD = 3

# VIP/VVIP tickets (active or checked_in) required for VIP Regular
VIP_REGULAR_THRESHOLD = 2

# Distinct checked-in events for Event Hopper
EVENT_HOPPER_THRESHOLD = 3

# Category-based badges
CATEGORY_BADGE_THRESHOLD = 2

# Merch collector: distinct paid merch products (never expose spend)
MERCH_COLLECTOR_THRESHOLD = 3

# Culture Fest Collector: distinct paid merch products from culture/fest events
CULTURE_FEST_COLLECTOR_THRESHOLD = 1

# Category slugs that count toward Culture Fest Collector
CULTURE_FEST_CATEGORY_SLUGS = frozenset({"arts-culture", "art-culture", "culture"})

# Category slugs that count toward Founder Mode Gear (with founders/tech events)
FOUNDER_MODE_CATEGORY_SLUGS = frozenset({"tech", "business"})

# Merch badge criteria keys (award after verified payment; none require pickup today)
MERCH_BADGE_CRITERIA = frozenset(
    {
        "first_merch_buy",
        "merch_collector",
        "vip_pack_owner",
        "event_drop_supporter",
        "vault_merch_member",
        "sponsor_drop_supporter",
        "culture_fest_collector",
        "founder_mode_gear",
    }
)

# Badges that wait for pickup/fulfilled or shipped/delivered — currently none.
# Award/confirm after payment only for all merch badges above.
MERCH_BADGES_REQUIRING_FULFILLMENT = frozenset()

DEFAULT_BADGES: list[dict[str, str]] = [
    {
        "slug": "first-ticket",
        "name": "First Ticket",
        "description": "Bought your first ticket on Pàdéyá.",
        "criteria_key": "first_ticket",
    },
    {
        "slug": "verified-attendee",
        "name": "Verified Attendee",
        "description": "Checked in to at least one event.",
        "criteria_key": "verified_attendee",
    },
    {
        "slug": "day-one-fan",
        "name": "Day One Fan",
        "description": "Follow a host and check in to one of their events.",
        "criteria_key": "day_one_fan",
    },
    {
        "slug": "vip-regular",
        "name": "VIP Regular",
        "description": "Hold multiple VIP or VVIP tickets.",
        "criteria_key": "vip_regular",
    },
    {
        "slug": "superfan",
        "name": "Superfan",
        "description": "Check in to many events from the same host.",
        "criteria_key": "superfan",
    },
    {
        "slug": "early-bird",
        "name": "Early Bird",
        "description": "Bought an early-bird ticket.",
        "criteria_key": "early_bird",
    },
    {
        "slug": "nightlife-explorer",
        "name": "Nightlife Explorer",
        "description": "Checked in to multiple Nightlife events.",
        "criteria_key": "nightlife_explorer",
    },
    {
        "slug": "concert-lover",
        "name": "Concert Lover",
        "description": "Checked in to multiple Music events.",
        "criteria_key": "concert_lover",
    },
    {
        "slug": "event-hopper",
        "name": "Event Hopper",
        "description": "Checked in across many different events.",
        "criteria_key": "event_hopper",
    },
    {
        "slug": "table-buyer",
        "name": "Table Buyer",
        "description": "Purchased a table ticket.",
        "criteria_key": "table_buyer",
    },
    {
        "slug": "vault-member",
        "name": "Vault Member",
        "description": "Unlocked Vault content with a paid purchase.",
        "criteria_key": "vault_member",
    },
    {
        "slug": "lagos-explorer",
        "name": "Lagos Explorer",
        "description": "Checked in to multiple Lagos events.",
        "criteria_key": "lagos_explorer",
    },
    {
        "slug": "checked-in-attendee",
        "name": "Checked-in Attendee",
        "description": "Completed a verified check-in at an event.",
        "criteria_key": "checked_in_attendee",
    },
    {
        "slug": "tech-regular",
        "name": "Tech Regular",
        "description": "Checked in to multiple Tech events.",
        "criteria_key": "tech_regular",
    },
    {
        "slug": "comedy-fan",
        "name": "Comedy Fan",
        "description": "Checked in to multiple Comedy events.",
        "criteria_key": "comedy_fan",
    },
    {
        "slug": "reviewer",
        "name": "Reviewer",
        "description": "Wrote a verified review on Pàdéyá.",
        "criteria_key": "reviewer",
    },
    {
        "slug": "review-writer",
        "name": "Review Writer",
        "description": "Shared multiple verified reviews.",
        "criteria_key": "review_writer",
    },
    {
        "slug": "campus-explorer",
        "name": "Campus Explorer",
        "description": "Checked in to campus or student community events.",
        "criteria_key": "campus_explorer",
    },
    {
        "slug": "first-merch-buy",
        "name": "First Merch Buy",
        "description": "Bought your first event merch on Pàdéyá.",
        "criteria_key": "first_merch_buy",
    },
    {
        "slug": "merch-collector",
        "name": "Merch Collector",
        "description": "Collected merch from multiple event drops.",
        "criteria_key": "merch_collector",
    },
    {
        "slug": "vip-pack-owner",
        "name": "VIP Pack Owner",
        "description": "Purchased a VIP merch pack.",
        "criteria_key": "vip_pack_owner",
    },
    {
        "slug": "event-drop-supporter",
        "name": "Event Drop Supporter",
        "description": "Supported a post-event merch drop.",
        "criteria_key": "event_drop_supporter",
    },
    {
        "slug": "vault-merch-member",
        "name": "Vault Merch Member",
        "description": "Unlocked Vault-exclusive merch.",
        "criteria_key": "vault_merch_member",
    },
    {
        "slug": "sponsor-drop-supporter",
        "name": "Sponsor Drop Supporter",
        "description": "Supported sponsor-branded event merch.",
        "criteria_key": "sponsor_drop_supporter",
    },
    {
        "slug": "culture-fest-collector",
        "name": "Culture Fest Collector",
        "description": "Collected merch from culture or festival events.",
        "criteria_key": "culture_fest_collector",
    },
    {
        "slug": "founder-mode-gear",
        "name": "Founder Mode Gear",
        "description": "Got founder or Tech Connect event merch on Pàdéyá.",
        "criteria_key": "founder_mode_gear",
    },
]

# Ticket statuses that count as ownership (not attendance)
OWNED_TICKET_STATUSES = ("active", "checked_in")
# Attendance is strictly check-in
ATTENDED_TICKET_STATUSES = ("checked_in",)
# Explicitly excluded from attendance / loyalty
EXCLUDED_TICKET_STATUSES = ("cancelled", "refunded", "expired", "invalid", "reserved")
