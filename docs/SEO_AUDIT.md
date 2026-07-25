# Pàdéyá SEO Audit

**Audit date:** 2026-07-24 (baseline) · **Post-implementation re-audit:** 2026-07-24  
**Scope:** Workspace code (Phases 0A–0C, 1A–1C) + live `https://padeya.com`.  
**Brand spelling:** Pàdéyá.  
**Related:** [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md) · [SEO.md](./SEO.md) · [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md).

**Status legend:** `PASS` · `PARTIAL` · `MISSING` · `INCORRECT` · `RISK` · `FIXED` · `STILL OPEN` · `NOT VERIFIED`  
**Priority:** `P0` launch blocker · `P1` important · `P2` improvement · `P3` optional

---

## Post-implementation audit — 2026-07-24

### Dual scores (do not conflate)

| Layer | Score | Notes |
|-------|------:|-------|
| **Original baseline (pre-phases)** | **52 / 100** | Soft-200 entities, client-only Host/Sponsor, unsafe origin/env, thin sitemap |
| **Code readiness (workspace Phases 0A–1C)** | **88 / 100** | All original P0s **FIXED in code**; remaining = quality/scale/ops |
| **Live production (`padeya.com`)** | **54 / 100** | Phases **not deployed** — production still shows original P0 failures |

**Why code rose (+36):** Phases 0A–1C closed crawl/index blockers (canonical origin, env noindex, entity SSR, true 404s, privacy sitemap, Organization/WebSite/Product, faceted/thin-hub policy, GSC/GA scaffolding, smoke tooling).

**Why live barely moved (+2):** SEO phase work is present in the **local workspace** but **not on the live deploy** probed on 2026-07-24 (`origin/main` lag / undeployed working tree). Live smoke **FAILED**.

### Verification method

| Check | Result |
|-------|--------|
| Code review of SEO modules + routes | Phases present in workspace |
| Local `npm run test:seo` | Pass (80 vitest + phase smokes) |
| `SEO_BASE_URL=https://padeya.com npm run seo:production-smoke` | **FAILED** |
| Live robots / sitemap / HTML samples | Confirms **pre-phase** production |

### Original P0 re-verification

| # | Finding | Code | Live |
|---|---------|------|------|
| 1 | Host Legacy SSR `/u/[username]` | **FIXED** — `app/u/[username]/page.tsx` + `host-metadata.ts` | **STILL OPEN** — miss → HTTP 200 |
| 2 | Sponsor profile SSR `/sponsors/[slug]` | **FIXED** — `sponsors/[slug]/page.tsx` + `sponsor-metadata.ts` | **STILL OPEN** |
| 3 | Sponsorships marketplace metadata | **FIXED** — `sponsorships/page.tsx` + `sponsorshipsIndexMetadata` | **STILL OPEN** — brand-only title; no canonical/OG |
| 4 | Soft-200 events → 404 | **FIXED** — `events/[slug]/page.tsx` `notFound()` | **STILL OPEN** — miss HTTP 200 + noindex |
| 5 | Soft-200 merch → 404 | **FIXED** — `merch/[slug]/page.tsx` `notFound()` | **STILL OPEN** — miss HTTP 200 |
| 6 | Soft-200 sponsors → 404 | **FIXED** | **STILL OPEN** |
| 7 | Preview/staging/dev noindex | **FIXED** — `env-policy.ts`, `robots.ts`, middleware `X-Robots-Tag` | **NOT VERIFIED** (preview); prod robots pre-phase |
| 8 | Canonical origin safety | **FIXED** — `getCanonicalSiteOrigin()` → `https://padeya.com` | **PARTIAL** — padeya.com used; incomplete coverage |
| 9 | Root `metadataBase` | **FIXED** — `layout.tsx` / `rootSeoMetadataFields()` | **STILL OPEN** on live vs phase code |
| 10 | Checkout noindex | **FIXED** — checkout layouts + robots | **STILL OPEN** — live robots omit checkout |
| 11 | `/sponsor` `/connect` `/messages` robots/noindex | **FIXED** | **STILL OPEN** — live robots omit these |
| 12 | Unlisted/password event noindex | **FIXED** — `event-metadata.ts` | **NOT VERIFIED** (no live event sample) |
| 13 | Host/Fan/Sponsor in sitemap | **FIXED** — `sitemap.ts` + `sitemap-filter.ts` | **STILL OPEN** — live has **0** `/u/`, `/f/`, `/sponsors/*` |

**Code P0 resolved:** **13 / 13 FIXED** (no REGRESSED in workspace).  
**Live P0 remaining:** most still open until deploy + smoke pass.

### Phase 1A–1C

| Phase | Code | Live |
|-------|------|------|
| **1A** Organization / WebSite / SearchAction, Product, `eventStatus`, BreadcrumbList | **FIXED** | **STILL OPEN** — home LD empty; no Product entity samples |
| **1B** Faceted `/events` noindex, `/events/search` policy, location SEO, alts | **FIXED** | **STILL OPEN** — `/events/search` still in sitemap; self-canonical; no noindex |
| **1C** GSC/Bing env, GA consent, smoke, launch checklist | **FIXED** | **Ops blocked** — smoke fails; do not request indexing |

### Live production snapshot

**Command:** `SEO_BASE_URL=https://padeya.com npm run seo:production-smoke` → **FAILED**

| Signal | Live observation |
|--------|------------------|
| robots.txt | Allow `/`; disallows host/dashboard/admin/auth; **missing** `/sponsor/`, `/connect/`, `/messages/`, checkout; Sitemap → padeya.com |
| sitemap.xml | **111** URLs; only `https://padeya.com`; **includes `/events/search`**; **0** event entities, hosts, fans, sponsors; merch hubs only; blog + help heavy |
| Home | 200; canonical OK; **no** Organization/WebSite JSON-LD |
| `/hosts` `/fans` `/sponsorships` | Weak/missing canonical + OG; some duplicate titles (`… · Pàdéyá · Pàdéyá`) |
| Missing entities | Soft-**200** |
| Private routes | 200; no obvious robots meta in sampled HTML |
| Sharding | **Not needed** (111 ≪ 50k) |

#### Live sitemap counts

| Category | Count |
|----------|------:|
| Total | 111 |
| Event `/events/{slug}` | **0** |
| Host `/u/*` | **0** |
| Fan `/f/*` | **0** |
| Sponsor `/sponsors/*` | **0** |
| Merch products | **0** (hubs only) |
| Blog posts | 6 |
| Help (articles + hubs) | ~70 |
| Location hubs | **0** |
| `/events/search` (should be gone post-0C) | **1** |

### Category scores (code readiness)

