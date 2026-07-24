# SEO

Marketplace SEO, structured data, sitemap, and robots for Pàdéyá public surfaces.

**Related:** [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [API.md](./API.md)

---

## Principles

- Public pages get per-entity **title**, **description**, **canonical**, Open Graph, and Twitter card.
- Reuse stored `seo_title` / `seo_description` / `social_share_*` when set; else fall back to title / tagline / truncated description.
- Brand name **Pàdéyá** appears in the root title template.
- Prefer server `generateMetadata` (thin server `page.tsx` + client view) for entity pages.
- Location in meta and JSON-LD follows the same privacy path as public APIs: city / area / `public_location_label` only when address is hidden; **never** private online URLs.

---

## Helpers

| Module | Role |
|--------|------|
| `frontend/src/lib/seo/site.ts` | `siteOrigin`, `absoluteUrl`, `buildPageMetadata`, default OG |
| `frontend/src/lib/seo/event-metadata.ts` | `buildEventMetadata`, `eventJsonLd` |
| `frontend/src/lib/seo/hub-metadata.ts` | Hub + host Legacy metadata builders |
| `frontend/src/lib/seo/jsonld.tsx` | `breadcrumbJsonLd`, `JsonLdScript` |
| `frontend/src/lib/seo/sitemap-filter.ts` | `filterListedEventsForSitemap` — listed-only |
| `frontend/src/lib/marketplace-breadcrumbs.ts` | Trail builders for UI + BreadcrumbList |

---

## Page coverage

| Page | Metadata | JSON-LD |
|------|----------|---------|
| `/events/[slug]` | Dynamic + OG image (`social_share_image_url` \|\| banner) | `Event` + `Offer`s (public tickets) + `BreadcrumbList` |
| `/events`, `/c/*`, `/city/*`, weekend/free/vip | Hub title/desc/canonical | `BreadcrumbList` |
| `/events/near-me` | Placeholder meta | BreadcrumbList only |
| `/@{username}` Legacy | Host name, bio, OG media | `Organization` + BreadcrumbList |
| Vault / Memory (public) | Safe title/desc | BreadcrumbList |
| `/sponsors`, `/hosts` | Directory meta | BreadcrumbList |
| Checkout / host / admin | Minimal or noindex | — |

---

## Event JSON-LD (privacy-safe)

```
Event
  name, description (scrubbed), image, startDate, endDate, eventAttendanceMode
  location: Place
    name: venue only if publicly revealed; else public_location_label or city
    address: PostalAddress — streetAddress ONLY if full_public
  organizer: Organization (host display name)
  offers: Offer[] per visible public ticket type (NGN)
```

Omit hidden ticket types. Never put online meeting URLs in `location` or `description`.

---

## Canonical URLs

| Entity | Canonical |
|--------|-----------|
| Event | `/events/{slug}` (not hub paths) |
| Legacy | `/@{username}` |
| Hubs | Hub path itself |
| `/events?category=…` filters | Prefer matching hub when filters equal a hub; else `/events` |

---

## Sitemap (`app/sitemap.ts`)

**Include:** `/`, `/events`, category/city hubs, weekend/free/vip, **listed** published events, `/hosts`, `/sponsors`, `/sponsors/hosts`, `/blog`, **published** blog posts only.

**Exclude:** `/host/**`, `/dashboard/**`, `/admin/**`, `/support/**`, drafts, scheduled/unpublished blog posts, `visibility` ≠ `listed` (unlisted, password, etc.), private Vault items.

Listed filter: `filterListedEventsForSitemap` (visibility unset or `listed`). Public `GET /events` already omits unlisted. Blog posts via `fetchBlogPostsServer` (public API returns published only).

**Priority (pragmatic):** home/events high; event detail medium-high; blog index/posts medium; hubs medium.

---

## Blog SEO

- RSC pages: `/blog`, `/blog/[slug]`, category/tag/author hubs
- Per-post metadata + Open Graph/Twitter via `lib/seo/blog-metadata.ts`
- Article JSON-LD on post detail
- Canonical URL (custom or `/blog/{slug}`)
- Draft/scheduled/archived → public 404 + `noindex` when metadata is generated for missing posts
- Sitemap includes published posts only
- HTML body sanitized server-side before render

---

## Robots (`app/robots.ts`)

```
Allow: /
Disallow: /host/, /dashboard/, /admin/, /support/, /ambassador/, /staff/, /api/, /login, /register
Sitemap: {origin}/sitemap.xml
```

---

## Breadcrumb SEO rules

- Parents linked; current page not linked.
- Privacy-safe labels only.
- Emit `BreadcrumbList` JSON-LD alongside visible crumbs on event (and hub) pages.

---

## Privacy checklist

- [x] Hidden venue → meta/JSON-LD has no street address  
- [x] Hidden online link → not in description, OG, or JSON-LD  
- [x] Unlisted/private events → not in public list / sitemap  
- [x] Ticket offers only for publicly visible types  
- [x] Studio SEO preview shows public location label only  

---

## Future expansion

- Split sitemap via index when URL count grows.
- `taxonomy_slug_redirects` (301) when admin renames hub slugs.
- CollectionPage JSON-LD on dense hubs.
- FAQPage JSON-LD only where FAQ content actually renders.
- Host directory and sponsor hub SEO once those hubs ship.
