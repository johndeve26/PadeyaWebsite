# Database

## Migrations

```bash
cd backend && alembic upgrade head
```

Always run this after pulling schema changes. Backend entrypoints also run `alembic upgrade head` on boot in production compose.

### Admin team management (`20260720_0101`)

Creates `admin_roles`, `admin_role_permissions`, `admin_team_members`, `admin_invites`, and `admin_audit_logs`. Login may attempt a best-effort write to `admin_audit_logs` (and a lookup on `admin_team_members`); apply this revision so admin login auditing works. Login itself must not 500 if these tables are missing — the auth path isolates that write in a SAVEPOINT.

### Admin event buyer export auditing

No dedicated export table — successful downloads write rows to existing `audit_logs`:

| Column / detail | Meaning |
|---|---|
| `action` | `admin_event_buyers_exported` · `admin_event_buyers_private_contact_exported` · `admin_event_buyers_finance_exported` |
| `actor_user_id` | Admin user |
| `resource_type` / `resource_id` | `event` / event UUID |
| `details` JSON | `admin_user_id`, `event_id`, `host_profile_id`, `export_mode`, `format`, `filters_json`, `row_count`, `reason`, `include_private_contact` |
| `ip_address` / `user_agent` | From request when present |

Permissions are seeded in `app/users/constants.py` (`admin.events.view`, `admin.events.export_buyers`, `admin.events.export_private_contact`, `admin.finance.export_event_sales`) — no new migration required beyond RBAC seed.

## Admin user management

