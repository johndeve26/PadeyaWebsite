# Pàdéyá AI Integration Audit

**Brand:** Pàdéyá  
**Date:** 2026-07-22  
**Status:** Audit + **Phase 1 partial implementation** (hardening + Event Studio + Merch Studio + Support AI + Admin summaries + Blog AI + **Admin AI controls**)  
**Scope:** Product + technical opportunities, risks, architecture, and prioritized roadmap  
**Out of scope for original audit:** Provider keys in repo, Fan Connect ranking, discovery AI, automated moderation/refunds  
**Admin controls (2026-07-22):** `/admin/ai` hub — settings, feature toggles, spend caps, usage dashboard, test connection; `AI_API_KEY` remains env-only

### Implementation status (2026-07-22)

| Item | Status |
|------|--------|
| AI context scrubber | **Shipped** — `backend/app/ai/context_scrubber.py` |
| Feature toggles + kill switch | **Shipped** — defaults + `AI_DISABLED_FEATURES` / `AI_KILL_SWITCH` + DB `ai_feature_configs` |
| Output validation (title/description) | **Shipped** — `backend/app/ai/output_validation.py` |
| Usage meta (latency, estimated cost) + audit logs | **Shipped** |
| Canonical keys `host.event.title` / `host.event.description` | **Shipped** |
| Event Studio Basics inline Generate with AI | **Shipped** — draft apply only |
| Generation feedback (applied/dismissed) | **Shipped** — `POST /ai/host/generation-feedback` |
| Merch Studio title / description / category / tags | **Shipped** — `host.merch.*` + `MerchAIAssist` |
| Merch-specific output validation + scrub allowlist | **Shipped** |
| Support ticket summary / triage / priority / reply draft / articles | **Shipped** — `support.ticket.*` + `SupportAIAssist` |
| Support context scrub + reply/category/priority/article validation | **Shipped** — `support_context.py` + output validators |
| Admin support queue / revenue / reports / daily ops summaries | **Shipped** — `admin.*.summary` + `AdminAISummaryPanel` |
| Admin aggregate context scrub + advisory validation | **Shipped** — `admin_context.py` |
| Blog CMS title / outline / excerpt / SEO / tags / social | **Shipped** — `admin.blog.*` + `BlogAIAssist` |
| Blog draft validation + scrub allowlist | **Shipped** — `blog_context.py` + blog validators |
| Admin AI controls + usage dashboard | **Shipped** — **AI Control Center** `/admin/ai` (+ providers, features, usage, logs, safety, settings) |
| Multi-provider profiles + per-feature routing | **Shipped** — `ai_provider_profiles`, `ai_feature_routes`, fallback chains |
| API key storage | **Env-only** — `AI_API_KEY` masked status; not editable in UI |
| Spend caps + hard stop + template fallback | **Shipped** — `ai_platform_settings` |
| Fan Connect ranking / discovery AI / auto-moderation / buyer merch recommendations | **Explicitly deferred** — `fan.connect.explanation`, `discovery.why_recommended` blocked in Control Center |
| Legacy host AI slugs + admin recommendation placeholders | **Quarantined** — `LEGACY_HOST_AI_FEATURES`, `ADMIN_QUARANTINED_AI_FEATURES`; default off; HTTP 403 at generate |
| Pre-deploy hardening (announcement context, fan CC section) | **Shipped** — see `docs/AI_PREDEPLOY_HARDENING_AUDIT.md` |
| Customer-facing chatbot / auto-send / auto-close | **Explicitly deferred** |

---

## Executive summary

Pàdéyá already has a **Phase 15 AI Copilot foundation**: server-side provider abstraction, seeded prompt templates, host/admin generate APIs, usage logs, permissions (`ai.use_own` / `ai.use_platform`), template fallback when AI is off, and hard product rules that suggestions never publish, send, or write finance.

The highest-value next moves are **not** “more AI everywhere.” They are:

1. **Deepen safe draft generation** where hosts already write copy (Event Studio, Merch Studio, announcements, blog SEO).
2. **Staff assist tools** with mandatory human review (support triage, suggested replies, admin summaries).
3. **Harden the AI service layer** (feature toggles, spend limits, output validation, audit, redaction) before high-risk ranking/fraud features.

**Do not** start with Fan Connect ranking, discovery personalization that needs GPS, automated moderation/refund/suspension, or dynamic pricing. Keep those Phase 3+ after richer data, stronger redaction, and human-review workflows exist.

**Top first implementation candidate:** Host Event Studio inline **description + title** generator (extend existing `generate_event_*` into Studio steps — not a standalone novelty page).

---

