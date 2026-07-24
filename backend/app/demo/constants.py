"""Demo seed constants — local development only."""

from __future__ import annotations

DEMO_EMAIL_DOMAIN = "demo.padeye.test"
DEMO_PASSWORD = "DemoPass123!"
DEMO_EVENT_SLUG_PREFIX = "demo-"
DEMO_MARKER_NAMESPACE = "padeya.demo"

# Persona product context for messaging (tickets / attendance / Vault / reviews).
# Applied idempotently after commerce + Vault so Message Host/Fan CTAs feel connected.
DEMO_PERSONA_CONTEXT: list[dict] = [
    {
        "email": f"fan1@{DEMO_EMAIL_DOMAIN}",  # Tolu
        "upcoming": ["afrobeats-night-live", "founders-mixer-lagos"],
        "attended": ["island-comedy-night"],
        "vip_events": [],
        "vault_paid_slugs": ["secret-location"],
        "review_event": "island-comedy-night",
        "review_body": (
            "Sunday Comedy Room was sharp. Check-in with my Pàdéyá ticket was smooth."
        ),
    },
    {
        "email": f"fan2@{DEMO_EMAIL_DOMAIN}",  # Amaka
        "upcoming": ["afrobeats-night-live"],
        "attended": ["detty-friday-live"],
        "vip_events": [],
        "vault_paid_slugs": ["unreleased-set"],
        "review_event": "detty-friday-live",
        "review_body": (
            "Detty Friday Rooftop delivered. Open your Pàdéyá ticket next time — "
            "entry was fast."
        ),
    },
    {
        "email": f"fan3@{DEMO_EMAIL_DOMAIN}",  # Chidi
        "upcoming": ["afrobeats-night-live", "founders-mixer-lagos"],
        "attended": ["startup-demo-evening", "food-and-flow"],
        "vip_events": [],
        "vault_paid_slugs": [],
        "review_event": "startup-demo-evening",
        "review_body": (
            "Product Demo Night was useful. Your ticket-holder Vault access should unlock "
            "after check-in — mine did after I refreshed my Vault page."
        ),
    },
    {
        "email": f"fan4@{DEMO_EMAIL_DOMAIN}",  # Sade
        "upcoming": ["afrobeats-night-live", "lagos-comedy-jam"],
        "attended": ["island-comedy-night"],
        "vip_events": [],
        "vault_paid_slugs": [],
        "review_event": "island-comedy-night",
        "review_body": "Great comedy night. I’ll keep following Lagos Comedy Hub on Pàdéyá.",
    },
    {
        "email": f"fan5@{DEMO_EMAIL_DOMAIN}",  # Kunle VIP
        "upcoming": ["founders-mixer-lagos"],
        "attended": ["detty-friday-live"],
        "vip_events": ["afrobeats-night-live", "detty-friday-live"],
        "vault_paid_slugs": ["unreleased-set"],
        "review_event": "detty-friday-live",
        "review_body": "VIP rails felt premium. Vault unlocks are a nice plus on Pàdéyá.",
    },
    {
        "email": f"fan6@{DEMO_EMAIL_DOMAIN}",  # Mira
        "upcoming": ["mainland-after-dark", "founders-mixer-lagos"],
        "attended": ["detty-friday-live", "food-and-flow"],
        "vip_events": [],
        "vault_paid_slugs": [],
        "review_event": "detty-friday-live",
        "review_body": (
            "Detty Friday check-in was smooth. Left this verified review on Pàdéyá."
        ),
    },
    {
        "email": f"fan7@{DEMO_EMAIL_DOMAIN}",  # Ada — private Passport; mainland discovery
        "upcoming": ["mainland-vibes-summer"],
        "attended": [],
        "vip_events": [],
        "vault_paid_slugs": [],
        "review_event": None,
        "review_body": None,
    },
    {
        "email": f"fan8@{DEMO_EMAIL_DOMAIN}",  # Bayo
        "upcoming": ["founders-mixer-lagos", "mainland-vibes-summer"],
        "attended": ["detty-friday-live", "startup-demo-evening"],
        "vip_events": [],
        "vault_paid_slugs": [],
        "review_event": "detty-friday-live",
        "review_body": "Campus-friendly night. Booked through Pàdéyá and used my QR at check-in.",
    },
]

