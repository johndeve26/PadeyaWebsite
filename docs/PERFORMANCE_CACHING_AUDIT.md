# Pàdéyá performance & caching audit

**Brand:** Pàdéyá  
**Stack:** Next.js (frontend), FastAPI (backend), PostgreSQL, Redis, optional Cloudflare/CDN  
**Goal:** Make public discovery fast without leaking private data or stale checkout/ticket state.

This document is the Phase 1 audit. Phase 2 implementation lives in `backend/app/core/cache.py`, `cache_headers.py`, `cache_invalidation.py`, public router wiring, ISR/revalidate on public pages, and DB index migration(s).

---

## 1. Current state (before Phase 2)

### 1.1 Frontend (Next.js)

| Surface | Path(s) | Caching today | Notes |
|--------|---------|---------------|-------|
| Home | `/` | None (`revalidate` unset) | Client sections fetch picks/nearby; hero is static brand |
| Events list | `/events` | None | Client marketplace; API fetches uncached at edge |
| Event detail | `/events/[slug]` | `fetch` `revalidate: 60` | Good baseline; no page-level `export const revalidate` |
| Hosts directory | `/hosts` | `fetch` `revalidate: 30` | Legacy discover API |
| Fans directory | `/fans` | Client-driven | Public passport directory |
| Sponsors | `/sponsors`, `/sponsors/hosts` | `revalidate: 30` on host list | |
| Blog | `/blog`, `/blog/[slug]`, category/tag/author | `export const revalidate = 60` + tagged fetch | Revalidate route `/api/revalidate/blog` |
| Help / KB | `/help`, articles, categories | `revalidate = 60` + tags `["help"]` | |
| FAQ | `/faq` | Static content module | Safe to ISR long |
| About / pricing / for-hosts / for-fans / legal | marketing pages | Mostly static | No `revalidate` export yet |
| Checkout | `/events/[slug]/checkout`, `/checkout/*` | Client / dynamic | **Must never CDN-cache** |
| Dashboards | `/dashboard/*`, `/host/*`, `/admin/*` | Auth client apps | **Must never CDN-cache** |
| Map / calendar / near-me | `/events/map`, `/calendar`, `/near-me` | Client fetches | Heavy; lazy below-fold OK |

**Images:** `next.config.ts` enables AVIF/WebP for local `/public` brand assets. Remote event media often goes through `/media` rewrite — ensure `next/image` where practical; avoid caching private Vault media.

**Gaps:**
- Most marketing/legal pages lack explicit ISR.
- Homepage and `/events` rely on client waterfalls instead of short ISR shells.
- No shared frontend TTL constants; blog/help already set the pattern.
- Maps/calendars not consistently deferred.

### 1.2 Backend public APIs

| API | Route | Cache today | Recommended |
|-----|-------|-------------|-------------|
| Event list | `GET /events` | None | Redis 60–120s; key includes filters |
| Pàdéyá Picks | `GET /events/padeya-picks` | None | Redis 60–180s |
| Event detail | `GET /events/{slug}` | None | Redis 60–300s; short TTL on capacity fields |
| Categories | `GET /events/categories` | None | Redis 10–60m |
| Nearby | `GET /events/nearby` | Rate-limited via Redis | Redis 60–180s; key includes lat/lng/radius/filters |
| Map | `GET /events/map` | Rate-limited via Redis | Redis 60–180s; viewport + filters |
| Calendar | `GET /events/calendar` | None | Redis 60–180s; month + filters |
| Blog public | `GET /blog/*` | None (FE ISR only) | Redis 1–24h |
| Help public | `GET /help/*` | None (FE ISR) | Redis 1–24h |
| CMS FAQ/banners/tiles | `GET /cms/faqs` etc. | None | Redis 1–24h |
| Taxonomy public | `GET /taxonomy/*` | None | Redis 10–60m |
| Sponsorship public | `GET /sponsorships/public/*` | None | Redis 60–300s |
| Host discover | `GET /legacy/discover/hosts` | None | Redis 60–300s |
| Fan directory | `GET /fans` | None | Redis 60–300s |
| Public passport | `GET /passport/public/...` / fan pages | None | Redis 60–300s |
| Public pricing | `GET /pricing/public` | FE `revalidate: 300` | Redis 5–30m |

### 1.3 Never publicly cache (no-store)

