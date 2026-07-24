"""Analytics utility helpers: bots, UTM, visitor ids, dedupe keys."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

_BOT_UA = re.compile(
    r"(bot|crawl|spider|slurp|facebookexternalhit|preview|headless|"
    r"wget|curl|python-requests|scrapy|httpclient|monitoring)",
    re.I,
)

_UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")


def is_likely_bot(user_agent: str | None) -> bool:
    """Heuristic bot detection from User-Agent."""
    if not user_agent or not user_agent.strip():
        return False
    return bool(_BOT_UA.search(user_agent.strip()[:500]))


def normalize_utm_params(
    raw: dict[str, Any] | None = None,
    *,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    term: str | None = None,
    content: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_term: str | None = None,
    utm_content: str | None = None,
    url: str | None = None,
) -> dict[str, str | None]:
    """Normalize UTM-style attribution into a stable dict."""
    from_url: dict[str, str] = {}
    if url:
        try:
            qs = parse_qs(urlparse(url).query)
            for key in _UTM_KEYS:
                vals = qs.get(key) or qs.get(key.replace("utm_", ""))
                if vals and vals[0]:
                    from_url[key] = str(vals[0]).strip()[:160]
        except Exception:
            pass

    bag = dict(raw or {})
    for key in _UTM_KEYS:
        if key in bag and bag[key] is not None:
            from_url[key] = str(bag[key]).strip()[:160]

    def pick(*values: str | None) -> str | None:
        for value in values:
            if value is None:
                continue
            cleaned = str(value).strip()[:160]
            if cleaned:
                return cleaned.lower() if cleaned else None
        return None

    src = pick(source, utm_source, from_url.get("utm_source"), bag.get("source"))
    med = pick(medium, utm_medium, from_url.get("utm_medium"), bag.get("medium"))
    camp = pick(campaign, utm_campaign, from_url.get("utm_campaign"), bag.get("campaign"))
    trm = pick(term, utm_term, from_url.get("utm_term"), bag.get("term"))
    cnt = pick(content, utm_content, from_url.get("utm_content"), bag.get("content"))

    return {
        "source": src,
        "medium": med,
        "campaign": camp,
        "term": trm,
        "content": cnt,
        "utm_source": src,
        "utm_medium": med,
        "utm_campaign": camp,
        "utm_term": trm,
        "utm_content": cnt,
    }


def visitor_identity(
    *,
    user_id: UUID | str | None = None,
    anonymous_id: str | None = None,
    session_id: str | None = None,
) -> str | None:
    """Stable visitor key for unique metrics (prefer user → anon → session)."""
    if user_id is not None:
        return f"u:{user_id}"
    if anonymous_id and anonymous_id.strip():
        return f"a:{anonymous_id.strip()[:64]}"
    if session_id and session_id.strip():
        return f"s:{session_id.strip()[:64]}"
    return None


def generate_dedupe_key(
    scope: str,
    *,
    request_id: str | None = None,
    target_event_id: UUID | str | None = None,
    session_id: str | None = None,
    anonymous_id: str | None = None,
    user_id: UUID | str | None = None,
    order_id: UUID | str | None = None,
    list_context: str | None = None,
    extra: str | None = None,
) -> str | None:
    """Build a stable dedupe key for analytics writes.

    Preference order for identity: request_id → user/anon/session + event dims.
    """
    scope_clean = (scope or "").strip().lower()[:64]
    if not scope_clean:
        return None
    if request_id and request_id.strip():
        return f"{scope_clean}:req:{request_id.strip()[:128]}"[:191]

    parts = [scope_clean]
    if target_event_id is not None:
        parts.append(f"evt:{target_event_id}")
    if order_id is not None:
        parts.append(f"ord:{order_id}")

    identity = visitor_identity(
        user_id=user_id, anonymous_id=anonymous_id, session_id=session_id
    )
    if identity:
        parts.append(identity)
    elif order_id is None:
        # Without visitor identity or order, cannot safely dedupe
        return None

    if list_context and str(list_context).strip():
        parts.append(f"ctx:{str(list_context).strip()[:64]}")
    if extra and str(extra).strip():
        parts.append(str(extra).strip()[:64])
    return ":".join(parts)[:191]