# Primary accounts shown on /demo (emails are for local login only — never public)
DEMO_ACCOUNTS: list[dict[str, str]] = [
    {
        "email": f"buyer@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Demo Buyer",
        "role": "buyer",
    },
    {
        "email": f"host@{DEMO_EMAIL_DOMAIN}",
        "full_name": "DJ Maze",
        "role": "host",
    },
    {
        "email": f"host2@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Lagos Comedy Hub",
        "role": "host",
    },
    {
        "email": f"staff@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Gate Staff",
        "role": "host_staff",
    },
    {
        "email": f"support@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Demo Support Agent",
        "role": "support_agent",
    },
    {
        "email": f"finance@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Finance Admin",
        "role": "finance_admin",
    },
    {
        "email": f"admin@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Demo Super Admin",
        "role": "super_admin",
    },
]

# Extra host owners (still demo-scoped emails)
EXTRA_HOST_ACCOUNTS: list[dict[str, str]] = [
    {
        "email": f"mainland@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Mainland Vibes",
        "role": "host",
    },
    {
        "email": f"tech@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Tech Connect Africa",
        "role": "host",
    },
    {
        "email": f"praise@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Praise Experience",
        "role": "host",
    },
]

# DJ Maze host-team accounts (login password = DEMO_PASSWORD).
# RBAC role host_staff; host-team role/permissions live on HostTeamMember.
DEMO_TEAM_ACCOUNTS: list[dict[str, str]] = [
    {
        "email": f"ops@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Event Ops Manager",
        "role": "host_staff",
    },
    {
        "email": f"gate@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Gate Scanner",
        "role": "host_staff",
    },
    {
        "email": f"pickup@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Pickup Staff",
        "role": "host_staff",
    },
    {
        "email": f"sponsor-observer@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Sponsor Observer",
        "role": "host_staff",
    },
    {
        "email": f"team-invitee@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Pending Teammate",
        "role": "buyer",
    },
]

# Stable raw invite token for /team/invite/{token} demo shortcut (hashed in DB).
DEMO_TEAM_INVITE_TOKEN = "demo-padeya-team-invite-afrobeats"

# Membership specs for DJ Maze (host slug ``djmaze``).
# event_keys resolve via DEMO_EVENT_SLUG_PREFIX + key (e.g. afrobeats-night-live).
DEMO_TEAM_MEMBERS: list[dict] = [
    {
        "email": f"ops@{DEMO_EMAIL_DOMAIN}",
        "role": "admin",
        "role_label": "Event Ops Manager",
        "scope": "host_wide",
        "event_keys": [],
        "permission_overrides": None,  # admin preset
    },
    {
        "email": f"gate@{DEMO_EMAIL_DOMAIN}",
        "role": "scanner",
        "role_label": "Gate Scanner",
        "scope": "selected_events",
        "event_keys": ["afrobeats-night-live"],
        "permission_overrides": {
            "tickets.scan_qr": True,
            "tickets.check_in": True,
        },
    },
    {
        "email": f"pickup@{DEMO_EMAIL_DOMAIN}",
        "role": "merch_staff",
        "role_label": "Pickup Staff",
        "scope": "selected_events",
        "event_keys": ["afrobeats-night-live"],
        "permission_overrides": {
            "merch.scan_pickup_qr": True,
            "merch.mark_picked_up": True,
        },
    },
    {
        "email": f"sponsor-observer@{DEMO_EMAIL_DOMAIN}",
        "role": "viewer",
        "role_label": "Sponsor Observer",
        "scope": "host_wide",
        "event_keys": [],
        "permission_overrides": {
            "_replace": True,
            "sponsors.view": True,
            "analytics.view_sponsors": True,
        },
    },
]

