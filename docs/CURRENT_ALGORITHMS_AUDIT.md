# Pàdéyá — current algorithms audit

**Date:** 2026-07-22  
**Scope:** Rankings, recommendations, sorting, matching, scoring, and discovery logic across the public website, fan dashboard, and admin surfaces.  
**Method:** Code and docs inspection only — no behavior changes.  
**Brand:** Pàdéyá (correct spelling throughout).

This document describes **what the product does today**, what is **missing**, and what should be **improved next**, before adding new algorithms.

---

## Executive summary

| Category | Mostly global / editorial | Geo-aware | Personalized (rules) | No real algorithm |
|----------|---------------------------|-----------|----------------------|-------------------|
| Homepage | Picks, featured seed, blog | Nearby section (optional) | — | Hosts/merch on `/` (CTA only) |
| Events | List + featured flag + Picks | Near-me, map, nearby API | — | “Recommended” ≈ featured → soonest |
| Hosts | Public `/hosts` directory | City chips (client filter) | `GET /hosts/recommendations` (auth) | Legacy `related_discovery` = link chips |
| Fan Connect | — | Optional one-shot geo | Scoring v2 + diversity mixer | — |
| Merch / sponsors | Featured + sort keys | City filter (merch) | Access only (Vault), not rank | Sponsor “recommended” heuristic (client) |
| Search | Per-silo ILIKE / filters | City on fans/events | Host recs separate from search | No unified relevance rank |
| Trust | Legacy composite score | — | — | Content graph ranks not shipped |
| AI ranking | **Blocked** for discovery keys | — | — | Draft/summarize/help only |

**AI discovery safeguards (confirmed):** `discovery.why_recommended`, `fan.connect.explanation`, and `recommend_featured_events` remain disabled/quarantined; no LLM re-ranks public feeds. Host fan recommendations are **rules-only** in `app/hosts/recommendations/`.

---

## 1. Homepage discovery

**Page:** `frontend/src/app/page.tsx` (ISR `revalidate = 120`)  
**Loader:** `frontend/src/lib/home/load-homepage-public.ts`

### Pàdéyá Picks

| Field | Detail |
|-------|--------|
| Route / component | `/` → `HomePadeyaPicks` → `PadeyaPicksSection` |
| API | `GET /api/v1/events/padeya-picks?context=homepage` |
| Backend order | `placements/service.list_padeya_picks` — Primary/Secondary slots by `slot_number`; live placement window (`starts_at`/`ends_at`); event must be `published` + `listed`/`approval_required` |
| Frontend | `resolvePadeyaPicks` keeps slot order; fills empty slots to **2** from featured pool with client `sort: "trending"` |
| Personalization | No |
| Location | Global homepage context (no per-user city on picks API) |
| Admin curation | Yes — Featured Placement / admin Picks |
| Fallback | Empty → trending featured upcoming; empty UI → link `/events` |

### Featured events (SSR seed)

| Field | Detail |
|-------|--------|
| Route / component | Used as SSR seed; grid via `FeaturedEvents` |
| API | `GET /events?sort=featured` (+ optional default city params from `NEXT_PUBLIC_DEFAULT_DISCOVERY_CITY_*`, default Lagos) |
| Backend | `list_published_events`; `sort=featured` → featured first, then `start_datetime` |
| Frontend | `diversifyHomepageEvents` — prefer `featured`, category round-robin, **limit 8** |
| Personalization | No |
| Location | Optional default city for seed pool |
| Admin curation | `Event.featured` flag |
| Fallback | City pool empty → diversified global featured |

### Nearby / “Trending” (same section)

| Field | Detail |
|-------|--------|
| Route / component | `HomeNearbyEventsSection` → `FeaturedEvents` |
| API (client) | `GET /events/nearby` (`lat`, `lng`, `radius_km`, `limit=8`) |
| Backend | `events/geo.list_nearby_events` — within radius; sort `(distance, start, featured, -ticket_sold_proxy, -freshness)` |
| Frontend | Re-sort by `distance_km`; pad to 8 with SSR seed; eyebrow **“Trending”** when geo declined/unavailable (label only) |
| Personalization | No (geo only) |
| Location | Browser/stored geo or Places city; soft auto-locate if previously allowed |
| Admin curation | Featured as tie-break in nearby sort only |
| Fallback | SSR `defaultCityEvents` or `featured`; declined geo → seed + help copy |