## 0. Current state (baseline)

### Already shipped (Phase 15)

| Area | Location | Notes |
|------|----------|--------|
| Backend module | `backend/app/ai/` | `providers.py`, `service.py`, `router.py`, `models.py`, `seed.py`, `constants.py` |
| Provider abstraction | `OpenAICompatibleProvider` + `TemplateFallbackProvider` + `UnavailableProvider` | Env: `AI_ENABLED`, `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`, `AI_BASE_URL`, limits |
| Host features | `/host/ai`, `/host/events/[id]/ai` | Titles, description, tier copy, social/WhatsApp/email drafts, pricing/promo ideas, performance summary, Legacy path, recap draft |
| Admin features | `/admin/ai` (+ settings/features/usage), `/admin/support/ai-summary` | Admin controls + advisory summaries; **risk/fraud are placeholders** |
| Permissions | `ai.use_own`, `ai.use_platform` | In `backend/app/users/constants.py` |
| Tables | `ai_prompt_templates`, `ai_usage_logs` | Prompt admin CRUD exists for platform; usage dashboard incomplete |
| Safety flags on responses | Always | `requires_human_confirmation=true`, `can_auto_publish/send/modify_finance=false` |
| Runtime settings | Env + Class B knobs | `AI_API_KEY` stays Class A / env-only today ([ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md)) |

### Product surfaces that are ready for AI *assist* (not autopilot)

| Domain | Key routes / code |
|--------|-------------------|
| Event Studio | `/host/events/new`, `/host/events/[id]/edit` · `frontend/src/components/events/studio/` |
| Merch Studio | `/host/merchandise/*`, `/host/events/[id]/merchandise/*` |
| Announcements / CRM | `/host/announcements/new`, `/host/audience` |
| Support + Help | `/support/*`, `/admin/support/*`, `/help*`, deflection in `app/support` + `app/knowledge_base` |
| Blog CMS | `/admin/blog/*` |
| Sponsorships | `/host/sponsorships*`, `/sponsors*`, `/admin/sponsorships` |
| Fan Passport | `/dashboard/passport/settings`, `/f/[username]` |
| Fan Connect | Rules scoring in `app/fan_connect/scoring.py` — **keep deterministic** |
| Discovery | Taxonomy hubs, Pàdéyá Picks, marketplace sort — **rules first** |
| Analytics | `/host/analytics`, `/admin/analytics*` — aggregate-only inputs |

### Explicit product invariants that constrain AI

- Hosts cannot delete reviews; Support cannot modify financial records.
- Tickets only after verified payment webhook; signed QR — never send QR secrets to providers.
- Vault locked bodies never leak; private venues redacted by access level.
- Messaging / Fan Connect privacy: no phone, payment, private venue, CRM notes, locked Vault in peer surfaces.
- AI never publishes, sends announcements, or writes finance (already encoded in Copilot responses).
- AI support replies must **never auto-send** without human review.

---

## 1. Host AI Copilot

### Opportunity map

| Opportunity | Fit | Notes |
|-------------|-----|--------|
| Event title | **High** | Already seeded; move into Event Studio Basics step |
| Event description | **High** | Highest host time-saver; Studio-native UX |
| Category suggestions | **Medium** | Prefer taxonomy rules + light LLM re-rank from controlled vocab only |
| Ticket tier suggestions | **Medium** | Structure (names/benefits) OK; pricing needs caution |
| Pricing suggestions | **Medium–High risk** | Keep advisory + “not financial advice”; use host’s own history + public comps scrubbed |
| Promo copy | **High** | Draft only into `/host/announcements` / promo forms |
| Social posts | **High** | Already have Instagram captions feature |
| Email/message announcement drafts | **High** | Must never auto-dispatch CRM/email |
| FAQ generation | **Medium** | Event policies / FAQ blocks in Studio |
| Refund/cancellation copy | **Medium** | Policy-safe templates; never override platform refund rules |
| Host analytics summaries | **High** | Extend `summarize_event_performance` with redacted aggregates only |
| Audience CRM insights | **Medium–High risk** | Aggregate segments only — never raw buyer PII to provider |
| Merch product descriptions | **High** | Not in Phase 15 yet — strong Phase 1 add |
| Post-event drop ideas | **Medium** | After event memory + merch drop surfaces exist |
| Sponsorship pitch generation | **Medium** | Phase 2; use public-safe host/event facts |
| Ambassador campaign copy | **Medium** | Draft into `/host/ambassadors/campaigns/*` |

### Host recommendations

**Build first (inline, not only `/host/ai`):**