# Host profiles — stable slugs; sponsor_ready / vault_enabled drive seed flags
DEMO_HOSTS: list[dict] = [
    {
        "slug": "djmaze",
        "owner_email": f"host@{DEMO_EMAIL_DOMAIN}",
        "display_name": "DJ Maze",
        "category": "Music / Nightlife",
        "primary_category_slug": "nightlife",
        "host_type_slug": "dj-artist",
        "tier_slug": "icon",
        "city": "Lagos",
        "state": "Lagos",
        "sponsor_ready": True,
        "vault_enabled": True,
        "bio": "Premium Afrobeats and nightlife experiences across Lagos.",
        "avatar": "hosts/djmaze-avatar.svg",
        "cover": "hosts/djmaze-cover.svg",
    },
    {
        "slug": "lagoscomedyhub",
        "owner_email": f"host2@{DEMO_EMAIL_DOMAIN}",
        "display_name": "Lagos Comedy Hub",
        "category": "Comedy",
        "primary_category_slug": "comedy",
        "host_type_slug": "comedy-collective",
        "tier_slug": "established",
        "city": "Lagos",
        "state": "Lagos",
        "sponsor_ready": True,
        "vault_enabled": True,
        "bio": "Stand-up comedy shows, open mic nights, and live entertainment.",
        "avatar": "hosts/lagoscomedyhub-avatar.svg",
        "cover": "hosts/lagoscomedyhub-cover.svg",
    },
    {
        "slug": "techconnectafrica",
        "owner_email": f"tech@{DEMO_EMAIL_DOMAIN}",
        "display_name": "Tech Connect Africa",
        "category": "Tech / Business",
        "primary_category_slug": "tech",
        "host_type_slug": "tech-community",
        "tier_slug": "established",
        "city": "Lagos",
        "state": "Lagos",
        "sponsor_ready": True,
        "vault_enabled": True,
        "bio": "Founder mixers, tech talks, product demos, and networking events.",
        "avatar": "hosts/techconnectafrica-avatar.svg",
        "cover": "hosts/techconnectafrica-cover.svg",
    },
    {
        "slug": "praiseexperience",
        "owner_email": f"praise@{DEMO_EMAIL_DOMAIN}",
        "display_name": "Praise Experience",
        "category": "Gospel / Worship",
        "primary_category_slug": "gospel",
        "host_type_slug": "faith-organization",
        "tier_slug": "rising",
        "city": "Ibadan",
        "state": "Oyo",
        "sponsor_ready": False,
        "vault_enabled": True,
        "bio": "Gospel concerts, worship nights, and inspirational gatherings.",
        "avatar": "hosts/praiseexperience-avatar.svg",
        "cover": "hosts/praiseexperience-cover.svg",
    },
    {
        "slug": "mainlandvibes",
        "owner_email": f"mainland@{DEMO_EMAIL_DOMAIN}",
        "display_name": "Mainland Vibes",
        "category": "Lifestyle / Culture",
        "primary_category_slug": "lifestyle",
        "host_type_slug": "lifestyle-brand",
        "tier_slug": "rising",
        "city": "Lagos",
        "state": "Lagos",
        "sponsor_ready": True,
        "vault_enabled": True,
        "bio": "Youthful social events, games nights, and culture-led gatherings.",
        "avatar": "hosts/mainlandvibes-avatar.svg",
        "cover": "hosts/mainlandvibes-cover.svg",
    },
]

