# Analytics privacy

**Brand:** Pàdéyá  
**Scope:** first-party product analytics only  
**Last updated:** 2026-07-17

This document defines what Pàdéyá analytics may collect, store, and show — especially to **hosts**. It matches the scrubbing and access rules in `backend/app/analytics/dimensions.py`, track writers, and host/admin report builders.

Related docs:

| Doc | Topic |
|---|---|
| [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md) | Taxonomy, endpoints, FE wiring, host/admin dashboards, rollups |
| [ANALYTICS_ROLLUPS.md](./ANALYTICS_ROLLUPS.md) | Rollup CLI / cron / Docker |
| [API.md](./API.md) | Authz on analytics routes |
| [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) | `/host/.../analytics`, `/admin/.../analytics` |
| [SECURITY.md](./SECURITY.md) | Broader security |
| [COOKIES_AND_STORAGE.md](./COOKIES_AND_STORAGE.md) | Browser storage keys for analytics ids / queue |

---

## Principles

1. **First-party only** — do not send analytics to GA, Mixpanel, Segment, Meta Pixel, or similar in this product phase.
2. **Commerce truth is not client analytics** — payment success, ticket issuance, check-in, and refunds come from trusted server paths, not the browser.
3. **Hosts see aggregates** — counts, rates, and coarse dimensions for *their* events. Not raw visitor dumps or buyer contact lists via analytics APIs.
4. **No sensitive payloads in the stream** — scrub on write; never rely on “clients won’t send it.”
5. **Append-only stream** — analytics rows are not updated/deleted in normal product flows; privacy deletion is a future ops path (see below).

---

## What is tracked

### Product actions (taxonomy)

Funnel and engagement signals such as:

- Discovery: card/featured impressions and clicks, list/search/filter usage  
- Detail: event page views, shares, save/follow clicks, gallery, policy views  
- Ticket intent: panel/type impressions, type selected, checkout start  
- Checkout: page/step/payment started, abandoned (client); **payment success / failed / ticket issued** (trusted server only)  
- Post-purchase: ticket view/download (client); **check-in success**, **review submitted** (trusted)  
- Limited vault/legacy/sponsor surface clicks where wired  

Exact action names live in `app.analytics.taxonomy.TrackedAction` — full funnel groups in [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md) §2.

### Attribution & coarse context

- UTM / source / medium / campaign / term / content  
- Referrer, landing page, path  
- Coarse geo hints: **country**, **city** (never street address)  
- Device class: device type, browser, OS  
- Optional `environment` / `app_version`  

### Opaque visitor keys

- `anonymous_id` — client-generated opaque id for logged-out continuity  
- `session_id` — short-lived browsing session key  
- `user_id` — set only when the visitor is authenticated (UUID FK); not an email  
- Ambassador **referral landings** reuse `anonymous_id` when logged out to compute **unique clicks** (24h window); hosts never receive `visitor_hash`, raw IP, or UA. Canonical rows: `referral_clicks` via `ReferralTrackingService` ([AMBASSADORS.md](./AMBASSADORS.md)).  
- `request_id` — idempotency / dedupe key  

### Hashed network / UA signals

