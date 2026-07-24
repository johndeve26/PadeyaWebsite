"""Demo blog seed content for Pàdéyá — six SEO-optimised guides."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.blog.markdown import estimate_reading_minutes
from app.blog.models import (
    BlogAuthor,
    BlogCategory,
    BlogComment,
    BlogPost,
    BlogPostTag,
    BlogTag,
)


CATEGORIES = [
    ("Event planning", "event-planning", "Tips for planning memorable nights"),
    ("Discovery", "discovery", "Finding the right events on Pàdéyá"),
    ("Host growth", "host-growth", "Growing your host brand"),
    ("Safety", "safety", "Ticketing safety and trust"),
    ("Fans", "fans", "Fan Passport, Connect, and the night out"),
    ("Product", "product", "Pàdéyá platform guides"),
]

TAGS = [
    ("Nightlife", "nightlife"),
    ("Ticketing", "ticketing"),
    ("Check-in", "check-in"),
    ("Fan Passport", "fan-passport"),
    ("Fan Connect", "fan-connect"),
    ("Sponsorships", "sponsorships"),
    ("Ambassadors", "ambassadors"),
    ("Hosts", "hosts"),
    ("Legacy", "legacy"),
    ("Merch", "merch"),
    ("Vault", "vault"),
    ("Reviews", "reviews"),
]

# Six curated, conversion-focused guides. Seed upserts by slug.
POSTS = [
    {
        "title": "How to discover the right night on Pàdéyá",
        "slug": "discover-events-on-padeya",
        "category": "discovery",
        "tags": ["nightlife"],
        "featured": True,
        "cover_url": "/brand/padeya-hero.jpg",
        "seo_title": "Discover events on Pàdéyá | Nightlife & tickets",
        "seo_description": (
            "Browse cities, vibes, and price tiers on Pàdéyá. Find verified nights, "
            "follow hosts you trust, and buy tickets in one place."
        ),
        "excerpt": (
            "Filter by city and vibe, spot trusted hosts, and move from browse to "
            "ticket without leaving Pàdéyá."
        ),
        "body": """## Nights worth showing up for

Pàdéyá is built as an **event marketplace**, not a random flyer wall. Discovery should feel premium: clear vibes, honest pricing, and hosts you can follow after the night.

When you open [Events](/events), you are not just scrolling posters. You are choosing a room, a price, and a host brand you will remember next weekend.

### Browse with intent

1. Start on **Events** — filter by city, weekend, and price
2. Open [Hosts](/hosts) when you already know who you trust
3. Use Pàdéyá Picks and featured nights when you want editor-backed options
4. Save or follow hosts so the next drop is easier to catch

### What to check before you pay

- Clear venue and start time on the event page
- Transparent ticket tiers (early bird, general, VIP)
- A host **Legacy Page** with past nights and reviews
- Refund and ticket policy links before checkout

> Tip: Follow hosts you like so their next drop shows up when you are ready to go out.

### After you buy

Tickets live in **My Tickets** with a signed QR for door check-in. Keep the purchase on Pàdéyá — off-platform “deals” are how fake tickets happen.

If something goes wrong with an order, use the [Support Center](/support). Fans, hosts, and visitors can open cases with a clean history.

### Make discovery a habit

The best nights are rarely last-minute panic buys. Check city filters mid-week, follow two or three hosts whose rooms you trust, and treat your Fan Passport as the memory of where you have been — not just a profile.

::cta{label="Explore events"; href="/events"}
""",
    },
    {
        "title": "Verified tickets and QR check-in on Pàdéyá",
        "slug": "verified-tickets-and-qr-check-in",
        "category": "safety",
        "tags": ["ticketing", "check-in"],
        "featured": False,
        "cover_url": "/brand/padeya-hero.jpg",
        "seo_title": "Verified QR tickets & check-in | Pàdéyá safety",
        "seo_description": (
            "How Pàdéyá issues tickets after verified payment, signs QR payloads, "
            "and helps hosts run fast, trusted door check-in."
        ),
        "excerpt": (
            "Tickets only after verified payment. Signed QR at the door. "
            "A safer night for fans and hosts."
        ),
        "body": """## Why on-platform tickets matter

Pàdéyá issues tickets **only after a verified payment**. That means your QR is tied to a real order — not a forwarded screenshot from a group chat.

Hosts get a cleaner door. Fans get fewer “this code already used” surprises. The platform keeps an audit trail when Support needs to help.

### For fans

1. Buy on the official event page — never via random bank transfer “slots”
2. Open **My Tickets** on the night; keep the QR ready (works well as a PWA on mobile)
3. Do not share payment references or ticket QR codes in public chats
4. If a listing feels off, use [Report](/report) or Support before you pay

### For hosts