# Named fan personas (fan1–fan8). Emails are internal login only — never shown on public Passport.
# fan9–fan20 remain generic volume accounts for commerce/messaging.
DEMO_FAN_PERSONAS: list[dict] = [
    {
        "email": f"fan1@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Tolu Nightlife Explorer",
        "username": "toluwave",
        "display_name": "Tolu Nightlife Explorer",
        "tagline": "Chasing afterparties and verified Detty stamps.",
        "visibility": "public",
        "appear_in_directory": True,
        "city": "Lagos",
        "categories": ["Nightlife", "Music"],
        "badge_slugs": [
            "verified-attendee",
            "nightlife-explorer",
            "early-bird",
        ],
        # Hosts followed or attended may Message Fan; no cold public requests
        "allow_messages_from_hosts_i_follow": True,
        "allow_messages_from_hosts_i_attended": True,
        "allow_messages_from_public": False,
        "message_requests_enabled": True,
    },
    {
        "email": f"fan2@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Amaka Concert Lover",
        "username": "amakaconcerts",
        "display_name": "Amaka Concert Lover",
        "tagline": "Front-row energy. Badges over FOMO.",
        "visibility": "public",
        "appear_in_directory": True,
        "city": "Lagos",
        "categories": ["Music", "Concerts"],
        "badge_slugs": ["concert-lover", "vault-member", "superfan"],
        "allow_messages_from_hosts_i_follow": True,
        "allow_messages_from_hosts_i_attended": False,
        "allow_messages_from_public": False,
        "message_requests_enabled": True,
    },
    {
        "email": f"fan3@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Chidi Tech Regular",
        "username": "chiditech",
        "display_name": "Chidi Tech Regular",
        "tagline": "Founders mixers, product nights, notebook always ready.",
        "visibility": "public",
        "appear_in_directory": True,
        "city": "Lagos",
        "categories": ["Tech", "Networking"],
        "badge_slugs": [
            "tech-regular",
            "checked-in-attendee",
            "reviewer",
        ],
        "allow_messages_from_hosts_i_follow": False,
        "allow_messages_from_hosts_i_attended": True,
        "allow_messages_from_public": False,
        "message_requests_enabled": True,
    },
    {
        "email": f"fan4@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Sade Comedy Fan",
        "username": "sadecomedy",
        "display_name": "Sade Comedy Fan",
        "tagline": "Island punchlines and mainland open mics.",
        "visibility": "public",
        "appear_in_directory": True,
        "city": "Lagos",
        "categories": ["Comedy"],
        "badge_slugs": ["comedy-fan", "review-writer"],
        "allow_messages_from_hosts_i_follow": True,
        "allow_messages_from_hosts_i_attended": True,
        "allow_messages_from_public": False,
        "message_requests_enabled": True,
    },
    {
        "email": f"fan5@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Kunle VIP Regular",
        "username": "kunlevip",
        "display_name": "Kunle VIP Regular",
        "tagline": "VIP rails, Vault unlocks, Host Legacy loyalist.",
        "visibility": "public",
        "appear_in_directory": False,
        "city": "Lagos",
        "categories": ["Nightlife", "VIP"],
        "badge_slugs": ["vip-regular", "table-buyer"],
        "allow_messages_from_hosts_i_follow": False,
        "allow_messages_from_hosts_i_attended": True,
        "allow_messages_from_public": False,
        "message_requests_enabled": True,
    },
    {
        "email": f"fan6@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Mira Lagos Explorer",
        "username": "miralagos",
        "display_name": "Mira Lagos Explorer",
        "tagline": "City-hopping — Passport stays private.",
        "visibility": "private",
        "appear_in_directory": False,
        "city": "Lagos",
        "categories": ["Arts", "Food"],
        "badge_slugs": ["lagos-explorer"],
        # Private Passport — no public Message Fan CTA
        "allow_messages_from_hosts_i_follow": False,
        "allow_messages_from_hosts_i_attended": False,
        "allow_messages_from_public": False,
        "message_requests_enabled": False,
    },
    {
        "email": f"fan7@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Ada First Timer",
        "username": "adafirsttimer",
        "display_name": "Ada First Timer",
        "tagline": "First Pàdéyá ticket. Quiet Passport.",
        "visibility": "private",
        "appear_in_directory": False,
        "city": "Ibadan",
        "categories": ["Gospel"],
        "badge_slugs": ["first-ticket"],
        # Private Passport; Ada messages hosts via event pages (fan→host)
        "allow_messages_from_hosts_i_follow": False,
        "allow_messages_from_hosts_i_attended": False,
        "allow_messages_from_public": False,
        "message_requests_enabled": False,
    },
    {
        "email": f"fan8@{DEMO_EMAIL_DOMAIN}",
        "full_name": "Bayo Campus Fan",
        "username": "bayocampus",
        "display_name": "Bayo Campus Fan",
        "tagline": "Campus nights — unlisted Passport, direct link only.",
        "visibility": "unlisted",
        "appear_in_directory": False,
        "city": "Akure",
        "categories": ["Campus", "Lifestyle", "Tech"],
        "badge_slugs": ["campus-explorer"],
        "allow_messages_from_hosts_i_follow": True,
        "allow_messages_from_hosts_i_attended": True,
        "allow_messages_from_public": False,
        "message_requests_enabled": True,
    },
]

