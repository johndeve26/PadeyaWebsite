"""Hybrid lexical FTS + route/title boost retrieval."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.assistant.constants import RETRIEVAL_TOP_K
from app.assistant.routes.public_registry import PUBLIC_ROUTE_REGISTRY, resolve_public_route


def retrieve_knowledge(
    db: Session,
    *,
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    k = max(1, min(int(top_k), 12))
    results: list[dict[str, Any]] = []

    # Route registry boost
    route = resolve_public_route(q)
    if route:
        results.append(
            {
                "title": route.title,
                "url": route.path,
                "snippet": route.description,
                "source_type": "registry",
                "route_key": route.key,
                "score": 10.0,
            }
        )
    else:
        ql = q.lower()
        for entry in PUBLIC_ROUTE_REGISTRY.values():
            if any(s in ql for s in entry.synonyms) or entry.title.lower() in ql:
                results.append(
                    {
                        "title": entry.title,
                        "url": entry.path,
                        "snippet": entry.description,
                        "source_type": "registry",
                        "route_key": entry.key,
                        "score": 6.0,
                    }
                )
                if len(results) >= 3:
                    break

    # FTS on chunks
    try:
        rows = db.execute(
            text(
                """
                SELECT c.id, c.content, c.heading_path, d.title, d.canonical_url,
                       d.route_group, d.source_type,
                       ts_rank_cd(c.search_vector, plainto_tsquery('english', :q)) AS rank
                FROM assistant_knowledge_chunks c
                JOIN assistant_knowledge_documents d ON d.id = c.document_id
                WHERE d.status = 'active'
                  AND c.search_vector @@ plainto_tsquery('english', :q)
                ORDER BY rank DESC
                LIMIT :lim
                """
            ),
            {"q": q, "lim": k},
        ).mappings().all()
        for row in rows:
            results.append(
                {
                    "title": row["title"] or "Pàdéyá",
                    "url": row["canonical_url"],
                    "snippet": (row["content"] or "")[:280],
                    "source_type": row["source_type"] or "knowledge",
                    "route_key": row["route_group"],
                    "heading_path": row["heading_path"],
                    "score": float(row["rank"] or 0) + (
                        2.0 if route and route.path in (row["canonical_url"] or "") else 0.0
                    ),
                }
            )
    except Exception:
        # Table may not exist yet in fresh envs — fail soft
        pass

    results.sort(key=lambda r: float(r.get("score") or 0), reverse=True)
    # Dedupe by url
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in results:
        url = str(item.get("url") or "")
        if url in seen:
            continue
        seen.add(url)
        out.append(item)
        if len(out) >= k:
            break
    return out
