"""Public search tools — events, hosts, pages, resources, products, memories."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.privacy import redact_dict
from app.assistant.routes.public_registry import PUBLIC_ROUTE_REGISTRY, resolve_public_route
from app.events.service import get_event_by_slug, list_published_events


def _query_tokens(q: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", (q or "").lower()) if len(t) >= 3}


def _text_matches_query(q: str, *fields: str) -> bool:
    tokens = _query_tokens(q)
    if not tokens:
        return True
    blob = " ".join(fields).lower()
    return any(token in blob for token in tokens)


def search_public_events(
    db: Session, *, args: dict[str, Any], **_: Any
) -> dict[str, Any]:
    q = str(args.get("query") or args.get("q") or "").strip()[:200]
    limit = min(int(args.get("limit") or 8), 20)
    events = list_published_events(db, q=q or None, limit=limit)
    items = []
    for event in events:
        items.append(
            {
                "id": str(event.id),
                "slug": event.slug,
                "title": event.title,
                "city": getattr(event, "city", None),
                "start_datetime": (
                    event.start_datetime.isoformat() if event.start_datetime else None
                ),
                "url": f"/events/{event.slug}" if event.slug else None,
            }
        )
    return {"ok": True, "query": q, "results": items, "count": len(items)}


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
