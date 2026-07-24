# Pàdéyá SEO Implementation

Brand: **Pàdéyá**  
Companion to [SEO.md](./SEO.md) and [SEO_AUDIT.md](./SEO_AUDIT.md).

---

## Phase 0A — Canonical / indexing safety (shipped)

Scope: origin safety, `metadataBase`, environment noindex, private-route noindex, robots hardening, checkout noindex, unlisted/password event noindex.

### Canonical production domain

| Rule | Value |
|------|-------|
| Production SEO origin | `https://padeya.com` |
| Helper | `getCanonicalSiteOrigin()` in `frontend/src/lib/seo/env-policy.ts` |
| `metadataBase` | Root layout via `rootSeoMetadataFields()` |
| Forbidden hosts | localhost, `*.vercel.app`, `*.onrender.com`, `*.trycloudflare.com`, ngrok hosts, `*.smartlancedesigns.com` |

`siteOrigin()` / `absoluteUrl()` / sitemap / robots sitemap URL all use the canonical helper — never preview or tunnel hosts.

Optional `NEXT_PUBLIC_SITE_URL` / `SITE_URL` overrides are accepted **only** when they validate as `https://padeya.com` (www normalized to apex).

### Indexable environment rules

| Environment | Index? |
|-------------|--------|
| Production (`APP_ENV=production` and/or `VERCEL_ENV=production`, or `NODE_ENV=production` with no non-prod signals) | Yes |
| Development | No |
| Staging / test / preview | No |
| Vercel preview (`VERCEL_ENV=preview`) | No (even if `APP_ENV=production`) |

**Important:** Missing `APP_ENV` on a production Node/`VERCEL_ENV=production` deploy does **not** force noindex.

Non-production protections (layered):

1. Root `metadata.robots` → `noindex, nofollow`
2. `buildPageMetadata` forces noindex when env is non-production
3. `robots.ts` → `Disallow: /` and **no** sitemap advertisement
4. Middleware `X-Robots-Tag: noindex, nofollow`

### Private route policy

Layout-level `privateAreaMetadata()` (HTML robots) **plus** middleware header **plus** robots.txt disallow:

- `/admin`, `/dashboard`, `/host`, `/sponsor`, `/connect`, `/messages`, `/staff`, `/ambassador`
- Auth: `/login`, `/register`, `/forgot-password`, `/reset-password`
- `/account/appeal` (existing), tickets, team invites, demo
- Checkout: `/events/[slug]/checkout`, `/merch/hosts/[username]/checkout`, `/checkout/*`, `/tickets/claim`

Public Support Center (`/support`) remains indexable; `/support/tickets/*` and staff desk routes are noindex.

### Canonical query policy

- Tracking params (`utm_*`, `ref`, `gclid`, …) never enter `alternates.canonical`
- Generic `/events` filter URLs keep canonical `https://padeya.com/events` (via path-only builder)
- Live request URLs may keep query params for attribution (no forced redirect strip)

### Robots policy (production)

Allow `/` with disallows for operational/private trees listed above.  
Sitemap: `https://padeya.com/sitemap.xml`

### Event privacy / indexing (0A)

| Visibility | Meta robots | Sitemap | JSON-LD |
|------------|-------------|---------|---------|
| `listed` | index (prod) | include | Event schema |
| `approval_required` | index (prod) | exclude (listed-only sitemap) | Event schema |
| `unlisted` | **noindex** | exclude | Event schema (still scrubbed) |
| `password_protected` | **noindex** | exclude | **omitted**; generic description only |

---

## Phase 0B — Entity SSR SEO + soft 404s (shipped)

Scope: Host Legacy SSR, sponsor profile SSR, sponsorship marketplace metadata, Fan Passport metadata upgrade, soft HTTP 404 for missing events/merch/sponsors.

**Not in 0B:** Sitemap entity expansion, Product JSON-LD, sitewide Organization/WebSite/SearchAction, location SEO depth.

### Host Legacy (`/u/[username]`, `/@` rewrite)

| Item | Behavior |
|------|----------|
| Rendering | Server `page.tsx` + `LegacyPublicClient` island |
| Missing / inactive | `notFound()` → HTTP 404 |
| Metadata | `buildHostMetadataFromPage` — name, tagline/bio, category slug label, city, cover/avatar, canonical `/u/{username}` |
| JSON-LD | `ProfilePage` → `Organization` (public website/social `sameAs` only; **no** `public_email`) |

