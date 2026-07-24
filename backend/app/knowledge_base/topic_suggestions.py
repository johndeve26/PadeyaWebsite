"""Map Support Center topics → Help Center article/category/keyword hints."""

from __future__ import annotations

# Support category value → search keywords + preferred article slugs + audience.
TOPIC_HINTS: dict[str, dict] = {
    "account_login": {
        "keywords": ["login", "password", "account", "security", "session"],
        "slugs": ["login-and-account-security", "how-to-appeal-restriction"],
        "audiences": ["fan", "host", "visitor", "admin"],
        "category_slugs": ["login-and-security", "notifications"],
    },
    "tickets_orders": {
        "keywords": ["ticket", "qr", "order", "guest checkout", "buy for someone"],
        "slugs": [
            "how-to-buy-tickets",
            "how-guest-checkout-works",
            "how-to-find-your-qr-ticket",
            "how-to-buy-ticket-for-someone-else",
        ],
        "audiences": ["fan", "visitor"],
        "category_slugs": ["buying-tickets", "my-tickets-and-qr", "guest-checkout"],
    },
    "payments_refunds": {
        "keywords": ["refund", "payment", "pending", "fees", "checkout"],
        "slugs": [
            "how-refunds-work",
            "how-payments-work",
            "how-padeya-fees-and-host-earnings-work",
        ],
        "audiences": ["fan", "host", "visitor"],
        "category_slugs": ["refunds", "secure-payments", "platform-fees"],
    },
    "event_issue": {
        "keywords": ["event", "venue", "cancelled", "reschedule", "listing"],
        "slugs": ["find-events-on-padeya", "how-refunds-work"],
        "audiences": ["fan", "visitor"],
        "category_slugs": ["finding-events", "reviews"],
    },
    "host_issue": {
        "keywords": ["host", "publish", "check-in", "team", "create event"],
        "slugs": [
            "how-to-become-a-host",
            "create-your-first-event",
            "how-qr-check-in-works",
            "how-hosts-add-team-members",
        ],
        "audiences": ["host"],
        "category_slugs": [
            "becoming-a-host",
            "creating-events",
            "qr-check-in",
            "host-team",
        ],
    },
    "merch": {
        "keywords": ["merch", "vault", "drop", "pickup"],
        "slugs": ["how-merch-and-post-event-drops-work", "how-vault-content-works"],
        "audiences": ["fan", "host", "visitor"],
        "category_slugs": ["merch", "vault", "merch-studio", "vault-studio"],
    },
    "fan_connect": {
        "keywords": ["fan connect", "suggestions", "privacy", "block"],
        "slugs": [
            "how-fan-connect-suggestions-work",
            "how-to-create-fan-passport",
            "how-to-block-or-report-someone",
        ],
        "audiences": ["fan"],
        "category_slugs": ["fan-connect", "fan-passport", "privacy-settings"],
    },
    "messaging_abuse": {
        "keywords": ["message", "report", "block", "abuse", "safety"],
        "slugs": ["how-to-block-or-report-someone", "login-and-account-security"],
        "audiences": ["fan", "host", "visitor"],
        "category_slugs": ["messages", "reports-and-blocking", "privacy-settings"],
    },
    "sponsorship": {
        "keywords": ["sponsor", "sponsorship", "brand", "inquiry"],
        "slugs": ["how-sponsorship-inquiries-work"],
        "audiences": ["sponsor", "host"],
        "category_slugs": [
            "finding-hosts-events",
            "sending-sponsorship-inquiries",
            "managing-sponsorship-requests",
            "sponsorships",
        ],
    },
    "ambassador": {
        "keywords": ["ambassador", "campaign", "referral", "reward"],
        "slugs": ["how-ambassador-campaigns-work"],
        "audiences": ["ambassador", "host", "fan"],
        "category_slugs": [
            "joining-campaigns",
            "sharing-events",
            "tracking-conversions",
            "rewards-and-payouts",
            "ambassador-campaigns",
        ],
    },
    "technical": {
        "keywords": ["bug", "error", "loading", "app", "technical"],
        "slugs": ["how-to-contact-support", "login-and-account-security"],
        "audiences": ["fan", "host", "visitor", "admin"],
        "category_slugs": ["login-and-security", "notifications"],
    },
    "other": {
        "keywords": ["help", "support", "contact"],
        "slugs": ["how-to-contact-support"],
        "audiences": ["fan", "host", "visitor", "admin", "sponsor", "ambassador"],
        "category_slugs": ["support-tickets"],
    },
}
