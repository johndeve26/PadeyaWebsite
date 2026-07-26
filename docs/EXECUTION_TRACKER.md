# Execution tracker

Brand: **Pàdéyá**

Lightweight log of verification runs for major product domains. Not a roadmap.

---

## SEO production indexability regression (2026-07-26)

**Regression audit = implemented in workspace** — PageSpeed `/events` “blocked from indexing” investigation; live public inventory verified; `buildPageMetadata` robots wipe fixed; env contradiction hardened; www→apex redirect; smoke + `seo:indexability-audit` hardened.

Canonical: [SEO_AUDIT.md](./SEO_AUDIT.md#production-indexability-regression-audit--2026-07-26) · [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md).

| Item | Status |
|---|---|
| Live `/events` noindex today | **Not present** (LIVE VERIFIED indexable; missing explicit robots meta pre-fix) |
| Root cause class | Metadata merge wipe + env contradiction risk + www duplicate host |
| Accidental public noindex on live | **0** found |
| Code fixes | **Done** (await deploy for LIVE re-verify of explicit `index,follow` + www redirect) |
| `seo:production-smoke` noindex hard-fail | **Done** |
| `seo:indexability-audit` | **Done** |

---

## Performance Phase 3.6 — /events mount RSC closure (2026-07-26)

**Phase 3.6 = implemented in workspace** — stop bare `/events` from `router.replace` into `price_max=500` / `lat=0&lng=0` (Number(null) trap + default price sync). Event/merch CLS already **LIVE CLOSED** at 0. **Await /events n=3 + SEO to close Phase 3.**

| Item | Status |
|---|---|
| price_max mount RSC | **CODE-LEVEL** fixed (`syncPriceToUrl`) |
| lat=0/lng=0 mount RSC | **CODE-LEVEL** fixed (`parseLatLngSearchParams`) |
| `/?_rsc` repeats | Secondary to soft-nav storm (Logo prefetch) |
| Maintenance GET vs OPTIONS | Documented — target ≤1 GET |
| Local tests / build / `test:seo` | **Passed** (LOCAL) |
| Post-deploy `/events` LH n=3 | **NOT YET DEPLOYED** |

---

## Performance Phase 3.5 — Targeted cleanup (2026-07-26)

**Phase 3.5 = implemented in workspace** — `/events` Link `prefetch={false}` on dense cards; maintenance status single-flight; event/merch Suspense stable fallbacks (fixes footer.mt-auto CLS); `lighthouse-summary.mjs`. **Await deploy + n=3 Lighthouse before closing Phase 3.**

| Item | Status |
|---|---|
| Events RSC prefetch root cause (viewport Link prefetch) | **CODE-LEVEL** identified + fixed |
| Maintenance duplicate Gate+Banner | **CODE-LEVEL** single-flight |
| Event/merch CLS = footer after `fallback={null}` | **LIVE LAB** + **CODE-LEVEL** fix |
| Home LCP | Hero already priority; remaining = TTFB/image load (**LIVE LAB**) |
| vitest + `npm run build` + `test:seo` | **Passed** (LOCAL) |
| Post-deploy LH n=3 | **NOT YET DEPLOYED** |

---

## Performance Phase 3 — Browser / Core Web Vitals (2026-07-26)

**Phase 3 = implemented in workspace** — next/image Media + trusted `remotePatterns`, LCP `priority` on heroes only, Logo CLS fix, variable Manrope, dynamic map/gallery/QR/auth chrome, YouTube click-to-play, idle PWA register. **Post-deploy Lighthouse/CWV not claimed until remeasure.** Fan Passport HTML remains **force-dynamic/no-store**.

Canonical: [PERFORMANCE_IMPLEMENTATION.md](./PERFORMANCE_IMPLEMENTATION.md#phase-3--browser--core-web-vitals) · [`performance-phase3-baseline.json`](./performance-phase3-baseline.json) · [`performance-phase3-after.json`](./performance-phase3-after.json).

| Item | Status |
|---|---|
| Phase 3 Lighthouse baseline (prod mobile n=1) | **LIVE LAB MEASURED** |
| Media / next/image + remotePatterns | **Done** (CODE-LEVEL) |
| LCP hero priority + card sizes | **Done** (CODE-LEVEL) |
| Footer Logo CLS (`width:auto` removed) | **Done** (CODE-LEVEL) |
| Variable Manrope | **Done** (~24.6 KB primary; LOCAL BUILD) |
| Dynamic QR / map / gallery / auth chrome | **Done** (CODE-LEVEL) |
| YouTube facade on event gallery | **Done** (CODE-LEVEL) |
| Fan Passport no-store | **Preserved** (LOCAL test) |
| `npm run build` + `test:seo` | **Passed** (LOCAL) |
| Post-deploy Lighthouse / HTTP remeasure | **Pending deploy** |
| Field CWV | **NOT MEASURED** |

---

## Performance Phase 2 — Next.js SSR / CDN (2026-07-26)

**Phase 2 = deployed & production verified** — RSC AbortSignal removed, React `cache()` loaders, hub ISR, Fan Passport **force-dynamic/no-store**, fan revalidate route, facet `noindex,follow`.

Canonical: [PERFORMANCE_IMPLEMENTATION.md](./PERFORMANCE_IMPLEMENTATION.md) · baseline [`performance-phase2-baseline.json`](./performance-phase2-baseline.json).

| Item | Status |
|---|---|
| Phase 2 baseline (MISS + private no-store on hubs/entities) | **LIVE VERIFIED** |
| AbortSignal / Data Cache root cause | **Fixed** |
| Fan Passport HTML no-store (PUBLIC→PRIVATE safe) | **Done** (hardened) |
| Deployed FE HIT + totals | **LIVE VERIFIED** (user) |
| Phase 3 images/fonts/CWV | **Done in workspace** (see above) |

---

## Performance Phase 1 — API/query latency (2026-07-26)

**Phase 1 = implemented in workspace** — events list SQL filters/order/limit + lean list DTO (`listv2` cache key), sponsor public batched loads, Legacy public no-rescore path, maintenance 15s off-allow cache, request-scoped RBAC memo, host workspaces single-flight. **No speculative DB indexes. Production improvement not claimed until post-deploy measurement.**

Canonical: [PERFORMANCE_IMPLEMENTATION.md](./PERFORMANCE_IMPLEMENTATION.md) · [PERFORMANCE_AUDIT.md](./PERFORMANCE_AUDIT.md) · baseline [`performance-phase1-baseline.json`](./performance-phase1-baseline.json).

| Item | Status |
|---|---|
| Phase 1 baseline capture (pre-change prod) | **Done** (Phase 0 undeployed → no Server-Timing) |
| Events SQL list + lean DTO | **Done** (CODE-LEVEL) |
| Sponsor / Legacy public optimizations | **Done** (CODE-LEVEL) |
| Maintenance decision cache | **Done** (CODE-LEVEL) |
| Request-scoped RBAC memo | **Done** (CODE-LEVEL) |
| Host workspaces single-flight | **Done** (CODE-LEVEL + vitest) |
| Speculative indexes | **None** |
| Local tests (`test_performance_phase1` + vitest) | **Passed** |
| Deployed before/after production timings | **Pending deploy** |
| Phase 2 SSR / images / CDN / geography | **Out of scope** (next) |

---

## Performance Phase 0 — reliability & observability (2026-07-26)

**Phase 0 = implemented** — request timing middleware, X-Request-ID, Server-Timing, `/health` vs `/ready`, frontend timeout policy, Redis socket timeouts, maintenance/RBAC instrumentation, safe global 500 handler, audit script terminology cleanup, regression tests for maintenance seed + unread poll guard.

Canonical: [PERFORMANCE_IMPLEMENTATION.md](./PERFORMANCE_IMPLEMENTATION.md) · [PERFORMANCE_AUDIT.md](./PERFORMANCE_AUDIT.md).

| Item | Status |
|---|---|
| FastAPI timing + slow labels | **Done** |
| X-Request-ID + Server-Timing | **Done** |
| `/ready` (SELECT 1) vs cheap `/health` | **Done** |
| Frontend central timeouts | **Done** |
| Redis socket timeouts (fail-open cache) | **Done** |
| Maintenance/RBAC observability | **Done** |
| Exception handler (no traceback to clients) | **Done** |
| Regression: maintenance seed + unread poll | **Done** |
| Phase 1 query optimizations | **See Phase 1 section above** |

---

## SEO post-implementation audit (2026-07-24)

**Re-audit after Phases 0A–0C + 1A–1C.** Dual scores: code **88 / 100** (was **52**); live `padeya.com` **54 / 100**. Production smoke **FAILED** — phases implemented in workspace but **not deployed** at audit time. Launch: **not ready**.

Canonical: [SEO_AUDIT.md](./SEO_AUDIT.md#post-implementation-audit--2026-07-24) · [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md) · [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md).

| Item | Status |
|---|---|
| Code P0s (13) | **FIXED** in workspace |
| Live P0s | **STILL OPEN** (undeployed) |
| `seo:production-smoke` @ padeya.com | **FAILED** |
| GSC indexing request | **Blocked** until green smoke |
| Next action | Commit/deploy phases → re-smoke → then GSC |

---

## SEO Phase 1C — GSC / analytics / production smoke (2026-07-24)

**Phase 1C = implemented** — optional GSC/Bing verification metadata via env; first-party analytics kept primary; optional consent-gated GA4; production SEO smoke script; [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md).

Canonical: [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO.md](./SEO.md) · [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md).

| Item | Status |
|---|---|
| `GOOGLE_SITE_VERIFICATION` / Bing meta (env-only) | **Done** |
| First-party analytics primary | **Done** |
| Optional GA4 + consent on `/cookies` | **Done** |
| `seo-production-smoke.mjs` | **Done** |
| Launch checklist + CWV notes | **Done** |
| `npm run test:seo` + `npm run build` | **Done** |
| Live GSC verify + sitemap submit | **Ops** (post-deploy) |
| Dynamic OG / sitemap sharding | **Out of scope** |

---

## SEO Phase 1B — Faceted nav + location SEO (2026-07-24)

**Phase 1B = implemented** — faceted `/events` noindex + canonical `/events`; `/events/search` noindex/follow + canonical `/events`; location SEO columns + thin-hub thresholds; city×category gates; image alts; sitemap eligibility aligned; event location/host crawl links.

Canonical: [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO.md](./SEO.md).

| Item | Status |
|---|---|
| Faceted `/events` policy | **Done** |
| `/events/search` noindex + canonical `/events` | **Done** (no redirect) |
| Location SEO fields + thresholds | **Done** |
| City × category eligibility | **Done** |
| Image alt helpers on public media | **Done** |
| Sitemap location/combo gates | **Done** |
| `npm run test:seo` + `npm run build` | **Done** |
| Sitemap sharding / dynamic OG / GSC | **Out of scope** |

---

## SEO Phase 1A — Sitewide + Product structured data (2026-07-24)

**Phase 1A = implemented** — root Organization/WebSite `@graph`, SearchAction on working `/events?q=` (not `/events/search`), Product/Offer for indexable merch, Event `eventStatus`, BreadcrumbList on merch/host/sponsor/fan, CollectionPage/FAQ reference WebSite `@id`.

Canonical: [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO.md](./SEO.md).

| Item | Status |
|---|---|
| Organization `https://padeya.com/#organization` | **Done** |
| WebSite `https://padeya.com/#website` | **Done** |
| SearchAction (`/events?q=`) | **Done** (documented; `/events/search?q=` rejected) |
| Product / Offer (indexable merch) | **Done** |
| Event `eventStatus` | **Done** (Scheduled/Cancelled; no Postponed/Rescheduled in model) |
| Entity BreadcrumbList | **Done** |
| `npm run test:seo` + `npm run build` | **Done** |
| Location SEO / faceted noindex / sitemap shard | **Out of scope** |

---

## SEO Phase 0C — Privacy-safe sitemap completeness (2026-07-24)

**Phase 0C = implemented** — sitemap includes Host Legacy (`/u/*` via discover), directory Fan Passports (`/f/*`), verified public Sponsors (`/sponsors/*`), `/fans`, non-empty blog category/tag/author hubs, ambassadors marketing; removed `/events/search`; entity `lastModified` from real timestamps only; privacy filter vitest + smoke.

Canonical: [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO.md](./SEO.md).

| Item | Status |
|---|---|
| Host / Fan / Sponsor entity URLs in sitemap | **Done** |
| `/fans` + ambassadors marketing | **Done** |
| Non-empty blog hubs | **Done** |
| Remove `/events/search` | **Done** |
| Entity lastModified (no invented `now`) | **Done** |
| Privacy-safe filter tests | **Done** |
| Sitemap sharding | **Not needed yet** |
| `npm run test:seo` (0A+0B+0C) | **Done** |
| Product JSON-LD / sitewide Organization | **Out of scope (later)** |

---

## SEO Phase 0B — Entity SSR SEO + soft 404s (2026-07-24)

**Phase 0B = implemented** — Host Legacy `/u/[username]` SSR metadata + ProfilePage/Organization JSON-LD; sponsor `/sponsors/[slug]` SSR + 404; `/sponsorships` + `/sponsorships/hosts` server metadata; Fan Passport `buildFanMetadata` + public Person schema / unlisted noindex; soft-404 → `notFound()` for missing events, merch, sponsors.

Canonical: [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO.md](./SEO.md).

| Item | Status |
|---|---|
| Host Legacy SSR + generateMetadata + Organization | **Done** |
| Sponsor profile SSR + generateMetadata + Organization | **Done** |
| Sponsorships marketplace route metadata | **Done** |
| Event / merch / sponsor soft-404 → HTTP 404 | **Done** |
| Fan Passport canonical/OG + public Person / unlisted noindex | **Done** |
| `npm run test:seo` (0A+0B) | **Done** |
| Sitemap entity expansion / Product JSON-LD | **Sitemap done in 0C; Product JSON-LD later** |

---

## SEO Phase 0A — Canonical / indexing safety (2026-07-24)

**Phase 0A = implemented** — production-safe `https://padeya.com` canonical origin, `metadataBase`, non-production noindex (root robots + `buildPageMetadata` + `robots.ts` Disallow `/` + middleware `X-Robots-Tag`), private/auth/checkout layout noindex, hardened production robots, unlisted/password event noindex + password meta scrub / no Event JSON-LD.

Canonical: [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO.md](./SEO.md).

| Item | Status |
|---|---|
| `getCanonicalSiteOrigin` / env indexing policy | **Done** |
| Root `metadataBase` + env robots | **Done** |
| Non-prod robots Disallow `/` (no sitemap ad) | **Done** |
| Middleware `X-Robots-Tag` | **Done** |
| Private workspace + auth + checkout noindex layouts | **Done** |
| Unlisted / password event noindex | **Done** |
| Tracking params stripped from canonicals | **Done** |
| `npm run test:seo` | **Done** |
| Host Legacy / sponsor SSR / soft-404 | **Done in 0B** |
| Sitemap entity expansion | **Done in 0C** |

---

## Event recommendations integration (2026-07-22)

**Event recommendations = integrated (rules-only; no AI ranking)** — `GET /events/recommendations`, `/events` rail + `?sort=recommended`, `/events/[slug]` detail rail, dashboard “Events for you”, impressions + unified feedback endpoint, runtime `event-recommendations`, admin debug. Backend: `tests/test_event_recommendations.py` (5). Frontend smoke: `frontend/scripts/events-recommendations-smoke.mjs`.

Canonical: [EVENT_RECOMMENDATIONS.md](./EVENT_RECOMMENDATIONS.md).

| Item | Status |
|---|---|
| GET `/events/recommendations` | **Done** |
| `/events` Recommended rail | **Done** |
| `/events?sort=recommended` | **Done** |
| Dashboard Events for you | **Done** |
| Impression + feedback loop | **Done** |
| Admin tuning + debug | **Done** |
| `/events/[slug]` detail rail | **Done** |

---

## Host recommendations integration (2026-07-22)

**Host recommendations = integrated (rules-only; no AI ranking)** — `/hosts` rail + `?sort=recommended`, impression batch API, dismiss/not-interested/more-like/click/follow, runtime category `host-recommendations`, admin debug endpoint. Backend tests: `tests/test_host_recommendations.py` (7). Frontend smoke: `frontend/scripts/hosts-recommendations-smoke.mjs`.

Canonical: [HOST_RECOMMENDATIONS.md](./HOST_RECOMMENDATIONS.md) · [API.md](./API.md#fan-host-recommendations-rules-only).

| Item | Status |
|---|---|
| GET `/hosts/recommendations` | **Done** |
| `/hosts` Recommended rail (signed-in) | **Done** |
| `/hosts?sort=recommended` | **Done** |
| Impression tracking | **Done** |
| Feedback loop | **Done** |
| Admin tuning + debug | **Done** |
| Safe reason chips | **Confirmed** |

---

## Phase 1 Blog AI helper (2026-07-22)

**Blog AI = implemented (docs + code; no new provider keys; no tests)** — `admin.blog.title` / `outline` / `excerpt` / `seo_meta` / `tags` / `social_snippets` with blog scrubbing, draft validation, usage/audit, and `BlogAIAssist` on `/admin/blog/new` and `/admin/blog/[postId]/edit`. Never auto-publishes.

Canonical: [AI_INTEGRATION_AUDIT.md](./AI_INTEGRATION_AUDIT.md) · [SECURITY.md](./SECURITY.md#ai-copilot-phase-15--phase-1-hardening) · [API.md](./API.md#ai-copilot-phase-15--phase-1-hardening).

| Item | Status |
|---|---|
| Title ideas (3–5, click to apply) | **Implemented** |
| Outline draft (apply / copy / regenerate / dismiss) | **Implemented** |
| Excerpt draft | **Implemented** |
| SEO meta (title / description / slug / OG) | **Implemented** |
| Catalog tag suggestions | **Implemented** |
| Social snippets (copy-only) | **Implemented** |
| Draft-only + no auto-publish | **Confirmed** |
| Redaction + validation + audit/usage | **Implemented** |
| Legal policy page generation | **Out of scope** |
| Tests | **Deferred** (per request) |

---

## Phase 1 Admin AI summaries (2026-07-22)

**Admin AI summaries = implemented (docs + code; no new provider keys; no tests)** — `admin.support.queue_summary` / `admin.analytics.revenue_summary` / `admin.reports.summary` / `admin.operations.daily_summary` with aggregate scrubbing, advisory validation, usage/audit, and `AdminAISummaryPanel` on `/admin`, `/admin/support`, `/admin/analytics`, `/admin/reviews`, `/admin/message-reports`. Never auto-moderates or changes finance.

Canonical: [AI_INTEGRATION_AUDIT.md](./AI_INTEGRATION_AUDIT.md) · [SECURITY.md](./SECURITY.md#ai-copilot-phase-15--phase-1-hardening) · [API.md](./API.md#ai-copilot-phase-15--phase-1-hardening).

| Item | Status |
|---|---|
| Support queue summary | **Implemented** |
| Revenue / analytics period summary | **Implemented** |
| Reports / moderation summary | **Implemented** (`/admin/reviews`, `/admin/message-reports`) |
| Daily operations summary (on demand) | **Implemented** (`/admin`) |
| Advisory-only guardrails | **Confirmed** |
| Redaction + validation + audit/usage | **Implemented** |
| Fan Connect ranking / auto-moderation | **Out of scope** |
| Tests | **Deferred** (per request) |

---

## Phase 1 Support AI assist (2026-07-22)

**Support AI = implemented (docs + code; no new provider keys; no tests)** — `support.ticket.summary` / `triage` / `priority` / `reply_draft` / `article_suggestions` with support scrubbing, output validation, usage/audit, draft-only `SupportAIAssist` on `/admin/support/[ticketId]` and `/support/cases/[id]`. Never auto-sends or auto-closes.

Canonical: [AI_INTEGRATION_AUDIT.md](./AI_INTEGRATION_AUDIT.md) · [SECURITY.md](./SECURITY.md#ai-copilot-phase-15--phase-1-hardening) · [API.md](./API.md#ai-copilot-phase-15--phase-1-hardening).

| Item | Status |
|---|---|
| Ticket summary (staff-only) | **Implemented** |
| Category suggestion (catalog) + Apply / Ignore | **Implemented** |
| Priority suggestion + reason + confirm | **Implemented** |
| Reply draft → composer (Send manual) | **Implemented** |
| Help article suggestions (KB catalog only) | **Implemented** |
| Redaction + reply/category/priority validation | **Implemented** |
| Audit / usage (`ai.generation_*`, latency/cost) | **Implemented** |
| Customer chatbot / auto-send / auto-close | **Out of scope** |
| Tests | **Deferred** (per request) |

---

## Phase 1 Merch Studio AI (2026-07-22)

**Merch Studio AI = implemented (docs + code; no new provider keys; no tests)** — `host.merch.title` / `description` / `category` / `tags` with scrubbing, merch-specific validation, usage/audit, draft-only apply in `HostMerchProductForm` / `MerchAIAssist`.

Canonical: [AI_INTEGRATION_AUDIT.md](./AI_INTEGRATION_AUDIT.md) · [SECURITY.md](./SECURITY.md#ai-copilot-phase-15--phase-1-hardening) · [API.md](./API.md#ai-copilot-phase-15--phase-1-hardening).

| Item | Status |
|---|---|
| Merch title ideas (3–5, click to apply) | **Implemented** |
| Merch description draft (apply / regenerate / copy / dismiss) | **Implemented** |
| Category suggestion (controlled catalog only) | **Implemented** |
| Tag suggestions (validated) | **Implemented** |
| Redaction + merch output validation | **Implemented** |
| Draft-only (no auto-publish / price / inventory / finance) | **Confirmed** |
| Buyer merch recommendations / AI image gen | **Out of scope** |
| Tests | **Deferred** (per request) |

---

## AI Control Center upgrade (2026-07-22)

**AI Control Center = implemented** — multi-provider profiles, per-feature routing with fallback chains, premium admin UI; runtime AI de-emphasized.

| Item | Status |
|---|---|
| `/admin/ai` overview + sub-routes | **Implemented** |
| `ai_provider_profiles` + health checks | **Implemented** |
| `ai_feature_routes` + generation fallback chain | **Implemented** |
| Permissions `admin.ai.manage_providers` / `manage_safety` / `manage_spend` | **Implemented** |
| Runtime `/admin/settings/runtime/ai` banner → Control Center | **Implemented** |

---

## Admin AI controls + usage dashboard (2026-07-22)

**Admin AI controls = implemented (no new product AI features; no tests; no terminal in this pass)** — platform admins manage global AI, provider/model, feature toggles, spend caps, usage, and safe logs before expanding Phase 2 AI.

Canonical: [AI_INTEGRATION_AUDIT.md](./AI_INTEGRATION_AUDIT.md) · [SECURITY.md](./SECURITY.md#ai-copilot-phase-15--phase-1-hardening) · [API.md](./API.md#ai-copilot-phase-15--phase-1-hardening) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).

| Item | Status |
|---|---|
| `/admin/ai` hub + settings / features / usage | **Implemented** |
| Global enable + env kill switch (non-overridable) | **Implemented** |
| Provider/model/base URL (openai/anthropic/gemini/grok/template) | **Implemented** |
| API key env-only (masked status) | **Confirmed** |
| Test connection (audited) | **Implemented** |
| Per-feature toggles + limits + human review | **Implemented** (`ai_feature_configs`) |
| Monthly spend cap + soft/hard stop | **Implemented** (`ai_platform_settings`) |
| Usage dashboard + safe generation logs | **Implemented** |
| Permissions `admin.ai.*` | **Implemented** |
| Fan Connect ranking / recommendations / auto-send | **Out of scope** |
| Tests | **Deferred** (per request) |

---

## Phase 1 AI hardening + Event Studio inline generate (2026-07-22)

**Phase 1 AI = implemented (docs + code; no new provider keys; no tests in this pass)** — context scrubber, feature toggles, output validation, usage/audit logging, canonical `host.event.title` / `host.event.description`, Event Studio Basics “Generate with AI” (draft-only apply).

Canonical: [AI_INTEGRATION_AUDIT.md](./AI_INTEGRATION_AUDIT.md) · [SECURITY.md](./SECURITY.md#ai-copilot-phase-15--phase-1-hardening) · [API.md](./API.md#ai-copilot-phase-15--phase-1-hardening).

| Item | Status |
|---|---|
| Context redaction before provider | **Implemented** |
| Feature toggles + rate limit + kill switch | **Implemented** |
| Output validation (title options / description) | **Implemented** |
| `ai_usage_logs` meta (latency, cost estimate) | **Implemented** |
| Audit `ai.generation_*` | **Implemented** |
| Event Studio title ideas (3–5, click to apply) | **Implemented** |
| Event Studio description draft (apply / regenerate / copy / dismiss) | **Implemented** |
| Draft-only (no auto-publish / send / finance) | **Confirmed** |
| Fan Connect ranking / discovery AI / auto-moderation | **Out of scope** |
| Tests | **Deferred** (per request) |

---

## Sponsor profile workspace (2026-07-23)

**Sponsor as first-class workspace** — extended `sponsors` table, `/api/v1/sponsors/*`, sponsor workspace UI (`/sponsor/*`), public directory + rich `/sponsors/[slug]` partnership profile (public campaigns, placements, hosts), admin `/admin/sponsors`, marketplace inquiry link for logged-in sponsors. **Rich local demo:** `python -m scripts.seed_sponsor_demo_data --force` — public sponsor profiles show ≥5 sponsored events for verified demo brands with enriched partnership cards.

| Item | Status |
|---|---|
| Backend sponsor profiles + admin verify/restrict | **Done** |
| Sponsor workspace + onboarding FE | **Done** |
| Public directory + profile | **Done** |
| Tests (`test_sponsor_profiles.py`, `test_sponsor_team.py`, `sponsor-workspace.test.ts`) | **Done** |

---

## Sponsor team UI (2026-07-23)

| Item | Status |
|---|---|
| Team APIs + invites + audit | **Done** |
| `/sponsor/settings/team` UI | **Done** |
| Invite accept route | **Done** |

---

## Sponsor saved items (2026-07-23)

| Item | Status |
|---|---|
| `sponsor_saved_items` + CRUD APIs | **Done** |
| `/sponsor/saved` workspace page | **Done** |
| Save on marketplace host/slot + event detail | **Done** |
| Tests `test_sponsor_saved.py` | **Done** |

---

## Sponsor campaigns (2026-07-23)

| Item | Status |
|---|---|
| `sponsor_campaigns` + `campaign_saved_items` migration | **Done** |
| Workspace + admin moderation APIs | **Done** |
| `/sponsor/campaigns/*` pages | **Done** |
| Saved + inquiry `campaign_id` linking | **Done** |
| Tests `test_sponsor_campaigns.py` | **Done** |

---

## Sponsor campaign recommendations (2026-07-23)

| Item | Status |
|---|---|
| Rules-only scoring + feedback tables | **Done** |
| Campaign + admin debug APIs | **Done** |
| `/sponsor/campaigns/[id]` + opportunities campaign sort | **Done** |
| Tests `test_sponsor_campaign_recommendations.py` | **Done** |

---

## Sponsor reports (2026-07-23)

| Item | Status |
|---|---|
| Overview + campaign report APIs | **Done** |
| `/sponsor/reports` + campaign reports UI | **Done** |
| Tests `test_sponsor_reports.py` | **Done** |

## Sponsorship deals & payments (2026-07-23)

| Item | Status |
| --- | --- |
| `sponsorship_deals` / invoices / payment_events migration `20260723_0138` | **Done** |
| Host/sponsor/admin APIs + Paystack `PDY-SPN-` webhook | **Done** |
| `/host/sponsorships/deals`, `/sponsor/deals`, `/admin/sponsorship-deals` | **Done** |
| Reports `deals` block + host revenue summary | **Done** |
| Notifications `sponsor.deal_proposal`, `sponsor.deal_active` | **Done** |
| Tests `test_sponsorship_deals.py` | **Done** |

## Sponsorship deliverables (2026-07-23)

| Item | Status |
| --- | --- |
| `sponsorship_deliverables` migration `20260723_0139` | **Done** |
| Seed on active deal + host/sponsor/admin APIs | **Done** |
| Deal detail checklists (host/sponsor/admin) | **Done** |
| Report + host summary deliverable metrics | **Done** |
| Notifications (submit/approve/reject/complete) | **Done** |
| Tests `test_sponsorship_deliverables.py` | **Done** |

---

**AI integration audit = completed (docs only)** — product + technical opportunities across Host / Fan / Admin / Support / discovery / Fan Connect / Merch / Sponsorships / Blog; security rules; architecture; provider strategy; phased roadmap. **No AI implementation, provider keys, or tests in this pass.**

Canonical: [AI_INTEGRATION_AUDIT.md](./AI_INTEGRATION_AUDIT.md) · baseline Phase 15 Copilot in [ROADMAP.md](./ROADMAP.md) · [SECURITY.md](./SECURITY.md#ai-copilot-phase-15) · [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md).

| Item | Status |
|---|---|
| Host / Fan / Admin / Support opportunity audit | **Done** |
| Discovery + Fan Connect AI boundaries | **Done** (rules first; explain-only later; no ranking yet) |
| Merch / Sponsorship / Blog AI map | **Done** |
| Security / privacy / denylist | **Done** |
| Architecture + provider abstraction plan | **Done** (extend `backend/app/ai/`; no single-vendor lock-in) |
| Recommended data tables (not migrated) | **Documented only** |
| Phase 1–3 roadmap + feature catalog | **Done** |
| Implementation / keys / tests | **Out of scope** (deferred) |

### Top Phase 1 candidates (from audit)

1. Event Studio inline title + description  
2. Merch title/description generator  
3. Support triage + suggested replies + summarize (never auto-send)  
4. Admin/support analytics summaries  
5. Blog SEO meta / outline helper  

---

## Host-as-Fan self-abuse (2026-07-20)

**Host-as-Fan = implemented** — hosts remain Personal/Fan users; only the **owner** is blocked from Personal/Fan actions on their **own** host. Host A→Host B stays normal. Team/staff may fan that host.

Canonical: [HOST_AS_FAN.md](./HOST_AS_FAN.md) · [CHECKOUT.md](./CHECKOUT.md) · [REVIEWS.md](./REVIEWS.md) · [MESSAGING.md](./MESSAGING.md) · [AMBASSADORS.md](./AMBASSADORS.md) · [PRIVACY.md](./PRIVACY.md#host-as-fan).

| Rule | Status |
|---|---|
| Hosts keep Personal / Fan identity | **Implemented** |
| Host A owner may fan Host B | **Implemented** |
| Own-host checkout blocked (owner) | **Implemented** |
| Own-host public reviews blocked (owner) | **Implemented** |
| Own-host Personal fan messaging blocked (owner) | **Implemented** |
| Own-host follow blocked (owner) | **Implemented** |
| Ambassador self-referral blocked | **Implemented** |
| Host-owner commission blocked unless `allow_host_owner_commission` | **Implemented** |
| Test/admin flows must not inflate public metrics | **Documented** (test-order helper deferred; `order_excluded_from_public_metrics` ready) |
| Own-host public CTAs (Open Host workspace / Manage event) | **Implemented** |

### Verification

| Evidence | Result |
|---|---|
| `pytest` `test_host_as_fan.py` | **Pass** (prior run) |
| Vitest `own-host-ctas` / `host-affiliation` | **Pass** |
| Docs: HOST_AS_FAN · CHECKOUT · REVIEWS | **Added** |

---

## Own Fan Passport self-actions (2026-07-20)

**Own Fan Passport self-actions = implemented** — users can view/share/edit their public Passport; they cannot Connect, Message, Follow, Report, or Block themselves.

Canonical: [FAN_PASSPORT.md#own-fan-passport](./FAN_PASSPORT.md#own-fan-passport) · [FAN_CONNECT.md](./FAN_CONNECT.md#self-actions-own-passport) · [MESSAGING.md](./MESSAGING.md) · [PRIVACY.md](./PRIVACY.md).

| Rule | Status |
|---|---|
| View + share own public Fan Passport | **Implemented** |
| Own Passport CTAs: Edit Passport · Personal dashboard · Share profile | **Implemented** |
| Hide Connect / Message / Follow / Report / Block on own Passport | **Implemented** |
| Directory own card: “You” + no self social actions | **Implemented** |
| Cannot Fan Connect to self (`SELF_CONNECT_DETAIL`) | **Implemented** |
| Cannot fan↔fan message / thread with self (`SELF_MESSAGE_DETAIL`) | **Implemented** |
| Cannot follow self (`SELF_FOLLOW_DETAIL`) | **Implemented** |
| Cannot report / block self | **Implemented** |
| Self excluded from Connect suggestions + connection counts | **Implemented** |

### Verification (2026-07-20)

| Command | Result |
|---|---|
| `pytest tests -k "fan_connect or messaging or passport or directory or self"` | Self-action tests **Pass** |
| `npm run lint` · `build` · `test:pwa` · `test:theme` · `test:fan-connect` | **Pass** |
| Vitest `own-fan-ctas.test.ts` | **Pass** |

---

## Admin User Management MVP (2026-07-20)

**Admin User Management = implemented** — directory + detail, safe fields only, flags, notes, status changes, scrubbed audit logs, granular permissions, impersonation, acceptance tests, docs.

Canonical: [ADMIN.md](./ADMIN.md#user-management-safe-actions) · [API.md](./API.md#admin-user-management-safe-actions) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [DATABASE.md](./DATABASE.md#admin-user-management) · [SECURITY.md](./SECURITY.md#admin-user-management) · [PRIVACY.md](./PRIVACY.md#admin-user-management) · [CRUD_MATRIX.md](./CRUD_MATRIX.md).

| Item | Status |
|---|---|
| FE `/admin/users` directory | **Implemented** |
| FE `/admin/users/[userId]` detail (Overview · Restrictions · Activity · Flags · Notes · Security · Audit) | **Implemented** |
| Safe fields only — no passwords / tokens in API or UI | **Implemented** |
| Flags (add / resolve / dismiss) | **Implemented** |
| Notes (append-only, admin-only) | **Implemented** |
| Status changes (under review / suspend / ban / restricted) | **Implemented** |
| Selective restrictions (`user_restrictions` + presets + enforcement) | **Implemented** — see section below |
| Audit logs (`admin_user_*`) | **Implemented** |
| Permissions (`admin.users.*` granular matrix) | **Implemented** |
| Migrations `20260720_0092`–`0096` | **Implemented** |
| Impersonation (see section below) | **Implemented** |
| Acceptance: `test_admin_users_phase14` · `test:admin-users` · `test_impersonation` · `test:impersonation` · `test_user_restrictions` · `test:user-restrictions` | **Pass** (re-verify below) |
| Docs update (phase 15 + selective restrictions) | **Done** |

### Verification (2026-07-20)

| Command | Result |
|---|---|
| `alembic upgrade head` | **Pass** |
| `pytest` admin users / flags / notes / audit / permission / impersonation | **Pass** |
| `npm run test:admin-users` · `test:impersonation` · lint · build | **Pass** |

---

## Selective user restrictions (2026-07-20)

**Selective user restrictions = implemented** — categorized Restrictions panel + presets; append-only `user_restrictions`; derive `account_status=restricted`; Full suspension preset-only; enforce at product gates.

Canonical: [ADMIN.md](./ADMIN.md#selective-restrictions-primary-moderation) · [API.md](./API.md#admin-user-management-safe-actions) · [DATABASE.md](./DATABASE.md#user_restrictions) · [SECURITY.md](./SECURITY.md#admin-user-management) · [PRIVACY.md](./PRIVACY.md#admin-user-management) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [CRUD_MATRIX.md](./CRUD_MATRIX.md) · [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md).

| Item | Status |
|---|---|
| `user_restrictions` table (soft lifecycle; never hard-delete) | **Implemented** |
| Catalog + groups + presets (Messaging / Buyer / Host / Ambassador / Read-only / Full suspension) | **Implemented** |
| APIs GET/POST/PATCH/revoke | **Implemented** |
| Perms `view_restrictions` · `add_restriction` · `revoke_restriction` · `ban` | **Implemented** |
| Enforcement `assert_no_restriction` (checkout, messaging, Fan Connect, reviews, host, ambassadors, …) | **Implemented** |
| Admin UI Restrictions tab + end-user disable UX (keys only) | **Implemented** |
| Audits `admin_user_restriction_*` + `restricted_user_blocked_from_action` | **Implemented** |
| Full suspension = preset only (`account_status=suspended` + major keys) | **Implemented** |
| Migration `20260720_0096` | **Implemented** |
| Tests `test_user_restrictions.py` · `test:user-restrictions` · `test:admin-users` | **Pass** |

### Verification (selective restrictions — 2026-07-20)

| Command | Result |
|---|---|
| `alembic upgrade head` | **Pass** (`20260720_0096`) |
| `pytest` `-k "admin or users or restriction or permission or checkout or messaging or fan_connect or review or host"` | **422 passed**, 473 deselected |
| `npm run lint` · `build` · `test:pwa` · `test:theme` · `test:admin-users` · `test:user-restrictions` | **Pass** |

---

## Suspension notification + appeals (2026-07-20)

**Suspension notify + appeals = implemented** — on suspend: in-app / email / push with public category·duration·date; Appeal CTA; admin `/admin/appeals` approve/reject; backend enforces suspension; FE `/account/suspended`.

| Item | Status |
|---|---|
| `account_suspensions` + `account_appeals` (migration `20260720_0097`) | **Implemented** |
| Notify on suspend (in-app + email if available + push if enabled) | **Implemented** |
| Public fields only (no internal notes / fraud logic) | **Implemented** |
| `GET /me/suspension` · `POST /appeals` · admin appeals CRUD | **Implemented** |
| Approve → unsuspend; reject + optional user-facing reply | **Implemented** |
| Audits: notified / submitted / approved / rejected / unsuspended | **Implemented** |
| Auth + middleware product-API block for suspended | **Implemented** |
| FE `/account/suspended` + `/admin/appeals` | **Implemented** |
| Perm `admin.appeals.review` | **Implemented** |
| Tests `test_appeals.py` | **Pass** (2) |

---

## Admin user impersonation (2026-07-20)

**Admin user impersonation = implemented** — internal support/QA sessions: fully audited, target never notified, admin/target separation, sensitive-action blocks, banner, demo QA, tests.

Canonical: [AUTH.md](./AUTH.md) · [SECURITY.md](./SECURITY.md#admin-user-impersonation) · [ADMIN.md](./ADMIN.md#user-impersonation) · [PRIVACY.md](./PRIVACY.md#admin-user-impersonation) · [API.md](./API.md#admin-user-impersonation) · [DATABASE.md](./DATABASE.md#admin-user-impersonation) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).

| Item | Status |
|---|---|
| Internal + audited (audit logs retained) | **Implemented** |
| Target never notified (no email / in-app / push) | **Implemented** |
| Permission `admin.users.impersonate` · max duration 60 (default 30) | **Implemented** |
| Separate impersonation access token (no refresh; no password; no session hijack) | **Implemented** |
| `current_user` = target · `actor_admin_id` separate (`/me/session`) | **Implemented** |
| Sensitive actions blocked + audited · Passport settings UI locked | **Implemented** |
| Global banner + Exit · `/admin` deny-while-impersonating | **Implemented** |
| Tables `admin_impersonation_sessions` + `_audit_logs` (`20260720_0089`) | **Implemented** |
| FE `/admin/users*` + email lookup · `/demo` Impersonation QA | **Implemented** |
| Pytest + `npm run test:impersonation` | **Implemented** |

### Verification commands (2026-07-20)

| Command | Result |
|---|---|
| `alembic upgrade head` | **Pass** |
| `pytest tests -k "admin or impersonation or auth or permission"` | **Pass** (150) |
| `npm run lint` · `build` · `test:pwa` · `test:theme` · `test:impersonation` | **Pass** |

---

## Admin user safe actions (2026-07-20)

Superseded by **[Admin User Management MVP](#admin-user-management-mvp-2026-07-20)** above (same date). Kept as a pointer for older links.

| Item | Status |
|---|---|
| Notes, flags, status, force logout / password-reset, hard delete blocked | **Implemented** (see MVP section) |

---

## Admin Runtime Settings (2026-07-20)

**Admin Runtime Settings = implemented (core path)** — allowlisted Class B overrides, specialist email/push kept separate, FE hub under `/admin/settings/runtime*`.

Canonical: [SETTINGS.md](./SETTINGS.md) · [ENVIRONMENT.md](./ENVIRONMENT.md) · [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md) · [ADMIN.md](./ADMIN.md) · [API.md](./API.md) · [SECURITY.md](./SECURITY.md).

| Item | Status |
|---|---|
| Audit doc A–E + locked specialist-tables decision | **Done** |
| Model `runtime_settings` + Alembic `20260720_0090` | **Implemented** |
| Registry + `RuntimeSettingsService` (DB → env → default) | **Implemented** |
| API `/api/v1/admin/settings/runtime*` + `admin.settings.*` perms | **Implemented** |
| FE `/admin/settings/runtime`, `/[category]`, `/audit` | **Implemented** |
| Keep `email_provider_settings` / `push_provider_settings`; unify via UI | **Locked** |
| Secret masking (`Configured · ending in ####` / Not configured) | **Implemented** |
| Startup independent of DB runtime settings | **Implemented** (graceful degrade) |
| Dedicated pytest suite / full consumer wiring | **Partial / landing** |

### Verification notes

Re-run when landing tests: `alembic upgrade head`; `pytest tests -k "runtime_settings or admin_settings"`; FE lint/build for admin settings routes.

---

## Admin event buyer export (2026-07-20)

**Admin event buyer export = implemented** — modes, granular perms, filters, audited CSV/JSON streaming, FE export modal, docs, tests.

Canonical: [TICKETS.md](./TICKETS.md) · [ADMIN.md](./ADMIN.md) · [API.md](./API.md) · [PRIVACY.md](./PRIVACY.md) · [SECURITY.md](./SECURITY.md).

| Item | Status |
|---|---|
| Perms `admin.events.view` + `export_buyers` (+ private contact / finance) | **Implemented** |
| Modes `public_summary` / `operations` / `finance` | **Implemented** |
| Private contact opt-in + reason; finance reason | **Implemented** |
| Filters on list + export; CSV injection sanitize + stream filename | **Implemented** |
| Structured audit actions + IP/UA | **Implemented** |
| FE `/admin/events/[id]/buyers` export modal | **Implemented** |
| Hosts / normal users blocked on admin export | **Implemented** |

### Verification commands (2026-07-20)

| Command | Result |
|---|---|
| `alembic upgrade head` | **Pass** |
| `pytest tests -k "admin and event and export"` | **Pass** — 13 passed, 736 deselected |
| `pytest tests -k "buyer or attendee or privacy"` | **Pass** — 98 passed, 651 deselected (4 unrelated warnings) |
| `npm run lint` / `build` / `test:pwa` / `test:theme` | **Pass** |

---

## Host Command Center (2026-07-20)

**Host Command Center = implemented** in the frontend — canonical `/host`, grouped sidebar, roadmap, role-aware landing, operational event list, and server redirects. Audit baseline: [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md).

Canonical docs: [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md#host-command-center) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md#role-aware-command-center-ux) · [TEAMS.md](./TEAMS.md#frontend-routes-quick) · [EVENTS.md](./EVENTS.md).

| Item | Status |
|---|---|
| `/host` Command Center home (`OwnerCommandCenter` / team desk overview) | **Implemented** |
| `/host/dashboard` → `/host` (**308**) | **Implemented** |
| `/host/roadmap` launch checklist (inferred statuses) | **Implemented** |
| `/host/onboarding` first-time only; existing host → `/host/roadmap` | **Implemented** |
| Sidebar groups Home / Operate / Grow / Manage (`workspace.ts` + `host-nav.ts`) | **Implemented** |
| Payouts / promos off primary sidebar (deep links only) | **Implemented** |
| Role landing (`hostHomePathForWorkspace`) — owner, desk, sponsor manager | **Implemented** |
| Role sidebar + path guards (`navGroupsForWorkspace`, `canAccessHostPath`) | **Implemented** |
| `/host/events` tabs, search, filters, sort, Table/List/Grid (default table) | **Implemented** |
| Server **308** redirects: merch alias, notification prefs | **Implemented** |
| `/host/support` → `/support` entry | **Implemented** |
| Roadmap skip / share tracking persistence API | **Deferred** (inferred-only v1) |
| `/host/events/[id]/studio` route alias | **Deferred** (use `/edit?step=`; no `page.tsx`) |
| Platform-admin host impersonation mode | **Implemented** (user-level audited impersonation; see AUTH.md / SECURITY.md / ADMIN.md) |

### Verification commands (2026-07-20)

| Command | Result |
|---|---|
| `npm run test:host-command-center` | **Pass** — redirects, nav groups, roadmap, event list defaults |
| `npm run test:host-team` | **Pass** (team + desk smoke; run with Command Center QA) |

### Host Command Center polish (2026-07-20)

**Frontend-only** — routes and backend permissions unchanged. Detail: [HOST_COMMAND_CENTER_POLISH.md](./HOST_COMMAND_CENTER_POLISH.md).

| Item | Status |
|---|---|
| Owner CC header → Overview + Legacy Page CTA; no in-body switcher | **Implemented** |
| Member overview role/action titles; desk → `/host/desk` | **Implemented** |
| Today’s ops Scanner/Pickup gated (`canScanTickets` / `canScanMerch`) | **Implemented** |
| Host-switch refetch (`active?.host_id` + remount key) | **Implemented** |
| Pending tasks eyebrow → Needs attention | **Implemented** |
| Events grid desk safety (coerce off grid; `HostEventRowActions`) | **Implemented** |
| Event action labels: Merch Studio / Ambassador Campaigns (paths unchanged) | **Implemented** |
| Host sidebar labels preserved; public Hosts marketplace unchanged | **Confirmed** |
| Phase 2 chrome preserved; privacy boundaries preserved | **Confirmed** |
| Backend pytest / alembic | **Skipped** (FE-only) |

| Command | Result |
|---|---|
| `npm run lint` · `build` · `test:pwa` · `test:theme` | **Pass** |
| `npm run test:host-command-center` | **Pass** (includes polish locks) |
| `npm run test:workspace-privacy` · `test:buyer-dashboard-nav` | **Pass** |

---

## Ambassadors — open Event Ambassadors (2026-07-19)

**Ambassadors = implemented** through open participation, campaigns, attribution, verified-payment conversions, privacy, fraud, notifications, demo seed, tests, and docs.

Canonical: [AMBASSADORS.md](./AMBASSADORS.md) · discounts vs referral: [PROMO_CODES.md](./PROMO_CODES.md) · demo: [DEMO_DATA.md](./DEMO_DATA.md#open-event-ambassadors-demo).

| Item | Status |
|---|---|
| Open join (`public_open` / active campaigns) + terms | **Implemented** |
| Campaign types `event_tickets` / `event_merch` + commission rules | **Implemented** |
| Referral links/codes + last-click cookie; explicit code wins | **Implemented** |
| Conversions only after verified Paystack finalize; FE success never earns | **Implemented** |
| Refund / ticket-cancel reverse (v1 + domain, idempotent) | **Implemented** |
| Privacy allowlist (no buyer PII / payment refs on self APIs) | **Implemented** |
| Fraud (self-referral, host-owner guard, rate limit, hashed IP/UA, click spikes) | **Implemented** |
| Email + in-app + push templates | **Implemented** |
| FE `/ambassadors*`, `/dashboard/ambassador*`, host/admin Ambassadors | **Implemented** |
| Demo Afrobeats Night Ambassador Drive + `/demo` shortcuts | **Implemented** |
| Docs §18 (AMBASSADORS, PROMO_CODES, tickets/merch/payments/emails/notifications/API/DB/routes/security/privacy/tracker) | **Implemented** |
| Backend `test_ambassador_*` / `test_open_ambassadors` / phase17 checklist | **Pass** |
| FE `npm run test:ambassadors` + lint / build / theme / pwa | **Pass** |
| Alembic | Through `20260719_0087` (sale payout meta) |

### Product rules (locked)

- Open participation for eligible active users — not host team / scanner / merch desk  
- Commission only after verified paid webhook; duplicate webhooks idempotent  
- Explicit checkout Ambassador code overrides cookie/link attribution  
- Ambassadors never see buyer private data  
- Self-referral and (by default) host-owner commission blocked  

### Verification commands (2026-07-19)

| Command | Result |
|---|---|
| `alembic upgrade head` | Applied through `20260719_0087` |
| `pytest` ambassadors + payments + ticketing + merch + privacy | **Pass** (125+) |
| `npm run lint` · `npm run build` · `npm run test:pwa` · `npm run test:theme` · `npm run test:ambassadors` | **Pass** |

## Ambassadors — host reward approval + team permissions (2026-07-19)

Host-owned campaign reward approval is the normal path (owner or permitted team). Admin oversight retained for fraud / platform campaigns / emergency. Docs: [AMBASSADORS.md](./AMBASSADORS.md) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) · [TEAMS.md](./TEAMS.md) · [PAYMENTS.md](./PAYMENTS.md) · [PRIVACY.md](./PRIVACY.md) · [SECURITY.md](./SECURITY.md) · [API.md](./API.md) · [DATABASE.md](./DATABASE.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).

| Item | Status |
|---|---|
| Host `POST …/conversions/{id}/reward-status` (approve/reject/paid/reversed) | **Implemented** |
| Team gates: `approve_rewards` / `reject_rewards` / `mark_rewards_paid` / `reverse_rewards` (+ finance alt) | **Implemented** |
| Admin oversight `POST /promos/admin/conversions/{id}/reward-status` | **Retained** |
| Reward audit (`reward_audit.py` + host/admin GET feeds) | **Implemented** |
| Flag suspicious conversion | **Implemented** |
| Host conversion DTO strips order/buyer private data | **Implemented** |
| Notifications (ambassador + host owner + high-value admin) | **Implemented** |
| FE `/host/ambassadors/conversions` + `/payouts` + team toggle hint | **Implemented** |
| Migration `20260719_0087` payout meta columns | **Implemented** |
| Docs update (item 12) | **Implemented** |

### Completion gates

- Host owner can approve / mark paid for own campaign  
- Permitted team member can approve / mark paid  
- Non-permitted team member denied  
- Platform admin oversight still works  
- All reward actions audited  
- Buyer private data not exposed on host conversion APIs  
- Tests / build pass  

### Verification commands (host rewards)

| Command | Result |
|---|---|
| `alembic upgrade head` | Through `20260719_0087` |
| `pytest -k "ambassador or team or permission or payout or reward"` | **Pass** (150) |
| `pytest -k "payment or ticket or merch or privacy"` | **Pass** (228) |
| `npm run lint` · `build` · `test:pwa` · `test:theme` · `test:ambassadors` | **Pass** |

## Transactional email system (2026-07-19)

**Transactional Email = implemented** with a central `email_events` outbox, Log/SMTP provider abstraction, branded HTML+text templates, user preferences, signed unsubscribe, admin email log/resend, and key product integrations (auth welcome, Paystack ticket/merch confirms, host sales, merch lifecycle, refunds, event cancel, sponsors, Fan Connect, messaging, reviews).

Pre-work “log-only / no outbox” notes are **historical baseline only** — see [EMAIL_AUDIT.md](./EMAIL_AUDIT.md) § Before implementation. They are **not** current status.

| Item | Status |
|---|---|
| Central outbox + SMTP/log providers + templates + prefs + unsubscribe + admin log | **Implemented** |
| Key product integrations (tickets/merch/host/sponsors/connect/messaging/reviews) | **Implemented** |
| Event reminder scheduler / password-reset API / verify-email flow | **Deferred** (templates ready) |
| Bounce/complaint webhooks | **Placeholder** |
| Admin-managed SMTP (Fernet-encrypted DB settings) | **Implemented** — `/admin/email/settings` overrides env; worker re-reads each batch |
| In-app + browser push notifications | **Implemented** — see § Push notifications below |
| Production live send | Requires admin SMTP (or env fallback) + `EMAIL_SETTINGS_ENCRYPTION_KEY` + outbox worker + DNS — [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md) |

## Host team management (2026-07-19)

**Host team = implemented** — true pending email invites, role presets + permission toggles, host-wide vs per-event scope, hybrid desk scan with `event_staff_assignments`, workspace switching, audit logs, security/privacy hardening, demo seed, tests, docs.

Canonical docs: [TEAMS.md](./TEAMS.md) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) · [HOST_TEAM.md](./HOST_TEAM.md) · [TICKETS.md](./TICKETS.md) · [MERCH.md](./MERCH.md) · [EMAILS.md](./EMAILS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md) · [API.md](./API.md) · [DATABASE.md](./DATABASE.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [SECURITY.md](./SECURITY.md) · [PRIVACY.md](./PRIVACY.md).

| Item | Status |
|---|---|
| True pending invite by email + outbox `team_invite` (hashed token, 7-day TTL) | **Implemented** |
| Accept / revoke / resend / suspend / remove | **Implemented** |
| Role presets + editable `permissions_json` toggles | **Implemented** |
| Host-wide vs `selected_events` scope + staff sync | **Implemented** |
| Hybrid ticket + merch desk auth (`app/teams/permissions.py`) | **Implemented** |
| Keep / extend `event_staff_assignments` (`team_member_id`, assignment types) | **Implemented** |
| Workspace switcher + `user_active_workspaces` | **Implemented** |
| Unified audit feed (`/host/team/audit-log` + desk scans) | **Implemented** |
| Security/privacy (minimal desk payloads, shipping gate, owner-only payouts, deny on suspend) | **Implemented** |
| Demo DJ Maze team + pending invite | **Implemented** |
| FE `/host/team*`, `/host/desk`, `/workspaces`, `/team/invite/[token]` | **Implemented** |
| Docs §17 (TEAMS, permissions, tickets, merch, emails, notifications, API, DB, routes, security, privacy, tracker) | **Implemented** |
| Backend tests (`test_host_team`, `test_team_audit`, `test_team_security_privacy`, …) | **Pass** |
| FE `npm run test:host-team` + lint / build / theme / pwa | **Pass** |
| Alembic | Through `20260719_0075` (`invite_method` / username privacy) |

## Dashboard ↔ Host unification — Option A (2026-07-20)

**UI/navigation only** — `/dashboard/*` remains **Personal**; `/host/*` remains **Host: {name}**. One shared `WorkspaceShell` chrome; mode-pure nav configs. **No** `/dashboard/host` alias or canonical tree. Admin (`/admin`) and Support (`/support`) stay separate shells (not switcher options).

Docs: [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md) · [BUYER_DASHBOARD_AUDIT.md](./BUYER_DASHBOARD_AUDIT.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) · [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md).

| Item | Status |
|---|---|
| Shared `WorkspaceShell` + always-on switcher (**Personal account** · **Host: {name}**) | **Implemented** |
| Shell titles **Personal** / **Host: {display_name}**; Connect shell aligned | **Implemented** |
| SiteHeader: single **Personal** entry → `/dashboard`; private peer **Host** removed; public **Hosts** kept | **Implemented** |
| Role-aware Host landing via `hostHomePathForWorkspace` (desk → `/host/desk`; never hardcode `/host/events`) | **Implemented** |
| `padeya-workspace-mode` persisted (last-used workspace click deferred) | **Implemented** |
| Vertical sidebar + mobile drawer same groups; Command Center duplicate switcher removed | **Implemented** |
| Shell `homeHref` threaded for active-state + breadcrumbs (desk-safe) | **Implemented** |
| Redirects unchanged; no `/dashboard/host` | **Implemented** |
| Privacy smoke `npm run test:workspace-privacy` | **Implemented** |
| Buyer/host data merge or host pages under `/dashboard` | **Out of scope** |

### Personal workspace chrome — Phase 2 (2026-07-20)

Buyer/Personal audit Phase 2 — labels + chrome only ([BUYER_DASHBOARD_AUDIT.md](./BUYER_DASHBOARD_AUDIT.md) §14 Phase 2).

| Item | Status |
|---|---|
| SiteHeader / Footer workspace entry **Personal** → `/dashboard` | **Implemented** |
| Private Host top-nav link absent; public **Hosts** marketplace kept | **Implemented** |
| Personal sidebar **Team** → **Workspaces** (`/dashboard/team` unchanged) | **Implemented** |
| Personal sidebar group **Growth** → **Earn** | **Implemented** |
| Connect nav → `/connect` (aliases remain) | **Implemented** |
| Breadcrumbs: Personal / Overview · Workspaces · Ambassadors; Host Team under `/host` | **Implemented** |
| Switcher clarity (Personal account · Host: {name} · Become a host) | **Implemented** |
| Permissions / route trees unchanged | **Confirmed** |

### Personal Command Center — Phase 3 (2026-07-20)

`/dashboard` is now the **Personal Command Center** ([BUYER_DASHBOARD_AUDIT.md](./BUYER_DASHBOARD_AUDIT.md) §11 / §14 Phase 3 · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md)).

| Item | Status |
|---|---|
| `/dashboard` = Personal Command Center home | **Shipped** |
| Routes unchanged (`/dashboard/*`, `/host/*`, `/admin/*`, `/support/*`) | **Confirmed** |
| Header: Personal Command Center · Hello · no roles dump · no in-body switcher | **Implemented** |
| Next up priority + Open QR modal · merch · cart · welcome empty | **Implemented** |
| My activity / community / identity / Vault / Ambassadors (hide when empty) | **Implemented** |
| P0 then deferred loads; privacy §12 own-data only | **Confirmed** (smoke-locked) |
| Phase 2 chrome unbroken (Personal / Hosts / switcher / Workspaces / Earn) | **Confirmed** |
| Docs: BUYER audit · unification · FRONTEND_ROUTES · PRODUCTION_SMOKE · this tracker | **Updated** |
| Smoke `npm run test:personal-command-center` | **Implemented** |

### Verification (2026-07-20)

| Command | Result |
|---|---|
| `npm run lint` | **Pass** |
| `npm run build` | **Pass** |
| `npm run test:pwa` · `npm run test:theme` | **Pass** |
| `npm run test:buyer-dashboard-nav` · `test:host-command-center` · `test:workspace-privacy` | **Pass** |
| `npm run test:personal-command-center` | **Pass** (Phase 3) |
| Vitest `personal-command-center` + `host-access.home-path` | **Pass** |

**Confirmations (code + smoke):** no host finance/scanner/admin on `/dashboard` body; no raw `qr_payload` text in Next up; quiet welcome + optional sections hide when empty; P0/deferred fetches use `allSettled`. Signed-in browser pass still recommended ([PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md)).

## Push notifications (2026-07-19)

**Browser push + in-app alerts = implemented.** Docs: [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md) · [NOTIFICATION_PUSH_AUDIT.md](./NOTIFICATION_PUSH_AUDIT.md).

| Item | Status |
|---|---|
| Central channel registry (`notifications/channel_registry.py`) + kind→template aliases | **Implemented** (2026-07-22) |
| Wired product kinds use dedicated safe push templates (not generic) | **Implemented** (2026-07-22) |
| Integration tests (`test_notification_push_integration.py`) | **Implemented** (2026-07-22) |
| Fan check-in success push (`ticket.checked_in` wired from scanner/offline/override) | **Implemented** (2026-07-22) |
| Push pref gating uses dotted in-app `kind` (not snake_case template) | **Implemented** (2026-07-22) |
| Admin campaign push uses `resolve_template_name` | **Implemented** (2026-07-22) |
| Opt-in permission (never on page load) + unsupported/denied UI | **Implemented** |
| VAPID admin settings (encrypted private key) + public key API | **Implemented** |
| Multi-device subscriptions + soft deactivate / 410 handling | **Implemented** |
| `push_events` outbox + `log` / `web_push` providers | **Implemented** |
| Compose `push_worker` + `scripts/process_push_outbox.py` | **Implemented** |
| Templates / triggers / prefs gating / message away-only | **Implemented** |
| Privacy whitelist (BE + SW) + message preview opt-in | **Implemented** |
| Admin test push + delivery/events inspection | **Implemented** |
| Notification center + toast bridge (works without push) | **Implemented** |
| Checklist tests + `npm run test:pwa` / theme / lint / build | **Verified** |

### Verification commands (2026-07-19)

| Command | Result |
|---|---|
| `alembic upgrade head` | Applied through `20260719_0068` |
| `pytest` push / notifications / tickets / merch / messaging / fan_connect / privacy | **Pass** |
| `npm run lint` · `npm run build` · `npm run test:pwa` · `npm run test:theme` | **Pass** |

## Fan Connect v1 — final QA (2026-07-18)

**Fan Connect v1 = implemented and stable.**

Brand: **Pàdéyá**. Product docs: [FAN_CONNECT.md](./FAN_CONNECT.md) · [PRIVACY.md](./PRIVACY.md) · [DEMO_DATA.md](./DEMO_DATA.md#fan-connect-demo).

### Status

| Layer | Status |
| --- | --- |
| Backend domain (`app/fan_connect`) | **Implemented · stable** |
| Suggestions + scoring (public context only) | **Implemented · stable** |
| Connection request / accept / remove / block / report | **Implemented · stable** |
| `fan_fan` messaging (post-accept only) | **Implemented · stable** |
| Admin Connect moderation | **Implemented · stable** |
| Frontend `/connect/*` + dashboard aliases | **Implemented · stable** |
| Event detail Fan Connect section | **Implemented · stable** |
| Demo seed + `/demo` shortcuts | **Implemented · stable** |
| Notifications + analytics | **Implemented · stable** |
| Directional decline cooldown + marketplace visibility (2026-07-22) | **Implemented** — default **30** days; FE cooldown/decliner CTAs + decline modal; see [FAN_CONNECT.md](./FAN_CONNECT.md#decline-cooldown-directional) |

### End-to-end flows verified (tests + smoke)

| # | Flow | Evidence |
| --- | --- | --- |
| 1 | Connect disabled excluded from suggestions | `test_fan_connect_disabled_excluded` |
| 2 | Private Passport excluded | `test_private_passport_excluded` |
| 3 | Unlisted Passport excluded in live eligibility (demo Chidi↔Bayo seeded exception) | `test_unlisted_passport_excluded` · `DEMO_DATA.md` |
| 4 | Public + Connect on can appear | request/accept + suggestion tests |
| 5–7 | Same public event / host / scene → suggestion | privacy_safety suggestion tests |
| 8 | Private/secret event does not create suggestion | `test_private_events_never_in_shared_context` |
| 9–11 | Hidden venue / VIP / spend never exposed | leak + safe_reasons tests |
| 12–15 | Send → accept → `connected` + `fan_fan` thread | `test_accept_unlocks_thread_pre_accept_denied` |
| 16 | Message denied before accept | same |
| 17 | Remove disables messaging | `test_remove_disables_messaging` |
| 18 | Block disables suggestions + messaging | block tests |
| 19–20 | Report + admin Fan Connect reports | report / admin resolve tests |
| 21 | Event Fan Connect section only when safe | `EventFanConnectSection` + smoke |
| 22–23 | Mobile + dark/light | fan-connect + theme smokes; dark token fix in Connect UI |

### Verification results (this run)

| Check | Result |
| --- | --- |
| `alembic upgrade head` | **Pass** (messaging head includes `20260718_0052`–`0059`) |
| Fan Connect + messaging + passport + privacy pytest | **Pass** |
| Frontend lint | **Pass** |
| Frontend `next build` | **Pass** — `/connect/*`, `/dashboard/connect/*`, `/admin/fan-connect/*`, `/events/[slug]` |
| `npm run test:pwa` | **Pass** |
| `npm run test:theme` | **Pass** |
| `npm run test:fan-connect` | **Pass** |
| `npm run test:messaging` | **Pass** (Phase 20) |

### Out of scope (by design)

Dating/matchmaking UI · proximity map · phone sharing · host mass-DM of connect graph · private attendee lists on event pages · Fan Connect for hosts.

---

## Messaging realtime + attachments (2026-07-18)

**Status: implemented** (REST send authority unchanged; image + PDF/DOCX/text attachments; expanded WS events).

| Layer | Status |
| --- | --- |
| `message_attachments` migrations `20260718_0052`–`0054` | **Implemented** |
| Upload + bind on send (same permission gates) | **Implemented** |
| In-memory WS hub + `WS /api/v1/messages/ws` | **Implemented** |
| WS protocol (`message.*` / `thread.*` / `connection.*` / `attachment.*`) + subscribe/typing/read | **Implemented** |
| Redis pub/sub multi-worker fan-out + in-memory single-worker fallback | **Implemented** |
| FE reconnect (ping 25s, backoff, 4401 token refresh) | **Implemented** |
| WS server-side thread permission gates (block/connect/admin) | **Implemented** |
| FE `useMessageSocket` + composer/bubble/inbox | **Implemented** |
| Private attachment storage + authorized download | **Implemented** |
| File safety (Pillow verify, EXIF strip, scanner hook, no AV yet) | **Implemented** |
| Attachment permissions (requests/block/Fan Connect/admin report-scope) | **Implemented** |
| Attachment privacy allowlist (no storage keys / signed URL scope) | **Implemented** |
| Attachment moderation (report view + hide/restore/soft-delete/review) | **Implemented** |
| Attachment-safe notifications (WS + in-app coalesce; no file URLs) | **Implemented** |
| Safe demo attachment seed (Chidi↔Bayo, Tolu↔Maze, reported thread) | **Implemented** |
| Phase 19 WS / attachment / privacy pytest checklist | **Verified** |
| Phase 20 FE messaging smoke + lint/build/theme/PWA | **Verified** |
| Phase 21 docs (MESSAGING / API / PRIVACY / SECURITY / …) | **Verified** |

Out of scope: voice/video calls, live location, proximity map, phone sharing, private attendee lists, public group chats, host broadcast, antivirus scanning, S3/R2 production storage, per-message read-receipts table, cross-worker online presence. (Redis multi-worker fan-out **is** in scope and shipped.)

---

## Messaging chat features — edit / reply / pin / star (2026-07-18)

**Status: implemented · documented** (fan↔host / fan↔fan gates unchanged; REST remains send authority; stars private; pins shared).

| Layer | Status |
| --- | --- |
| Migrations `0055`–`0059` (reply/pins/stars → edit history → soft unpin → soft unstar → delete-for-me) | **Implemented** |
| Permission layer `app.messaging.permissions` (`can_read/send/edit/pin/star/reply`) | **Implemented** |
| Edit (24h) + `message_edits` history (no public history UI) | **Implemented** |
| Reply (`reply_to_message_id`) + sanitized previews | **Implemented** |
| Shared pins (max 3) + personal stars + delete-for-me | **Implemented** |
| Thread-level read status (`peer_read_at` / Sent·Delivered·Read·Failed) | **Implemented** |
| WS `message.updated` + `message.pinned` / `unpinned` (no star WS) | **Implemented** |
| FE: timestamps, day separators, action menu, quote/reply/edit composer, pin bar, starred list, search | **Implemented** |
| Privacy: report-scoped admin hide; inbox/search redaction; star isolation | **Implemented** |
| Demo seed + `/demo` shortcuts (Tolu↔Maze, Chidi↔Bayo, starred, pinned) | **Implemented** |
| Docs (MESSAGING / FAN_CONNECT / PRIVACY / SECURITY / API / DATABASE / FRONTEND_ROUTES / DEMO_DATA) | **Updated** |
| Pytest `test_messaging_chat_features.py` + privacy / demo chat-feature tests | **Verified** |
| `npm run test:messaging` | **Verified** |

---

## Advanced merch commerce — final QA (2026-07-18)

### Status

| Layer | Status |
| --- | --- |
| Event-linked merch (Phase 1) | **Implemented · stable** |
| Advanced commerce expansion | **Implemented · stable** |
| Live Printful / Printify sync | **Deferred by design** |
| Live carrier label APIs | **Deferred by design** |
| Buyer multi-channel stock-alert prefs | **Deferred by design** |
| Zone delivery-estimate field | **Deferred by design** |

### Verification results

| Check | Result |
| --- | --- |
| Merch backend suite (11 files) | **113 passed** |
| Full backend `pytest tests` | **423+ passed**; demo reset FK fixed during QA (`test_demo_seed_idempotent_and_consistent` green after fix) |
| Frontend lint | **Clean** (0 errors / 0 warnings after unused import cleanup) |
| Frontend `next build` | **Pass** — all listed merch routes present |
| `npm run test:pwa` | **Pass** |
| `node scripts/merch-smoke.mjs` | **Pass** |
| Manual route presence | All host / buyer / admin merch paths exist |
| Browser smoke | `/u/djmaze/merch` loads; host merch routes require auth (expected) |

### QA flows covered (tests + route smoke)

1. Host creates merch product — `test_merch.py` / host UI `/host/merchandise/new`
2. Variants / inventory — reserve, oversell block, webhook idempotent
3. Shipping zones — CRUD + archive excludes checkout (`test_merch_commerce`)
4. Ticket + merch bundles — expand / unpaid / inventory / host CRUD
5. Merch discount codes — validate, limits, refund reverse, host CRUD
6. Stock alerts — host API + page
7. Size charts — create / public / attach / archive
8. Product reviews — verified purchase; hosts cannot delete
9. Revenue report — splits + CSV no PII
10. POD jobs — created after paid; manual fulfill; unpaid creates none
11. Post-event drops — host create/list/patch; eligibility; notify idempotent
12. Vault-exclusive merch — teaser only when locked; purchase gate
13. Buyer event merch — catalog / detail routes
14. Host storefront — `/u/[username]/merch`
15. Bundle selection — checkout picker + FE smoke
16. Merch discount at checkout — validate + apply
17. Pickup fulfillment — codes + desk
18. Shipping fulfillment — address required; encrypted; ship/deliver
19. Checkout — `POST /orders` polymorphic items
20. Paystack webhook finalize — only trusted path issues fulfillments
21. Merch line confirmed — fulfillment after paid
22. Inventory safety — reserve / commit / no oversell / idempotent
23. Merch QR pickup once — scan + double-pickup reject
24. Cancelled/refunded cannot pickup — blocked
25. Buyer dashboard merch — `/dashboard/merchandise`
26. Review requires verified purchase — blocked when unverified
27. Fan Passport merch badges — after paid; revoke on refund
28. Private shipping never public — serializers + analytics scrub
29. Hidden event location not on public merch — redaction tests
30. Vault-exclusive no locked leak — teaser tests

### Bugs found and fixed during final QA

1. **Demo reset FK failure** — `reset_demo_data` deleted events/ticket types while `merch_bundles` still RESTRICT-referenced `ticket_types`. Fixed in `backend/app/demo/reset.py` (delete bundles/carts/products/zones/discounts/charts before events/hosts).
2. **Lint unused imports** — removed unused analytics imports on `/u/[username]/merch`.

### Frontend routes verified present

- `/events/[slug]/merch`
- `/u/[username]/merch`
- `/host/merchandise` (+ `new`, `shipping-zones`, `discounts`, `stock-alerts`, `reviews`, `revenue`, `size-charts`, `print-on-demand`)
- `/host/events/[id]/bundles`
- `/host/events/[id]/post-event-drops`
- `/dashboard/merchandise`
- `/dashboard/cart`
- `/admin/merchandise` (+ `revenue`, `print-on-demand`)

### Deferred by design (do not treat as incomplete Phase work)

- Live Printful / Printify / custom POD provider sync (manual jobs + provider-ready architecture shipped)
- Live carrier label / tracking APIs (manual ship/deliver + tracking number shipped)
- Buyer multi-channel stock-alert notification preferences (host stock alerts shipped)
- Shipping-zone delivery time estimates (fee/geo only; no ETA column)

---

## Merch suite stabilization — earlier same day

| Check | Result |
| --- | --- |
| Merch backend suite | Stabilized from 108/4 → fully green |
| Fixes | Route order for post-event drops; cart 201 status; analytics request_id; demo seed fans/checkout/`_safe` |

See git history / prior conversation for detail.

---

## Configurable fees, host earnings & platform ledger (2026-07-21)

Canonical docs: [FINANCE.md](./FINANCE.md) · [HOST_EARNINGS.md](./HOST_EARNINGS.md) · [PAYOUTS.md](./PAYOUTS.md) · [PAYMENTS.md](./PAYMENTS.md) · [ADMIN.md](./ADMIN.md#finance-fees-earnings-platform-revenue).

| Check | Result |
| --- | --- |
| Global fee settings + host overrides + admin UI | **Implemented** |
| Checkout fee calc + immutable `order_fee_snapshots` + Paystack amount = `final_total` | **Implemented** |
| Buyer checkout fee breakdown (buyer lines only) | **Implemented** |
| Host earnings gross/net + fee terms + CSV | **Implemented** (`/host/earnings`) |
| Admin earnings + platform revenue report + CSV (audited) | **Implemented** |
| Append-only `platform_ledger_entries` (webhook / refund / payout) | **Implemented** (`20260721_0114`) |
| Order fee summary columns | **Implemented** (`20260721_0113`) |
| Support blocked from finance ledgers / fee manage / mark paid | **Confirmed** |
| Help article + admin/host fee help copy | **Updated** |

**Alembic head:** `20260721_0114`  
**Deferred:** live Paystack refund API · partial refunds · automatic payouts · analytics placeholder take-rate cleanup (checkout already uses fee settings)