**Note:** “Trending” on homepage is **not** a separate engagement algorithm — it reuses featured/city SSR seed unless nearby mode is active.

### Discovery rails (weekend / free / VIP)

| Field | Detail |
|-------|--------|
| Component | `HomeDiscoveryRails` |
| API | `GET /events?sort=soonest` |
| Frontend | `buildMarketplaceGroups` — client grouping/labels |
| Personalization | No |

### Hosts / merch on homepage

| Surface | Behavior |
|---------|----------|
| Hosts | `HomeLegacyCta` — static CTA to `/hosts`; **no host list/ranking on `/`** |
| Merch | **No merch feed** on homepage |
| Sponsors | `HomeSponsorship` — static CTA to `/sponsors` |
| Blog | `HomeBlogTeaser` — `GET /blog/posts?limit=3`, `published_at DESC`; no `featured` filter on homepage |

---

## 2. Event discovery algorithm

**Core backend:** `backend/app/events/service.py` → `list_published_events`  
**Core frontend:** `frontend/src/lib/discovery/event-filters.ts` → `filterPublicEvents`, `compareEvents`  
**Marketplace:** `frontend/src/lib/events/marketplace-listing.ts`

### Eligibility (public lists)

- `status == published`
- `visibility in (listed, approval_required)` — excludes unlisted / password-protected
- `end_datetime >= now` (still live)
- Optional filters: `q`, category, taxonomy location, weekend, paid
- Public ticket types only in API payloads; access codes stripped
- **Sold out:** remains in lists; optional marketplace filter excludes; “Sold out” label from remaining inventory
- **Private event type** can still list if visibility is listed (product nuance)

### Routes

| Route | Mechanism |
|-------|-----------|
| `/events`, `/events/search` | SSR/CSR public list + `filterMarketplaceEvents` |
| `/events/today`, collections | `CollectionLandingClient` + `today` / format / price presets |
| `/events/c/[slug]` | BE category + client weekend/soonest |
| `/events/city/*`, state/area/country | `location_kind` + `location_slug` on BE |
| `/events/calendar` | Redirect → `?view=calendar`; `GET /events/calendar` month grouping |
| `/events/map`, `/events/near-me` | Map bounds / geo consent + proximity sort on client or `/events/nearby` |
| Event detail related | **Frontend only** — `rankRelatedEvents` / `groupRelatedEvents` |

### Sort keys (`filterPublicEvents`)

| Sort | Order |
|------|--------|
| `soonest` (default in filter helper) | Start ascending |
| `newest` | `published_at` / `created_at` desc |
| `featured` | Featured first, then soonest |
| `recommended` / `trending` | Featured first, then soonest (**not** behavioral trending) |
| `price_asc` / `price_desc` | Min public ticket price |

Marketplace default sort: **`recommended`**. With near-me active: distance enrich → `sortMarketplaceByProximity`.

### Related events (“More in …”)

Priority: **same host → same city → same category → similar vibe** (`related-discovery.ts`). Pool is the current public event list passed into the detail page — not a dedicated graph API.

### Personalization status

**None** for event lists. Editorial Picks + featured flag + geo proximity only.

### Missing signals (events)

- Per-fan ticket history / category affinity in list rank
- True engagement trending (views, saves, velocity)
- Graph edges (`trending_in_city`, `recommended_next` in taxonomy doc) — **not production-ranked**
- Server-side related-events API (today FE-only)

---

## 3. Host discovery algorithm

### Public marketplace `/hosts`

| Field | Detail |
|-------|--------|
| Route / component | `frontend/src/app/hosts/page.tsx` → `HostsMarketplace` |
| API | `GET /api/v1/legacy/discover/hosts` (cached ~180s) |
| Backend | `legacy/discover.list_discover_hosts` |
| Who appears | `Host.status == active` + ≥1 published listed/approval_required event |
| Server rank | Verified first → upcoming event count → verified check-ins → display name; cap 60–120 |
| Featured strip (FE) | Top 3 **verified** by `upcoming_events_count + tickets_sold_count` |
| Directory | Excludes featured IDs when unfiltered; category/location = **client** chip filters |
| Personalization | **No** on public page (following state for follow button only) |
| Fallback | `DEMO_DISCOVER_HOSTS` if API empty locally |