1. Event title + description in Event Studio  
2. Merch title + description in Merch Studio  
3. Announcement / WhatsApp / email drafts on create screens  
4. Analytics “explain this week” on `/host/analytics` and per-event analytics  

**Wait:** dynamic pricing that changes live tiers; CRM messages that auto-send; insights that require shipping PII or private venue addresses to a model.

**Data needed:** event title/city/public category/date/capacity/public venue name (respect location privacy mode — never hidden street), ticket tier names + prices the host already set, aggregate analytics, host notes the user typed.

**Risks:** leaking private location; hallucinated dates/prices; hosts treating pricing as platform advice; auto-send temptation in announcements UI.

---

## 2. Fan AI

| Opportunity | Fit now? | Notes |
|-------------|----------|--------|
| Event recommendations | **Later** | Rules + taxonomy + Picks first; LLM optional for “why this event” blurbs only |
| “Events near me” | **Rules first** | `/events/near-me` is placeholder; use coarse city/opt-in geo — no creepy tracking |
| Fan Passport bio | **Shipped** | `fan.passport.bio` on `/dashboard/passport/settings` — public fields + notes only; manual save |
| Fan Connect suggestions explanation | **Phase 2** | Natural-language rewrite of **safe reason codes only** — do not re-rank yet |
| Itinerary / night-out planning | **Later** | Fun but low core-commerce value; privacy-sensitive |
| Merch recommendations | **Later** | High creep risk; start with “same event / same host” rules |
| Support self-help | **Phase 1–2** | Enhance Help deflection (`/help` suggestions) — already rule/KB based |
| Ticket/order lookup guidance | **Phase 1–2** | Guided flows + KB; LLM only for clarifying questions, not account takeover |

**Fan AI principle:** Prefer **explain / draft / guide**. Avoid **rank people** or **infer private life** from tickets, spend, or messages.

---

## 3. Admin AI

| Opportunity | Fit | Human review required? |
|-------------|-----|------------------------|
| Support ticket triage | **High** | Yes — suggest category/priority only |
| Report/abuse summarization | **High** | Yes |
| Fraud signal summaries | **Phase 3** | Yes — placeholders exist; do not auto-act |
| Event moderation assistance | **Medium** | Yes — never auto-approve/reject alone |
| Merch moderation assistance | **Medium** | Yes |
| User risk summaries | **Phase 3** | Yes — never auto-suspend |
| Refund dispute summaries | **Medium–High** | Yes — Support escalate-only; finance decides |
| Admin analytics summaries | **High** | Yes (advisory) |
| Email/template drafting | **Medium** | Yes — admin email templates |
| Content/blog drafts | **High** | Yes — editor publishes |

**Hard rule:** AI must not execute moderation, refund, payout, ban, or featured-placement writes. Admin Copilot remains suggestion-only.

---

## 4. Support AI

Existing strengths: Help-first guided flow, knowledge base articles, deflection metadata on tickets (`deflection_meta`, suggested article IDs), staff desks at `/support/desk`, `/admin/support/*`.

| Opportunity | Recommendation |
|-------------|----------------|
| AI help before ticket creation | **Yes (Phase 1–2)** — suggest KB articles from topic + free text; keep current deflection analytics |
| Suggested help articles | **Yes** — hybrid: keyword/taxonomy first, LLM re-rank optional |
| Ticket category detection | **Yes (Phase 1)** — suggest; agent confirms |
| Priority detection | **Yes (Phase 1)** — suggest; flag safety keywords to humans immediately |
| Suggested admin replies | **Yes (Phase 1)** — **compose into draft box only** |
| Summarize conversation history | **Yes (Phase 1)** — staff-only; redact payments/QR/Vault |
| Detect urgent/safety issues | **Yes (Phase 1)** — classifier → queue flag; never auto-close |

### Non-negotiable

> **AI must not auto-send support replies.** Every reply requires a human click. Log who accepted/edited the draft.

---

## 5. Event discovery / recommendation AI

### Now vs later

| Approach | Status |
|----------|--------|
| Taxonomy hubs, facets, weekend/free/VIP, featured placements / Pàdéyá Picks | **Shipped — keep as primary** |
| Marketplace `sort=recommended` + proximity hints | **Rules / ranking signals — keep** |
| LLM-powered personalized feed | **Phase 3+** — needs retention, evaluation, privacy design |
| “Why recommended” blurbs from public event fields | **Phase 2 optional** |

### Rules first (recommended)

1. Location hierarchy + category + date windows  
2. Editorial Picks / placements  
3. Collaborative signals later (same host follow / same category ticket) as **anonymous aggregates**  
4. Explicit opt-in for any finer location

### Creep / privacy avoidance

