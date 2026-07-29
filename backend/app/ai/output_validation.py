"""Validate AI outputs before returning drafts to hosts."""

from __future__ import annotations

import re

from fastapi import HTTPException, status

from app.ai.constants import (
    DESCRIPTION_MAX_LEN,
    DESCRIPTION_MIN_LEN,
    TITLE_MAX_LEN,
    TITLE_MIN_LEN,
    TITLE_OPTIONS_MAX,
    TITLE_OPTIONS_MIN,
)

# Phrases that must not appear in host-facing drafts
BANNED_PHRASES = (
    "guaranteed sales",
    "guaranteed attendance",
    "guaranteed revenue",
    "official padeya policy",
    "official pàdéyá policy",
    "official platform policy",
    "auto-create event",
    "publish with ai",
    "we will refund",
    "full refund guaranteed",
    "money-back guarantee",
    "100% refund",
    "no questions asked refund",
    "guaranteed profit",
    "risk-free investment",
)

MERCH_BANNED_PHRASES = BANNED_PHRASES + (
    "100% cotton guaranteed",
    "premium quality guaranteed",
    "guaranteed authentic",
    "limited edition only",
    "selling out fast",
    "only a few left",
    "cures",
    "treats ",
    "clinically proven",
    "fda approved",
    "official merchandise of",
    "licensed by",
    "endorsed by",
    "as seen with",
    "free returns forever",
    "lifetime warranty",
)

_POLICY_OVERCLAIM = re.compile(
    r"(?i)\b(official\s+policy|legally\s+binding\s+refund|"
    r"padeya\s+guarantees|pàdéyá\s+guarantees)\b"
)

_MERCH_OVERCLAIM = re.compile(
    r"(?i)\b(guaranteed\s+(quality|authentic|cotton|sale|scarcity)|"
    r"limited\s+edition\s+only|official\s+(merch|merchandise)\s+of|"
    r"cures?\b|treats\b|clinically\s+proven|lifetime\s+warranty|"
    r"free\s+returns?\s+forever)\b"
)

_PRIVATE_ECHO = re.compile(
    r"(?i)\b(password|api[_ -]?key|bearer\s+\S+|sk-[a-z0-9]{8,}|"
    r"paystack\s+secret|qr\s*(secret|token|payload)|jti\s*[:=])\b"
)

_NUMBERED_LINE = re.compile(
    r"^\s*(?:[-*]|\d+[.)])\s*(.+)$",
    re.MULTILINE,
)

_TAG_SAFE = re.compile(r"^[a-z0-9][a-z0-9\- ]{0,30}[a-z0-9]$|^[a-z0-9]$", re.I)


def _contains_banned(text: str, *, merch: bool = False) -> str | None:
    lower = text.lower()
    phrases = MERCH_BANNED_PHRASES if merch else BANNED_PHRASES
    for phrase in phrases:
        if phrase in lower:
            return phrase
    if _POLICY_OVERCLAIM.search(text):
        return "policy_overclaim"
    if merch and _MERCH_OVERCLAIM.search(text):
        return "merch_overclaim"
    if _PRIVATE_ECHO.search(text):
        return "private_data_echo"
    return None


def sanitize_draft_text(text: str) -> str:
    """Light cleanup: strip leading 'Draft' banners duplication; keep content."""
    cleaned = (text or "").strip()
    # Remove markdown fence wrappers if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:\w+)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_title_options(text: str) -> list[str]:
    """Extract 3–5 title candidates from model/template output."""
    cleaned = sanitize_draft_text(text)
    options: list[str] = []
    for match in _NUMBERED_LINE.finditer(cleaned):
        candidate = match.group(1).strip().strip("\"'`")
        candidate = re.sub(r"^\*\*?|\*\*?$", "", candidate).strip()
        if TITLE_MIN_LEN <= len(candidate) <= TITLE_MAX_LEN:
            options.append(candidate)
        if len(options) >= TITLE_OPTIONS_MAX:
            break
    if len(options) < TITLE_OPTIONS_MIN:
        # Fallback: split non-empty lines
        for line in cleaned.splitlines():
            line = line.strip().strip("\"'`")
            line = re.sub(r"^\d+[.)]\s*", "", line)
            line = re.sub(r"^[-*]\s*", "", line).strip()
            if TITLE_MIN_LEN <= len(line) <= TITLE_MAX_LEN and line.lower() not in {
                o.lower() for o in options
            }:
                # Skip instruction-y lines
                if line.lower().startswith(("task:", "based on", "draft", "1)", "2)")):
                    continue
                if "review before" in line.lower():
                    continue
                options.append(line)
            if len(options) >= TITLE_OPTIONS_MAX:
                break
    # Dedupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for o in options:
        key = o.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(o)
    return unique[:TITLE_OPTIONS_MAX]