DEMO_CATEGORY_EXTRAS: list[tuple[str, str, str]] = [
    ("Tech", "tech", "Product demos, meetups, and founder sessions"),
    ("Gospel", "gospel", "Worship nights and faith gatherings"),
    ("Conference", "conference", "Multi-session conferences and summits"),
    ("Food & Drink", "food-drink", "Food festivals and tasting events"),
    ("Campus", "campus", "Student and campus community events"),
    ("Lifestyle", "lifestyle", "Games nights, socials, and lifestyle experiences"),
    ("Sports", "sports", "Sports watch parties and tournaments"),
    ("Art & Culture", "art-culture", "Art walks, exhibitions, and culture nights"),
]

PROMO_CODES: list[dict] = [
    {"code": "MAZE20", "discount_type": "percentage", "discount_value": 20, "host_slug": "djmaze"},
    {"code": "EARLYBIRD", "discount_type": "fixed", "discount_value": 1500, "host_slug": "djmaze"},
    {"code": "VIP10", "discount_type": "percentage", "discount_value": 10, "host_slug": "djmaze"},
    {"code": "COMEDY5", "discount_type": "fixed", "discount_value": 500, "host_slug": "lagoscomedyhub"},
    {"code": "TECHFREE", "discount_type": "percentage", "discount_value": 100, "host_slug": "techconnectafrica"},
    {"code": "PRAISE15", "discount_type": "percentage", "discount_value": 15, "host_slug": "praiseexperience"},
    {"code": "MAINLAND25", "discount_type": "percentage", "discount_value": 25, "host_slug": "mainlandvibes"},
    {"code": "STUDENT10", "discount_type": "percentage", "discount_value": 10, "host_slug": "mainlandvibes"},
    {"code": "GROUPSAVE", "discount_type": "fixed", "discount_value": 5000, "host_slug": "djmaze", "status": "inactive"},
    {"code": "VAULTDROP", "discount_type": "percentage", "discount_value": 30, "host_slug": "djmaze"},
]

AMBASSADORS: list[dict[str, str]] = [
    {"display_name": "Tola", "referral_code": "tola-demo"},
    {"display_name": "Kunle", "referral_code": "kunle-demo"},
    {"display_name": "Amaka", "referral_code": "amaka-demo"},
    {"display_name": "Femi", "referral_code": "femi-demo"},
    {"display_name": "Zainab", "referral_code": "zainab-demo"},
    {"display_name": "Chinedu", "referral_code": "chinedu-demo"},
    {"display_name": "Seyi", "referral_code": "seyi-demo"},
    {"display_name": "Joy", "referral_code": "joy-demo"},
]

# Open Event Ambassadors demo (DJ Maze · Afrobeats Night Live).
# Codes are stored lowercase; display as TOLUAFRO / AMAKA20 / CHIDILIVE.
OPEN_AMBASSADOR_EVENT_KEY = "afrobeats-night-live"
OPEN_AMBASSADOR_CAMPAIGN_NAME = "Afrobeats Night Ambassador Drive"
OPEN_AMBASSADOR_PARTICIPANTS: list[dict[str, object]] = [
    {
        "email": f"fan1@{DEMO_EMAIL_DOMAIN}",
        "display_name": "Tolu Nightlife Explorer",
        "code": "toluafro",
        "clicks": 14,
    },
    {
        "email": f"fan2@{DEMO_EMAIL_DOMAIN}",
        "display_name": "Amaka Concert Lover",
        "code": "amaka20",
        "clicks": 8,
    },
    {
        "email": f"fan3@{DEMO_EMAIL_DOMAIN}",
        "display_name": "Chidi Tech Regular",
        "code": "chidilive",
        "clicks": 5,
    },
]

HOST_SLUGS = [h["slug"] for h in DEMO_HOSTS]
FAN_PERSONA_BY_EMAIL = {p["email"]: p for p in DEMO_FAN_PERSONAS}