- Do not continuously track GPS for recommendations.  
- Near-me: user-initiated, coarse (city/area), clear UI consent, short-lived client coords — never store precise lat/lng in AI prompts or long-term profiles without a dedicated privacy design.  
- Never use private/hidden venue, VIP spend, or Fan Connect graph in public discovery ranking.  
- Align with [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md) scrubbing.

---

## 6. Fan Connect AI

### Current algorithm (keep)

Deterministic `FanConnectScoringService` (0–100), eligibility gates, **safe reason codes only**, opt-in defaults off, no GPS, private events never used. Documented in [FAN_CONNECT.md](./FAN_CONNECT.md) and [FAN_CONNECT_SUGGESTION_ALGORITHM_AUDIT.md](./FAN_CONNECT_SUGGESTION_ALGORITHM_AUDIT.md).

### AI role recommendation

| Role | Verdict |
|------|---------|
| Explain suggestions (NL from safe reasons) | **Allowed later (Phase 2)** |
| Help rank suggestions | **Defer (Phase 3+)** — only after offline eval; AI must not bypass eligibility |
| Replace scoring | **Do not** |
| Read full DMs to improve match | **Never** |

### Safe to use (with user consent / public-safe only)

- Safe reason codes + public event titles already shown on cards  
- Shared public hosts / categories / dual-opt-in city labels  
- Public badge names  

### Never send to an AI provider

- Phone, email, WhatsApp, device IDs  
- Private / unlisted Passport fields  
- Private attendance, hidden venues, ticket type, VIP/table, order/payment/refund/spend  
- Full message bodies / attachments  
- CRM notes, admin notes, Vault bodies  
- Block/report internal details beyond staff-only tools  
- Graph dumps (“everyone this user declined”)  

---

## 7. Merch AI

| Opportunity | Phase | Risk |
|-------------|-------|------|
| Title / description generation | **1** | Low–medium (hallucinated materials/claims) |
| Category / tag suggestions | **1** | Low — constrain to catalog |
| Product image prompt suggestions | **2** | Medium — copyright / brand misuse |
| Post-event drop ideas | **2** | Low–medium |
| Inventory / low-stock insights | **2** | Low if aggregates only |
| Host shop optimization | **2** | Medium |
| Buyer merch recommendations | **3** | **High** creep / fairness |

Wire into `/host/merchandise/new` and Merch Studio editors. Never expose buyer shipping PII or payment refs in prompts. Public teaser rules for Vault-exclusive merch stay intact.

---

## 8. Sponsorship AI

| Opportunity | Phase | Notes |
|-------------|-------|--------|
| Sponsor–host matching | **3** | Needs marketplace maturity + brand-safety policy |
| Sponsor pitch generation | **2** | Host drafts from public-safe metrics |
| Host media kit summaries | **2** | From Legacy/public analytics aggregates |
| Sponsor inquiry summarization | **2** | Host/admin assist |
| Brand safety checks | **2–3** | Assist only — human final call |

Keep sponsorships isolated from ticketing/payments/Vault checkout (existing product boundary).

---

## 9. Blog / Content AI

| Opportunity | Phase | Route |
|-------------|-------|--------|
| Blog draft generation | **1–2** | `/admin/blog/new`, edit |
| SEO meta descriptions | **1** | Blog SEO fields |
| Article outlines | **1** | Same |
| Related post suggestions | **2** | Rules + embeddings later |
| Category/tag suggestions | **1** | Constrained vocab |
| Newsletter / social snippets | **2** | Admin drafts |

Never invent legal/policy claims that contradict `/terms`, `/privacy`, refund/ticket policies.

---

## 10. Security, privacy, and compliance

### Hard denylist (never send to providers)

| Data class | Examples |
|------------|----------|
| Secrets | Passwords, JWT/refresh tokens, `SECRET_KEY`, Paystack keys, `AI_API_KEY`, encryption keys |
| Payments | Raw Paystack payloads, full PAN (N/A), provider refs beyond scrubbed IDs staff already see in-app |
| Tickets | QR secrets, jti, rotating token material, device bindings |
| Vault | Locked bodies, private media URLs, invite codes |
| Location | Private/hidden venue streets, exact GPS, private join URLs |
| Messaging | Full private message bodies / attachments unless **explicit staff tool + permission + ticket scope** |
| Admin internals | Admin notes, impersonation details, internal fraud playbooks → never to end users |
| Fan Connect | Private graph details beyond safe public reasons |

### Decision autonomy denylist

AI must **not** finally decide:

- Moderation hide/remove  
- Refunds / payouts / fee changes  
- Suspensions / bans / restrictions  
- Featured placement publish  
- Fan Connect accept/block  
- Ticket issuance  

### Required controls

- Redaction layer before prompt assembly (`ai_context_scrubber`)  
- Audit logs for every generate / accept / reject / apply-to-field  
- Feature-level kill switches + global `AI_ENABLED`  
- No AI impersonation of admins/users in outbound email or chat  
- Retention limits on stored prompts/outputs  
- Staff-only features require `ai.use_platform` (or narrower future perms)

---

## 11. Architecture (recommended)

Build on existing `backend/app/ai/` — do not fork a second stack.

```text
┌──────────── FE (Host / Admin / Support / optional Fan) ────────────┐
│  “Generate” / “Suggest reply” → copy into editable fields only      │
└───────────────────────────────┬────────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────────┐
│  AI API (FastAPI) — authz, feature toggle, rate limit, spend check │
│  Prompt registry (DB) → Context builder → Redaction → Provider     │
│  Output validation / safety filter → Usage + audit + optional store│
└───────────────────────────────┬────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
  Provider adapters      Background jobs          Human review
  (OpenAI-compat,        (long summaries,         (draft inbox;
   Anthropic, Gemini,     batch admin jobs)        accept/edit/reject)
   Grok, template)
```

### Components

| Component | Purpose |
|-----------|---------|
| AI service layer | Single entry: `generate(feature, audience, context_ref)` |
| Provider abstraction | Protocol already exists — extend adapters; **never hardcode one vendor in product code** |
| Admin-configurable provider/model | Eventually DB settings + encrypted key strategy (see §12) |
| Prompt registry | `ai_prompts` / existing `ai_prompt_templates` with versioning |
| Output validation | Length, banned patterns (contact harvest, fake policy), JSON schema where structured |
| Moderation/safety filters | Pre/post checks; escalate safety keywords |
| Token/cost tracking | Extend `ai_usage_logs` with estimated cost + monthly rollups |
| Rate limits | Per user, per host, per feature, global |
| Background jobs | Summaries / batch triage via existing worker patterns |
| Retries/timeouts | Already partial via `AI_TIMEOUT_SECONDS` |
| Streaming | Optional for Studio UX later — not required for Phase 1 |
| Caching | Cache identical host drafts briefly; **never cache** staff summaries of private tickets across users |
| Human review workflow | `ai_generation_outputs.status`: draft → accepted / edited / rejected |
| Audit logs | Mirror sensitive accepts into `audit_logs` |

---

## 12. Provider strategy

### Recommendation

| Provider | Role |
|----------|------|
| **OpenAI-compatible** (current) | Default production path when enabled |
| **Anthropic** | Strong alternative for long staff summaries |
| **Gemini** | Optional; good multimodal later (image prompts) |
| **Grok** | Optional alternative — same abstraction |
| **Template / local fallback** | Keep forever for `AI_ENABLED=false` and outages |

**Do not hardcode one provider** in feature code. Select via settings: `provider` + `model` + credentials.

### Admin settings (target state)

| Setting | Notes |
|---------|--------|
| Provider | Enum |
| Model | String |
| API key | Encrypted at rest; masked in UI; prefer env Class A initially, then specialist table like email SMTP |
| Feature toggles | Per `feature_key` |
| Monthly spend limit | Soft block + alert |
| Per-feature limits | Tokens / requests |
| Test connection | Reuse pattern from `runtime_settings/test_actions.py` |
| Disable AI globally | `AI_ENABLED` / admin override |

Until a deliberate secrets design ships, keep **`AI_API_KEY` env-only** (current Class A posture).

---

## 13. Data model audit (recommend only — do not implement)

| Table | Purpose |
|-------|---------|
| `ai_provider_settings` | Active provider/model/base URL; encrypted key ref; global enable |
| `ai_prompts` | Versioned prompts (evolve from `ai_prompt_templates`) |
| `ai_feature_settings` | Per-feature enable, limits, audience, requires_review |
| `ai_usage_logs` | **Exists** — extend cost, latency, feature, redaction flags |
| `ai_generation_requests` | Request envelope (feature, actor, resource refs, scrubbed context hash) |
| `ai_generation_outputs` | Model text, status (draft/accepted/edited/rejected), editor user |
| `ai_moderation_logs` | Safety filter hits |
| `ai_audit_logs` | Or dual-write to existing `audit_logs` for accepts/applies |
| `ai_feedback` | Thumbs / “used in publish” for quality loop |

**Lifecycle:** Prefer soft-deactivate prompts; usage/moderation/audit append-only; outputs retain with TTL policy. Document in `docs/CRUD_MATRIX.md` before implementing.

