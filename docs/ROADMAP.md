# Roadmap

## Phase 1 — Foundation
- [x] Brand, Docker, modular API, docs

## Phase 2 — Identity
- [x] Auth, RBAC, audit base

## Phase 3 — Hosts & events
- [x] Host onboarding, events, approval, ticket types
- [x] Event Studio (10-step create/edit): taxonomy/location, privacy, agenda/people, media, questions, policies, SEO, publish checklist
- [x] Location privacy serializers + buyer reveal after payment; SEO scrub of hidden addresses
- [x] Subresource lifecycle: agenda/people upsert-by-id; checkout questions archive-when-answered; media DELETE; ticket deactivate vs delete
- [x] Studio tests: `test_event_studio_lifecycle.py` + `npm run test:studio`

## Phase 4 — Commerce

- [x] Event-linked merchandise (Phase 1 — **shipped**): event catalog, variants/inventory, checkout add-ons, buyer dashboard, host fulfillment, admin moderation, demo data — plus notifications, messaging context, analytics, API aliases. Do not rebuild. See [MERCHANDISE.md](./MERCHANDISE.md) · [MERCH.md](./MERCH.md)
- [x] Merch commerce expansion (shipping, host storefront, bundles, merch discounts, merch QR pickup, stock alerts, size charts, reviews, sponsor fields, POD manual jobs, revenue splits, abandoned cart, post-event drops, Vault-exclusive teasers, Passport merch badges) — see [COMMERCE.md](./COMMERCE.md). Live Printful/Printify sync remains future.
- [x] Orders, Paystack, webhook ticket issuance, signed QR

## Phase 5 — Check-in
- [x] Scanner sessions, QR validation, staff, logs, stats

## Phase 6 — Legacy Page & verified reviews
- [x] Public `/@{username}` Legacy Page
- [x] Verified reviews + moderation

## Phase 7 — Legacy tiers
- [x] Named tiers + weighted score + admin thresholds

## Legacy Content Studio (Phase 1)
- [x] `host_legacy_pages` / content blocks / featured items / social + contact settings
- [x] Host Studio: `/host/legacy`, edit, content, preview, tier
- [x] Public renderer driven by visible blocks + defaults
- [x] Vault/review privacy rules on public Legacy
- [ ] Phase 2: richer gallery / video / FAQ editors, sponsor inquiry from Legacy, follower proof widgets

## Phase 8 — Promos & ambassadors
- [x] Host promo codes (%, fixed, limits, expiry, restrictions)
- [x] Server-side checkout discount validation
- [x] Ambassador referral links (`?ref=`)
- [x] Click tracking + sales attribution
- [x] Host + ambassador dashboards

## Phase 9 — Host CRM & audience
- [x] Host followers + marketing opt-in (default off)
- [x] Audience segments (buyers, VIP, check-in, promo/referral; superfans/Vault placeholders)
- [x] Announcements + recipients; email via log abstraction; WhatsApp export only
- [x] Host audience / followers / announcements UI + `/dashboard/following`
- [x] Fan Passport loyalty / badges (Phase 12)
- [x] Event Memories (Phase 13)
- [x] AI Copilot foundation (Phase 15)
- [ ] Deeper AI / loyalty scoring (deferred)

## Phase 10 — Finance ops
- [x] Refund requests + admin/finance review (full refund; partial placeholder)
- [x] Ticket invalidation + QR revoke on refund
- [x] Host balances + append-only ledger
- [x] Payout requests + finance review
- [x] Super-admin mark-as-paid with immutable evidence
- [x] Support escalate-only; cannot edit financial records
- [x] Basic settlement report

## Phase 11 — The Vault
- Vault = exclusive host content fans unlock by follow, ticket, attendance, VIP, invite, or one-time purchase ([VAULT.md](./VAULT.md))
- [x] Vault items + media via storage abstraction
- [x] Vault Content Studio (multi-step create: content → media → access → related → publish; fan preview; Legacy feature)
- [x] Access rules: free, followers, ticket-holder, checked-in, VIP, one-time unlock, invite, admin-hidden
- [x] Public `/@{username}/vault` + item pages with locked/unlocked redaction
- [x] Legacy `vault_preview` teasers only (no locked body/media leak)
- [x] Related Vault teasers on event detail + Event Memory
- [x] Paystack unlock (`PDY-VLT-*`) + idempotent grants + host earnings (`vault_sale`); never issues tickets
- [x] Buyer library `/dashboard/vault` + purchase poll after Paystack return
- [x] Admin moderation (filters, hide/archive/restore with reason; support lacks `vault.moderate` by default)
- [x] Vault analytics funnel (`vault_page_view`, item impression/click/view, unlock_*, media/download)
- [x] Docs + backend checklist tests + FE `npm run test:vault`
- [ ] Subscriptions unlock Vault content (deferred)
- [ ] Invite-only deep-link grant tokens (deferred; code redeem + manual grant work today)