# Showcase events used by messaging demos + /demo links.
# lifecycle: "upcoming" (published) | "completed" (published → checked-in → reviews).
# location_mode: public-safe only ("full_public" | "area_only") — never secret street for these.
DEMO_SHOWCASE_EVENTS: list[dict] = [
    {
        "key": "afrobeats-night-live",
        "title": "Afrobeats Night Live",
        "host_slug": "djmaze",
        "category_slug": "music",
        "lifecycle": "upcoming",
        "city": "Lagos",
        "location_mode": "full_public",
        "featured": True,
        "vault": True,
    },
    {
        "key": "detty-friday-live",
        "title": "Detty Friday Rooftop",
        "host_slug": "djmaze",
        "category_slug": "nightlife",
        "lifecycle": "completed",
        "city": "Lagos",
        "location_mode": "area_only",
        "featured": False,
        "vault": True,
    },
    {
        "key": "mainland-after-dark",
        "title": "Mainland After Dark",
        "host_slug": "djmaze",
        "category_slug": "nightlife",
        "lifecycle": "upcoming",
        "city": "Lagos",
        "location_mode": "area_only",
        "featured": True,
        "vault": True,
    },
    {
        "key": "lagos-comedy-jam",
        "title": "Laugh Lagos Live",
        "host_slug": "lagoscomedyhub",
        "category_slug": "comedy",
        "lifecycle": "upcoming",
        "city": "Lagos",
        "location_mode": "full_public",
        "featured": True,
        "vault": True,
    },
    {
        "key": "island-comedy-night",
        "title": "Sunday Comedy Room",
        "host_slug": "lagoscomedyhub",
        "category_slug": "comedy",
        "lifecycle": "completed",
        "city": "Lagos",
        "location_mode": "area_only",
        "featured": False,
        "vault": True,
    },
    {
        "key": "founders-mixer-lagos",
        "title": "Founders Mixer Lagos",
        "host_slug": "techconnectafrica",
        "category_slug": "tech",
        "lifecycle": "upcoming",
        "city": "Lagos",
        "location_mode": "full_public",
        "featured": True,
        "vault": True,
    },
    {
        "key": "startup-demo-evening",
        "title": "Product Demo Night",
        "host_slug": "techconnectafrica",
        "category_slug": "business",
        "lifecycle": "completed",
        "city": "Lagos",
        "location_mode": "area_only",
        "featured": False,
        "vault": True,
    },
    {
        "key": "praise-experience-live",
        "title": "Choir & Community Live",
        "host_slug": "praiseexperience",
        "category_slug": "gospel",
        "lifecycle": "upcoming",
        "city": "Ibadan",
        "location_mode": "full_public",
        "featured": False,
        "vault": True,
    },
    {
        "key": "worship-under-stars",
        "title": "Worship Night Ibadan",
        "host_slug": "praiseexperience",
        "category_slug": "gospel",
        "lifecycle": "completed",
        "city": "Ibadan",
        "location_mode": "area_only",
        "featured": False,
        "vault": True,
    },
    {
        "key": "food-and-flow",
        "title": "Mainland Food & Culture Fest",
        "host_slug": "mainlandvibes",
        "category_slug": "food-drink",
        "lifecycle": "completed",
        "city": "Lagos",
        "location_mode": "full_public",
        "featured": False,
        "vault": True,
    },
    {
        "key": "mainland-vibes-summer",
        "title": "Lagos Creative Market",
        "host_slug": "mainlandvibes",
        "category_slug": "lifestyle",
        "lifecycle": "upcoming",
        "city": "Lagos",
        "location_mode": "area_only",
        "featured": True,
        "vault": True,
    },
]

SHOWCASE_EVENT_KEYS = [e["key"] for e in DEMO_SHOWCASE_EVENTS]
SHOWCASE_COMPLETED_KEYS = [
    e["key"] for e in DEMO_SHOWCASE_EVENTS if e["lifecycle"] == "completed"
]
SHOWCASE_UPCOMING_KEYS = [
    e["key"] for e in DEMO_SHOWCASE_EVENTS if e["lifecycle"] == "upcoming"
]
