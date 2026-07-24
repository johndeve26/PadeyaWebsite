# Pàdéyá analytics tracking plan

**Status:** shipped (first-party event analytics)  
**Brand:** Pàdéyá  
**Scope:** first-party internal analytics only (no third-party SDKs)  
**Last updated:** 2026-07-17

This document is the product reference for Pàdéyá **per-event** analytics: taxonomy, APIs, frontend instrumentation, rollups, host/admin dashboards, and privacy boundaries — without changing payment/ticket/check-in commerce rules.

**Also see**

| Doc | Topic |
|---|---|
| [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md) | What is tracked / not tracked; host vs admin visibility |
| [ANALYTICS_ROLLUPS.md](./ANALYTICS_ROLLUPS.md) | Daily rollup job, cron, Docker |
| [API.md](./API.md) | Endpoint tables |
| [DATABASE.md](./DATABASE.md) | Stream + rollup tables |
| [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) | Dashboard routes |

---

## 1. Principles (non-negotiable)

1. **First-party only** — store and aggregate inside Pàdéyá. Do not send analytics to GA, Mixpanel, Segment, Meta Pixel, etc.
2. **Do not break commerce** — payment success, ticket issuance, and check-in stay in orders / webhooks / tickets.
3. **Trusted vs untrusted** — money and ticket outcomes come from the backend. The browser must not be the sole source of payment success.
4. **No sensitive PII in analytics** — no passwords, card data, government IDs, exact street addresses, phones, or private messages in metadata.
5. **Append-only stream** — analytics rows are not updated/deleted in normal product flows.
6. **Aggregate for hosts/admins** — counts, rates, and coarse dimensions — not raw visitor identity dumps.

---

## 2. Event tracking taxonomy

Canonical names: `backend/app/analytics/taxonomy.py` (`TrackedAction`).  
Frontend mirror: `frontend/src/lib/analytics-taxonomy.ts`.

| Funnel group | Actions | Trust |
|---|---|---|
| **Discovery** | `event_card_impression`, `event_card_click`, `event_list_view`, `event_search_performed`, `category_filter_used`, `city_filter_used`, `location_filter_used`, `country_page_view`, `state_page_view`, `city_page_view`, `area_page_view`, `featured_event_impression`, `featured_event_click`, `padeya_pick_impression`, `padeya_pick_click`, `featured_placement_impression`, `featured_placement_click` | Client |
| **Detail** | `event_detail_view`, `event_gallery_view`, `event_share_click`, `host_profile_click_from_event`, `legacy_page_click_from_event`, `save_event_click`, `follow_host_click_from_event`, `refund_policy_view`, `venue_reveal_info_view` | Client |
| **Ticket intent** | `ticket_panel_view`, `ticket_type_impression`, `ticket_type_selected`, `ticket_quantity_changed`, `checkout_start_click`, `promo_code_entered`, `promo_code_applied`, `promo_code_failed`, `ambassador_referral_detected` | Client / either |
| **Checkout (client)** | `checkout_page_view`, `checkout_step_started`, `checkout_payment_started`, `checkout_abandoned` | Client |
| **Checkout (trusted)** | `payment_success`, `payment_failed`, `ticket_issued` | **Server only** |
| **Event merch (client)** | `merch_section_viewed`, `merch_product_viewed`, `merch_variant_selected`, `merch_added_to_checkout`, `merch_removed_from_checkout`, `merch_checkout_started`, `merch_pickup_viewed` | Client |
| **Event merch (trusted)** | `merch_payment_confirmed`, `merch_purchase_completed`, `merch_marked_picked_up`, `merch_sold_out`, `host_merch_product_created`, `host_merch_product_updated`, `host_merch_product_paused`, `admin_merch_hidden` | **Server only** |
| **Post-purchase** | `ticket_viewed`, `ticket_downloaded`, `ticket_transfer_*`, `buyer_tickets_page_view`, `ticket_tab_changed`, `ticket_group_expanded`, `ticket_qr_clicked`, `ticket_details_clicked`, `ticket_event_clicked`, `review_prompt_viewed`; trusted: `checkin_success`, `review_submitted` | Mixed |
| **Vault / Legacy** | `vault_page_view`, `vault_item_impression`, `vault_item_click`, `vault_item_view`, `vault_unlock_click`, `vault_unlock_success`, `vault_unlock_failed`, `vault_follow_unlock`, `vault_ticket_unlock`, `vault_media_open`, `vault_download_click`, `vault_preview_click_from_event`, `legacy_page_view_from_event`, `host_followed_from_event` | Client / either (`vault_unlock_success` either; `vault_purchase` trusted only) |
| **Sponsorship** | `sponsor_slot_click_from_event`, `sponsor_inquiry_from_event` | Client / either |
| **Commerce / finance** | `refund_approved`, `vault_purchase`, `promo_redemption`, `ambassador_sale`, `payout_completed` | **Server only** |