| Category | /10 |
|----------|----:|
| Indexing/environment safety | 9 |
| Canonicalization | 9 |
| Metadata | 8 |
| SSR/crawlability | 7 |
| Structured data | 9 |
| Sitemap | 8 |
| Robots/noindex | 9 |
| Entity SEO | 9 |
| Location SEO | 8 |
| Faceted navigation | 9 |
| Image SEO | 8 |
| Internal linking | 7 |
| Performance risks | 6 |
| Search Console readiness | 8 |
| Analytics/consent | 8 |
| Privacy | 9 |

**Code ≈ 88 / 100.** Live ≈ **54 / 100**.

### Search result quality (live examples)

| URL | Issue |
|-----|--------|
| `/hosts` | Title `Hosts \| Pàdéyá · Pàdéyá` (brand doubled); no canonical/OG |
| `/fans` | Title `Fans · Fan Passport · Pàdéyá · Pàdéyá`; no canonical/OG |
| `/sponsorships` | Title falls back to `Pàdéyá` only |
| `/events/search` | Still self-canonical; indexable meta path on live |
| Missing event/merch | Soft-200 with weak titles (`Event · Pàdéyá`, `Merch · Pàdéyá · Pàdéyá`) |

### Internal linking (code)

Event pages link host/category/location; `/hosts`, `/fans`, `/sponsorships` directory cards link entities. **Live orphan risk:** zero Host/Fan/Sponsor/Event URLs in sitemap → entities only reachable if linked from hubs/content.

### Performance (code-level risk; not measured Lighthouse)

- Client islands on Host Legacy, sponsor, event detail, fans directory, sponsorships.
- Optional GA4 after consent.
- Manrope weights 400–800 via `next/font`.
- No synthetic Lighthouse scores invented.

### Remaining work

#### P0 — launch blockers

1. Commit + **deploy** Phases 0A–1C.
2. Green `seo:production-smoke` against `https://padeya.com`.
3. Confirm live robots/sitemap match phase policy.
4. Do **not** request GSC indexing until smoke passes.

#### P1

1. Ensure public events/hosts/sponsors/merch exist so sitemap has entity coverage.
2. Category hub thin-content gates (parity with location) — **PARTIAL** in code.
3. Post-deploy GSC verify + sitemap submit.
4. Improve crawlable HTML depth on client-heavy entities (incremental).
5. Fix any remaining title-template duplication after deploy.

#### P2

1. Sitemap sharding when scale requires (not now).
2. Dynamic OG images.
3. Admin UI for location SEO fields.
4. Richer location/editorial copy.
5. EventPostponed/Rescheduled when modeled.

#### P3

1. Bing Webmaster (env ready).
2. EventSeries / AggregateRating only with real data.

### Launch recommendation

**not ready**

| Metric | Value |
|--------|------:|
| Code SEO score | **88 / 100** |
| Original score | **52 / 100** |
| Live score | **54 / 100** |
| P0 fixed in code | **13 / 13** |
| Remaining P0 | Deploy + live smoke + GSC gate |
| Live verification | **FAILED** |

After deploy + green smoke → **ready with warnings** (CWV manual, entity inventory, no dynamic OG).

---

## Executive summary (phase delivery notes)

Workspace foundation after Phases 0A–0C + 1A–1C: shared metadata, entity SSR, Event/Profile/Product JSON-LD, site graph, faceted/thin-hub control, robots/sitemap, smoke tooling.

| Metric | Value |
|--------|------:|
| **Code readiness** | **88 / 100** |
| **Live production** | **54 / 100** (undeployed) |
| Remaining P0 | Deploy + production smoke |
| Strongest (code) | Canonical safety, entity SSR, privacy sitemap, structured data, facets |
| Weakest | Live deploy lag; dynamic OG; client-heavy bodies; empty live entity sitemap |

## Historical baseline sections (pre-deploy evidence)

> The sections below retain the **original 2026-07-24 baseline** narrative and many row statuses.
> They are useful for diffing what was found before Phases 0A–1C.
> **Authoritative post-phase status** is in **Post-implementation audit — 2026-07-24** at the top of this file.
> Live `padeya.com` as of the re-audit still matches much of this baseline (phases undeployed).

## Current architecture

| Layer | Location | Role |
|-------|----------|------|
| Shared metadata | `frontend/src/lib/seo/site.ts` | `siteOrigin()`, `absoluteUrl()`, `buildPageMetadata()`, `LIVE_SITE_ORIGIN`, `publicShareOrigin()` |
| Event SEO | `frontend/src/lib/seo/event-metadata.ts` | `buildEventMetadata()`, `eventJsonLd()` |
| Hub SEO | `frontend/src/lib/seo/hub-page.tsx`, `hub-metadata.ts` | Hub meta + `HubJsonLd`; unused `buildHostMetadata()` |
| Blog / Help | `blog-metadata.ts`, `help-metadata.ts` | Article meta + JSON-LD |
| FAQ | `audience-metadata.ts` | `FAQPage` JSON-LD |
| JSON-LD helpers | `frontend/src/lib/seo/jsonld.tsx` | `BreadcrumbList`, `CollectionPage`, `JsonLdScript` |
| Sitemap filter | `frontend/src/lib/seo/sitemap-filter.ts` | Listed events + host/fan/sponsor/merch privacy + forbidden paths |
| Robots | `frontend/src/app/robots.ts` | Dynamic robots.txt |
| Sitemap | `frontend/src/app/sitemap.ts` | Single sitemap (no index split) |
| Middleware | `frontend/src/middleware.ts` | `/@` → `/u` rewrite only |
| Root layout | `frontend/src/app/layout.tsx` | Title template, icons, manifest — **no `metadataBase`** |
| Backend | FastAPI `/api/v1/*` | Public list/detail filters; **no backend robots/sitemap** |

Canonical production intent: **`https://padeya.com`** (`LIVE_SITE_ORIGIN`). Runtime origin resolves from `NEXT_PUBLIC_SITE_URL` / `SITE_URL`, else `http://localhost:3000`.

**Finding — architecture** · `PARTIAL` · **P1**  
Evidence: SEO helpers exist and are reused; Host Legacy builder exists but is unused; root lacks `metadataBase`; env-based origin can leak non-production hosts into canonicals/sitemaps.

---

## Route indexability matrix

### Classification key

| Class | Meaning |
|-------|---------|
| **should-index** | Public marketing / discovery content |
| **cannot-index-now** | Should be indexed but crawlers cannot reliably get content/meta |
| **should-noindex** | Public URL that must not rank |
| **auth/private** | Auth / workspace |
| **duplicate/param** | Facet, alias, or query variant |
| **unknown** | Needs product decision |

### Homepage

| Route | Class | Meta | Notes | Status |
|-------|-------|------|-------|--------|
| `/` | should-index | `buildPageMetadata` | ISR `revalidate=120`; SSR rails | `PASS` · P3 |

### Events