def validate_title_options(options: list[str]) -> list[str]:
    valid: list[str] = []
    for opt in options:
        text = sanitize_draft_text(opt)
        if not (TITLE_MIN_LEN <= len(text) <= TITLE_MAX_LEN):
            continue
        banned = _contains_banned(text)
        if banned:
            continue
        valid.append(text)
    if len(valid) < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    return valid[:TITLE_OPTIONS_MAX]


def validate_description(text: str, *, merch: bool = False) -> str:
    cleaned = sanitize_draft_text(text)
    # Drop meta "Draft — review" prefixes from template fallback if they dominate
    lines = [ln for ln in cleaned.splitlines() if ln.strip()]
    if lines and lines[0].lower().startswith("[draft"):
        lines = lines[1:]
        cleaned = "\n".join(lines).strip()
    banned = _contains_banned(cleaned, merch=merch)
    if banned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI draft failed safety checks. You can keep editing manually.",
        )
    if len(cleaned) > DESCRIPTION_MAX_LEN:
        cleaned = cleaned[:DESCRIPTION_MAX_LEN].rstrip()
    if len(cleaned) < DESCRIPTION_MIN_LEN:
        # Soft pad with review note rather than hard-fail useful short drafts
        if len(cleaned) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI is unavailable right now. You can keep editing manually.",
            )
    return cleaned


def validate_merch_title_options(options: list[str]) -> list[str]:
    valid: list[str] = []
    for opt in options:
        text = sanitize_draft_text(opt)
        if not (TITLE_MIN_LEN <= len(text) <= TITLE_MAX_LEN):
            continue
        if _contains_banned(text, merch=True):
            continue
        valid.append(text)
    if len(valid) < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    return valid[:TITLE_OPTIONS_MAX]


def _normalize_category_token(token: str) -> str:
    return (
        token.strip()
        .lower()
        .replace("&", "and")
        .replace("/", " ")
        .replace("_", " ")
    )


def resolve_merch_category_slug(token: str) -> str | None:
    """Map label or slug to controlled merch category slug."""
    from app.merch.constants import MERCH_CATEGORY_LABELS, MERCH_CATEGORY_SLUGS

    raw = (token or "").strip().strip("\"'`").lower()
    if not raw:
        return None
    # Direct slug
    if raw in MERCH_CATEGORY_SLUGS:
        return raw
    # Label match
    norm = _normalize_category_token(raw)
    for slug, label in MERCH_CATEGORY_LABELS.items():
        if _normalize_category_token(label) == norm or slug.replace("_", " ") == norm:
            return slug
    # Soft aliases from product brief
    aliases = {
        "accessories": "other",
        "accessory": "other",
        "vouchers": "food_drink",
        "voucher": "food_drink",
        "food": "food_drink",
        "drink": "food_drink",
        "mask": "masks",
        "masks": "masks",
        "cap": "caps",
        "hat": "caps",
        "wristband": "wristbands",
        "poster": "posters",
        "bundle": "bundles",
        "digital item": "digital",
        "digital items": "digital",
        "collectible": "collectibles",
        "apparel": "apparel",
        "clothing": "apparel",
        "tee": "apparel",
        "t-shirt": "apparel",
        "tshirt": "apparel",
    }
    if norm in aliases:
        return aliases[norm]
    return None