### Location & placement discovery signals

| Action | When | Metadata (scrubbed allowlist) |
|---|---|---|
| `location_filter_used` | Cascade / popular chip in `LocationFilterBar` | `country`, `state`, `city`, `area`, `category` |
| `country_page_view` / `state_page_view` / `city_page_view` / `area_page_view` | Location landing mount (`LocationPageViewTracker`) | Same location dims; rolls into `page_views` |
| `padeya_pick_impression` / `padeya_pick_click` | Pàdéyá Picks cards | `placement_context`, `slot_number` (1\|2), `event_id` + location dims → `event_impressions` / `event_clicks` |
| `featured_placement_impression` / `featured_placement_click` | Emitted **with** pick events when the card came from an admin placement (not FE fallback) | Same as pick |

Helpers: `trackLocationFilterUsed`, `trackLocationPageView`, `trackPadeyaPickImpression`, `trackPadeyaPickClick` in `frontend/src/lib/analytics.ts`.  
Registered in both `backend/app/analytics/taxonomy.py` and `frontend/src/lib/analytics-taxonomy.ts` (including `COUNTRY`/`STATE`/`CITY`/`AREA_PAGE_VIEW`, `PADEYA_PICK_*`, `FEATURED_PLACEMENT_*`). Metadata dims `country`/`state`/`city`/`area`/`placement_context`/`slot_number` are allowlisted in `dimensions.py`.  
`featured_event_*` remains the older featured-flag listing signal — distinct from Pàdéyá Picks / Featured Placement Slots.

### Messaging signals

| Action | When | Trust |
|---|---|---|
| `message_cta_clicked` | Message Host / Ask host CTA | Client |
| `host_message_fan_clicked` | Host Message Fan / audience Message | Client |
| `message_thread_created` / `message_sent` / `message_read` | Optional client helpers | Client |
| `message_blocked_user` / `message_reported` | Safety actions | Client |

**Never** send message body text in analytics payloads.

### Fan Connect signals

Product context: [FAN_CONNECT.md](./FAN_CONNECT.md). Opt-in fan↔fan only — never private attendance, hidden venues, ticket types, order/payment IDs, spend, phone/email, shipping, locked Vault content, or **message bodies**.

| Action | When | Trust |
|---|---|---|
| `fan_connect_page_view` | `/connect` · `/connect/settings` (and related Connect surfaces) | Client |
| `fan_connect_settings_updated` | Settings save / disable CTA | Client |
| `fan_connect_suggestion_impression` / `_clicked` | Suggestion card visibility / Connect or Passport click | Client |
| `fan_connect_enabled` / `_disabled` | Settings transition or admin soft-disable | Trusted |
| `fan_connect_request_sent` / `_accepted` / `_declined` | Request lifecycle | Trusted |
| `fan_connect_connection_removed` | Remove connection | Trusted |
| `fan_connect_blocked` / `_reported` | Safety actions | Trusted |
| `fan_fan_message_thread_created` / `fan_fan_message_sent` | Accept creates thread · fan↔fan send | Trusted |