| Route | Class | Meta / schema | Notes | Status |
|-------|-------|---------------|-------|--------|
| `/events` | should-index | Hub + CollectionPage | SSR list + client marketplace; query facets share same canonical path via static hub meta | `PARTIAL` · P1 |
| `/events/[slug]` | should-index | Dynamic + Event + BreadcrumbList | Soft-200 when missing (`EventUnavailableState`) | `PARTIAL` · P0 |
| `/events/[slug]/checkout` | should-noindex | **None** | Client checkout; not in robots disallow | `MISSING` · P0 |
| `/events/[slug]/merch*` | should-index / duplicate | Weak | Event-attached merch; referral `?ref=` | `PARTIAL` · P2 |
| `/events/c/[categorySlug]` | should-index | Dynamic hub | Taxonomy SEO title/desc when set | `PASS` · P2 |
| `/events/city|state|country|area/[slug]` | should-index* | Dynamic hub | SEO fields + inventory thresholds (1B); thin → noindex | `PASS` · 1B |
| `/events/city/[city]/[category]` | should-index* / thin risk | Dynamic | Threshold-gated index + sitemap (1B) | `PASS` · 1B |
| `/events/state/.../[category]` | should-index* / thin risk | Dynamic | Same eligibility helpers | `PASS` · 1B |
| `/events/today`, `this-weekend`, `free`, `vip`, `online`, `in-person`, `hybrid` | should-index | Hub presets | In sitemap (subset) | `PASS` · P2 |
| `/events/under/[maxPrice]` | should-index / thin risk | Dynamic | Price facet landing | `RISK` · P2 |
| `/events/search` | should-noindex | **noindex,follow** + canonical `/events` | Sitemap excluded | `PASS` · 1B |
| `/events/location` | should-index | Hub | Index of location hubs | `PASS` · P2 |
| `/events/near-me`, `/map`, `/calendar` | should-noindex or weak | Placeholder / client geo | Geo should not be indexable with coords | `PARTIAL` · P1 |
| `/events?sort=*`, `?city=*`, `?category=*`, UTM/`ref` | duplicate/param | Same `/events` canonical (static) | Facet URLs not individually canonicalized | `RISK` · P1 |

### Hosts

| Route | Class | Notes | Status |
|-------|-------|-------|--------|
| `/hosts` | should-index | Title/desc only (not full `buildPageMetadata` OG/canonical) | `PARTIAL` · P1 |
| `/hosts/[slug]` | duplicate | Redirect → `/u/[slug]` | `PASS` · P3 |
| `/u/[username]` (`/@` rewrite) | **cannot-index-now** | `"use client"` only; **no** `generateMetadata`; `buildHostMetadata` unused; client `notFound()` | `MISSING` · P0 |
| `/u/[username]/vault`, `/merch`, memories | mixed | Vault teasers public; private Vault content auth | `PARTIAL` · P1 |
| `/hosts/recommendations` | auth-ish / weak | Personalized | `should-noindex` preferred · P2 |

### Fans

| Route | Class | Notes | Status |
|-------|-------|-------|--------|
| `/fans` | should-index | Meta title/desc; directory is **client** (`FansDirectory`) | `PARTIAL` · P1 |
| `/f/[username]` | should-index (public only) | Server fetch + meta title/desc; **no** canonical/OG via `buildPageMetadata`; private → API 404 → `notFound()` | `PARTIAL` · P1 |
| `/passport/[username]` | duplicate | Redirect → `/f/...` | `PASS` · P3 |
| Unlisted passports | unknown | Reachable by URL; not in directory; **still indexable if discovered** | `RISK` · P1 |

### Sponsors / sponsorships

| Route | Class | Notes | Status |
|-------|-------|-------|--------|
| `/sponsors` | duplicate | 301 → `/sponsorships` | `PASS` · P3 |
| `/sponsorships` | should-index | **Fully client**; **no** route metadata | `MISSING` · P0 |
| `/sponsorships/hosts` | should-index | Client marketplace hosts | `MISSING` · P1 |
| `/sponsors/[slug]` | **cannot-index-now** | Client-only; soft-200 “not found”; no meta/JSON-LD | `MISSING` · P0 |
| `/sponsor/*` | auth/private | Workspace; **not** in `robots.ts` disallow | `RISK` · P0 |

### Merch

| Route | Class | Notes | Status |
|-------|-------|-------|--------|
| `/merch`, `/drops`, `/vault`, `/merch-guide` | should-index | `buildPageMetadata` | `PASS` · P2 |
| `/merch/[slug]` | should-index when `indexable` | Meta + Product JSON-LD when indexable; 404 on miss | `PASS` · 1A |
| `/merch/hosts/[username]` | should-index | Dynamic meta | `PARTIAL` · P2 |
| `?h=` host disambiguator | duplicate/param | Canonical strips to `/merch/{slug}` in meta | `PARTIAL` · P2 |

### Content

| Route | Class | Notes | Status |
|-------|-------|-------|--------|
| `/blog`, `/blog/[slug]` | should-index | Strong RSC + Article JSON-LD; draft → 404 | `PASS` · P2 |
| `/blog/category|tag|author/[slug]` | should-index | Dynamic meta; **not in sitemap** | `PARTIAL` · P2 |
| `/help`, `/help/[category]`, `/help/articles/[slug]` | should-index | Strong; Article JSON-LD on articles | `PASS` · P2 |
| `/guides*` | duplicate | 301 → `/blog` | `PASS` · P3 |

### Trust / legal / marketing

| Route | Class | Status |
|-------|-------|--------|
| `/about`, `/contact`, `/privacy`, `/terms`, `/cookies`, `/refund-policy`, `/ticket-policy`, `/community-guidelines`, `/safety`, `/report`, `/accessibility`, `/faq`, `/pricing`, `/for-fans`, `/for-hosts` | should-index | Mostly `PASS` · P3 |
| `/ambassadors*` | should-index | Client landing; **no** metadata export | `MISSING` · P1 |
| `/support` (public) | should-index | OK | `PARTIAL` · P2 |
| `/support/tickets/*`, staff desk | auth/private | Partial robots disallow | `PARTIAL` · P1 |

### Never index (required)

| Route pattern | Current protection | Status |
|---------------|-------------------|--------|
| `/login`, `/register` | robots disallow; title-only meta (**no** robots noindex) | `PARTIAL` · P1 |
| `/forgot-password`, `/reset-password` | title only | `MISSING` · P1 |
| `/checkout/success|failed|claim`, `/tickets/claim` | explicit noindex layouts | `PASS` · P3 |
| `/events/[slug]/checkout` | **none** | `MISSING` · P0 |
| `/dashboard/*`, `/host/*`, `/admin/*` | robots disallow + auth; **no** layout robots | `PARTIAL` · P1 |
| `/sponsor/*` workspace | auth only; **not** in robots | `RISK` · P0 |
| `/connect/*`, `/messages/*` | auth; **not** in robots | `RISK` · P1 |
| `/team/invite/[token]`, claim/token pages | token URLs | `MISSING` · P1 |
| Preview (`/host/legacy/preview`, vault preview) | under `/host/` disallow | `PARTIAL` · P2 |
| `/offline`, `/unauthorized`, `/account/appeal` | noindex | `PASS` · P3 |
| `/demo` | should never be production-indexed | `RISK` · P1 |