| Surface | Why |
|---------|-----|
| Auth (`/auth/*`), sessions, impersonation | Identity leakage |
| Admin (`/admin/*`, staff support desk) | Privileged data |
| Host/fan private dashboard (`/hosts/me`, `/passport/me`, `/dashboard/*`) | Per-user |
| Payments / checkout / Paystack init+verify+webhooks | Money safety |
| Orders, tickets, QR payloads, PDF, transfers | Ownership + signed QR |
| Check-in scan APIs | Door integrity |
| Messages + WS + attachments | Private fan↔host |
| Notifications / push subscriptions | Per-user |
| Support tickets | PII + case data |
| Vault private / unlock grants | Paid private content |
| Restriction / appeal / maintenance admin | Security state |
| Fee quotes tied to cart (if buyer-specific) | Prefer no-store |

**Authenticated APIs:** default `Cache-Control: no-store` unless explicitly audited as public-safe.

### 1.4 Redis today vs gaps

| Use | Module | Behavior if Redis down |
|-----|--------|------------------------|
| Rate limits (nearby/map) | `events/rate_limit.py` | Falls through / limits fail open carefully |
| Messaging WS fan-out | `messaging/ws_bus.py` | In-memory single-worker fallback |
| Presence | messaging presence | Degraded |
| Health | `redis_health()` | Reports unavailable |
| **Response cache** | **Missing** | **Gap — Phase 2 adds namespaced `padeya:cache:*`** |

**Rule:** Cache keys use prefix `padeya:cache:` so they never collide with pub/sub channels or rate-limit counters. Cache layer must tolerate Redis down (compute fresh, log miss).

### 1.5 Database / query performance

**Already indexed (high value):**
- `events.slug` (unique), `status`, `host_id`, `category_id`, `primary_category_id`, `location_id`
- Composites: `primary_category + start`, `location + start`
- Orders/payments/tickets: reference, status, foreign keys widely indexed
- Blog: slug + status; help/KB similarly
- Host/fan slugs on profiles/passport

**Gaps / recommendations:**
- Composite `events(status, start_datetime)` for published discovery sorts
- Composite `blog_posts(status, published_at)` for public list
- Ensure map/nearby queries use lat/lng + status filters efficiently (existing geo path)
- Avoid N+1: public list serializers already load ticket_types; keep compact DTOs for map (`MapEventCompact`)
- Paginate map/nearby (already limited); debounce FE search/map pans

### 1.6 HTTP / CDN / Cloudflare

- No Cloudflare cache rules checked into repo yet.
- Next rewrites `/api/*` and `/media/*` to FastAPI — **CDN must not cache proxied private APIs**.
- Messaging sets `Cache-Control: private, max-age=300` on one attachment-style response — keep private, never public shared cache.

**Recommended Cloudflare bypass (Cache Everything / edge cache OFF):**
- `/admin/*`, `/dashboard/*`, `/host/*`, `/checkout/*`, `/support/*`, `/messages/*`
- `/api/v1/auth/*`, `/api/v1/admin/*`, `/api/v1/payments/*`, `/api/v1/orders*`, `/api/v1/tickets*`, `/api/v1/messages*`, `/api/v1/notifications*`, `/api/v1/support*`, `/api/v1/passport/me*`, `/api/v1/hosts/me*`, `/api/v1/checkins*`, `/api/v1/vault*` (non-public), WebSocket paths

**Safe to edge-cache (short TTL + SWR):** public marketing HTML from Next ISR, public GET allowlist APIs with Redis + `Cache-Control: public, max-age=…, stale-while-revalidate=…`.

---

## 2. TTL policy (Phase 2)

| Content class | TTL | SWR (HTTP) |
|---------------|-----|------------|
| Featured / Picks | 60–180s | +60–120s |
| Event lists | 60–120s | +60s |
| Event detail | 60–300s | +60s |
| Calendar / map / nearby | 60–180s | +30–60s |
| Host/fan public profiles & directories | 60–300s | +60s |
| Taxonomy / categories / tags | 10–60 min | +5 min |
| Blog / help / FAQ / legal / CMS static | 1–24h | +1h |
| Ticket availability / capacity-sensitive | Prefer ≤60s or bypass field freshness | — |

Keys **must** include filter/query params (and rounded or exact geo where used).

---

## 3. Invalidation matrix

| Mutation | Invalidate |
|----------|------------|
| Event CUD / publish / pause / cancel / feature / pick / ticket types / capacity | Event detail key, list patterns, picks, calendar, map, nearby patterns, host public page |
| Blog / help / FAQ / legal / CMS publish | Article key + indexes; FE `revalidateTag` / `revalidatePath` |
| Host/fan public profile update | Profile + directory keys |
| Ticket purchase (webhook confirmed) | Event detail + list availability (short TTL also bounds staleness) |
| Taxonomy CUD | Taxonomy namespace |

Prefer **archive** over hard delete for content; cache invalidation still runs on archive/restore.

---