Safe metadata only: `connection_id`, `thread_id`, `username` / `counterpart_username`, `score_band`, `cta_state`, `reason_code_count` (counts — not unsafe labels), `request_policy`, `fan_connect_enabled`, `page_section`, `list_context`, `path` (+ public `target_event_id` only when already a shared public event).

**Never in Fan Connect analytics:** private event IDs/attendance, hidden venues, ticket type / VIP/table, order/payment refs, spend amounts, phone/email, shipping, locked Vault URLs/bodies, or message text.

Helpers: `trackFanConnect*` in `frontend/src/lib/analytics.ts`; emitters in `backend/app/fan_connect/analytics.py`.

### Event merch signals

Product context: [MERCHANDISE.md](./MERCHANDISE.md) · [COMMERCE.md](./COMMERCE.md).

Commerce expansion (storefront, bundles, discounts, QR, stock alerts, size charts, reviews, sponsor, POD, revenue, abandoned cart, drops, Vault-exclusive, Passport badges) reuses this taxonomy — there are **no** separate `merch_storefront_*` / `merch_cart_*` / `admin_merch_revenue_*` event names in code today.

| Action | When | Trust |
|---|---|---|
| `merch_section_viewed` | Event page merch panel with sellable products (`EventMerchSection`) | Client |
| `merch_product_viewed` / `merch_variant_selected` | Merch detail / variant change (`EventMerchDetail`) | Client |
| `merch_added_to_checkout` / `merch_removed_from_checkout` | Checkout qty 0→N / N→0 | Client |
| `merch_checkout_started` | Pay started with merch in cart | Client |
| `merch_pickup_viewed` | Buyer `/dashboard/merchandise` | Client |
| `merch_payment_confirmed` / `merch_purchase_completed` | Webhook finalize with merch fulfillments | Trusted |
| `merch_marked_picked_up` / `merch_sold_out` | Desk pickup / inventory hits zero | Trusted |
| `host_merch_product_created` / `host_merch_product_updated` / `host_merch_product_paused` | Host catalog mutations | Trusted |
| `admin_merch_hidden` | Admin hide | Trusted |

Metadata allowlist: `merch_product_id`, `merch_variant_id`, `merch_item_count`, `fulfillment_id`, `product_status`, `moderation_status` (+ shared `order_id`, `quantity`).

**Never track (merch / commerce):**

- Shipping street, phone, delivery notes, or full address
- Buyer email / phone / private account fields
- Payment secrets, Paystack refs, card data, amounts / spend / conversion_value from the client
- Locked Vault body, media URLs, invite codes
- Hidden / private venue streets
- Desk-only `fulfillment_notes`
- Discount code strings as free-text PII (ids only if needed later — not in current allowlist)
- Badge meta beyond safe criteria keys (no order IDs)

Helpers: `trackMerch*` in `frontend/src/lib/analytics.ts`; emitters in `backend/app/analytics/trusted.py`.

### Fan Passport Directory signals

Product context: [FAN_PASSPORT.md](./FAN_PASSPORT.md). Track discovery of **opt-in public** Passports only — never email, order, or payment fields.

| Action | When | Trust |
|---|---|---|
| `fan_directory_view` | `/fans` mount | Client |
| `fan_directory_search` | Directory search submit | Client |
| `fan_directory_filter_used` | City / category / sort / reviews filter | Client |
| `fan_card_impression` / `fan_card_click` | Directory card visibility / View Passport | Client |
| `fan_passport_view` | Public `/f/{username}` mount | Client |
| `fan_directory_opt_in` / `fan_directory_opt_out` | Settings directory toggle change | Client |

**Metadata allowlist extras:** `username`, `q_length`, `filter_type`, `filter_value` (plus existing `page_section` / `list_context` / `click_target`). Do not send email, user UUID, or private stats.

Helpers: `trackFanDirectoryView`, `trackFanDirectorySearch`, `trackFanDirectoryFilterUsed`, `trackFanCardImpression`, `trackFanCardClick`, `trackFanPassportView`, `trackFanDirectoryOptIn`, `trackFanDirectoryOptOut` in `frontend/src/lib/analytics.ts`.

