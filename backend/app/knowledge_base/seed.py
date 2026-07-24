"""Idempotent Knowledge Base seed — categories + published help articles."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blog.markdown import estimate_reading_minutes
from app.knowledge_base.models import (
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    KnowledgeBaseTag,
)
from app.knowledge_base.seed_content import SAMPLE_ARTICLES
from app.knowledge_base.video import parse_video_url

# (name, slug, description, group_key, sort_order, icon_key)
CATEGORIES: list[tuple[str, str, str, str, int, str]] = [
    # Fan Help
    ("Buying tickets", "buying-tickets", "Purchase tickets on official event pages", "fan", 10, "ticket"),
    ("Guest checkout", "guest-checkout", "Buy without an account using email", "fan", 15, "guest"),
    ("My tickets and QR codes", "my-tickets-and-qr", "Find and show signed QR tickets", "fan", 20, "qr"),
    ("Finding events", "finding-events", "Discover nights on Pàdéyá", "fan", 25, "search"),
    ("Refunds", "refunds", "Refund requests and timelines", "fan", 30, "refund"),
    ("Fan Passport", "fan-passport", "Badges, memories, and fan identity", "fan", 40, "passport"),
    ("Fan Connect", "fan-connect", "Meet the night with privacy controls", "fan", 50, "connect"),
    ("Messages", "messages", "Fan↔host messaging on Pàdéyá", "fan", 60, "message"),
    ("Following hosts", "following-hosts", "Follow hosts you trust", "fan", 70, "follow"),
    ("Reviews", "reviews", "Leave honest reviews after nights", "fan", 80, "review"),
    ("Merch", "merch", "Buying host merch and drops", "fan", 90, "merch"),
    ("Vault", "vault", "Vault content and access", "fan", 100, "vault"),
    # Host Help
    ("Becoming a host", "becoming-a-host", "Start hosting on Pàdéyá", "host", 110, "host"),
    ("Creating events", "creating-events", "Publish and manage event listings", "host", 120, "event"),
    ("Ticket types and pricing", "ticket-types-and-pricing", "Tiers, inventory, and pricing", "host", 130, "tickets"),
    ("Promo codes", "promo-codes", "Discount codes for ticket sales", "host", 140, "promo"),
    ("Ambassador codes", "ambassador-codes", "Tracked ambassador referral codes", "host", 150, "code"),
    ("QR check-in", "qr-check-in", "Door scanning and entry tools", "host", 160, "qr"),
    ("Host team", "host-team", "Invite and permission your team", "host", 170, "team"),
    ("Merch Studio", "merch-studio", "Create and sell merch", "host", 180, "studio"),
    ("Vault Studio", "vault-studio", "Publish Vault content", "host", 190, "vault"),
    ("Legacy Page", "legacy-page", "Your public host legacy", "host", 200, "legacy"),
    ("Audience CRM", "audience-crm", "Followers, segments, announcements", "host", 210, "crm"),
    ("Sponsorships", "sponsorships", "Brand partnerships on Pàdéyá", "host", 220, "sponsor"),
    ("Analytics", "analytics", "Event and audience insights", "host", 230, "chart"),
    ("Host earnings and fees", "host-earnings-and-fees", "Earnings, fees, and payouts", "host", 240, "money"),
    # Sponsor Help
    ("Finding hosts/events", "finding-hosts-events", "Discover hosts and nights to sponsor", "sponsor", 310, "search"),
    ("Sending sponsorship inquiries", "sending-sponsorship-inquiries", "Reach hosts with brand goals", "sponsor", 320, "send"),
    ("Managing sponsorship requests", "managing-sponsorship-requests", "Track inquiry status", "sponsor", 330, "manage"),
    # Ambassador Help
    ("Joining campaigns", "joining-campaigns", "Join host ambassador campaigns", "ambassador", 410, "join"),
    ("Sharing events", "sharing-events", "Share tracked links and codes", "ambassador", 420, "share"),
    ("Tracking clicks/conversions", "tracking-conversions", "See campaign performance", "ambassador", 430, "chart"),
    ("Rewards and payouts", "rewards-and-payouts", "Campaign rewards timing", "ambassador", 440, "reward"),
    # Account & Safety
    ("Login and security", "login-and-security", "Sign-in, passwords, and sessions", "account", 510, "lock"),
    ("Notifications", "notifications", "Email and push preferences", "account", 520, "bell"),
    ("Privacy settings", "privacy-settings", "What you share and with whom", "account", 530, "privacy"),
    ("Reports and blocking", "reports-and-blocking", "Report abuse and block users", "account", 540, "report"),
    ("Suspensions and appeals", "suspensions-and-appeals", "Restrictions and appeals", "account", 550, "appeal"),
    # Payments & Policies
    ("Secure payments", "secure-payments", "Supported payment checkout", "payments", 610, "payment"),
    ("Platform fees", "platform-fees", "Platform and processing fees", "payments", 620, "fees"),
    ("Refund Policy help", "refund-policy-help", "How refunds relate to policy pages", "payments", 630, "refund"),
    ("Ticket Policy help", "ticket-policy-help", "Ticket access and QR rules", "payments", 640, "ticket"),
    ("Terms help", "terms-help", "Platform Terms overview", "payments", 650, "terms"),
    ("Privacy help", "privacy-help", "Privacy Policy overview", "payments", 660, "privacy"),
    # Admin / Support ops
    ("Support tickets", "support-tickets", "How Support Center cases work", "admin", 710, "support"),
    ("User management", "user-management", "Admin user tools and safe actions", "admin", 720, "users"),
    ("Maintenance mode", "maintenance-mode", "Platform maintenance controls", "admin", 730, "wrench"),
    ("Admin teams and roles", "admin-teams-and-roles", "Admin team permissions", "admin", 740, "roles"),
]

TAGS = [
    ("Tickets", "tickets"),
    ("Check-in", "check-in"),
    ("How-to", "how-to"),
    ("Video", "video"),
    ("Safety", "safety"),
    ("Hosts", "hosts"),
    ("Fans", "fans"),
    ("Getting started", "getting-started"),
    ("Merch", "merch"),
    ("Vault", "vault"),
]

# Legacy gateway-named slugs → neutral slugs (idempotent remap on re-seed).
_LEGACY_CATEGORY_SLUGS = {"paystack-payments": "secure-payments"}
_LEGACY_ARTICLE_SLUGS = {"how-paystack-payments-work": "how-payments-work"}


def _remap_legacy_slugs(db: Session) -> None:
    """Rename old Paystack-named help slugs without leaving duplicate rows."""
    for old, new in _LEGACY_CATEGORY_SLUGS.items():
        legacy = db.scalar(
            select(KnowledgeBaseCategory).where(KnowledgeBaseCategory.slug == old)
        )
        if not legacy:
            continue
        existing_new = db.scalar(
            select(KnowledgeBaseCategory).where(KnowledgeBaseCategory.slug == new)
        )
        if existing_new:
            for article in db.scalars(
                select(KnowledgeBaseArticle).where(
                    KnowledgeBaseArticle.category_id == legacy.id
                )
            ).all():
                article.category_id = existing_new.id
            db.delete(legacy)
        else:
            legacy.slug = new

    for old, new in _LEGACY_ARTICLE_SLUGS.items():
        legacy = db.scalar(
            select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.slug == old)
        )
        if not legacy:
            continue
        existing_new = db.scalar(
            select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.slug == new)
        )
        if existing_new:
            db.delete(legacy)
        else:
            legacy.slug = new


def seed_knowledge_base(db: Session) -> dict[str, int]:
    """Idempotent seed of categories, tags, and sample published articles."""
    created = {"categories": 0, "tags": 0, "articles": 0, "updated": 0}

    _remap_legacy_slugs(db)

    cat_by_slug: dict[str, KnowledgeBaseCategory] = {
        c.slug: c for c in db.scalars(select(KnowledgeBaseCategory)).all()
    }
    for name, slug, desc, group_key, sort_order, icon_key in CATEGORIES:
        if slug not in cat_by_slug:
            row = KnowledgeBaseCategory(
                name=name,
                slug=slug,
                description=desc,
                group_key=group_key,
                sort_order=sort_order,
                icon_key=icon_key,
            )
            db.add(row)
            db.flush()
            cat_by_slug[slug] = row
            created["categories"] += 1
        else:
            existing = cat_by_slug[slug]
            existing.name = name
            existing.description = desc
            existing.group_key = group_key
            existing.sort_order = sort_order
            existing.icon_key = icon_key

    tag_by_slug: dict[str, KnowledgeBaseTag] = {
        t.slug: t for t in db.scalars(select(KnowledgeBaseTag)).all()
    }
    for name, slug in TAGS:
        if slug not in tag_by_slug:
            row = KnowledgeBaseTag(name=name, slug=slug)
            db.add(row)
            db.flush()
            tag_by_slug[slug] = row
            created["tags"] += 1

    now = datetime.now(UTC)
    for item in SAMPLE_ARTICLES:
        existing = db.scalar(
            select(KnowledgeBaseArticle).where(
                KnowledgeBaseArticle.slug == item["slug"]
            )
        )
        cat = cat_by_slug.get(item["category"])
        tags = [tag_by_slug[s] for s in item["tags"] if s in tag_by_slug]
        video_url = item.get("video_url")
        video_provider = None
        video_thumbnail = None
        if video_url:
            try:
                parsed = parse_video_url(video_url)
                video_url = parsed.get("video_url")
                video_provider = parsed.get("provider")
                video_thumbnail = parsed.get("thumbnail_url")
            except ValueError:
                video_url = None

        fields = {
            "title": item["title"],
            "excerpt": item["excerpt"],
            "body": item["body"],
            "content_type": item["content_type"],
            "difficulty": item["difficulty"],
            "audiences": list(item["audiences"]),
            "category_id": cat.id if cat else None,
            "is_featured": bool(item.get("featured")),
            "featured_sort": int(item.get("featured_sort") or 0),
            "seo_title": item.get("seo_title"),
            "seo_description": item.get("seo_description"),
            "video_url": video_url,
            "video_provider": video_provider,
            "video_thumbnail_url": video_thumbnail,
            "reading_time_minutes": estimate_reading_minutes(item["body"]),
            "status": "published",
            "published_at": now,
            "archived_at": None,
        }

        if existing is None:
            row = KnowledgeBaseArticle(slug=item["slug"], **fields)
            db.add(row)
            db.flush()
            row.tags = tags
            created["articles"] += 1
        else:
            for key, val in fields.items():
                setattr(existing, key, val)
            existing.tags = tags
            created["updated"] += 1

    db.commit()
    return created