---

## Metadata audit

### Global

| Item | Evidence | Status |
|------|----------|--------|
| Title template | `layout.tsx`: `%s · ${brand.name}` → **Pàdéyá** | `PASS` · P3 |
| Default description | `brand.tagline` only at root; pages that omit description inherit weakly | `PARTIAL` · P2 |
| `metadataBase` | **Absent** | `MISSING` · P0 |
| Icons / manifest | Present | `PASS` · P3 |
| Keywords | Not used (good) | `PASS` · P3 |
| Verification tags | None | `MISSING` · P1 |

### Shared builder (`buildPageMetadata`)

Sets: `title`, `description`, `alternates.canonical`, optional `robots`, `openGraph` (title/description/url/siteName/images/type), `twitter` (summary_large_image).

**Missing from builder:** `openGraph.type` variants (`article`), `publishedTime`/`modifiedTime`, locale, `metadataBase`-relative safety.

### Route-level coverage

| Surface | Dynamic from entity? | Gaps |
|---------|----------------------|------|
| Event | Yes — seo_title, social_share_*, banner, privacy scrub | No `eventStatus`; checkout offers URL may be indexable path |
| Host Legacy | **No** (client) | Unused `buildHostMetadata` |
| Fan Passport | Partial — name/tagline only | No canonical/OG/image |
| Sponsor brand | **No** | — |
| Merch | Yes — name/desc/image/`indexable` | Missing product → still indexable generic meta |
| Blog | Yes — seo_*, cover, canonical override, status robots | Strong |
| Help | Yes | Strong |
| Hubs | Title/desc/path; category SEO fields; location SEO fields **requested but Location model has none** | `PARTIAL` |
| Hosts/Fans directories | Static-ish title/desc | Incomplete OG/canonical |
| Sponsorships / Ambassadors | **None** | — |
| Login/Register | Title only | No noindex |

### Duplicate / weak titles

- Pattern `X · Pàdéyá` vs `X | Pàdéyá` inconsistency (passport uses `|`).
- Missing-entity merch meta: `Merch · Pàdéyá` still indexable.
- Missing event: title `"Event"` + noindex (good) but body soft-200 (bad).

**Finding — metadata** · `PARTIAL` · **P0** (metadataBase + Host/Sponsor gaps)

---

## Canonical audit

| Concern | Current behavior | Status |
|---------|------------------|--------|
| Canonical host | `siteOrigin()` from env; fallback localhost | `RISK` · P0 |
| Production hardcode for shares | `publicShareOrigin()` → `https://padeya.com` when local | `PASS` · P2 |
| www / non-www | Not enforced in Next config (infra-dependent) | `UNKNOWN` · P1 |
| http / https | Assumed via env URL | `RISK` · P1 |
| Trailing slash | Next default (no trailing slash); unset in config | `PARTIAL` · P2 |
| Query facets on `/events` | Hub metadata always canonical `/events` (good for filters) but search landing also indexable | `PARTIAL` · P1 |
| Pagination | Mostly client / API cursor — few crawlable `?page=` | `PARTIAL` · P2 |
| UTM / ambassador `ref` | Tracked client-side; not stripped from crawlable URLs by middleware | `RISK` · P1 |
| Merch `?h=` | Meta canonical without query | `PASS` · P2 |
| Aliases | `/hosts/[slug]`, `/passport/*`, `/sponsors`→sponsorships, `/guides`→blog | `PASS` · P3 |
| Vercel preview as canonical | If `NEXT_PUBLIC_SITE_URL` = preview URL → robots + sitemap + canonicals point at preview | `RISK` · P0 |
| Staging | No env-gated noindex | `RISK` · P0 |

**Finding — canonical** · `RISK` · **P0**

---

## Robots audit

**File:** `frontend/src/app/robots.ts`  
**Static `public/robots.txt`:** none (dynamic only).

### Exact directives (current)

```
User-agent: *
Allow: /
Disallow:
  /host/
  /dashboard/
  /admin/
  /support/desk
  /support/cases
  /support/refunds
  /ambassador/
  /staff/
  /api/
  /login
  /register
Sitemap: {siteOrigin}/sitemap.xml
```

| Check | Status |
|-------|--------|
| Sitemap declaration | `PASS` · P3 |
| Private workspaces partially covered | `PARTIAL` · P1 |
| `/sponsor/`, `/connect/`, `/messages/`, checkout, claim tokens | `MISSING` · P0 |
| Non-production `Disallow: /` or noindex | `MISSING` · P0 |
| robots.txt as sole private protection | Documented risk — auth still required | `RISK` · P1 |

Note: `docs/SEO.md` claims broader `/support/` disallow than code implements.

---

## Sitemap audit

**File:** `frontend/src/app/sitemap.ts` · single response · `revalidate` 300 on API fetches · limit 100 on blog/help/merch · **Phase 0C privacy-safe entity expansion**.

### Included

- Static: `/`, `/events`, location index, hosts, **`/fans`**, sponsorship marketplace + hosts, weekend/free/vip, blog, help, about, for-hosts/fans, merch*, pricing, faq, contact, support, legal, safety, report, accessibility, today, **ambassadors marketing**
- Dynamic: listed events, categories, taxonomy locations (country/state/city/area), city×category derived from events, published blog + help articles + help categories, **non-empty blog category/tag/author hubs**, indexable merch (limit 100), **Host Legacy `/u/*`**, **directory Fan Passports `/f/*`**, **verified public Sponsors `/sponsors/*`**

### Excluded / missing

| Resource | In sitemap? | Status |
|----------|-------------|--------|
| Host Legacy `/u/*` | Yes (discover API) | `PASS` · 0C |
| Fan passports `/f/*` | Yes (directory-eligible public only) | `PASS` · 0C |
| `/fans` directory | Yes | `PASS` · 0C |
| Sponsor brand `/sponsors/[slug]` | Yes (public directory) | `PASS` · 0C |
| Blog category/tag/author | Yes when non-empty | `PASS` · 0C |
| Ambassadors marketing | Yes | `PASS` · 0C |
| `/events/search` | **Removed** | `PASS` · 0C |
| Unpublished / non-listed events | Filtered | `PASS` |
| Draft blog/help | Filtered by status | `PASS` |
| Private / unlisted / hidden passports | Never (directory API) | `PASS` |
| Pending / unlisted sponsors | Never (directory API) | `PASS` |
| lastModified | Real entity timestamps; omit when absent (no invented `now` for entities) | `PASS` · 0C |
| Localhost / Vercel URLs | Blocked by `getCanonicalSiteOrigin()` | `PASS` · 0A |

