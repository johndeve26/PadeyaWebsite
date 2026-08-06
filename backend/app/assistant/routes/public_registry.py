"""Public route registry for Ask Pàdéyá navigation."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PublicRouteEntry:
    key: str
    path: str
    title: str
    description: str
    synonyms: tuple[str, ...] = ()
    common_questions: tuple[str, ...] = ()
    route_group: str = "marketing"


PUBLIC_ROUTE_REGISTRY: dict[str, PublicRouteEntry] = {
    "home": PublicRouteEntry(
        key="home",
        path="/",
        title="Home",
        description="Pàdéyá home — discover events and culture.",
        synonyms=("home", "homepage", "main page", "start"),
        common_questions=("What is Pàdéyá?", "Where do I start?"),
        route_group="marketing",
    ),
    "events": PublicRouteEntry(
        key="events",
        path="/events",
        title="Events",
        description="Browse and search public events.",
        synonyms=("events", "find events", "what's on", "shows", "parties"),
        common_questions=("How do I find events?", "Where are tonight's events?"),
        route_group="events",
    ),
    "hosts": PublicRouteEntry(
        key="hosts",
        path="/hosts",
        title="Hosts",
        description="Discover hosts and Legacy Pages.",
        synonyms=("hosts", "host directory", "promoters", "creators"),
        common_questions=("How do I find a host?", "What is a Legacy Page?"),
        route_group="hosts",
    ),
    "fans": PublicRouteEntry(
        key="fans",
        path="/fans",
        title="Fans",
        description="Fan community and Fan Connect overview.",
        synonyms=("fans", "fan page", "community"),
        common_questions=("How does Fan Connect work?",),
        route_group="fans",
    ),
    "memories": PublicRouteEntry(
        key="memories",
        path="/memories",
        title="Memories",
        description="Public event memory albums.",
        synonyms=("memories", "photos", "albums", "recap"),
        common_questions=("Where can I see event photos?",),
        route_group="memories",
    ),
    "ambassadors": PublicRouteEntry(
        key="ambassadors",
        path="/ambassadors",
        title="Ambassadors",
        description="Ambassador program overview.",
        synonyms=("ambassadors", "referral program", "affiliate", "become an ambassador"),
        common_questions=("How do I become an ambassador?",),
        route_group="ambassadors",
    ),
    "sponsors": PublicRouteEntry(
        key="sponsors",
        path="/sponsors",
        title="Sponsors",
        description="Sponsorship opportunities and overview.",
        synonyms=("sponsors", "sponsorship", "brand partners"),
        common_questions=("How do brands sponsor events?",),
        route_group="sponsors",
    ),
    "shop": PublicRouteEntry(
        key="shop",
        path="/shop",
        title="Shop",
        description="Merch and marketplace products.",
        synonyms=("shop", "merch", "store", "merchandise"),
        common_questions=("Where can I buy merch?",),
        route_group="shop",
    ),
    "resources": PublicRouteEntry(
        key="resources",
        path="/resources",
        title="Resources",
        description="Guides and resources hub.",
        synonyms=("resources", "guides", "learning"),
        common_questions=("Where are hosting guides?",),
        route_group="resources",
    ),
    "blog": PublicRouteEntry(
        key="blog",
        path="/blog",
        title="Blog",
        description="Pàdéyá blog articles.",
        synonyms=("blog", "articles", "stories", "news"),
        common_questions=("Where is the blog?",),
        route_group="resources",
    ),
    "help": PublicRouteEntry(
        key="help",
        path="/help",
        title="Help",
        description="Help center articles.",
        synonyms=("help", "help center", "docs", "how to"),
        common_questions=("Where is the help center?",),
        route_group="help",
    ),
    "support": PublicRouteEntry(
        key="support",
        path="/support",
        title="Support",
        description="Contact support / open a ticket.",
        synonyms=("support", "contact support", "support ticket", "help desk"),
        common_questions=("How do I contact support?",),
        route_group="help",
    ),
    "faq": PublicRouteEntry(
        key="faq",
        path="/faq",
        title="FAQ",
        description="Frequently asked questions.",
        synonyms=("faq", "faqs", "common questions"),
        common_questions=("What are the FAQs?",),
        route_group="help",
    ),
    "about": PublicRouteEntry(
        key="about",
        path="/about",
        title="About",
        description="About Pàdéyá.",
        synonyms=("about", "about us", "company"),
        common_questions=("What is Pàdéyá about?",),
        route_group="marketing",
    ),
    "policies": PublicRouteEntry(
        key="policies",
        path="/policies",
        title="Policies",
        description="Platform policies hub.",
        synonyms=("policies", "terms", "privacy", "legal"),
        common_questions=("Where are the terms and privacy policy?",),
        route_group="legal",
    ),
    "contact": PublicRouteEntry(
        key="contact",
        path="/contact",
        title="Contact",
        description="Contact Pàdéyá.",
        synonyms=("contact", "email us", "get in touch"),
        common_questions=("How do I contact Pàdéyá?",),
        route_group="marketing",
    ),
    "report": PublicRouteEntry(
        key="report",
        path="/report",
        title="Report",
        description="Report a safety or policy concern.",
        synonyms=("report", "report abuse", "safety report"),
        common_questions=("How do I report something?",),
        route_group="safety",
    ),
}


def get_public_route_by_key(key: str) -> PublicRouteEntry | None:
    return PUBLIC_ROUTE_REGISTRY.get((key or "").strip().lower())


def get_route_by_key(key: str) -> PublicRouteEntry | None:
    """Lookup public route by key (auth routes use get_auth_route_by_key)."""
    return get_public_route_by_key(key)


def resolve_public_route(query: str) -> PublicRouteEntry | None:
    """Best-effort match of a natural-language query to a public route."""
    q = (query or "").strip().lower()
    if not q:
        return None
    # Exact path
    for entry in PUBLIC_ROUTE_REGISTRY.values():
        if q == entry.path or q.rstrip("/") == entry.path.rstrip("/"):
            return entry
    # Synonym / title token scoring
    best: PublicRouteEntry | None = None
    best_score = 0
    tokens = set(re.findall(r"[a-z0-9']+", q))
    for entry in PUBLIC_ROUTE_REGISTRY.values():
        score = 0
        for syn in entry.synonyms:
            syn_l = syn.lower()
            if syn_l in q:
                score += 3 + len(syn_l.split())
            elif set(syn_l.split()) <= tokens:
                score += 2
        if entry.title.lower() in q:
            score += 2
        for question in entry.common_questions:
            if question.lower() in q:
                score += 4
        if score > best_score:
            best_score = score
            best = entry
    return best if best_score >= 2 else None