---

## 14. Prioritization roadmap

### Phase 1 — Highest value, lowest risk

1. Architecture hardening: redaction, feature toggles, spend/rate limits, audit on accept  
2. Event Studio inline title + description (existing features, better UX)  
3. Merch title + description generator  
4. Support: category/priority suggest + **draft replies** + conversation summarize (no auto-send)  
5. Admin analytics / support queue summaries (improve existing)  
6. Blog SEO meta + outline helper  

### Phase 2 — Medium risk/value

1. Host analytics narrative insights (aggregates only)  
2. Promo / social / announcement drafts in-context  
3. Sponsorship pitch + inquiry summaries  
4. Fan Passport bio optimizer (opt-in)  
5. Fan Connect **explanation** of safe reasons  
6. Email template drafting for admin  
7. FAQ / refund policy copy assists  
8. Ambassador campaign copy  

### Phase 3 — Higher risk / needs more data

1. Personalized event recommendations (LLM rank)  
2. Fan Connect **ranking** assist  
3. Fraud / high-risk host analysis beyond placeholders  
4. Automated moderation suggestions that can write (still human-confirm, but higher blast radius)  
5. Dynamic pricing  
6. Refund **decision** suggestions tied to finance actions  
7. Buyer merch personalization  
8. Itinerary / night-out planners with location  

---

## 15. Feature catalog (detailed)

Legend: **Privacy** / **Cost** / **Difficulty** / **Value** = Low · Medium · High  
**HR** = human review required

### Host

| Feature | Role | Page/route | Code area | Inputs | Outputs | Privacy | Cost | Diff | Value | HR | Phase | Notes |
|---------|------|------------|-----------|--------|---------|---------|------|------|-------|----|-------|-------|
| Event title generator | Host | `/host/events/new`, edit Studio | `events/studio`, `app/ai` | Vibe, city, category, notes | 3–5 titles | L | L | L | H | Yes | **1** | Exists; inline UX |
| Event description generator | Host | Studio Basics | same | Title, public venue, category, notes | 120–180w draft | L–M | L | L | **H** | Yes | **1** | Top candidate |
| Category suggestions | Host | Studio taxonomy | `taxonomy`, `app/ai` | Title, notes, controlled vocab | Category/tag IDs | L | L | M | M | Yes | 1–2 | Constrain to DB vocab |
| Ticket tier copy | Host | Studio tickets / `/tickets` | `TicketTypeBuilder`, `app/ai` | Event context | Tier blurbs | L | L | L | M | Yes | 1 | Exists |
| Pricing suggestions | Host | Studio tickets | `app/ai` | Capacity, category, current tiers, city | Ranges + rationale | M | M | M | M | Yes | 2 | Advisory only |
| Promo strategy | Host | `/host/promos`, announcements | `promos`, `app/ai` | Metrics aggregates | Plan draft | M | M | M | M | Yes | 2 | Exists |
| Instagram / social captions | Host | `/host/events/[id]/ai` + share | `app/ai` | Event public fields | Captions | L | L | L | H | Yes | 1 | Exists |
| WhatsApp broadcast draft | Host | Announcements | `crm`, `app/ai` | Event fields | Short draft | L | L | L | H | Yes | 1 | Never auto-send |
| Email announcement draft | Host | `/host/announcements/new` | `host.announcements.draft`, `announcements_context` | Event + segment label + notes | Subject/body/WhatsApp | M | M | M | H | Yes | **Shipped** | Draft-only; no auto-dispatch |
| FAQ generation | Host | Studio policies | studio | Description, policies | FAQ Q/A | L | L | M | M | Yes | 2 | |
| Refund/cancellation copy | Host | Studio policies | studio | Policy notes | Attendee-facing copy | M | L | M | M | Yes | 2 | Align with platform policy |
| Analytics summary | Host | `/host/analytics`, event analytics | `analytics`, `app/ai` | Aggregates only | Narrative + 3 actions | M | M | M | H | Yes | 1–2 | Exists partially |
| Audience CRM insights | Host | `/host/audience` | `crm` | Segment counts, no PII | Insights | **H** | M | H | M | Yes | 3 | Aggregates only |
| Merch description | Host | Merch Studio | `merch`, `app/ai` | Title, event, notes | Description | L | L | L | **H** | Yes | **1** | New |
| Post-event drop ideas | Host | drops / memory | `merch`, memories | Event + sales aggregates | Ideas | L | L | M | M | Yes | 2 | |
| Sponsorship pitch | Host | `/host/sponsorships` | `host.sponsorship.pitch`, `sponsorship_context` | Public metrics, slot type, notes | Pitch + bullets + package | M | M | M | M | Yes | **Shipped** | Draft-only; no auto-send |
| Ambassador campaign copy | Host | `/host/ambassadors/campaigns/*` | `ambassadors` | Campaign fields | Copy | L | L | L | M | Yes | 2 | |
| Event recap draft | Host | `/host/events/[id]/memory/edit` | memories, `app/ai` | Metrics + notes | Recap | L | L | L | M | Yes | 1 | Exists |
| Legacy tier path | Host | Legacy studio | `legacy`, `app/ai` | Tier progress | Actions | L | L | L | M | Yes | 2 | Exists |