### Scale

Single sitemap; merch/blog capped at 100. Sharding **not** required at current scale. At marketplace scale (tens of thousands of events + locations + products), **sitemap index + splitting will be required**.

**Finding — sitemap** · `PASS` (Phase 0C) · remaining scale work is P2

---

## Structured data audit

| Schema | Where | Status |
|--------|-------|--------|
| Organization (sitewide) | Root layout `@graph` → `https://padeya.com/#organization` | `PASS` · 1A |
| WebSite + SearchAction | Root `@graph`; SearchAction → `/events?q={search_term_string}` (not `/events/search`) | `PASS` · 1A |
| BreadcrumbList | Events, hubs, merch detail, host, sponsor, fan (public), for-fans/hosts | `PASS` · 1A |
| CollectionPage | Hubs; `isPartOf` → WebSite `@id` (no duplicate WebSite) | `PASS` · 1A |
| Event | `eventJsonLd` — privacy-aware + `eventStatus` | `PASS` · 1A |
| Event `eventStatus` | `published`/`paused`→Scheduled; `cancelled`→Cancelled; no Postponed/Rescheduled in model | `PASS` · 1A (partial platform) |
| EventSeries | None | `MISSING` · P3 |
| Offer currency (events) | Hardcoded `NGN` on ticket offers | `PARTIAL` · P2 |
| Person / ProfilePage (Fan) | Public only | `PASS` · 0B |
| Organization / ProfilePage (Host/Sponsor) | Page-specific `@id` (not sitewide) | `PASS` · 0B/1A |
| Product | Indexable merch detail | `PASS` · 1A |
| Article / BlogPosting | Blog uses `Article` (not BlogPosting); help uses `Article` | `PARTIAL` · P2 |
| FAQPage | `/faq`, `/for-fans`, `/for-hosts` (eligible rendered FAQs) | `PASS` · P2 |
| HowTo | None observed (good — not fabricated) | `PASS` · P3 |

### Event schema quality notes

- Privacy scrubbing for street address in meta + JSON-LD: **strong** (`event-metadata.ts`).
- Approx coordinates not emitted in JSON-LD (good); still present in API payload.
- Offers link to `/events/{slug}/checkout` (checkout should be noindex).
- No performer unless real — currently omitted (correct).
- Sold out via Offer availability InStock/SoldOut.
- `eventStatus` mapped for published/cancelled; Postponed/Rescheduled not modeled in product.

**Finding — structured data** · `PASS` (Phase 1A core) · remaining: EventSeries, event ticket currency flexibility, AggregateRating only if real public reviews ship

---

## Social sharing audit

| Surface | OG / Twitter | Dynamic OG image route | Status |
|---------|--------------|------------------------|--------|
| Default | `/brand/padeya-og.png` | None | `PASS` · P2 |
| Event | Entity image or default | No `opengraph-image.tsx` | `PARTIAL` · P2 |
| Host Legacy | **None** (client) | — | `MISSING` · P0 |
| Fan | Title/desc only | — | `PARTIAL` · P1 |
| Sponsor | **None** | — | `MISSING` · P0 |
| Merch | Cover when present | — | `PARTIAL` · P2 |
| Blog | og_image / cover | — | `PASS` · P2 |
| ImageResponse | Not used | — | `MISSING` · P3 |

Share cards for Host/Sponsor will currently look like generic site fallbacks or empty client shells.

---

## Image SEO audit

| Finding | Evidence | Status |
|---------|----------|--------|
| Empty `alt=""` on event heroes, related cards, map thumbs, lineup | `EventPublicView`, discovery cards | `INCORRECT` · P1 |
| Host Legacy empty alts | `LegacyPublicPageRenderer` | `INCORRECT` · P1 |
| Merch gallery empty alts | Marketplace components | `INCORRECT` · P1 |
| Blog cover alts | Meaningful helpers | `PASS` · P3 |
| Decorative empty alt | Sometimes intentional | `PARTIAL` · P2 |
| `next/image` remotePatterns | **None** in `next.config.ts` | `RISK` · P2 |
| Formats avif/webp | Enabled | `PASS` · P3 |
| Wrong-domain absolute assets | Env-dependent API/media proxy `/media/*` | `RISK` · P1 |

---

## Internal linking audit

| Path | Status |
|------|--------|
| Header → Events, Hosts, Fans, Sponsors (`/sponsorships`), Shop, Resources | `PASS` · P3 |
| Footer → Discover, audiences, legal, company | `PASS` · P3 |
| Event → host (`/@slug`), category/city crumbs, related events | `PASS` · P2 |
| Host → events / merch / vault | Present in Legacy UI (client) | `PARTIAL` · P1 |
| Sponsor → sponsored events | Client profile | `PARTIAL` · P1 |
| Blog → related content | Present | `PASS` · P2 |
| Location → events | Hub pages | `PASS` · P2 |
| Breadcrumbs UI + JSON-LD | Events/hubs strong; blog/help lighter | `PARTIAL` · P2 |

### Orphans / weak

- Individual Host Legacy & Fan Passport & Sponsor brand URLs **in sitemap** (Phase 0C) via public directory/discover APIs.
- Ambassadors pages not in primary nav/sitemap.
- Host directory cards may not be crawlable as `<a href>` depending on card implementation (verify before launch).

**Finding — internal linking** · `PARTIAL` · **P1**

---

## Faceted navigation audit

| List | Mechanism | Crawlability | Recommendation (do not implement yet) |
|------|-----------|--------------|----------------------------------------|
| `/events` | Query params + SSR for non-geo filters; client marketplace | Facets share `/events` canonical | Canonical parent; dedicated hubs for city/category only |
| Hosts | Client filters on SSR initial | Weak facet URLs | Keep directory indexable; noindex sort variants |
| Fans | Client directory | Low | Index `/fans` + public passports only |
| Sponsors marketplace | Client + `?host=` | Low | Canonical `/sponsorships`; noindex filtered |
| Merch | Client + API sort | Product pages indexable via flag | noindex vault/private visibility |
| Blog | RSC filters | Category/tag/author hubs OK | Include hubs in sitemap when non-thin |

**Infinite scroll / client-only:** Fans, sponsorships, ambassadors, Host Legacy — primary content after JS.

**Finding — faceted nav** · `RISK` · **P1** (index bloat + thin city×category)

---

## Rendering / crawlability audit