def validate_merch_category(text: str) -> tuple[str, str]:
    """Return (slug, label) from model output constrained to catalog."""
    from app.merch.constants import MERCH_CATEGORY_LABELS

    cleaned = sanitize_draft_text(text)
    candidates: list[str] = []
    for match in _NUMBERED_LINE.finditer(cleaned):
        candidates.append(match.group(1))
    if not candidates:
        # First non-empty line / whole text
        for line in cleaned.splitlines():
            line = line.strip()
            if line and not line.lower().startswith(("task:", "draft", "catalog:")):
                candidates.append(line)
                break
        if not candidates and cleaned:
            candidates.append(cleaned.split(",")[0].split(":")[-1].strip())

    for cand in candidates:
        # Prefer "slug — label" or "slug: label"
        parts = re.split(r"[—\-:|]", cand, maxsplit=1)
        for part in parts:
            slug = resolve_merch_category_slug(part)
            if slug:
                return slug, MERCH_CATEGORY_LABELS.get(slug, slug)
        slug = resolve_merch_category_slug(cand)
        if slug:
            return slug, MERCH_CATEGORY_LABELS.get(slug, slug)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="AI draft failed safety checks. You can keep editing manually.",
    )


def validate_merch_tags(text: str) -> list[str]:
    from app.ai.constants import MERCH_TAG_MAX_COUNT, MERCH_TAG_MAX_LEN

    cleaned = sanitize_draft_text(text)
    raw_tags: list[str] = []
    for match in _NUMBERED_LINE.finditer(cleaned):
        raw_tags.append(match.group(1).strip())
    if not raw_tags:
        # Comma / line split
        blob = cleaned.replace("\n", ",")
        raw_tags = [p.strip() for p in blob.split(",") if p.strip()]

    tags: list[str] = []
    seen: set[str] = set()
    for tag in raw_tags:
        t = sanitize_draft_text(tag).strip("\"'`#").strip()
        t = re.sub(r"\s+", " ", t)
        if not t or len(t) > MERCH_TAG_MAX_LEN:
            continue
        if not _TAG_SAFE.match(t):
            continue
        if _contains_banned(t, merch=True):
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(t)
        if len(tags) >= MERCH_TAG_MAX_COUNT:
            break

    if not tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI draft failed safety checks. You can keep editing manually.",
        )
    return tags


SUPPORT_REPLY_BANNED = (
    "we have issued a refund",
    "refund has been processed",
    "payment is confirmed",
    "we guarantee",
    "we will suspend",
    "we will ban",
    "i have closed your ticket",
    "ticket is now closed",
    "as an ai",
    "internal note",
    "impersonation",
    "fraud playbook",
)

_SUPPORT_REPLY_OVERCLAIM = re.compile(
    r"(?i)\b(refund\s+(has\s+been|was)\s+(issued|processed|approved)|"
    r"payment\s+(is|was)\s+confirmed|"
    r"we\s+(will|have)\s+(ban|suspend|delete)\s+|"
    r"guaranteed\s+refund|legally\s+binding)\b"
)


def validate_support_category(text: str) -> tuple[str, str]:
    from app.support.constants import CATEGORIES, CATEGORY_LABELS

    cleaned = sanitize_draft_text(text)
    candidates: list[str] = []
    for match in _NUMBERED_LINE.finditer(cleaned):
        candidates.append(match.group(1))
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith(("category:", "suggested:", "slug:")):
            candidates.append(line.split(":", 1)[-1].strip())
        elif not low.startswith(("task:", "reason:", "catalog:")):
            candidates.append(line)
    if cleaned and not candidates:
        candidates.append(cleaned.split(",")[0])

    for cand in candidates:
        token = cand.strip().strip("\"'`").lower().replace(" ", "_").replace("/", "_")
        token = token.replace("-", "_")
        # Map common labels
        aliases = {
            "account/login": "account_login",
            "account_login": "account_login",
            "tickets/orders": "tickets_orders",
            "tickets_orders": "tickets_orders",
            "payments/refunds": "payments_refunds",
            "payments_refunds": "payments_refunds",
            "event_issue": "event_issue",
            "event issue": "event_issue",
            "host_issue": "host_issue",
            "host issue": "host_issue",
            "merch": "merch",
            "fan_connect": "fan_connect",
            "fan connect": "fan_connect",
            "messaging_abuse": "messaging_abuse",
            "messaging/report abuse": "messaging_abuse",
            "sponsorship": "sponsorship",
            "ambassador": "ambassador",
            "technical": "technical",
            "technical issue": "technical",
            "other": "other",
        }
        slug = aliases.get(token) or aliases.get(cand.strip().lower())
        if slug is None and token in CATEGORIES:
            slug = token
        if slug in CATEGORIES:
            return slug, CATEGORY_LABELS.get(slug, slug)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="AI draft failed safety checks. You can keep editing manually.",
    )


