"""Built-in audience segment catalog."""

from decimal import Decimal

# Lifetime paid spend (NGN) for VIP if ticket type is not vip/vvip
VIP_SPEND_THRESHOLD = Decimal("50000.00")

SYSTEM_SEGMENTS: list[dict[str, str]] = [
    {
        "slug": "followers",
        "name": "Followers",
        "segment_key": "followers",
        "description": "People who follow this host.",
    },
    {
        "slug": "past-buyers",
        "name": "Past buyers",
        "segment_key": "past_buyers",
        "description": "Buyers with at least one paid order.",
    },
    {
        "slug": "repeat-buyers",
        "name": "Repeat buyers",
        "segment_key": "repeat_buyers",
        "description": "Buyers across two or more events.",
    },
    {
        "slug": "vip-buyers",
        "name": "VIP buyers",
        "segment_key": "vip_buyers",
        "description": "VIP/VVIP ticket holders or high spenders.",
    },
    {
        "slug": "checked-in-attendees",
        "name": "Checked-in attendees",
        "segment_key": "checked_in_attendees",
        "description": "Ticket holders who checked in.",
    },
    {
        "slug": "no-shows",
        "name": "No-shows",
        "segment_key": "no_shows",
        "description": "Had a ticket for an ended event but never checked in.",
    },
    {
        "slug": "promo-code-buyers",
        "name": "Promo-code buyers",
        "segment_key": "promo_code_buyers",
        "description": "Paid orders that used a promo code.",
    },
    {
        "slug": "ambassador-referrals",
        "name": "Ambassador referrals",
        "segment_key": "ambassador_referrals",
        "description": "Paid orders attributed to an ambassador referral.",
    },
    {
        "slug": "superfans",
        "name": "Superfans",
        "segment_key": "superfans",
        "description": "Placeholder — loyalty scoring not implemented yet.",
    },
    {
        "slug": "vault-subscribers",
        "name": "Vault subscribers",
        "segment_key": "vault_subscribers",
        "description": "Placeholder — Vault not implemented yet.",
    },
]
