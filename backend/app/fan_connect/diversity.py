"""Diversity mixer for Fan Connect suggestions (mode=mixed / Best matches).

Ranking philosophy: safety first, then strong shared event/social signals,
then nearby, interests/place, recent activity, and feedback. Distance alone
must never dominate the default feed.
"""

from __future__ import annotations

from typing import Any

from app.fan_connect import constants as C


# Bucket fill order for mixed pages (round-robin quotas)
_BUCKET_ORDER = (
    ("strong", C.DIVERSITY_QUOTA_STRONG),
    ("shared_event", C.DIVERSITY_QUOTA_SHARED_EVENT),
    ("nearby", C.DIVERSITY_QUOTA_NEARBY),
    ("fof", C.DIVERSITY_QUOTA_FOF),
    ("fresh", C.DIVERSITY_QUOTA_FRESH),
)


def mix_suggestions(
    scored_items: list[tuple[int, dict, list[str]]],
    *,
    limit: int,
    mode: str,
) -> list[dict]:
    """
    scored_items: (score, card, buckets) sorted by score desc is fine but not required.
    Returns cards for one page (up to limit), diversified when mode is mixed.
    """
    if not scored_items:
        return []

    if mode != C.MODE_MIXED:
        ordered = sorted(scored_items, key=lambda t: t[0], reverse=True)
        return [card for _, card, _ in ordered[:limit]]

    # Group into buckets (a card may appear in multiple; we pick once)
    pools: dict[str, list[tuple[int, dict]]] = {name: [] for name, _ in _BUCKET_ORDER}
    pools["other"] = []
    for score, card, buckets in scored_items:
        placed = False
        for name, _ in _BUCKET_ORDER:
            if name in buckets:
                pools[name].append((score, card))
                placed = True
                break
        if not placed:
            pools["other"].append((score, card))

    for name in pools:
        pools[name].sort(key=lambda t: t[0], reverse=True)

    selected: list[dict] = []
    seen: set[str] = set()
    quotas = {name: q for name, q in _BUCKET_ORDER}

    def _take(pool_name: str, n: int) -> None:
        pool = pools.get(pool_name) or []
        taken = 0
        while taken < n and pool:
            score, card = pool.pop(0)
            key = str(card.get("user_id") or card.get("username") or id(card))
            if key in seen:
                continue
            seen.add(key)
            selected.append(card)
            taken += 1

    # Round-robin one from each bucket until quotas filled or page full
    while len(selected) < limit:
        progressed = False
        for name, quota in _BUCKET_ORDER:
            if len(selected) >= limit:
                break
            if quotas[name] <= 0:
                continue
            before = len(selected)
            _take(name, 1)
            if len(selected) > before:
                quotas[name] -= 1
                progressed = True
        if not progressed:
            break

    # Fill remainder from leftover highest scores
    leftovers: list[tuple[int, dict]] = []
    for name in (*[n for n, _ in _BUCKET_ORDER], "other"):
        leftovers.extend(pools.get(name) or [])
    leftovers.sort(key=lambda t: t[0], reverse=True)
    for score, card in leftovers:
        if len(selected) >= limit:
            break
        key = str(card.get("user_id") or card.get("username") or id(card))
        if key in seen:
            continue
        seen.add(key)
        selected.append(card)

    return selected


def filter_by_mode(
    scored_items: list[tuple[int, dict, list[str]]],
    *,
    mode: str,
) -> list[tuple[int, dict, list[str]]]:
    """Narrow candidates for focused tabs; mixed returns all."""
    if mode in (C.MODE_MIXED, None, ""):
        return scored_items
    if mode == C.MODE_NEAR_ME:
        return [t for t in scored_items if "nearby" in t[2]]
    if mode == C.MODE_SAME_EVENT:
        return [t for t in scored_items if "shared_event" in t[2]]
    if mode == C.MODE_CONNECTIONS_OF_CONNECTIONS:
        return [t for t in scored_items if "fof" in t[2]]
    if mode == C.MODE_SAME_INTERESTS:
        return [t for t in scored_items if "interests" in t[2]]
    if mode == C.MODE_NEW_PEOPLE:
        return [t for t in scored_items if "fresh" in t[2] or "interests" in t[2]]
    return scored_items


def empty_state_copy(mode: str) -> dict[str, str]:
    """Mode-specific empty copy for API/FE consumers."""
    mapping: dict[str, dict[str, str]] = {
        C.MODE_NEAR_ME: {
            "title": "No nearby fans yet",
            "description": "No nearby fans yet. Check back as more fans opt in near your city and events.",
        },
        C.MODE_CONNECTIONS_OF_CONNECTIONS: {
            "title": "No friends-of-friends yet",
            "description": "No friends-of-friends yet. Connect with more fans to improve this.",
        },
        C.MODE_SAME_INTERESTS: {
            "title": "No interest matches yet",
            "description": "Add interests to your Fan Passport to get better suggestions.",
        },
        C.MODE_SAME_EVENT: {
            "title": "No shared-event fans yet",
            "description": "Get tickets to public nights on Pàdéyá to meet fans going too.",
        },
        C.MODE_NEW_PEOPLE: {
            "title": "No new people right now",
            "description": "Check back soon — fresh Passports appear here as fans join.",
        },
        C.MODE_MIXED: {
            "title": "No suggestions right now",
            "description": "Suggestions only show opted-in fans with shared event energy — never a dating feed.",
        },
    }
    return mapping.get(mode) or mapping[C.MODE_MIXED]