## Messaging (in-app inbox)
- [x] Fan ↔ host threads (HTTP + polling unread)
- [x] Message requests, block, report, admin moderation
- [x] Public Message Host / Ask host CTAs + Host Message Fan (relationship-gated)
- [x] Fan/host message settings screens + `blocked_users` on settings API
- [x] Rich inbox UI (avatars, event chips, unread/request/archived/blocked/reported badges)
- [x] Demo messaging seed + privacy guard + `/demo` one-click inbox shortcuts
- [x] Docs: [MESSAGING.md](./MESSAGING.md), [DEMO_DATA.md](./DEMO_DATA.md), [PRIVACY.md](./PRIVACY.md); backend `test_demo_messaging_privacy.py`
- [ ] WebSockets / typing / attachments (deferred)

## Phase 12 — Fan Passport
- [x] `fan_passports` + auto-create for buyers
- [x] Attendance from checked-in tickets (exclude cancelled/refunded)
- [x] Tickets bought, hosts followed, VIP history, upcoming tickets
- [x] Host loyalty records + Superfan status
- [x] Deterministic badge catalog + awards
- [x] Vault access summary when Vault purchases exist
- [x] `/dashboard/passport` + `/dashboard/badges`
- [x] Privacy settings (private / unlisted / public) + profile fields
- [x] Public Fan Passport `/f/[username]` with privacy-safe activity
- [x] `/dashboard/passport/settings`
- [x] Fan Passport Directory `/fans` (opt-in `appear_in_directory` only)
- [x] Admin Fan Passport moderation (`/admin/fans` hide/restore)

## Phase 13 — Event Memories
- [x] `event_memories` + `event_memory_media`
- [x] Auto-create memory on event completion
- [x] Public `/@{username}/memories/[eventSlug]` for completed events
- [x] Verified attendance stats, rating, top reviews
- [x] Host recap note + gallery upload abstraction
- [x] Upcoming event CTA + Legacy Page links
- [x] Host edit pages + admin hide moderation

## Phase 14 — Advanced analytics
- [x] Tracking tables: analytics_events, page_views, impressions, clicks, conversions
- [x] Taxonomy (`TrackedAction`) + trusted server emitters (payment/ticket/check-in/review)
- [x] Unified `/analytics/track` + `/track/batch` (reject unknown + trusted client spoofing)
- [x] Session / UTM / device / geo dimensions + metadata privacy scrub
- [x] Impression / detail-view dedupe
- [x] Aggregation helpers for host + admin dashboards
- [x] Host portfolio analytics (sales, check-ins, promos, ambassadors, Vault, Legacy trend)
- [x] Host per-event analytics APIs + `/host/events/[id]/analytics` dashboard
- [x] Admin analytics (GMV, fees placeholder, refunds, payouts, trends, support proxy)
- [x] Admin per-event + leaderboard / compare / channels (`/admin/events/[id]/analytics`, `/admin/analytics/events`)
- [x] CSV exports (permission-protected)
- [x] Frontend instrumentation (AnalyticsProvider, EventCard, detail, checkout)
- [x] Daily rollups + `python -m scripts.run_analytics_rollups` CLI
- [x] Demo 90-day analytics seed + privacy/API docs
- [x] `/host/analytics`, `/host/events/[id]/analytics`, `/admin/analytics/*`, `/admin/events/[id]/analytics`

## Phase 15 — AI Copilot foundation
- [x] Provider abstraction + env settings (`AI_*`)
- [x] Prompt templates + usage logs
- [x] Host Copilot (titles, copy, pricing, promos, performance, Legacy, recap drafts)
- [x] Admin Copilot (support/reviews/revenue summaries; risk placeholders)
- [x] Safe fallback when AI disabled/unavailable
- [x] Rate-limit placeholder + human-confirmation flags
- [x] `/host/ai`, `/host/events/[id]/ai`, `/admin/ai`, `/admin/support/ai-summary`
- AI never publishes, sends announcements, or writes finance

## Phase 16 — Sponsorship marketplace
- [x] Sponsors, slots, inquiries, placements, analytics models
- [x] Host settings + slot create/publish (verified hosts only)
- [x] Public marketplace + inquiry form
- [x] Admin moderation (disable/remove listings)
- [x] Host inquiry management + placement analytics counters
- [x] `/sponsors`, `/sponsors/hosts`, `/host/sponsorships`, `/admin/sponsorships`
- Isolated from core ticketing/payments/Vault checkout

