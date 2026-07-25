# Pàdéyá Performance Implementation

Brand: **Pàdéyá**  
Source audit: [PERFORMANCE_AUDIT.md](./PERFORMANCE_AUDIT.md)

---

## Phase 0 — Reliability & observability (implemented)

Scope: measurable latency/failures and hang protection. **No** query rewrites, index changes, region moves, or broad cache policy changes.

### Request timing standard

Middleware: `backend/app/core/timing_middleware.py` (`RequestTimingMiddleware`).

Safe log line:

```text
[HTTP] request_id=… GET /api/v1/events 200 duration_ms=842 env=… deploy=… user_loads=… maintenance_ms=…
```

Slow prefixes (log only — not converted to errors):


| duration_ms | Label              |
| ----------- | ------------------ |
| < 1000      | (normal) `[HTTP]`  |
| ≥ 1000      | `[HTTP:SLOW]`      |
| ≥ 3000      | `[HTTP:VERY_SLOW]` |
| ≥ 10000     | `[HTTP:CRITICAL]`  |


Never logged: Authorization, JWTs, passwords, secret query params, bodies, private message content.

Paths are normalized (`/api/v1/events/{slug}`, `/api/v1/f/{username}`, UUIDs → `{id}`).

### Request IDs

- Accept `X-Request-ID` when safe (`[A-Za-z0-9._-]`, ≤ 64 chars)
- Else generate `uuid4().hex`
- Echo `X-Request-ID` on responses
- Available on `request.state.request_id` and contextvar for error logs



### Server-Timing

```http
Server-Timing: app;dur=842.3
```

Reserved for later: `db;dur=`, `redis;dur=`, `upstream;dur=` (not instrumented in Phase 0).

CORS exposes `X-Request-ID` and `Server-Timing`.

### Health vs readiness


| Endpoint                           | Meaning                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `GET /health` (+ `/api/v1/health`) | **Liveness** — process up. No DB query.                                                                   |
| `GET /ready` (+ `/api/v1/ready`)   | **Readiness** — `SELECT 1` on Postgres. Redis status reported but **fail-open** (Redis down ≠ not ready). |


Responses omit hostnames, credentials, and connection strings.

### Frontend timeout policy

Central module: `frontend/src/lib/api-timeouts.ts`


| Budget    | ms    | Use                                    |
| --------- | ----- | -------------------------------------- |
| `public`  | 10000 | Public / SSR marketplace GETs          |
| `chrome`  | 5000  | Unread polls / nav chrome              |
| `default` | 15000 | Normal authenticated API               |
| `long`    | 60000 | Explicit AI / upload / download opt-in |


Wired into `apiRequest`, `apiUpload`, `apiDownload`, `fetchPublicJson` (SEO + cache helpers).

- Timeouts become `TimeoutError` (recognizable; not infinite spinners)
- **No automatic retry** of POST/PUT/PATCH/DELETE on timeout
- 401 refresh retry unchanged (auth only)



### Redis timeout policy

`backend/app/core/redis.py`:

- `socket_connect_timeout=3s`
- `socket_timeout=3s`
- Brief cooldown after failed connect (fail-open for cache)
- Does not change rate-limit / lock / payment correctness semantics — those callers must still treat Redis appropriately; cache remains fail-open



### Maintenance / RBAC instrumentation

- Maintenance middleware logs `[MAINTENANCE] request_id=… duration_ms=… db_touched=… allowed=…` without config secrets
- Timing log includes `maintenance_lookup` / `maintenance_db` / `maintenance_ms`
- `get_user_by_id` increments request-local `user_loads` / `roles_loads` / `permissions_loads` (selectinload path) for duplicate-load evidence — **no permission semantic changes**



### Global errors

`backend/app/core/exception_handlers.py` — unhandled exceptions → generic 500 + `request_id`; traceback server-side only. HTTPException / 4xx unchanged.

### Regression protection

1. Maintenance seed commit / short-circuit — `tests/test_maintenance_seed_regression.py`
2. Unread poll guard without token — `canPollAuthenticatedChrome()` + vitest



### Audit script terminology

`frontend/scripts/performance-production-audit.mjs` records `total_response_ms` (full transfer).  
**TTFB** remains curl phase timings only. Cold probe labeled **NOT A TRUE IDLE COLD START**.

---

## Phase 1 — API/query latency (implemented in workspace)

Scope: reduce backend/API latency and DB work. **No** region moves, speculative indexes, auth/Paystack weakening, broad public cache TTL changes, UI redesign, or image/font work.

Evidence labels:

| Label | Meaning |
|-------|---------|
| **LOCAL TEST RESULT** | pytest / vitest in this workspace |
| **CODE-LEVEL IMPROVEMENT** | Query/DTO/middleware changes landed; expected to help once deployed |
| **DEPLOYED MEASUREMENT** | Production timings after deploy — **pending** |

### Phase 1 baseline (pre-change production)

Captured low-volume against live API **before** these code changes (Phase 0 also not yet live — no `Server-Timing` / `/ready` 404). Artifact: [`performance-phase1-baseline.json`](./performance-phase1-baseline.json).

| Endpoint | total_s median | bytes (uncompressed) | app;dur |
|----------|---------------:|---------------------:|---------|
| `GET /health` | ~0.63 | 104 | n/a (Phase 0 undeployed) |
| `GET /ready` | ~0.70 | 41 | **404** |
| `GET /api/v1/events` | ~0.98 | **155187** | n/a |
| `GET /api/v1/events/{slug}` | ~0.71 | ~13 KB | n/a |
| `GET /api/v1/legacy/{host}` | ~1.51 | ~8 KB | n/a |
| `GET /api/v1/u/{username}/legacy` | ~1.52 | ~8 KB | n/a |
| `GET /api/v1/sponsors/public/{slug}` | ~1.58 | ~6 KB | n/a |
| `GET /api/v1/merch?limit=50` | ~0.85 | ~61 KB | n/a |