### Vault interaction signals

Product context: [VAULT.md](./VAULT.md). Analytics track engagement and unlock funnel only — they never grant access and must not carry locked body/media URLs.

| Action | When | Trust |
|---|---|---|
| `vault_page_view` | Public catalog `/u/{username}/vault` mount | Client |
| `vault_item_impression` / `vault_item_click` | Catalog / related teaser cards (Legacy, event detail, memory) | Client |
| `vault_item_view` | Item detail mount | Client |
| `vault_unlock_click` / `vault_unlock_failed` | Paid unlock or invite redeem attempt | Client |
| `vault_unlock_success` | Immediate paid/invite/follow unlock in UI; also trusted after purchase finalize | Either |
| `vault_follow_unlock` / `vault_ticket_unlock` | Follow / ticket CTA from locked panel | Client |
| `vault_media_open` / `vault_download_click` | Unlocked media link / file download | Client |
| `vault_preview_click_from_event` | Event detail → Vault CTA | Client |
| `vault_purchase` | Paystack/webhook finalize only | **Server only** |

**Metadata allowlist (Vault):** `host_id` (top-level), `vault_item_id`, `access_type`, `related_event_id`, `locked_state` (`locked`\|`unlocked`), `source_page`, plus `media_id` / `failure_reason` where relevant. Do **not** put Vault item IDs in `target_event_id` (reserved for real events). Do **not** send revenue fields from the client for unlock success.

Helpers: `trackVaultPageView`, `trackVaultItemImpression`, `trackVaultItemClick`, `trackVaultItemView`, `trackVaultUnlock*`, `trackVaultFollowUnlock`, `trackVaultTicketUnlock`, `trackVaultMediaOpen`, `trackVaultDownloadClick` in `frontend/src/lib/analytics.ts`.

**Rules**

- `POST /api/v1/analytics/track` requires a known taxonomy action and rejects server-only names (403/422).
- Clients must not send revenue inflation keys (`conversion_value`, `amount`, `gross_revenue`, …).
- Legacy aliases (`page_view`, `event_impression`, `checkout_complete`, …) normalize into taxonomy names; clients still cannot emit paid success via aliases.

---

## 3. Backend endpoints

### 3.1 Public track

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/analytics/health` | Module health |
| POST | `/api/v1/analytics/track` | Unified client track (known actions) |
| POST | `/api/v1/analytics/track/batch` | Batch; trusted rows rejected per item |
| POST | `/api/v1/analytics/track/event` | Legacy generic event |
| POST | `/api/v1/analytics/track/page-view` | Page / detail view (+ dedupe) |
| POST | `/api/v1/analytics/track/impression` | Listing impression (+ session/context dedupe) |
| POST | `/api/v1/analytics/track/click` | Listing click |
| POST | `/api/v1/analytics/track/conversion` | Funnel stages (no client paid success) |

### 3.2 Host portfolio summaries

| Method | Path | Auth |
|---|---|---|
| GET | `/api/v1/analytics/host/summary` | `analytics.view_own` |
| GET | `/api/v1/analytics/host/events/{event_id}` | Own events only |
| GET | `/api/v1/analytics/host/export.csv` | `analytics.export` |

### 3.3 Host per-event analytics

Base: `/api/v1/host/events/{event_id}/analytics/`

| Suffix | Purpose |
|---|---|
| `overview` | KPIs + conversion rates |
| `funnel` | Step counts + dropoffs |
| `timeseries` | Hour / day / week trends |
| `sources` | Channel buckets + UTM campaigns |
| `tickets` | Ticket-type performance |
| `audience` | Device / city / new vs returning (aggregates) |
| `promos` | Promo performance |
| `ambassadors` | Ambassador / referral performance |
| `export` | Aggregate CSV |

**Filters:** `date_from`, `date_to`, `source`, `medium`, `campaign`, `ticket_type_id`, `device_type`, `city`, `include_bots` (hosts cannot enable bots).

### 3.4 Admin platform + per-event

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/analytics/admin/summary` | Platform overview |
| GET | `/api/v1/analytics/admin/revenue` | Revenue breakdown |
| GET | `/api/v1/analytics/admin/events` | Category / city trends |
| GET | `/api/v1/analytics/admin/hosts` | Host rankings |
| GET | `/api/v1/analytics/admin/support` | Support / fraud placeholders |
| GET | `/api/v1/analytics/admin/export.csv` | Platform CSV |
| GET | `/api/v1/admin/events/{event_id}/analytics` | Full event analytics bundle |
| GET | `/api/v1/admin/events/{event_id}/analytics/funnel` | Funnel |
| GET | `/api/v1/admin/events/{event_id}/analytics/timeseries` | Timeseries |
| GET | `/api/v1/admin/events/{event_id}/analytics/audience` | Audience |
| GET | `/api/v1/admin/events/{event_id}/analytics/promos` | Promos |
| GET | `/api/v1/admin/events/{event_id}/analytics/ambassadors` | Ambassadors |
| GET | `/api/v1/admin/events/{event_id}/analytics/export` | Event CSV |
| GET | `/api/v1/admin/analytics/events/leaderboard` | Cross-event ranking |
| GET | `/api/v1/admin/analytics/events/channels` | Platform channel mix |
| GET | `/api/v1/admin/analytics/events/compare` | Multi-event compare (`event_ids`) |
| GET | `/api/v1/admin/analytics/events/export` | Events leaderboard CSV |