def validate_support_priority(text: str) -> tuple[str, str]:
    from app.support.constants import PRIORITIES

    cleaned = sanitize_draft_text(text)
    priority = ""
    reason = ""
    for line in cleaned.splitlines():
        low = line.lower().strip()
        if low.startswith("priority:"):
            priority = line.split(":", 1)[-1].strip().lower()
        elif low.startswith("reason:"):
            reason = line.split(":", 1)[-1].strip()
    if not priority:
        # First token that matches
        for p in PRIORITIES:
            if re.search(rf"\b{p}\b", cleaned, re.I):
                priority = p
                break
    priority = priority.replace(" ", "_")
    if priority not in PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI draft failed safety checks. You can keep editing manually.",
        )
    if not reason:
        # Remainder after priority word
        reason = "Based on ticket content — confirm before applying."
    if _contains_banned(reason) or _PRIVATE_ECHO.search(reason):
        reason = "Staff should confirm priority using ticket context."
    return priority, reason[:400]


def validate_support_summary(text: str) -> str:
    cleaned = sanitize_draft_text(text)
    if _PRIVATE_ECHO.search(cleaned) or _contains_banned(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI draft failed safety checks. You can keep editing manually.",
        )
    if len(cleaned) < 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    return cleaned[:4000]


def validate_support_reply(text: str) -> str:
    cleaned = sanitize_draft_text(text)
    lower = cleaned.lower()
    for phrase in SUPPORT_REPLY_BANNED:
        if phrase in lower:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI draft failed safety checks. You can keep editing manually.",
            )
    if _SUPPORT_REPLY_OVERCLAIM.search(cleaned) or _PRIVATE_ECHO.search(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI draft failed safety checks. You can keep editing manually.",
        )
    if _contains_banned(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI draft failed safety checks. You can keep editing manually.",
        )
    if len(cleaned) < 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    return cleaned[:4000]


def validate_support_articles(
    text: str, catalog: list[dict]
) -> list[dict]:
    """Return articles from catalog only (by slug or id)."""
    if not catalog:
        return []
    by_slug = {str(a.get("slug") or "").lower(): a for a in catalog}
    by_id = {str(a.get("id") or "").lower(): a for a in catalog}
    picked: list[dict] = []
    seen: set[str] = set()
    cleaned = sanitize_draft_text(text)
    if "no strong match" in cleaned.lower() or "no relevant" in cleaned.lower():
        return []
    tokens: list[str] = []
    for match in _NUMBERED_LINE.finditer(cleaned):
        tokens.append(match.group(1))
    tokens.extend(cleaned.replace(",", "\n").splitlines())
    for tok in tokens:
        raw = tok.strip().strip("\"'`")
        if not raw:
            continue
        # slug|title|id or bare slug
        parts = [p.strip() for p in re.split(r"[|—\-]", raw) if p.strip()]
        hit = None
        for part in parts:
            key = part.lower()
            if key in by_slug:
                hit = by_slug[key]
                break
            if key in by_id:
                hit = by_id[key]
                break
            # title contains
            for a in catalog:
                if (a.get("title") or "").lower() == key:
                    hit = a
                    break
            if hit:
                break
        if hit is None:
            continue
        sid = str(hit.get("id"))
        if sid in seen:
            continue
        seen.add(sid)
        picked.append(
            {
                "id": hit.get("id"),
                "slug": hit.get("slug"),
                "title": hit.get("title"),
                "path": hit.get("path") or f"/help/articles/{hit.get('slug')}",
            }
        )
        if len(picked) >= 5:
            break
    return picked


ADMIN_SUMMARY_BANNED = (
    "i have refunded",
    "refund approved",
    "payout sent",
    "user suspended",
    "account banned",
    "content hidden",
    "report rejected",
    "report approved",
    "automatically moderated",
    "i have closed",
    "ticket closed automatically",
    "finance updated",
    "as an ai i executed",
)

_ADMIN_DECISION_RE = re.compile(
    r"(?i)\b(auto[- ]?(approve|reject|suspend|ban|refund|payout|hide|feature)|"
    r"(refund|payout|suspension|ban)\s+(has\s+been|was)\s+(issued|processed|completed)|"
    r"i\s+(have|just)\s+(suspended|banned|refunded|hidden|approved|rejected))\b"
)


