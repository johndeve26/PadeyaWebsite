# SEO

Marketplace SEO, structured data, sitemap, and robots for Pàdéyá public surfaces.

**Related:** [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) · [SEO_AUDIT.md](./SEO_AUDIT.md) · [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md) · [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [API.md](./API.md)

---

## Principles

- Public pages get per-entity **title**, **description**, **canonical**, Open Graph, and Twitter card.
- Reuse stored `seo_title` / `seo_description` / `social_share_*` when set; else fall back to title / tagline / truncated description.
- Brand name **Pàdéyá** appears in the root title template.
- Prefer server `generateMetadata` (thin server `page.tsx` + client view) for entity pages.
- Location in meta and JSON-LD follows the same privacy path as public APIs: city / area / `public_location_label` only when address is hidden; **never** private online URLs.
- **Canonical origin is always `https://padeya.com`** for SEO surfaces (never localhost, Vercel preview, Render, or tunnel hosts).
- **Non-production environments are noindex** (metadata + robots.txt + `X-Robots-Tag`).

---

## Helpers

| Module | Role |
|--------|------|
| `frontend/src/lib/seo/env-policy.ts` | `getCanonicalSiteOrigin`, `shouldIndexEnvironment`, `isProductionSeoEnvironment` |
| `frontend/src/lib/seo/site.ts` | `siteOrigin`, `absoluteUrl`, `buildPageMetadata`, `rootSeoMetadataFields`, default OG |
| `frontend/src/lib/seo/site-graph.ts` | Organization / WebSite `@graph`, SearchAction, stable `@id`s |
| `frontend/src/lib/seo/noindex.ts` | `privateAreaMetadata`, `NOINDEX_ROBOTS` |
| `frontend/src/lib/seo/canonical-path.ts` | Strip tracking params from canonical paths |
| `frontend/src/lib/seo/event-metadata.ts` | `buildEventMetadata`, `eventJsonLd`, `eventStatusSchemaUrl`, unlisted/password noindex |
| `frontend/src/lib/seo/merch-metadata.ts` | Product / Offer JSON-LD for indexable merch |
| `frontend/src/lib/seo/host-metadata.ts` | Host Legacy meta + ProfilePage/Organization JSON-LD |
| `frontend/src/lib/seo/sponsor-metadata.ts` | Sponsor brand + sponsorships index meta + Organization JSON-LD |
| `frontend/src/lib/seo/fan-metadata.ts` | Fan Passport meta + public Person JSON-LD |
| `frontend/src/lib/seo/public-asset.ts` | Absolute OG/image URL helpers |
| `frontend/src/lib/seo/hub-metadata.ts` | Hub metadata; re-exports `buildHostMetadata` |
| `frontend/src/lib/seo/jsonld.tsx` | `breadcrumbJsonLd`, `collectionPageJsonLd` (`isPartOf` → WebSite `@id`), `JsonLdScript` |
| `frontend/src/lib/seo/sitemap-filter.ts` | Privacy filters + `sitemapLastModified` + forbidden paths |
| `frontend/src/lib/seo/facet-policy.ts` | Faceted `/events` noindex + `/events/search` policy |
| `frontend/src/lib/seo/hub-eligibility.ts` | Location / city×category thin-hub thresholds |
| `frontend/src/lib/seo/image-alt.ts` | Public media alt helpers |
| `frontend/src/lib/seo/verification.ts` | Optional GSC / Bing `metadata.verification` |
| `frontend/src/lib/seo/production-checks.ts` | Live smoke parsers (canonical, JSON-LD, sitemap) |
| `frontend/src/lib/analytics-consent.ts` | Optional GA4 consent gating |
| `frontend/src/lib/marketplace-breadcrumbs.ts` | Trail builders for UI + BreadcrumbList |

---

## Environment indexing (Phase 0A)

| Signal | Index? |
|--------|--------|
| `APP_ENV=production` and not preview | Yes |
| `VERCEL_ENV=production` | Yes |
| `NODE_ENV=production` with `APP_ENV` unset (and not preview) | Yes |
| `VERCEL_ENV=preview` / staging / development / test | **No** |

See [SEO_IMPLEMENTATION.md](./SEO_IMPLEMENTATION.md) for full policy.

---

## Page coverage

| Page | Metadata | JSON-LD |
|------|----------|---------|
| `/events/[slug]` | Dynamic + OG; **noindex** if unlisted/password | `Event` (+ `eventStatus`) + Offers + BreadcrumbList (password: no JSON-LD) |
| `/events/[slug]/checkout` | **noindex** layout | — |
| `/events`, `/c/*`, `/city/*`, weekend/free/vip | Hub title/desc/canonical | CollectionPage (`isPartOf` → WebSite `@id`) + BreadcrumbList |
| `/@{username}` Legacy | Dynamic SSR meta + OG; canonical `/u/{username}` | ProfilePage → Organization + BreadcrumbList |
| `/sponsors/[slug]` | Dynamic SSR meta | ProfilePage → Organization + BreadcrumbList |
| `/sponsorships`, `/sponsorships/hosts` | Hub metadata + CollectionPage | CollectionPage |
| `/f/[username]` | `buildFanMetadata`; unlisted noindex | ProfilePage → Person (public) + BreadcrumbList |
| `/merch/[slug]` | Meta; **noindex** if `indexable=false` | Product + Offer (when indexable) + BreadcrumbList |
| Sitewide (root layout) | — | Organization + WebSite (+ SearchAction on `/events?q=`) |
| Blog / help | Strong RSC meta + Article | Yes |
| Private workspaces / auth / checkout | Layout `noindex` + robots disallow + `X-Robots-Tag` | — |

---

## Event JSON-LD (privacy-safe)

```
Event
  name, description (scrubbed), image, startDate, endDate, eventAttendanceMode, eventStatus
  location: Place
    name: venue only if publicly revealed; else public_location_label or city
    address: PostalAddress — streetAddress ONLY if full_public
  organizer: Organization (host display name; page @id when host_slug known)
  offers: Offer[] per visible public ticket type (NGN)
```

`eventStatus`: `published`/`paused` → `EventScheduled`; `cancelled` → `EventCancelled`. No Postponed/Rescheduled in the product model. Past published events stay Scheduled (not Cancelled).

Omit hidden ticket types. Never put online meeting URLs in `location` or `description`.  
Password-protected events: **no** Event JSON-LD; generic meta description only.

Checkout Offer URLs may point at `/events/{slug}/checkout`; that route is **noindex**.

---

## Sitewide Organization / WebSite

Root layout emits one `@graph`:

- Organization `@id` `https://padeya.com/#organization`
- WebSite `@id` `https://padeya.com/#website` with `publisher` → Organization
- SearchAction → `https://padeya.com/events?q={search_term_string}` (working public search; **not** `/events/search`)

---

## Canonical URLs

| Entity | Canonical |
|--------|-----------|
| Site origin | `https://padeya.com` |
| Event | `/events/{slug}` (not hub paths; no utm/ref) |
| Legacy | `/u/{username}` (also served at `/@{username}` via rewrite) |
| Hubs | Hub path itself |
| `/events?…` filters / UTM / ref | `https://padeya.com/events` |

---

## Sitemap (`app/sitemap.ts`)

**Include:** `/`, `/events`, category/city hubs, weekend/free/vip, **listed** published events, `/hosts`, `/fans`, Host Legacy `/u/*`, public Fan Passports `/f/*` (directory-eligible), verified public Sponsors `/sponsors/*`, sponsorship marketplace, `/blog` + published posts + non-empty category/tag/author hubs, help, merch (indexable), ambassadors marketing (`/ambassadors`, `/ambassadors/events`, `/ambassadors/how-it-works`).

**Exclude:** private workspaces, drafts, `visibility` ≠ `listed`, private/unlisted/hidden passports, unverified/unlisted sponsors, non-indexable merch, `/events/search`, auth/checkout/token/query URLs.

**lastModified:** entity `updated_at` / `published_at` when present; omitted for entities without a real timestamp (never invent generation time for entities).

**Origin:** always `https://padeya.com` via `getCanonicalSiteOrigin()`.

Production robots advertise `https://padeya.com/sitemap.xml`. Non-production robots do **not** advertise a sitemap.

---

## Robots (`app/robots.ts`)

**Production:** Allow `/` with disallows for `/admin/`, `/dashboard/`, `/host/`, `/sponsor/`, `/connect/`, `/messages/`, `/staff/`, `/ambassador/`, `/api/`, auth pages, support tickets/desk, checkout patterns, `/team/invite/`, `/demo`, etc.

**Non-production:** `Disallow: /` (no sitemap line).

---

## Privacy checklist

- [x] Hidden venue → meta/JSON-LD has no street address  
- [x] Hidden online link → not in description, OG, or JSON-LD  
- [x] Unlisted/password events → **noindex** + not in sitemap  
- [x] Password events → no protected body in meta / no Event JSON-LD  
- [x] Ticket offers only for publicly visible types  
- [x] Non-production deployments → noindex  
- [x] Canonical never localhost / preview / tunnel  

---

## Search Console & production smoke (Phase 1C)

- Optional verification env: `GOOGLE_SITE_VERIFICATION`, `BING_SITE_VERIFICATION` (prefer DNS in prod).
- Analytics: first-party primary; optional GA4 via `NEXT_PUBLIC_GA_MEASUREMENT_ID` + consent on `/cookies`.
- Live smoke: `SEO_BASE_URL=https://padeya.com npm run seo:production-smoke`
- Ops checklist: [SEO_LAUNCH_CHECKLIST.md](./SEO_LAUNCH_CHECKLIST.md)

---

## Future expansion

- Split sitemap via index when URL count grows
- `taxonomy_slug_redirects` (301) when admin renames hub slugs
- EventPostponed / EventRescheduled when modeled
- Dynamic OG images
- Admin UI for location SEO fields