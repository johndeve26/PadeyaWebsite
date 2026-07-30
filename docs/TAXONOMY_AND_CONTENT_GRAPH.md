# Pàdéyá taxonomy and content graph

Authoritative contract for marketplace taxonomy, discovery routes, content relationships, breadcrumbs, SEO, sitemap, admin console, Studio/host integration, and demo seed.

**Companions:** [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [API.md](./API.md) · [DATABASE.md](./DATABASE.md) · [SEO.md](./SEO.md) · [CRUD_MATRIX.md](./CRUD_MATRIX.md) · [CRUD_PATTERN.md](./CRUD_PATTERN.md) · [ROADMAP.md](./ROADMAP.md)

**Brand:** Pàdéyá  
**Invariant:** Never expose hidden/private venue street addresses or private online links in hubs, breadcrumbs, metadata, JSON-LD, or related rails. Prefer city / area / `public_location_label` when redacted ([`backend/app/events/privacy.py`](../backend/app/events/privacy.py)).

---

## 1. Taxonomy model

### Controlled vocabulary (Wave 1 tables)

| Table | Role |
|-------|------|
| `taxonomy_categories` | Top-level browse categories (`nightlife`, `comedy`, …) |
| `taxonomy_subcategories` | Child of category (`category_id` + slug unique) |
| `taxonomy_tags` | Multi-select discovery tags |
| `taxonomy_vibes` | Mood / energy labels |
| `taxonomy_audience_types` | Audience segments (e.g. `adults-18`, `students`) |
| `host_types` | Host niche types (e.g. `dj-artist`, `comedy-collective`) |
| `venue_types` | Venue kind catalog (e.g. `club`, `rooftop`) |
| `locations` | Place tree: `kind` ∈ `country` \| `state` \| `city` \| `area`; `parent_id`, `slug` |

Shared vocab fields: `name`, `slug`, `description`, `sort_order`, `featured`, `seo_title`, `seo_description`, `is_active`, `archived_at` (locations use `is_active` without `archived_at`).

### Location hierarchy (seed)

Parent map: `state`→`country`, `city`→`state`, `area`→`city` (`LOCATION_PARENT_KIND` in `backend/app/taxonomy/constants.py`).

State and city may share a slug (e.g. `lagos`); always resolve with **`kind` + `slug`**.

| Kind | Seed rows (`DEFAULT_LOCATIONS`) |
|------|----------------------------------|
| country | `nigeria` (NG) |
| state | `lagos` (LA), `oyo` (OY), `ondo` (ON), `fct` (FC) — parent `nigeria` |
| city | `lagos`→Lagos state, `ibadan`→Oyo, `akure`→Ondo, `abuja`→FCT |
| area | Under Lagos city: `lekki`, `victoria-island`, `ikeja`, `yaba`, `mainland` (Lagos Mainland) |

Legacy renames: `lagos-state`→`lagos`, `oyo-state`→`oyo`.  
Popular shortcuts: Lagos / Ibadan / Abuja / Akure cities + VI / Lekki / Ikeja / Yaba / Lagos Mainland areas.

Demo events assign a leaf `location_id` (area or city) so country/state/city/area hubs resolve via descendants.

### Link tables

| Table | Role |
|-------|------|
| `event_taxonomy_links` | Event ↔ category/tag/vibe/audience (`link_type`, `taxonomy_id`, `taxonomy_slug`) |
| `host_taxonomy_links` | Host ↔ host_type/category/audience |
| `host_location_links` | Host primary city + service areas (`is_primary`) |

Future (not shipped): `vault_taxonomy_links`, `memory_taxonomy_links`, `sponsorship_taxonomy_links`, first-class `venues` table.

### Dual-write (current)

| Canonical / new | Legacy / flat (still read) |
|-----------------|----------------------------|
| `events.primary_category_id` → `taxonomy_categories` | `events.category_id` → `event_categories` |
| `events.location_id` → `locations` | `events.city`, `events.state` free text |
| Tag/vibe links | `events.hashtags`, `events.vibe` |
| Host taxonomy links | Host profile city + `social_links.niche_positioning` |

**Location filter behavior (today)**

| Surface | Prefers | Fallback |
|---------|---------|----------|
| Hub routes + cascade (`location_kind` + `location_slug`) | `events.location_id` ∈ node + descendants | Free-text `city`/`state` match when `location_id` is null |
| Legacy facet `city=` on `GET /events` | Slugified `events.city` | — |
| Studio save | Sets `location_id` and dual-writes `city`/`state`/`public_location_label` from taxonomy | Hosts may still edit flat city text |
| Faceted “City” select on non-cascade hubs | Free-text `events.city` from listing payload | Hidden when `LocationFilterBar` cascade is active |
| Sitemap city URLs | Taxonomy `locations` hubs + slugified `events.city` from listed events | — |

Both fields are kept for compatibility. **Wave 6 cutover (future):** stop treating flat `events.city` as a source of truth for discovery facets/sitemap; require `location_id` for listed geo events; free-text becomes display-only fallback.

Public category discovery still filters on legacy `event_categories.slug` until taxonomy category cutover.
### Lifecycle

- Prefer **archive / deactivate** over hard delete.
- `DELETE /taxonomy/admin/{resource}/{id}` → **405** (“use archive”).
- Soft archive must not break published events that still reference the term.
- Admin changes are audit-logged (`taxonomy.*` actions).
- Usage counts on categories (events via primary, legacy slug, or links).

---

## 2. Relationship model (content graph)

Strong FKs remain source of truth (`events.host_id`, `category_id`, memory↔event).

### `content_relationships`

```
content_relationships(
  id, source_type, source_id, target_type, target_id,
  relationship_type, weight, reason, created_by,
  created_at, updated_at, expires_at
)
UNIQUE(source_type, source_id, target_type, target_id, relationship_type)
```

### Key `relationship_type` values

`hosted_by`, `primary_category`, `located_in`, `related_event`, `same_category`, `same_city`, `same_host`, `similar_vibe`, `upcoming_event`, `past_event`, `memory_of_event`, `vault_from_host`, `vault_related_event`, `sponsor_slot_for_host`, `category_top_event`, `city_top_host`, `trending_in_city`, `recommended_next`.

### Page → related rails

| Page | Rails |
|------|--------|
| Event detail | Same host → same category → same city → similar vibe; Legacy CTA; omit empty |
| Legacy | Upcoming / past / memories / vault / sponsor slots |
| Vault item | More from host; related event (when linked) |
| Sponsors | Similar sponsor-ready; same city (soft) |
| Host/Admin event ops | `EventOpsNav` (ops links, not graph) |

**Wave 0–1:** live queries (`groupRelatedEvents` on FE; list filters on BE).  
**Wave 5:** graph job fills `content_relationships` with live-query fallback.  
**Rule:** omit empty rails — never render empty shells.

---

## 3. Route hierarchy

### Canonical entities (stable)

```
/events/[slug]
/@[username]              → /u/[username]
/@[username]/vault[/item]
/@[username]/memories/[eventSlug]
/sponsors · /sponsors/hosts
```

### Discovery hubs (shipped)

```
/events
/events/location
/events/country/[countrySlug]
/events/state/[stateSlug]
/events/state/[stateSlug]/[categorySlug]
/events/c/[categorySlug]
/events/city/[citySlug]
/events/city/[citySlug]/[categorySlug]
/events/area/[areaSlug]
/events/this-weekend · /free · /vip · /near-me (placeholder)
/hosts
```

### Deferred hubs (future expansion)

`/events/tag/[tagSlug]`, `/events/vibe/[vibeSlug]`, subcategory hubs, `/hosts/c/*`, `/hosts/type/*`, sponsor city/category hubs.

**Reserved path segments** (must not collide with event slugs): `location`, `country`, `state`, `area`, `c`, `city`, `tag`, `vibe`, `free`, `vip`, `this-weekend`, `near-me`.

Hub routes lock hierarchy facets (`category`, `city`, `weekend`, `paid`) as non-removable chips. Shareable refinements sync to the URL query (`q`, `category`, `city`, `location_kind`, `location_slug`, `paid`, `weekend`, `event_format`, `secret_location`, `sort`) via `EventDiscoveryView`.

`GET /api/v1/events` with `location_kind` + `location_slug` includes events whose `location_id` is the node or any descendant (e.g. Lekki area event appears under Lagos city / Lagos state / Nigeria).

---

## 3b. Featured Placement Slots / Pàdéyá Picks

Orthogonal to `events.featured`. Public surface label: **Pàdéyá Picks**. Admin surface: **Featured Placement Slots**.

| Concept | Values |
|---------|--------|
| Table | `featured_placements` |
| Slots | `slot_number` **1** = Primary Spotlight, **2** = Secondary Spotlight |
| `placement_type` | `homepage`, `events_page`, `country_page`, `state_page`, `city_page`, `area_page`, `category_page`, `city_category_page` |
| `context_type` (targeting) | `global`, `country`, `state`, `city`, `area`, `category`, `city_category` |
| Status | `draft` \| `active` \| `scheduled` \| `expired` \| `archived` |
| Public live | `active` + `scheduled` within `starts_at`/`ends_at`; event must be `published` + visibility `listed` \| `approval_required` |

**Rules**

- Same event cannot occupy both slots under one `placement_key` (`409`).
- Empty slots stay `draft`; activating requires a published event.
- Expired / not-yet-started scheduled slots are omitted from public picks.
- Legacy `context` aliases: `global_homepage`→`homepage`, `events`→`events_page`, plus bare `country`/`state`/`city`/`area`/`category`/`city_category`.
- FE fallback: `resolvePadeyaPicks(adminPicks, pool)` fills remaining slots from trending when admin returns fewer than 2 (section hides when empty).

**Public API:** `GET /api/v1/events/padeya-picks?context=&location_kind=&location_slug=&category=`  
**Admin API:** `/api/v1/admin/featured-placements/*` (see [API.md](./API.md)).  
**Admin UI:** `/admin/featured-placements`, `/new`, `/[id]/edit` (`id` = Primary slot UUID).

---

## 4. Breadcrumb rules

- Computed only (no `content_breadcrumbs` table).
- Parents are linked; **current page is not linked**.
- Mobile: truncate middle segments; keep Home + current.
- Labels must be privacy-safe (city / area / public label — never redacted street).

### Examples

| Surface | Trail |
|---------|--------|
| Event | Home → Events → {City} → {Category} → {Title} |
| Category hub | Home → Events → {Category} |
| Country hub | Home → Events → Nigeria |
| City hub | Home → Events → Nigeria → Lagos |
| Area hub | Home → Events → Nigeria → Lagos → Lekki |
| City × category | Home → Events → Lagos → Nightlife |
| Legacy | Home → Hosts → {Display name} |
| Vault item | Home → Hosts → {Host} → Vault → {Item} |
| Host workspace | Host → Events → {Title} → Tickets (ops) |

**Helpers:** `frontend/src/lib/marketplace-breadcrumbs.ts`, `MarketplaceBreadcrumbs`, JSON-LD `BreadcrumbList` (`lib/seo/jsonld.tsx`).

---

## 5. SEO rules

Full detail: [SEO.md](./SEO.md).

| Rule | Detail |
|------|--------|
| Metadata | Per public page: title, description, canonical, OG, Twitter |
| Event JSON-LD | `Event` + public `Offer`s + `BreadcrumbList` |
| Location in meta/JSON-LD | City / area / `public_location_label` when address hidden; **never** street or private online URL |
| Canonical | Event → `/events/{slug}`; Legacy → `/@{username}`; hubs → hub path |
| Sitemap | Listed published events + hubs; exclude unlisted / dashboards / admin |
| Robots | Disallow `/host/`, `/admin/`, `/dashboard/`, `/api/`, auth pages |

Studio SEO preview must show the **public** location label only.

---

## 6. Privacy rules

### Location visibility modes (`events.location_visibility`)

Access levels on serialize: `public` (anonymous) · `buyer` (paid ticket `active`/`checked_in`) · `host` · `admin`. Host/admin always see full address and online URL.

| Mode | Public shows | Full address / venue reveal |
|------|--------------|-----------------------------|
| `full_public` | Venue name, address, city | Always |
| `area_only` | Area / city / state / public label; **never** street | Not on public; messaging says after purchase (buyer still gated by product rules — street stays private unless a future reveal path opens it) |
| `hidden_until_payment` | `public_location_label` or secret copy | **Buyer always** after paid ticket |
| `hidden_until_24h_before` | Same | Public when now ≥ start−24h; buyer may also unlock via `reveal_timing` |
| `hidden_until_manual_approval` | Same | Intended: buyer + manual approval; timing gate `manual_approval` is not a positive unlock yet — treat as secret until ops approval is shipped |
| `online_only` | “Online Event”; no street | Online URL per `online_url_reveal_rule` (default `after_payment` for buyers) |

Related fields: `reveal_timing`, `reveal_note`, `public_location_label`, `online_event_url`, `online_url_reveal_rule`.

**Serializer behavior when address not revealed:** `address=null`, `location_address_revealed=false`, privacy message set, venue lat/lng/notes scrubbed, street fragments removed from SEO/social/hashtags/keywords on **public** access. Taxonomy `location_id` remains for hubs — street never lives on the location node.

| Must | Enforcement |
|------|-------------|
| No redacted street in hubs, crumbs, meta, JSON-LD, related cards, Pàdéyá Picks | `privacy.py` + public serializers; FE `lib/event-privacy.ts` + `lib/seo/event-metadata.ts` |
| No private online meeting URLs in metadata | Same |
| Unlisted / password / non-listed visibility out of public list + sitemap | `GET /events` + `filterListedEventsForSitemap` |
| Secret / area-only location never leaks venue name+street on public surfaces | Public event payload |
| Ticket-holder Vault suggestions respect access control | Vault module |

Tests: `backend/tests/test_taxonomy.py` (hidden venue), `test_event_location_privacy.py`, `test_event_studio_lifecycle.py` (buyer reveal + SEO scrub), `test_placements.py` (picks privacy).

---

## 7. Search / filter contract

URL query params are source of truth:

```
q, category, city, location_kind, location_slug, weekend, paid, event_format, secret_location, sort
```

Shipped on `GET /api/v1/events` and FE `fetchPublicEvents` / `EventDiscoveryView` / `LocationFilterBar`.  
`location_kind` + `location_slug` filter by taxonomy tree (node + descendants).  
Hide subcategory / vibe-slug / audience facets until hubs exist.

**Sorts:** `soonest`, `newest`, `featured`, soft `trending`, `price_asc` / `price_desc`.

---

## 8. Admin management

| Route | Resource |
|-------|----------|
| `/admin/taxonomy` | Overview |
| `/admin/taxonomy/categories` | Categories (+ usage, nested subcategories) |
| `/admin/taxonomy/tags` | Tags (archive/restore) |
| `/admin/taxonomy/locations` | Location tree (`kind` + `parent_id`) |
| `/admin/taxonomy/host-types` | Host types (archive/restore) |
| `/admin/taxonomy/venue-types` | Venue types (archive/restore) |
| `/admin/featured-placements` | Featured Placement Slots list |
| `/admin/featured-placements/new` | Create Primary+Secondary set |
| `/admin/featured-placements/[id]/edit` | Edit set (`id` = Primary slot id) |
| `/admin/events/picks` | Listing-centric Pàdéyá Picks (homepage / events page) |
| `/admin/events/featured` | Redirect → featured-placements |

**Taxonomy API:** `/api/v1/taxonomy/admin/*` (permission: `admin.full_access` or `events.approve`).  
**Placement API:** `/api/v1/admin/featured-placements/*` (same permission). Support cannot edit taxonomy or placements.

### Admin placement workflow

1. **From listings (recommended for homepage/events page):** `/admin/events/picks` or the **Pàdéyá Pick** action on `/admin/events` / event review — assigns Primary/Secondary via `featured_placements`.
2. **Full context editor:** `/admin/featured-placements` for city/category/hub surfaces.
3. Choose `placement_type` / context (homepage, events page, country/state/city, category, city×category).
4. Select location and/or category when required.
5. Assign Primary (slot 1) and optional Secondary (slot 2) published events.
6. Optional title/subtitle/badge + `starts_at`/`ends_at`.
7. Save set (`PUT …/sets`) or per-slot (`PUT …/{slot_number}`); activate / draft / archive via `POST …/sets/{set_id}/status`.
8. Preview uses public Pàdéyá Picks layout (`PlacementPreview`).

Public read: `/api/v1/taxonomy/categories`, `/tags`, `/vibes`, `/host-types`, `/audience-types`, `/locations?kind=`, `/locations/{kind}/{slug}`.

---

## 9. Studio + host profile

**Event Studio (Location & Privacy):** taxonomy cascade `country → state → city → area` (`location_id`), `venue_name`, `venue_type` (slug from `/taxonomy/venue-types`), `public_location_label`, full private address (`address`), `location_visibility`, `reveal_timing`, `reveal_note`, `online_event_url`, `online_url_reveal_rule`. Host/admin always see private address; public cards/SEO never get hidden street addresses; buyers see address/URL only when reveal rules allow.  
**Event Studio (Basics):** primary category (required for listed submit / checklist), vibe/hashtags, “Apply host defaults”, SEO preview.  
**Event Studio (other steps):** schedule + agenda upsert, ticket-type lifecycle (deactivate vs delete), media DELETE, people lineup, checkout questions (archive when answered), policies, SEO scrub preview, publish checklist (`preview_checked` in sessionStorage). Full field map: [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [API.md](./API.md).  
**Host settings:** host types, categories, audience, primary city, service areas, niche positioning via `PATCH /hosts/me`.

---

## 10. Demo seed niches

| Host | Niche |
|------|--------|
| djmaze | nightlife / music |
| lagoscomedyhub | comedy / open mic |
| techconnectafrica | tech / founders |
| praiseexperience | gospel / worship |
| mainlandvibes | lifestyle / campus / parties |

Modules: `backend/app/taxonomy/demo_seed.py` (`apply_demo_taxonomy`), `backend/app/placements/demo_seed.py` (homepage / Lagos / Nightlife / Tech placements).

---

## 11. Component library

Compose existing `Breadcrumb`, `EventCard`, `HostCard`, `FilterBar` — do not invent a second design system.

Public hub UI is a **sectioned marketplace discovery** flow (not a flat filter page): breadcrumbs → full-bleed hub hero → taxonomy browse → intent collections → featured spotlight → sticky faceted refine → results → adjacent hubs/hosts. Shared eyebrow language: Browse · Collections · Spotlight · Refine.

| Area | Path |
|------|------|
| Discovery chrome | `components/discovery/*` (`LocationFilterBar`, `LocationLandingHero`, `LocationStats`, `RelatedLocations`, `PadeyaPicksSection`, `FeaturedPlacementCard`, browse/collections/adjacent) |
| Taxonomy cards/nav | `components/taxonomy/*` (editorial `CategoryNav` / `CityNav`, media `TaxonomyEventCard`) |
| Related rails | `components/related/*` |
| Admin vocab | `components/admin/taxonomy/*` |
| Admin placements | `AdminPlacementForm`, `PlacementPreview` |
| Studio | `TaxonomyFields`, `LocationTaxonomyFields`, `SeoPreviewCard` |
| Host | `HostTaxonomyFields` |

Helpers: `lib/marketplace-breadcrumbs.ts`, `lib/discovery/*` (incl. `padeya-picks.ts`, `category-stories.ts`), `lib/seo/*`, `lib/event-privacy.ts`.

**Smoke:** `npm run test:taxonomy`, `npm run test:discovery`.  
**API tests:** `backend/tests/test_taxonomy.py`, `test_placements.py`.

---

## 12. Analytics (location & placements)

Client discovery signals (see [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md)):

| Action | When |
|--------|------|
| `location_filter_used` | Cascade / popular chip in `LocationFilterBar` |
| `country_page_view` / `state_page_view` / `city_page_view` / `area_page_view` | Location landing mount |
| `padeya_pick_impression` / `padeya_pick_click` | Pàdéyá Picks cards |
| `featured_placement_impression` / `featured_placement_click` | Same cards when pick came from admin placement (not fallback) |

Metadata: `country`, `state`, `city`, `area`, `category`, `placement_context`, `slot_number`, `event_id`.

---

## 13. Migration waves

| Wave | Status | Scope |
|------|--------|--------|
| 0 | Shipped | Crumbs, hubs, filters, rails, SEO/sitemap on current category/city |
| 1 | Shipped | Vocab/location/link tables + admin + migration `20260717_0023` |
| 1b | Shipped | Rich demo taxonomy seed + Nigeria hierarchy |
| 1c | Shipped | Featured placements (`0024`–`0027`, incl. `area_page`), location privacy modes, location analytics |
| 2–3 | Shipped (MVP) | Studio discoverability + host profile taxonomy + location privacy / publish checklist |
| 4 | Future | Tag/vibe/subcategory/host-type hubs |
| 5 | Future | Graph job swaps related rails |
| 6 | Future | Cutover — stop JSON hashtags / flat city as source of truth; first-class venues |

---

## 14. Future expansion notes

- First-class `venues` (`public_label`, `address_private`, `location_id`, `venue_type_id`) and `events.venue_id`.
- Vault / Memory / Sponsorship taxonomy link tables.
- Admin UX: tree editor for locations, drag sort, vibes/audience admin pages, slug redirect map on rename.
- Public host directory facets (category, host type, city, sponsor-ready).
- Graph scoring job + editorial overrides (`recommended_next`, `trending_in_city`).
- Sitemap index split when URL count grows.
- Dedupe near-duplicate legacy categories (`arts-culture` / `art-culture`) via
  merge into canonical `arts-culture` (Arts & Culture); redirect old URLs.
- Wave 6 location cutover (see Dual-write): drop free-text `city` as discovery source of truth.