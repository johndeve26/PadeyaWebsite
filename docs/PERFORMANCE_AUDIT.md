# Pàdéyá Performance & Reliability Audit

**Brand spelling:** Pàdéyá  
**Audit type:** Read-only / diagnostic (no production mutations, no load testing)  
**Production:** https://padeya.com  
**API:** https://padeyawebsite.onrender.com  
**Audit window:** 2026-07-25 (UTC)  
**Companion artifacts:**
- `docs/performance-audit-timings.json` (3-sample fetch timings)
- `docs/performance-audit-curl-phases.json` (DNS/TLS/TTFB phases)
- `frontend/scripts/performance-production-audit.mjs` (safe GET-only re-run script)

### Implementation status

| Phase | Status | Doc |
|-------|--------|-----|
| **Phase 0** — reliability & observability | **Implemented** (workspace; deploy separately) | [PERFORMANCE_IMPLEMENTATION.md](./PERFORMANCE_IMPLEMENTATION.md) |
| **Phase 1** — API/query latency | **Implemented in workspace** — **DEPLOYED MEASUREMENT pending** | [PERFORMANCE_IMPLEMENTATION.md](./PERFORMANCE_IMPLEMENTATION.md#phase-1--apiquery-latency-implemented-in-workspace) |

Phase 0 delivered: request timing + IDs + Server-Timing, `/ready`, frontend/Redis timeouts, maintenance/RBAC instrumentation, safe 500 handler, regression tests.

Phase 1 delivered (code): SQL marketplace events list + lean list DTO, sponsor/Legacy public query reductions, maintenance decision cache, request-scoped RBAC memo, host-workspaces single-flight. **No speculative indexes. Production before/after not claimed until post-deploy audit.** Baseline: [`performance-phase1-baseline.json`](./performance-phase1-baseline.json).

**Evidence labels used throughout:**
- **MEASURED** — observed with low-volume production requests in this audit
- **OBSERVED IN LOGS** — from prior production incident investigation (not re-logged here)
- **CODE-LEVEL RISK** — supported by source inspection
- **HYPOTHESIS** — plausible but not proven

---

## Executive Summary

Pàdéyá is up and serving public HTML/API with **no 5xx in this audit’s samples**. Warm homepage and login are relatively fast via Vercel cache (**HIT/STALE**). Marketplace and profile routes that miss CDN and call Render/Neon are commonly **~0.7–1.7 s TTFB**.

The dominant latency story is **not classic Render Free sleep** in this window (health stayed ~0.3–0.5 s). It is a stack of:

1. **Cross-region path** (Africa edge `cpt1` → Vercel `iad1` → Render → Neon `us-east-2` / Upstash) — **MEASURED** headers + **CODE-LEVEL** region hints  
2. **Heavy / unbounded public events query** with large JSON (~151 KB uncompressed for 12 events) — **MEASURED** + **CODE-LEVEL RISK**  
3. **Per-request maintenance middleware DB work** on the API — **CODE-LEVEL RISK** (prior **OBSERVED** Neon deadlock incident mitigated)  
4. **SSR pages that bypass CDN** (`x-vercel-cache: MISS`, some `private, no-store`) and **fan passport `no-store`** — **MEASURED** + **CODE-LEVEL RISK**  
5. **Duplicate metadata + page loaders** without `react.cache` — **CODE-LEVEL RISK**

Reliability recovered after the maintenance-section seed/deadlock fix, but observability gaps remain (no request-timing middleware, health without DB ping).

---

## Overall Score

| Dimension | Score | Notes |
|-----------|------:|-------|
| **Performance** | **61 / 100** | Warm shell OK; many public/API paths 0.8–1.7 s; payload & query shape risks |
| **Reliability** | **68 / 100** | No 5xx this window; recent P0 DB contention fixed; auth poll storm mitigated; weak health/telemetry |

---

## Production Architecture

```
Browser
  ↓
Vercel — Next.js frontend (padeya.com)
  ↓  (server fetch / client fetch)
Render — FastAPI backend (padeyawebsite.onrender.com)
  ↓
Neon — PostgreSQL (region hint: us-east-2)
  ↓
Upstash — Redis (host pattern *.upstash.io)
```

| Layer | Role |
|-------|------|
| FRONTEND / VERCEL | App Router RSC/ISR, CDN, edge |
| BACKEND / RENDER | FastAPI API, auth, payments webhooks |
| DATABASE / NEON | Primary datastore |
| REDIS / UPSTASH | Cache, rate limits, WS fanout (fail-open) |
| NETWORK | TLS + multi-hop geo |
| THIRD PARTY | Paystack, Google Maps/Places, GA4 (gated), SMTP |

---

## Production Timing Baseline

### Method

- Tooling: `frontend/scripts/performance-production-audit.mjs` (3 samples/route) + curl phase timing (3 samples)
- Client vantage: auditor network (Africa-adjacent; Vercel id shows `cpt1::iad1`)
- Safe GETs only; no auth mutations; not a load test
- Compression: with `Accept-Encoding: br`, HTML/JSON compressed (**MEASURED**)

### Frontend routes (median total response time, n=3) — MEASURED

| Route | Median | First | Warm median | Status | Bytes (decoded) | x-vercel-cache |
|-------|-------:|------:|------------:|--------|----------------:|----------------|
| `/` | 383 ms | 974 ms | 337 ms | 200 | ~471 KB | STALE |
| `/events` | 1175 ms | 1175 ms | 1270 ms | 200 | ~268 KB | MISS |
| `/events/demo-afrobeats-night-live` | 762 ms | 762 ms | 743 ms | 200 | ~126 KB | MISS |
| `/hosts` | 704 ms | 704 ms | 791 ms | 200 | ~51 KB | STALE |
| `/u/mainlandvibes` | 838 ms | 1245 ms | 687 ms | 200 | ~100 KB | MISS |
| `/fans` | 311 ms | — | — | 200 | ~55 KB | (client listing shell) |
| `/f/pizzlecole` | 1221 ms | 1340 ms | 1123 ms | 200 | ~58 KB | MISS |
| `/sponsorships` | 750 ms | 755 ms | 673 ms | 200 | ~77 KB | MISS |
| `/sponsors/korawave-pay` | 758 ms | 765 ms | 660 ms | 200 | ~90 KB | MISS |
| `/merch` | 309 ms | — | — | 200 | ~53 KB | (client listing shell) |
| `/merch/mainland-vibes-logo-tee` | 621 ms | 733 ms | 663 ms | 200 | ~70 KB | MISS |
| `/blog` | 333 ms | — | — | 200 | ~80 KB | — |
| `/help` | 736 ms | 788 ms | 660 ms | 200 | ~172 KB | MISS |
| `/login` | 260 ms | — | — | 200 | ~43 KB | HIT |
| `/register` | 397 ms | — | — | 200 | ~43 KB | — |
| `/dashboard` | 383 ms | — | — | 200 | ~26 KB | (shell; data client-side) |
| `/host` | 390 ms | — | — | 200 | ~26 KB | shell |
| `/sponsor` | 347 ms | — | — | 200 | ~45 KB | shell |

**Additional samples (n=2):**  
- `/blog/sponsorships-and-ambassadors-that-convert` — TTFB ~1.27–1.31 s, 200  
- `/help/articles/how-to-block-or-report-someone` — TTFB ~0.73–1.36 s, 200  

### Curl phases (median seconds, n=3) — MEASURED

DNS is negligible (~3–5 ms). TLS handshake ~170–250 ms. TTFB dominates.

| Target | DNS | TLS (appconnect) | TTFB | Total | Cache |
|--------|----:|-----------------:|-----:|------:|-------|
| FE `/` | 0.003 | 0.172 | **0.465** | 0.779 | HIT |
| FE `/events` | 0.004 | 0.183 | **1.351** | 1.740 | MISS |
| FE `/events/{slug}` | 0.004 | 0.245 | **0.892** | 1.170 | MISS |
| FE `/u/mainlandvibes` | 0.003 | 0.250 | **0.789** | 1.150 | MISS |
| FE `/f/pizzlecole` | 0.004 | 0.199 | **0.947** | 1.185 | MISS |
| FE `/sponsors/{slug}` | 0.004 | 0.176 | **0.718** | 0.830 | MISS |
| FE `/login` | 0.003 | 0.233 | **0.499** | 0.607 | HIT |
| API `/health` | 0.005 | 0.173 | **0.526** | 0.527 | — |
| API `/api/v1/events` | 0.005 | 0.226 | **1.134** | 1.259 | — |
| API `/api/v1/legacy/mainlandvibes` | 0.004 | 0.238 | **1.728** | 1.729 | — |
| API `/api/v1/sponsors/public/{slug}` | 0.005 | 0.177 | **1.704** | 1.704 | — |

### API endpoints (median total, n=3) — MEASURED

| Endpoint | Median | First | Warm | Status | Bytes | Class |
|----------|-------:|------:|-----:|--------|------:|-------|
| `/health` | 345 ms | — | — | 200 | 104 | ACCEPTABLE |
| `/api/v1/events` | 871 ms | **1622** | **749** | 200 | **155187** | SLOW |
| `/api/v1/events/{slug}` | 536 ms | — | — | 200 | 12918 | ACCEPTABLE |
| `/api/v1/legacy/{host}` | 1339 ms | — | — | 200 | 8052 | SLOW |
| `/api/v1/u/{user}/legacy` | 1345 ms | — | — | 200 | 8052 | SLOW |
| `/api/v1/f/{user}` | 523 ms | — | — | 200 | 524 | ACCEPTABLE |
| `/api/v1/sponsors/public/{slug}` | **1462 ms** | 1763 | 1434 | 200 | 5777 | SLOW |
| `/api/v1/merch?limit=50` | 807 ms | — | — | 200 | 61105 | SLOW |
| `/api/v1/merch/{slug}` | 707 ms | — | — | 200 | 8928 | ACCEPTABLE |
| `/api/v1/blog/posts?limit=20` | 684 ms | — | — | 200 | 6313 | ACCEPTABLE |
| `/api/v1/help/articles?limit=20` | 528 ms | — | — | 200 | 21637 | ACCEPTABLE |

Heuristic classes: &lt;300 ms FAST · 300–800 ACCEPTABLE · 800–2000 SLOW · &gt;2000 CRITICAL.

**Note:** Backend processing time alone was **not** separable from network RTT in this audit (no `Server-Timing` / request-id duration headers). Total times include NETWORK + RENDER + APPLICATION + DATABASE.

---

## Cold Start Analysis

### Classification (this window)

| Latency class | Assessment |
|---------------|------------|
| **COLD-START LATENCY** | **Not dominant.** `/health` stayed ~345–526 ms across samples. No multi-second “sleep wake” observed. |
| **APPLICATION LATENCY** | **Significant.** Sponsor/legacy ~1.3–1.7 s even when warm. |
| **DATABASE LATENCY** | **Likely contributor** (unbounded events query, middleware SELECTs) — CODE-LEVEL RISK; not EXPLAIN’d. |
| **NETWORK LATENCY** | **Significant.** TLS ~0.17–0.25 s + Africa→US path (`cpt1::iad1`). |

### First vs warm — MEASURED

- `/api/v1/events`: first **1622 ms**, warm median **749 ms** → cache/connection warmup likely; not a classic 10–30 s Render Free spin-up.
- FE `/`: first **974 ms**, warm **337 ms** with `x-vercel-cache: STALE/HIT`.

### Startup / init — CODE-LEVEL RISK

| Item | Finding |
|------|---------|
| Docker entrypoint | `alembic upgrade head` before uvicorn |
| FastAPI lifespan | Seeds roles/categories/AI templates/etc. (best-effort) |
| Migrations at request time | Not observed in request path |
| Maintenance seed | Previously ran insert-without-commit → Neon locks (**OBSERVED IN LOGS**, mitigated in code) |
| Redis | Lazy connect + ping on first use; **no socket timeouts** |
| AI providers | Resolve on use, not every request |

### Render Free assessment

**Verdict:** With current warm timings, **Render Free sleep is not the primary UX problem in this audit window.** Application + geo + DB query shape dominate. Confirm the service remains on a plan that avoids long idle sleep; do **not** treat a plan upgrade alone as sufficient optimization.

---

## Frontend Performance

### Strengths

- Several public shells use ISR (`revalidate` 90–300)
- Homepage / login can be CDN HIT/STALE (**MEASURED**)
- Brotli compresses large HTML payloads (~471 KB → ~37 KB on wire for `/`)
- Lean npm surface (no chart/editor mega-deps)

### Weaknesses

- Marketplace detail/list pages often `x-vercel-cache: MISS` (**MEASURED**)
- `/f/[username]` forces `no-store` (**CODE-LEVEL RISK**) → FE median **1221 ms**
- Client-hydrated hubs (`/fans`, `/merch`, `/sponsorships`) defer data to browser
- Root layout always mounts Auth + Analytics + PWA + unread hooks when session exists

---

## Next.js Rendering

| Route | Mode | Notes |
|-------|------|-------|
| `/`, `/events`, `/events/[slug]`, `/u/[username]`, `/sponsors/[slug]`, `/blog`, `/help` | ISR-ish (`revalidate`) | Still often CDN MISS for dynamic segments |
| `/f/[username]` | Dynamic / no-store | Privacy-driven; costs latency |
| `/fans`, `/merch`, `/sponsorships` | Mostly client data | Fast HTML shell, slower perceived content |
| `/dashboard`, `/host`, `/sponsor` | Client shells | Auth-gated; not SSR-complete |

`force-dynamic` not used on main public marketing routes (only demo).

---

## Client JavaScript

**CODE-LEVEL RISK (not bundle-analyzer measured in this pass):**

- Large client islands: `EventsMarketplaceClient`, `EventDetailClient`, host/fan/sponsor/merch marketplaces
- `html5-qrcode` / `qrcode.react` for check-in (scoped)
- Global clients in root layout increase baseline JS on every page
- Manrope weights 400–800 (5 files) on every page

**PASS-ish:** No recharts/tiptap/monaco in `package.json`.

---

## API Performance

### Slowest measured (end-to-end)

1. `GET /api/v1/sponsors/public/{slug}` — **1462 ms** (SLOW)  
2. `GET /api/v1/u/{user}/legacy` / `legacy/{host}` — **~1340 ms** (SLOW)  
3. `GET /api/v1/events` — **871 ms** median; first 1622 (SLOW)  
4. `GET /api/v1/merch?limit=50` — **807 ms** (SLOW)  

### Structural issues — CODE-LEVEL RISK

- `list_published_events` / `_event_query()`: **9 selectinloads**, **no SQL limit**, Python-side filters (`backend/app/events/service.py`)
- Redis list cache (TTL ~90s) masks but does not remove cold/miss cost
- Maintenance middleware opens DB session on nearly every request
- Auth path can load user+roles+permissions in multiple middlewares + dependency

---

## Server Error Audit

### This audit window — MEASURED

| Code | Observed on sampled public routes? |
|------|-------------------------------------|
| 500 / 502 / 503 / 504 | **None** |
| 429 | **None** |
| 404 | Probe-only wrong API paths (`/api/v1/hosts?limit=50`, guessed directory URLs) — not product failures |
| 401 / 403 | Not exercised (no credentialed audit) |

### Prior production evidence — OBSERVED IN LOGS

- Mass `401` on `/messages/unread-count` and `/notifications/unread-count` after token clear while React user remained set (mitigated: session-expired clears user; NavLabel badge-gates hooks)
- Neon deadlocks / `idle in transaction` from maintenance `ensure_section_rows` insert-without-commit (mitigated in `maintenance/service.py`)
- SMTP timeouts on Render free outbound ports (ops; user reported plan upgrade)

### Code-level error handling — CODE-LEVEL RISK

- No global unhandled Exception handler beyond Starlette HTTPException
- Frontend `apiRequest` has **no default timeout** → hung requests possible
- Events list error UI is a simple danger text line (not rich EmptyState/retry)

---

## Database Performance

| Finding | Evidence type | Notes |
|---------|---------------|-------|
| Unbounded published events load + heavy eager loads | CODE-LEVEL RISK | Primary scale/latency risk |
| Python-side filtering/sorting after load | CODE-LEVEL RISK | CPU + transfer |
| Maintenance SELECTs every request | CODE-LEVEL RISK | Constant overhead |
| Suspended middleware sync DB on event loop | CODE-LEVEL RISK | Contends with async loop |
| Duplicate auth user loads | CODE-LEVEL RISK | Extra round-trips |
| Engine singleton + `get_db` close | PASS | `database.py` |
| Pool 10 / overflow 20 / timeout 10 / pre_ping | PASS / RISK | No `pool_recycle` |

**EXPLAIN ANALYZE:** NOT MEASURED (audit-only; no prod EXPLAIN run).

---

## Database Index Review

| Area | Status | Notes |
|------|--------|-------|
| users.email / account_status | GOOD INDEX | |
| events.slug, status, host_id, category/location | GOOD INDEX | |
| events (status, start_datetime) composites | GOOD INDEX | migration `20260721_0115_*` |
| events.visibility in composites | POSSIBLY MISSING | query uses visibility |
| events.end_datetime (upcoming) | POSSIBLY MISSING / NEEDS EXPLAIN | upcoming filtered in Python today |
| notifications (user_id, created_at) | POSSIBLY MISSING | separate indexes exist |
| messages (thread_id, created_at) | POSSIBLY MISSING | separate indexes exist |
| merch marketplace composites | GOOD INDEX | |
| sponsors status/slug | GOOD INDEX | |

**Do not add indexes without EXPLAIN** matching real query plans.

---

## Neon Connection Review

| Setting | Value | Assessment |
|---------|-------|------------|
| Engine | Module singleton | PASS |
| pool_size | 10 | ACCEPTABLE for current size; watch workers |
| max_overflow | 20 | |
| pool_timeout | 10s | |
| pool_pre_ping | True | PASS |
| pool_recycle | unset | RISK for idle Neon |
| connect_timeout | 5s | PASS |
| Session close | `finally: db.close()` | PASS |
| Region hint | `us-east-2` in env examples | GEO risk vs Africa users |

Prior incident: connection pile-up from maintenance inserts — **OBSERVED**, mitigated.

---

## Redis / Upstash

| Question | Finding |
|----------|---------|
| What cached? | Public events list/detail/nearby, taxonomy, blog content TTLs (`cache.py` / `public_cache.py`) |
| Fail-open? | Yes → memory fallback | Beneficial for availability |
| Timeouts? | **None** on Redis client | RISK — hang possible |
| Sequential calls? | Possible GET-then-SET per cache miss | Neutral–latency |
| Critical path? | Misses fall through to DB | Beneficial when hit; not SPOF for pages |
| Classification | **Beneficial with latency-contributor risk on miss/hang** | |

---

## Caching

| Layer | Public behavior | Notes |
|-------|-----------------|-------|
| Browser | Varies | |
| Next fetch / ISR | 90–300s many routes | `/f/*` no-store |
| Vercel CDN | HIT/STALE on `/`, `/login`; MISS on many SSR pages | MEASURED |
| FastAPI Cache-Control middleware | Present | |
| Redis | Events/taxonomy/etc. | |
| Must NOT publicly cache | auth, tickets, orders, private fan/sponsor, messages, admin, vault | CODE-LEVEL — SW excludes many of these |

---

## Network Waterfalls

### Public SSR detail (event / host / sponsor / fan)

```
generateMetadata → fetch entity
page()          → fetch same entity again  (dedupe depends on Next fetch cache; fan is no-store)
     → HTML to browser
     → hydrate client island
     → optional client fetches (recs, auth-gated)
```

**CODE-LEVEL RISK:** no `react.cache` wrappers around loaders.

### Dashboard (authenticated) — CODE-LEVEL RISK

```
AuthProvider: refresh? → /me
  → workspace hooks
  → P0 parallel: tickets, orders, merch, cart
      → refunds
      → deferred batch: Connect, Following, Passport, Vault, subs, Ambassador, reviews
Nav: unread messages + notifications polling (when logged in)
```

### Hosts marketplace (logged-in) — CODE-LEVEL RISK

Per-card `useHostAffiliation` → `fetchHostWorkspaces()` without shared module cache → **N identical workspace fetches**.

---

## N+1 Requests

| Surface | Pattern | Severity |
|---------|---------|----------|
| Hosts marketplace cards | N× workspaces | P1 CODE-LEVEL |
| Host event list cards | analytics per event | P2 CODE-LEVEL |
| Events list | single list API | PASS (amplification low) |
| Fans directory | single directory fetch | PASS |
| Merch home | 3 parallel + catalog | Fan-out P2, not N+1 |

---

## Authentication & RBAC

| Topic | Finding |
|-------|---------|
| Login latency | NOT MEASURED (no credentialed login in audit) |
| `/me` multiplicity | Bootstrap + many consumers — CODE-LEVEL RISK |
| 401 refresh | Single-flight refresh; retry once — mitigated stampede |
| Unread poll storm | Previously OBSERVED; mitigated |
| Permission DB | Full user+roles+permissions via selectinload; may run 2–3×/request | P1 CODE-LEVEL |
| JWT claims for RBAC | Not trusted (correct for security) | Do not weaken |

---

## Dashboard Performance

HTML shell ~380 ms (**MEASURED**). Perceived load dominated by client waterfall above — **CODE-LEVEL RISK**, not fully timed authenticated.

---

## Event Detail Performance

| Piece | Notes |
|-------|-------|
| SSR + metadata | Dual `loadEvent` — CODE-LEVEL RISK of duplicate API |
| FE TTFB | ~0.89 s median (**MEASURED**) |
| API detail | ~536 ms median; ~13 KB |
| Related/recs/merch/reviews | Additional client/SSR children possible |
| JSON-LD | Built from same loader data in page |

---

## Host / Sponsor / Fan SSR Performance

| Route | FE median | API median | Cache |
|-------|----------:|-----------:|-------|
| `/u/mainlandvibes` | 838 ms | legacy ~1340 ms | MISS |
| `/sponsors/korawave-pay` | 758 ms | public ~1462 ms | MISS |
| `/f/pizzlecole` | 1221 ms | `/f/*` ~523 ms | MISS + no-store |

Fan page is slower on FE than its small API payload suggests → **HYPOTHESIS:** metadata+page double fetch and/or SSR wait + RSC payload, not DB size.

---

## Payload Sizes

| Response | Uncompressed | Flag |
|----------|-------------:|------|
| `/api/v1/events` (12 events) | **151.5 KB** | &gt;100 KB |
| `/api/v1/merch?limit=50` | 59.7 KB | watch |
| Event detail | 12.6 KB | OK |
| Legacy host | 7.9 KB | OK (latency not size) |
| Sponsor public | 5.8 KB | OK (latency not size) |
| FE `/` HTML decoded | ~471 KB | large RSC; ~37 KB br on wire |

---

## Image Performance

| Topic | Finding |
|-------|---------|
| `next/image` | Rare (~5 files) |
| Plain `<img>` / `Media.tsx` | Dominant; lazy by default |
| `remotePatterns` | Missing in `next.config` |
| Hero priority | Limited `priority` usage |

**CODE-LEVEL RISK** for LCP on image-heavy pages. Not Lighthouse-measured.

---

## Font Performance

`layout.tsx`: Manrope via `next/font/google`, weights **400–800**, `subsets: ["latin"]`, `display: "swap"`.

**CODE-LEVEL RISK:** five weights may be excessive; justification not proven necessary for all public pages.

---

## Third-Party Scripts

| Script | Load | Risk |
|--------|------|------|
| GA4 | Consent + prod gated | Low–medium |
| First-party analytics | Always init | Low |
| Paystack Inline | Lazy on pay | Medium on checkout only |
| Google Maps/Places | Lazy when needed | Medium on map pages |

---

## Core Web Vitals Risks

| Vital | MEASURED? | CODE-LEVEL RISK |
|-------|-----------|-----------------|
| LCP | NOT MEASURED | Slow TTFB on MISS pages; hero via plain img; large RSC |
| INP | NOT MEASURED | Large client islands; marketplace filters |
| CLS | NOT MEASURED | Images without dimensions in Media; late fonts swap |

Do not invent CWV scores.

---

## Sitemap Performance

- ~196 URLs in production sitemap (**MEASURED** earlier / consistent with ~185+)
- Sources fetched with `Promise.all` + `revalidate: 300`
- Fans: sequential pagination up to **50 pages × 48** — **CODE-LEVEL RISK** at scale
- Sharding not required at ~200 URLs today

---

## Timeout Analysis

| Layer | Timeout | Gap |
|-------|---------|-----|
| Frontend `apiRequest` / `fetchPublicJson` | **None** | Can hang past Render |
| Hosts SSR race | 5s | Good local pattern |
| DB connect | 5s | |
| DB pool | 10s | |
| Redis | **None** | RISK |
| Paystack httpx | 30s | |
| AI | ~30s default | Separate budget |
| SMTP | 20–30s | |

Mismatch risk: browser waits forever while upstream dies earlier — **CODE-LEVEL RISK**.

---

## Background Work

| Work | In request path? |
|------|------------------|
| Ticket email after pay | Enqueued (preferred) |
| Sync email if queue disabled | Yes — RISK |
| Push deliver sync | Possible if not worker |
| Paystack webhook finalize | Substantial sync DB — correctness &gt; speed |
| AI | AI routes only |

---

## Payment Reliability

- Init/verify: sync HTTP 30s timeout  
- Webhook: signature + idempotent event key + paid recovery  
- Do **not** weaken verification for speed  
- Latency NOT MEASURED (no transactions)

---

## Logging / Observability

| Signal | Present? |
|--------|----------|
| Request duration middleware | **No** |
| Request ID | Not standardized in audit |
| DB duration | No |
| `/health` Redis | Yes |
| `/health` DB | **No** |
| Exception detail | Default FastAPI |

**Recommend (do not implement in this audit):** timing middleware logging method, normalized route, status, `duration_ms`, request_id; warn &gt;1s / &gt;3s / &gt;10s; never log tokens/passwords/payment secrets/private messages.

---

## PWA / Service Worker

`frontend/public/sw.js` (`padeya-pwa-v24`):

- Network-first navigations; offline fallback  
- Does **not** cache `/api` or sensitive path regex  
- Cache-first only icons/brand/manifest  

**PASS** for private API caching rules (code-level). Stale-asset after deploy: NOT MEASURED.

---

## Geographic Latency

| Evidence | Value |
|----------|-------|
| MEASURED | `x-vercel-id: cpt1::iad1` (Cape Town edge → IAD) |
| CODE-LEVEL | Neon host pattern `us-east-2` |
| CODE-LEVEL | Upstash `*.upstash.io` (typically US) |
| HYPOTHESIS | Render region also US-proximate |

Cross-region Africa→US is a **real** contributor to TLS+TTFB floor (~0.4–0.6 s even for tiny `/health`).

Colocate only when product priority is African TTFB and evidence remains after app-query fixes.

---

## Scale Risks

| Area | CURRENT PROBLEM | FUTURE SCALE RISK |
|------|-----------------|-------------------|
| Events list | Heavy payload for 12 events; unbounded query | 1k–10k events → severe |
| Fan sitemap pages | Sequential loop | 10k fans → sitemap TTFB blowup |
| Notifications/messages | Index composites possibly missing | Inbox at 100k users |
| Hosts N× workspaces | Logged-in amplification | Worse with more cards |
| Maintenance middleware | Constant DB tax | Multiplies with QPS |
| Analytics dashboards | Not fully timed | Aggregate tables grow |

---

## Finding Matrix (selected)

| ID | Status | Sev | Layer | Evidence | Affected | Likely cause | Recommended fix | Impact | Complexity |
|----|--------|-----|-------|----------|----------|--------------|-----------------|--------|------------|
| F01 | FAIL | P1 | DATABASE/BACKEND | CODE + MEASURED | `/api/v1/events`, `/events` | Unbounded ORM + Python filter | SQL filters + limit/cursor + lean columns | High | Med |
| F02 | RISK | P1 | BACKEND | CODE | All API | Maintenance DB every request | Cache decision in Redis/memory; skip seed path | High | Med |
| F03 | FAIL | P1 | BACKEND | MEASURED | sponsor/legacy APIs | App/DB work + geo | Profile queries; eager-load once | High | Med |
| F04 | RISK | P1 | FRONTEND | CODE + MEASURED | `/f/*` | no-store + dual fetch | `react.cache`; short private cache where safe | Med | Low |
| F05 | RISK | P1 | FRONTEND | CODE | `/u`,`/sponsors`,`/events/[slug]` | Dual metadata/page fetch | `react.cache` / shared loader | Med | Low |
| F06 | RISK | P1 | BACKEND | CODE | Auth routes | Multi load user+RBAC | Request-scoped cache | Med | Med |
| F07 | RISK | P1 | FRONTEND | CODE | `/hosts` logged-in | N× workspaces | Module-level cache / context | Med | Low |
| F08 | PARTIAL | P1 | NETWORK | MEASURED | All | `cpt1→iad1` + US data | Fix app first; consider region later | Med | High |
| F09 | RISK | P2 | REDIS | CODE | Cache path | No Redis timeouts | socket timeouts | Med | Low |
| F10 | RISK | P2 | FRONTEND | CODE | All fetch | No API timeout | AbortSignal timeouts | Med | Low |
| F11 | RISK | P2 | FRONTEND | CODE | Images | Plain img, no remotePatterns | next/image + dimensions | Med | Med |
| F12 | RISK | P2 | FRONTEND | CODE | Fonts | 5 Manrope weights | Trim to 400/600/700 | Low | Low |
| F13 | RISK | P2 | BACKEND | CODE | Ops | No timing middleware | Add duration logs | High (ops) | Low |
| F14 | RISK | P2 | BACKEND | CODE | Health | No DB ping | `/health` readiness split | Med | Low |
| F15 | PARTIAL | P2 | VERCEL | MEASURED | Many SSR | CDN MISS | Align Cache-Control / ISR | Med | Med |
| F16 | PASS | — | FRONTEND | CODE | SW | API not cached | Keep | — | — |
| F17 | PASS | — | DATABASE | CODE | Engine | Singleton pool | Keep | — | — |
| F18 | RISK | P0* | DATABASE | OBSERVED (mitigated) | All API | Maintenance seed deadlock | Keep regression tests | Critical if regresses | Done |
| F19 | RISK | P1 | FRONTEND | OBSERVED (mitigated) | Unread polls | 401 storm | Keep session clear + token guards | High if regresses | Done |
| F20 | NOT MEASURED | P2 | FRONTEND | — | CWV | — | Lighthouse field data | — | — |

\*P0 historical; currently mitigated — treat regression as P0.

---

## P0 Findings

**Open P0 (active outage/data integrity) in this audit window:** none measured.

**Mitigated P0 (must not regress):**
1. Maintenance section seed lock contention on Neon  
2. Authenticated unread polling after session expiry (401 storm)

---

## P1 Findings

1. Unbounded / heavy `list_published_events` + 151 KB payload for 12 events  
2. Slow warm APIs: sponsor public (~1.46 s), legacy (~1.34 s)  
3. Per-request maintenance middleware DB tax  
4. Fan passport SSR no-store + likely duplicate fetches (FE ~1.22 s)  
5. Duplicate SSR loaders without `react.cache`  
6. Auth/RBAC user loaded multiple times per request  
7. Hosts marketplace N× `fetchHostWorkspaces`  
8. Cross-region Africa→US floor latency  

---

## P2 Findings

1. No FastAPI request-timing middleware / Server-Timing  
2. Health without DB check  
3. Redis client without timeouts  
4. Frontend API client without timeouts  
5. Widespread unoptimized images  
6. Manrope 5 weights  
7. Sitemap fan pagination scalability  
8. Merch marketplace multi-fetch fan-out  
9. CDN MISS on many ISR pages  
10. Missing composite indexes pending EXPLAIN  

---

## Quick Wins

Ranked by impact / effort:

1. **Wrap SSR loaders in `react.cache`** (event/host/fan/sponsor/merch)  
2. **Add frontend fetch timeouts** (e.g. 10–15 s public, shorter for chrome polls)  
3. **Add Redis socket timeouts**  
4. **Request-scoped memo for `get_current_user` / RBAC**  
5. **Cache maintenance decision** (short TTL memory/Redis) to skip DB when off  
6. **Lean events list DTO** (drop agenda/people/checkout from list) + SQL `LIMIT`  
7. **Module-cache `fetchHostWorkspaces`** for host cards  
8. **Trim Manrope weights**  
9. **Add FastAPI duration logging middleware**  
10. **Split liveness vs readiness** (`/health` vs `/ready` with DB)  

---

## Infrastructure Findings

| Item | Verdict |
|------|---------|
| Render Free sleep | **Not primary** in this warm window |
| Render always-on | Confirm plan; still needed for idle nights |
| Neon region | US — contributes to Africa RTT |
| Upstash region | Likely US — same |
| Vercel | Edge CPT, compute IAD — MEASURED |
| Compression | Brotli works when Accept-Encoding set — MEASURED |
| Secrets hygiene | Ensure `.env.example` has **placeholders only** (no live credentials) — ops note, no values published here |

---

## Recommended Performance Budget

Targets for Pàdéyá’s current architecture (Africa users + US origin):

| Surface | Budget |
|---------|--------|
| Public HTML warm TTFB (CDN HIT) | &lt; **400 ms** |
| Public HTML warm TTFB (SSR MISS) | &lt; **800 ms** p50; &lt; **1.5 s** p95 |
| Simple API (health, small GET) | p50 &lt; **300 ms** origin*; p95 &lt; **800 ms** |
| Complex API (list/detail aggregates) | p50 &lt; **700 ms**; p95 &lt; **2 s** |
| Events list payload | &lt; **50 KB** compressed typical page |
| 5xx rate | &lt; **0.5%** |
| Auth chrome polls | Fail closed on missing token; no retry storm |

\*Origin time excluding multi-continent RTT; field budgets should be region-aware.

---

## Recommended Implementation Roadmap

### Phase 0 — Protect reliability (1–2 days)
- Regression tests for maintenance seed / no insert-without-commit  
- Confirm unread hooks never poll without token  
- Add timing middleware + slow-request logs  
- `/ready` with DB ping  

### Phase 1 — Cut API P50 (3–7 days) — **workspace complete; await deploy + remeasure**
- Lean list queries + SQL filters/limits for events  
- Profile sponsor public + legacy endpoints  
- Request-scoped auth memoization  
- Maintenance short-circuit cache  
- Host workspaces single-flight (moved up — API amplification)  

### Phase 2 — Frontend SSR/CDN (3–5 days)
- `react.cache` loaders  
- Revisit fan cache policy (privacy-safe short TTL)  
- Fetch timeouts (partially in Phase 0)  

### Phase 3 — Assets & CWV (3–5 days)
- next/image + dimensions for heroes/avatars  
- Font weight trim  
- Field CWV (CrUX / Lighthouse)  

### Phase 4 — Geography (only if Phase 1–2 insufficient)
- Measure again from target markets  
- Consider colocating Render/Neon/Upstash nearer users  

**Do not** start with index spray or Redis TTL churn without query plans and hit-rate data.

---

## How to Re-run (safe)

```bash
PERF_BASE_URL=https://padeya.com \
PERF_API_URL=https://padeyawebsite.onrender.com \
PERF_SAMPLES=3 \
PERF_OUT=docs/performance-audit-timings.json \
node frontend/scripts/performance-production-audit.mjs
```

Rules: GET/HEAD only · low volume · no login · no payments · no stress tools (`ab`/`wrk`/`k6`).

---

## Appendix: Latency Attribution Cheat Sheet

| Symptom | More likely |
|---------|-------------|
| `/health` ~0.5 s from Africa | NETWORK / GEO floor |
| `/health` 5–30 s after idle | RENDER cold start |
| `/events` API 1.5 s+, health 0.5 s | APPLICATION / DATABASE |
| FE HIT 0.3 s, FE MISS 1.2 s | VERCEL origin + SSR upstream |
| Small JSON but 1.5 s | Query shape / middleware / geo, not payload |
| Large JSON + slow | Payload + serialization + ORM |

---

*End of audit. No production code, indexes, or cache behavior was changed by this document.*