## 4. Privacy & correctness risks

1. **Cross-user cache bleed** — never key private responses without user id; default private APIs to no-store and skip Redis body cache.
2. **Sold-out staleness** — short TTL + invalidate on paid webhook; never cache QR or ownership.
3. **Location privacy** — nearby/map already use approximate coords for restricted events; cache only serialized public payloads.
4. **Auth on public pages** — CDN must vary or bypass when authenticated HTML embeds private chrome. The browser sends JWTs via `Authorization` headers (tokens in localStorage), not session cookies; prefer cache anonymous HTML only.
5. **Redis shared with messaging** — namespace + no `FLUSHDB` from cache utilities.
6. **Paystack / fees** — never trust FE cache for payment success; webhooks remain source of truth.

---

## 5. Monitoring

- Dev / debug: cache hit/miss logs (`padeya.cache` logger).
- Optional lightweight timing on slow public list builders.
- Health already exposes Redis reachability — keep.

---

## 6. Implementation checklist (Phase 2)

- [x] Audit doc (this file)
- [x] `app/core/cache.py` — get/set/delete/pattern, key builder, TTLs, Redis-down fallback
- [x] `app/core/cache_headers.py` — public Cache-Control vs no-store middleware
- [x] `app/core/cache_invalidation.py` — domain helpers
- [x] Wire public events/blog/help/cms/taxonomy/sponsorships/passport/legacy
- [x] Invalidate on CUD paths (events, tickets purchase webhook, blog, help, CMS FAQ, passport)
- [x] DB composite indexes migration (`20260721_0115`)
- [x] Frontend ISR on public marketing pages + shared TTL helpers
- [x] Tests: `tests/test_public_cache.py`
- [x] Document Cloudflare bypass in this file (section 1.6)

---

## 7. Remaining limitations / follow-ups

Confirmed by Phase 1 deep audit ([Audit caching surfaces](86e786db-d3aa-4204-a7d8-535b3230b996)):

| Gap | Status |
|-----|--------|
| Redis response cache + HTTP Cache-Control | **Done** (Phase 2) |
| ISR on marketing / blog / help / events shells | **Done** |
| Lazy code-split map + calendar in marketplace | **Done** (`next/dynamic` in `EventsResults`) |
| Event detail duplicate fetch + full `/events` related dump | **Done** (pass `initialEvent`; category-scoped related) |
| Fan passport HTML `cache: "no-store"` | **Intentional** — privacy toggles / hide must not ISR-serve stale 404s; API still Redis-cached short TTL |
| `list_published_events` still loads published set then filters in Python | **Open** — Redis bounds cost; SQL push-down + pagination is next perf phase |
| No lat/lng DB indexes / PostGIS | **Open** — nearby/map still O(n) over published set (rate-limited) |
| Listing cards use `<img>` not `next/image` | **Open** — needs `remotePatterns` for `/media` hosts |
| Home discovery rails still client-fetched | **Done** — RSC `loadHomepagePublicData` + ISR; nearby is client-enhanced after consent |
| Declined geolocation UX | **Done** — session sticky decline; popular/default fallbacks; no re-prompt |
| Nearby cache exact lat/lng | **Done** — ~0.05° grid buckets; response echoes bucketed coords only |
| Cloudflare rules not in-repo | **Open** — ops applies bypass list from §1.6 |

### Homepage + `/events` SSR notes

- **Default public experience is SSR/ISR first.** Geolocation never blocks first paint.
- **Nearby / Near me** stays client-side after browser consent. URL `lat`/`lng`/`near=1` does **not** SSR nearby with precise GPS (privacy + cache safety). SSR still seeds the unfiltered public list.
- **Declined geo:** keep cached featured/default-city/weekend rails; friendly copy; manual city; no blank section; no repeated prompts in the same session (`sessionStorage`).
- **Checkout:** always re-fetches public event + ticket types client-side before pay — never treat cached list/detail as final availability truth. Private APIs remain `Cache-Control: no-store`.

### Nearby Redis key policy

Keys use `bucket_lat_lng` (~0.05°, ≈5–6 km). Ranking uses request coords inside the producer; Redis never stores raw browser GPS. TTL = `TTL.availability` (60s). Invalidation covers `events:nearby*`, `events:list*`, `events:homepage*`, picks, map, calendar on event CUD / ticket purchase.

---

## 8. Out of scope (this phase)

- Rebuilding marketing site aesthetics
- Caching private Vault, Legacy studio drafts, Fan Connect suggestions (user-specific — separate audit)
- Changing fee copy or inventing pricing claims
- Hard-deleting content for cache reasons
- Full SQL rewrite of discovery queries / PostGIS