def validate_admin_summary(text: str) -> str:
    """Advisory admin summary — no automated decision language or private echoes."""
    cleaned = sanitize_draft_text(text)
    lower = cleaned.lower()
    for phrase in ADMIN_SUMMARY_BANNED:
        if phrase in lower:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI draft failed safety checks. You can keep editing manually.",
            )
    if (
        _ADMIN_DECISION_RE.search(cleaned)
        or _PRIVATE_ECHO.search(cleaned)
        or _contains_banned(cleaned)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI draft failed safety checks. You can keep editing manually.",
        )
    if len(cleaned) < 40:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    return cleaned[:5000]


BLOG_BANNED = BANNED_PHRASES + (
    "terms of service say",
    "privacy policy guarantees",
    "refund policy requires us to",
    "legally binding",
    "guaranteed safety",
    "100% safe",
    "we promise a refund",
    "auto-publish",
    "published automatically",
)

_BLOG_OVERCLAIM = re.compile(
    r"(?i)\b(guaranteed\s+(refund|payout|safety|attendance|sales)|"
    r"contradict(s|ing)?\s+(the\s+)?(terms|privacy|refund)|"
    r"auto[- ]?publish|"
    r"this\s+post\s+(has\s+been|is\s+now)\s+published)\b"
)

_SLUG_SAFE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _blog_fail() -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="AI draft failed safety checks. You can keep editing manually.",
    )


def _assert_blog_safe(text: str) -> str:
    cleaned = sanitize_draft_text(text)
    lower = cleaned.lower()
    for phrase in BLOG_BANNED:
        if phrase in lower:
            _blog_fail()
    if _BLOG_OVERCLAIM.search(cleaned) or _PRIVATE_ECHO.search(cleaned):
        _blog_fail()
    if _contains_banned(cleaned):
        _blog_fail()
    return cleaned


def validate_blog_title_options(options: list[str]) -> list[str]:
    from app.ai.constants import BLOG_TITLE_MAX_LEN, TITLE_OPTIONS_MAX, TITLE_OPTIONS_MIN

    out: list[str] = []
    seen: set[str] = set()
    for opt in options:
        t = _assert_blog_safe(opt).strip("\"'`")
        if not t or len(t) < 3 or len(t) > BLOG_TITLE_MAX_LEN:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= TITLE_OPTIONS_MAX:
            break
    if len(out) < TITLE_OPTIONS_MIN:
        _blog_fail()
    return out


def validate_blog_excerpt(text: str) -> str:
    from app.ai.constants import BLOG_EXCERPT_MAX_LEN

    cleaned = _assert_blog_safe(text)
    # Prefer first paragraph
    for line in cleaned.splitlines():
        line = line.strip()
        if line and not line.lower().startswith(("excerpt:", "draft:")):
            cleaned = line
            break
    if len(cleaned) < 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    return cleaned[:BLOG_EXCERPT_MAX_LEN]


def validate_blog_outline(text: str) -> str:
    cleaned = _assert_blog_safe(text)
    if len(cleaned) < 40:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    return cleaned[:6000]


def _slugify_blog(value: str) -> str:
    from app.ai.constants import BLOG_SLUG_MAX_LEN

    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:BLOG_SLUG_MAX_LEN] or "post"


def validate_blog_seo_meta(text: str) -> dict[str, str]:
    from app.ai.constants import (
        BLOG_META_DESC_MAX_LEN,
        BLOG_SEO_TITLE_MAX_LEN,
        BLOG_SLUG_MAX_LEN,
    )

    cleaned = _assert_blog_safe(text)
    seo_title = ""
    meta = ""
    slug = ""
    og = ""
    for line in cleaned.splitlines():
        low = line.lower().strip()
        if low.startswith(("seo title:", "title:")):
            seo_title = line.split(":", 1)[-1].strip()
        elif low.startswith(("meta description:", "description:", "meta:")):
            meta = line.split(":", 1)[-1].strip()
        elif low.startswith(("slug:", "suggested slug:")):
            slug = line.split(":", 1)[-1].strip()
        elif low.startswith(("og description:", "open graph:", "og:")):
            og = line.split(":", 1)[-1].strip()
    seo_title = _assert_blog_safe(seo_title)[:BLOG_SEO_TITLE_MAX_LEN]
    meta = _assert_blog_safe(meta)[:BLOG_META_DESC_MAX_LEN]
    if not seo_title or not meta:
        _blog_fail()
    slug = _slugify_blog(slug or seo_title)
    if not _SLUG_SAFE.match(slug) or len(slug) > BLOG_SLUG_MAX_LEN:
        _blog_fail()
    og = _assert_blog_safe(og or meta)[:BLOG_META_DESC_MAX_LEN]
    return {
        "seo_title": seo_title,
        "seo_description": meta,
        "suggested_slug": slug,
        "og_description": og,
    }