- Use Tickets & Entry / desk tools for QR validation
- Train door staff to scan — not to accept photo-only “proof”
- Keep refund and ticket policies published before sale
- Prefer on-platform refunds and messaging so disputes stay documented

### Trust stack

- **Verified payment** — no ticket without settlement
- **Signed QR** — fake images fail validation
- **Support Center** — fans and hosts escalate with case history
- **Abuse reporting** — report scams and unsafe listings
- **Privacy controls** — share only what the door needs

Stay on Pàdéyá. Stay check-in ready. Read more on [Safety](/safety) when you want the full trust story.

::cta{label="Read Safety"; href="/safety"}
""",
    },
    {
        "title": "Fan Passport and Fan Connect, explained",
        "slug": "fan-passport-and-fan-connect",
        "category": "fans",
        "tags": ["fan-passport", "fan-connect"],
        "featured": False,
        "cover_url": "/brand/padeya-hero.jpg",
        "seo_title": "Fan Passport & Fan Connect | Pàdéyá for fans",
        "seo_description": (
            "Build your Fan Passport, earn badges and memories, and use Fan Connect "
            "to meet the night — with privacy controls you own."
        ),
        "excerpt": (
            "Your night identity on Pàdéyá — Passport for presence, Connect for "
            "people, privacy when you want it."
        ),
        "body": """## Show up as more than a ticket

**Fan Passport** is your public-facing night identity on Pàdéyá: badges, memories, and the story of where you have been — on your terms.

**Fan Connect** is how fans meet other fans around events, without turning the platform into an unmoderated free-for-all.

Together they answer a simple question: who are you in this nightlife, and who do you want to meet next?

### Fan Passport

- Collect memories from nights you attended
- Earn badges as you show up
- Link out from your fan profile when you choose to be discoverable
- Keep details private when you want; open them when you are ready

Passport is not a vanity score. It is a portable sense of belonging across hosts and cities.

### Fan Connect

- Connect around shared nights and hosts you follow
- Keep messaging within fan↔host and Connect rules
- Report abuse from Support when something feels off
- Treat pins and stars carefully — shared pins are not private notes

### Merch, Vault, and the afterglow

After the night, hosts can drop **merch** and **Vault** content. Your Passport and follow graph help you catch those drops early — and your reviews help the next fan decide.

Explore more on the [Fans](/fans) page, then open your Passport from Personal when you are signed in.

::cta{label="Explore for fans"; href="/fans"}
""",
    },
    {
        "title": "Host playbook: sell tickets, check in guests, build Legacy",
        "slug": "host-playbook-tickets-check-in-legacy",
        "category": "host-growth",
        "tags": ["hosts", "legacy", "ticketing"],
        "featured": False,
        "cover_url": "/brand/padeya-hero.jpg",
        "seo_title": "Host playbook on Pàdéyá | Tickets, check-in, Legacy",
        "seo_description": (
            "Create events, sell verified tickets, run QR check-in, manage audience CRM, "
            "and grow a Host Legacy Page on Pàdéyá."
        ),
        "excerpt": (
            "From first publish to door scan to Legacy Page — the host loop that "
            "turns one night into a brand."
        ),
        "body": """## One workspace for the night

Hosts on Pàdéyá run events from a dedicated workspace: publish, sell, check in, message, and grow — without duct-taping five tools together.

If you are starting from zero, begin with [Become a host](/host/onboarding). If you already host, treat every publish as a chapter on your Legacy Page.

### Launch

1. Create the event with a sharp title, city, and cover
2. Set early-bird and VIP tiers with clear inventory
3. Publish refund and ticket policies before checkout goes live
4. Share one clear promise — vibe, lineup, or experience — not five conflicting claims

### Sell and operate

- Share the public event link and your **Legacy Page**
- Use audience CRM to understand who keeps showing up
- Run **QR check-in** at the door so entry stays fast and verified
- Keep staff on the desk tools; do not invent parallel guest lists in chats

### Grow after the night

- Ask for **verified reviews** while the memory is fresh
- Publish a recap on your Legacy Page
- Tease the next date — consistency beats one viral flyer
- Layer merch, Vault, ambassadors, or sponsorships when the brand can carry them

Your **Legacy Page** is the long home for past nights, merch, and Vault. Treat it like a storefront, not an afterthought. Browse inspiration on [Hosts](/hosts).

::cta{label="Become a host"; href="/host/onboarding"}
""",
    },
    {
        "title": "Merch and Vault: keep the night going after checkout",
        "slug": "merch-and-vault-after-the-night",
        "category": "product",
        "tags": ["merch", "vault", "hosts"],
        "featured": False,
        "cover_url": "/brand/padeya-hero.jpg",
        "seo_title": "Merch & Vault drops on Pàdéyá | Post-event revenue",
        "seo_description": (
            "Launch merch and Vault content after your event. Keep fans close, "
            "extend revenue, and make Legacy Pages feel alive."
        ),
        "excerpt": (
            "Tickets start the relationship. Merch and Vault keep fans in your "
            "world between nights."
        ),
        "body": """## The night should not end at the door