### Host profile `/@username` / Legacy

- Public host page blocks; `related_discovery` block = **navigation chips** (Events, Hosts, city hub, category) — not ranked host list
- No “similar hosts” scoring on profile today

### Fan host recommendations (auth)

| Field | Detail |
|-------|--------|
| API | `GET /api/v1/hosts/recommendations` |
| FE | `HostRecommendationsSection` on `/dashboard` |
| Algorithm | Rules-only `FanHostAffinity` + `score_host_for_fan`; pool = discover hosts; exclude followed + own host; dismiss 60d |
| Signals | Check-ins, tickets, similar-to-followed, connected fans’ follows (aggregate), passport categories, saved city/area, trust/upcoming, dismiss/feedback |
| Threshold | Score ≥ 35 + safe reason |
| AI | **Not** wired to `discovery.why_recommended` |

### Missing host signals (public + rec)

- Personalized ranking on `/hosts` for signed-in users
- Username search / relevance on marketplace (lookup by slug only)
- Graph `city_top_host` (doc-only)
- Explicit “hosts like X” from co-attendance graph

---

## 4. Fan Connect matching algorithm

**Docs:** `docs/FAN_CONNECT.md`, `docs/FAN_CONNECT_SUGGESTION_ALGORITHM_AUDIT.md`  
**Backend:** `backend/app/fan_connect/` — `service.suggestions`, `scoring.FanConnectScoringService`, `eligibility.classify_fan_connect`, `diversity.mix_suggestions`

### Flow

1. Actor must have Fan Connect enabled + passport username  
2. Load up to **120** public passports (`updated_at DESC`) — not score-ordered at query  
3. Per candidate: `classify_fan_connect(for_discovery=True)` then `evaluate`  
4. Keep if score ≥ **40**, eligible, ≥1 safe reason  
5. Upsert suggestion cache (24h); **serve live computed list** (cache not read for response)  
6. `mode=mixed`: diversity mixer quotas; else sort score DESC + paginate  

### Scoring weights (`fan_connect/constants.py`)

| Signal | Points (high level) |
|--------|---------------------|
| Same upcoming public event | +35 |
| Shared checked-in event | +25 |
| Friend-of-friend | +20 |
| Shared host follows (capped) | +10 each, max 20 |
| Shared favorite categories | +15 |
| Passport complete / both recently active | +5 each |
| Nearby tiers (2/5/10/25 km) | +25 / +20 / +15 / +10 |
| Shared city / area | +10 |
| Similar attended categories / venue / host types / scene | +10–15 |
| Dismiss (expired window) | −30 |
| Recently declined / too many outgoing / low trust / report risk | −15 to −40 |
| More-like-this / click boosts | +5 / +10 patterns via feedback |

**Labels:** Strong ≥80, Good ≥60, Similar ≥40.

### Diversity mixer (mixed mode)

Quotas per page (~12): strong 3, nearby 3, FoF 2, shared event 2, fresh 2 (`DIVERSITY_QUOTA_*`).

### Eligibility / privacy

- Request policies: `same_event`, `same_host`, `public_passports`, `nobody` (multi-select OR)  
- Blocks, reports, admin-hidden passports, connect-off settings, decline cooldown  
- Safe reason codes only — no VIP, spend, private venues, raw GPS in reasons  
- lat/lng query params: **one-shot** matching; not stored from suggestions endpoint  

### Fan Passport directory `/fans`

- API: `GET /fans` → `passport/directory_service.list_directory_passports`  
- Requires `appear_in_directory` + public visibility rules  
- Sort: `recently_active` (default, `updated_at`), `most_events`, `newest`, `most_reviews`, `most_badges` (latter two sorted client-side after filter)  
- **Not** Fan Connect scoring — separate directory  

### Missing / edge cases

- No randomization; candidate cap 120 may miss lower-score good matches  
- Fan Connect graph not used for event/host marketplace (by design)  
- `fan.connect.explanation` AI blocked — no NL rewrite of reasons in prod  

---

## 5. Merch recommendation / marketplace ranking

**Backend:** `backend/app/merch/marketplace.py`, `constants.MARKETPLACE_SORTS`  
**Frontend:** `/merch`, `MarketplaceFilters`

### Eligibility