Helpers: `frontend/src/lib/seo/host-metadata.ts`

### Sponsor brand (`/sponsors/[slug]`)

| Item | Behavior |
|------|----------|
| Rendering | Server page + `SponsorProfileClient` |
| Missing / private / ineligible | `notFound()` → HTTP 404 (no soft Alert) |
| Metadata | name, bio, industry, categories, locations, logo/cover |
| JSON-LD | `ProfilePage` → `Organization` (no budget/contact/team) |

Helpers: `frontend/src/lib/seo/sponsor-metadata.ts`

### Sponsorship marketplace

| Route | Behavior |
|-------|----------|
| `/sponsorships` | Server metadata + CollectionPage JSON-LD; client filters/grid |
| `/sponsorships/hosts` | Server metadata + CollectionPage JSON-LD; SSR host list shell |

### Soft 404s

| Resource | Missing / unpublished | Still 200 |
|----------|----------------------|-----------|
| Event | `notFound()` | Published (incl. past / sold out) |
| Merch | `notFound()` | Loaded product with `indexable=false` (noindex meta) |
| Sponsor | `notFound()` | Public/unlisted per API reachability |

### Fan Passport (`/f/[username]`)

| Visibility | Meta | JSON-LD |
|------------|------|---------|
| `public` | `buildFanMetadata` (canonical, OG, Twitter, avatar) | `ProfilePage` → `Person` |
| `unlisted` | **noindex** (reachable) | none |
| `private` / missing | HTTP 404 | — |

Helpers: `frontend/src/lib/seo/fan-metadata.ts`

### Social image fallback

Cover → avatar/logo → default `/brand/padeya-og.png` via `pickEntityOgImage` / `resolvePublicAssetUrl`.

---

## Phase 0C — Privacy-safe sitemap completeness (shipped)

Scope: expand `sitemap.xml` with Host Legacy, Fan Passport, Sponsor profiles, `/fans`, non-empty blog hubs, and ambassadors marketing pages — all from public-safe APIs. Remove `/events/search`. No sitemap sharding (scale not required yet).

### Canonical origin

Sitemap URLs always use `getCanonicalSiteOrigin()` → `https://padeya.com`.

### New / updated sitemap resources

| Resource | Source API | Eligibility |
|----------|------------|-------------|
| `/u/{username}` | `GET /legacy/discover/hosts` | Active hosts exposed on public marketplace cards |
| `/f/{username}` | `GET /fans` (paginated) | Public + `appear_in_directory` + not admin-hidden |
| `/sponsors/{slug}` | `GET /sponsors/public/directory` | Active + `visibility=public` + verified |
| `/fans` | static | Fan directory landing |
| `/blog/category\|tag\|author/{slug}` | taxonomy lists ∩ published posts | Hub included only when ≥1 published post in sample |
| `/ambassadors`, `/ambassadors/events`, `/ambassadors/how-it-works` | static marketing | Indexable marketing surfaces |

### Explicitly excluded

Private/inactive hosts · hidden / private / unlisted Fan Passports · pending / unverified / unlisted sponsors · private campaigns · draft / unpublished / non-`listed` events · non-indexable merch · auth / workspace URLs · checkout · token / claim / invite URLs · `/events/search` · faceted query URLs.

Helpers: `frontend/src/lib/seo/sitemap-filter.ts` (`filter*ForSitemap`, `sitemapLastModified`, `isForbiddenSitemapPath`, `buildEntitySitemapPaths`).

### lastModified

- Entity URLs: real `updated_at` / `published_at` via `sitemapLastModified` — **omit** when API has no timestamp (never invent generation time for entities).
- Static marketing / hub shells: generation time is allowed.

### Verification

```bash
cd frontend
npm run test:seo   # includes seo-phase0c-smoke + phase0c vitest
```

---

## Verification (all Phase 0)

```bash
cd frontend
npm run test:seo
npx eslint src/lib/seo …
npx tsc --noEmit
npm run build
```

---

## Phase 1A — Sitewide + Product structured data (shipped)

Scope: Organization / WebSite graph, SearchAction (valid target only), Product/Offer for merch, Event `eventStatus`, BreadcrumbList on entity pages touched here. No location SEO, sitemap sharding, dynamic OG, analytics/GSC, or large faceted-nav changes.