Great hosts sell the memory as carefully as the ticket. On Pàdéyá, **merch** and **Vault** sit beside your Legacy Page so fans know where to return.

Ticket buyers already trust you enough to show up. That is the warmest audience you will ever have for a drop.

### Merch that matches the vibe

- Drop limited items tied to a specific night or season
- Prefer pickup flows your team can run — clear instructions beat surprise shipping chaos
- Feature merch on your Legacy Page and event follow-ups
- Keep creative on-brand; a weak tee can dilute a strong room

### Vault for exclusive content

Vault is for gated drops: recaps, sets, photo packs, or member-only cuts. Use it when the content is worth protecting — not as a junk drawer.

Announce what fans get. Deliver it. Archive or rotate when the moment has passed.

### Timing that converts

1. Soft-announce during the event week
2. Launch within 48 hours while energy is high
3. Reminder to attendees via host messaging (consent-aware)
4. Point everything back to Legacy so first-time fans can browse the story

Fans who already trust your tickets are waiting for the next reason to stay. Give them one.

::cta{label="Browse hosts"; href="/hosts"}
""",
    },
    {
        "title": "Sponsorships and ambassadors that grow real ticket sales",
        "slug": "sponsorships-and-ambassadors-that-convert",
        "category": "host-growth",
        "tags": ["sponsorships", "ambassadors", "hosts"],
        "featured": False,
        "cover_url": "/brand/padeya-hero.jpg",
        "seo_title": "Sponsorships & ambassadors on Pàdéyá | Host growth",
        "seo_description": (
            "Use the Pàdéyá sponsorship marketplace and ambassador campaigns to "
            "fund nights and drive tracked ticket sales — without off-platform chaos."
        ),
        "excerpt": (
            "Brands discover hosts. Creators get tracked links. Hosts keep growth "
            "on-platform and payouts accountable."
        ),
        "body": """## Growth without breaking the vibe

Two levers matter when you want a bigger room: **sponsorships** that fit the night, and **ambassadors** who actually sell tickets.

Pàdéyá keeps both on-platform so inquiries, conversions, and payouts leave a trail you can trust.

### Sponsorship marketplace

Brands browse hosts and events on [Sponsors](/sponsors). Hosts receive inquiries that stay professional — fit over spray-and-pray logos.

- List opportunities that match your audience
- Keep deliverables clear (placement, shoutouts, on-site)
- Never trade fan trust for a messy activation
- Prefer partners who understand nightlife tone, not just logo size

### Ambassador campaigns

Ambassadors share tracked links. You reward **real conversions**, not vanity clicks.

1. Launch a campaign from host tools
2. Share creative that matches your event promise
3. Approve and pay rewards with an audit trail
4. Pause or close campaigns that attract spammy traffic

### Keep money and trust on Pàdéyá

Do not move sponsorship payouts or ambassador “deals” into unverified DMs. Platform records protect hosts, creators, and brands when something goes wrong — and Support can help with a clean case history.

Pair growth tools with a strong Legacy Page and verified tickets. Growth is louder when the product already feels premium.