Active, listed, public visibility; safe host/event linkage; optional Vault/drops filters.

### Sort (server)

| Sort | Order |
|------|--------|
| `featured` (default) | `is_featured DESC`, `created_at DESC` |
| `newest` | `created_at DESC` |
| `price_*` | `base_price`, then `created_at` |
| `popular` | Sum `sold_quantity` DESC, then featured |

### Home rails (`GET /merch/home`)

Featured, event merch, host shops (by product count), drops (`newest`), vault teasers (`featured`) — curated sections, not personalized.

### Personalization

Optional buyer id for **Vault eligibility / serialization only** — does not change catalog order.

### Missing

- “Because you bought / attended” merch rank  
- Co-purchase or same-event bundles ranking  
- Post-event drop surfacing by fan ticket history  

---

## Sponsor campaign ↔ opportunity matching (rules-only)

**APIs:** `GET /sponsors/workspaces/{sponsor_id}/campaigns/{campaign_id}/recommendations`, feedback POST, admin debug on `/admin/sponsor-campaigns/{id}/recommendations/debug`

**Scoring:** Deterministic 0–100 — category/objective (30), location (20), budget (20), host trust/activity (15), event timing (10), sponsor feedback (10). No LLM ranking.

**Privacy:** Fixed safe reason labels only; no fan PII, buyer spend, venue secrets, or internal risk notes.

**Frontend:** `/sponsor/campaigns/[id]` recommended section; `/sponsor/opportunities` campaign sort.

---

## 6. Sponsorship marketplace ranking

**Public APIs:** `GET /sponsorships/public/slots`, `GET /sponsorships/public/hosts`  
**Backend order:** slots → `published_at DESC`; hosts → `open_slots DESC`  
**Frontend:** `filterAndSortSponsorshipSlots` / `filterAndSortSponsorHosts` (`sponsor-slot-presentation.ts`)

### Client “recommended” (slots)

Heuristic: `verified ? 1000 : 0` + min(audience/100, 500) − price/10000.

### Filters

Search haystack, city, category, slot type, budget bucket, audience bucket, host username; hosts: verified-only, featured rail first.

### Admin

Host/slot lifecycle and moderation in host/admin modules; public list excludes non-published/removed.

### Missing

- Brand ↔ host affinity matching  
- Campaign performance-based rank  
- Personalized sponsor dashboard ordering beyond recency  

---

## 7. Search ranking

**No unified global search** (no single index across entities).

| Domain | Route | Matching | Rank |
|--------|-------|----------|------|
| Events | `/events`, `q` param | Substring on title/city/venue fields in BE filter | API sort param + FE sorts |
| Hosts | `/hosts` | Slug lookup form → `/@slug`; directory not full-text ranked | Discover API order |
| Fans | `/fans` | Username/display ILIKE | Directory sort keys |
| Merch | `/merch` | Name/description ILIKE | Marketplace sort |
| Blog | `/blog` | Title/excerpt ILIKE | `published_at DESC` |
| Help | `/help` | Title/excerpt/body/tags | `published_at DESC` or `popular` (views/helpful) |
| Help suggestions | `GET /help/suggestions?topic=` | Topic keyword → articles | KB service ordering |
| 404 recovery | `NotFoundExperience` | Client filter | Events + hosts only |

**Typo handling:** None beyond case-insensitive partial match.  
**Missing:** Unified relevance, fuzzy match, cross-entity rank, search analytics-driven order.

---

## 8. Notification targeting and priority

**Registries:** `notifications/channel_registry.py`, `admin_notifications/registry.py`, `admin_notifications/audience.py`, `admin_notifications/orchestrator.py`

### Channel selection

- Per notification **kind** → in-app / email / push flags + user prefs  
- **Critical** vs marketing classification; marketing requires opt-in  
- Admin broadcasts: audience segments (followers, ticket buyers, geo, roles, etc.) + per-channel gates + **cooldown** (`registry` metadata)

### Priority

- Not a numeric global queue score for fan notifications  
- Support tickets use `low|normal|high|urgent` **filter** but admin list sorts **`created_at DESC`** (not priority-first)

### Push

- Denylist for kinds that must not push; VAPID mode in settings  
- Rate limits via orchestrator cooldowns (admin campaigns)

### Missing