Auth: `analytics.view_platform` (+ `analytics.export` for CSVs).

### 3.5 Key modules

| Path | Role |
|---|---|
| `app/analytics/tracking.py` | Client write helpers + dedupe |
| `app/analytics/trusted.py` | Server emitters for commerce outcomes |
| `app/analytics/event_detail_reports.py` | Per-event report builders |
| `app/analytics/rollups.py` | Daily rollup recalculation |
| `app/analytics/dimensions.py` | IP/UA hash + metadata scrub |
| `scripts/run_analytics_rollups.py` | Ops CLI |
| `app/demo/analytics_seed.py` | Demo 90-day traffic + rollups |

---

## 4. Frontend instrumentation

| Layer | Location |
|---|---|
| Root provider | `components/analytics/AnalyticsProvider.tsx` in `app/layout.tsx` |
| Queue / batch / UTM / track helpers | `lib/analytics.ts`, `lib/analytics-client.ts` |
| HTTP client | `lib/analytics-api.ts` |
| Taxonomy types | `lib/analytics-taxonomy.ts` |
| Hooks | `hooks/useAnalytics.ts`, `useTrackImpression.ts`, `useTrackPageView.ts`, `useUTMAttribution.ts` |
| Impression observer | `components/analytics/TrackImpression.tsx` |
| Dashboards | `EventAnalyticsDashboard`, `AnalyticsFunnel`, `MultiMetricTrend`, `AdminAnalyticsSubnav` |

**Wired product surfaces**

| Surface | Instrumentation |
|---|---|
| `EventCard` / `LegacyEventCard` | Card impression + click |
| `EventPublicView` | Detail view, share, buy CTA, ticket panel/type |
| `/events` | List page view; `LocationFilterBar` → `location_filter_used` |
| Location hubs | `LocationPageViewTracker` → `country`/`state`/`city`/`area_page_view` |
| `PadeyaPicksSection` / `FeaturedPlacementCard` | `padeya_pick_*` (+ `featured_placement_*` when admin-sourced) |
| `/events/[slug]/checkout` | Checkout page view, promo, payment started, abandon |

`track()` is SSR-safe (no-ops when `window` is undefined). Client impression dedupe uses session TTL keys. Smoke: `npm run test:analytics`, `npm run test:discovery`.
---

## 5. Rollup job commands

Idempotent daily aggregates from the raw stream. Full ops guide: [ANALYTICS_ROLLUPS.md](./ANALYTICS_ROLLUPS.md).