::cta{label="Explore sponsorships"; href="/sponsors"}
""",
    },
]


# Demo discussion threads — keyed by post slug. Guest names only (no emails).
DEMO_COMMENTS: dict[str, list[dict[str, str]]] = {
    "discover-events-on-padeya": [
        {
            "guest_name": "Tolu A.",
            "body": (
                "This is exactly how I use Pàdéyá now — filter by city, check the host "
                "Legacy, then buy. Way less flyer spam."
            ),
        },
        {
            "guest_name": "Chioma",
            "body": (
                "Following hosts I trust changed everything. Their next drop shows up "
                "and I stop guessing which WhatsApp flyer is real."
            ),
        },
        {
            "guest_name": "Kelechi O.",
            "body": (
                "The tip about checking ticket tiers before checkout saved me. Early "
                "bird on a Friday night in Lekki was still available."
            ),
        },
        {
            "guest_name": "Amaka",
            "body": (
                "QR check-in is smooth. Had my ticket in My Tickets and was through "
                "the door in under a minute."
            ),
        },
        {
            "guest_name": "David N.",
            "body": (
                "Pàdéyá Picks actually recommended a night I loved. More of that "
                "editor curation, please."
            ),
        },
    ],
}


def seed_blog_content(db: Session) -> dict[str, int]:
    """Idempotent seed of categories, tags, author, and demo posts (upsert by slug)."""
    import app.users.models  # noqa: F401 — BlogAuthor FK → users.id

    created = {
        "categories": 0,
        "tags": 0,
        "authors": 0,
        "posts": 0,
        "updated": 0,
        "comments": 0,
    }

    cat_by_slug: dict[str, BlogCategory] = {
        c.slug: c for c in db.scalars(select(BlogCategory)).all()
    }
    for name, slug, desc in CATEGORIES:
        if slug not in cat_by_slug:
            row = BlogCategory(
                name=name, slug=slug, description=desc, sort_order=created["categories"]
            )
            db.add(row)
            db.flush()
            cat_by_slug[slug] = row
            created["categories"] += 1

    tag_by_slug: dict[str, BlogTag] = {
        t.slug: t for t in db.scalars(select(BlogTag)).all()
    }
    for name, slug in TAGS:
        if slug not in tag_by_slug:
            row = BlogTag(name=name, slug=slug)
            db.add(row)
            db.flush()
            tag_by_slug[slug] = row
            created["tags"] += 1

    author = db.scalar(select(BlogAuthor).where(BlogAuthor.slug == "padeya-editorial"))
    if author is None:
        author = BlogAuthor(
            display_name="Pàdéyá Editorial",
            slug="padeya-editorial",
            bio="Guides for fans, hosts, and partners on the Pàdéyá event marketplace.",
            role_title="Editorial",
        )
        db.add(author)
        db.flush()
        created["authors"] += 1
    else:
        author.bio = (
            "Guides for fans, hosts, and partners on the Pàdéyá event marketplace."
        )

    now = datetime.now(UTC)
    for i, spec in enumerate(POSTS):
        cat = cat_by_slug.get(spec["category"])
        reading = estimate_reading_minutes(spec["body"])
        seo_title = spec.get("seo_title") or spec["title"]
        seo_description = (spec.get("seo_description") or spec["excerpt"])[:300]
        cover = spec.get("cover_url")
        featured = bool(spec.get("featured", i == 0))
        published_at = now - timedelta(days=len(POSTS) - i)

        existing = db.scalar(select(BlogPost).where(BlogPost.slug == spec["slug"]))
        if existing is not None:
            existing.title = spec["title"]
            existing.excerpt = spec["excerpt"]
            existing.body = spec["body"]
            existing.status = "published"
            existing.is_featured = featured
            existing.reading_time_minutes = reading
            existing.category_id = cat.id if cat else None
            existing.author_id = author.id
            existing.seo_title = seo_title
            existing.seo_description = seo_description
            existing.cover_url = cover
            existing.og_image_url = cover
            if existing.published_at is None:
                existing.published_at = published_at
            db.flush()
            db.execute(delete(BlogPostTag).where(BlogPostTag.post_id == existing.id))
            for tslug in spec.get("tags", []):
                tag = tag_by_slug.get(tslug)
                if tag:
                    db.add(BlogPostTag(post_id=existing.id, tag_id=tag.id))
            created["updated"] += 1
            continue

        post = BlogPost(
            title=spec["title"],
            slug=spec["slug"],
            excerpt=spec["excerpt"],
            body=spec["body"],
            cover_url=cover,
            og_image_url=cover,
            status="published",
            is_featured=featured,
            reading_time_minutes=reading,
            category_id=cat.id if cat else None,
            author_id=author.id,
            seo_title=seo_title,
            seo_description=seo_description,
            published_at=published_at,
        )
        db.add(post)
        db.flush()
        for tslug in spec.get("tags", []):
            tag = tag_by_slug.get(tslug)
            if tag:
                db.add(BlogPostTag(post_id=post.id, tag_id=tag.id))
        created["posts"] += 1

    created["comments"] = _seed_demo_comments(db)
    db.commit()
    return created


def _seed_demo_comments(db: Session) -> int:
    """Idempotent guest comments for curated demo posts (match by body on post)."""
    added = 0
    now = datetime.now(UTC)
    for slug, specs in DEMO_COMMENTS.items():
        post = db.scalar(select(BlogPost).where(BlogPost.slug == slug))
        if post is None:
            continue
        existing_bodies = {
            (c.body or "").strip()
            for c in db.scalars(
                select(BlogComment).where(BlogComment.post_id == post.id)
            ).all()
        }
        for i, spec in enumerate(specs):
            body = (spec.get("body") or "").strip()
            name = (spec.get("guest_name") or "Guest").strip()
            if not body or body in existing_bodies:
                continue
            # Stagger timestamps so the thread reads oldest → newest
            created_at = now - timedelta(hours=len(specs) - i, minutes=12 * i)
            row = BlogComment(
                post_id=post.id,
                user_id=None,
                guest_name=name[:120],
                guest_email=None,
                body=body,
                status="published",
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(row)
            existing_bodies.add(body)
            added += 1
    return added