- Fan notification **inbox** priority sort beyond recency  
- Cross-channel dedupe scoring  
- Smart quiet hours (beyond user prefs)

---

## 9. Ambassador / referral scoring

**Click tracking:** `ambassadors/referral_tracking.py` — duplicate 30s suppression; unique window (default 24h) via hashed keys  
**Attribution:** `promos/service.py` — explicit checkout code beats cookie; self-referral blocked; commission on verified payment webhook  
**Fraud:** `ambassadors/fraud.py` + admin flags / notifications  
**Leaderboard:** `promos/campaigns.campaign_leaderboard` — sort **revenue DESC**, then **clicks DESC**, limit 50  

### Missing

- Multi-touch attribution  
- Device graph beyond visitor hash  
- Public ambassador discovery rank (N/A)

---

## 10. Reviews, Legacy, and trust scoring

**Formula:** `legacy/scoring.py` + weights in `legacy/constants.py`  
**Composite 0–100:** verified rating 30%, completed events 15%, tickets sold 15%, verified checkins 15%, refund/dispute 10%, consistency 10%, repeat buyers/followers 5%  
**Tiers:** Hard gates on events/tickets/checkins/reviews/rating per `DEFAULT_TIERS`  
**Collection:** `legacy/service.collect_host_metrics` — **excludes host-owner self** tickets/reviews/follows (`fan_self_abuse`)  
**Decay:** No time decay on Legacy composite today — refresh on recalc  
**Public cards:** Stored `HostLegacyScore` on discover + recommendations trust bonuses  

### Reviews aggregation

Mean rating over visible/published reviews (owner excluded where enforced) — events, merch, memories, analytics.

### Missing trust signals

- Freshness decay on Legacy  
- Check-in fraud weighting in public rank  
- Buyer-verified vs host-claimed signal separation in discovery  

---

## 11. Admin queues and risk ordering

| Queue | Sort today | Priority field | Notes |
|-------|------------|----------------|-------|
| Support | `created_at DESC` | Filter only | `support/service.py` |
| Refunds | `created_at DESC` | Status filters | `finance/service.py` |
| Payouts | `created_at DESC` | — | Finance |
| Message reports | `created_at DESC` | — | Messaging |
| Review reports | `created_at DESC` | — | Reviews |
| Sponsorship admin | Various recency | Moderation status | Host/admin UI |
| Merch moderation | Recency-based lists | — | Attachments/moderation modules |
| Audit log | `created_at DESC` | — | Admin |
| User admin lists | Often name/recency | Account status flags | No unified risk score sort |

### Missing triage

- SLA age escalation in sort key  
- Composite risk score for users/hosts  
- Priority-first support queue (urgent on top)

---

## 12. AI-related discovery safeguards

| Key | Status | Enforcement |
|-----|--------|-------------|
| `discovery.why_recommended` | Blocked / future | `FUTURE_AI_FEATURES`, default off, not allowlisted |
| `fan.connect.explanation` | Blocked / future | Same + safety routing lock |
| `recommend_featured_events` | Quarantined admin | HTTP **403** in `ai/service.generate_suggestion` |
| Legacy host AI slugs | Quarantined | 403, not on allowlist |

**Shipped AI (non-ranking):** host drafts (announcements, merch copy), fan passport bio, support/admin/blog summaries — human-in-loop, no public feed re-order.

**Accidental AI ranking:** None found in production paths; host fan recs and Fan Connect are explicit Python scoring.

---

## Master algorithm table