| Page | Mode | Primary content for bots | Status |
|------|------|--------------------------|--------|
| Home | RSC + ISR | Good | `PASS` |
| Events index | RSC + client enhance | List SSR’d | `PASS` |
| Event detail | RSC meta/JSON-LD + client body | Title/desc/schema in HTML; rich body hybrid | `PARTIAL` |
| Location/category hubs | RSC shell + client lists | Meta good; list may be client | `PARTIAL` |
| Blog / help articles | RSC | Good | `PASS` |
| Host Legacy | **Client-only** | Shell + root defaults | `MISSING` · P0 |
| Sponsor brand | **Client-only** | Soft empty | `MISSING` · P0 |
| Sponsorships | **Client-only** | Weak | `MISSING` · P0 |
| Fans directory | Client | Weak | `PARTIAL` · P1 |
| Fan passport | RSC data + client view | Meta in HTML; body client | `PARTIAL` |
| Merch detail | Meta SSR; body client | Partial | `PARTIAL` |
| Checkout | Client | Should be noindex | `RISK` |

Caching: event `revalidate=120`, hubs ~90–180, blog 300 — reasonable ISR.

---

## Status code / redirect audit

| Case | Behavior | Status |
|------|----------|--------|
| Global `not-found.tsx` | HTTP 404 + noindex | `PASS` |
| Blog/help unpublished | `notFound()` | `PASS` |
| Fan private/missing | `notFound()` | `PASS` |
| Host inactive/missing | Client `notFound()` after fetch — **may briefly 200** | `RISK` · P1 |
| Event unpublished/cancelled/archived/paused | API 404 → FE soft UI **HTTP 200** + meta noindex | `INCORRECT` · P0 |
| Merch missing | Soft Alert **200** + indexable generic meta | `INCORRECT` · P0 |
| Sponsor missing | Soft Alert **200** | `INCORRECT` · P0 |
| Redirect aliases | Mostly permanent 301/308 in `next.config.ts` | `PASS` |
| Redirect chains | Relatively short | `PASS` · P3 |

Backend: non-published events → indistinct 404 (good privacy). Past **still-published** events remain detail-reachable (list excludes past) — good for long-tail if pages stay 200 with accurate schema.

---

## Event lifecycle SEO audit

| State | Public API | FE page | Sitemap | Event JSON-LD | Recommendation |
|-------|------------|---------|---------|---------------|----------------|
| Upcoming published listed | Detail + list | Full | Include | Present (no eventStatus) | Keep |
| Unlisted / password | Detail by slug; **not** list/sitemap | Indexable if discovered | Exclude | Present | **noindex** unlisted; gate password |
| Approval required | List + detail | Indexable | Filter treats non-listed only — approval_required may be excluded by filter (`listed` only) | Present | Confirm product intent |
| Sold out | Detail | Offers SoldOut | Include | OK | Keep live |
| Past (still published) | Detail yes; list no | Live | May remain until status changes | Dates in past | **Keep for history/long-tail**; add `EventScheduled`/`EventCompleted` when modeled |
| Postponed | Status may stay published with new dates | Live | Include | Dates update; no Postponed status | Add `eventStatus` when API exposes |
| Cancelled / archived / paused / draft | API 404 | Soft-200 unavailable | Excluded | None | Must be **HTTP 404** (or 410) |
| Deleted | 404 | Soft-200 | Excluded | None | Same |

**Finding — lifecycle** · `PARTIAL` · **P0** (soft 404) / **P1** (eventStatus + unlisted noindex)

---

## Location SEO audit

| Item | Status |
|------|--------|
| Routes country/state/city/area + city×category | Present |
| Metadata | Generated titles; Location **DB has no seo_title/seo_description** (unlike categories) | `PARTIAL` · P1 |
| Canonical | Hub path | `PASS` · P2 |
| Breadcrumbs + CollectionPage | Yes | `PASS` |
| Sitemap | Taxonomy locations + event-derived cities | `PASS` · P2 |
| Thin pages | Area + city×category combos risk thin/near-duplicate | `RISK` · P1 |
| Unique content | Relies on event listings + generic subtext | `PARTIAL` · P1 |

**Do not mass-generate empty location pages.** Prefer index only hubs with sufficient upcoming (or curated historical) inventory + unique intro copy.

---

## UGC SEO audit

| UGC | Indexable? | Notes | Status |
|-----|------------|-------|--------|
| Fan Passport (public) | Yes (intended) | Privacy 404 for private; unlisted discoverable | `PARTIAL` · P1 |
| Fan directory | Yes | Public + appear_in_directory only | `PASS` · P2 |
| Host Legacy bio/reviews | Yes (intended) | Client SEO gap; reviews may expose ticket/user UUIDs in API | `RISK` · P1 |
| Event descriptions (host UGC) | Yes | Moderation-dependent; address scrubbing partial on body fields | `PARTIAL` · P1 |
| Blog comments | On-page; published only | Prefer noindex fragments / no separate URLs | `PASS` · P3 |
| Merch reviews | On product page | OK if moderated | `PARTIAL` · P2 |
| Vault protected content | Never index full content | Teasers only | `PASS` · P1 |

Spam/thin: public passports with empty bios are thin — consider noindex below quality threshold (P2).

---

## Performance SEO risks

Code-level only (no Lighthouse run in this audit).

| Risk | Evidence | Priority |
|------|----------|----------|
| Client-heavy entity pages (Legacy, sponsors, sponsorships) | `"use client"` + post-hydration fetch | P0 crawl + LCP |
| Root providers hydrate globally | Auth, Analytics, Pwa, Theme, Notifications | P1 INP/JS |
| Manrope via `next/font` | Good (`display: swap`) | PASS |
| Empty hero alts / unsized media | CLS risk on banners | P1 |
| Third-party scripts | No GA/GTM today (good for perf; bad for GSC analytics) | — |
| Blocking API on sitemap generation | Many parallel fetches; 100-cap | P2 |
| Dynamic import on home taxonomy | Good pattern | PASS |
| Large checkout bundle reachable from Offer URLs | P2 |

---

## Environment / indexing safety

| Env | Expected | Actual | Status |
|-----|----------|--------|--------|
| Development | noindex | robots always allow `/`; origin localhost | `RISK` · P0 |
| Staging | noindex | No `VERCEL_ENV` / staging gate | `RISK` · P0 |
| Vercel preview | noindex + non-prod canonical | No middleware `X-Robots-Tag`; sitemap uses `siteOrigin()` | `RISK` · P0 |
| Production | index with `https://padeya.com` | Relies on correct env | `PARTIAL` · P0 |
| Cloudflare tunnel / ngrok | In `allowedDevOrigins` | Can become share origin if misconfigured | `RISK` · P1 |

`publicShareOrigin()` mitigates **client** share links when local; **server** canonical/sitemap/robots do **not** use the same live fallback.

---

## Privacy risks