def validate_blog_tags(text: str, catalog: list[dict]) -> list[str]:
    from app.ai.constants import BLOG_TAG_MAX_COUNT

    if not catalog:
        return []
    by_slug = {str(t.get("slug") or "").lower(): t for t in catalog}
    by_name = {str(t.get("name") or "").lower(): t for t in catalog}
    cleaned = _assert_blog_safe(text)
    picked: list[str] = []
    seen: set[str] = set()
    tokens: list[str] = []
    for match in _NUMBERED_LINE.finditer(cleaned):
        tokens.append(match.group(1))
    tokens.extend(cleaned.replace(",", "\n").splitlines())
    for tok in tokens:
        raw = tok.strip().strip("\"'`#")
        if not raw:
            continue
        low = raw.lower().replace(" ", "-")
        hit = by_slug.get(low) or by_name.get(raw.lower())
        if hit is None:
            # try slugify
            hit = by_slug.get(_slugify_blog(raw))
        if hit is None:
            continue
        name = str(hit.get("name") or hit.get("slug") or "")
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        picked.append(name)
        if len(picked) >= BLOG_TAG_MAX_COUNT:
            break
    return picked


def validate_blog_social_snippets(text: str) -> dict[str, str]:
    cleaned = _assert_blog_safe(text)
    platforms = {
        "twitter": "",
        "instagram": "",
        "linkedin": "",
        "whatsapp": "",
    }
    aliases = {
        "x": "twitter",
        "x/twitter": "twitter",
        "twitter": "twitter",
        "instagram": "instagram",
        "ig": "instagram",
        "linkedin": "linkedin",
        "whatsapp": "whatsapp",
        "wa": "whatsapp",
    }
    current = None
    buffers: dict[str, list[str]] = {k: [] for k in platforms}
    for line in cleaned.splitlines():
        low = line.strip().lower()
        matched = None
        for alias, key in aliases.items():
            if low.startswith(f"{alias}:") or low.startswith(f"**{alias}**"):
                matched = key
                break
        if matched:
            current = matched
            rest = line.split(":", 1)[-1].strip() if ":" in line else ""
            if rest:
                buffers[current].append(rest)
            continue
        if current and line.strip():
            buffers[current].append(line.strip())
    out: dict[str, str] = {}
    for key, parts in buffers.items():
        blob = _assert_blog_safe(" ".join(parts)).strip()
        if blob:
            out[key] = blob[:500]
    if len(out) < 2:
        _blog_fail()
    return out


ANNOUNCEMENT_BANNED = BANNED_PHRASES + (
    "already sent",
    "we have sent",
    "has been sent",
    "message was delivered",
    "email has gone out",
    "limited time only",
    "act now or",
    "last chance",
    "only a few tickets left",
    "guaranteed entry",
    "your refund is approved",
    "we will refund you",
    "discount ends tonight",
    "free ticket if you",
)

_ANNOUNCEMENT_SENT_CLAIM = re.compile(
    r"(?i)\b(already\s+sent|has\s+been\s+sent|we\s+(?:have\s+)?sent|"
    r"delivered\s+to\s+(?:your|all)|message\s+went\s+out|"
    r"this\s+announcement\s+was\s+sent)\b"
)


def _announcement_fail() -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="AI announcement draft failed safety checks. Edit manually.",
    )


def _assert_announcement_safe(text: str) -> str:
    cleaned = sanitize_draft_text(text)
    lower = cleaned.lower()
    for phrase in ANNOUNCEMENT_BANNED:
        if phrase in lower:
            _announcement_fail()
    if _ANNOUNCEMENT_SENT_CLAIM.search(cleaned) or _PRIVATE_ECHO.search(cleaned):
        _announcement_fail()
    if _contains_banned(cleaned):
        _announcement_fail()
    return cleaned