| Surface | Route / API | Current algorithm | Signals used | Personalization? | Location-aware? | Admin-curated? | Privacy safeguards | Missing signals | Recommended improvement | Priority |
|---------|-------------|-------------------|--------------|------------------|-----------------|----------------|--------------------|-----------------|-------------------------|----------|
| Pàdéyá Picks | `/`, `/events/padeya-picks` | Placement slots → fill trending featured | Slot schedule, featured pool | No | No | Yes | Public events only | Contextual city picks on homepage | Stronger empty-slot policy per city | P2 |
| Homepage featured | `/`, `GET /events?sort=featured` | Featured → soonest + diversify | `Event.featured`, category diversity | No | Optional city seed | Partial (featured flag) | Listed visibility | True trending | Keep editorial; add labeled “Featured” not “Trending” | P2 |
| Homepage nearby | `/`, `GET /events/nearby` | Distance → start → featured → proxies | Geo, coords, ticket proxy | No | Yes | Tie-break only | Discovery-safe coords | Saved home city without GPS | Default city from profile preference | P2 |
| Event marketplace | `/events` | BE publish filter + FE sort; signed-in **Recommended** lane | Featured, start, price, filters + rules rec API | **Yes** (rail/sort) | Near-me optional | Featured + Picks elsewhere | Hides unlisted | — | Tune runtime `event-recommendations` | **Done** |
| Event related | Event detail | Signed-in: rules rec rail; logged-out: host → city → category | Same list pool + rec API | **Yes** (signed-in) | City match | No | Safe reasons | — | Optional server `GET /events/{slug}/related` | P2 |
| Public hosts | `/hosts`, `/legacy/discover/hosts` | Verified → upcoming → check-ins → name | Legacy score fields | No | Client city chips | No | Active + listed events only | Search relevance | Signed-in re-rank optional strip | P2 |
| Host recommendations | `/dashboard`, `/hosts`, `GET /hosts/recommendations` | Weighted rules 0–100 | Tickets, follows, connect graph, geo prefs, dismiss, impressions | **Yes** | Yes | No | Safe reasons, no spend | Impression + feedback wired | Runtime `host-recommendations` + admin debug | **Done** |
| Fan Connect | `/connect`, `GET /fan-connect/suggestions` | Score + mixer | Events, hosts, geo, FoF, feedback | **Yes** | Optional one-shot | No | Policies, blocks, safe reasons | Larger candidate pool | Candidate sampling strategy | P1 |
| Fan directory | `/fans`, `GET /fans` | Sort keys on passport stats | Badges, events, reviews | No | City filter | Opt-in directory | Hidden passports excluded | Interest similarity | Optional “similar fans” (Connect overlap) | P3 |
| Merch marketplace | `/merch`, `GET /merch` | Featured/newest/price/popular | sold_quantity, featured | No | City filter | Featured flag | Public listings | Ticket-linked recs | Same-host / same-event boost | P2 |
| Sponsor slots | `/sponsors` | BE recency + FE heuristic | Verified, audience, price | No | Client filters | Publish workflow | Public slots only | Brand fit | Rules-based brand↔host match | P2 |
| Legacy score | Host public metrics | Weighted composite | Reviews, sales, checkins, refunds | No | No | Tier catalog | Owner self excluded | Decay | Time-decay + recalc job docs | P2 |
| Support queue | `/admin/support` | Newest first | created_at | No | No | Priority labels | RBAC | Priority sort | Sort urgent/high first, then age | P0 |
| AI discovery | — | **Disabled** | — | — | — | — | Quarantine + 403 | — | Do not enable until rules mature | P0 |

*(Table abbreviated for length; sections 1–12 contain full detail.)*

---

## A. Current algorithm inventory

1. **Featured Placement / Pàdéyá Picks** — editorial event slots (`placements/service.py`)  
2. **Public event list filtering & sort** — BE eligibility + FE `filterPublicEvents`  
3. **Nearby events rank** — haversine + tie-breakers (`events/geo.py`)  
4. **Map / calendar event selection** — published + privacy-safe coordinates  
5. **Related events rank (FE)** — `related-discovery.ts`  
6. **Homepage event diversification** — category round-robin  
7. **Public host discover list** — `legacy/discover.py` global sort  
8. **Host featured strip (FE)** — verified + activity heuristic  
9. **Fan host recommendations** — `hosts/recommendations/*` rules engine  
10. **Fan Connect scoring v2** — `fan_connect/scoring.py` + diversity mixer  
11. **Fan Passport directory sorts** — `passport/directory_service.py`  
12. **Merch marketplace sorts** — SQL order in `merch/marketplace.py`  
13. **Sponsorship public lists + FE recommended heuristic**  
14. **Legacy composite trust score** — `legacy/scoring.py`  
15. **Review/means for display** — domain services (events, merch, memories)  
16. **Ambassador leaderboard ordering** — revenue then clicks  
17. **Referral click dedupe / unique windows** — `referral_tracking.py`  
18. **Admin notification audience + cooldown** — orchestrator  
19. **Help/blog search order** — recency or popularity  
20. **Admin queue recency sorts** — support, refunds, reports  

