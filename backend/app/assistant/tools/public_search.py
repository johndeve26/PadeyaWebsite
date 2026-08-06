"""Public search tools — events, hosts, pages, resources, products, memories."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.privacy import redact_dict
from app.assistant.routes.public_registry import PUBLIC_ROUTE_REGISTRY, resolve_public_route
from app.events.service import get_event_by_slug, list_published_events


from app.assistant.privacy import redact_dict
from app.assistant.routes.public_registry import PUBLIC_ROUTE_REGISTRY, resolve_public_route
from app.events.service import get_event_by_slug, list_published_events
from app.users.models import User

_EVENT_STOPWORDS = frozenset(
    {
        "event",
        "events",
        "coming",
        "up",
        "upcoming",
        "soon",
        "any",
        "show",
        "me",
        "find",
        "list",
        "please",
        "recommend",
        "recommendation",
        "recommendations",
        "suggest",
        "suggestion",
        "for",
        "or",
        "the",
        "a",
        "an",
        "on",
        "to",
        "do",
        "what",
        "whats",
        "happening",
        "something",
        "anything",
        "things",
        "fun",
        "near",
        "some",
        "good",
        "best",
        "padeya",
        "attend",
        "attending",
        "about",
        "how",
        "week",
        "next",
        "this",
        "eveng",  # common typo for event
    }
)

_CITY_HINTS = (
    "lagos",
    "ibadan",
    "abuja",
    "port harcourt",
    "benin",
    "enugu",
    "jos",
    "kaduna",
    "kano",
    "accra",
    "london",
)


def _query_tokens(q: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", (q or "").lower()) if len(t) >= 3}


def _text_matches_query(q: str, *fields: str) -> bool:
    tokens = _query_tokens(q)
    if not tokens:
        return True
    blob = " ".join(fields).lower()
    return any(token in blob for token in tokens)


def extract_event_search_query(raw: str) -> tuple[str, bool, dict[str, Any]]:
    """Normalize a user message into an event search needle.

    Returns (query, needs_preferences, filters). Empty query = browse upcoming.
    """
    text = (raw or "").strip()
    lower = text.lower()
    filters: dict[str, Any] = {}

    for city in _CITY_HINTS:
        if city in lower:
            filters["city"] = city.title()
            break

    if re.search(r"\bfree\b", lower):
        filters["paid"] = "free"
    if re.search(r"\btonight\b", lower):
        filters["when"] = "tonight"
    elif re.search(r"\bthis weekend\b|\bweekend\b", lower):
        filters["when"] = "weekend"
    elif re.search(r"\bnext week\b", lower):
        filters["when"] = "next_week"
    elif re.search(r"\bthis week\b", lower):
        filters["when"] = "this_week"
    elif re.search(r"\btomorrow\b", lower):
        filters["when"] = "tomorrow"

    tokens = [
        t
        for t in re.findall(r"[a-z0-9']+", lower)
        if t not in _EVENT_STOPWORDS and len(t) >= 3
    ]
    # Drop tokens already captured as structured filters.
    drop = set()
    if filters.get("city"):
        drop.update(filters["city"].lower().split())
    if filters.get("when"):
        drop.update(
            {
                "tonight",
                "tomorrow",
                "weekend",
                "this",
                "next",
                "week",
            }
        )
    tokens = [t for t in tokens if t not in drop]
    query = " ".join(tokens)[:120]
    needs_preferences = not bool(filters.get("city") or filters.get("when") or query)
    return query, needs_preferences, filters


def _serialize_event(event: Any) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "title": event.title,
        "slug": event.slug,
        "city": getattr(event, "city", None),
        "start_datetime": (
            event.start_datetime.isoformat() if event.start_datetime else None
        ),
        "url": f"/events/{event.slug}" if event.slug else None,
    }


def search_public_events(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    from datetime import UTC, datetime, timedelta

    raw = str(args.get("query") or args.get("q") or "").strip()[:200]
    limit = min(int(args.get("limit") or 8), 20)
    if args.get("browse_upcoming") and not raw:
        query, needs_preferences, filters = "", True, {}
    else:
        query, needs_preferences, filters = extract_event_search_query(raw)
        if args.get("city"):
            filters["city"] = str(args["city"])[:64]
            needs_preferences = False
        if args.get("paid"):
            filters["paid"] = str(args["paid"])[:16]
            needs_preferences = False
        if args.get("when"):
            filters["when"] = str(args["when"])[:32]

    search_q = query or None
    if filters.get("city") and (
        not search_q or filters["city"].lower() not in (search_q or "").lower()
    ):
        search_q = filters["city"] if not search_q else f"{search_q} {filters['city']}"

    # Time-window asks should browse upcoming, not FTS on "next week".
    when = filters.get("when")
    if when in {"next_week", "this_week", "tonight", "tomorrow"} and not filters.get("city"):
        search_q = None

    events = list_published_events(
        db,
        q=search_q,
        weekend=when == "weekend",
        paid=filters.get("paid"),
        limit=max(limit, 20),
    )
    used_fallback_browse = False
    if not events and search_q:
        events = list_published_events(db, q=None, limit=max(limit, 20))
        used_fallback_browse = bool(events)
        needs_preferences = True

    now = datetime.now(UTC)

    def _in_window(event: Any) -> bool:
        start = getattr(event, "start_datetime", None)
        if start is None:
            return True
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if when == "tonight":
            return start.date() == now.date()
        if when == "tomorrow":
            return start.date() == (now + timedelta(days=1)).date()
        if when == "this_week":
            end = now + timedelta(days=(6 - now.weekday()))
            return now <= start <= end.replace(hour=23, minute=59, second=59)
        if when == "next_week":
            # Next Monday 00:00 through following Sunday
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            start_window = (now + timedelta(days=days_until_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_window = start_window + timedelta(days=7)
            return start_window <= start < end_window
        return True

    if when in {"next_week", "this_week", "tonight", "tomorrow"}:
        windowed = [e for e in events if _in_window(e)]
        # If the calendar window is empty, still show soonest upcoming
        # and ask for preferences — better than blog deflection.
        if windowed:
            events = windowed
        else:
            used_fallback_browse = True
            needs_preferences = True

    events = events[:limit]
    items = [_serialize_event(event) for event in events]
    preference_prompt = (
        "To personalize this, tell me a city (e.g. Lagos, Ibadan), when "
        "(tonight / this weekend), and vibe (Afrobeats, comedy, free only)."
    )
    if not items:
        summary = (
            "I could not find upcoming listed events right now. " + preference_prompt
        )
    elif when == "next_week" and used_fallback_browse:
        titles = ", ".join(str(i["title"]) for i in items[:3] if i.get("title"))
        summary = (
            f"I do not see events specifically tagged for next week yet. "
            f"Here are {len(items)} upcoming event(s)"
            + (f": {titles}." if titles else ".")
            + f" {preference_prompt}"
        )
    elif needs_preferences or used_fallback_browse:
        titles = ", ".join(str(i["title"]) for i in items[:3] if i.get("title"))
        summary = (
            f"Here are {len(items)} upcoming event(s) on Pàdéyá"
            + (f": {titles}." if titles else ".")
            + f" {preference_prompt}"
        )
    else:
        titles = ", ".join(str(i["title"]) for i in items[:3] if i.get("title"))
        summary = f"Found {len(items)} upcoming event(s): {titles}."

    return {
        "ok": True,
        "query": search_q or "",
        "filters": filters,
        "needs_preferences": needs_preferences or used_fallback_browse,
        "preference_prompt": preference_prompt,
        "results": items,
        "count": len(items),
        "summary": summary,
    }


def get_my_event_recommendations(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}

    args = args or {}
    raw = str(args.get("query") or args.get("q") or "").strip()
    _, needs_preferences, filters = extract_event_search_query(raw)
    city = args.get("city") or filters.get("city")
    limit = min(int(args.get("limit") or 8), 20)
    preference_prompt = (
        "Want better picks? Tell me your city, preferred night (weeknight / weekend), "
        "and vibe (music, comedy, free only)."
    )

    try:
        from app.events.recommendations.service import list_recommendations

        payload = list_recommendations(
            db,
            user,
            limit=limit,
            city=str(city)[:64] if city else None,
            category=str(args.get("category") or "")[:64] or None,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": "lookup_failed",
            "detail": type(exc).__name__,
            "results": [],
        }

    items: list[dict[str, Any]] = []
    for row in payload.get("events") or []:
        if not isinstance(row, dict):
            continue
        event = row.get("event")
        if hasattr(event, "model_dump"):
            event = event.model_dump()
        if not isinstance(event, dict):
            event = row
        slug = event.get("slug")
        reasons = row.get("reasons") or []
        primary_reason = None
        if isinstance(reasons, list) and reasons:
            primary_reason = reasons[0] if isinstance(reasons[0], str) else str(reasons[0])
        items.append(
            {
                "id": str(event.get("id") or ""),
                "title": event.get("title"),
                "slug": slug,
                "city": event.get("city"),
                "start_datetime": event.get("start_datetime"),
                "url": f"/events/{slug}" if slug else None,
                "reason": primary_reason,
            }
        )

    if not items:
        browse = search_public_events(
            db, args={"query": "", "browse_upcoming": True, "limit": limit}
        )
        return {
            "ok": True,
            "results": browse.get("results") or [],
            "count": browse.get("count") or 0,
            "needs_preferences": True,
            "preference_prompt": preference_prompt,
            "filters": filters,
            "summary": (
                "I do not have personalized recommendations yet. "
                + str(browse.get("summary") or preference_prompt)
            ),
            "used_public_fallback": True,
        }

    titles = ", ".join(str(i["title"]) for i in items[:3] if i.get("title"))
    summary = f"Recommended for you: {titles}."
    if needs_preferences:
        summary += f" {preference_prompt}"

    return {
        "ok": True,
        "results": items,
        "count": len(items),
        "needs_preferences": needs_preferences,
        "preference_prompt": preference_prompt,
        "filters": filters,
        "summary": summary,
    }


def get_public_event(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    slug = str(args.get("slug") or args.get("event_slug") or "").strip()
    if not slug:
        return {"ok": False, "error": "missing_slug", "result": None}
    event = get_event_by_slug(db, slug)
    if event is None or getattr(event, "status", None) != "published":
        return {"ok": False, "error": "not_found", "result": None}
    visibility = getattr(event, "visibility", None) or "listed"
    if visibility not in ("listed", "approval_required"):
        return {"ok": False, "error": "not_public", "result": None}
    return {
        "ok": True,
        "result": {
            "id": str(event.id),
            "slug": event.slug,
            "title": event.title,
            "city": getattr(event, "city", None),
            "start_datetime": (
                event.start_datetime.isoformat() if event.start_datetime else None
            ),
            "url": f"/events/{event.slug}",
            "short_description": (getattr(event, "short_description", None) or "")[:300],
        },
    }


def search_public_hosts(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    q = str(args.get("query") or args.get("q") or "").strip().lower()[:200]
    limit = min(int(args.get("limit") or 8), 20)
    try:
        from app.legacy.discover import list_discover_hosts

        hosts = list_discover_hosts(db, limit=60)
    except Exception:
        return {"ok": True, "query": q, "results": [], "count": 0}
    results = []
    for host in hosts:
        name = str(host.get("display_name") or host.get("name") or "")
        username = str(host.get("username") or "")
        if q and q not in name.lower() and q not in username.lower():
            continue
        results.append(
            {
                "id": str(host.get("id") or ""),
                "display_name": name,
                "username": username,
                "url": host.get("legacy_url") or (f"/u/{username}" if username else None),
            }
        )
        if len(results) >= limit:
            break
    return {"ok": True, "query": q, "results": results, "count": len(results)}


def get_public_pricing(
    db: Session, *, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    """Public fee structure from live pricing settings (no invented rates)."""
    try:
        from app.pricing.service import build_public_pricing

        payload = build_public_pricing(db)
        categories = [
            {
                "label": row.label,
                "payer": row.payer,
                "description": row.public_description,
                "display_rate": row.display_rate,
                "may_vary_by_host": row.may_vary_by_host,
            }
            for row in payload.categories
        ]
        host_rows = [c for c in categories if c.get("payer") == "host"]
        buyer_rows = [c for c in categories if c.get("payer") == "buyer"]
        return {
            "ok": True,
            "note": payload.note,
            "url": "/pricing",
            "host_fee_categories": host_rows,
            "buyer_fee_categories": buyer_rows,
            "summary": (
                "Pàdéyá charges hosts platform fees on successful sales "
                "(tickets, merch, Vault) deducted from host earnings. "
                "Buyers may see separate service/processing fees at checkout. "
                "Exact host rates may vary and appear in Host → Earnings."
            ),
        }
    except Exception:
        return {
            "ok": True,
            "url": "/pricing",
            "summary": (
                "Hosts pay configurable platform fees on successful sales, "
                "deducted from earnings. See /pricing and Help for details."
            ),
            "host_fee_categories": [],
            "buyer_fee_categories": [],
        }


def search_public_sponsors(
    db: Session, *, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    q = str((args or {}).get("query") or (args or {}).get("q") or "").strip()[:120]
    limit = min(int((args or {}).get("limit") or 8), 20)
    results: list[dict[str, Any]] = []
    try:
        from app.sponsor_profiles.service import list_public_sponsors

        rows = list_public_sponsors(db)
        ql = q.lower()
        for sponsor in rows:
            name = (getattr(sponsor, "display_name", None) or getattr(sponsor, "company_name", "") or "")
            slug = getattr(sponsor, "slug", "") or ""
            industry = getattr(sponsor, "industry", "") or ""
            blob = f"{name} {slug} {industry}".lower()
            if ql and ql not in blob and not any(t in blob for t in _query_tokens(q)):
                continue
            results.append(
                {
                    "display_name": name,
                    "slug": slug,
                    "industry": industry,
                    "url": f"/sponsors/{slug}" if slug else "/sponsors",
                    "verified": getattr(sponsor, "verification_status", None) == "verified",
                }
            )
            if len(results) >= limit:
                break
    except Exception:
        results = []
    return {
        "ok": True,
        "query": q,
        "results": results,
        "count": len(results),
        "summary": f"Found {len(results)} public sponsor profile(s).",
    }


def search_public_pages(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    q = str(args.get("query") or args.get("q") or "").strip()
    route = resolve_public_route(q)
    registry_hits = []
    if route:
        registry_hits.append(
            {
                "key": route.key,
                "title": route.title,
                "url": route.path,
                "description": route.description,
                "source": "registry",
            }
        )
    else:
        ql = q.lower()
        for entry in PUBLIC_ROUTE_REGISTRY.values():
            blob = " ".join(
                [entry.title, entry.description, *entry.synonyms]
            ).lower()
            if ql and ql in blob:
                registry_hits.append(
                    {
                        "key": entry.key,
                        "title": entry.title,
                        "url": entry.path,
                        "description": entry.description,
                        "source": "registry",
                    }
                )
            if len(registry_hits) >= 6:
                break

    knowledge_hits: list[dict[str, Any]] = []
    try:
        from app.assistant.knowledge.retrieve import retrieve_knowledge

        knowledge_hits = retrieve_knowledge(db, query=q, top_k=4)
    except Exception:
        knowledge_hits = []

    return {
        "ok": True,
        "query": q,
        "results": registry_hits,
        "knowledge": knowledge_hits,
        "count": len(registry_hits) + len(knowledge_hits),
    }


def search_public_resources(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    q = str(args.get("query") or args.get("q") or "").strip()[:200]
    limit = min(int(args.get("limit") or 6), 15)
    results: list[dict[str, Any]] = []
    # Blog
    try:
        from app.blog.models import BlogPost

        stmt = select(BlogPost).where(BlogPost.status == "published").limit(40)
        posts = list(db.scalars(stmt).all())
        ql = q.lower()
        for post in posts:
            title = getattr(post, "title", "") or ""
            slug = getattr(post, "slug", "") or ""
            if ql and not _text_matches_query(q, title, slug):
                continue
            results.append(
                {
                    "type": "blog",
                    "title": title,
                    "url": f"/blog/{slug}" if slug else "/blog",
                    "slug": slug,
                }
            )
            if len(results) >= limit:
                break
    except Exception:
        pass
    # Knowledge base / help
    try:
        from app.knowledge_base import models as kb_models

        Article = getattr(kb_models, "KnowledgeArticle", None) or getattr(
            kb_models, "HelpArticle", None
        )
        if Article is not None:
            rows = list(db.scalars(select(Article).limit(40)).all())
            ql = q.lower()
            for row in rows:
                title = getattr(row, "title", "") or ""
                slug = getattr(row, "slug", "") or ""
                excerpt = getattr(row, "excerpt", "") or ""
                if ql and not _text_matches_query(q, title, slug, excerpt):
                    continue
                results.append(
                    {
                        "type": "help",
                        "title": title,
                        "url": f"/help/{slug}" if slug else "/help",
                        "slug": slug,
                    }
                )
                if len(results) >= limit:
                    break
    except Exception:
        pass
    return {"ok": True, "query": q, "results": results[:limit], "count": len(results[:limit])}


def search_public_products(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    q = str(args.get("query") or args.get("q") or "").strip()[:200]
    limit = min(int(args.get("limit") or 8), 20)
    results: list[dict[str, Any]] = []
    try:
        from app.merch.models import MerchProduct

        stmt = select(MerchProduct).limit(80)
        # Prefer marketplace-listed if column exists
        products = list(db.scalars(stmt).all())
        ql = q.lower()
        for product in products:
            if hasattr(product, "marketplace_listed") and not getattr(
                product, "marketplace_listed", True
            ):
                continue
            status = getattr(product, "status", None)
            if status and status not in ("active", "published", "live"):
                continue
            title = getattr(product, "title", None) or getattr(product, "name", "") or ""
            slug = getattr(product, "slug", "") or ""
            if ql and ql not in title.lower() and ql not in slug.lower():
                continue
            results.append(
                {
                    "title": title,
                    "slug": slug,
                    "url": f"/shop/{slug}" if slug else "/shop",
                }
            )
            if len(results) >= limit:
                break
    except Exception:
        results = []
    return {"ok": True, "query": q, "results": results, "count": len(results)}


def search_public_memories(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    q = str(args.get("query") or args.get("q") or "").strip()[:200]
    limit = min(int(args.get("limit") or 6), 15)
    results: list[dict[str, Any]] = []
    try:
        from app.memories.albums import list_public_albums

        albums, _cursor = list_public_albums(db, limit=limit, cursor=None, city=None)
        ql = q.lower()
        for album in albums or []:
            if isinstance(album, dict):
                title = str(album.get("title") or album.get("event_title") or "")
                url = album.get("url") or album.get("path")
                if ql and ql not in title.lower():
                    continue
                results.append(redact_dict({"title": title, "url": url, **album}))
            if len(results) >= limit:
                break
    except Exception:
        results = []
    return {"ok": True, "query": q, "results": results, "count": len(results)}