Soft lifecycle tooling for platform users. **No hard delete** of users from this surface. Product: [ADMIN.md](./ADMIN.md#user-management-safe-actions) · API: [API.md](./API.md#admin-user-management-safe-actions).

### Migrations

| Revision | Contents |
| --- | --- |
| `20260720_0092` | `user_admin_notes`, `user_admin_flags`, `users.under_review_at` / `under_review_reason` |
| `20260720_0093` | Flag MVP: `flag_type`, `severity`, `internal_note`, `created_by_admin_id`, `resolved_by_admin_id`; status `active` |
| `20260720_0094` | Notes MVP: `note_type`, `created_by_admin_id`, nullable `updated_at` |
| `20260720_0095` | `users.account_status`, `users.account_restrictions` |
| `20260720_0096` | `user_restrictions` table; migrate legacy JSON / `ambassadors_blocked` |
| `20260720_0097` | `account_suspensions`, `account_appeals` (public-safe suspension + appeal lifecycle) |

### `users` (admin-relevant columns)

| Column | Meaning |
| --- | --- |
| `account_status` | `active` · `under_review` · `restricted` · `suspended` · `banned` · `deleted` |
| `account_restrictions` | JSON mirror of **active** keys (legacy; primary source is `user_restrictions`) |
| `under_review_at` / `under_review_reason` | Soft ops hold (distinct from suspend / security lock) |
| `security_locked_at` / `security_lock_reason` | Security investigation lock (blocks impersonation) |
| `password_hash` | **Never** returned on admin APIs |

### `user_restrictions`

Append-only selective activity limits — **never hard-delete**. Soft statuses only: `active` → `expired` (past `ends_at`) or `revoked`.

| Column | Meaning |
| --- | --- |
| `id` | UUID PK |
| `user_id` | FK → users |
| `restriction_key` | Catalog key (see `account_status_constants.py`) |
| `status` | `active` · `expired` · `revoked` |
| `reason` | **Required** admin reason |
| `internal_note` | Nullable; admin-only (never in `/me`) |
| `starts_at` / `ends_at` | Window; `ends_at` null = indefinite |
| `created_by_admin_id` | Admin who created |
| `revoked_by_admin_id` / `revoked_at` | Soft revoke actors |
| `created_at` / `updated_at` | Timestamps |

Helpers: `user_has_restriction` / `assert_no_restriction` in `app/users/restrictions.py` (active rows with `ends_at` null or future only).

### `account_suspensions`

Public-safe suspension metadata shown to the user (category / dates only — **never** admin reason body, fraud internals, or internal notes). Soft lift only (`active` → `lifted`).

| Column | Meaning |
| --- | --- |
| `id` | UUID PK |
| `user_id` | FK → users |
| `status` | `active` · `lifted` |
| `reason_category` | User-facing: `policy_violation` · `abuse_or_harassment` · `safety` · `account_security` · `terms_of_service` · `other` |
| `starts_at` / `ends_at` | Window; `ends_at` null = indefinite |
| `created_by_admin_id` | Admin who suspended |
| `lifted_at` / `lifted_by_admin_id` | Soft lift actors |

### `account_appeals`

User appeal against an active suspension. Soft status only — no hard delete.

| Column | Meaning |
| --- | --- |
| `id` | UUID PK |
| `user_id` / `suspension_id` | FKs |
| `message` | User appeal text |
| `status` | `pending` · `approved` · `rejected` · `withdrawn` |
| `admin_reply` | Optional user-facing reply on reject/approve |
| `reviewed_by_admin_id` / `reviewed_at` | Review actors |

### `user_admin_notes`

Append-only internal notes — **never shown to the end user**. No edit/delete API in MVP.

| Column | Meaning |
| --- | --- |
| `user_id` | Target user |
| `note_type` | Catalog type (e.g. `general`) |
| `body` | Note text (rejected if it looks like password/token/payment/QR secret content) |
| `created_by_admin_id` | Authoring admin |
| `created_at` / `updated_at` | `updated_at` nullable until an edit path exists |

### `user_admin_flags`

Risk/abuse/support flags — soft-close only (`active` → `resolved` / `dismissed`); no hard delete.

| Column | Meaning |
| --- | --- |
| `user_id` | Target user |
| `flag_type` / `severity` | Catalog type + `low`–`critical` |
| `status` | `active` · `resolved` · `dismissed` |
| `reason` / `internal_note?` | Why flagged (admin-only) |
| `created_by_admin_id` / `resolved_by_admin_id` / `resolved_at` | Lifecycle actors |
| `resolution_note?` | Optional close note |

### Admin user management audit

Platform `audit_logs` (`resource_type=user`) — writer: `app/users/admin_user_audit.py`.

| Action | When |
| --- | --- |
| `admin_user_viewed` | Admin opens user detail |
| `admin_user_private_contact_viewed` | Unmasked contact in response |
| `admin_user_note_created` | Internal note added |
| `admin_user_flag_created` / `admin_user_flag_updated` | Flag add / resolve-dismiss |
| `admin_user_status_changed` | Account status transition |
| `admin_user_restriction_added` | Restriction row(s) created |
| `admin_user_restriction_revoked` | Restriction revoked |
| `admin_user_restriction_extended` | `ends_at` extended |
| `admin_user_restriction_preset_applied` | Named preset applied |
| `restricted_user_blocked_from_action` | Product gate blocked restricted user |
| `admin_user_force_logout` | Force logout |
| `admin_user_force_password_reset` | Force password-reset email |

Details JSON (scrubbed): `admin_user_id`, `target_user_id`, optional `restriction_keys` / `reason` / `internal_note_present` (boolean only) / `starts_at` / `ends_at` / `previous_status` / `new_status` / `before_json` / `after_json`. Row columns: `ip_address`, `user_agent`, `created_at`. **Never** stores passwords, tokens, note/flag bodies, internal note text, or payment/QR secrets.

## Admin user impersonation

Migration `20260720_0089` — audited support/QA sessions (not a real login). Scopes column: `20260726_0142`. See [AUTH.md](./AUTH.md) · [SECURITY.md](./SECURITY.md#admin-user-impersonation).

### `admin_impersonation_sessions`

| Column | Meaning |
| --- | --- |
| `id` | Session UUID (= JWT `impersonation_id`) |
| `actor_admin_id` | Admin who started the session |
| `target_user_id` | User being viewed |
| `reason` | Required support/QA reason |
| `support_ticket_id` | Optional ticket reference |
| `started_at` / `expires_at` / `ended_at` | Lifecycle timestamps (max duration 60 min) |
| `ended_by_admin_id` | Who ended the session (when applicable) |
| `status` | `active` · `ended` · `expired` · `revoked` |
| `scopes` | JSON list: `view` / `host_events` / `credentials` (capability pack) |
| `ip_address` / `user_agent` | Start request context |
| `created_at` | Row create time |

### `admin_impersonation_audit_logs`

| Column | Meaning |
| --- | --- |
| `impersonation_id` | FK → session |
| `actor_admin_id` / `target_user_id` | Parties |
| `action` | `admin_impersonation_started` · `_ended` · `_expired` · `_sensitive_action_blocked` · `_request_made` |
| `method` / `path` / `status_code` | Request stamp when applicable |
| `metadata_json` | Scrubbed extras (`reason`, `support_ticket_id`, `route`, `scopes`, `pack`, timestamps, …) — never passwords, tokens, payment/QR payloads, request bodies, or message content |
| `ip_address` / `user_agent` | When known |
| `created_at` | Event time |

Canonical actions: `admin_impersonation_started` · `admin_impersonation_ended` · `admin_impersonation_expired` · `admin_impersonation_sensitive_action_blocked` · `admin_impersonation_request_made`.

Required field matrix (columns + metadata): `impersonation_id`, `actor_admin_id`, `target_user_id`, `action`, `path`/`route`, `method`, `reason`, `support_ticket_id?`, `ip_address?`, `user_agent?`, `created_at`.

Also dual-writes to platform `audit_logs` (`resource_type=impersonation_session`). **Audit logs are retained** (including demo seeds). Target users are **never** notified — there is no impersonation email, in-app, or push template.

**Internal audit must include:** actor admin · target user · reason · support ticket ID (if provided) · start time · end time · expiry · visited routes/actions (`admin_impersonation_request_made`) · blocked sensitive actions (`admin_impersonation_sensitive_action_blocked`).

| Revision | Contents |
| --- | --- |
| `20260716_0001` … `0006` | Auth → Legacy tiers |
| `20260716_0007` | Promo codes, ambassadors, clicks, sales; order discount/referral columns |
| `20260719_0076` | Open Event Ambassadors: event flags + `ambassadors.event_id` / `program_kind` |
| `20260719_0077` | Ambassador eligibility: `users.ambassadors_blocked` + terms fields on ambassadors |
| `20260719_0078` | `ambassador_sales.merch_units_sold` for merch attribution |
| `20260719_0079` | `ambassador_campaigns` + `ambassadors.campaign_id` |
| `20260719_0080` | Admin Ambassadors: platform settings, campaign `source`, sale reverse/reward fields |
| `20260719_0081` | `ambassador_campaigns.campaign_type` (`event_tickets` \| `event_merch`); enroll once per campaign |
| `20260719_0082` | Referral codes unique per campaign; `orders.referral_attribution_source` |
| `20260719_0083` | Commission rules: `commission_type` / `value` / `applies_to` / hold / caps / free-ticket / leaderboard reward |
| `20260719_0084` | Ambassador domain: profiles, participants, clicks, attributions, conversions, payouts, audit; campaign `host_profile_id` / visibility / cookie window |
| `20260719_0085` | `orders.ambassador_participant_id` / `ambassador_attribution_id` for domain checkout attribution |
| `20260719_0086` | Fraud controls: `allow_host_owner_commission`, `promo_clicks.user_agent_hash`, `ambassador_fraud_flags` |
| `20260719_0087` | Host reward payout meta on `ambassador_sales`: `payout_reference`, `payout_note`, `rejection_reason` |
| `20260720_0088` | User security lock columns |
| `20260720_0089` | Admin impersonation sessions + domain audit logs |
| `20260720_0090` | `runtime_settings` (Admin Runtime Settings Class B overrides) |
| `20260720_0092` | Admin user notes/flags + `users.under_review_*` |
| `20260720_0093` | Admin user flags MVP columns |
| `20260720_0094` | Admin user notes MVP columns |
| `20260720_0095` | `users.account_status` + `account_restrictions` |
| `20260720_0096` | `user_restrictions` (selective restriction history) |
| `20260720_0097` | `account_suspensions` + `account_appeals` |
| `20260716_0008` | Host CRM: followers, segments, announcements, recipients |
| `20260716_0009` | Finance: refunds, host balances, ledger, payouts, evidence |
| `20260716_0010` | Vault items, media, access rules, purchases, views |
| `20260717_0033` | Vault item field expansions (content types, related links, tags) |
| `20260717_0034` | Vault access rule fields (invite hash, ticket filters, windows) |
| `20260717_0035` | Vault item lifecycle statuses (`scheduled` / `expired` / `hidden_by_admin`, …) |
| `20260717_0036` | `vault_access_grants` + `vault_unlock_attempts` |
| `20260716_0016` | Advanced ticketing: transfers, groups, tables, offline sync |
| `20260717_0023` | Taxonomy vocab, locations, links, content graph; event `primary_category_id` / `location_id` |
| `20260717_0024` | Initial `featured_placement_slots` |
| `20260717_0025` | Placement context columns on slots |
| `20260717_0026` | `featured_placements` table; migrate/drop legacy slots |
| `20260717_0027` | Allow `area_page` placement type |
| `20260717_0018` | Event Studio: agenda/people/checkout questions; privacy/media/policy/SEO columns; ticket access fields |
| `20260717_0020` | `event_templates` |
| `20260717_0028` | `events.venue_type` |
| `20260717_0029` | Checkout question `help_text` + `order_checkout_answers` |
| `20260717_0030` | Checkout question `status` / `archived_at` (archive-when-answered) |
| `20260717_0031` | Event map/location: country/area/postcode, exact + approximate coords, Google Maps URLs |
| `20260717_0032` | Legacy Content Studio: pages, content blocks, featured items, social links, contact settings |
| `20260718_0050` | Fan Connect v1: settings/connections + `message_threads.fan_b_user_id` for `fan_fan` |
| `20260718_0051` | Fan Connect schema v2: settings, connections, blocks, reports, suggestions |
| `20260718_0052` | `message_attachments` (staged nullable `message_id`, image metadata) |
| `20260718_0053` | `message_attachments` v2 (thread_id, status, checksum, dims) + `message_attachment_downloads` |
| `20260718_0054` | `message_attachments.reviewed_at` for admin moderation |
| `20260718_0055` | `messages.reply_to_message_id` + `message_pins` + `message_stars` |
| `20260718_0056` | `messages.edit_count` / `last_edited_by_user_id` + `message_edits` history |
| `20260718_0057` | `message_pins.unpinned_at` soft unpin |
| `20260718_0058` | `message_stars.starred_at` + `unstarred_at` soft unstar |
| `20260718_0059` | `message_deletions` (per-viewer soft delete) |

## Legacy Content Studio (schema)

Head revision: **`20260717_0032`**.

| Table | Role |
| --- | --- |
| `host_legacy_pages` | Tagline, CTAs, sponsorship, category/host-type hints, service areas |
| `host_legacy_content_blocks` | Block type, visibility, order, layout, source, limit, config JSONB |
| `host_legacy_featured_items` | Featured event/review/vault/memory/sponsor/media placements |
| `host_social_links` | Structured public social links |
| `host_contact_settings` | Contact preference + public email/note |

Existing `hosts` / `host_profiles` / `host_legacy_scores` remain the identity + reputation core.

## Event Studio (schema)

Event Studio tables remain as below (map fields in `0031`).

| Table | Role |
| --- | --- |
| `events` | Core + Studio location privacy, schedule, media URLs, policies, SEO (nullable for BC) |
| `event_venues` | Nested 1:1 venue; dual with flat `events.venue_*` / address fields |
| `event_media` | Gallery + typed media (`media_type`); **not** a separate gallery table |
| `event_agenda_items` | Nested **upsert-by-id** agenda (omit on PATCH → hard delete) |
| `event_people` | Nested **upsert-by-id** lineup (omit → hard delete) |
| `event_checkout_questions` | Nested upsert-by-id; `help_text`; `status` (`active`/`archived`) + `archived_at` |
| `order_checkout_answers` | Immutable buyer answer snapshots on orders (blocks question hard-delete) |
| `event_templates` | Host JSON blueprints (archive/restore) |
| `ticket_types` | Pricing + access/lifecycle (`transfer_allowed`, waitlist, seats, sold/reserved, …) |

**Subresource write model:** event `POST`/`PATCH` upserts agenda/people/questions by stable `id`. Omitting an unused row deletes it. Omitting a question that already has answers **archives** it (`status=archived`, `archived_at` set) instead of deleting.

**Not stored:** publish checklist — computed in `build_publish_checklist()` / Studio FE (`preview_checked` is client/session only).  
**Do not create:** `event_gallery_media`, `event_publish_checklists`, `event_checkout_answers` (answers live on orders).

Category dual-write: Studio `category_id` (`event_categories`) mirrors to `primary_category_id` (`taxonomy_categories`) by slug when taxonomy is seeded.

### Studio field columns on `events` (selected)

| Concern | Columns |
| --- | --- |
| Identity | `title`, `slug`, `description`, `short_tagline`, `vibe`, `event_type`, `visibility`, `category_id`, `primary_category_id` |
| Place | `location_id`, `venue_name`, `venue_type`, `address`, `city`, `state`, `country`, `area`, `postcode`, `public_location_label` |
| Map | Exact `latitude`/`longitude`, `google_maps_share_url`/`google_maps_place_url`; public-safe `approximate_*` |
| Privacy | `location_visibility` (default `full_public`), `reveal_timing`, `reveal_note`, `online_event_url`, `online_url_reveal_rule` — serializer adds `location_map_mode` / `map_*` |
| Schedule | `start_datetime`, `end_datetime`, `doors_open_datetime`, `timezone` |
| Media URLs | `banner_url`, `mobile_banner_url`, `teaser_video_url`, `social_share_image_url`, `brand_accent_override` (+ JSON arrays for gallery/sponsors via media / payload) |
| Policies | refund/cancellation/age/ID/safety/terms, door/re-entry, check-in windows, logistics copy, `capacity` |
| SEO | `seo_title`, `seo_description`, social share fields, hashtags/keywords JSON |
| Lifecycle | `status` ∈ draft → published → paused/completed/cancelled/rejected/archived (soft admin flags on publish/edit; no `pending_review`) |

### Ticket type lifecycle columns

`ticket_types.status` (`active` / `inactive` / `sold_out`), `visibility`, `quantity` / `quantity_sold` / `quantity_reserved`, access fields (`transfer_allowed`, waitlist, seats, sale window, …). Hard delete blocked when sold or reserved > 0 — deactivate instead.

## Promos & ambassadors (Phase 8 + open Event Ambassadors)

Product overview: [AMBASSADORS.md](./AMBASSADORS.md) · ticket discounts: [PROMO_CODES.md](./PROMO_CODES.md). Migrations `20260719_0076`–`0087` (open join → domain tables → payment FKs → fraud flags → host payout meta).

- `promo_codes` — host-owned **ticket** discount codes (type, value, limits, expiry, event/ticket restrictions) — not Ambassador referral
- `promo_redemptions` — per-order redemption (`pending` → `redeemed` / `released`)
- `ambassadors` — v1 referral enrollments + optional linked user + commission %; `program_kind` `host_curated` \| `open_event`; open rows set `event_id` / `campaign_id`; `terms_accepted_at` / `terms_version` on open join
- `users.ambassadors_blocked` — platform block from Ambassadors (not host team)
- `events.open_ambassadors_enabled` / `open_ambassador_commission_percent` — synced from live campaigns
- `promo_clicks` — v1 referral click funnel (`ip_hash`, `user_agent_hash`; no raw IP)
- `ambassador_campaigns` — open promotion rules (v1 + phase-9): `host_profile_id`, nullable `event_id` / `merch_product_id`, `visibility`, `cookie_window_days`, commission rules, hold/caps/rewards, `allow_host_owner_commission`. Legacy v1 services still use `host_id` + statuses `public_open|paused|ended`.
- `ambassador_profiles` — one Ambassadors identity per user (`active|suspended|blocked`)
- `ambassador_participants` — campaign enrollment + `ambassador_code` (unique per campaign)
- `ambassador_clicks` — append-only referral clicks (hashed visitor signals)
- `ambassador_attributions` — cookie/session attribution windows (`link|code|qr`)
- `ambassador_conversions` — commission ledger (`pending→…→paid|reversed|rejected`); unique `dedupe_key`; reverse-only EOL
- `ambassador_payouts` — payout requests (`pending|approved|paid|cancelled`)
- `ambassador_audit_logs` — append-only domain audit (`metadata_json`)
- `ambassador_fraud_flags` — open click-spike / suspicious conversion flags for admin review
- `ambassador_sales` — **v1** sales ledger still live until cutover; reward statuses + `payout_reference` / `payout_note` / `rejection_reason` (migration `0087`) for host mark-paid meta (not Paystack refs)
- `ambassadors` / `promo_clicks` — **v1** tables still live until service cutover; do not drop
- `ambassador_platform_settings` — global enable/disable kill-switch
- Reward status changes also append platform `audit_logs` (`ambassador_reward_*` / `…_by_admin`) via `app/ambassadors/reward_audit.py`

### Orders (extended)

- `discount_amount`, `promo_code_id`, `promo_code_snapshot`
- `ambassador_id`, `referral_code`, `referral_attribution_source`
- `ambassador_participant_id`, `ambassador_attribution_id` — domain attribution at checkout; conversions only after paid webhook
- `order_items.item_kind` — `ticket` \| `merch` \| `bundle` (polymorphic lines; bundles expand into ticket+merch on create)
- `order_items.ticket_type_id` nullable when merch; `merch_product_id` / `merch_variant_id` + name snapshots when merch; optional `bundle_id`
- `orders.merch_discount_code_id` / `merch_discount_code_snapshot` / `merch_discount_amount` / `shipping_amount` / `fulfillment_method`

## Event merch (Phase 1)

Phase 1 plus commerce expansion. Product rules: [MERCHANDISE.md](./MERCHANDISE.md) · commerce: [COMMERCE.md](./COMMERCE.md) · technical index: [MERCH.md](./MERCH.md).

Merch reuses `orders` / `order_items` / `payments` (no parallel merch payment tables). Stock, discount redemptions, POD jobs, revenue splits, and Passport merch badges commit on verified payment finalize only.

| Table | Purpose |
| --- | --- |
| `event_merch_products` | Catalog (+ storefront/vault/sponsor/shipping/POD/size_chart/drop fields; `event_id` nullable when evergreen; `requires_vip`, `drop_live_notified_at` via `0049`) |
| `event_merch_variants` | Variants + inventory/reserved/sold + low_stock / POD refs; reserve on pending checkout, deduct on paid finalize |
| `merch_fulfillments` | Pickup/shipping/POD rows (`MRCH-*`, QR hash); 1:1 with merch `order_items` |
| `event_merch_fulfillment_events` | Append-only fulfillment timeline (`created`, `qr_scanned`, `shipped`, `picked_up`, …) |
| `merch_bundles` | Ticket+merch packs (expand on order create) |
| `merch_discount_codes` / `merch_discount_redemptions` | Merch codes (separate from ticket `promo_codes`); usage on paid finalize; `description` + `currency` via `0048` |
| `merch_shipping_addresses` | Encrypted private ship-to (order-scoped) |
| `merch_shipping_zones` | Host/event flat shipping fees |
| `merch_size_charts` | Reusable size guides |
| `merch_reviews` | Verified purchase reviews (hosts cannot delete) |
| `merch_stock_alerts` | Persisted low/sold-out/restock/pre-event/high-reserve alerts |
| `merch_revenue_splits` | Append-only paid merch split snapshots |
| `merch_carts` / `merch_cart_items` | Abandoned cart recovery (never paid state) |
| `merch_print_on_demand_integrations` / `merch_pod_jobs` | POD provider-ready (manual now; live Printful sync future) |
| `merch_product_reports` | Buyer reports (reason/details/admin_notes; statuses `open`/`reviewing`/`resolved`/`dismissed`) |

Related:

- `events.allow_merch_only_checkout`
- `host_profiles.merch_storefront_enabled` / `title` / `description` / `visibility` (`public` \| `unlisted`)
- `message_threads.related_merch_order_item_id` (nullable FK → `order_items`, messaging context only)

Migrations: `20260718_0047_merch_commerce_expansion`, `0048` (discount description/currency), `0049` (post-event drop flags).

## Host team

Product overview: [TEAMS.md](./TEAMS.md) · deep: [HOST_TEAM.md](./HOST_TEAM.md). Migrations `20260719_0069`–`0075` (includes `user_active_workspaces`, invite privacy / `invite_method`).

`host_id` on these tables is the host workspace id (`hosts.id` — product “host profile”).

| Table | Purpose |
|---|---|
| `host_team_members` | Accepted roster: `user_id`, `role`, `status`, `permissions_json`, `scope_json`, `invite_method` / `invited_username` (privacy), `invited_by_user_id`, lifecycle timestamps |
| `host_team_invites` | Pending invites — see columns below |
| `host_team_audit_logs` | Immutable team audit trail (`actor_user_id`, `target_user_id`, `action`, `entity_*`, sanitized `metadata_json`, optional IP/UA) |
| `event_staff_assignments` | Per-event desk; optional `team_member_id` (synced from team scope), `assignment_type` (`ticket_scanner` / `merch_pickup` / `event_ops`), `permissions_json`, `status`, `expires_at` |
| `desk_scan_audit_logs` | Every ticket/merch desk scan attempt: actor, host, event, ticket/order item, action, result, denial reason (migration `20260719_0072`) |
| `user_active_workspaces` | Persisted active host workspace per user (`host_id`) for switcher resolve |

#### `host_team_invites` columns

| Column | Notes |
|---|---|
| `invite_method` | `email` \| `username` |
| `invited_username` | Nullable; set for username invites (stored without requiring host-visible email) |
| `invited_user_id` | Nullable; set when invitee is a known Pàdéyá user (always for username invites) |
| `email` | Kept populated for outbox delivery (email invites + resolved username → account email). **Not** returned on host APIs when `invite_method=username` |
| `token_hash` | SHA-256 only — raw token never stored |
| `expires_at` | Typically 7 days |
| `status` | `pending` / `accepted` / `expired` / `revoked` (+ `accepted_at` / `revoked_at`) |

Uniques: one pending invite per `(host_id, lower(email))`; one live membership per `(host_id, user_id)` when `status` in active/suspended/invited. Hybrid scan uses team + staff together — see [TEAMS.md](./TEAMS.md#hybrid-scan-authorization).

## Host CRM (Phase 9)

- `host_followers` — unique `(host_id, user_id)`; `marketing_opt_in` defaults `false`
- `audience_segments` — host-scoped system + custom segments (`segment_key`, JSON `filters`)
- `host_announcements` — title, email/WhatsApp bodies, channel, status, `delivery_status`, `recipient_count`
- `announcement_recipients` — per-user targeting row with delivery/skip status (`marketing_opt_out`, etc.)

## Finance (Phase 10 + fees / platform ledger)

Canonical product docs: [FINANCE.md](./FINANCE.md) · [PAYOUTS.md](./PAYOUTS.md) · [HOST_EARNINGS.md](./HOST_EARNINGS.md).

**Refunds & host cash**

- `refund_requests` — buyer refund asks (policy snapshot, amount, status, escalation/review notes)
- `refunds` — completed refund records linked to request + ledger entry
- `host_balances` — available / pending payout / lifetime earned·refunded·paid_out
- `ledger_entries` — **append-only** host journal (`sale_credit`, `refund_debit`, `payout_hold`, `payout_release`, `payout_paid`, `vault_sale`, `adjustment`)
- `payout_requests` — host payout asks with bank snapshot + workflow status
- `payout_evidence` — immutable mark-as-paid evidence (transfer ref, file URL, paid_by, paid_at, bank snapshot)

**Configurable fees**

- `platform_fee_settings` — global fee schedule (key, type, %, fixed minor units, payer, effective window)
- `host_fee_overrides` — per-host overrides (beat global when enabled + in window)
- `order_fee_snapshots` — immutable per-line fee capture at order create (minor units)
- `orders` fee summary columns: `buyer_fee_total`, `host_fee_total`, `processing_fee_total`, `platform_revenue_total`, `host_net_estimate`

**Platform ledger**

- `platform_ledger_entries` — append-only platform journal (`buyer_payment`, `ticket_revenue`, `merch_revenue`, `vault_revenue`, `buyer_platform_fee`, `host_commission`, `processing_fee`, `refund`, `chargeback`, `ambassador_reward`, `host_payout`, `adjustment`); unique `dedupe_key`; optional `order_id` / `host_id` / `event_id` / masked metadata

Migrations: `20260716_0009` (refunds/balances/ledger/payouts) · `20260721_0110`–`0112` (fee tables/notes) · `20260721_0113` (order fee totals) · `20260721_0114` (platform ledger).

## Vault (Phase 11)

Exclusive host content fans unlock by follow, ticket, attendance, VIP, invite, or purchase. See [VAULT.md](./VAULT.md).

| Table | Purpose |
| --- | --- |
| `vault_items` | Drop identity (type, slug, description, preview, body, cover, file/external URLs, related event/memory, tags, price, status `draft`/`published`/`scheduled`/`expired`/`archived`/`hidden_by_admin`, published/expires, moderation) |
| `vault_media` | Media URLs + storage keys; `is_preview` may be public while locked |
| `vault_access_rules` | Access type (`free`, `followers_only`, `ticket_holder_only`, `checked_in_attendee_only`, `vip_ticket_holder_only`, `one_time_unlock`, `invite_only`, `admin_hidden`) + price, event/ticket filters, hashed invite code, max unlocks, window |
| `vault_purchases` | Unlock rows (`PDY-VLT-*` Paystack refs; also invite/manual/demo); payment status |
| `vault_access_grants` | Idempotent entitlement `UNIQUE(vault_item_id, user_id)` — source of paid/invite unlock truth |
| `vault_unlock_attempts` | Append-only checkout attempt log (no entitlement) |
| `vault_views` | View log with `had_access` |
| `vault_subscriptions` | Buyer↔host subscription list (CRM); does **not** grant Vault access yet |

**Privacy:** locked public serializers omit `body` / private media URLs. **Money:** verified unlock credits append-only `vault_sale` ledger entries (never tickets).

## Admin Runtime Settings

See [SETTINGS.md](./SETTINGS.md) · [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md). Migration `20260720_0090`.

| Table | Purpose |
|---|---|
| `runtime_settings` | Allowlisted Class B overrides: unique `key`, `category`, `value_plain` (non-secrets) or `value_encrypted` + `last_four` (secrets), `value_type`, `is_secret`, `is_editable`, `is_required_for_runtime` (always false for optional), `source` label, `validation_schema_json`, `updated_by_admin_id`, timestamps |

**Rules:** Never store boot-critical Class A secrets here. Prefer clear-override (delete row) over hard-delete of audit history. Email SMTP / push VAPID stay on specialist tables below — not migrated into `runtime_settings`. Resolver: DB → env → default; startup does not require rows.

## Transactional email

| Table | Purpose |
|---|---|
| `email_events` | Outbox: template, recipient, status (`pending`/`sent`/`failed`/`skipped`), attempts, dedupe_key, context_json |
| `email_provider_settings` | Admin SMTP/provider rows; one `is_active`; Fernet `smtp_*_encrypted` + last4 masks; test/success timestamps |
| `user_email_preferences` | Per-user email **and** push channel toggles + marketing unsubscribe timestamp |

Migration: `20260719_0060`. Soft lifecycle only — no hard delete of email events.

## Browser push

See [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md). Migrations `0063`–`0068`.

| Table | Purpose |
|---|---|
| `push_provider_settings` | Admin kill switch, provider (`log`/`web_push`), VAPID public + `vapid_private_key_encrypted`, subject |
| `push_subscriptions` | Per-device endpoints; Fernet `p256dh`/`auth`; `is_active`, failure counters, `revoked_at` |
| `push_events` | Outbox mirror of email: template, title/body/action_url, status, attempts, dedupe_key, sanitized `data_json` |
| `push_delivery_events` | Per-device send attempts (append-only status trail) |

Push preference columns live on `user_email_preferences` (`push_enabled`, category toggles, `push_message_previews`, …). Soft lifecycle only — deactivate subscriptions / skip outbox rows; no hard delete of delivery history.

## Messaging

See [MESSAGING.md](./MESSAGING.md) and [DEMO_DATA.md](./DEMO_DATA.md).

Chat-feature migrations: `0055` (reply/pins/stars) → `0056` (edit history) → `0057` (soft unpin) → `0058` (soft unstar) → `0059` (delete-for-me).

| Table | Role |
| --- | --- |
| `message_threads` | fan↔host (`fan_user_id` + `host_id`) **or** fan↔fan (`fan_user_id` + `fan_b_user_id`); optional related event/merch/ticket (internal); per-side archive; **thread-level read cursors** `fan_last_read_at` / `host_last_read_at` (no per-message receipts); status `active\|request\|blocked\|reported\|closed` |
| `messages` | Text / system / image / attachment-bearing; moderation fields; `edited_at`, `edit_count`, `last_edited_by_user_id`; optional `reply_to_message_id` (`ON DELETE SET NULL`) |
| `message_edits` | Append-only edit history (`previous_body`, `new_body`, `editor_user_id`, `edited_at`) — audit only, not public UI |
| `message_pins` | **Shared** pins (`thread_id`, unique `message_id`, `pinned_by_user_id`, `pinned_at`, `unpinned_at`); max 3 active; hide/delete soft-unpins |
| `message_stars` | **Personal** stars (`user_id` + `message_id`, `starred_at`, `unstarred_at`); peer never sees |
| `message_deletions` | Per-viewer soft delete (`delete_scope=for_me`); message row retained |
| `message_attachments` | Staged uploads (`message_id` null until send); private `storage_key` + status lifecycle |
| `message_attachment_downloads` | Optional download audit |
| `message_blocks` | Block pairs (also Fan Connect eligibility) |
| `message_reports` | Moderation reports — **required** for admin hide/restore + attachment moderation scope |
| `message_settings` | Fan/host prefs + auto-reply + suspension |
| `in_app_notifications` | Generic / attachment-safe notices (no full bodies) |

**Storage bytes** live outside Postgres under private attachment storage (`MESSAGING_ATTACHMENT_STORAGE_*`); DB holds `storage_key` only (never returned in public serializers).

**Demo chat features:** `app/demo/messaging_chat_features_seed.py` enriches Tolu↔DJ Maze, Chidi↔Bayo, and reported Bayo↔Tech after scripted bodies.

## Fan Connect

See [FAN_CONNECT.md](./FAN_CONNECT.md) and [DEMO_DATA.md](./DEMO_DATA.md#fan-connect-demo).

- `fan_connect_settings` — per-user opt-in flags, discoverability, display toggles, `request_policy`, `hide_private_events_always`
- `fan_connections` — canonical pair (`user_low_id` / `user_high_id`); status `suggested|request_sent|connected|declined|blocked|removed`; requester/recipient; `reasons_json` (safe codes only); score; related public event/host; `message_thread_id`; lifecycle timestamps
- `fan_connection_blocks` — blocker / blocked pairs (+ reason)
- `fan_connection_reports` — Connect reports (`open|reviewing|resolved|dismissed`) with safe connection context
- `fan_connect_suggestions` — optional persisted suggestion rows for demos / ranking aids

**Privacy:** `reasons_json` and admin Connect serializers never store private venues, ticket types, VIP/table, orders, payments, spend, contact, or Vault bodies.

### Demo seed tables / markers

- `demo_entity_markers` — scopes wipe/reset to demo users, hosts, events, and related commerce
- Messaging seed: `app/demo/messaging_seed.py` (idempotent; prunes non-QA threads for allowlisted hosts)
- Chat features seed: `app/demo/messaging_chat_features_seed.py` (edit/reply/pin/star enrichment)
- Privacy guard at seed time: `app/demo/messaging_privacy.py`
- Persona tickets / Vault / reviews for messaging CTAs: `DEMO_PERSONA_CONTEXT` in `app/demo/constants.py`

## Fan Passport (Phase 12+)

See [FAN_PASSPORT.md](./FAN_PASSPORT.md).

- `fan_passports` — one row per buyer (`user_id` unique); denormalized counts + Superfan flag + favorite categories; profile fields (`username`, `avatar_url`, `tagline`, `bio`); visibility (`private`/`unlisted`/`public`, default `public`); `appear_in_directory` (default true); section toggles (`show_*`, `hide_private_events_always`); admin moderation (`admin_hidden_at`, `admin_hidden_reason`)
- `fan_badges` — badge catalog (slug, name, description, criteria_key)
- `user_badges` — awards (`user_id` + `badge_id` unique); `awarded_at`
- `loyalty_records` — per-user-per-host loyalty (tickets, check-ins, VIP purchases, `is_superfan`)

Directory eligibility (application layer): `visibility=public` ∧ `appear_in_directory` ∧ username set ∧ `admin_hidden_at` null ∧ user active.

## Event Memories (Phase 13)

- `event_memories` — one row per event (`event_id` unique); status, host recap note, moderation fields, `published_at`
- `event_memory_media` — gallery media (`url`, `storage_key`, `media_type`, `label`, `sort_order`) via media storage abstraction

## Advanced Analytics (Phase 14)

See [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md) and [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md).

### Raw stream + legacy track tables

- `analytics_events` — append-only taxonomy stream (`event_name` = tracked action); `target_event_id`, host/user, `anonymous_id` / `session_id` / `request_id`, `occurred_at`, UTM + source/medium/campaign, path/landing/referrer, device/browser/os, country/city, `ip_hash` / `user_agent_hash`, scrubbed `metadata`/`properties`, `is_bot`, `environment`
- `page_views` — path + optional host/event; dual-write BC
- `event_impressions` — listing/detail impressions; dual-write BC
- `event_clicks` — CTA clicks; dual-write BC
- `conversion_events` — legacy funnel stages with optional order/amount; dual-write BC

### Daily rollups + dedupe

- `event_daily_analytics` — date × event funnel + revenue rollup
- `event_source_analytics` — date × event × source/medium/campaign
- `event_ticket_type_analytics` — date × event × ticket_type
- `event_geo_device_analytics` — date × event × country/city/device/browser
- `analytics_dedupe_keys` — request / windowed idempotency claims

Recalculate: `python -m scripts.run_analytics_rollups` ([ANALYTICS_ROLLUPS.md](./ANALYTICS_ROLLUPS.md)).

## AI Copilot (Phase 15 + Phase 1 hardening)

- `ai_platform_settings`, `ai_feature_configs` — spend + legacy toggles
- `ai_provider_profiles` — multi-provider Control Center profiles (API key env or encrypted when ready)
- `ai_feature_routes` — per-feature primary/fallback provider + model + limits
- `ai_provider_health_checks` — audited connection tests
- `ai_prompt_templates` — seeded prompt catalog (`slug`, audience host/admin, system + user templates); includes `host.event.title` / `host.event.description`
- `ai_usage_logs` — per-request usage (user/host, feature, provider, fallback, tokens, error); `meta` may include `latency_ms`, `estimated_cost_micros`, `redaction_applied`, feedback history — **no API keys or raw secrets**
- Audit trail via `audit_logs` actions `ai.generation_*` (created / failed / applied / accepted / rejected / dismissed)

## Sponsorship marketplace (Phase 16)

- `sponsors` — brand/sponsor contacts (company, email, optional user link)
- `host_sponsorship_settings` — per-host accepting flag, pitch, audience notes
- `sponsorship_slots` — host listings (type, price, status, moderation)
- `sponsorship_inquiries` — public inquiries (auditable)
- `sponsorship_placements` — confirmed placements linked to slot + sponsor
- `sponsorship_analytics` — impressions / clicks / attributed inquiries per placement

## Advanced ticketing (Phase 17)

- `ticket_types.seats_per_unit` — attendees/seats per inventory unit (group/table)
- `tickets` extras — `qr_mode`, device binding hash, table/seat labels, attendee index
- `ticket_qr_tokens` extras — `rotation_version`, `is_rotating`
- `ticket_transfers` — auditable ownership transfers
- `ticket_groups` / `ticket_group_members` — multi-attendee issuances
- `table_reservations` — table/seat assignment placeholders
- `offline_scan_batches` / `offline_scan_items` — offline scanner sync + conflicts

### Admin event buyer export (no dedicated table)

Exports read `tickets` + `orders` (+ payment/refund status, check-ins, Fan Passport, host profile) and append platform `audit_logs` with actions `admin_event_buyers_exported` / `admin_event_buyers_private_contact_exported` / `admin_event_buyers_finance_exported`. Details JSON holds `admin_user_id`, `event_id`, `host_profile_id`, `export_mode`, `format`, `filters_json`, `row_count`, `reason`; columns `ip_address` / `user_agent` on the audit row. Permissions live in seeded RBAC (`admin.events.*`, `admin.finance.export_event_sales`) — not a separate export store.

## Taxonomy & content graph

Authoritative contract: [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md). Migration `20260717_0023_taxonomy_graph`.

### Taxonomy model (vocab)

| Table | Notes |
| --- | --- |
| `taxonomy_categories` | Slug-unique browse categories; SEO fields; archive via `archived_at` |
| `taxonomy_subcategories` | `category_id` + slug unique per parent |
| `taxonomy_tags` | Multi-select tags |
| `taxonomy_vibes` | Mood labels |
| `taxonomy_audience_types` | Audience segments |
| `host_types` | Host niche types |
| `venue_types` | Venue kind catalog |
| `locations` | Tree: `kind` (`country`/`state`/`city`/`area`), `parent_id`, `slug`, `state_code`, `country_code`, `is_active` (no `archived_at`). Seed: Nigeria → Lagos/Oyo/Ondo/FCT → cities → Lagos areas (Lekki, VI, Ikeja, Yaba, Mainland). |

### Featured placements (Pàdéyá Picks)

Migrations `20260717_0024`–`0027`. Not sponsorship `sponsorship_placements`.

| Table | Notes |
| --- | --- |
| `featured_placements` | Unique `(placement_key, slot_number)`; `slot_number` ∈ {1, 2} |

Columns: `placement_key`, `placement_type`, `context_type`, `context_id`, `country_id`/`state_id`/`city_id`/`area_id` → `locations.id`, `category_id` → `event_categories.id`, `event_id` → `events.id` (nullable for empty draft), `title_override`, `subtitle_override`, `badge_text`, `starts_at`, `ends_at`, `status`, `created_by`/`updated_by`, timestamps.

Checks: `placement_type` ∈ `homepage` \| `events_page` \| `country_page` \| `state_page` \| `city_page` \| `area_page` \| `category_page` \| `city_category_page`; `status` ∈ `draft` \| `active` \| `scheduled` \| `expired` \| `archived`.

### Relationship / link model

| Table | Notes |
| --- | --- |
| `event_taxonomy_links` | Event ↔ vocab (`link_type`, `taxonomy_id`, `taxonomy_slug`) |
| `host_taxonomy_links` | Host ↔ host_type / category / audience |
| `host_location_links` | Host ↔ location; `is_primary` for primary city |
| `content_relationships` | Graph edges: `source_*`, `target_*`, `relationship_type`, `weight`, `reason`, `expires_at`; unique edge key |

### Event dual-write / privacy columns

- `events.primary_category_id` → `taxonomy_categories` (nullable; dual-write with `category_id` → `event_categories`)
- `events.location_id` → `locations` (nullable; dual-write with flat `city` / `state`)
- Privacy: `location_visibility` (default `full_public`), `reveal_timing`, `reveal_note`, `public_location_label`, `online_event_url`, `online_url_reveal_rule`
- Redaction is **serializer-time** (`privacy.py`) — private street stays in DB for host/admin/eligible buyers; public API nulls `address` and scrubs SEO when hidden

### Lifecycle

- Archive/deactivate preferred; hard delete blocked at API (405) for taxonomy.
- Placement sets: prefer `archived` / clear to `draft` over hard delete; slot rows retained.
- Indexes: slug uniques; `events(primary_category_id, start_datetime)`; `events(location_id, start_datetime)`; link `(link_type, taxonomy_slug)`; graph source/target composites; placements by `placement_key`, `status`, location/category FKs.

### Future (not shipped)

- First-class `venues` + `events.venue_id`
- `vault_taxonomy_links`, `memory_taxonomy_links`, `sponsorship_taxonomy_links`
- Slug redirect table for hub renames
- Wave 6: cutover off free-text `events.city` as discovery source of truth (keep dual-write display fields)