"""Real internal link inventory for Blog AI Studio — never invent URLs."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.blog.models import BlogPost

# Only routes that exist as first-class app pages in this repo.
APPROVED_STATIC_ROUTES: tuple[tuple[str, str], ...] = (
    ("/events", "Events"),
    ("/hosts", "Hosts"),
    ("/help", "Help"),
    ("/blog", "Blog"),
    ("/pricing", "Pricing"),
)


def static_route_suggestions() -> list[dict[str, str]]:
    return [
        {
            "target_url": path,
            "target_title": title,
            "suggested_anchor": title,
            "insertion_location": "relevant body section",
            "relevance_reason": "Approved static Pàdéyá route",
        }
        for path, title in APPROVED_STATIC_ROUTES
    ]


def search_published_posts(
    db: Session,
    *,
    query: str | None = None,
    exclude_post_id=None,
    limit: int = 8,
) -> list[dict[str, str]]:
    stmt = select(BlogPost).where(
        BlogPost.status == "published",
        BlogPost.archived_at.is_(None),
    )
    if exclude_post_id is not None:
        stmt = stmt.where(BlogPost.id != exclude_post_id)
    q = (query or "").strip()
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                BlogPost.title.ilike(like),
                BlogPost.excerpt.ilike(like),
                BlogPost.slug.ilike(like),
            )
        )
    stmt = stmt.order_by(BlogPost.published_at.desc()).limit(limit)
    rows = db.scalars(stmt).all()
    out: list[dict[str, str]] = []
    for row in rows:
        url = f"/blog/{row.slug}"
        out.append(
            {
                "target_url": url,
                "target_title": row.title,
                "suggested_anchor": row.title,
                "insertion_location": "related reading / body",
                "relevance_reason": "Published blog post",
            }
        )
    return out


def suggest_internal_links(
    db: Session,
    *,
    query: str | None = None,
    exclude_post_id=None,
    limit_posts: int = 6,
) -> list[dict[str, str]]:
    """Return only real URLs: published /blog/{slug} + approved static inventory."""
    posts = search_published_posts(
        db, query=query, exclude_post_id=exclude_post_id, limit=limit_posts
    )
    # Prefer post matches; always allow a few static routes
    static = static_route_suggestions()
    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    for item in posts + static:
        url = item["target_url"]
        if url in seen:
            continue
        if not url.startswith("/"):
            continue
        seen.add(url)
        merged.append(item)
    return merged