**Not implemented as algorithms:** taxonomy content graph ranks (`city_top_host`, `recommended_next`), unified search relevance, event personalization, merch personalization, AI explanation/ranking keys.

---

## B. Missing algorithm list

- Personalized **event** recommendations (rules-first lane)  
- Personalized **host** recommendations on public `/hosts` (API exists; UI partial)  
- **Merch** recommendations (same event/host/attendance)  
- **Sponsorship** brand↔host matching  
- **Search** relevance ranking (per entity + global)  
- **Homepage** personalized discovery (signed-in)  
- **Notification** priority/inbox scoring  
- **Support/refund** priority queues  
- **Legacy** freshness decay  
- **Graph-based** related content (events/hosts/cities)  
- **True trending** (velocity, not featured alias)  

---

## C. Improvement roadmap

### P0 — safety / correctness

- Support (and similar) queues: **sort by priority then age**, not created_at only  
- Audit any public surface that could expose non-directory fans or private events (eligibility tests)  
- Keep AI discovery keys disabled; gate any new “explain” feature behind rules output  
- Confirm push/critical notifications bypass prefs only where documented  

### P1 — high product value, rules-first

- **Event recommendations** API (mirror host rec pattern: tickets, follows, city, dismiss)  
- **Host recommendations**: tune weights, add impressions, optional signed-in strip on `/hosts`  
- **Fan Connect**: candidate pool strategy, mode-specific caps, documented edge cases  
- **Search**: explicit sort=relevance within each silo (still deterministic)  
- **Related events** server endpoint sharing FE rules  

### P2 — marketplace depth

- Merch: same-host / same-event boost sort  
- Sponsorship: sponsor-ready + category/city match rank  
- Homepage: honest labeling (Featured vs Trending); city-aware Picks  
- Legacy decay + public trust badges tied to formula docs  

### P3 — after rules mature

- **`discovery.why_recommended`** — NL blurbs over existing reason codes only (no re-rank)  
- **`fan.connect.explanation`** — same for Connect  
- Graph-powered adjacency where editorial overrides exist (`TAXONOMY_AND_CONTENT_GRAPH.md`)  

---

## D. Recommended algorithm principles (Pàdéyá)

1. **Rules-first** — explicit weights, thresholds, and reason codes  
2. **Explainable** — every personalized row has human-safe labels  
3. **Deterministic** — same inputs → same order (modulo pagination)  
4. **Privacy-safe** — no spend/VIP/private venue/peers by name in public rank  
5. **Auditable** — constants in code; changes reviewed + tested  
6. **Admin-tunable** — editorial placements override algorithm fills  
7. **No AI ranking** until rules systems and CRUD/docs are complete  
8. **Separate concerns** — Fan Connect graph ≠ host marketplace ≠ event lists  

---

## E. References (primary code)

| Area | Path |
|------|------|
| Events list / filter | `backend/app/events/service.py`, `frontend/src/lib/discovery/event-filters.ts` |
| Nearby | `backend/app/events/geo.py` |
| Picks | `backend/app/placements/service.py`, `frontend/src/lib/discovery/padeya-picks.ts` |
| Host discover | `backend/app/legacy/discover.py`, `frontend/src/components/hosts/HostsMarketplace.tsx` |
| Host recs | `backend/app/hosts/recommendations/` |
| Fan Connect | `backend/app/fan_connect/constants.py`, `scoring.py`, `service.py`, `diversity.py` |
| Fan directory | `backend/app/passport/directory_service.py` |
| Merch | `backend/app/merch/marketplace.py` |
| Sponsors | `backend/app/sponsorships/service.py`, `frontend/src/lib/sponsor-slot-presentation.ts` |
| Legacy trust | `backend/app/legacy/scoring.py`, `legacy/service.py` |
| AI guards | `backend/app/ai/constants.py`, `ai/service.py`, `ai/feature_status.py` |
| Notifications | `backend/app/admin_notifications/orchestrator.py`, `notifications/channel_registry.py` |
| Ambassadors | `backend/app/ambassadors/referral_tracking.py`, `backend/app/promos/campaigns.py` |

---

## Files created/changed (this audit)

| File | Action |
|------|--------|
| `docs/CURRENT_ALGORITHMS_AUDIT.md` | **Created** (this document) |

No application code, migrations, or ranking behavior was modified.
