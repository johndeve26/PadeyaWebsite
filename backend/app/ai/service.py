"""AI Copilot orchestration — suggestions only; no finance or publish side effects."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.constants import (
    ADMIN_FEATURES,
    ADMIN_SUMMARY_DISCLAIMER,
    ADMIN_SUMMARY_FEATURES,
    ANNOUNCEMENT_DRAFT_DISCLAIMER,
    ANNOUNCEMENT_FEATURES,
    BLOG_DRAFT_DISCLAIMER,
    BLOG_FEATURES,
    DRAFT_DISCLAIMER,
    FEATURE_ADMIN_BLOG_EXCERPT,
    FEATURE_ADMIN_BLOG_OUTLINE,
    FEATURE_ADMIN_BLOG_SEO,
    FEATURE_ADMIN_BLOG_SOCIAL,
    FEATURE_ADMIN_BLOG_TAGS,
    FEATURE_ADMIN_BLOG_TITLE,
    FEATURE_ADMIN_DAILY_OPS,
    FEATURE_ADMIN_REPORTS_SUMMARY,
    FEATURE_ADMIN_REVENUE_SUMMARY,
    FEATURE_ADMIN_SUPPORT_QUEUE,
    FEATURE_HOST_EVENT_DESCRIPTION,
    FEATURE_HOST_EVENT_TITLE,
    FEATURE_HOST_MERCH_CATEGORY,
    FEATURE_HOST_MERCH_DESCRIPTION,
    FEATURE_HOST_MERCH_TAGS,
    FEATURE_HOST_MERCH_TITLE,
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
    FEATURE_HOST_SPONSORSHIP_PITCH,
    FEATURE_FAN_PASSPORT_BIO,
    FEATURE_LABELS,
    FEATURE_SUPPORT_ARTICLES,
    FEATURE_SUPPORT_PRIORITY,
    FEATURE_SUPPORT_REPLY_DRAFT,
    FEATURE_SUPPORT_SUMMARY,
    FEATURE_SUPPORT_TRIAGE,
    FEATURE_TEMPLATE_SLUG,
    HOST_FEATURES,
    HOST_FEATURES_PUBLIC,
    PASSPORT_DRAFT_DISCLAIMER,
    PASSPORT_FEATURES,
    SPONSORSHIP_DRAFT_DISCLAIMER,
    SPONSORSHIP_FEATURES,
    FAN_FEATURES,
    FAN_FEATURES_PUBLIC,
    SUPPORT_DRAFT_DISCLAIMER,
    SUPPORT_FEATURES,
)
from app.ai.context_scrubber import (
    scrub_context,
    scrub_event_studio_context,
    scrub_merch_studio_context,
    scrub_prompt_text,
    venue_allowed_for_ai,
)
from app.ai.feature_toggles import (
    assert_ai_globally_available,
    assert_feature_enabled,
    canonicalize_feature,
    feature_requires_human_review,
    is_feature_enabled,
)
from app.ai.models import AIPromptTemplate, AIUsageLog
from app.ai.output_validation import (
    parse_title_options,
    validate_admin_summary,
    validate_blog_excerpt,
    validate_blog_outline,
    validate_blog_seo_meta,
    validate_blog_social_snippets,
    validate_blog_tags,
    validate_blog_title_options,
    validate_description,
    validate_host_announcement_draft,
    validate_host_sponsorship_pitch,
    validate_fan_passport_bio,
    validate_merch_category,
    validate_merch_tags,
    validate_merch_title_options,
    validate_support_articles,
    validate_support_category,
    validate_support_priority,
    validate_support_reply,
    validate_support_summary,
    validate_title_options,
)
from app.ai.prompts import render_prompt
from app.ai.providers import get_ai_provider
from app.ai.schemas import AIGenerateRequest, AIGenerationFeedbackRequest
from app.ai.seed import seed_ai_prompt_templates
from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.events.models import Event, TicketType
from app.hosts.service import require_actor_host
from app.users.models import User
from app.users.service import user_has_permission

# Rough USD micros per 1K tokens when provider omits cost (gpt-4o-mini-ish)
_EST_COST_IN_MICROS_PER_1K = 150  # $0.00015
_EST_COST_OUT_MICROS_PER_1K = 600  # $0.00060


MERCH_FEATURES = frozenset(
    {
        FEATURE_HOST_MERCH_TITLE,
        FEATURE_HOST_MERCH_DESCRIPTION,
        FEATURE_HOST_MERCH_CATEGORY,
        FEATURE_HOST_MERCH_TAGS,
    }
)

EVENT_COPY_FEATURES = frozenset(
    {FEATURE_HOST_EVENT_TITLE, FEATURE_HOST_EVENT_DESCRIPTION}
)


def _host_permission_for_ai_feature(feature: str) -> str | tuple[str, ...]:
    if feature in ANNOUNCEMENT_FEATURES:
        return (
            "announcements.create",
            "announcements.update_draft",
            "events.create",
            "events.manage_own",
        )
    if feature in SPONSORSHIP_FEATURES:
        return "sponsorships.manage"
    if feature in MERCH_FEATURES:
        return ("merch.manage_own", "merch.create")
    if feature in EVENT_COPY_FEATURES:
        return ("events.manage_own", "events.create", "events.update_own")
    return ("events.read_own", "events.manage_own", "events.create")


def assert_host_ai_actor(
    db: Session,
    user: User,
    *,
    feature: str | None = None,
) -> None:
    """Host owners (ai.use_own), admins, or active-workspace team with host ops."""
    if user_has_permission(user, "ai.use_own") or user_has_permission(
        user, "admin.full_access"
    ):
        return
    perm: str | tuple[str, ...]
    if feature:
        perm = _host_permission_for_ai_feature(feature)
    else:
        perm = (
            "announcements.create",
            "events.create",
            "events.manage_own",
            "events.read_own",
        )
    try:
        require_actor_host(db, user, permission=perm)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="AI permission required",
            ) from exc
        raise


def ensure_templates(db: Session) -> None:
    count = db.scalar(select(func.count()).select_from(AIPromptTemplate)) or 0
    if int(count) == 0:
        seed_ai_prompt_templates(db)
        return
    # Ensure Phase 1 canonical templates exist even on older DBs
    needed = (
        FEATURE_HOST_EVENT_TITLE,
        FEATURE_HOST_EVENT_DESCRIPTION,
        FEATURE_HOST_MERCH_TITLE,
        FEATURE_HOST_MERCH_DESCRIPTION,
        FEATURE_HOST_MERCH_CATEGORY,
        FEATURE_HOST_MERCH_TAGS,
        FEATURE_SUPPORT_SUMMARY,
        FEATURE_SUPPORT_TRIAGE,
        FEATURE_SUPPORT_PRIORITY,
        FEATURE_SUPPORT_REPLY_DRAFT,
        FEATURE_SUPPORT_ARTICLES,
        FEATURE_ADMIN_SUPPORT_QUEUE,
        FEATURE_ADMIN_REVENUE_SUMMARY,
        FEATURE_ADMIN_REPORTS_SUMMARY,
        FEATURE_ADMIN_DAILY_OPS,
        FEATURE_ADMIN_BLOG_TITLE,
        FEATURE_ADMIN_BLOG_OUTLINE,
        FEATURE_ADMIN_BLOG_EXCERPT,
        FEATURE_ADMIN_BLOG_SEO,
        FEATURE_ADMIN_BLOG_SOCIAL,
        FEATURE_ADMIN_BLOG_TAGS,
        FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
        FEATURE_HOST_SPONSORSHIP_PITCH,
        FEATURE_FAN_PASSPORT_BIO,
    )
    for slug in needed:
        exists = db.scalar(
            select(AIPromptTemplate.id).where(AIPromptTemplate.slug == slug)
        )
        if exists is None:
            seed_ai_prompt_templates(db)
            break


def list_features(audience: str, db: Session | None = None) -> list[dict]:
    if audience == "host":
        keys = HOST_FEATURES_PUBLIC
    elif audience == "fan":
        keys = FAN_FEATURES_PUBLIC
    else:
        keys = ADMIN_FEATURES
    return [
        {
            "key": k,
            "label": FEATURE_LABELS.get(k, k),
            "audience": audience,
            "enabled": is_feature_enabled(k, db=db),
        }
        for k in keys
    ]


def ai_status(db: Session | None = None) -> dict:
    import os

    from app.ai.runtime_config import resolve_ai_settings

    settings = resolve_ai_settings(db) if db is not None else get_settings()
    kill = (os.environ.get("AI_KILL_SWITCH") or "").strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
    }
    return {
        "enabled": bool(settings.ai_enabled) and not kill,
        "provider": settings.ai_provider,
        "model": settings.ai_model,
        "rate_limit_per_hour": settings.ai_rate_limit_per_hour,
        "kill_switch": kill,
        "disabled_by_environment": kill,
        "ai_enabled_setting": bool(settings.ai_enabled),
        "status_label": (
            "Disabled by environment"
            if kill
            else ("Enabled" if settings.ai_enabled else "Disabled")
        ),
    }


def _check_rate_limit(db: Session, user_id: UUID) -> None:
    from app.ai.runtime_config import resolve_ai_settings

    settings = resolve_ai_settings(db)
    limit = settings.ai_rate_limit_per_hour
    if limit <= 0:
        return
    since = datetime.now(UTC) - timedelta(hours=1)
    count = int(
        db.scalar(
            select(func.count())
            .select_from(AIUsageLog)
            .where(AIUsageLog.user_id == user_id, AIUsageLog.created_at >= since)
        )
        or 0
    )
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI rate limit reached. You can keep editing manually.",
        )


def _estimate_cost_micros(tokens_in: int | None, tokens_out: int | None) -> int | None:
    if tokens_in is None and tokens_out is None:
        return None
    tin = int(tokens_in or 0)
    tout = int(tokens_out or 0)
    return int(
        (tin * _EST_COST_IN_MICROS_PER_1K + tout * _EST_COST_OUT_MICROS_PER_1K) / 1000
    )


def _get_template(db: Session, feature: str, audience: str) -> AIPromptTemplate:
    ensure_templates(db)
    slug = FEATURE_TEMPLATE_SLUG.get(feature, feature)
    row = db.scalar(
        select(AIPromptTemplate).where(
            AIPromptTemplate.slug == slug,
            AIPromptTemplate.audience == audience,
            AIPromptTemplate.is_active.is_(True),
        )
    )
    if row is None and slug != feature:
        row = db.scalar(
            select(AIPromptTemplate).where(
                AIPromptTemplate.slug == feature,
                AIPromptTemplate.audience == audience,
                AIPromptTemplate.is_active.is_(True),
            )
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return row


def _safe_ticket_tier_names(db: Session, event_id: UUID) -> str:
    tiers = db.scalars(select(TicketType).where(TicketType.event_id == event_id)).all()
    names = [t.name for t in tiers if t.name]
    return ", ".join(names) or "none"


def _event_studio_context_from_event(db: Session, event: Event) -> dict[str, str]:
    visibility = getattr(event, "location_visibility", None) or "full_public"
    venue = ""
    if venue_allowed_for_ai(visibility):
        venue = event.venue_name or ""
    return {
        "title": event.title or "",
        "city": event.city or "",
        "area": getattr(event, "area", None) or "",
        "venue": venue,
        "category": event.category.name if event.category else "",
        "date": event.start_datetime.isoformat() if event.start_datetime else "",
        "capacity": str(event.capacity or ""),
        "ticket_tiers": _safe_ticket_tier_names(db, event.id),
        "vibe": (event.description or "")[:240],
        "short_tagline": getattr(event, "short_tagline", None) or "",
        "location_visibility": visibility,
        "notes": "",
    }


def _event_context(db: Session, event: Event) -> dict[str, str]:
    """Privacy-aware event context — venue only when public; tier names only."""
    base = _event_studio_context_from_event(db, event)
    # location_visibility is for scrubbing decisions, not model content
    return base


def _admin_context(db: Session, feature: str) -> dict[str, str]:
    ctx: dict[str, str] = {
        "support_snapshot": "",
        "reports_snapshot": "",
        "revenue_snapshot": "",
        "top_events": "",
        "risk_signals": "placeholder — no automated risk model",
        "fraud_signals": "placeholder — fraud signals not wired",
        "notes": "",
        "range_label": "",
        "operations_snapshot": "",
        "top_hosts": "",
        "category_trends": "",
        "suggested_review_links": "",
    }
    try:
        from app.analytics.aggregations import (
            build_admin_platform_summary,
            build_admin_revenue,
            build_admin_support,
            resolve_range,
        )

        start, end = resolve_range()
        ctx["range_label"] = f"{start.isoformat()} → {end.isoformat()}"
        if feature in {
            "summarize_support_complaints",
            FEATURE_ADMIN_SUPPORT_QUEUE,
        }:
            ctx["support_snapshot"] = json.dumps(
                build_admin_support(db), default=str
            )[:2000]
        if feature in {"explain_revenue_trends", FEATURE_ADMIN_REVENUE_SUMMARY}:
            ctx["revenue_snapshot"] = json.dumps(
                build_admin_revenue(db, range_start=start, range_end=end), default=str
            )[:2000]
        if feature in {"recommend_featured_events"}:
            summary = build_admin_platform_summary(
                db, range_start=start, range_end=end
            )
            ctx["top_events"] = json.dumps(summary.get("top_events") or [], default=str)[
                :2000
            ]
        if feature in {"identify_high_risk_hosts", "fraud_risk_summary"}:
            summary = build_admin_platform_summary(
                db, range_start=start, range_end=end
            )
            ctx["fraud_signals"] = json.dumps(
                summary.get("fraud_signals") or [], default=str
            )
            ctx["risk_signals"] = ctx["fraud_signals"]
    except Exception:
        pass

    if feature in {"summarize_review_reports", FEATURE_ADMIN_REPORTS_SUMMARY}:
        try:
            from app.reviews.models import ReviewReport, VerifiedReview

            reports = db.scalars(
                select(ReviewReport)
                .where(ReviewReport.status == "open")
                .order_by(ReviewReport.created_at.desc())
                .limit(20)
            ).all()
            rows = []
            for r in reports:
                review = db.get(VerifiedReview, r.review_id)
                rows.append(
                    {
                        "reason": r.reason,
                        "rating": review.rating if review else None,
                        "title": review.title if review else None,
                    }
                )
            ctx["reports_snapshot"] = json.dumps(rows, default=str)[:2000]
        except Exception:
            ctx["reports_snapshot"] = "[]"

    return ctx


def _catalog_categories_text() -> str:
    from app.merch.constants import MERCH_CATEGORY_LABELS, MERCH_CATEGORY_SLUGS

    return ", ".join(
        f"{slug} ({MERCH_CATEGORY_LABELS.get(slug, slug)})"
        for slug in MERCH_CATEGORY_SLUGS
    )


def _public_event_merch_bits(db: Session, event: Event) -> dict[str, str]:
    visibility = getattr(event, "location_visibility", None) or "full_public"
    city = ""
    # Coarse public place only — never private venue street
    if visibility in {"full_public", "area_only"}:
        city = event.city or ""
    category = ""
    try:
        if event.category is not None:
            category = event.category.name or ""
    except Exception:
        category = ""
    return {
        "event_title": event.title or "",
        "event_city": city,
        "event_category": category,
        "event_date": event.start_datetime.isoformat() if event.start_datetime else "",
        "location_visibility": visibility,
    }


def _merch_context_defaults() -> dict[str, str]:
    return {
        "title": "",
        "name": "",
        "notes": "",
        "description": "",
        "short_description": "",
        "product_type": "",
        "merch_kind": "",
        "marketplace_kind": "",
        "event_title": "",
        "event_category": "",
        "event_city": "",
        "event_date": "",
        "host_name": "",
        "audience_label": "",
        "fulfillment_label": "",
        "limited_stock": "no",
        "catalog_categories": _catalog_categories_text(),
        "existing_category": "",
        "existing_tags": "",
    }


def _build_context(
    db: Session,
    *,
    user: User,
    audience: str,
    feature: str,
    payload: AIGenerateRequest,
) -> tuple[dict[str, str], UUID | None, list[str], dict]:
    context: dict[str, str] = {
        "notes": (payload.notes or "").strip(),
        "title": "",
        "city": "",
        "area": "",
        "venue": "",
        "category": "",
        "date": "",
        "capacity": "",
        "ticket_tiers": "",
        "vibe": "",
        "short_tagline": "",
        "metrics": "",
        "current_tier": "",
        "next_tier": "",
        "progress": "",
        "requirements_remaining": "",
        "suggested_actions": "",
        "support_snapshot": "",
        "reports_snapshot": "",
        "revenue_snapshot": "",
        "top_events": "",
        "risk_signals": "",
        "fraud_signals": "",
    }
    host_id: UUID | None = None
    redactions: list[str] = []
    location_visibility = "full_public"

    # Client-provided studio draft fields (create flow may have no event_id)
    client_extra: dict[str, object] = {}
    if payload.extra:
        for k, v in payload.extra.items():
            if isinstance(k, str):
                client_extra[k] = v

    if audience == "fan":
        if feature in PASSPORT_FEATURES:
            from app.ai.passport_context import build_fan_passport_bio_context

            scrubbed, redactions = build_fan_passport_bio_context(
                db,
                user=user,
                notes=payload.notes,
                extra=client_extra,
            )
            context.update(scrubbed)
            return context, None, redactions, {}
        raise HTTPException(status_code=400, detail="Unknown AI feature")

    if audience == "host":
        if feature in ANNOUNCEMENT_FEATURES:
            from app.ai.announcements_context import build_host_announcement_context

            built = build_host_announcement_context(
                db,
                user=user,
                event_id=payload.event_id,
                notes=payload.notes,
                extra=client_extra,
            )
            context.update(built.scrubbed_context)
            return context, built.host_id, built.redactions, {}
        host = require_actor_host(
            db, user, permission=_host_permission_for_ai_feature(feature)
        )
        host_id = host.id
        if feature in SPONSORSHIP_FEATURES:
            from app.ai.sponsorship_context import build_host_sponsorship_context

            scrubbed, redactions, host_id = build_host_sponsorship_context(
                db,
                user=user,
                notes=payload.notes,
                extra=client_extra,
            )
            context.update(scrubbed)
            return context, host_id, redactions, {}
        if payload.event_id is not None:
            event = db.get(Event, payload.event_id)
            if event is None or event.host_id != host.id:
                raise HTTPException(status_code=404, detail="Event not found")
            if feature in MERCH_FEATURES:
                context.update(_public_event_merch_bits(db, event))
                location_visibility = context.get("location_visibility") or "full_public"
            else:
                event_ctx = _event_context(db, event)
                context.update(event_ctx)
                location_visibility = event_ctx.get("location_visibility") or getattr(
                    event, "location_visibility", None
                ) or "full_public"

        if feature in MERCH_FEATURES:
            merged = {
                **_merch_context_defaults(),
                "host_name": host.display_name or "",
                **{k: context.get(k, "") for k in _merch_context_defaults()},
                **client_extra,
                "notes": (
                    payload.notes
                    or client_extra.get("notes")
                    or context.get("notes")
                    or ""
                ),
                "title": str(
                    client_extra.get("title")
                    or client_extra.get("name")
                    or context.get("title")
                    or ""
                ),
                "location_visibility": client_extra.get(
                    "location_visibility", location_visibility
                ),
                "catalog_categories": _catalog_categories_text(),
            }
            # Never trust client host_name over server
            merged["host_name"] = host.display_name or ""
            scrubbed, redactions = scrub_merch_studio_context(merged)
            context.update(scrubbed)
            for key in _merch_context_defaults():
                context.setdefault(key, "")
            context["catalog_categories"] = _catalog_categories_text()
            context["host_name"] = host.display_name or ""
        elif feature in EVENT_COPY_FEATURES:
            merged = {
                **{k: context.get(k, "") for k in (
                    "title",
                    "notes",
                    "city",
                    "area",
                    "category",
                    "vibe",
                    "date",
                    "capacity",
                    "ticket_tiers",
                    "short_tagline",
                    "venue",
                )},
                **client_extra,
                "notes": (payload.notes or client_extra.get("notes") or context.get("notes") or ""),
                "location_visibility": client_extra.get(
                    "location_visibility", location_visibility
                ),
            }
            scrubbed, redactions = scrub_event_studio_context(merged)
            context.update(scrubbed)
            for key in (
                "title",
                "notes",
                "city",
                "area",
                "category",
                "vibe",
                "date",
                "capacity",
                "ticket_tiers",
                "venue",
            ):
                context.setdefault(key, "")
        else:
            # General host features: scrub extra + event context
            if client_extra:
                for k, v in client_extra.items():
                    context[k] = str(v) if v is not None else ""
            scrubbed, redactions = scrub_context(
                context, location_visibility=location_visibility
            )
            context.update(scrubbed)

        return context, host_id, redactions, {}

    # Admin / staff audience
    extras: dict = {}
    if feature in SUPPORT_FEATURES:
        from app.ai.support_context import (
            assert_support_reply_permission,
            build_support_ticket_context,
        )

        if payload.support_ticket_id is None:
            raise HTTPException(
                status_code=400, detail="support_ticket_id is required"
            )
        if feature == FEATURE_SUPPORT_REPLY_DRAFT:
            assert_support_reply_permission(user)
        scrubbed, redactions, articles = build_support_ticket_context(
            db, user=user, ticket_id=payload.support_ticket_id
        )
        context.update(scrubbed)
        extras["article_catalog"] = articles
        extras["support_ticket_id"] = str(payload.support_ticket_id)
        return context, None, redactions, extras

    if feature in ADMIN_SUMMARY_FEATURES:
        from app.ai.admin_context import build_admin_summary_context

        scrubbed, redactions = build_admin_summary_context(
            db,
            user=user,
            feature=feature,
            notes=payload.notes or "",
        )
        context.update(scrubbed)
        extras["resource_scope"] = feature
        return context, None, redactions, extras

    if feature in BLOG_FEATURES:
        from app.ai.blog_context import build_blog_studio_context
        from app.blog.service import list_tags

        scrubbed, redactions = build_blog_studio_context(
            db,
            user=user,
            blog_post_id=payload.blog_post_id,
            extra=client_extra,
            notes=payload.notes or "",
        )
        context.update(scrubbed)
        extras["blog_post_id"] = (
            str(payload.blog_post_id) if payload.blog_post_id else None
        )
        extras["tag_catalog"] = [
            {"id": str(t.id), "slug": t.slug, "name": t.name}
            for t in list_tags(db)
        ]
        return context, None, redactions, extras

    context.update(_admin_context(db, feature))
    scrubbed, redactions = scrub_context(context)
    context.update(scrubbed)
    return context, host_id, redactions, extras


def _empty_validated(**overrides: object) -> dict:
    base = {
        "suggestion": "",
        "options": None,
        "category_slug": None,
        "tags": None,
        "priority": None,
        "priority_reason": None,
        "articles": None,
        "seo_title": None,
        "seo_description": None,
        "suggested_slug": None,
        "og_description": None,
        "social_snippets": None,
        "announcement_subject": None,
        "announcement_email_body": None,
        "announcement_whatsapp_body": None,
        "sponsorship_pitch_title": None,
        "sponsorship_short_pitch": None,
        "sponsorship_value_bullets": None,
        "sponsorship_audience_summary": None,
        "sponsorship_package_wording": None,
        "sponsorship_follow_up_message": None,
    }
    base.update(overrides)
    return base


def _validate_output(
    feature: str,
    text: str,
    *,
    article_catalog: list[dict] | None = None,
    tag_catalog: list[dict] | None = None,
) -> dict:
    """Return validated draft fields for the response."""
    if feature == FEATURE_HOST_EVENT_TITLE:
        options = validate_title_options(parse_title_options(text))
        suggestion = "\n".join(f"{i}. {o}" for i, o in enumerate(options, start=1))
        return _empty_validated(suggestion=suggestion, options=options)
    if feature == FEATURE_HOST_EVENT_DESCRIPTION:
        return _empty_validated(suggestion=validate_description(text))
    if feature == FEATURE_HOST_MERCH_TITLE:
        options = validate_merch_title_options(parse_title_options(text))
        suggestion = "\n".join(f"{i}. {o}" for i, o in enumerate(options, start=1))
        return _empty_validated(suggestion=suggestion, options=options)
    if feature == FEATURE_HOST_MERCH_DESCRIPTION:
        return _empty_validated(suggestion=validate_description(text, merch=True))
    if feature == FEATURE_HOST_MERCH_CATEGORY:
        slug, label = validate_merch_category(text)
        return _empty_validated(suggestion=label, options=[label], category_slug=slug)
    if feature == FEATURE_HOST_MERCH_TAGS:
        tags = validate_merch_tags(text)
        suggestion = "\n".join(f"{i}. {t}" for i, t in enumerate(tags, start=1))
        return _empty_validated(suggestion=suggestion, options=tags, tags=tags)
    if feature == FEATURE_HOST_ANNOUNCEMENTS_DRAFT:
        parts = validate_host_announcement_draft(text)
        suggestion = (
            f"SUBJECT: {parts['announcement_subject']}\n\n"
            f"{parts['announcement_email_body']}"
        )
        return _empty_validated(suggestion=suggestion, **parts)
    if feature == FEATURE_HOST_SPONSORSHIP_PITCH:
        parts = validate_host_sponsorship_pitch(text)
        suggestion = parts["sponsorship_short_pitch"]
        return _empty_validated(suggestion=suggestion, **parts)
    if feature == FEATURE_FAN_PASSPORT_BIO:
        parts = validate_fan_passport_bio(text)
        return _empty_validated(
            suggestion=str(parts["suggestion"]),
            options=parts["options"],
        )
    if feature == FEATURE_SUPPORT_TRIAGE:
        slug, label = validate_support_category(text)
        return _empty_validated(
            suggestion=f"Category: {label}\nSlug: {slug}",
            options=[label],
            category_slug=slug,
        )
    if feature == FEATURE_SUPPORT_PRIORITY:
        priority, reason = validate_support_priority(text)
        return _empty_validated(
            suggestion=f"Priority: {priority}\nReason: {reason}",
            options=[priority],
            priority=priority,
            priority_reason=reason,
        )
    if feature == FEATURE_SUPPORT_SUMMARY:
        return _empty_validated(suggestion=validate_support_summary(text))
    if feature == FEATURE_SUPPORT_REPLY_DRAFT:
        return _empty_validated(suggestion=validate_support_reply(text))
    if feature == FEATURE_SUPPORT_ARTICLES:
        articles = validate_support_articles(text, article_catalog or [])
        if not articles:
            suggestion = "No strong match in the help catalog."
        else:
            suggestion = "\n".join(
                f"{i}. {a.get('title')} ({a.get('path')})"
                for i, a in enumerate(articles, start=1)
            )
        return _empty_validated(
            suggestion=suggestion,
            options=[str(a.get("title") or "") for a in articles] or None,
            articles=articles,
        )
    if feature in ADMIN_SUMMARY_FEATURES:
        return _empty_validated(suggestion=validate_admin_summary(text))
    if feature == FEATURE_ADMIN_BLOG_TITLE:
        options = validate_blog_title_options(parse_title_options(text))
        suggestion = "\n".join(f"{i}. {o}" for i, o in enumerate(options, start=1))
        return _empty_validated(suggestion=suggestion, options=options)
    if feature == FEATURE_ADMIN_BLOG_OUTLINE:
        return _empty_validated(suggestion=validate_blog_outline(text))
    if feature == FEATURE_ADMIN_BLOG_EXCERPT:
        return _empty_validated(suggestion=validate_blog_excerpt(text))
    if feature == FEATURE_ADMIN_BLOG_SEO:
        meta = validate_blog_seo_meta(text)
        suggestion = (
            f"SEO title: {meta['seo_title']}\n"
            f"Meta description: {meta['seo_description']}\n"
            f"Slug: {meta['suggested_slug']}\n"
            f"OG description: {meta['og_description']}"
        )
        return _empty_validated(
            suggestion=suggestion,
            seo_title=meta["seo_title"],
            seo_description=meta["seo_description"],
            suggested_slug=meta["suggested_slug"],
            og_description=meta["og_description"],
        )
    if feature == FEATURE_ADMIN_BLOG_TAGS:
        tags = validate_blog_tags(text, tag_catalog or [])
        if not tags:
            suggestion = "No strong catalog tag match."
        else:
            suggestion = "\n".join(f"{i}. {t}" for i, t in enumerate(tags, start=1))
        return _empty_validated(
            suggestion=suggestion,
            options=tags or None,
            tags=tags or None,
        )
    if feature == FEATURE_ADMIN_BLOG_SOCIAL:
        snippets = validate_blog_social_snippets(text)
        suggestion = "\n".join(f"{k.title()}: {v}" for k, v in snippets.items())
        social = [{"platform": k, "text": v} for k, v in snippets.items()]
        return _empty_validated(suggestion=suggestion, social_snippets=social)
    from app.ai.output_validation import sanitize_draft_text

    return _empty_validated(suggestion=sanitize_draft_text(text))


def _describe_ai_fallback(
    *,
    result,
    routed: "RoutedCompletion",
    settings,
    force_template: bool,
) -> str | None:
    if not result.used_fallback:
        return None
    if force_template:
        return (
            "Monthly AI spend cap reached — network provider skipped; template draft returned."
        )
    if not settings.ai_enabled:
        return (
            "AI is disabled globally. In Admin → Pàdéyá AI → Settings, enable AI globally "
            "and save (requires admin.ai.manage_settings)."
        )
    if not (get_settings().ai_api_key or "").strip():
        return (
            "AI_API_KEY is not available to the API server. Set it in backend environment "
            "(not frontend NEXT_PUBLIC_*), restart the API, then test connection in admin."
        )
    if result.error_message:
        return str(result.error_message)[:500]
    if routed.primary_failed or routed.fallback_failed:
        chain = ", ".join(routed.chain[-3:]) if routed.chain else ""
        hint = f" Last attempts: {chain}." if chain else ""
        return (
            "Network provider failed or returned empty output. Check Admin → Pàdéyá AI → "
            f"Providers, model name, and Test connection.{hint}"
        )
    return "AI provider unavailable — template draft returned."


def generate_suggestion(
    db: Session,
    *,
    user: User,
    audience: str,
    payload: AIGenerateRequest,
) -> dict:
    raw_feature = payload.feature.strip()
    assert_ai_globally_available()
    from app.ai.constants import ADMIN_QUARANTINED_AI_FEATURES, LEGACY_HOST_AI_FEATURES

    quarantine_keys = {raw_feature, canonicalize_feature(raw_feature)}
    if quarantine_keys & LEGACY_HOST_AI_FEATURES:
        raise HTTPException(
            status_code=403,
            detail=(
                "Legacy host AI keys are disabled and not available in production. "
                "Use canonical host.* features (Event Studio, Merch Studio, announcements, sponsorship)."
            ),
        )
    if quarantine_keys & ADMIN_QUARANTINED_AI_FEATURES:
        raise HTTPException(
            status_code=403,
            detail=(
                "This admin AI feature is not available. Featured listings and "
                "recommendation decisions require product and safety review."
            ),
        )
    feature = assert_feature_enabled(raw_feature, db=db)

    host_allowed = {canonicalize_feature(f) for f in HOST_FEATURES} | set(HOST_FEATURES)
    fan_allowed = {canonicalize_feature(f) for f in FAN_FEATURES} | set(FAN_FEATURES)
    admin_allowed = set(ADMIN_FEATURES)
    if audience == "fan":
        allowed = fan_allowed
    elif audience == "host":
        allowed = host_allowed
    else:
        allowed = admin_allowed
    if feature not in allowed and raw_feature not in allowed:
        raise HTTPException(status_code=400, detail="Unknown AI feature")

    if audience == "fan":
        from app.users.restrictions import assert_can_edit_passport

        assert_can_edit_passport(db, user)
    elif audience == "host":
        assert_host_ai_actor(db, user, feature=feature)
    else:
        if not user_has_permission(user, "ai.use_platform") and not user_has_permission(
            user, "admin.full_access"
        ):
            raise HTTPException(status_code=403, detail="AI permission required")

    from app.ai.admin_controls import (
        assert_feature_request_limits,
        assert_spend_allows_network,
    )
    from app.ai.runtime_config import resolve_ai_settings

    assert_feature_request_limits(db, feature)
    spend_info = assert_spend_allows_network(db)
    force_template = bool(spend_info.get("force_template_fallback"))

    _check_rate_limit(db, user.id)
    template = _get_template(db, feature, audience)
    context, host_id, redactions, extras = _build_context(
        db, user=user, audience=audience, feature=feature, payload=payload
    )
    user_prompt = scrub_prompt_text(render_prompt(template.user_template, context))
    system_prompt = scrub_prompt_text(template.system_prompt)

    started = time.perf_counter()
    from app.ai.feature_routing import RoutedCompletion, complete_for_feature

    routed = complete_for_feature(
        db,
        feature_key=feature,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        force_template_only=force_template,
    )
    result = routed.result
    provider_chain = routed.chain
    runtime_settings = resolve_ai_settings(db)
    fallback_reason = _describe_ai_fallback(
        result=result,
        routed=routed,
        settings=runtime_settings,
        force_template=force_template,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    merch_product_id = payload.merch_product_id
    support_ticket_id = payload.support_ticket_id
    blog_post_id = payload.blog_post_id
    if feature in SUPPORT_FEATURES:
        resource_type = "support_case"
        resource_id = str(support_ticket_id) if support_ticket_id else None
    elif feature in ADMIN_SUMMARY_FEATURES:
        resource_type = "admin_summary"
        resource_id = feature
    elif feature in BLOG_FEATURES:
        resource_type = "blog_post"
        resource_id = str(blog_post_id) if blog_post_id else None
    elif feature in MERCH_FEATURES:
        resource_type = "merch_product"
        resource_id = str(merch_product_id) if merch_product_id else None
    elif feature in ANNOUNCEMENT_FEATURES:
        resource_type = "host_announcement"
        resource_id = str(payload.event_id) if payload.event_id else None
    elif feature in SPONSORSHIP_FEATURES:
        resource_type = "host_sponsorship"
        resource_id = str(host_id) if host_id else None
    elif feature in PASSPORT_FEATURES:
        resource_type = "fan_passport"
        resource_id = str(user.id)
    else:
        resource_type = "event"
        resource_id = str(payload.event_id) if payload.event_id else None

    article_catalog = extras.get("article_catalog") or []
    tag_catalog = extras.get("tag_catalog") or []
    announcement_subject = None
    announcement_email_body = None
    announcement_whatsapp_body = None
    sponsorship_pitch_title = None
    sponsorship_short_pitch = None
    sponsorship_value_bullets = None
    sponsorship_audience_summary = None
    sponsorship_package_wording = None
    sponsorship_follow_up_message = None

    try:
        validated = _validate_output(
            feature,
            result.text,
            article_catalog=article_catalog,
            tag_catalog=tag_catalog,
        )
        suggestion = validated["suggestion"]
        options = validated["options"]
        category_slug = validated["category_slug"]
        tags = validated["tags"]
        priority = validated["priority"]
        priority_reason = validated["priority_reason"]
        articles = validated["articles"]
        seo_title = validated.get("seo_title")
        seo_description = validated.get("seo_description")
        suggested_slug = validated.get("suggested_slug")
        og_description = validated.get("og_description")
        social_snippets = validated.get("social_snippets")
        announcement_subject = validated.get("announcement_subject")
        announcement_email_body = validated.get("announcement_email_body")
        announcement_whatsapp_body = validated.get("announcement_whatsapp_body")
        sponsorship_pitch_title = validated.get("sponsorship_pitch_title")
        sponsorship_short_pitch = validated.get("sponsorship_short_pitch")
        sponsorship_value_bullets = validated.get("sponsorship_value_bullets")
        sponsorship_audience_summary = validated.get("sponsorship_audience_summary")
        sponsorship_package_wording = validated.get("sponsorship_package_wording")
        sponsorship_follow_up_message = validated.get("sponsorship_follow_up_message")
        success = True
        error_message = result.error_message
    except HTTPException as exc:
        cost = _estimate_cost_micros(result.tokens_in, result.tokens_out)
        fail_log = AIUsageLog(
            user_id=user.id,
            host_id=host_id,
            feature_key=feature,
            prompt_template_slug=template.slug,
            provider=result.provider,
            model_name=result.model_name,
            success=False,
            used_fallback=result.used_fallback,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            error_message=str(exc.detail)[:500],
            meta={
                "audience": audience,
                "event_id": str(payload.event_id) if payload.event_id else None,
                "merch_product_id": str(merch_product_id) if merch_product_id else None,
                "support_ticket_id": (
                    str(support_ticket_id) if support_ticket_id else None
                ),
                "blog_post_id": str(blog_post_id) if blog_post_id else None,
                "resource_scope": extras.get("resource_scope"),
                "redaction_applied": bool(redactions),
                "redaction_actions": redactions[:40],
                "latency_ms": latency_ms,
                "provider_chain": provider_chain,
                "estimated_cost_micros": cost,
                "prompt_template_version": template.updated_at.isoformat()
                if template.updated_at
                else None,
                "validation_failed": True,
                "validation_result": "failed",
            },
        )
        db.add(fail_log)
        write_audit_log(
            db,
            action="ai.generation_failed",
            actor_user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "feature_key": feature,
                "host_id": str(host_id) if host_id else None,
                "event_id": str(payload.event_id) if payload.event_id else None,
                "merch_product_id": str(merch_product_id) if merch_product_id else None,
                "support_ticket_id": (
                    str(support_ticket_id) if support_ticket_id else None
                ),
                "blog_post_id": str(blog_post_id) if blog_post_id else None,
                "resource_scope": extras.get("resource_scope"),
                "redaction_applied": bool(redactions),
                "provider": result.provider,
                "model": result.model_name,
                "reason": "validation_failed",
                "validation_result": "failed",
            },
        )
        db.commit()
        raise

    cost = _estimate_cost_micros(result.tokens_in, result.tokens_out)
    log = AIUsageLog(
        user_id=user.id,
        host_id=host_id,
        feature_key=feature,
        prompt_template_slug=template.slug,
        provider=result.provider,
        model_name=result.model_name,
        success=success,
        used_fallback=result.used_fallback,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        error_message=error_message,
        meta={
            "audience": audience,
            "event_id": str(payload.event_id) if payload.event_id else None,
            "merch_product_id": str(merch_product_id) if merch_product_id else None,
            "support_ticket_id": (
                str(support_ticket_id) if support_ticket_id else None
            ),
            "blog_post_id": str(blog_post_id) if blog_post_id else None,
            "resource_scope": extras.get("resource_scope"),
            "redaction_applied": bool(redactions),
            "redaction_actions": redactions[:40],
            "latency_ms": latency_ms,
            "provider_chain": provider_chain,
            "estimated_cost_micros": cost,
            "prompt_template_version": template.updated_at.isoformat()
            if template.updated_at
            else None,
            "options_count": len(options) if options else None,
            "validation_result": "passed",
            "category_slug": category_slug,
            "priority": priority,
        },
    )
    db.add(log)
    write_audit_log(
        db,
        action="ai.generation_created",
        actor_user_id=user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        details={
            "feature_key": feature,
            "host_id": str(host_id) if host_id else None,
            "event_id": str(payload.event_id) if payload.event_id else None,
            "merch_product_id": str(merch_product_id) if merch_product_id else None,
            "support_ticket_id": (
                str(support_ticket_id) if support_ticket_id else None
            ),
            "blog_post_id": str(blog_post_id) if blog_post_id else None,
            "resource_scope": extras.get("resource_scope"),
            "prompt_template_slug": template.slug,
            "prompt_template_version": template.updated_at.isoformat()
            if template.updated_at
            else None,
            "redaction_applied": bool(redactions),
            "provider": result.provider,
            "model": result.model_name,
            "used_fallback": result.used_fallback,
            "latency_ms": latency_ms,
            "estimated_cost_micros": cost,
            "draft_only": True,
            "validation_result": "passed",
        },
    )
    db.commit()
    db.refresh(log)

    if feature in SUPPORT_FEATURES:
        disclaimer = SUPPORT_DRAFT_DISCLAIMER
    elif feature in ADMIN_SUMMARY_FEATURES:
        disclaimer = ADMIN_SUMMARY_DISCLAIMER
    elif feature in BLOG_FEATURES:
        disclaimer = BLOG_DRAFT_DISCLAIMER
    elif feature in ANNOUNCEMENT_FEATURES:
        disclaimer = ANNOUNCEMENT_DRAFT_DISCLAIMER
    elif feature in SPONSORSHIP_FEATURES:
        disclaimer = SPONSORSHIP_DRAFT_DISCLAIMER
    elif feature in PASSPORT_FEATURES:
        disclaimer = PASSPORT_DRAFT_DISCLAIMER
    else:
        disclaimer = DRAFT_DISCLAIMER
    return {
        "feature": feature,
        "label": FEATURE_LABELS.get(feature, feature),
        "suggestion": suggestion,
        "options": options,
        "category_slug": category_slug,
        "tags": tags,
        "priority": priority,
        "priority_reason": priority_reason,
        "articles": articles,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "suggested_slug": suggested_slug,
        "og_description": og_description,
        "social_snippets": social_snippets,
        "announcement_subject": announcement_subject,
        "announcement_email_body": announcement_email_body,
        "announcement_whatsapp_body": announcement_whatsapp_body,
        "sponsorship_pitch_title": sponsorship_pitch_title,
        "sponsorship_short_pitch": sponsorship_short_pitch,
        "sponsorship_value_bullets": sponsorship_value_bullets,
        "sponsorship_audience_summary": sponsorship_audience_summary,
        "sponsorship_package_wording": sponsorship_package_wording,
        "sponsorship_follow_up_message": sponsorship_follow_up_message,
        "provider": result.provider,
        "model_name": result.model_name,
        "used_fallback": result.used_fallback,
        "fallback_reason": fallback_reason,
        "requires_human_confirmation": feature_requires_human_review(feature, db=db),
        "can_auto_publish": False,
        "can_auto_send": False,
        "can_modify_finance": False,
        "draft_only": True,
        "disclaimer": disclaimer,
        "usage_log_id": log.id,
        "created_at": log.created_at,
        "redaction_applied": bool(redactions),
    }


def record_generation_feedback(
    db: Session,
    *,
    user: User,
    payload: AIGenerationFeedbackRequest,
) -> dict:
    """Record accepted / applied / rejected / dismissed — never auto-sends."""
    log = db.get(AIUsageLog, payload.usage_log_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status_code=404, detail="Generation not found")

    host_id = log.host_id
    if not (
        user_has_permission(user, "ai.use_own")
        or user_has_permission(user, "ai.use_platform")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="AI permission required")

    meta = dict(log.meta or {})
    feedback_entry = {
        "action": payload.action,
        "at": datetime.now(UTC).isoformat(),
        "applied_field": payload.applied_field,
        "selected_option_len": len(payload.selected_option or ""),
    }
    history = list(meta.get("feedback") or [])
    history.append(feedback_entry)
    meta["feedback"] = history[-20:]
    log.meta = meta

    merch_id = payload.merch_product_id or (
        UUID(str(meta["merch_product_id"]))
        if meta.get("merch_product_id")
        else None
    )
    event_id = payload.event_id or (
        UUID(str(meta["event_id"])) if meta.get("event_id") else None
    )
    support_ticket_id = payload.support_ticket_id or (
        UUID(str(meta["support_ticket_id"]))
        if meta.get("support_ticket_id")
        else None
    )
    blog_post_id = payload.blog_post_id or (
        UUID(str(meta["blog_post_id"])) if meta.get("blog_post_id") else None
    )
    if support_ticket_id:
        resource_type = "support_case"
        resource_id = str(support_ticket_id)
    elif blog_post_id:
        resource_type = "blog_post"
        resource_id = str(blog_post_id)
    elif merch_id:
        resource_type = "merch_product"
        resource_id = str(merch_id)
    else:
        resource_type = "event"
        resource_id = str(event_id) if event_id else None

    audit_action = {
        "accepted": "ai.generation_applied",
        "applied": "ai.generation_applied",
        "rejected": "ai.generation_dismissed",
        "dismissed": "ai.generation_dismissed",
    }.get(payload.action, f"ai.generation_{payload.action}")

    write_audit_log(
        db,
        action=audit_action,
        actor_user_id=user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        details={
            "feature_key": log.feature_key,
            "host_id": str(host_id) if host_id else None,
            "usage_log_id": str(log.id),
            "applied_field": payload.applied_field,
            "event_id": str(event_id) if event_id else None,
            "merch_product_id": str(merch_id) if merch_id else None,
            "support_ticket_id": (
                str(support_ticket_id) if support_ticket_id else None
            ),
            "blog_post_id": str(blog_post_id) if blog_post_id else None,
            "redaction_applied": bool((log.meta or {}).get("redaction_applied")),
            "provider": log.provider,
            "model": log.model_name,
            "feedback_action": payload.action,
            "validation_result": (log.meta or {}).get("validation_result"),
        },
    )
    db.commit()
    return {"ok": True, "action": payload.action, "usage_log_id": log.id}