### Fan

| Feature | Role | Page/route | Code area | Inputs | Outputs | Privacy | Cost | Diff | Value | HR | Phase | Notes |
|---------|------|------------|-----------|--------|---------|---------|------|------|-------|----|-------|-------|
| Event recommendations | Fan | `/events`, home | discovery | Public prefs, history aggregates | Ranked events | **H** | H | H | H | Soft | **3** | Rules first |
| Near-me suggestions | Fan | `/events/near-me` | discovery | Coarse city / opt-in | Event list | **H** | M | M | M | Soft | 2–3 | No continuous GPS |
| Passport bio improve | Fan | `/dashboard/passport/settings` | `passport` | Current bio + notes | Bio draft | M | L | L | M | Yes | 2 | Opt-in |
| Connect explanation | Fan | `/connect/suggestions` | `fan_connect` | Safe reasons only | Sentence | L | L | L | M | Soft | 2 | No re-rank |
| Connect ranking | Fan | suggestions | scoring | — | Reordered list | **H** | H | H | M | Soft | **3** | Avoid for now |
| Itinerary planner | Fan | TBD | — | Location + dates | Plan | **H** | H | H | L | Yes | 3 | Defer |
| Merch recommendations | Fan | `/merch` | merch | Browse history | Products | **H** | M | H | M | Soft | 3 | Creep risk |
| Support self-help | Fan | `/support/new`, `/help` | KB + support | Topic + text | Articles | L | L | M | H | Soft | 1–2 | Enhance deflection |
| Ticket/order guidance | Fan | `/dashboard/tickets`, support | support | User question | Steps | M | L | M | M | Soft | 1–2 | No secret reveal |

### Admin / Support

| Feature | Role | Page/route | Code area | Inputs | Outputs | Privacy | Cost | Diff | Value | HR | Phase | Notes |
|---------|------|------------|-----------|--------|---------|---------|------|------|-------|----|-------|-------|
| Support triage (category) | Support/Admin | `/admin/support/[id]`, desk | `support`, `app/ai` | Subject/body scrubbed | Category suggest | M | L | M | H | Yes | **1** | |
| Priority detection | Support/Admin | same | same | Text + signals | Priority + flags | M | L | M | H | Yes | **1** | Safety → human |
| Suggested replies | Support/Admin | case detail composer | same | Thread summary | Draft reply | **H** | M | M | **H** | **Yes** | **1** | Never auto-send |
| Conversation summarize | Support/Admin | case detail | same | Thread (permissioned) | Summary | **H** | M | M | H | Yes | **1** | Staff only |
| Urgent/safety detect | Support/Admin | queue | same | Text | Flag | M | L | M | H | Yes | **1** | |
| Help article suggest | User/Support | `/support` guided | KB | Query | Articles | L | L | M | H | Soft | 1 | |
| Abuse report summarize | Admin | message/FC/merch reports | moderation | Report fields | Summary | **H** | M | M | H | Yes | 1–2 | |
| Review report summarize | Admin | `/admin/reviews` | reviews, `app/ai` | Open reports | Summary | M | L | L | M | Yes | 1 | Exists |
| Fraud signal summary | Admin | `/admin/analytics/support` | analytics, `app/ai` | Aggregates | Narrative | **H** | H | H | M | Yes | **3** | Placeholder today |
| Event moderation assist | Admin | admin events | events | Public listing fields | Risk notes | M | M | M | M | Yes | 2 | |
| Merch moderation assist | Admin | `/admin/merchandise` | merch | Listing fields | Notes | M | M | M | M | Yes | 2 | |
| User risk summary | Admin | `/admin/users/[id]` | users | Flags/restrictions metadata | Summary | **H** | M | H | M | Yes | **3** | No auto-status |
| Refund dispute summary | Admin/Finance | `/admin/refunds` | finance | Case + order scrubbed | Summary | **H** | M | M | M | Yes | 2 | No auto-refund |
| Revenue trends explain | Admin | `/admin/analytics/revenue` | analytics, `app/ai` | Aggregates | Narrative | L | M | L | M | Yes | 1 | Exists |
| Featured event recommend | Admin | placements | placements, `app/ai` | Top events | Suggestions | L | L | L | M | Yes | 2 | Exists |
| Blog draft / SEO meta | Admin | `/admin/blog/*` | blog | Outline, title | Draft/meta | L | M | L | H | Yes | **1** | |
| Email template draft | Admin | `/admin/emails/templates/*` | email | Template key, purpose | Draft | M | M | M | M | Yes | 2 | |

