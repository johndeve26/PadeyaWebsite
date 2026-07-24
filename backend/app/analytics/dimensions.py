"""Dimension helpers: UA parse, IP hash, metadata privacy scrubbing."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.analytics.utils import is_likely_bot, normalize_utm_params
from app.core.config import get_settings

# Never persist these keys in analytics metadata / properties.
FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "ip",
        "raw_ip",
        "ip_address",
        "client_ip",
        "email",
        "phone",
        "full_name",
        "name",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "card",
        "card_number",
        "pan",
        "cvv",
        "cvc",
        "expiry",
        "exp_month",
        "exp_year",
        "bank_account",
        "account_number",
        "bvn",
        "nin",
        "address",
        "street_address",
        "venue_address",
        "private_address",
        "hidden_address",
        "exact_address",
        "online_event_url",
        "join_url",
        "recipient_name",
        "shipping_address",
        "shipping_phone",
        "line1",
        "line2",
        "delivery_notes",
        "authorization_code",
        "card_authorization",
        "vault_title",
        "vault_description",
        "vault_body",
        "locked_title",
        "locked_description",
        "locked_body",
        "hidden_venue",
        "venue_name_private",
    }
)

# Allowed event-specific metadata keys (others from client are dropped unless nested scrub).
ALLOWED_METADATA_KEYS = frozenset(
    {
        "ticket_type_id",
        "ticket_type_name",
        "ticket_price",
        "promo_code",
        "ambassador_code",
        "order_id",
        "payment_reference",
        "card_position",
        "list_context",
        "page_section",
        "search_query",
        "category_filter",
        "city_filter",
        "sort_order",
        "share_channel",
        "conversion_value",
        "currency",
        "click_target",
        "method",
        "quantity",
        "action",
        "tracked_action",
        "target_event_id",
        "event_listing_id",
        "event_id",
        "stage",
        "path",
        "referrer",
        "source",
        "amount",
        "trusted",
        "currency",
        "discount",
        "promo_code_id",
        "refund_request_id",
        "vault_purchase_id",
        "vault_item_id",
        "access_type",
        "related_event_id",
        "locked_state",
        "source_page",
        "media_id",
        "failure_reason",
        "payout_request_id",
        "ambassador_id",
        "commission",
        "deduped",
        "unique_click",
        "country",
        "state",
        "city",
        "area",
        "category",
        "placement_context",
        "slot_number",
        "username",
        "q_length",
        "filter_type",
        "filter_value",
        # Event merch (no payment secrets, buyer PII, spend totals, or private venue copy)
        "merch_product_id",
        "merch_product_slug",
        "product_slug",
        "merch_variant_id",
        "variant_sku",
        "sku",
        "merch_item_count",
        "fulfillment_id",
        "fulfillment_method",
        "product_status",
        "moderation_status",
        "discount_code",
        "discount_applied",
        "bundle_id",
        "badge_key",
        "cart_id",
        "host_username",
        "event_slug",
        "order_item_id",
        "sponsor_brand_name",
        # Fan Connect (no private attendance, venues, tickets, spend, PII, Vault)
        "connection_id",
        "thread_id",
        "score_band",
        "cta_state",
        "reason_code_count",
        "request_policy",
        "fan_connect_enabled",
        "counterpart_username",
    }
)


def hash_ip(ip: str | None) -> str | None:
    """One-way hash of IP. Never store the raw address."""
    if not ip:
        return None
    cleaned = ip.strip().split(",")[0].strip()  # first X-Forwarded-For hop
    if not cleaned or cleaned.lower() in {"unknown", "null"}:
        return None
    secret = get_settings().secret_key
    digest = hashlib.sha256(f"{secret}|{cleaned}".encode("utf-8")).hexdigest()
    return digest[:64]


def hash_user_agent(ua: str | None) -> str | None:
    """One-way hash of user-agent (prefer over long-term raw UA joins)."""
    if not ua:
        return None
    cleaned = ua.strip()
    if not cleaned:
        return None
    secret = get_settings().secret_key
    digest = hashlib.sha256(f"{secret}|ua|{cleaned}".encode("utf-8")).hexdigest()
    return digest[:64]


def parse_user_agent(ua: str | None) -> dict[str, str | bool | None]:
    if not ua:
        return {
            "device_type": "unknown",
            "browser": "Other",
            "os": "Other",
            "is_bot": False,
            "user_agent": None,
        }
    truncated = ua[:500]
    lower = truncated.lower()
    is_bot = is_likely_bot(truncated)

    if "ipad" in lower or "tablet" in lower:
        device = "tablet"
    elif "mobi" in lower or "iphone" in lower or "android" in lower:
        device = "mobile"
    else:
        device = "desktop"

    if "edg/" in lower or "edge/" in lower:
        browser = "Edge"
    elif "chrome/" in lower and "chromium" not in lower:
        browser = "Chrome"
    elif "safari/" in lower and "chrome/" not in lower:
        browser = "Safari"
    elif "firefox/" in lower:
        browser = "Firefox"
    else:
        browser = "Other"

    if "windows" in lower:
        os_name = "Windows"
    elif "android" in lower:
        os_name = "Android"
    elif "iphone" in lower or "ipad" in lower or "ios" in lower:
        os_name = "iOS"
    elif "mac os" in lower or "macintosh" in lower:
        os_name = "macOS"
    elif "linux" in lower:
        os_name = "Linux"
    else:
        os_name = "Other"

    return {
        "device_type": device,
        "browser": browser,
        "os": os_name,
        "is_bot": is_bot,
        "user_agent": truncated,
    }


def scrub_metadata(raw: dict[str, Any] | None, *, strict_allowlist: bool = True) -> dict[str, Any]:
    """Strip PII / payment / private venue fields from analytics metadata."""
    if not raw:
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        k = str(key).strip().lower()[:64]
        if not k or k in FORBIDDEN_METADATA_KEYS:
            continue
        if strict_allowlist and k not in ALLOWED_METADATA_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, str):
            out[k] = value[:500]
        elif isinstance(value, (int, float, bool)):
            out[k] = value
        elif isinstance(value, UUID):
            out[k] = str(value)
        else:
            # Drop nested objects / lists to avoid accidental PII dumps
            continue
    return out


def truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def coalesce_received_at(value: datetime | None = None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def build_analytics_row_dimensions(
    *,
    anonymous_id: str | None = None,
    request_id: str | None = None,
    occurred_at: datetime | None = None,
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
    referrer: str | None = None,
    landing_page: str | None = None,
    path: str | None = None,
    current_path: str | None = None,
    previous_path: str | None = None,
    user_agent: str | None = None,
    device_type: str | None = None,
    browser: str | None = None,
    os: str | None = None,
    country: str | None = None,
    city: str | None = None,
    client_ip: str | None = None,
    metadata: dict[str, Any] | None = None,
    properties: dict[str, Any] | None = None,
    is_bot: bool | None = None,
    environment: str | None = None,
    app_version: str | None = None,
    target_event_id: UUID | None = None,
) -> dict[str, Any]:
    """Normalize inbound dimension fields for AnalyticsEvent insert."""
    ua_info = parse_user_agent(user_agent)
    merged_meta = scrub_metadata({**(properties or {}), **(metadata or {})})

    settings = get_settings()
    env = truncate(environment, 32) or truncate(settings.app_env, 32)

    utm = normalize_utm_params(
        source=source,
        medium=medium,
        campaign=campaign,
        term=term,
        content=content,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_term=utm_term,
        utm_content=utm_content,
        url=path or current_path or landing_page,
    )
    src = truncate(utm.get("source"), 120)
    med = truncate(utm.get("medium"), 120)
    camp = truncate(utm.get("campaign"), 160)
    trm = truncate(utm.get("term"), 160)
    cnt = truncate(utm.get("content"), 160)
    path_value = truncate(path or current_path, 500)
    ua_raw = ua_info["user_agent"] if user_agent else truncate(user_agent, 500)

    # Client may flag bot=true but cannot clear a UA-detected bot.
    detected_bot = bool(ua_info["is_bot"]) or is_likely_bot(
        ua_raw if isinstance(ua_raw, str) else None
    )
    if is_bot is True:
        detected_bot = True

    return {
        "target_event_id": target_event_id,
        "anonymous_id": truncate(anonymous_id, 64),
        "request_id": truncate(request_id, 64),
        "occurred_at": occurred_at,
        "received_at": coalesce_received_at(),
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
        "referrer": truncate(referrer, 500),
        "landing_page": truncate(landing_page, 500),
        "path": path_value,
        "current_path": truncate(current_path or path_value, 500),
        "previous_path": truncate(previous_path, 500),
        "user_agent": ua_raw,
        "user_agent_hash": hash_user_agent(ua_raw if isinstance(ua_raw, str) else None),
        "device_type": truncate(device_type, 32) or ua_info["device_type"],
        "browser": truncate(browser, 64) or ua_info["browser"],
        "os": truncate(os, 64) or ua_info["os"],
        "country": truncate(country, 64),
        "city": truncate(city, 96),
        "ip_hash": hash_ip(client_ip),
        "event_metadata": merged_meta or None,
        "properties": merged_meta or None,  # legacy mirror
        "is_bot": detected_bot,
        "environment": env,
        "app_version": truncate(app_version, 64),
    }