### Architecture

| Stable `@id` | Entity |
|--------------|--------|
| `https://padeya.com/#organization` | Sitewide Organization (root layout `@graph`) |
| `https://padeya.com/#website` | Sitewide WebSite (publisher → Organization `@id`) |
| `{entityUrl}#organization` | Host / Sponsor page Organizations |
| `{entityUrl}#person` | Fan Passport Person |
| `{entityUrl}#event` | Event |
| `{entityUrl}#product` | Merch Product |

Helpers: `frontend/src/lib/seo/site-graph.ts`, `merch-metadata.ts`, `event-metadata.ts` (`eventStatusSchemaUrl`), `jsonld.tsx` (`websiteIdRef` for CollectionPage/FAQ).

### Organization

Emitted once in root layout via `siteGraphJsonLd()`. Fields: name, url, logo (ImageObject), description (`brand.tagline`). `sameAs` only from optional `NEXT_PUBLIC_SOCIAL_SAME_AS` (https only). No address / phone / founding / ratings.

### WebSite

Emitted once in the same `@graph`. `publisher: { "@id": https://padeya.com/#organization }`. CollectionPage / FAQ `isPartOf` uses `{ "@id": WEBSITE_ID }` — no embedded duplicate WebSite.

### SearchAction — decision

| Candidate | Result |
|-----------|--------|
| `/events/search?q={search_term_string}` | **Rejected** — route ignores `q`; not a real search results URL |
| `/events?q={search_term_string}` | **Accepted** — SSR + public `GET /events?q=` without auth |

Implemented template: `https://padeya.com/events?q={search_term_string}`.

### Product / Offer (merch)

`merchProductJsonLd` on `/merch/[slug]` only when product exists, public, `indexable !== false`, and has name/slug/price/currency. Availability map: `purchasable`→InStock, `sold_out`→SoldOut, `coming_soon`→PreOrder; `locked`/`unavailable` omit Offer. No sku, AggregateRating, inventory, vault, or buyer fields.

### Event `eventStatus`

| Platform `status` | schema.org | Notes |
|-------------------|------------|-------|
| `published`, `paused` | `EventScheduled` | Past published stays Scheduled (not Cancelled) |
| `cancelled` | `EventCancelled` | Mapped; public detail currently 404s cancelled |
| postponed / rescheduled | **unsupported** | No first-class status (`postpone_event` only moves datetimes) |
| draft / completed / … | omit | Do not guess |

Password events still emit no Event JSON-LD. Privacy scrubbing unchanged.

### Breadcrumbs (canonical paths)

| Page | Trail |
|------|-------|
| Event | Home → Events → city?/category? → title (existing) |
| Merch | Home → Merch → name |
| Host | Home → Hosts → name |
| Sponsor | Home → Sponsorships → name |
| Fan (public) | Home → Fans → name |

### Verification

```bash
cd frontend
npm run test:seo   # includes seo-phase1a-smoke + phase1a vitest
npm run build
```

---

## Phase 1B — Faceted nav + location SEO (shipped)

Scope: faceted URL index-bloat control, `/events/search` noindex, location SEO fields + thin-hub thresholds, city×category gates, image alts, related internal links, sitemap eligibility. No sitemap sharding, dynamic OG, GA/GSC, or mass-generated location pages.

### Faceted navigation policy

| Surface | Indexable? | Canonical |
|---------|------------|-----------|
| `/events` (no filter params) | Yes | `/events` |
| `/events?sort=` / `?q=` / `?category=` / city/area/price/date/… | **noindex** | `/events` |
| `/events?utm_*` / `?ref=` only | Yes (tracking) | `/events` |
| Curated hubs (`/events/c/*`, `/events/city/*`, weekend/free/vip, …) | Yes when eligible | Own path |
| `/sponsorships?host=` / `?sponsor=` | **noindex** | `/sponsorships` |
| `/hosts`, `/fans`, `/merch` | Path-only canonicals | Own path |

Helper: `frontend/src/lib/seo/facet-policy.ts` (`hasEventsFacetQuery`). Filtering UX unchanged (no forced redirects).

### `/events/search`

- **robots:** `index: false`, `follow: true`
- **canonical:** `https://padeya.com/events`
- Kept as a legacy UX surface (not redirected) — SearchAction still uses `/events?q=`
- Remains excluded from sitemap