### Merch / Sponsorship / Content (cross-cutting already partially above)

See §§7–9. Buyer-facing merch ranking and sponsor auto-matching stay Phase 3.

---

## 16. Final recommendation

### Top 5 AI features to build first

1. **Event Studio description + title** (inline; reuse existing generate features)  
2. **Merch title/description generator** in Merch Studio  
3. **Support suggested replies + triage + summarize** (human send only)  
4. **Admin/support queue & analytics summaries** (harden placeholders; still advisory)  
5. **Blog SEO meta / outline helper**  

### Top 5 AI features to avoid for now

1. **Fan Connect ranking / replacement of deterministic scoring**  
2. **Automated moderation / suspension / refund decisions**  
3. **Dynamic pricing that mutates live ticket prices**  
4. **Personalized discovery that depends on precise location or private attendance**  
5. **Any auto-send of support, CRM, or Fan Connect messages**  

### Required architecture before broader rollout

- Single AI service layer + provider protocol (extend existing)  
- Context redaction denylist enforced in one place  
- Feature toggles + global disable  
- Usage/cost tracking + rate limits  
- Human-review status on outputs for staff tools  
- Audit events on generate and on “apply/accept”  

### Recommended admin controls

- Global enable/disable  
- Provider + model (+ test connection)  
- Per-feature toggles and quotas  
- Monthly spend cap  
- Masked API key management (env-first, then encrypted settings)  
- Usage dashboard (missing today)  

### Recommended provider strategy

- Abstraction-first; OpenAI-compatible as current default path  
- Add Anthropic / Gemini / Grok as adapters without feature-level hardcoding  
- Always keep template fallback  

### Security rules (short list)

1. Never send secrets, QR material, raw payments, Vault locked content, or private venues.  
2. Never auto-send support/CRM; never auto-write finance/moderation.  
3. Fan Connect: explain safe reasons only; do not feed private graph/DMs.  
4. Log AI actions; prefer aggregates over PII.  
5. AI must not impersonate staff or users in outbound channels.  

### Next implementation prompt suggestion

Use a focused follow-up like:

> Implement Phase 1 AI hardening + Event Studio inline description/title generation for Pàdéyá.  
> Extend `backend/app/ai` with context redaction, feature toggles, and audit-on-accept.  
> Wire “Generate with AI” into Event Studio Basics (reuse `generate_event_title` / `generate_event_description`).  
> Do not add new provider keys to the repo; do not auto-publish; do not build Fan Connect ranking, fraud automation, or merch buyer recommendations yet.  
> Update `docs/CRUD_MATRIX.md` for any new AI tables only if migrations are included; otherwise keep schema changes out of this PR.

---

## Appendix A — Key code & doc references

| Resource | Path |
|----------|------|
| AI module | `backend/app/ai/` |
| Host/Admin UI | `frontend/src/app/host/ai`, `.../events/[id]/ai`, `frontend/src/app/admin/ai` (+ `settings`/`features`/`usage`/`playground`), `.../support/ai-summary` |
| Client API | `frontend/src/lib/ai-api.ts` |
| Permissions | `ai.use_own`, `ai.use_platform` |
| Fan Connect scoring | `backend/app/fan_connect/scoring.py` |
| Support deflection | `backend/app/support/service.py`, KB `/help` |
| Security AI section | [SECURITY.md](./SECURITY.md#ai-copilot-phase-15) |
| Runtime AI settings audit | [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md) |
| Roadmap Phase 15 | [ROADMAP.md](./ROADMAP.md) |
| Privacy | [PRIVACY.md](./PRIVACY.md), [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md) |

## Appendix B — Decision record

| Decision | Choice |
|----------|--------|
| Implement AI in this audit? | **No** |
| Replace Fan Connect algorithm with AI? | **No** |
| Primary near-term value? | Host copy + support drafts + Studio UX |
| Recommendations engine? | Rules/editorial first; AI later |
| Provider lock-in? | **Forbidden** — abstraction required |

---

*End of audit. Brand spelling: **Pàdéyá**.*