```bash
# From backend/
python -m scripts.run_analytics_rollups --date-from 2026-01-01 --date-to 2026-01-31
python -m scripts.run_analytics_rollups --last-days 7
python -m scripts.run_analytics_rollups                    # default: last 2 UTC days
python -m scripts.run_analytics_rollups --last-days 30 --event-id <uuid>
```

```bash
docker compose exec backend \
  python -m scripts.run_analytics_rollups --last-days 7
```

Rollup tables: `event_daily_analytics`, `event_source_analytics`, `event_ticket_type_analytics`, `event_geo_device_analytics`. Bots excluded. Safe to re-run.

**Read path:** host/admin **overview** and **funnel** prefer daily rollups when no dimension filters are set (`traffic_source: "rollup"`). Filtered reports, sources, tickets, and audience still use live SQL over the stream. Commerce KPIs always come from orders/tickets.

---

## 6. Host analytics dashboard

| Route | What hosts see |
|---|---|
| `/host/analytics` | Portfolio summary — sales, traffic, check-ins, promos/ambassadors, Vault/Legacy trends |
| `/host/events/[id]/analytics` | Per-event overview, funnel, trends, sources, ticket types, audience buckets, promos/ambassadors, CSV export |

**Behavior**

- Own events only (foreign event IDs → 404).
- Empty / loading / error states in the UI.
- Aggregates only — no buyer emails, phones, raw IPs, or private venue details ([ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md)).
- Revenue / tickets sold / check-ins / reviews prefer trusted commerce + stream alignment.

Door check-in stats remain at `/host/events/[id]/check-in/analytics` (separate from product funnel analytics).

---

## 7. Admin analytics dashboard

| Route | What admins see |
|---|---|
| `/admin/analytics` | Platform overview |
| `/admin/analytics/revenue` | Revenue drilldown |
| `/admin/analytics/events` | Leaderboard, compare, channels, conversion outliers |
| `/admin/analytics/hosts` | Host rankings |
| `/admin/analytics/support` | Support / fraud placeholders |
| `/admin/events/[id]/analytics` | Same per-event dashboard as hosts, for any event |

Admins can include bots for quality investigation. Analytics still must not expose card data or private venue secrets.

---

## 8. Privacy rules

Full policy: [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md).

Highlights:

- Scrub emails, phones, card fields, private/hidden venue addresses, join URLs on write.
- Store `ip_hash` only; never show raw IPs on host dashboards.
- Opaque `anonymous_id` / `session_id` for unique counts.
- Host analytics = aggregates for own events; admin = platform + any event, still aggregate-first.
- Fan Connect / `fan_fan` events follow the same scrub rules plus the never-list above (no message bodies, spend, or private attendance).
- Recommended retention: ~13 months raw stream, longer for daily rollups; user anonymization pipeline is future work.

---

## 9. Storage model

### Raw stream

`analytics_events` — append-only taxonomy actions with UTM, device, geo, scrubbed metadata, `is_bot`.

### Legacy dual-write (BC)

`page_views`, `event_impressions`, `event_clicks`, `conversion_events`.

### Rollups + dedupe

| Table | Grain |
|---|---|
| `event_daily_analytics` | date × event |
| `event_source_analytics` | date × event × source/medium/campaign |
| `event_ticket_type_analytics` | date × event × ticket_type |
| `event_geo_device_analytics` | date × event × country/city/device/browser |
| `analytics_dedupe_keys` | Windowed / request idempotency |

Migrations: `20260716_0013_advanced_analytics`, `20260717_0022_analytics_storage`.

---

## 10. Explicit non-goals

- Third-party analytics vendors  
- Changing Paystack / ticket QR / check-in issuance rules  
- Host access to raw buyer browsing profiles  
- Replacing promo/ambassador tables with analytics-only attribution  
- Real-time streaming warehouse  

---

## 11. Summary

Pàdéyá ships first-party **per-event** analytics: taxonomy stream, unified track + batch, trusted commerce signals, host and admin dashboards, demo seed, and idempotent daily rollups — with privacy scrubbing so hosts never see emails, phones, raw IPs, or private venue details through analytics APIs.