## Phase 17 — Advanced ticketing
- [x] Ticket transfer + transfer history / audit
- [x] Group tickets → multiple attendee entries (`seats_per_unit`)
- [x] Table tickets + table/seat assignment placeholder
- [x] Rotating QR foundation (short-lived signed tokens)
- [x] Device-bound ticket placeholder
- [x] Offline scanner local buffer + sync with conflict detection
- [x] Ticket cancellation workflow (QR revoke; fails validation)
- [x] `/dashboard/tickets/[id]/transfer`, `/host/events/[id]/tables`, `/host/events/[id]/offline-check-in`, `/admin/tickets`
- Existing payment / single-ticket / live check-in flows unchanged

## Phase 18 — Mobile-first & PWA (current)
- [x] Web app manifest + app icons + install prompt
- [x] Service worker (shell/assets only; never Vault/API/checkout/auth)
- [x] Buyer mobile bottom navigation
- [x] Host/staff quick scanner dock
- [x] Offline ticket display cache (validation remains server-side)
- [x] Offline scanner queue → Phase 17 sync API
- [x] Mobile checkout sticky pay bar + larger ticket QR
- [x] Push notification placeholder (no permission prompt yet)
- [x] `/offline` graceful fallback
- Not a native mobile app

## Phase 19 — Taxonomy, discovery & content graph (current)

- [x] Controlled vocab tables + locations + link tables + `content_relationships` (`20260717_0023`)
- [x] Dual-write `events.primary_category_id` / `location_id` with legacy category/city
- [x] Location hierarchy seed: Nigeria → Lagos/Oyo/Ondo/FCT → cities → Lagos areas
- [x] Public discovery hubs: `/events`, `/events/location`, country / state / city / area (+ state×category, city×category), weekend / free / vip / near-me
- [x] Faceted filters + `GET /events` query params (`q`, `category`, `city`, `location_kind`, `location_slug`, `weekend`, `paid`, `sort`, …)
- [x] Location privacy modes (`full_public` … `online_only`) on public serializers + FE labels
- [x] Featured Placement Slots / Pàdéyá Picks (`featured_placements`, migrations `0024`–`0027`, incl. `area_page`)
- [x] Admin `/admin/featured-placements` + public `GET /events/padeya-picks`; FE `resolvePadeyaPicks` fallback
- [x] Related locations from taxonomy children/siblings/parent (not Lagos-hardcoded primary)
- [x] Event breadcrumbs from `location_id` ancestry; sitemap country/state/city/area hubs
- [x] Analytics: `location_filter_used`, location `*_page_view`, `padeya_pick_*`, `featured_placement_*`
- [x] Related rails (host / category / city); omit empty sections
- [x] Marketplace breadcrumbs + event `generateMetadata` / JSON-LD
- [x] `sitemap.ts` + `robots.ts` (listed-only events; dashboards disallowed)
- [x] Admin taxonomy console `/admin/taxonomy/*` (archive/restore; hard delete blocked)
- [x] Event Studio discoverability + SEO preview; host settings taxonomy
- [x] Event Studio full field surface + location privacy + publish checklist (client `preview_checked`)
- [x] Demo taxonomy + placement seed + `tests/test_taxonomy.py` / `test_placements.py` / `test_event_studio_lifecycle.py` + `npm run test:taxonomy` / `test:discovery` / `test:studio`
- [x] Docs: [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md), [SEO.md](./SEO.md), API / DATABASE / FRONTEND_ROUTES / CRUD_* / SECURITY / analytics plan updates

## Later
- Deeper AI recommendations / richer provider integrations
- Deeper support tooling · live provider refund/payout APIs · partial refunds
- Sponsor checkout / paid placement automation
- Enforce device-bound tickets at door · richer seating charts
- Real push notification backend + native apps
- Taxonomy Wave 4–6: tag/vibe/host-type hubs, graph scoring job, venue catalog + cutover off flat hashtags/`events.city` as discovery source of truth
- Per-location editorial imagery / CMS fields; near-me geolocation
- Admin tree editor for locations (drag-sort, redirects)
- Merch live POD provider sync (Printful/Printify) — **future**; provider interface + manual jobs **shipped** ([COMMERCE.md](./COMMERCE.md))
- Merch live carrier label / tracking APIs — **future**; host manual tracking **shipped**
- Buyer multi-channel stock-alert preferences — **future**; host persisted `merch_stock_alerts` **shipped**