Do **not** treat wall-clock alone as app duration. After deploy, prefer `Server-Timing: app;dur=`.

### Events list query

**CODE-LEVEL IMPROVEMENT** — `backend/app/events/service.py` + `router.py`

- `_event_list_query()` — selectinload only `category`, `location`, `ticket_types`, `host` (no agenda/people/media/venue/checkout)
- `list_published_events` — SQL filters for status, visibility, `end_datetime >= now`, `q`, category, location/city, weekend, paid/free; SQL `ORDER BY`; SQL `LIMIT` (max **100**)
- Public route accepts `limit` 1–100; Redis key includes `v=listv2` so old fat payloads are not reused
- `serialize_event_list_item` / `list_mode=True` — empty detail nests; null policy/SEO blobs; description truncated to ~160 chars for hover preview; public ticket types only (no access codes)

Preserves prior product filter semantics (listed + approval_required, upcoming by end time, etc.).

### Sponsor public profile

**CODE-LEVEL IMPROVEMENT** — `backend/app/sponsor_profiles/public_profile_service.py`

- Batched placement → slot/host/event/deal/deliverable loads (same public eligibility rules)
- Partner hosts derived from sponsored rows (no per-host re-fetch)
- Related sponsors capped query (no full directory scan)
- Still public-safe only (no budgets/team/payment internals)

### Host Legacy public API

**CODE-LEVEL IMPROVEMENT** — `legacy/service.py` + `studio.py`

- `build_legacy_page(..., host=, rescore=)` — public path `rescore=False` (serve stored score; bootstrap only if missing)
- Both `/legacy/{host}` and `/u/{username}/legacy` share assembly; events query capped at 80

### Maintenance short-circuit

**CODE-LEVEL IMPROVEMENT** — `maintenance/decision_cache.py` + middleware

- Process-memory TTL **15s** for “mode off / no active sections → allow without DB”
- Invalidated on admin settings/section/schedule mutations and when schedules apply mode changes
- Does **not** cache secrets; does not skip DB when maintenance/sections are active
- Observability: `decision_cache_hit` on maintenance obs notes; `maintenance_db=false` when short-circuited

### Request-scoped auth/RBAC

**CODE-LEVEL IMPROVEMENT** — `request_context.py` + `users/service.get_user_by_id`

- Per-request memo keyed by `(user_id, session id)` — reuse within one HTTP request/session only
- Suspension gate uses thin `get_user_account_gate` (no roles/permissions load)
- Counters still recorded for observability; JWT claims are not trusted as RBAC source of truth

### Host workspaces single-flight (FE)

**CODE-LEVEL IMPROVEMENT** — `frontend/src/lib/hosts-api.ts` + auth storage invalidation

- Module-level in-flight/result cache per access token
- Invalidate on login/logout (`setTokens` / `clearTokens`), active-workspace change, host onboard
- Vitest: `hosts-api.workspaces.test.ts`

### Database indexes

**None added in Phase 1.** Candidates (visibility, end_datetime, notification/message composites) remain documented for later **only with EXPLAIN evidence**.

### Redis

- List cache key versioned (`v=listv2`); filter params still part of key
- Cache miss runs optimized producer; outage still fail-open where intended
- No broad TTL policy change

### Local tests

| Suite | Result |
|-------|--------|
| `tests/test_performance_phase1.py` | **10 passed** (LOCAL) |
| `tests/test_performance_phase0.py` | passed (LOCAL) |
| vitest `hosts-api.workspaces.test.ts` + Phase 0 timeout/unread | **10 passed** (LOCAL) |

### Before / after measurements

| Endpoint | Before median (prod total_s) | After median | % | Payload before | Payload after |
|----------|-----------------------------:|-------------:|--:|---------------:|--------------:|
| `/api/v1/events` | ~0.98 s | **pending deploy** | — | ~155 KB | **pending deploy** |
| Sponsor public | ~1.58 s | **pending deploy** | — | ~6 KB | **pending deploy** |
| Legacy public | ~1.51 s | **pending deploy** | — | ~8 KB | **pending deploy** |

After deploy:

```bash
PERF_BASE_URL=https://padeya.com \
PERF_API_URL=https://padeyawebsite.onrender.com \
PERF_SAMPLES=3 \
node frontend/scripts/performance-production-audit.mjs
```

Compare `Server-Timing` `app;dur=` and uncompressed JSON sizes. Do not claim production improvement until that run.

### Phase 1 targets (goals, not guarantees)

| Metric | Goal |
|--------|------|
| Events list app p50 | &lt; 600 ms (stretch &lt; 400 ms warm/miss-optimized) |
| Sponsor / Legacy app p50 | &lt; 700 ms |
| Events list payload | meaningfully &lt; ~151 KB; prefer &lt; 75 KB / &lt; 50 KB if cards allow |
| Maintenance | near-zero DB while cached off |
| Auth | one user+RBAC load path per request where semantics allow |

---

## Remaining Phase 2 (frontend / SSR)

Not done in Phase 1:

1. SSR `react.cache` for duplicate metadata/page loaders
2. Safe revisit of fan passport `no-store` / CDN policy
3. Image / font optimization
4. Geography / region moves only if app fixes leave unacceptable Africa TTFB floor
5. Index additions only with query-plan evidence

Do **not** weaken authorization or payment verification for speed.