def _join_announcement_section_lines(lines: list[str]) -> str:
    """Rebuild section text, keeping blank lines as paragraph breaks."""
    if not lines:
        return ""
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if line:
            current.append(line)
            continue
        if current:
            paragraphs.append("\n".join(current))
            current = []
    if current:
        paragraphs.append("\n".join(current))
    return "\n\n".join(paragraphs).strip()


def validate_host_announcement_draft(text: str) -> dict[str, str]:
    """Parse SUBJECT / EMAIL_BODY / WHATSAPP sections from model output."""
    cleaned = _assert_announcement_safe(text)
    subject = ""
    email_body = ""
    whatsapp = ""
    section: str | None = None
    email_lines: list[str] = []
    wa_lines: list[str] = []

    for line in cleaned.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("subject:"):
            subject = _assert_announcement_safe(stripped.split(":", 1)[-1].strip())
            section = None
            continue
        if low.startswith("email_body:") or low.startswith("email body:"):
            rest = stripped.split(":", 1)[-1].strip()
            section = "email"
            if rest:
                email_lines.append(rest)
            continue
        if low.startswith("whatsapp:") or low.startswith("whatsapp body:"):
            rest = stripped.split(":", 1)[-1].strip()
            section = "whatsapp"
            if rest:
                wa_lines.append(rest)
            continue
        if section == "email":
            # Keep blank lines so EMAIL_BODY paragraphs survive apply/send.
            email_lines.append(stripped)
        elif section == "whatsapp":
            wa_lines.append(stripped)

    email_body = _assert_announcement_safe(_join_announcement_section_lines(email_lines))
    whatsapp = _assert_announcement_safe(_join_announcement_section_lines(wa_lines))

    if not subject or len(subject) < 3:
        # Fallback: first non-empty line as subject, rest as body
        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
        if lines:
            subject = _assert_announcement_safe(lines[0][:120])
            email_body = _assert_announcement_safe("\n".join(lines[1:]).strip())
    if not email_body or len(email_body) < 5:
        _announcement_fail()

    if whatsapp and len(whatsapp) > 500:
        whatsapp = whatsapp[:500]

    return {
        "announcement_subject": subject,
        "announcement_email_body": email_body,
        "announcement_whatsapp_body": whatsapp,
    }


SPONSORSHIP_BANNED = BANNED_PHRASES + (
    "guaranteed roi",
    "guaranteed return",
    "pàdéyá endorses",
    "padeya endorses",
    "official endorsement from pàdéyá",
    "official endorsement from padeya",
    "pàdéyá guarantees",
    "guaranteed sponsorship",
    "guaranteed placement",
    "we guarantee sales",
    "guaranteed attendance",
    "already sent",
    "message has been sent",
    "approved your sponsorship",
    "sponsorship is confirmed",
)

_SPONSORSHIP_ENDORSE = re.compile(
    r"(?i)\b(pàdéyá|padeya)\s+(?:officially\s+)?(?:endorses|recommends|guarantees)\b"
)


def _sponsorship_fail() -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="AI sponsorship pitch failed safety checks. Edit manually.",
    )


def _assert_sponsorship_safe(text: str) -> str:
    cleaned = sanitize_draft_text(text)
    lower = cleaned.lower()
    for phrase in SPONSORSHIP_BANNED:
        if phrase in lower:
            _sponsorship_fail()
    if _SPONSORSHIP_ENDORSE.search(cleaned) or _PRIVATE_ECHO.search(cleaned):
        _sponsorship_fail()
    if _contains_banned(cleaned):
        _sponsorship_fail()
    return cleaned


def _parse_section_block(cleaned: str, header: str) -> str:
    """Extract lines after a HEADER: line until the next known header."""
    headers = (
        "pitch_title:",
        "short_pitch:",
        "value_bullets:",
        "audience_summary:",
        "package_wording:",
        "follow_up:",
    )
    lines = cleaned.splitlines()
    capture = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith(header):
            capture = True
            rest = stripped.split(":", 1)[-1].strip()
            if rest:
                out.append(rest)
            continue
        if capture:
            if any(low.startswith(h) for h in headers if h != header):
                break
            if stripped:
                out.append(stripped)
    return _assert_sponsorship_safe("\n".join(out).strip())


