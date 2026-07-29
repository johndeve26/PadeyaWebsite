"""Normalize Fan Connect request policy selections."""

from __future__ import annotations

from app.fan_connect import constants as C


def normalize_request_policies(
    policies: list[str] | tuple[str, ...] | None = None,
    *,
    fallback: str | None = None,
) -> list[str]:
    """Return a canonical non-empty policy list.

    - ``nobody`` is exclusive.
    - Other options may be combined (OR eligibility).
    - Invalid / empty input falls back to all open paths (never nobody).
    """
    raw = list(policies or [])
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if value not in C.REQUEST_POLICIES or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)

    if C.POLICY_NOBODY in cleaned:
        return [C.POLICY_NOBODY]

    ordered = [p for p in C.REQUEST_POLICY_OPTIONS if p in seen]
    if ordered:
        return ordered

    if fallback == C.POLICY_NOBODY:
        return [C.POLICY_NOBODY]
    if fallback in C.REQUEST_POLICY_OPTIONS:
        return [fallback]
    return list(C.DEFAULT_REQUEST_POLICIES)


def primary_request_policy(policies: list[str]) -> str:
    """Most permissive selected policy (legacy single-field sync)."""
    normalized = normalize_request_policies(policies)
    if C.POLICY_NOBODY in normalized:
        return C.POLICY_NOBODY
    return max(normalized, key=lambda p: C.REQUEST_POLICY_RANK.get(p, 0))


def policies_allow_shared(policies: list[str], shared: dict) -> bool:
    """True when any selected non-nobody policy is satisfied."""
    from app.fan_connect.context import policy_allows_shared

    normalized = normalize_request_policies(policies)
    if C.POLICY_NOBODY in normalized:
        return False
    return any(policy_allows_shared(policy, shared) for policy in normalized)