### Location SEO model

Migration `20260724_0141_location_seo_fields` adds on `locations`:

| Field | Purpose |
|-------|---------|
| `seo_title` | Curated title |
| `seo_description` | Curated description |
| `intro_content` | Short hub intro |
| `seo_index_mode` | `auto` \| `force_index` \| `force_noindex` |

Fallback titles/descriptions are natural (`locationHubFallbackCopy`) — not keyword-stuffed.

### Thin-hub thresholds (`HUB_ELIGIBILITY`)

| Hub | Default min listed events |
|-----|---------------------------:|
| country / state / city | 2 |
| area | 1 |
| city × category | 2 |

`auto` uses inventory; curated `force_index` / `force_noindex` overrides. Empty valid hubs stay **200 + noindex** (not 404). Sitemap uses the same helpers (`isLocationInSitemap`, `isCityCategoryInSitemap`).

### Image alts

Helpers in `frontend/src/lib/seo/image-alt.ts`. Applied to event heroes/cards, merch gallery, sponsor logo/cover, host Legacy media, fan avatars. Decorative chrome keeps `alt=""`.

### Verification

```bash
cd frontend
npm run test:seo   # includes seo-phase1b-smoke + phase1b vitest
npm run build
```

---

## Phase 1C — GSC / analytics / production smoke (shipped)

Scope: Search Console readiness, optional Bing verification, analytics/consent architecture, production smoke tooling, launch checklist. No dynamic OG, sitemap sharding, AI SEO content, rank tracking, or EventPostponed/Rescheduled.

### Verification metadata

| Env | Emits |
|-----|--------|
| `GOOGLE_SITE_VERIFICATION` (or `NEXT_PUBLIC_…`) | Next.js `metadata.verification.google` |
| `BING_SITE_VERIFICATION` (or `NEXT_PUBLIC_…`) | `metadata.verification.other["msvalidate.01"]` |

Only emitted when configured. Prefer **DNS TXT** (or HTML file) for production ownership; meta tokens are optional. See [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md).

### Analytics decision

| Layer | Role |
|-------|------|
| First-party `AnalyticsProvider` → `/analytics/track*` | Primary product analytics (localStorage/sessionStorage IDs). Not consent-gated. |
| Optional GA4 (`NEXT_PUBLIC_GA_MEASUREMENT_ID`) | Loads only when production SEO **and** consent `granted` on `/cookies`. Missing ID / non-prod / denied / unset → never loads. |

Do not add GTM unless product explicitly requires it. GA4 is optional for launch.

### Consent behavior

- States: `granted` | `denied` | `unset` (`padeya_analytics_consent` in localStorage)
- Control: `OptionalAnalyticsConsentControls` on `/cookies` (hidden if GA not configured)
- First-party operational analytics stay on regardless of GA preference

### Production smoke

```bash
cd frontend
SEO_BASE_URL=https://padeya.com npm run seo:production-smoke
```

Script: `frontend/scripts/seo-production-smoke.mjs`. Pure helpers: `frontend/src/lib/seo/production-checks.ts`.

Checks: robots, sitemap safety, HTTP status (200/404), redirect chains, canonicals, meta/OG/Twitter, JSON-LD type presence, private/noindex samples, faceted `/events` → canonical `/events`.

### Verification

```bash
cd frontend
npm run test:seo   # includes seo-phase1c-smoke + phase1c vitest
npm run build
SEO_BASE_URL=https://padeya.com npm run seo:production-smoke
```

Launch steps: [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md).

---

## Later phases (not done)

- Sitemap index / sharding when URL count requires it
- Dynamic OG images
- EventPostponed / EventRescheduled when product models them
- Admin UI polish for location SEO fields (API already accepts updates)

---

## Post-implementation audit note (2026-07-24)

Re-audit scores:

| Layer | Score |
|-------|------:|
| Original baseline | 52 |
| Code (Phases 0A–1C in workspace) | **88** |
| Live `https://padeya.com` | **54** |

Live `seo:production-smoke` **FAILED** — production still serves pre-phase robots/sitemap/soft-200 behavior. Phases are implemented in the workspace but were **not deployed** at audit time.

**Launch recommendation:** **not ready** until commit/deploy + green production smoke. Details: [SEO_AUDIT.md](./SEO_AUDIT.md#post-implementation-audit--2026-07-24) · [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md).