def validate_host_sponsorship_pitch(text: str) -> dict[str, str]:
    cleaned = _assert_sponsorship_safe(text)
    pitch_title = _parse_section_block(cleaned, "pitch_title:")
    short_pitch = _parse_section_block(cleaned, "short_pitch:")
    value_bullets = _parse_section_block(cleaned, "value_bullets:")
    audience_summary = _parse_section_block(cleaned, "audience_summary:")
    package_wording = _parse_section_block(cleaned, "package_wording:")
    follow_up = _parse_section_block(cleaned, "follow_up:")

    if not short_pitch or len(short_pitch) < 20:
        _sponsorship_fail()
    if not pitch_title:
        pitch_title = short_pitch.split(".")[0][:120]
    pitch_title = _assert_sponsorship_safe(pitch_title[:160])
    short_pitch = _assert_sponsorship_safe(short_pitch[:4000])
    if value_bullets:
        value_bullets = _assert_sponsorship_safe(value_bullets[:2000])
    if audience_summary:
        audience_summary = _assert_sponsorship_safe(audience_summary[:2000])
    if package_wording:
        package_wording = _assert_sponsorship_safe(package_wording[:2000])
    if follow_up:
        follow_up = _assert_sponsorship_safe(follow_up[:1000])

    return {
        "sponsorship_pitch_title": pitch_title,
        "sponsorship_short_pitch": short_pitch,
        "sponsorship_value_bullets": value_bullets,
        "sponsorship_audience_summary": audience_summary,
        "sponsorship_package_wording": package_wording,
        "sponsorship_follow_up_message": follow_up,
    }


PASSPORT_BIO_BANNED = BANNED_PHRASES + (
    "checked in to",
    "i've attended",
    "i have attended",
    "vip table",
    "spent over",
    "total spend",
    "ticket holder for",
    "verified attendee",
    "guaranteed entry",
    "official pàdéyá ambassador",
    "official padeya ambassador",
)

_PASSPORT_INFERENCE = re.compile(
    r"(?i)\b(vip|table\s+spend|total\s+spend|spent\s+\$|spent\s+₦|"
    r"attended\s+\d+\s+events|checked\s+in\s+\d+|buyer\s+of)\b"
)


def _passport_bio_fail() -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="AI bio draft failed safety checks. Edit manually.",
    )


def _assert_passport_bio_safe(text: str) -> str:
    cleaned = sanitize_draft_text(text)
    lower = cleaned.lower()
    for phrase in PASSPORT_BIO_BANNED:
        if phrase in lower:
            _passport_bio_fail()
    if _PASSPORT_INFERENCE.search(cleaned) or _PRIVATE_ECHO.search(cleaned):
        _passport_bio_fail()
    if _contains_banned(cleaned):
        _passport_bio_fail()
    return cleaned


def validate_fan_passport_bio(text: str) -> dict[str, object]:
    from app.ai.constants import (
        PASSPORT_BIO_MAX_LEN,
        PASSPORT_BIO_MIN_LEN,
        PASSPORT_BIO_OPTIONS_MAX,
        PASSPORT_BIO_OPTIONS_MIN,
    )

    cleaned = sanitize_draft_text(text)
    chunks = re.split(r"(?m)^\s*\d+[.)]\s*", cleaned)
    options_raw = [c.strip() for c in chunks if c.strip()]
    if len(options_raw) <= 1:
        options_raw = parse_title_options(cleaned)
    valid: list[str] = []
    for opt in options_raw:
        blob = _assert_passport_bio_safe(opt)
        if len(blob) > PASSPORT_BIO_MAX_LEN:
            blob = blob[:PASSPORT_BIO_MAX_LEN].rstrip()
        if len(blob) < PASSPORT_BIO_MIN_LEN:
            continue
        valid.append(blob)
    if len(valid) < PASSPORT_BIO_OPTIONS_MIN:
        blob = _assert_passport_bio_safe(cleaned)
        if PASSPORT_BIO_MIN_LEN <= len(blob) <= PASSPORT_BIO_MAX_LEN:
            valid = [blob]
    if len(valid) < 1:
        _passport_bio_fail()
    valid = valid[:PASSPORT_BIO_OPTIONS_MAX]
    suggestion = "\n\n".join(f"{i + 1}. {o}" for i, o in enumerate(valid))
    return {"suggestion": suggestion, "options": valid}

