"""Seed AI prompt templates for Host and Admin copilots."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.constants import (
    FEATURE_ADMIN_BLOG_EXCERPT,
    FEATURE_ADMIN_BLOG_OUTLINE,
    FEATURE_ADMIN_BLOG_SEO,
    FEATURE_ADMIN_BLOG_SOCIAL,
    FEATURE_ADMIN_BLOG_TAGS,
    FEATURE_ADMIN_BLOG_TITLE,
    FEATURE_ADMIN_DAILY_OPS,
    FEATURE_ADMIN_REPORTS_SUMMARY,
    FEATURE_ADMIN_REVENUE_SUMMARY,
    FEATURE_ADMIN_SUPPORT_QUEUE,
    FEATURE_HOST_EVENT_DESCRIPTION,
    FEATURE_HOST_EVENT_TITLE,
    FEATURE_HOST_MERCH_CATEGORY,
    FEATURE_HOST_MERCH_DESCRIPTION,
    FEATURE_HOST_MERCH_TAGS,
    FEATURE_HOST_MERCH_TITLE,
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
    FEATURE_HOST_SPONSORSHIP_PITCH,
    FEATURE_FAN_PASSPORT_BIO,
    FEATURE_SUPPORT_ARTICLES,
    FEATURE_SUPPORT_PRIORITY,
    FEATURE_SUPPORT_REPLY_DRAFT,
    FEATURE_SUPPORT_SUMMARY,
    FEATURE_SUPPORT_TRIAGE,
    SYSTEM_ADMIN_SAFE,
    SYSTEM_ADMIN_SUMMARY_SAFE,
    SYSTEM_BLOG_SAFE,
    SYSTEM_HOST_MERCH_SAFE,
    SYSTEM_HOST_ANNOUNCEMENT_SAFE,
    SYSTEM_HOST_SPONSORSHIP_SAFE,
    SYSTEM_FAN_PASSPORT_SAFE,
    SYSTEM_HOST_SAFE,
    SYSTEM_SUPPORT_SAFE,
)
from app.ai.models import AIPromptTemplate

SYSTEM_HOST = SYSTEM_HOST_SAFE
SYSTEM_ADMIN = SYSTEM_ADMIN_SAFE
SYSTEM_ADMIN_SUMMARY = SYSTEM_ADMIN_SUMMARY_SAFE
SYSTEM_BLOG = SYSTEM_BLOG_SAFE
SYSTEM_MERCH = SYSTEM_HOST_MERCH_SAFE
SYSTEM_SUPPORT = SYSTEM_SUPPORT_SAFE

TEMPLATES: list[dict[str, str]] = [
    {
        "slug": FEATURE_HOST_EVENT_TITLE,
        "name": "Generate event title ideas",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Generate exactly 5 event title options as a numbered list (1-5).\n"
            "Each title must be under 80 characters, vivid, and local.\n"
            "Do not claim guaranteed sales or official Pàdéyá policy.\n"
            "Draft only — the host will edit before publishing.\n"
            "Event vibe: {vibe}\nCity: {city}\nArea: {area}\nCategory: {category}\n"
            "Existing title: {title}\nDate: {date}\nVenue (public only): {venue}\n"
            "Notes: {notes}"
        ),
    },
    {
        "slug": FEATURE_HOST_EVENT_DESCRIPTION,
        "name": "Generate event description",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Write one polished event description (120-220 words).\n"
            "Cover what the night is, who it is for, and why to come.\n"
            "Do not invent refund guarantees or official platform policy.\n"
            "Do not claim guaranteed attendance or sales.\n"
            "Draft only — the host will edit before publishing.\n"
            "Title: {title}\nCity: {city}\nArea: {area}\nVenue (public only): {venue}\n"
            "Category: {category}\nDate: {date}\nCapacity: {capacity}\n"
            "Ticket tier names: {ticket_tiers}\nNotes: {notes}\nVibe: {vibe}"
        ),
    },
    {
        "slug": FEATURE_HOST_MERCH_TITLE,
        "name": "Generate merch title ideas",
        "audience": "host",
        "system_prompt": SYSTEM_MERCH,
        "user_template": (
            "Task: Generate exactly 5 merch product title options as a numbered list (1-5).\n"
            "Each title under 80 characters. No fake materials, scarcity, or official claims.\n"
            "Draft only — host will edit before publishing. Do not change price.\n"
            "Existing title: {title}\nProduct type: {product_type}\n"
            "Merch kind: {merch_kind}\nHost: {host_name}\n"
            "Event (public): {event_title}\nEvent category: {event_category}\n"
            "Event city: {event_city}\nEvent date: {event_date}\n"
            "Audience: {audience_label}\nFulfillment: {fulfillment_label}\n"
            "Limited stock marked by host: {limited_stock}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_HOST_MERCH_DESCRIPTION,
        "name": "Generate merch description",
        "audience": "host",
        "system_prompt": SYSTEM_MERCH,
        "user_template": (
            "Task: Write one polished product description (80-180 words).\n"
            "No fake materials, quality guarantees, scarcity (unless limited_stock=yes), "
            "refunds, medical claims, celebrity/brand claims, or official claims.\n"
            "Draft only — do not change price or inventory.\n"
            "Title: {title}\nShort description: {short_description}\n"
            "Product type: {product_type}\nMerch kind: {merch_kind}\n"
            "Host: {host_name}\nEvent (public): {event_title}\n"
            "Event category: {event_category}\nEvent city: {event_city}\n"
            "Event date: {event_date}\nAudience: {audience_label}\n"
            "Fulfillment: {fulfillment_label}\nLimited stock: {limited_stock}\n"
            "Notes: {notes}\nExisting description: {description}"
        ),
    },
    {
        "slug": FEATURE_HOST_MERCH_CATEGORY,
        "name": "Suggest merch category",
        "audience": "host",
        "system_prompt": SYSTEM_MERCH,
        "user_template": (
            "Task: Suggest exactly one browse category from this catalog only:\n"
            "{catalog_categories}\n"
            "Reply with the category slug (preferred) or exact label. Do not invent categories.\n"
            "Title: {title}\nProduct type: {product_type}\nMerch kind: {merch_kind}\n"
            "Existing category: {existing_category}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_HOST_MERCH_TAGS,
        "name": "Suggest merch tags",
        "audience": "host",
        "system_prompt": SYSTEM_MERCH,
        "user_template": (
            "Task: Suggest 3–6 short merchandising tags as a numbered list.\n"
            "Tags should be lowercase words/phrases, no hashtags, no private data, "
            "no fake brand/celebrity claims.\n"
            "Title: {title}\nProduct type: {product_type}\nCategory: {existing_category}\n"
            "Merch kind: {merch_kind}\nEvent category: {event_category}\n"
            "Existing tags: {existing_tags}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_SUPPORT_SUMMARY,
        "name": "Summarize support ticket",
        "audience": "admin",
        "system_prompt": SYSTEM_SUPPORT,
        "user_template": (
            "Task: Write a staff-only ticket summary with these headings:\n"
            "Issue summary:\nUser goal:\nRelated context:\nCurrent status:\nSuggested next action:\n"
            "Do not promise refunds or claim payment confirmation.\n"
            "Subject: {subject}\nCategory: {category}\nPriority: {priority}\nStatus: {status}\n"
            "Requester context: {requester_context}\n"
            "Order ref: {related_order_ref}\nEvent: {related_event_title}\n"
            "Merch: {related_merch_title}\nConversation:\n{conversation}"
        ),
    },
    {
        "slug": FEATURE_SUPPORT_TRIAGE,
        "name": "Suggest support category",
        "audience": "admin",
        "system_prompt": SYSTEM_SUPPORT,
        "user_template": (
            "Task: Suggest exactly one support category slug from this catalog:\n"
            "{catalog_categories}\n"
            "Reply as:\nCategory: <slug>\nReason: <one short sentence>\n"
            "Subject: {subject}\nCurrent category: {category}\n"
            "Requester context: {requester_context}\nConversation:\n{conversation}"
        ),
    },
    {
        "slug": FEATURE_SUPPORT_PRIORITY,
        "name": "Suggest support priority",
        "audience": "admin",
        "system_prompt": SYSTEM_SUPPORT,
        "user_template": (
            "Task: Suggest priority from: {catalog_priorities}\n"
            "Reply as:\nPriority: <low|normal|high|urgent>\n"
            "Reason: <payment issue / event happening soon / safety/abuse / "
            "angry user / refund dispute / host blocked / other>\n"
            "Subject: {subject}\nCategory: {category}\nCurrent priority: {priority}\n"
            "Status: {status}\nConversation:\n{conversation}"
        ),
    },
    {
        "slug": FEATURE_SUPPORT_REPLY_DRAFT,
        "name": "Draft support reply",
        "audience": "admin",
        "system_prompt": SYSTEM_SUPPORT,
        "user_template": (
            "Task: Draft a polite public reply for the requester.\n"
            "Do not promise refunds, payment confirmation, bans, or ticket closure.\n"
            "Do not expose internal notes or secrets. Keep under 180 words.\n"
            "Staff must review and send manually.\n"
            "Subject: {subject}\nCategory: {category}\nPriority: {priority}\n"
            "Status: {status}\nRequester context: {requester_context}\n"
            "Order ref: {related_order_ref}\nEvent: {related_event_title}\n"
            "Conversation:\n{conversation}"
        ),
    },
    {
        "slug": FEATURE_SUPPORT_ARTICLES,
        "name": "Suggest help articles",
        "audience": "admin",
        "system_prompt": SYSTEM_SUPPORT,
        "user_template": (
            "Task: Pick up to 5 help articles from this catalog only "
            "(format slug|title|id). If none fit, reply: no strong match.\n"
            "Catalog:\n{article_catalog}\n"
            "Subject: {subject}\nCategory: {category}\nConversation:\n{conversation}"
        ),
    },
    {
        "slug": "generate_event_title",
        "name": "Generate event title",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Generate 5 event title options as a numbered list.\n"
            "Draft only — review before publishing.\n"
            "Event vibe: {vibe}\nCity: {city}\nCategory: {category}\n"
            "Existing title: {title}\nNotes: {notes}"
        ),
    },
    {
        "slug": "generate_event_description",
        "name": "Generate event description",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Write an event description (120-180 words).\n"
            "Draft only — review before publishing. No refund guarantees.\n"
            "Title: {title}\nCity: {city}\nVenue: {venue}\n"
            "Category: {category}\nNotes: {notes}"
        ),
    },
    {
        "slug": "generate_ticket_tier_copy",
        "name": "Generate ticket tier copy",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Write short copy for ticket tiers (Regular / VIP / Table).\n"
            "Draft only — review before publishing.\n"
            "Event: {title}\nCity: {city}\nNotes: {notes}"
        ),
    },
    {
        "slug": "generate_instagram_captions",
        "name": "Generate Instagram captions",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Write 3 Instagram captions with CTAs to buy tickets on Pàdéyá.\n"
            "Draft only — do not claim guaranteed sales.\n"
            "Event: {title}\nCity: {city}\nDate: {date}\nNotes: {notes}"
        ),
    },
    {
        "slug": "generate_whatsapp_broadcast",
        "name": "Generate WhatsApp broadcast",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Draft a WhatsApp broadcast (under 500 characters).\n"
            "Event: {title}\nCity: {city}\nDate: {date}\nNotes: {notes}\n"
            "Do not send automatically — draft only."
        ),
    },
    {
        "slug": "generate_email_announcement",
        "name": "Generate email announcement",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Draft an email announcement (subject + body).\n"
            "Event: {title}\nCity: {city}\nDate: {date}\nNotes: {notes}\n"
            "Do not send automatically — draft only."
        ),
    },
    {
        "slug": FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
        "name": "Draft host announcement",
        "audience": "host",
        "system_prompt": SYSTEM_HOST_ANNOUNCEMENT_SAFE,
        "user_template": (
            "Task: Draft a host CRM announcement (draft only — not sent).\n"
            "Format exactly:\n"
            "SUBJECT: <internal/recipient-facing subject line>\n"
            "EMAIL_BODY:\n<email body, plain text, warm and clear>\n"
            "WHATSAPP:\n<optional short WhatsApp copy under 500 chars, or leave blank>\n"
            "Host: {host_name}\n"
            "Event title: {event_title}\n"
            "Event date: {event_date}\n"
            "City: {event_city}\n"
            "Area: {event_area}\n"
            "Category: {event_category}\n"
            "Announcement channel: {channel}\n"
            "Audience segment (label only): {audience_label}\n"
            "Merch title (label only): {merch_title}\n"
            "Vault label (no locked content): {vault_label}\n"
            "Host notes: {host_notes}\n"
            "Never imply the message was already sent. Never include recipient contact details."
        ),
    },
    {
        "slug": FEATURE_HOST_SPONSORSHIP_PITCH,
        "name": "Draft sponsorship pitch",
        "audience": "host",
        "system_prompt": SYSTEM_HOST_SPONSORSHIP_SAFE,
        "user_template": (
            "Task: Draft a sponsorship pitch for the host marketplace (draft only).\n"
            "Format exactly:\n"
            "PITCH_TITLE: <short headline>\n"
            "SHORT_PITCH:\n<2-4 sentences for the host card>\n"
            "VALUE_BULLETS:\n- bullet one\n- bullet two\n"
            "AUDIENCE_SUMMARY:\n<aggregate audience + event context, no invented numbers>\n"
            "PACKAGE_WORDING:\n<suggested slot/package copy for brands>\n"
            "FOLLOW_UP:\n<optional short follow-up message draft, or leave blank>\n"
            "Host: {host_name}\n"
            "Category: {host_category}\n"
            "City: {host_city}\n"
            "Legacy tier (public): {legacy_tier}\n"
            "Followers (aggregate): {follower_count}\n"
            "Verified check-ins (aggregate): {verified_checkins}\n"
            "Average rating (aggregate): {average_rating}\n"
            "Review count: {review_count}\n"
            "Events hosted: {events_hosted}\n"
            "Public events (JSON): {public_events_summary}\n"
            "Aggregate stats (JSON): {aggregate_stats}\n"
            "Slot type: {slot_type_label}\n"
            "Host notes: {host_notes}\n"
            "Never claim Pàdéyá endorses the host. Never guarantee ROI or sponsorship."
        ),
    },
    {
        "slug": FEATURE_FAN_PASSPORT_BIO,
        "name": "Improve Fan Passport bio",
        "audience": "fan",
        "system_prompt": SYSTEM_FAN_PASSPORT_SAFE,
        "user_template": (
            "Task: Draft 2–3 short Fan Passport bio options (draft only — user saves manually).\n"
            "Format as a numbered list (1. … 2. … 3. …). Each option 2–4 sentences, "
            "max 2000 characters, friendly event-community tone.\n"
            "Display name: {display_name}\n"
            "Username: {username}\n"
            "Existing bio: {existing_bio}\n"
            "Public interests: {public_interests}\n"
            "Visible badges (labels only): {visible_badges}\n"
            "Public city: {public_city}\n"
            "Public area: {public_area}\n"
            "User notes: {user_notes}\n"
            "Do not invent attendance counts, spend, VIP status, or private details."
        ),
    },
    {
        "slug": "suggest_ticket_pricing",
        "name": "Suggest ticket pricing",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Suggest ticket pricing ranges (NGN) with rationale.\n"
            "This is advisory only — not financial advice; host must confirm.\n"
            "Event: {title}\nCity: {city}\nCategory: {category}\n"
            "Capacity: {capacity}\nCurrent tiers: {ticket_tiers}\nNotes: {notes}"
        ),
    },
    {
        "slug": "suggest_promo_strategy",
        "name": "Suggest promo strategy",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Suggest a promo / early-bird / ambassador strategy.\n"
            "Draft only — do not create promos automatically.\n"
            "Event: {title}\nCity: {city}\nMetrics: {metrics}\nNotes: {notes}"
        ),
    },
    {
        "slug": "summarize_event_performance",
        "name": "Summarize event performance",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Summarize event performance and 3 next actions.\n"
            "Use aggregates only. Draft insights — host confirms actions.\n"
            "Event: {title}\nMetrics: {metrics}\nNotes: {notes}"
        ),
    },
    {
        "slug": "suggest_legacy_tier_path",
        "name": "Suggest Legacy tier path",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Suggest how to reach the next Legacy tier.\n"
            "Current tier: {current_tier}\nNext tier: {next_tier}\n"
            "Progress: {progress}\nRemaining: {requirements_remaining}\n"
            "Suggested actions already: {suggested_actions}"
        ),
    },
    {
        "slug": "generate_event_recap_draft",
        "name": "Generate event recap draft",
        "audience": "host",
        "system_prompt": SYSTEM_HOST,
        "user_template": (
            "Task: Draft a host thank-you / event memory recap note.\n"
            "Event: {title}\nCity: {city}\nDate: {date}\n"
            "Metrics: {metrics}\nNotes: {notes}\n"
            "Do not publish automatically — draft only."
        ),
    },
    {
        "slug": FEATURE_ADMIN_SUPPORT_QUEUE,
        "name": "Summarize support queue",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN_SUMMARY,
        "user_template": (
            "Task: Write an advisory support queue summary with headings:\n"
            "Open tickets:\nUrgent / high priority:\nMain issue themes:\n"
            "Needs fastest attention:\nSuggested staff focus:\n"
            "Use only this snapshot. Do not invent counts. Do not close tickets "
            "or approve refunds.\n"
            "Range: {range_label}\nSupport snapshot: {support_snapshot}\n"
            "Review links: {suggested_review_links}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_REVENUE_SUMMARY,
        "name": "Explain revenue period",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN_SUMMARY,
        "user_template": (
            "Task: Explain this analytics period using aggregates only.\n"
            "Include: revenue trend, ticket sales, merch sales, refund/failed "
            "payment notes, top events/hosts/categories, and 3 suggested reviews.\n"
            "Do not invent totals. Do not approve refunds or payouts.\n"
            "Range: {range_label}\nRevenue snapshot: {revenue_snapshot}\n"
            "Top events: {top_events}\nTop hosts: {top_hosts}\n"
            "Categories: {category_trends}\n"
            "Review links: {suggested_review_links}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_REPORTS_SUMMARY,
        "name": "Summarize reports",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN_SUMMARY,
        "user_template": (
            "Task: Summarize moderation/report queues for human review.\n"
            "Include: report themes, high-risk items, repeated targets by safe "
            "display labels, and a suggested review order.\n"
            "Do not hide, approve, reject, suspend, or warn anyone.\n"
            "Reports snapshot: {reports_snapshot}\n"
            "Review links: {suggested_review_links}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_DAILY_OPS,
        "name": "Daily operations summary",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN_SUMMARY,
        "user_template": (
            "Task: Write an on-demand daily operations summary with:\n"
            "New users/hosts/events, ticket sales, merch signal if present, "
            "support load, safety/report load, payment issues, and action items "
            "as a checklist (suggestions only).\n"
            "Do not execute actions. Do not invent totals.\n"
            "Range: {range_label}\nOperations: {operations_snapshot}\n"
            "Support: {support_snapshot}\nReports: {reports_snapshot}\n"
            "Review links: {suggested_review_links}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_BLOG_TITLE,
        "name": "Generate blog title ideas",
        "audience": "admin",
        "system_prompt": SYSTEM_BLOG,
        "user_template": (
            "Task: Generate 3–5 blog title options as a numbered list.\n"
            "Draft only — never publish. No fake policy/legal claims.\n"
            "Title: {title}\nCategory: {category}\nAudience: {audience}\n"
            "Goal: {goal}\nExcerpt: {excerpt}\nBody draft:\n{body}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_BLOG_OUTLINE,
        "name": "Generate blog outline",
        "audience": "admin",
        "system_prompt": SYSTEM_BLOG,
        "user_template": (
            "Task: Write a structured markdown outline with ## headings and "
            "bullet points under each section.\n"
            "Do not publish. Do not invent legal policy text.\n"
            "Title: {title}\nCategory: {category}\nAudience: {audience}\n"
            "Goal: {goal}\nExcerpt: {excerpt}\nBody draft:\n{body}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_BLOG_EXCERPT,
        "name": "Generate blog excerpt",
        "audience": "admin",
        "system_prompt": SYSTEM_BLOG,
        "user_template": (
            "Task: Write one short blog excerpt (1–3 sentences, under 280 chars).\n"
            "Draft only. No guarantees of refunds, sales, or safety.\n"
            "Title: {title}\nCategory: {category}\nBody draft:\n{body}\nNotes: {notes}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_BLOG_SEO,
        "name": "Generate SEO meta",
        "audience": "admin",
        "system_prompt": SYSTEM_BLOG,
        "user_template": (
            "Task: Suggest SEO fields. Reply exactly as:\n"
            "SEO title: <under 60 chars>\n"
            "Meta description: <under 155 chars>\n"
            "Slug: <lowercase-hyphenated>\n"
            "OG description: <short social description>\n"
            "Do not overwrite claims; draft only.\n"
            "Title: {title}\nExisting slug: {existing_slug}\n"
            "Existing SEO title: {existing_seo_title}\n"
            "Existing SEO description: {existing_seo_description}\n"
            "Excerpt: {excerpt}\nCategory: {category}\nBody draft:\n{body}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_BLOG_TAGS,
        "name": "Suggest blog tags",
        "audience": "admin",
        "system_prompt": SYSTEM_BLOG,
        "user_template": (
            "Task: Suggest up to 6 tags from this catalog only "
            "(slug (name)). Numbered list. Do not invent new categories.\n"
            "Catalog: {catalog_tags}\n"
            "Title: {title}\nCategory: {category}\nExisting tags: {existing_tags}\n"
            "Body draft:\n{body}"
        ),
    },
    {
        "slug": FEATURE_ADMIN_BLOG_SOCIAL,
        "name": "Generate social snippets",
        "audience": "admin",
        "system_prompt": SYSTEM_BLOG,
        "user_template": (
            "Task: Draft social snippets. Reply as:\n"
            "Twitter: ...\nInstagram: ...\nLinkedIn: ...\nWhatsApp: ...\n"
            "Copy-only drafts — never send. No policy inventions.\n"
            "Title: {title}\nExcerpt: {excerpt}\nCategory: {category}\n"
            "Audience: {audience}\nGoal: {goal}\nBody draft:\n{body}"
        ),
    },
    {
        "slug": "summarize_support_complaints",
        "name": "Summarize support complaints",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN,
        "user_template": (
            "Task: Summarize open/under-review refund complaints themes.\n"
            "Support snapshot: {support_snapshot}\nNotes: {notes}\n"
            "Do not approve refunds."
        ),
    },
    {
        "slug": "summarize_review_reports",
        "name": "Summarize review reports",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN,
        "user_template": (
            "Task: Summarize open review reports for moderation triage.\n"
            "Reports: {reports_snapshot}\nNotes: {notes}\n"
            "Do not hide or delete reviews."
        ),
    },
    {
        "slug": "explain_revenue_trends",
        "name": "Explain revenue trends",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN,
        "user_template": (
            "Task: Explain revenue trends in plain language.\n"
            "Revenue snapshot: {revenue_snapshot}\nNotes: {notes}\n"
            "Do not modify financial records."
        ),
    },
    {
        "slug": "recommend_featured_events",
        "name": "Recommend featured events",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN,
        "user_template": (
            "Task: Recommend events to feature (human must confirm).\n"
            "Top events: {top_events}\nNotes: {notes}"
        ),
    },
    {
        "slug": "identify_high_risk_hosts",
        "name": "Identify high-risk hosts",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN,
        "user_template": (
            "Task: Placeholder high-risk host scan.\n"
            "Signals: {risk_signals}\nNotes: {notes}\n"
            "This is a placeholder — do not suspend hosts automatically."
        ),
    },
    {
        "slug": "fraud_risk_summary",
        "name": "Fraud risk summary",
        "audience": "admin",
        "system_prompt": SYSTEM_ADMIN,
        "user_template": (
            "Task: Placeholder fraud risk summary.\n"
            "Fraud signals: {fraud_signals}\nNotes: {notes}\n"
            "Placeholder only — no automated enforcement."
        ),
    },
]


def seed_ai_prompt_templates(db: Session) -> None:
    existing_slugs = set(db.scalars(select(AIPromptTemplate.slug)).all())
    for item in TEMPLATES:
        if item["slug"] in existing_slugs:
            continue
        db.add(
            AIPromptTemplate(
                slug=item["slug"],
                name=item["name"],
                audience=item["audience"],
                system_prompt=item["system_prompt"],
                user_template=item["user_template"],
                description=item.get("description"),
                is_active=True,
            )
        )
    db.commit()