| Risk | Severity | Status |
|------|----------|--------|
| Private street in Event meta/JSON-LD | Mitigated by scrub helpers | `PASS` · P1 |
| Description body may still contain address fragments in API | Residual | `RISK` · P1 |
| Approx lat/lng in public event JSON | Residual (not in JSON-LD) | `RISK` · P2 |
| Unlisted/password events slug-reachable + indexable meta | High | `RISK` · P0 |
| Legacy listing non-listed host events | Medium | `RISK` · P1 |
| Host `public_email` when opt-in | Intentional; avoid in meta if possible | `PARTIAL` · P2 |
| Review `ticket_id` / `reviewer_user_id` on Legacy API | Medium | `RISK` · P1 |
| Checkout / orders / messages / Vault / admin | Not in public SEO helpers | `PASS` · P1 |
| Sponsor contact email/phone | Not in public serialize | `PASS` · P1 |

SEO endpoints should never emit ticket ownership, CRM notes, or Vault unlocks — current public serializers largely respect this.

---

## Search Console readiness

| Capability | Status |
|------------|--------|
| GSC verification meta / DNS docs in code | `MISSING` · P1 |
| Bing verification | `MISSING` · P3 |
| GA4 / gtag / GTM | `MISSING` · P2 (first-party analytics only) |
| Consent / CMP | `MISSING` · P2 (cookies page mentions future consent) |
| Conversion tracking (SEO-attributed) | First-party UTM capture in `AnalyticsProvider` | `PARTIAL` · P2 |
| Sitemap submitted via robots | Ready **once** production origin correct | `PARTIAL` · P1 |

---

## Existing strengths

1. Central `buildPageMetadata` with canonical + OG + Twitter (`site.ts`).
2. Event SEO fields + privacy-aware JSON-LD (`event-metadata.ts`).
3. Blog & Help: published gating, Article JSON-LD, custom canonical, sitemap inclusion.
4. Discovery hubs: CollectionPage + BreadcrumbList (`hub-page.tsx`, `jsonld.tsx`).
5. Listed-only event sitemap filter (`sitemap-filter.ts`).
6. Merch `indexable` flag honored in meta + sitemap.
7. Fan Passport private → indistinct 404.
8. Global 404 noindex (`not-found.tsx`).
9. Checkout success/failed/claim noindex layouts.
10. Brand name **Pàdéyá** in root title template and legal/marketing copy.
11. FAQPage only on pages that render FAQs.
12. Product intent documented in `docs/SEO.md` (even where code lags).

---

## Critical issues

| ID | Finding | Status | Priority | Phase |
|----|---------|--------|----------|-------|
| C1 | Host Legacy `/u/[username]` client-only; no SSR metadata/JSON-LD | **FIXED (0B)** | — | 0B |
| C2 | Sponsor brand `/sponsors/[slug]` client-only; soft-200; no meta | **FIXED (0B)** | — | 0B |
| C3 | Event/merch/sponsor missing → HTTP 200 soft pages | **FIXED (0B)** | — | 0B |
| C4 | No preview/staging/dev automatic noindex / `X-Robots-Tag` | **FIXED (0A)** | — | 0A |
| C5 | `siteOrigin()` can publish localhost/preview as canonical + sitemap | **FIXED (0A)** | — | 0A |
| C6 | Checkout `/events/[slug]/checkout` indexable | **FIXED (0A)** | — | 0A |
| C7 | `/sponsor`, `/connect`, `/messages` missing from robots disallow | **FIXED (0A)** | — | 0A |
| C8 | No root `metadataBase` | **FIXED (0A)** | — | 0A |
| C9 | Sponsorships marketplace no route metadata (client) | **FIXED (0B)** | — | 0B |
| C10 | Sitemap omits hosts, fans, sponsor brands | **FIXED (0C)** | — | 0C |
| C11 | Unlisted/password events slug-reachable + indexable meta | **FIXED (0A)** | — | 0A |

---

## Missing features

| Feature | Priority |
|---------|----------|
| Sitewide Organization + WebSite + SearchAction JSON-LD | P1 |
| Product (+ Offer) JSON-LD for merch | P1 |
| ProfilePage / Organization for Host Legacy | P0 |
| Person / ProfilePage for Fan Passport | P2 |
| Dynamic OG image generation | P3 |
| Sitemap index + sharding | P2 (P1 at scale) |
| Facet/search noindex policy | P1 |
| Unlisted event `noindex` | P0 |
| Event `eventStatus` | P1 |
| Location SEO fields in DB | P1 |
| GSC verification + analytics consent path | P1–P2 |
| Page-level robots on auth layouts | P1 |
| Align `docs/SEO.md` with code | P2 |

---

## Recommended implementation roadmap

### Phase 0 — Launch blockers (P0)

#### Phase 0A — Canonical / indexing safety (**done 2026-07-24**)

1. ~~Add `metadataBase` + production-safe `siteOrigin()`~~ → `getCanonicalSiteOrigin()` / `rootSeoMetadataFields()`
2. ~~Env gate: staging/preview → noindex + robots Disallow `/` + `X-Robots-Tag`~~
3. ~~noindex checkout + expand robots disallow (`/sponsor/`, `/connect/`, `/messages/`, checkout, tokens)~~
4. ~~noindex unlisted/password-protected events~~
5. Private workspace layout `privateAreaMetadata` + middleware headers

#### Phase 0B — Entity SSR + soft 404s (**done 2026-07-24**)

1. ~~Host Legacy SSR/`generateMetadata` + Organization/ProfilePage JSON-LD~~
2. ~~SSR metadata for `/sponsors/[slug]` and `/sponsorships`; hard `notFound()` on miss~~
3. ~~Replace soft-200 event/merch/sponsor misses with `notFound()`~~
4. ~~Fan Passport `buildFanMetadata` + public Person / unlisted noindex~~

#### Phase 0C — Privacy-safe sitemap (**done 2026-07-24**)

1. ~~Host Legacy `/u/*`, Fan `/f/*` (directory), Sponsor `/sponsors/*`, `/fans`, blog hubs, ambassadors marketing in sitemap~~
2. ~~Remove `/events/search`; entity `lastModified` without invented `now`~~
3. ~~Privacy filter tests — private entities cannot enter~~

#### Phase 1B — Faceted nav + location SEO (**done 2026-07-24**)

1. ~~Faceted `/events` noindex + canonical `/events`; `/events/search` noindex/follow~~
2. ~~Location SEO fields + thin-hub thresholds; city×category gates; sitemap alignment~~
3. ~~Public image alts + related internal links~~

#### Phase 1C — GSC / analytics / production smoke (**done 2026-07-24**)

1. ~~Optional `GOOGLE_SITE_VERIFICATION` / `BING_SITE_VERIFICATION` via Next metadata~~
2. ~~First-party analytics primary; optional consent-gated GA4~~
3. ~~Production smoke script + launch checklist~~

#### After 1C — remaining

1. Sitemap index / sharding when scale requires it.
2. Dynamic OG images.
3. Admin UI polish for location SEO fields.
4. Live GSC property verify + sitemap submit (ops; see launch checklist).

