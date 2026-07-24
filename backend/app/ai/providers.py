"""AI provider abstraction — server-side only; never expose API keys."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class AICompletion:
    text: str
    provider: str
    model_name: str | None
    used_fallback: bool
    tokens_in: int | None = None
    tokens_out: int | None = None
    error_message: str | None = None


class AIProvider(Protocol):
    name: str

    def complete(self, *, system_prompt: str, user_prompt: str) -> AICompletion: ...


class TemplateFallbackProvider:
    """Deterministic local drafts when AI is disabled or unavailable."""

    name = "template"

    def complete(self, *, system_prompt: str, user_prompt: str) -> AICompletion:
        # Produce a useful draft from the user prompt body without calling a network API.
        draft = _template_draft(user_prompt)
        return AICompletion(
            text=draft,
            provider=self.name,
            model_name="template-v1",
            used_fallback=True,
            tokens_in=len(user_prompt.split()),
            tokens_out=len(draft.split()),
            error_message=None,
        )


class UnavailableProvider:
    """Explicit no-op provider that always falls back to template copy."""

    name = "none"

    def __init__(self, reason: str = "AI provider unavailable") -> None:
        self.reason = reason
        self._fallback = TemplateFallbackProvider()

    def complete(self, *, system_prompt: str, user_prompt: str) -> AICompletion:
        result = self._fallback.complete(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
        result.provider = self.name
        result.used_fallback = True
        result.error_message = self.reason
        return result


class OpenAICompatibleProvider:
    """Optional HTTP provider (OpenAI-compatible chat completions).

    Used for openai / anthropic / gemini / grok when pointed at a compatible base URL.
    """

    def __init__(self, settings: Settings, *, name: str = "openai") -> None:
        self.settings = settings
        self.name = name
        self._fallback = TemplateFallbackProvider()

    def complete(self, *, system_prompt: str, user_prompt: str) -> AICompletion:
        if not self.settings.ai_api_key:
            fb = self._fallback.complete(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            fb.provider = self.name
            fb.used_fallback = True
            fb.error_message = "AI_API_KEY not configured"
            return fb

        from app.ai.runtime_config import effective_base_url

        base = effective_base_url(self.settings)
        url = f"{base.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.ai_model,
            "max_tokens": self.settings.ai_max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.settings.ai_timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            usage = data.get("usage") or {}
            if not text:
                raise ValueError("Empty completion from provider")
            return AICompletion(
                text=text,
                provider=self.name,
                model_name=self.settings.ai_model,
                used_fallback=False,
                tokens_in=usage.get("prompt_tokens"),
                tokens_out=usage.get("completion_tokens"),
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError) as exc:
            logger.warning("AI provider failed; using fallback: %s", exc)
            fb = self._fallback.complete(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            fb.provider = self.name
            fb.used_fallback = True
            fb.error_message = str(exc)[:500]
            return fb


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    if not settings.ai_enabled:
        return UnavailableProvider("AI is disabled (AI_ENABLED=false)")
    provider = (settings.ai_provider or "template").strip().lower()
    if provider in {"none", "off", "disabled"}:
        return UnavailableProvider("AI provider set to none")
    if provider in {"openai", "anthropic", "gemini", "grok"}:
        return OpenAICompatibleProvider(settings, name=provider)
    # Default safe local provider (template fallback)
    return TemplateFallbackProvider()


@dataclass
class ProviderInvokeConfig:
    """Resolved call parameters for a single provider attempt (no secrets in logs)."""

    logical_name: str
    provider_type: str
    model: str
    base_url: str
    api_key: str | None
    max_tokens: int
    timeout_seconds: int
    profile_id: str | None = None


class StrictHTTPProvider:
    """OpenAI-compatible call without auto-template fallback (for routing chains)."""

    def __init__(self, config: ProviderInvokeConfig) -> None:
        self.config = config
        self.name = config.logical_name

    def complete(self, *, system_prompt: str, user_prompt: str) -> AICompletion:
        cfg = self.config
        if cfg.provider_type == "template_fallback":
            return TemplateFallbackProvider().complete(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
        if not cfg.api_key:
            return AICompletion(
                text="",
                provider=cfg.logical_name,
                model_name=cfg.model,
                used_fallback=False,
                error_message="API key not configured for provider profile",
            )
        url = f"{cfg.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": cfg.model,
            "max_tokens": cfg.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {cfg.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            usage = data.get("usage") or {}
            if not text:
                raise ValueError("Empty completion from provider")
            return AICompletion(
                text=text,
                provider=cfg.logical_name,
                model_name=cfg.model,
                used_fallback=False,
                tokens_in=usage.get("prompt_tokens"),
                tokens_out=usage.get("completion_tokens"),
            )
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ValueError,
            KeyError,
        ) as exc:
            logger.warning("Strict AI provider failed: %s", exc)
            return AICompletion(
                text="",
                provider=cfg.logical_name,
                model_name=cfg.model,
                used_fallback=False,
                error_message=str(exc)[:500],
            )


def default_base_url_for_type(provider_type: str) -> str:
    from app.ai.runtime_config import PROVIDER_DEFAULT_BASE_URLS

    p = provider_type.strip().lower()
    if p in {"openai", "openai_compatible"}:
        return PROVIDER_DEFAULT_BASE_URLS["openai"]
    return PROVIDER_DEFAULT_BASE_URLS.get(p, PROVIDER_DEFAULT_BASE_URLS["openai"])


def _template_draft(user_prompt: str) -> str:
    """Heuristic draft generator used as safe fallback."""
    lines = [ln.strip() for ln in user_prompt.splitlines() if ln.strip()]
    lower = user_prompt.lower()
    city = ""
    category = ""
    title = ""
    for ln in lines:
        low = ln.lower()
        if low.startswith("city:"):
            city = ln.split(":", 1)[-1].strip()
        elif low.startswith("category:"):
            category = ln.split(":", 1)[-1].strip()
        elif low.startswith("existing title:") or low.startswith("title:"):
            title = ln.split(":", 1)[-1].strip()

    place = city or "your city"
    scene = category or "night"
    base = title if title and title.lower() not in {"", "none"} else None

    if "generate exactly 5 event title" in lower or "generate 5 event title" in lower:
        seeds = [
            base or f"{scene.title()} Live in {place}",
            f"{place} {scene.title()} Night",
            f"After Dark: {scene.title()} in {place}",
            f"{place} Sessions — {scene.title()}",
            f"The {place} {scene.title()} Experience",
        ]
        return "\n".join(f"{i}. {s}" for i, s in enumerate(seeds, start=1))

    if "generate exactly 5 merch product title" in lower or "merch product title options" in lower:
        product = ""
        for ln in lines:
            if ln.lower().startswith("product type:"):
                product = ln.split(":", 1)[-1].strip().replace("_", " ")
                break
        kind = product or "merch"
        seeds = [
            base or f"{kind.title()} Drop",
            f"{place} {kind.title()}" if place != "your city" else f"Night Out {kind.title()}",
            f"Pàdéyá {kind.title()} Classic",
            f"The {kind.title()} Essential",
            f"{kind.title()} for the Night",
        ]
        return "\n".join(f"{i}. {s}" for i, s in enumerate(seeds, start=1))

    if "write one polished product description" in lower:
        name = base or "this product"
        return (
            f"{name} is a Pàdéyá host merch piece made for fans who want a tangible memory "
            f"of the night. Keep the fit, finish, and care details accurate to what you will "
            f"actually sell — edit this draft before publishing. Pair it with clear pickup or "
            f"delivery notes on your product page, and invite buyers to grab theirs on Pàdéyá. "
            f"This is a draft only: no price, inventory, or policy claims were changed for you."
        )

    if "suggest exactly one browse category" in lower:
        # Heuristic from product type
        product = ""
        for ln in lines:
            if ln.lower().startswith("product type:"):
                product = ln.split(":", 1)[-1].strip().lower()
                break
        mapping = {
            "t_shirt": "apparel",
            "hoodie": "apparel",
            "tote_bag": "apparel",
            "cap": "caps",
            "wristband": "wristbands",
            "face_mask": "masks",
            "poster": "posters",
            "vip_pack": "bundles",
            "souvenir": "collectibles",
        }
        slug = mapping.get(product, "other")
        return slug

    if "suggest 3–6 short merchandising tags" in lower or "merchandising tags" in lower:
        return "1. event merch\n2. fan gear\n3. night out\n4. host drop\n5. padeya"

    if "staff-only ticket summary" in lower or "write a staff-only ticket summary" in lower:
        subject = ""
        status = ""
        for ln in lines:
            low = ln.lower()
            if low.startswith("subject:"):
                subject = ln.split(":", 1)[-1].strip()
            elif low.startswith("status:"):
                status = ln.split(":", 1)[-1].strip()
        topic = subject or "this ticket"
        return (
            f"Issue summary: Requester needs help with {topic}.\n"
            f"User goal: Resolve the issue and get a clear next step.\n"
            f"Related context: See order/event refs in the ticket if present.\n"
            f"Current status: {status or 'open'}.\n"
            f"Suggested next action: Confirm facts with the requester, check "
            f"linked records, then reply with a clear next step. Do not promise "
            f"refunds or payment confirmation without verified status."
        )

    if "suggest exactly one support category slug" in lower:
        return "Category: other\nReason: Needs staff confirmation from conversation context."

    if "suggest priority from:" in lower:
        return (
            "Priority: normal\n"
            "Reason: Default triage — confirm if payment, safety, or event timing "
            "requires higher urgency."
        )

    if "draft a polite public reply" in lower:
        return (
            "Thanks for reaching out to Pàdéyá Support. I’ve reviewed your ticket "
            "and I’m looking into this for you.\n\n"
            "To help us move quickly, please reply with any extra details you can "
            "share about what you expected to happen and what you saw instead. "
            "We’ll follow up with clear next steps after we verify the relevant "
            "records.\n\n"
            "We appreciate your patience."
        )

    if "pick up to 5 help articles" in lower or "help articles from this catalog" in lower:
        # Prefer saying no strong match when catalog is empty/none
        for ln in lines:
            if ln.lower().startswith("catalog:") and "none" in ln.lower():
                return "no strong match"
        # If catalog lines exist with slug|title|id, echo first few
        picks: list[str] = []
        for ln in lines:
            if "|" in ln and not ln.lower().startswith(
                ("task:", "subject:", "category:", "conversation:")
            ):
                picks.append(ln.strip())
            if len(picks) >= 3:
                break
        if not picks:
            return "no strong match"
        return "\n".join(f"{i}. {p}" for i, p in enumerate(picks, start=1))

    if "advisory support queue summary" in lower or "write an advisory support queue" in lower:
        return (
            "Open tickets: See support_snapshot counts in source data.\n"
            "Urgent / high priority: Prioritize urgent and high rows first.\n"
            "Main issue themes: Review category breakdown in the snapshot.\n"
            "Needs fastest attention: Start with urgent/high subjects listed.\n"
            "Suggested staff focus:\n"
            "- [ ] Triage urgent tickets in /admin/support\n"
            "- [ ] Confirm payment/refund escalations with finance\n"
            "- [ ] Update waiting_on_user threads with clear next steps\n"
            "Advisory only — review source tickets before acting."
        )

    if "explain this analytics period" in lower or "explain this analytics period using aggregates" in lower:
        return (
            "Revenue trend: Use gross_revenue and sales_over_time from the snapshot.\n"
            "Ticket sales: tickets_sold in the supplied aggregates.\n"
            "Merch sales: merch_items_sold when present.\n"
            "Refund / failed payments: review refund_amount and failed_payments.\n"
            "Top performers: top_events / top_hosts / category_trends as provided.\n"
            "Suggested reviews:\n"
            "- [ ] Inspect /admin/analytics/revenue for the period\n"
            "- [ ] Check /admin/refunds for elevated refund amount\n"
            "- [ ] Review failed payment volume on finance dashboards\n"
            "Advisory only — do not invent totals beyond the snapshot."
        )

    if "summarize moderation/report queues" in lower:
        return (
            "Report themes: Use review_reason_themes and message_report_themes.\n"
            "High-risk items: Start with open samples that mention abuse/safety.\n"
            "Repeated targets: Prefer truncated display labels from the snapshot.\n"
            "Suggested review order:\n"
            "- [ ] Open /admin/reviews queue\n"
            "- [ ] Open /admin/message-reports\n"
            "- [ ] Cross-check Fan Connect reports if volume is elevated\n"
            "Do not hide, approve, reject, suspend, or warn automatically."
        )

    if "on-demand daily operations summary" in lower or "daily operations summary" in lower:
        return (
            "Operations snapshot (advisory):\n"
            "- New users / hosts / events: use operations_snapshot counts\n"
            "- Ticket sales and revenue: use supplied aggregates only\n"
            "- Support load: open tickets + urgent count\n"
            "- Safety/report load: open review + message reports\n"
            "- Payment issues: failed_payments / refund_amount when present\n"
            "Action items:\n"
            "- [ ] /admin/events/review for pending listings\n"
            "- [ ] /admin/support for urgent tickets\n"
            "- [ ] /admin/reviews and /admin/refunds for safety/finance follow-up\n"
            "Generated on demand — not an automatic job."
        )

    if "generate 3–5 blog title" in lower or "blog title options" in lower:
        return (
            "1. Discover nightlife on Pàdéyá\n"
            "2. A clearer way to find tickets this weekend\n"
            "3. Host nights that feel local — without the guesswork\n"
            "4. From discovery to check-in on Pàdéyá\n"
            "5. Guides for fans and hosts on Pàdéyá"
        )

    if "structured markdown outline" in lower or "write a structured markdown outline" in lower:
        return (
            "## Opening\n"
            "- Set the scene and why this guide matters on Pàdéyá\n"
            "## What you’ll learn\n"
            "- Core product areas covered in plain language\n"
            "## Step-by-step\n"
            "- Practical next actions for readers\n"
            "## Closing CTA\n"
            "- Invite readers to explore events or host tools\n"
            "- Reminder: editors must review before publishing"
        )

    if "write one short blog excerpt" in lower:
        return (
            "A practical Pàdéyá guide to help fans and hosts move from discovery "
            "to a smoother night out — edit this draft before you publish."
        )

    if "suggest seo fields" in lower:
        return (
            "SEO title: Discover events on Pàdéyá\n"
            "Meta description: Practical guides for fans and hosts on Pàdéyá — "
            "discovery, tickets, and night-out tips. Draft only.\n"
            "Slug: discover-events-on-padeya\n"
            "OG description: Practical Pàdéyá guides for fans and hosts."
        )

    if "suggest up to 6 tags from this catalog" in lower:
        return "1. nightlife\n2. ticketing\n3. hosts\n4. fans"

    if "draft social snippets" in lower:
        return (
            "Twitter: New on Pàdéyá — a practical guide for fans and hosts. "
            "Review the draft, then share when ready.\n"
            "Instagram: Behind the night: tips for discovering events and "
            "hosting with clarity on Pàdéyá. Edit before you post.\n"
            "LinkedIn: Editorial draft: how Pàdéyá helps local nights feel "
            "organized — for fans and hosts alike.\n"
            "WhatsApp: Sharing a Pàdéyá blog draft about discovery and tickets. "
            "Human review first — not auto-sent."
        )

    if "write one polished event description" in lower or "write an event description" in lower:
        name = base or f"a {scene} event in {place}"
        return (
            f"Join us for {name} on Pàdéyá — a carefully hosted night built for people who "
            f"care about atmosphere, community, and a memorable evening in {place}. "
            f"Expect a clear run-of-show, welcoming energy, and a crowd that came for the vibe. "
            f"Arrive ready to settle in, meet friends old and new, and enjoy the night as it unfolds. "
            f"Tickets are available on Pàdéyá — review the details, pick your tier, and lock in your spot. "
            f"This is a draft only: edit dates, venue notes, and house rules before you publish."
        )

    if "draft a host crm announcement" in lower:
        notes = ""
        for ln in lines:
            if ln.lower().startswith("host notes:"):
                notes = ln.split(":", 1)[-1].strip()
                break
        city = ""
        for ln in lines:
            if ln.lower().startswith("city:"):
                city = ln.split(":", 1)[-1].strip()
                break
        place = city or place or "your city"
        hook = notes or f"Something special is coming to {place} on Pàdéyá."
        return (
            f"SUBJECT: {base or 'Update from your host on Pàdéyá'}\n\n"
            f"EMAIL_BODY:\n"
            f"Hi there,\n\n"
            f"{hook}\n\n"
            f"We will share full details on Pàdéyá soon — this is a draft for you to edit "
            f"before you create or send anything.\n\n"
            f"WHATSAPP:\n"
            f"{hook[:480]}\n\n"
            f"(Generated by Pàdéyá template fallback — AI provider was unavailable or disabled.)"
        )

    context_bits = []
    for ln in lines:
        if ln.lower().startswith(("context:", "event:", "city:", "category:", "metrics:")):
            context_bits.append(ln)
    ctx = " · ".join(context_bits[:6]) if context_bits else "your Pàdéyá event"
    feature_hint = lines[0] if lines else "suggestion"
    return (
        f"[Draft — review before using]\n\n"
        f"{feature_hint}\n\n"
        f"Based on: {ctx}\n\n"
        f"1) Lead with a clear, local vibe and the night’s promise.\n"
        f"2) Keep the call-to-action simple: get tickets on Pàdéyá.\n"
        f"3) Human-edit tone, pricing, and dates before publishing or sending.\n\n"
        f"(Generated by Pàdéyá template fallback — AI provider was unavailable or disabled.)"
    )