- `ip_hash` — one-way hash of the edge IP (see [IP hashing](#ip-hashing))  
- `user_agent_hash` — one-way hash of UA string  
- Truncated UA may be stored for bot/device parsing; prefer hash for long-term joins  

### Allowed metadata examples

Allowlisted keys only (e.g. `ticket_type_id`, `promo_code`, `ambassador_code`, `order_id`, `list_context`, `share_channel`, quantity/amount on **trusted** writes). Client revenue inflation keys are stripped.

### Quality flags

- `is_bot` — marked when UA / heuristics look automated  
- Host dashboards and rollups **exclude bots by default**  

---

## What is not tracked

Do **not** put these in analytics metadata, properties, or client track payloads:

| Category | Examples |
|---|---|
| Payment instruments | Card number/PAN, CVV/CVC, expiry, bank account, BVN, NIN |
| Auth secrets | Passwords, tokens, authorization headers |
| Contact PII | Email, phone, full name |
| Precise location | Street address, private/hidden venue address, exact GPS |
| Private venue access | Hidden venue rules, invite-only join URLs, online event join links |
| Raw network identity | Raw IP address (clients must not send; server stores hash only) |
| Free-text private content | Private messages, government ID images, medical data |

Implementation: `FORBIDDEN_METADATA_KEYS` + allowlist scrubbing in `scrub_metadata()`. Nested objects/lists from clients are dropped.

**Payment amounts and ticket counts** on purchase outcomes are recorded only via **trusted server emitters** after verified commerce events — not as client-asserted “I paid.”

---

## No raw card / payment data

- Analytics never stores card PANs, CVVs, or full gateway raw payloads.  
- Trusted rows may reference `order_id` / `payment_reference` and aggregate amounts already known from the payments domain.  
- Host analytics show **order/ticket aggregates and revenue totals**, not card brands, last4 dumps, or processor chargeback files.  
- Clients cannot set forbidden revenue metadata keys to inflate dashboards.

---

## No private venue leakage

- Event analytics may record that someone viewed venue-related UI (`venue_reveal_info_view`) as a **count**.  
- Analytics must **not** store or return: private/hidden addresses, reveal rules, door codes, or online join URLs.  
- Keys such as `venue_address`, `private_address`, `hidden_address`, `online_event_url`, `join_url` are scrubbed on write.  
- Hosts already manage venue privacy in the events domain; analytics must not become a second channel that leaks reveal-gated details.

---

## `anonymous_id` and `session_id`

| Field | Purpose | Privacy note |
|---|---|---|
| `anonymous_id` | Stable-ish client id for unique visitors when logged out | Opaque string (max 64). Not an email or phone. Rotatable by clearing client storage. |
| `session_id` | Groups actions in one browsing session | Short-lived; used for dedupe (e.g. impressions) and unique counts. |
| `user_id` | Links actions to an account when logged in | UUID only in the stream. Host analytics APIs must not expand this to email/phone. |

Unique-visitor math prefers `user_id` → `anonymous_id` → `session_id` (see `visitor_identity()`). These keys support aggregation; they are not a license to build host-facing buyer directories from the analytics module.

---

## IP hashing

- Raw client IPs are **not** stored in analytics tables.  
- When the edge provides an IP, the server may set `ip_hash = SHA-256(secret_key | ip)` (first `X-Forwarded-For` hop), truncated to 64 hex chars (`hash_ip()`).  
- Hashing is one-way for analytics purposes; do not expose `ip_hash` on host dashboards.  
- Clients must not send `ip` / `raw_ip` / `ip_address` in metadata (forbidden keys).  
- Coarse **city/country** may be stored as separate dimensions when available; that is not a substitute for storing street-level location.

---

## Host-visible aggregation only

Host analytics (`/api/v1/host/...` and host event analytics routes) are limited to the host’s own events and should expose:

- Funnel counts and conversion rates  
- Time series and source/campaign breakdowns  
- Ticket-type performance  
- Audience **buckets** (device, city, new vs returning, logged-in vs anonymous) as **counts**  
- Promo / ambassador performance as aggregates  

### Host analytics must not expose

- Full buyer **emails**  
- Full **phone** numbers  
- Other private personal data (government IDs, exact home addresses, etc.)  
- **Hidden venue** addresses or reveal rules  
- **Raw IPs** (or host-facing `ip_hash` lists)  
- Raw append-only stream dumps of individual visitors for browsing  

Buyer CRM, ticket lists, and check-in tools are separate product surfaces with their own authz. Analytics dashboards are not a back door into those datasets.

**Host UI:** `/host/analytics` (portfolio), `/host/events/[id]/analytics` (per-event funnel/sources/tickets/audience).

---

## Admin access boundaries

| Capability | Host | Platform admin |
|---|---|---|
| Own-event funnel / sources / tickets | Yes | Yes (any event) |
| Cross-event leaderboard / compare / channels | No | Yes |
| Platform revenue summaries | No | Yes |
| `include_bots=true` on reports | No (rejected unless platform analytics role) | Yes |
| Raw payment instrument data | No | No (not in analytics) |

Admins still must not use analytics as a store of card data or private venue secrets. Broader admin tools (support, finance) remain governed by role permissions and audit logs outside this doc.

**Admin UI:** `/admin/analytics/*`, `/admin/events/[id]/analytics`.

---

## Bot filtering

- Likely bots are flagged with `is_bot=true` (UA heuristics; optional client hint).  
- Host and default admin event reports **exclude** bots.  
- Daily rollups exclude bots.  
- Admins may pass `include_bots=true` for quality investigation.  
- Bot traffic may still be written to the stream for ops visibility; it must not inflate host conversion KPIs by default.

---

## Retention recommendation

Recommended starting policy (ops can tighten):

| Store | Recommendation |
|---|---|
| Raw `analytics_events` (+ legacy impression/click tables) | **13 months** hot, then archive or delete |
| Daily rollup tables | **24–36 months** (aggregates; lower privacy risk) |
| Dedupe keys | TTL aligned with dedupe windows + short buffer (days–weeks) |
| Exports / CSV downloads | Treat as sensitive; do not retain on laptops; expire signed download links quickly |

Until automated retention jobs exist, treat the above as the target policy and avoid unbounded growth of raw stream copies in non-production dumps shared outside the team.

---

## User deletion / anonymization (future)

**Status:** not fully automated in the analytics module yet.

When account deletion or privacy erasure is implemented, analytics should:

1. Null or unlink `user_id` on historical stream rows for that account.  
2. Rotate or clear `anonymous_id` / `session_id` values that can be tied to the user via product logs (best-effort).  
3. Leave **non-identifying aggregates** (rollups, daily totals) intact where they cannot reasonably identify the person.  
4. Never restore scrubbed PII into the stream as part of “repair” jobs.  

Until that pipeline ships, treat analytics `user_id` as operational linkage only, and do not build host UI that reveals account contact fields from analytics joins.

---

## Implementation map

| Concern | Code / surface |
|---|---|
| Forbidden + allowlisted metadata | `app.analytics.dimensions.FORBIDDEN_METADATA_KEYS`, `scrub_metadata` |
| IP / UA hashing | `hash_ip`, `hash_user_agent` |
| Bot detection | `is_likely_bot`, `AnalyticsEvent.is_bot` |
| Trusted commerce signals | `app.analytics.trusted` |
| Host vs admin reports | `app.analytics.service`, host/admin event routers |
| Rollups exclude bots | `app.analytics.rollups` |

---

## Checklist for new analytics features

- [ ] Action is in the taxonomy; trusted actions are server-only if money/tickets are involved.  
- [ ] No new metadata keys that store email, phone, card, address, or join URLs.  
- [ ] Host API responses stay aggregate; no PII columns “for convenience.”  
- [ ] Bots excluded from host KPIs by default.  
- [ ] Docs updated if retention or deletion behavior changes.  