### Phase 1 — Important (P1)

1. ~~Product JSON-LD; WebSite/Organization/SearchAction~~ (**done 1A**)
2. ~~Faceted `/events` search noindex; keep curated hubs indexable~~ (**done 1B**)
3. Image alts on public heroes; location SEO columns or curated copy (**done 1B**; continue polishing)
4. Page-level noindex on auth layouts; login/register robots.
5. ~~Event `eventStatus`~~ (**done 1A**; Postponed/Rescheduled still unsupported)
6. ~~GSC verification + first-party/GA decision + consent~~ (**done 1C**; live GSC submit is ops)
7. Ambassadors marketing metadata.

### Phase 2 — Improvements (P2)

1. Sitemap index; raise entity caps; blog taxonomy URLs.
2. Stronger Fan Passport OG/canonical; unlisted noindex option.
3. Dynamic OG images; BreadcrumbList on blog/help.
4. Performance: reduce client islands on public entities.

### Phase 3 — Optional

1. EventSeries; HowTo only if truly eligible; advanced hreflang if multi-locale ships.
2. Bing Webmaster (optional env already supported in 1C).

---

## Appendix A — Key file index

| Path | Role |
|------|------|
| `frontend/src/lib/seo/site.ts` | Origin + metadata builder + verification |
| `frontend/src/lib/seo/verification.ts` | GSC / Bing verification env |
| `frontend/src/lib/seo/production-checks.ts` | Production smoke helpers |
| `frontend/src/lib/analytics-consent.ts` | Optional GA4 consent |
| `frontend/scripts/seo-production-smoke.mjs` | Live SEO smoke |
| `docs/SEO_LAUNCH_CHECKLIST.md` | Post-deploy GSC / CWV steps |
| `frontend/src/lib/seo/event-metadata.ts` | Event meta + Event JSON-LD |
| `frontend/src/lib/seo/hub-page.tsx` | Hub meta + JSON-LD |
| `frontend/src/lib/seo/hub-metadata.ts` | Unused `buildHostMetadata` |
| `frontend/src/lib/seo/blog-metadata.ts` | Blog |
| `frontend/src/lib/seo/help-metadata.ts` | Help |
| `frontend/src/lib/seo/jsonld.tsx` | Breadcrumb/Collection helpers |
| `frontend/src/lib/seo/sitemap-filter.ts` | Listed filter |
| `frontend/src/app/robots.ts` | robots.txt |
| `frontend/src/app/sitemap.ts` | sitemap.xml |
| `frontend/src/app/layout.tsx` | Global metadata |
| `frontend/src/middleware.ts` | `/@` rewrite |
| `frontend/src/app/events/[slug]/page.tsx` | Event SSR SEO |
| `frontend/src/app/u/[username]/page.tsx` | Host Legacy (client) |
| `frontend/src/app/sponsors/[slug]/page.tsx` | Sponsor brand (client) |
| `frontend/src/app/f/[username]/page.tsx` | Fan Passport |
| `frontend/src/app/merch/[slug]/page.tsx` | Merch meta |
| `backend/app/events/service.py` | `public_event_detail`, list filters |
| `docs/SEO.md` | Intent doc (partially stale) |

## Appendix B — Doc drift

`docs/SEO.md` claims Host Legacy has metadata + Organization JSON-LD and broader robots disallow for `/support/`. **Code does not match.** Treat this audit as source of truth until SEO.md is updated in an implementation pass.

---

## Production indexability regression audit — 2026-07-26

### PageSpeed `/events` finding

PageSpeed Insights reported `https://padeya.com/events` as **“Page is blocked from indexing”**. Prior production SEO smoke was green but did **not** hard-fail accidental public `noindex`.

### Exact `/events` root cause (LIVE + CODE)

| Layer | Finding | Status |
|-------|---------|--------|
| LIVE HTML meta robots | No `noindex` / no `googlebot` noindex on `/events` | **LIVE VERIFIED** indexable-by-default |
| LIVE `X-Robots-Tag` | Absent on `/events` | **LIVE VERIFIED** |
| LIVE robots.txt | Allows `/events` (checkout wildcards do not match) | **LIVE VERIFIED** |
| LIVE canonical | `https://padeya.com/events` | **LIVE VERIFIED** |
| CODE defect | `buildPageMetadata({… robots: undefined })` clears root `index,follow` in Next.js metadata merge — public hubs emit **no** robots meta | **CODE VERIFIED** (fixed) |
| CODE risk | `APP_ENV`/`NEXT_PUBLIC_APP_ENV=staging` previously beat `VERCEL_ENV=production` → sitewide noindex | **CODE VERIFIED** (fixed: production platform wins + warning) |
| WWW | `https://www.padeya.com/events` served **200** (canonical apex) — duplicate host | **LIVE VERIFIED** (www→apex redirect added) |

**Blocker classification for the PageSpeed report:** most consistent with a **historical / env-misclassification meta robots noindex** (or PSI/Search Console stale signal). At audit time the live `/events` response was **not** blocked by meta, Googlebot meta, `X-Robots-Tag`, or robots.txt.

### Inventory checked

- **45** static public/intentional routes probed live
- **196** sitemap URLs; sampled **5+5+5+4+5+5+5+10** across events/hosts/fans/sponsors/merch/blog/help/hubs
- **0** accidental public noindex routes on live production
- **0** sitemap URL indexability conflicts on live samples

### Fixes shipped in workspace

1. Explicit `INDEXABLE_ROBOTS` from `buildPageMetadata` (never `robots: undefined`)
2. Env precedence: true `VERCEL_ENV=production` is not silent-noindexed by mis-set `APP_ENV`
3. www → apex permanent redirect in `next.config.ts`
4. Ambassadors + Support public layouts get canonical metadata
5. Soft facet/thin-hub noindex uses `noIndexFollow`
6. `seo:production-smoke` hard-fails public noindex + samples sitemap categories
7. New `seo:indexability-audit` matrix script + `indexability.ts` helpers/tests

### Intentionally noindex (confirmed LIVE)

`/login`, `/register`, `/dashboard`, `/host`, `/sponsor`, `/events/search`, faceted `/events?q|sort|category=…`, checkout/private trees (middleware `X-Robots-Tag`).

### Post-deploy verification

```bash
curl -sL https://padeya.com/events | grep -iE 'name="robots"|name="googlebot"'
curl -sI https://padeya.com/events | grep -i 'x-robots-tag'
curl -sIL https://www.padeya.com/events | grep -iE 'HTTP/|location:|x-robots-tag'
cd frontend && SEO_BASE_URL=https://padeya.com npm run seo:production-smoke
cd frontend && SEO_BASE_URL=https://padeya.com npm run seo:indexability-audit
```

Expected after deploy: public hubs emit `index, follow`; www redirects to apex; smoke green.
