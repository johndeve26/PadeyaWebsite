# API

## Base

- Local: `http://localhost:8000`
- Prefix: `/api/v1`
- Docs: `/docs`

## Phases 2–7

Auth, hosts, events, payments, check-in, reviews, and Legacy tiers remain as documented in prior phases. Auth + impersonation contracts: [AUTH.md](./AUTH.md) · [SECURITY.md](./SECURITY.md#admin-user-impersonation).

## Admin user impersonation

**Internal support/QA** — audited session, **not** a real login. Permission: `admin.users.impersonate` (`super_admin` via `admin.full_access`; support/finance need explicit grant; buyers/hosts/host_staff never). Durations: **15 / 30 / 60** minutes (default **30**, max **60**). No password access; no target refresh-token hijack; sensitive mutations blocked; **target is never notified** (no email / in-app / push); admin and target identities stay separated (`actor_admin_id` vs `current_user_id`). Audit logs are retained.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/admin/users/{user_id}/impersonation/start` | `admin.users.impersonate` | Start audited session |
| POST | `/api/v1/admin/impersonation/end` | Impersonation token | End session |
| GET | `/api/v1/me/impersonation` | Any bearer | Current impersonation status |
| GET | `/api/v1/admin/users/{user_id}/impersonation/history` | `admin.users.impersonate` | Session history for target |
| GET | `/api/v1/me/session` | Any bearer | `current_user_id`, `actor_admin_id`, `impersonation_id`, `is_impersonating` |

### Start

`POST /api/v1/admin/users/{user_id}/impersonation/start`

```json
{
  "reason": "...",
  "support_ticket_id": "... optional",
  "duration_minutes": 30
}
```

Response:

```json
{
  "impersonation_id": "...",
  "target_user_id": "...",
  "expires_at": "...",
  "redirect_to": "/dashboard",
  "access_token": "...",
  "token_type": "bearer"
}
```

`access_token` is a **separate** short-lived impersonation JWT (target roles only). No `refresh_token`. Never returns passwords.

### End

`POST /api/v1/admin/impersonation/end`

```json
{
  "ended": true,
  "return_to": "/admin/users/{user_id}"
}
```

### Status

`GET /api/v1/me/impersonation` → `{ is_impersonating, impersonation_id?, target_user_id?, actor_admin_id?, reason?, expires_at?, ... }`

### Impersonation rules

- Required `reason` (≥ 3 chars). Blocked targets: self, platform admins, finance admin, security-locked, deleted/missing.
- Session claims: `actual_user_id`, `actor_admin_id`, `impersonation_id`, `is_impersonating`, `started_at`, `expires_at`, `reason` (+ target-only roles/permissions).
- Current user = target; actor admin stored separately; admin permissions never leak; `/admin` blocked while impersonating; no nested impersonation.
- Duration: default **30** min, max **60** (`15`/`30`/`60`). Auto-expire; end on Exit (`POST /admin/impersonation/end`) and on logout.
- Sensitive actions → `403` `This action is disabled during admin impersonation.` (audited as `admin_impersonation_sensitive_action_blocked`). Full allow/deny list: [SECURITY.md](./SECURITY.md#blocked--allowed-during-impersonation).
- **Do not notify** the target on start or end (no in-app / email / push templates for impersonation).
- **Audit logs retained**: actor admin, target, reason, support ticket (if provided), start/end/expiry, visited routes (`request_made`), blocked sensitive actions.
- Tables: `admin_impersonation_sessions`, `admin_impersonation_audit_logs` — [DATABASE.md](./DATABASE.md#admin-user-impersonation).

## Admin user management (safe actions)

**Canonical surface:** `/api/v1/admin/users*`. Legacy aliases remain under `/api/v1/users/admin*` for compatibility.  
FE: `/admin/users`, `/admin/users/[userId]` — [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · product: [ADMIN.md](./ADMIN.md#user-management-safe-actions) · lifecycle: [CRUD_MATRIX.md](./CRUD_MATRIX.md).

**No hard delete**, password/token reveal, or unsafe role editing.

**View** (`admin.users.view`; `admin.full_access` covers all): list, detail, notes (read), flags (read).  
`admin.users.view` implies `admin.users.view_activity` and `admin.users.view_audit`.  
**Mutations** use granular codes: `add_note`, `flag`, `restrict`, `suspend`, `force_logout`, `force_password_reset`.  
Private contact / security details: **email is always returned** on admin user list/detail (audited). Phone and related fields require `view_private_contact` / `view_security` when present.

**Permissions summary:** `admin.users.view` · `view_private_contact` · `view_activity` · `view_security` · `add_note` · `flag` · `restrict` (legacy umbrella) · `view_restrictions` · `add_restriction` · `revoke_restriction` · `suspend` · `ban` · `force_logout` · `force_password_reset` · `view_audit` · `impersonate`.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/users` | `admin.users.view` | Paginated user directory (`q`, `status`, `role`, `page`, `limit`) |
| GET | `/api/v1/admin/users/{user_id}` | `admin.users.view` | Admin detail (sections filtered by granular view perms) |
| GET | `/api/v1/admin/users/{user_id}/activity` | `admin.users.view_activity` | Activity slice from detail |
| GET | `/api/v1/admin/users/{user_id}/activity/{kind}` | `admin.users.view_activity` | Paginated Activity drill-down (`tickets` \| `orders` \| `merch` \| `refunds` \| `reviews` \| `hosts` \| `teams` \| `ambassadors`; `page`, `limit`). Finance fields gated by `payments.view` / refund / ambassador payouts perms. Audited `admin_user_activity_detail_viewed`. No passwords, tokens, QR secrets, private bodies, or raw payment payloads. |
| GET | `/api/v1/admin/users/{user_id}/audit` | `admin.users.view_audit` | Recent audit rows for user |
| POST | `/api/v1/admin/users/{user_id}/notes` | `admin.users.add_note` | Append internal note — `{ note_type, body }` |
| GET | `/api/v1/admin/users/{user_id}/notes` | `admin.users.view` | List internal notes |
| POST | `/api/v1/admin/users/{user_id}/flags` | `admin.users.flag` | Add flag — `{ flag_type, severity, reason, internal_note? }` |
| PATCH | `/api/v1/admin/users/{user_id}/flags/{flag_id}` | `admin.users.flag` | Soft-close flag — `{ status: resolved\|dismissed, reason, resolution_note? }` |
| POST | `/api/v1/admin/users/{user_id}/status` | `restrict` and/or `suspend`/`ban` (service-checked) | Global status — `{ status, reason, reason_category?, ends_at?, restrictions? }` (prefer restrictions API for selective limits) |
| GET | `/api/v1/me/suspension` | Authenticated (incl. suspended) | Public-safe active suspension + pending appeal |
| POST | `/api/v1/appeals` | Authenticated + suspended | Submit appeal — `{ message }` (10–4000 chars) |
| GET | `/api/v1/admin/appeals` | `admin.appeals.review` or `admin.users.suspend` | List appeals (`?status=&page=&limit=`) |
| GET | `/api/v1/admin/appeals/{appeal_id}` | same | Appeal detail |
| POST | `/api/v1/admin/appeals/{appeal_id}/approve` | same | Approve → unsuspend — `{ admin_reply? }` |
| POST | `/api/v1/admin/appeals/{appeal_id}/reject` | same | Reject — `{ admin_reply? }` (user-facing) |
| GET | `/api/v1/admin/users/{user_id}/restrictions` | `view_restrictions` (or `view` / `restrict`) | List restrictions (active + history) |
| POST | `/api/v1/admin/users/{user_id}/restrictions` | `add_restriction` (or `restrict`) | Apply keys / preset — creates active rows; never wipes history |
| PATCH | `/api/v1/admin/users/{user_id}/restrictions/{restriction_id}` | `add_restriction` (or `restrict`) | Extend / update (`ends_at`, optional note) — `{ reason, ends_at?, internal_note? }` |
| POST | `/api/v1/admin/users/{user_id}/restrictions/{restriction_id}/revoke` | `revoke_restriction` (or `restrict`) | Soft-revoke — `{ reason }` required; row kept |
| POST | `/api/v1/admin/users/{user_id}/force-logout` | `admin.users.force_logout` | Revoke all refresh sessions — `{ reason }` required |
| POST | `/api/v1/admin/users/{user_id}/force-password-reset` | `admin.users.force_password_reset` | Email password-reset link — `{ reason }` required |

**POST `/restrictions` body:** `{ restriction_keys, reason, internal_note?, ends_at?, preset?, force_full_suspension? }`. `restriction_keys` + `reason` required (unless preset supplies keys). `ends_at` null/omitted = indefinite. Presets: `messaging` · `buyer` · `host` · `ambassador` · `read_only` · `full_suspension`. Full suspension also sets `account_status=suspended` and requires `admin.users.suspend`.

Legacy aliases: `/users/admin/*` (including `/account-status`, `/sessions/revoke-all`, `/password-reset`, flag resolve/dismiss POSTs, suspend/unsuspend).

### Admin user response safety

Admin user JSON **never** includes: `password`, `hashed_password`, `password_hash`, `reset_token`, `email_verification_token`, `refresh_token`, `access_token`, `session_token`, OAuth tokens, `2FA`/`totp` secrets, QR payload/secret, merch pickup token, Paystack/raw payment provider payloads/secrets, or private message bodies.

Safe derived fields are preferred instead: `email_masked`, `phone_masked` / `phone_available`, `last_four`, `configured`, `status`, counts, timestamps. Enforced by `app.users.admin_response_safety` on list/detail/serialize paths.

`/me` and session payloads expose **restriction keys only** (`account_restrictions` / `restriction_keys`) — never admin `reason` or `internal_note`.

Admin user management also writes scrubbed platform `audit_logs` events: `admin_user_viewed`, `admin_user_private_contact_viewed`, `admin_user_note_created`, `admin_user_flag_created`, `admin_user_flag_updated`, `admin_user_status_changed`, `admin_user_restriction_added`, `admin_user_restriction_revoked`, `admin_user_restriction_extended`, `admin_user_restriction_preset_applied`, `restricted_user_blocked_from_action`, `admin_user_force_logout`, `admin_user_force_password_reset`, `admin_user_suspension_notified`, `account_appeal_submitted`, `account_appeal_approved`, `account_appeal_rejected`, `admin_user_unsuspended` — details carry `admin_user_id`, `target_user_id`, optional `restriction_keys` / `reason` / `internal_note_present` (boolean) / `before_json` / `after_json` (never note bodies or secrets). See [ADMIN.md](./ADMIN.md#audit-log-events).

Migration `20260720_0092`: `user_admin_notes`, `user_admin_flags`, `users.under_review_at` / `under_review_reason`.  
Migration `20260720_0093`: flag MVP fields — `flag_type`, `severity`, `internal_note`, `created_by_admin_id`, `resolved_by_admin_id`; status `active` (was `open`).  
Migration `20260720_0094`: notes MVP — `note_type`, `created_by_admin_id`, nullable `updated_at`.

**User flag types:** `suspicious_payment_activity`, `refund_abuse`, `ticket_resale_risk`, `chargeback_risk`, `spam`, `harassment`, `fake_profile`, `impersonation_risk`, `event_safety_risk`, `fraud_review`, `policy_violation`, `under_review`, `trusted_user`, `vip_support`, `manual_watchlist`.  
**Severity:** `low` \| `medium` \| `high` \| `critical`. **Status:** `active` \| `resolved` \| `dismissed`. Every add/resolve/dismiss writes `audit_logs` (`admin_user_flag_created` / `admin_user_flag_updated`).

Migration `20260720_0095`: `users.account_status`, `users.account_restrictions` (JSON mirror of active keys).  
Migration `20260720_0096`: `user_restrictions` history table; migrates legacy JSON + `ambassadors_blocked`.  
Migration `20260720_0097`: `account_suspensions` + `account_appeals`.

**Account statuses:** `active`, `under_review`, `restricted`, `suspended`, `banned`, `deleted`.  
Writable transitions include soft/partial among `active` / `under_review` / `restricted`; `* → suspended|banned`; `suspended|banned → active`. Every change requires a reason and writes `admin_user_status_changed`. Global statuses win over `restricted` until cleared. Suspended users may authenticate only for `/me`, `/me/suspension`, `/appeals`, and auth routes; product APIs return 403.

**Suspension notify:** on suspend → in-app + email (if email) + push (if enabled); payload shows `reason_category`, duration, date only — never admin notes or fraud logic. Templates: `account_suspended`, `account_appeal_approved`, `account_appeal_rejected`.

**Selective restrictions** (primary): append-only `user_restrictions` rows (`active` \| `expired` \| `revoked`). Catalog keys (groups: personal, community, host, ambassador, account, admin) in `account_status_constants.py`. Legacy `cannot_promote_as_ambassador` → `cannot_join_ambassador_campaigns`. Any ambassador-group key syncs `users.ambassadors_blocked`. Enforcement: `assert_no_restriction` → 403 at checkout, tickets, refunds, reviews, messaging, Fan Connect, following, passport, vault, host, and ambassador gates.

## Event Studio (host create / edit)

Canonical host create/edit surface. Nested Studio fields ride on event create/update; ticket types and media have dedicated routes. Lifecycle inventory: [CRUD_MATRIX.md](./CRUD_MATRIX.md). Privacy contract: [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md) §6.

### Host event routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/events` | Create draft (`EventCreate`) |
| GET | `/api/v1/events/by-id/{id}` | Host/admin detail (full address; includes `publish_checklist`) |
| PATCH | `/api/v1/events/by-id/{id}` | Update + nested upsert (`EventUpdate`; optional `slug`) |
| POST | `/api/v1/events/by-id/{id}/submit` | Draft/rejected/paused → `pending_review` |
| POST | `/api/v1/events/by-id/{id}/approve` \| `/reject` | Admin review |
| POST | `/api/v1/events/by-id/{id}/pause` \| `/resume` \| `/postpone` \| `/cancel` \| `/complete` \| `/archive` \| `/restore` | Lifecycle |
| DELETE | `/api/v1/events/by-id/{id}` | Discard **draft/rejected only**, and only when ticket `quantity_sold` is 0 |
| GET | `/api/v1/events/{slug}` | Public detail; optional auth upgrades access to buyer/host/admin |
| GET | `/api/v1/events` | Public list (`access=public`; privacy applied) |

### Nested create / update fields

| Group | Fields |
| --- | --- |
| Core | `title`, `description`, `short_tagline`, `vibe`, `event_type`, `visibility`, `category_id` |
| Taxonomy place | `location_id` (dual-writes city/state/label when set); `primary_category_id` mirrored from `category_id` by slug |
| Location privacy | `venue_name`, `venue_type`, `address`, `city`, `state`, `country`, `area`, `postcode`, exact `latitude`/`longitude`, `google_maps_share_url`/`google_maps_place_url`, `public_location_label`, `approximate_latitude`/`approximate_longitude`/`approximate_map_label`, `location_visibility`, `reveal_timing`, `reveal_note`, `online_event_url`, `online_url_reveal_rule`, nested `venue` |
| Public map (computed) | `location_map_mode` (`exact`\|`approximate`\|`none`), `map_latitude`/`map_longitude`/`map_label`/`map_open_url` — privacy-safe; exact coords/URLs nulled when address not revealed |
| Schedule | `start_datetime`, `end_datetime`, `doors_open_datetime`, `timezone`, `agenda_items[]` |
| Lineup | `people[]` |
| Questions | `checkout_questions[]` (active/archived) |
| Media URLs | `banner_url`, `mobile_banner_url`, `teaser_video_url`, `social_share_image_url`, `brand_accent_override`, `sponsor_logo_urls`, `gallery_urls` |
| Policies | `capacity`, refund/cancellation/age/ID/safety/terms, door/re-entry, check-in windows, dress/parking/what-to-bring/prohibited/entry |
| SEO | `seo_title`, `seo_description`, `social_share_*`, `hashtags`, `discoverable_keywords` |

**Enums (selected):**

- `location_visibility`: `full_public` · `area_only` · `hidden_until_payment` · `hidden_until_24h_before` · `hidden_until_manual_approval` · `online_only`
- `reveal_timing` / `online_url_reveal_rule`: `immediately` · `after_payment` · `twenty_four_hours_before` · `manual_approval` · `event_day`
- Agenda `type`: `doors_open` · `performance` · `speaker` · `break` · `networking` · `after_party` · `other`
- Question `type`: `short_text` · `long_text` · `dropdown` · `checkbox` · `phone` · `email`
- Question `status`: `active` · `archived`

### Subresource sync (PATCH semantics)

| Resource | Behavior |
| --- | --- |
| Agenda / people | **Upsert-by-`id`**. Rows omitted from the array are hard-deleted (no commerce refs). |
| Checkout questions | Upsert-by-`id`. Unused omit → hard delete. Omit with existing `order_checkout_answers` → **archive** (`status=archived`, `archived_at`). Already-archived rows are retained. |
| Gallery | `gallery_urls` syncs `event_media` gallery rows by URL |
| Venue | Nested 1:1 upsert |

Dedicated media: `POST .../media`, `POST .../media/upload`, `DELETE .../media/{media_id}` (clears matching banner/mobile/social URL fields when applicable).

### Ticket types

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/api/v1/events/by-id/{id}/ticket-types` | List / create |
| PATCH | `/api/v1/events/by-id/{id}/ticket-types/{tt_id}` | Update (after sales: structural fields blocked — price/type/name/quantity/seats/min/max) |
| POST | `.../ticket-types/{tt_id}/deactivate` | `status=inactive` (always allowed) |
| DELETE | `.../ticket-types/{tt_id}` | Hard delete **only** if `quantity_sold=0` and `quantity_reserved=0`; else `400` — deactivate instead |

Statuses: `active` · `inactive` · `sold_out`. Visibility: `public` · `hidden` · `invite_only`. Checkout requires `active` and not `hidden`.

### Checkout questions on orders

`POST /api/v1/orders` accepts optional `checkout_answers: [{ question_id, value }]`.

- Only **active** questions are enforced / returned on public event payloads.
- Required questions must be non-empty; `dropdown`/`checkbox` must match `options`; `email` / `phone` format-checked.
- Answers persist as immutable `order_checkout_answers` snapshots (label/type copied at purchase).

### Location privacy & access levels

`resolve_event_access`: anonymous → `public`; paid ticket (`active` / `checked_in`) → `buyer`; event host → `host`; `super_admin` → `admin`.

`serialize_event` + `apply_location_privacy`:

| Access | Street address / private online URL |
| --- | --- |
| `host` / `admin` | Always full |
| `buyer` | Per `location_visibility` / reveal rules (e.g. `hidden_until_payment` → full address after purchase) |
| `public` | Never when visibility is not `full_public`; SEO/social/hashtags/keywords scrub street fragments |

Public responses expose `location_address_revealed`, `public_location_label`, `location_privacy_message`; `address` is `null` when hidden. Taxonomy `location_id` stays for discovery — street never lives on the location node.

### Publish checklist

**Not a database table.** Host/admin event payloads include computed `publish_checklist` from `build_publish_checklist()`.

| Flag | True when |
| --- | --- |
| `basics_complete` | Title + description (≥10 chars) |
| `category_complete` | `category_id` set |
| `venue_privacy_complete` | Venue name **or** `online_only` **or** `public_location_label` **or** `location_id` |
| `date_complete` | Start + end + timezone |
| `has_ticket_type` | ≥1 ticket type |
| `banner_ready` | Always `true` (listing placeholders) |
| `refund_policy_selected` | `refund_policy_type` or `refund_policy` |
| `check_in_settings_complete` | Check-in start **or** doors **or** start datetime |
| `seo_complete` | `(seo_title or title)` and `(seo_description or short_tagline or description)` |
| `preview_checked` | Client argument only — **never persisted** |
| `ready_to_submit` | All flags including `preview_checked` |

`POST .../submit` does **not** enforce the checklist server-side (status gate only). Studio FE gates submit with local checklist + `sessionStorage` preview flag. Public list/detail set `publish_checklist` to `null`.

Tests: `tests/test_event_studio_lifecycle.py`, `test_event_location_privacy.py`, `test_event_subresource_lifecycle.py`, `test_event_lifecycle.py`.

## Ambassadors domain API (Phase 10)

**Canonical product rules:** [AMBASSADORS.md](./AMBASSADORS.md). Ticket discounts: [PROMO_CODES.md](./PROMO_CODES.md).

Preferred surface under `/api/v1/ambassadors/*` (domain tables). Legacy `/promos/*` ambassadors routes remain for existing FE until cutover. Click tracking exists on both stacks (`POST /ambassadors/track-click` and `POST /promos/referrals/click`) — both are rate-limited and store hashed IP/UA only.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/ambassadors/eligible-events` | Public | Joinable campaign events |
| POST | `/api/v1/ambassadors/join` | User | Join via `campaign_id` or `event_id` + terms |
| GET | `/api/v1/ambassadors/me` | User | Ambassador profile |
| GET | `/api/v1/ambassadors/me/campaigns` | User | Active/paused participations |
| GET | `/api/v1/ambassadors/me/links` | User | Share paths + codes |
| GET | `/api/v1/ambassadors/me/earnings` | User | Conversion earnings summary |
| GET | `/api/v1/ambassadors/campaigns/{id}` | Public | Campaign public detail |
| GET | `/api/v1/events/{slug}/ambassador-status` | Optional user | Enabled + joined state |
| POST | `/api/v1/events/{slug}/ambassador/join` | User | Join by event slug |
| GET | `/api/v1/events/{slug}/ambassador/link` | User | Own link for event |
| POST | `/api/v1/ambassadors/track-click` | Public | Click + attribution (rate-limited; hashed IP/UA) |
| POST | `/api/v1/ambassadors/track-checkout-started` | Optional user | Refresh attribution at checkout |
| GET | `/api/v1/admin/ambassadors/fraud-flags` | Admin | Click-spike / fraud flags |
| GET/POST | `/api/v1/host/ambassadors/campaigns` | Host | List / create |
| GET/PATCH | `/api/v1/host/ambassadors/campaigns/{id}` | Host | Detail / update |
| POST | `/api/v1/host/ambassadors/campaigns/{id}/pause\|end` | Host | Lifecycle |
| GET | `/api/v1/host/ambassadors/campaigns/{id}/participants` | Host | Participants + clicks |
| POST | `/api/v1/host/ambassadors/participants/{id}/remove` | Host | Soft-remove participant |
| GET | `/api/v1/host/ambassadors/analytics` | Host | Host-wide Ambassadors stats |
| GET | `/api/v1/host/ambassadors/payouts` | Host / team `view_payouts` | Ambassador payout summary (not host-balance payouts) |
| GET | `/api/v1/host/ambassadors/conversions` | Host / team `view_conversions` | Host-owned conversion ledger (no buyer/order refs) |
| GET | `/api/v1/host/ambassadors/conversions/{id}/audit` | Host / team | Per-conversion reward audit |
| GET | `/api/v1/host/ambassadors/reward-audit` | Host / team | Workspace reward audit feed |
| POST | `/api/v1/host/ambassadors/conversions/{id}/reward-status` | Host / team reward perms | Normal approve / reject / mark paid / reverse (no `admin.full_access`) |
| POST | `/api/v1/host/ambassadors/conversions/{id}/flag` | Host / team | Flag suspicious conversion |
| GET | `/api/v1/host/ambassadors/conversions/export` | Host / team `export` | CSV export |
| GET | `/api/v1/admin/ambassadors` | Admin | Profiles |
| GET | `/api/v1/admin/ambassadors/campaigns` | Admin | All campaigns |
| GET | `/api/v1/admin/ambassadors/conversions` | Admin | Domain conversion ledger (may include order refs) |
| GET | `/api/v1/admin/ambassadors/reward-audit` | Admin | Platform-wide reward audit |
| GET | `/api/v1/admin/ambassadors/payouts` | Admin | Payouts |
| POST | `/api/v1/admin/ambassadors/participants/{id}/block` | Admin | Block participant |
| POST | `/api/v1/admin/ambassadors/conversions/{id}/reverse` | Admin | Reverse conversion |

Body for host `reward-status`: `{ status: approved|rejected|paid|reversed, reason?, payout_reference?, payout_note? }`. Admin oversight: `POST /api/v1/promos/admin/conversions/{sale_id}/reward-status` (`admin.full_access`). Package: `backend/app/ambassadors/`. Tests: `tests/test_ambassadors_api_v2.py`, `tests/test_ambassador_host_rewards.py`.

## Promos & ambassadors (legacy Phase 8 `/promos`)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET/POST | `/api/v1/promos/codes` | Host | List / create promo codes |
| PATCH | `/api/v1/promos/codes/{id}` | Host | Update promo (status, limits, etc.) |
| POST | `/api/v1/promos/validate` | User | Preview discount (server-side) |
| POST | `/api/v1/promos/referrals/click` | Public | Track `?ref=` click |
| GET/POST | `/api/v1/promos/ambassadors` | Host | List / create host-curated ambassadors |
| GET/PATCH | `/api/v1/promos/ambassadors/{id}` | Host | Detail + performance / update |
| GET | `/api/v1/promos/ambassador/me` | Ambassador user | Primary linked dashboard (legacy single) |
| GET | `/api/v1/promos/ambassador/enrollments` | User | All ambassador enrollments (open + curated) |
| GET | `/api/v1/promos/events/{event_id}/ambassadors/program` | Public | Open Ambassadors enabled + commission type/value |
| GET/POST | `/api/v1/promos/campaigns` | Host | List / create Ambassadors campaigns (`campaign_type`: `event_tickets` \| `event_merch`) |
| GET | `/api/v1/promos/events/{event_id}/campaigns` | Host | Open campaigns for event (both types) |
| GET/PATCH | `/api/v1/promos/campaigns/{id}` | Host | Campaign detail / update |
| POST | `/api/v1/promos/campaigns/{id}/pause\|resume\|end` | Host | Lifecycle |
| GET | `/api/v1/promos/campaigns/{id}/leaderboard` | Host | Ranked ambassadors |
| POST | `/api/v1/promos/campaigns/{id}/ambassadors/{aid}/remove` | Host | Remove abusive ambassador |
| GET | `/api/v1/promos/events/{event_id}/campaign` | Host | Active/paused campaign for event |
| GET | `/api/v1/promos/ambassadors/eligible-events` | Public | Published events with live campaigns |
| POST | `/api/v1/promos/events/{event_id}/ambassadors/join` | User | Join open Event Ambassadors (`{ accept_terms: true }`) |
| GET | `/api/v1/promos/ambassador/earnings-summary` | User | Estimated / approved / payable / payout status |
| GET/PATCH | `/api/v1/promos/admin/settings` | Admin | Global Ambassadors enable/disable |
| GET/POST | `/api/v1/promos/admin/campaigns` | Admin | List all / create platform campaign |
| POST | `/api/v1/promos/admin/campaigns/{id}/pause\|resume` | Admin | Pause/resume any campaign |
| GET | `/api/v1/promos/admin/ambassadors` | Admin | Search enrollments + block state |
| POST | `/api/v1/promos/admin/ambassadors/{id}/block\|unblock` | Admin | Block linked user from Ambassadors |
| GET | `/api/v1/promos/admin/conversions` | Admin | Conversion ledger |
| POST | `/api/v1/promos/admin/conversions/{id}/reverse` | Admin | Reverse fraudulent conversion |
| POST | `/api/v1/promos/admin/conversions/{id}/reward-status` | Admin | Oversight reward status (fraud / platform campaigns / emergency). Normal host-owned workflow: `POST /host/ambassadors/conversions/{id}/reward-status` — does **not** require `admin.full_access` |
| GET | `/api/v1/promos/admin/reports/summary` | Admin | Platform Ambassadors totals |
| POST | `/api/v1/users/admin/{user_id}/ambassadors/block` | Admin | Block user from Ambassadors programs |
| POST | `/api/v1/users/admin/{user_id}/ambassadors/unblock` | Admin | Unblock Ambassadors |
| GET | `/api/v1/promos/events/{event_id}/ambassadors/me` | User | Own open enrollment for event |
| POST | `/api/v1/promos/events/{event_id}/ambassadors/leave` | User | Leave (deactivate) open enrollment |

Open Event Ambassadors overview: [AMBASSADORS.md](./AMBASSADORS.md).

### Checkout

`POST /api/v1/orders` accepts optional:

- `promo_code` — validated and discounted **only on the backend** (ticket lines only; rejected for merch-only carts)
- `referral_code` — attributes order to an active ambassador for the event host
- `checkout_answers` — answers to the event’s **active** checkout questions (see Event Studio above)
- `items[]` — polymorphic lines: ticket / merch / `bundle` (`bundle_id`) for the same `event_id`
- Optional: `merch_discount_code`, `fulfillment_method` (`pickup`|`shipping`), `shipping_address` (encrypted server-side; never returned publicly)

Redemption and ambassador sales/conversions are finalized inside payment success (`finalize_successful_payment`), not from the frontend. Domain path: pending order stores `ambassador_participant_id`; webhook calls `finalize_ambassador_conversions`; refunds call `reverse_conversions_for_order`. Merch inventory deducts and `merch_fulfillments` are created there — never from the browser. Product rules: [MERCHANDISE.md](./MERCHANDISE.md) · technical index: [MERCH.md](./MERCH.md).

## Event merch (Phase 1)

Product concept, host/buyer workflows, inventory, fulfillment, privacy, and moderation: [MERCHANDISE.md](./MERCHANDISE.md).

Canonical routes live under `/api/v1/merch/*`. Commerce expansion (storefront, bundles, discounts, QR scan, reviews, revenue, cart, POD): [COMMERCE.md](./COMMERCE.md). Preferred REST aliases (same handlers):

| Method | Alias | Delegates to |
| --- | --- | --- |
| GET/POST | `/api/v1/host/events/{event_id}/merchandise` | host product list/create |
| GET/PATCH | `/api/v1/host/events/{event_id}/merchandise/{product_id}` | get/update |
| PATCH | `.../pause` · `.../archive` | pause status / archive |
| GET | `/api/v1/host/events/{event_id}/merchandise/orders` | host fulfillments |
| PATCH | `/api/v1/host/merchandise/order-items/{id}/ready` · `.../picked-up` | ready / mark fulfilled |
| GET | `/api/v1/events/{event_slug}/merchandise` | public catalog by slug |
| GET | `/api/v1/events/{event_slug}/merchandise/{product_slug}` | public product |
| GET | `/api/v1/dashboard/merchandise` · `/{item_id}` | buyer `/merch/mine` |
| GET | `/api/v1/admin/merchandise` | admin product list |
| PATCH | `/api/v1/admin/merchandise/{id}/hide` · `.../restore` | moderate hide/restore |

Checkout money path stays `POST /api/v1/orders` (ticket / merch / `bundle` lines). Abandoned-cart APIs (`/dashboard/cart`) resume into orders — they are not a parallel payment ledger.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/merch/events/{event_id}/catalog` | Public | Active sellable products |
| GET | `/api/v1/merch/host/products` | Host | All products across host events |
| GET | `/api/v1/merch/host/events/{event_id}/stats` | Host | Studio stats (revenue/sold/pickup — no payment secrets) |
| POST | `/api/v1/merch/products/{id}/duplicate` | Host | Clone product as draft |
| POST | `/api/v1/merch/fulfillments/{id}/notes` | Host/staff | Append fulfillment desk note |
| GET | `/api/v1/merch/products/{id}` | Host | Single product |
| GET/POST | `/api/v1/merch/events/{event_id}/products` | Host | List / create products |
| PATCH | `/api/v1/merch/products/{id}` | Host | Update / pause |
| POST | `/api/v1/merch/products/{id}/archive` | Host | Soft archive |
| POST | `/api/v1/merch/products/{id}/variants` | Host | Add variant |
| PATCH | `/api/v1/merch/variants/{id}` | Host | Update stock/status |
| POST | `/api/v1/merch/variants/{id}/archive` | Host | Soft archive variant |
| GET | `/api/v1/merch/host/events/{event_id}/fulfillments` | Host/staff | Pickup queue |
| POST | `/api/v1/merch/fulfillments/{id}/fulfill` | Host/staff | Mark picked up |
| PATCH | `/api/v1/merch/fulfillments/{id}` | Host/staff | Status (`awaiting_pickup` / `collect_at_stand` / `fulfilled`) |
| GET | `/api/v1/merch/mine` | Buyer | Purchases + pickup codes |
| POST | `/api/v1/merch/products/{id}/report` | Buyer | Report listing |
| GET | `/api/v1/merch/admin/products` | Admin | Oversight list |
| POST | `/api/v1/merch/admin/products/{id}/moderate` | Admin | flag/clear/hide/remove/restore |
| POST | `/api/v1/merch/admin/products/{id}/deactivate-unsafe` | Admin | Pause+hide if host/event unsafe |
| GET | `/api/v1/merch/admin/orders` | Admin | Fulfillments/issues (no payment amounts) |
| GET | `/api/v1/merch/admin/reports` | Admin | Report queue |
| POST | `/api/v1/merch/admin/reports/{id}/resolve` | Admin | Resolve/dismiss (+ optional moderate) |

### Merch commerce expansion

Product index: [COMMERCE.md](./COMMERCE.md). Router: `backend/app/merch/commerce_router.py`.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/u/{username}/merch` | Public | Host storefront catalog |
| GET | `/api/v1/u/{username}/merch/{product_id}` | Public | Storefront product (teasers when Vault/drop locked) |
| GET/PATCH | `/api/v1/host/merchandise/storefront` | Host | Storefront settings |
| GET/POST | `/api/v1/host/events/{event_id}/bundles` | Host | List / create bundles |
| GET/PATCH | `/api/v1/host/events/{event_id}/bundles/{bundle_id}` | Host | Get / update |
| POST | `/api/v1/host/events/{event_id}/bundles/{bundle_id}/archive` | Host | Soft archive |
| GET | `/api/v1/events/{event_id}/bundles` | Public | Active sellable bundles for event |
| GET/POST | `/api/v1/host/merchandise/discounts` | Host | List / create merch discount codes |
| PATCH | `/api/v1/host/merchandise/discounts/{id}` | Host | Update |
| POST | `/api/v1/host/merchandise/discounts/{id}/archive` | Host | Soft archive |
| POST | `/api/v1/merch/discounts/validate` | Optional | Preview merch discount (no redeem) |
| GET/POST | `/api/v1/host/merchandise/shipping-zones` | Host | Flat shipping zones |
| POST | `/api/v1/host/merchandise/order-items/{id}/ship` · `…/deliver` | Host/staff | Shipping fulfillment |
| POST | `/api/v1/host/events/{event_id}/merchandise/scan-qr` | Host/staff | Desk scan `typ=padeya.merch.pickup` |
| GET | `/api/v1/dashboard/merchandise/{fulfillment_id}/qr` | Buyer | Own pickup QR payload |
| GET/POST | `/api/v1/host/merchandise/size-charts` | Host | Size charts CRUD (list/create) |
| PATCH | `/api/v1/host/merchandise/size-charts/{id}` | Host | Update |
| POST | `/api/v1/host/merchandise/size-charts/{id}/archive` | Host | Soft archive |
| GET | `/api/v1/merch/size-charts/{id}` | Public | Active chart for product UI |
| POST/PATCH/DELETE | `/api/v1/dashboard/merchandise/reviews` · `…/{id}` | Buyer | Create / edit / remove own review |
| GET | `/api/v1/dashboard/merchandise/reviews/by-order-item/{order_item_id}` | Buyer | Own review lookup |
| GET | `/api/v1/merch/products/{id}/reviews` | Public | Visible verified reviews |
| GET | `/api/v1/host/merchandise/reviews` | Host | Inbox (reply) |
| POST | `/api/v1/host/merchandise/reviews/{id}/reply` | Host | Reply |
| DELETE | `/api/v1/host/merchandise/reviews/{id}` | Host | Always **403** — hosts cannot delete |
| GET | `/api/v1/admin/merchandise/reviews` | Admin | Moderate queue |
| POST | `/api/v1/admin/merchandise/reviews/{id}/moderate` | Admin | Hide / restore |
| GET | `/api/v1/host/merchandise/stock-alerts` | Host | Persisted stock alerts |
| GET | `/api/v1/host/merchandise/revenue` · `…/export.csv` | Host | Split report / CSV (no PII) |
| GET | `/api/v1/admin/merchandise/revenue` · `…/export.csv` | Admin | Platform merch revenue |
| GET/POST/DELETE | `/api/v1/dashboard/cart` · `…/items` | Optional/user | Abandoned cart (never paid) |
| GET | `/api/v1/host/merchandise/print-on-demand` | Host | POD jobs (manual) |
| GET/PUT | `/api/v1/host/merchandise/print-on-demand/integrations` | Host | Provider refs (no live sync required) |
| POST | `/api/v1/host/merchandise/print-on-demand/jobs/{id}/fulfill` · `…/retry` | Host | Manual fulfill / retry |
| GET | `/api/v1/admin/merchandise/print-on-demand` | Admin | POD oversight |
| POST | `/api/v1/admin/merchandise/print-on-demand/jobs/{id}/fulfill` · `…/retry` | Admin | Manual fulfill / retry |

Privacy: shipping street/phone, payment secrets, buyer private info, locked Vault content, and hidden venue streets are never returned on public storefront/catalog/review endpoints. Money side effects (inventory, discount usage, POD jobs, badges, splits) require verified payment finalize.

### Promo rules

- Types: `percentage` · `fixed`
- Optional: usage limit, expiry, event restriction, ticket-type restriction
- `max_per_user` prevents duplicate abuse (pending + redeemed count)
- Usage increments when an order reserves the promo; released on payment failure

## Host CRM & audience (Phase 9)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/crm/follow` | User | Follow host (`host_id` or `host_slug`) |
| DELETE | `/api/v1/crm/follow/{host_id}` | User | Unfollow host |
| GET | `/api/v1/crm/me/following` | User | List followed hosts |
| PATCH | `/api/v1/crm/me/following/{host_id}` | User | Update `marketing_opt_in` (default off) |
| GET | `/api/v1/crm/host/audience` | Host | Audience dashboard stats |
| GET | `/api/v1/crm/host/followers` | Host | Follower list |
| GET | `/api/v1/crm/host/audience/members` | Host | Members by segment + filters |
| GET/POST | `/api/v1/crm/host/segments` | Host | List / create audience segments |
| GET/POST | `/api/v1/crm/host/announcements` | Host | List / create announcements |
| GET | `/api/v1/crm/host/announcements/{id}` | Host | Announcement + recipients + WhatsApp export |
| POST | `/api/v1/crm/host/announcements/{id}/dispatch-email` | Host | Send email via log abstraction (opt-in only) |

### Audience segments

System keys: `followers`, `past_buyers`, `repeat_buyers`, `vip_buyers`, `checked_in_attendees`, `no_shows`, `promo_code_buyers`, `ambassador_referrals`, `superfans` (placeholder), `vault_subscribers` (placeholder).

Optional member filters: `event_id`, `ticket_type_id`, `check_in_status` (`checked_in` | `not_checked_in`).

### Privacy & delivery

- Hosts only see their own audience.
- Display names are privacy-conscious (first name + last initial).
- `marketing_opt_in` defaults to `false` on follow; email dispatch skips opted-out recipients.
- WhatsApp is never sent; API returns export/copy text only.
- Announcement `delivery_status` is a placeholder (`not_sent`, `partial`, `sent`, etc.).

## Finance: refunds, balances, payouts, fees, earnings (Phase 10+)

Product docs: [FINANCE.md](./FINANCE.md) · [PAYOUTS.md](./PAYOUTS.md) · [HOST_EARNINGS.md](./HOST_EARNINGS.md) · [PAYMENTS.md](./PAYMENTS.md).

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/finance/refunds/requests` | Buyer | Create full refund request |
| GET | `/api/v1/finance/refunds/mine` | Buyer | Own refund requests |
| GET | `/api/v1/finance/refunds/requests` | `refunds.review` | Staff list |
| POST | `/api/v1/finance/refunds/requests/{id}/escalate` | `refunds.review` | Support escalate |
| POST | `/api/v1/finance/refunds/requests/{id}/review` | `refunds.approve` / finance | Approve or reject |
| GET | `/api/v1/finance/host/balance` | Host | Host balance |
| GET | `/api/v1/finance/host/ledger` | Host | Own host ledger |
| GET | `/api/v1/finance/host/earnings` | Host finance view | Gross / deductions / net + fee terms + rows |
| GET | `/api/v1/finance/host/earnings/export.csv` | Host finance view | Host earnings CSV |
| GET | `/api/v1/finance/host/events/{event_id}/earnings` | Host finance view | Event-scoped earnings |
| GET/POST | `/api/v1/finance/host/payouts` | Host (`payouts.request`) | List / request payout |
| GET | `/api/v1/finance/admin/payouts` | Finance / super | List payouts |
| POST | `/api/v1/finance/admin/payouts/{id}/review` | `payouts.review` | Approve / reject / under_review |
| POST | `/api/v1/finance/admin/payouts/{id}/mark-paid` | **super_admin only** | Mark paid + evidence |
| GET | `/api/v1/finance/admin/ledger` | Finance / super | Host ledger (admin) |
| GET | `/api/v1/finance/admin/settlement` | Finance / super | Basic settlement report |
| GET | `/api/v1/finance/admin/earnings` | Finance admin gates | Host earnings detail (`host_id` or `event_id`) |
| GET | `/api/v1/finance/admin/earnings/hosts` | Finance admin gates | Host earnings overview rows |
| GET | `/api/v1/finance/admin/earnings/export.csv` | Finance export | Host earnings CSV (audited) |
| GET | `/api/v1/finance/admin/hosts/{host_id}/earnings` | Finance admin gates | Per-host earnings |
| GET | `/api/v1/finance/admin/events/{event_id}/earnings` | Finance admin gates | Per-event earnings |
| GET | `/api/v1/finance/admin/platform-revenue` | Finance admin gates | Platform revenue + ledger rows |
| GET | `/api/v1/finance/admin/platform-revenue/export.csv` | Finance export | Platform revenue CSV (audited) |
| GET | `/api/v1/finance/admin/platform-ledger` | Finance admin gates | Platform ledger list (read-only) |
| GET/POST/PATCH | `/api/v1/finance/admin/fees/settings*` | `admin.finance.*` | Global fee settings |
| GET/POST/PATCH | `/api/v1/finance/admin/fees/overrides*` | `admin.finance.*` | Host fee overrides |
| GET | `/api/v1/pricing/public` | Public | Marketing-safe fee categories + buyer rates only (no host overrides, notes, or other hosts’ deals) |
| POST | `/api/v1/payments/fee-quote` | Public / optional auth | Buyer fee quote (buyer lines only) |

### Finance rules

- Support cannot approve refunds, manage payouts, read host/platform ledgers, settlement, earnings, or platform revenue.
- Host `payments.view` alone does **not** grant admin earnings / platform revenue.
- Marking payout paid requires bank transfer reference + evidence file URL; creates immutable `payout_evidence`.
- Paid payouts cannot be casually reversed.
- Successful payments create idempotent host `sale_credit` / `vault_sale` and platform ledger rows (`dedupe_key`).
- Checkout fee snapshots are immutable; Paystack amount = `order.total_amount`.
- Buyer APIs never expose host commission terms; platform revenue CSV masks payment references and never returns raw Paystack payloads.

## Vault (Phase 11 + Content Studio)

**Vault** = exclusive host content fans unlock by follow, ticket, attendance, VIP, invite, or one-time purchase. Canonical product rules: [VAULT.md](./VAULT.md).

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/vault/public/{username}` | Optional | Published catalog (`VaultCatalogCard` teasers only) |
| GET | `/api/v1/vault/public/{username}/{slug}` | Optional | Item detail; locked fields stripped; related event/memory teasers |
| GET | `/api/v1/vault/related/event/{event_id}` | Optional | Related Vault teasers for an event |
| GET | `/api/v1/vault/related/memory/{memory_id}` | Optional | Related Vault teasers for a memory/event |
| POST | `/api/v1/vault/unlock/{item_id}` | User | One-time unlock checkout (`PDY-VLT-*`) |
| POST | `/api/v1/vault/redeem/{item_id}` | User | Invite access-code redeem |
| GET | `/api/v1/vault/me/purchases` | User | Own purchases |
| GET | `/api/v1/vault/me/purchases/{id}` | User | Purchase status (post-Paystack poll) |
| GET | `/api/v1/vault/me/items` | User | Unlocked items (purchase / follower / ticket / VIP / check-in) |
| GET | `/api/v1/vault/me/library` | User | Fan library (unlocked, followed, ticket-holder, unlockable, activity) |
| GET | `/api/v1/vault/host/studio` | `vault.create` | Studio summary (items, earnings, Legacy featured) |
| GET/POST | `/api/v1/vault/host/items` | `vault.create` | Host list / create (Content → Media → Access → Related → Publish) |
| GET/PATCH | `/api/v1/vault/host/items/{id}` | Host | Own item get / update (owner unlocked) |
| GET | `/api/v1/vault/host/items/{id}/preview` | Host | Fan locked preview |
| POST | `/api/v1/vault/host/items/{id}/publish` | Host | Publish |
| POST | `/api/v1/vault/host/items/{id}/unpublish` | Host | Unpublish → draft |
| POST | `/api/v1/vault/host/items/{id}/schedule` | Host | Schedule (`scheduled` + starts_at) |
| POST | `/api/v1/vault/host/items/{id}/archive` | Host | Soft archive (`archived`) |
| POST | `/api/v1/vault/host/items/{id}/restore` | Host | Restore archived/expired → draft |
| POST | `/api/v1/vault/host/items/{id}/grant` | Host | Manual invite grant |
| DELETE | `/api/v1/vault/host/items/{id}` | Host | Hard delete draft only if no unlock history |
| GET | `/api/v1/vault/host/earnings` | Host | Vault earnings (`vault_sale`) |
| GET | `/api/v1/vault/admin/items` | `vault.moderate` | Admin list + unlock/purchase summary filters |
| POST | `/api/v1/vault/admin/items/{id}/moderate` | `vault.moderate` | Flag / approve / hide / archive / remove / restore |

### Vault rules

**Access types:** `free`, `followers_only`, `ticket_holder_only`, `checked_in_attendee_only`, `vip_ticket_holder_only`, `one_time_unlock`, `invite_only`, `admin_hidden`.

**Locked / unlocked**

- Without access: never return `body`, `file_url`, `external_url`, or private media URLs (private media omitted, not null-stubbed).
- Public catalog is slim cards only (title, teaser, cover, access type, lock state, price if paid, related event, CTA).
- Draft / scheduled / expired / archived / `hidden_by_admin` → not listed; public detail 404.

**Payments / unlock**

- Do not trust frontend payment success. Finalize only via Paystack webhook (or server free/demo path).
- `PDY-VLT-*` purchases write idempotent `vault_access_grants` + `vault_sale` ledger; never issue event tickets.
- Pending buyer+item checkouts are reused; invite codes hashed at rest and never returned (`access_code` always null).
- Invite unlock: `POST /vault/redeem/{id}` or host `POST /vault/host/items/{id}/grant`.

**Moderation / Legacy**

- Moderate actions that hide/archive/remove/restore require a reason (audited). Support lacks `vault.moderate` by default.
- Legacy `vault_preview` and related event/memory teasers use the same redaction rules — never leak locked content.

## Messaging

See [MESSAGING.md](./MESSAGING.md) (WS events, reconnect, typing, attachments, chat features, limits) and [DEMO_DATA.md](./DEMO_DATA.md).

### Chat features (summary)

| Concern | API behavior |
| --- | --- |
| Timestamps | ISO `created_at` / `edited_at` / `last_message_at` — FE formats display-only |
| Edit | `PATCH …/{message_id}` — own body, 24h window; writes `message_edits`; WS `message.updated` |
| Reply | `POST …/send` + optional `reply_to_message_id` — same-thread + permission-checked; safe `reply_to` in serializers |
| Pins | Shared `GET …/pins` + `POST …/pin\|unpin` — max 3 active; WS `message.pinned` / `unpinned` |
| Stars | Personal `GET …/starred` + `POST …/star\|unstar` — peer never notified; no star WS |
| Read status | Thread cursors via `PATCH …/read` + `peer_read_at` on detail; WS `message.read` |
| Delete for me | `POST …/delete` with `scope=for_me` only |
| Permissions | All actions go through `app.messaging.permissions` (fan↔host / fan↔fan / Connect gates) |
| Admin | Hide/restore + attachment moderation only on **reported** threads |

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/messages` | User | Fan inbox (`filter`: all/unread/requests/event/starred/archived) |
| POST | `/api/v1/messages/threads` | User | Start / continue fan→host (reuses existing pair) |
| POST | `/api/v1/messages/threads/{thread_id}/attachments` | User | Stage attachment (multipart `file`; no message until send) |
| GET | `/api/v1/messages/attachments/{attachment_id}` | User (Bearer or `?d=` signed) | Private download (thread access + `ready`; TTL via env) |
| GET | `/api/v1/messages/starred` | User | Personal starred messages (hidden/deleted bodies redacted) |
| GET | `/api/v1/messages/{id}` | User | Thread detail (`can_attach`, `peer_read_at`, `pinned_messages`, messages) |
| POST | `/api/v1/messages/{id}/send` | User | Send text and/or `attachment_ids` + optional `reply_to_message_id` |
| PATCH | `/api/v1/messages/{message_id}` | User | Edit own message body (24h window; history in `message_edits`) |
| GET | `/api/v1/messages/threads/{thread_id}/pins` | User | Active pinned messages |
| GET | `/api/v1/messages/threads/{thread_id}/search` | User | In-thread search (`q` body ILIKE + `starred`/`pinned`/`has_attachments`; no FTS index) |
| POST | `/api/v1/messages/{message_id}/pin` | User | Pin (max 3 active; soft-unpin via `unpinned_at`) |
| POST | `/api/v1/messages/{message_id}/unpin` | User | Soft-unpin |
| POST | `/api/v1/messages/{message_id}/star` | User | Personal star (peer never notified) |
| POST | `/api/v1/messages/{message_id}/unstar` | User | Soft-unstar (`unstarred_at`) |
| POST | `/api/v1/messages/{message_id}/delete` | User | Soft **delete for me** only (`scope=for_me`; peer still sees) |
| PATCH | `/api/v1/messages/{id}/read` | User | Mark read (thread-level cursor) |
| PATCH | `/api/v1/messages/{id}/archive` | User | Archive for fan |
| POST | `/api/v1/messages/{id}/accept` | User | Accept message request |
| POST | `/api/v1/messages/{id}/report` | User | Report thread |
| POST | `/api/v1/messages/block` | User | Block counterpart |
| DELETE | `/api/v1/messages/block/{user_id}` | User | Unblock |
| GET | `/api/v1/messages/unread-count` | User | Unread badge count |
| GET | `/api/v1/messages/notifications` | User | In-app notices (generic / attachment-safe bodies) |
| GET/PATCH | `/api/v1/messages/settings` | User | Prefs + `blocked_users` (names only) |
| WS | `/api/v1/messages/ws?token=` | User (JWT query) | Realtime push — see event table in [MESSAGING.md](./MESSAGING.md#real-time-delivery-websocket); **no send/upload** |
| GET | `/api/v1/host/messages` | Host | Host inbox (same filters, incl. starred) |
| GET | `/api/v1/host/messages/can-message/{fan_user_id}` | Host | Relationship gate |
| GET | `/api/v1/host/messages/can-message-by-username/{username}` | Host | Passport CTA gate |
| POST | `/api/v1/host/messages/threads` | Host | Host→fan (relationship required) |
| POST | `/api/v1/host/messages/threads/{thread_id}/attachments` | Host | Stage attachment (same allowlist) |
| GET | `/api/v1/host/messages/starred` | Host | Personal starred messages |
| GET/POST | `/api/v1/host/messages/{id}` · `…/send` | Host | Thread + send (optional attachments / `reply_to`) |
| PATCH | `/api/v1/host/messages/{message_id}` | Host | Edit own message (24h window) |
| GET | `/api/v1/host/messages/threads/{thread_id}/pins` | Host | Active pinned messages |
| GET | `/api/v1/host/messages/threads/{thread_id}/search` | Host | In-thread search twin |
| POST | `/api/v1/host/messages/{message_id}/pin` · `/unpin` | Host | Pin / soft-unpin |
| POST | `/api/v1/host/messages/{message_id}/star` · `/unstar` | Host | Personal star / soft-unstar |
| POST | `/api/v1/host/messages/{message_id}/delete` | Host | Soft delete for me twin |
| PATCH | `/api/v1/host/messages/{id}/read` · `…/archive` | Host | Read / archive |
| POST | `/api/v1/host/messages/{id}/report` | Host | Report |
| POST/DELETE | `/api/v1/host/messages/block…` | Host | Block / unblock |
| GET | `/api/v1/admin/message-reports` | Admin | Report queue |
| GET/PATCH | `/api/v1/admin/message-reports/{id}` | Admin | Detail / status (+ attachment metadata when `moderation_view`) |
| PATCH | `/api/v1/admin/messages/{id}/hide` · restore | Admin | Moderate message body on a **reported** thread (+ soft-hide attachments; clears pins) |
| PATCH | `/api/v1/admin/messages/attachments/{id}/hide` | Admin | Soft-hide attachment on a **reported** thread |
| PATCH | `/api/v1/admin/messages/attachments/{id}/restore` | Admin | Restore hidden/disabled attachment (keeps bytes) |
| PATCH | `/api/v1/admin/messages/attachments/{id}/delete` | Admin | Soft-disable access (`deleted_at`; no hard delete) |
| PATCH | `/api/v1/admin/messages/attachments/{id}/review` | Admin | Mark attachment reviewed |

**Attachment allowlist / limits:** JPEG/PNG/WebP, PDF, text/plain, CSV, DOCX · images 5MB · docs 10MB · total 15MB · max 4 (`MESSAGING_ATTACHMENT_MAX_*`). Storage: `MESSAGING_ATTACHMENT_STORAGE_PROVIDER` (`local` default).

### Messaging serializer rules

- Thread list/detail: counterpart display fields + optional related-event **chip** (`id`, `title`, `slug`, `path`, `banner_url`) — never street address, order ID, or ticket ID.
- Thread detail also exposes `can_attach`, `can_reply`, `peer_read_at`, `pinned_messages` (thread-level Seen hydration).
- Message public fields include `edited_at`, `reply_to`, `is_pinned`, `is_starred` (viewer-scoped), `deleted_for_me`.
- `reply_to` preview fields: `reply_message_id`, `reply_author_display_name`, `reply_body_preview`, `reply_attachment_preview`, `reply_created_at`, `reply_is_unavailable` — no contact/storage secrets; same-thread only.
- `message_edits` history is **not** returned on public message payloads (audit/internal only).
- `fan_fan` threads may include `connect_context` (badge + safe label) — never VIP/spend/private venue.
- Message bodies may be replaced with `[Message hidden by moderation]` / `[Message removed]` / `Message deleted` (for_me); attachments cleared/redacted when hidden/deleted; pins cleared on hide; inbox `last_message_preview` redacts hidden/deleted last messages.
- Attachments public fields: `id`, `url`, `content_type`, `byte_size`, `original_filename`, optional `width`/`height`, `status` (+ `reviewed_at` on admin moderation view). Never `storage_key` / checksum / FS path.
- WS payloads follow the same privacy rules; JWT required; no alternate send path. Pin events fan out to participants; star actions do not.
- Settings `blocked_users`: `user_id`, `display_name`, `username`, `role` — no email/phone.

## Fan Connect

See [FAN_CONNECT.md](./FAN_CONNECT.md). Opt-in fan↔fan graph; messaging only after mutual accept.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET/PATCH | `/api/v1/fan-connect/settings` | User | Own Connect settings (defaults on; untick anytime) |
| GET | `/api/v1/fan-connect/can-connect/{username}` | User | Eligibility, safe shared context, `cooldown_until`, `can_send_connect_request`, relationship flags |
| GET/POST | `/api/v1/fan-connect/requests` | User | List (`box=incoming\|outgoing`) / create request |
| POST | `/api/v1/fan-connect/requests/{id}/accept` | User | Accept → `connected` + unlock `fan_fan` |
| POST | `/api/v1/fan-connect/requests/{id}/decline` | User | Decline; optional `{ "cooldown_days": 0–365 }` (requester-only cooldown) |
| GET | `/api/v1/fan-connect/decline-cooldown-options` | User | Platform default + selectable decline durations |
| POST | `/api/v1/fan-connect/requests/{id}/cancel` | User | Cancel outgoing → `removed` |
| GET | `/api/v1/fan-connect/connections` | User | Accepted connections |
| POST | `/api/v1/fan-connect/connections/{id}/remove` | User | Soft end → `removed` |
| POST | `/api/v1/fan-connect/connections/{id}/disconnect` | User | Alias of remove |
| POST | `/api/v1/fan-connect/block` | User | Block fan (`204`) |
| POST | `/api/v1/fan-connect/report` | User | Report fan |
| GET | `/api/v1/fan-connect/suggestions` | User | Ranked suggestions; cards include `cta_state`, `cooldown_until`, `viewer_declined_target`, `can_send_connect_request` |
| GET | `/api/v1/fan-connect/events` | User | Public-safe nights for Connect UI |
| GET | `/api/v1/events/{slug}/fan-connect` | User | Event-scoped suggestions |
| GET | `/api/v1/admin/fan-connect/overview` | Admin | Moderation counts |
| GET/PATCH | `/api/v1/admin/fan-connect/settings` | Admin | Default decline cooldown (**30** days out of box; 0–365), audited |
| GET | `/api/v1/admin/fan-connect/blocks` | Admin | Block history |
| GET | `/api/v1/admin/fan-connect/reports` | Admin | Connect reports (+ safe context) |
| GET | `/api/v1/admin/fan-connect/reports/{id}` | Admin | Report detail |
| POST | `/api/v1/admin/fan-connect/reports/{id}/resolve` | Admin | Resolve / dismiss |
| GET | `/api/v1/admin/fan-connect/users/{id}/moderation` | Admin | Per-fan block/report history |
| POST | `/api/v1/admin/fan-connect/users/{id}/disable` | Admin | Soft-disable Connect |

### Fan Connect rules

- Defaults private; directory membership never enables Connect.
- Target Passport must be `public`; private/unlisted/admin-hidden excluded.
- Suggestion/request payloads and `reasons_json` use **safe reason codes only** — never private attendance, hidden venues, ticket type, VIP/table, order/payment/spend, contact, or Vault bodies.
- `fan_fan` messaging only when connection status is `connected`.
- Connect reports (`/admin/fan-connect/reports`) do not open unreported chats; message moderation stays on `/admin/message-reports`.

## Fan Passport (Phase 12+)

See [FAN_PASSPORT.md](./FAN_PASSPORT.md).

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/passport/me` | User | Own passport (auto-created); loyalty, attendance, badges, Vault summary |
| GET | `/api/v1/dashboard/passport` | User | Alias of `/passport/me` |
| GET | `/api/v1/passport/me/badges` | User | Full badge catalog with earned flags |
| GET/PATCH | `/api/v1/dashboard/passport/settings` | User | Profile + privacy toggles |
| GET/PATCH | `/api/v1/passport/me/settings` | User | Alias of settings |
| GET | `/api/v1/fans` | Public | Fan Passport Directory (public + `appear_in_directory` only) |
| GET | `/api/v1/f/{username}` | Public | Public/unlisted Fan Passport (404 if private/admin-hidden) |
| GET | `/api/v1/f/{username}/activity` | Public | Privacy-safe attended events |
| GET | `/api/v1/f/{username}/badges` | Public | Earned badges when allowed |
| GET | `/api/v1/admin/fans` | Admin | Moderate Fan Passports |
| PATCH | `/api/v1/admin/fans/{user_id}/hide` | Admin | Hide from directory + public page |
| PATCH | `/api/v1/admin/fans/{user_id}/restore` | Admin | Clear admin hide |
| GET | `/api/v1/passport/health` | Public | Module health |

### Passport rules

- Passport is created automatically on first `GET /passport/me` for the authenticated user.
- **Default visibility is private.** Public/unlisted only after the fan opts in.
- **Directory listing** requires `visibility=public` **and** `appear_in_directory=true` (both default on at signup). Unlisted/private never list. Non-public visibility clears directory listing.
- **Attendance** = distinct events with a `checked_in` ticket. Cancelled / refunded tickets never count.
- Owned tickets for stats = `active` or `checked_in` only.
- Badge awards are deterministic from ticket, check-in, follow, VIP, Vault, and city data.
- Public pages and directory cards never expose amounts, venues for hidden locations, secret attendance, locked Vault bodies, email, or payment data.

## Event Memories (Phase 13)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/memories/public/{username}/{event_slug}` | Public | Public memory page (completed + published only) |
| GET | `/api/v1/memories/host/events/{event_id}` | Host (`events.manage_own`) | Own memory (auto-ensures after completed) |
| PATCH | `/api/v1/memories/host/events/{event_id}` | Host | Edit host recap note |
| POST | `/api/v1/memories/host/events/{event_id}/media` | Host | Add gallery media (URL storage abstraction) |
| DELETE | `/api/v1/memories/host/events/{event_id}/media/{media_id}` | Host | Remove gallery media |
| GET | `/api/v1/memories/admin` | `memories.moderate` | Admin list |
| POST | `/api/v1/memories/admin/{id}/moderate` | `memories.moderate` | Hide / unhide / flag / approve |
| GET | `/api/v1/memories/health` | Public | Module health |

### Memory rules

- Memory records auto-create when an event is marked `completed`.
- Public pages require `event.status == completed`, memory `status == published`, and moderation not `removed`.
- Attendance stats use verified ticket data (`checked_in` / owned `active|checked_in` only).
- Verified rating and top reviews are visible reviews for that event only.
- Hosts may edit only their own event memories.
- Admin hide is audited (`memories.moderate.hide`).
- Legacy Page includes `event_memories` and `memory_path` on past event cards.

## Admin Runtime Settings

Allowlisted Class B tunables + status. Module: `backend/app/runtime_settings/`. Docs: [SETTINGS.md](./SETTINGS.md) · [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md).

Base: **`/api/v1/admin/settings/runtime`**. Secrets never returned as plaintext — `masked_value` is `Configured · ending in ####` or `Not configured`.

| Method | Path | Permission | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/settings/runtime` | `admin.settings.view` | List allowlisted settings grouped by category |
| GET | `/api/v1/admin/settings/runtime/status` | `view_system_status` or `view` | Class D / system status (env name, version, SHA, boot, configured flags) |
| GET | `/api/v1/admin/settings/runtime/audit` | `admin.settings.view_audit` | Settings-domain audit entries |
| GET | `/api/v1/admin/settings/runtime/{category}` | `admin.settings.view` | Category settings list |
| PUT | `/api/v1/admin/settings/runtime/{category}/{key}` | `edit_runtime` (+ `edit_secrets` if secret) | Upsert override; body `{ value?, clear?, reason? }` (blank secret keeps existing) |
| DELETE | `/api/v1/admin/settings/runtime/{category}/{key}/override` | `clear_overrides` (+ `edit_secrets` if secret) | Clear DB override → env/default |
| POST | `/api/v1/admin/settings/runtime/{category}/test` | `test_integrations` | Safe category test (no secret echo; payments never charge) |

`admin.full_access` satisfies all. Class A keys are hard-blocked on write. Email/push specialist secrets are not stored in `runtime_settings` — adapters delegate to existing services. Resolve order: DB → env → default. Startup does not depend on this table.

Audit actions: `runtime_setting_updated`, `runtime_secret_replaced`, `runtime_setting_cleared_to_env`, `runtime_setting_tested`, `runtime_setting_validation_failed`, `runtime_setting_viewed_sensitive_status`.

Specialist APIs (unchanged): `/api/v1/admin/email/settings*`, `/api/v1/admin/push/settings*`.

## Maintenance & platform status

Module: `backend/app/maintenance/`. Middleware: `MaintenanceMiddleware`. Tables: `maintenance_settings`, `maintenance_sections`, `maintenance_schedules`, `maintenance_notifications`, `maintenance_audit_logs`, `maintenance_bypass_sessions`.

| Method | Path | Permission | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/maintenance/status` | Public | Public mode + sections + upcoming schedule |
| GET | `/api/v1/maintenance/public` | Public | Alias of status |
| GET | `/api/v1/admin/platform/maintenance` | `admin.maintenance.view` | Dashboard (settings, sections, schedules) |
| PATCH | `/api/v1/admin/platform/maintenance` | `admin.maintenance.manage` | Update global mode / messages |
| PATCH | `/api/v1/admin/platform/maintenance/sections/{key}` | `admin.maintenance.manage` | Section enable/mode/message/window |
| POST | `/api/v1/admin/platform/maintenance/schedules` | `admin.maintenance.schedule` | Create schedule (auto enable/disable) |
| POST | `/api/v1/admin/platform/maintenance/schedules/{id}/cancel` | `admin.maintenance.schedule` | Cancel pending schedule |
| GET | `/api/v1/admin/platform/maintenance/history` | `admin.maintenance.view` | Domain audit log |
| GET/POST | `/api/v1/admin/platform/maintenance/notifications` | `notify` | List / send advance notices |
| POST | `/api/v1/admin/platform/maintenance/notifications/test` | `notify` | Test send to self |
| POST | `/api/v1/admin/platform/maintenance/bypass` | `bypass` | Issue TTL bypass token (shown once) |

Blocked product responses use **503** (maintenance) or **423** (read-only writes) with body `{ detail, maintenance, section, expected_back_at }`. Bypass header: `X-Maintenance-Bypass`. Never return raw bypass tokens in lists/logs.

## Transactional email

Central outbox — see [EMAILS.md](./EMAILS.md) and [EMAIL_AUDIT.md](./EMAIL_AUDIT.md).

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET/PATCH | `/api/v1/email/preferences` | User | Read/update email prefs |
| GET | `/api/v1/email/preferences/token` | User | Signed prefs + unsubscribe tokens |
| GET/PATCH | `/api/v1/email/preferences/by-token` | Public (token) | Prefs via email link |
| POST | `/api/v1/email/unsubscribe` | Public (token) | Marketing unsubscribe |
| GET | `/api/v1/admin/emails` | Admin | Outbox list |
| GET | `/api/v1/admin/emails/{id}` | Admin | Event detail |
| POST | `/api/v1/admin/emails/{id}/resend` | Admin | Re-queue / deliver |
| POST | `/api/v1/admin/emails/process-pending` | Admin | Drain pending |
| GET | `/api/v1/admin/email/settings` | Admin | Masked provider/SMTP settings |
| PATCH | `/api/v1/admin/email/settings` | Admin | Update settings (blank password keeps existing) |
| POST | `/api/v1/admin/email/settings/test` | Admin | SMTP connection and/or test send |
| POST | `/api/v1/admin/email/settings/activate` | Admin | Activate a settings row |
| POST | `/api/v1/admin/email/settings/disable` | Admin | Disable email sending |

Purchase emails are enqueued only after verified Paystack finalize (`ticket_confirmed`, `merch_order_confirmed`). Webhook handlers must not send SMTP inline.

## Browser push + in-app notifications

Deep dive: [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · product overview: [NOTIFICATIONS.md](./NOTIFICATIONS.md).

### User push

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/push/vapid-public-key` | Public / user | `{ enabled, public_key }` (empty when push off) |
| GET | `/api/v1/push/subscriptions` | User | List devices (no encrypted keys) |
| POST | `/api/v1/push/subscriptions` | User | Register / upsert device subscription |
| DELETE | `/api/v1/push/subscriptions` | User | Unregister by endpoint or id body |
| DELETE | `/api/v1/push/subscriptions/{id}` | User | Soft-revoke one device |
| GET / PATCH | `/api/v1/push/preferences` | User | Push category prefs (master `push_enabled` defaults on) |

Push copy for each in-app `kind` is resolved server-side (`app/push/templates.py` + `app/notifications/channel_registry.py`); clients only receive whitelisted payload fields. See [NOTIFICATION_PUSH_AUDIT.md](./NOTIFICATION_PUSH_AUDIT.md).

### Admin push (`admin.full_access`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET / PATCH | `/api/v1/admin/push/settings` | Kill switch, provider, VAPID (private never returned) |
| POST | `/api/v1/admin/push/settings/disable` | Disable push globally |
| POST | `/api/v1/admin/push/settings/test` | Test push to self (fixed copy) |
| POST | `/api/v1/admin/push/settings/test-user` | Test push by email / `user_id` |
| GET | `/api/v1/admin/push/subscriptions/lookup` | Active device count for a user |
| GET | `/api/v1/admin/push/deliveries` | Delivery summary + recent rows |
| GET | `/api/v1/admin/push/events` | Outbox `push_events` list |
| POST | `/api/v1/admin/push/cleanup-subscriptions` | Deactivate stale failed devices |

Admin per-type channels: `GET/PUT /api/v1/admin/notifications/settings` — each type includes `channels.push` and optional `push_unavailable_reason` when push is blocked for safety (internal kinds only).

### In-app notifications

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/notifications` | User | Inbox (`?category=`, mark-read surfaces) |
| GET | `/api/v1/notifications/unread-count` | User | Badge count |
| GET | `/api/v1/notifications/popup` | User | Toast poll fallback |
| POST | `/api/v1/notifications/{id}/read` | User | Mark one read |
| POST | `/api/v1/notifications/read-all` | User | Mark all read |

Commerce push/email enqueue only after verified Paystack finalize. Push outbox is drained by `scripts/process_push_outbox.py` / Compose `push_worker` — not inline in webhooks.

## Verified event reviews

Buyer CRUD for checked-in attendees. Hosts may reply or report only — never delete or edit buyer text. Prefer soft withdraw/hide over hard delete.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/reviews/eligibility` | Buyer | Check ticket/event eligibility |
| POST | `/api/v1/reviews` | Buyer | Create verified review (one per eligible ticket) |
| GET | `/api/v1/reviews/me` | Buyer | Own reviews (all statuses) |
| PATCH | `/api/v1/reviews/{id}` | Buyer (owner) | Edit rating/title/body; editing `withdrawn` restores `visible` |
| DELETE | `/api/v1/reviews/{id}` | Buyer (owner) | Soft withdraw (`status=withdrawn`) — not hard delete |
| GET | `/api/v1/reviews/host/me` | Host | Inbox for own events |
| POST | `/api/v1/reviews/{id}/reply` | Host | Upsert host reply |
| POST | `/api/v1/reviews/{id}/report` | Auth | Report for moderation |
| GET | `/api/v1/reviews/admin/reported` | Admin/support | Open reports queue |
| POST | `/api/v1/reviews/{id}/moderate` | Admin/support | `hide` / `restore` (audited) |

Rules: public Legacy shows `visible` only; hosts cannot delete reviews (403); buyers cannot edit `hidden` reviews; withdraw and restore are audited (`reviews.withdraw` / `reviews.restore`).

## Legacy Content Studio (Phase 1)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/host/legacy` | Host | Full studio payload (blocks, featured, settings) |
| PATCH | `/api/v1/host/legacy` | Host | Update identity, CTAs, socials, contact, sponsorship |
| GET | `/api/v1/host/legacy/content-blocks` | Host | List content blocks |
| POST | `/api/v1/host/legacy/content-blocks` | Host | Create block |
| PATCH | `/api/v1/host/legacy/content-blocks/{id}` | Host | Update block |
| POST | `/api/v1/host/legacy/content-blocks/reorder` | Host | Reorder (`ordered_ids`) |
| POST | `/api/v1/host/legacy/content-blocks/{id}/toggle` | Host | Toggle visibility |
| DELETE | `/api/v1/host/legacy/content-blocks/{id}` | Host | Archive/hide core blocks; delete optional |
| GET/POST | `/api/v1/host/legacy/featured-items` | Host | List / upsert featured items |
| DELETE | `/api/v1/host/legacy/featured-items/{placement}` | Host | Clear featured placement |
| GET | `/api/v1/u/{username}/legacy` | Public | Public Legacy (visible blocks only) |
| GET | `/api/v1/legacy/{username}` | Public | Compat alias |
| GET/PATCH | `/api/v1/legacy/me` | Host | Compat host page |

Public rules: visible blocks only; Vault bodies stay locked; verified reviews only; hiding the Reviews block does not delete reviews (trust note returned).

## Advanced Analytics (Phase 14)

First-party event analytics. Taxonomy, privacy, rollups, and dashboard behavior:
[ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md),
[ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md),
[ANALYTICS_ROLLUPS.md](./ANALYTICS_ROLLUPS.md).

### Public track

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/analytics/health` | Public | Module health |
| POST | `/api/v1/analytics/track` | Optional | Unified track (known taxonomy actions only) |
| POST | `/api/v1/analytics/track/batch` | Optional | Batch track; rejects trusted actions per item |
| POST | `/api/v1/analytics/track/event` | Optional | Legacy generic analytics event |
| POST | `/api/v1/analytics/track/page-view` | Optional | Page / detail view |
| POST | `/api/v1/analytics/track/impression` | Optional | Event card impression (session/context dedupe) |
| POST | `/api/v1/analytics/track/click` | Optional | Event card click |
| POST | `/api/v1/analytics/track/conversion` | Optional | Funnel stage (clients cannot emit payment success) |

### Host portfolio summaries

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/analytics/host/summary` | `analytics.view_own` | Host portfolio aggregates |
| GET | `/api/v1/analytics/host/events/{event_id}` | Host | Legacy per-event summary (own events) |
| GET | `/api/v1/analytics/host/export.csv` | `analytics.export` | Host CSV export |

### Host per-event analytics

Base: `/api/v1/host/events/{event_id}/analytics/` — own events only.

| Method | Path suffix | Purpose |
| --- | --- | --- |
| GET | `overview` | KPIs + conversion rates |
| GET | `funnel` | Funnel steps + dropoffs |
| GET | `timeseries` | Hour / day / week trends |
| GET | `sources` | Channel buckets + UTM campaigns |
| GET | `tickets` | Ticket-type performance |
| GET | `audience` | Device / city / new vs returning (aggregates) |
| GET | `promos` | Promo performance |
| GET | `ambassadors` | Ambassador performance |
| GET | `export` | Aggregate CSV |

Query filters: `date_from`, `date_to`, `source`, `medium`, `campaign`, `ticket_type_id`, `device_type`, `city`, `include_bots` (hosts cannot enable bots).

### Admin platform summaries

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/analytics/admin/summary` | `analytics.view_platform` | Platform overview |
| GET | `/api/v1/analytics/admin/revenue` | Platform | Revenue breakdown |
| GET | `/api/v1/analytics/admin/events` | Platform | Event / category / city trends |
| GET | `/api/v1/analytics/admin/hosts` | Platform | Host rankings |
| GET | `/api/v1/analytics/admin/support` | Platform | Support proxy + fraud placeholders |
| GET | `/api/v1/analytics/admin/export.csv` | `analytics.export` + platform | Admin CSV export |

### Admin per-event + cross-event analytics

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/admin/events/{event_id}/analytics` | Full event analytics bundle |
| GET | `/api/v1/admin/events/{event_id}/analytics/funnel` | Funnel |
| GET | `/api/v1/admin/events/{event_id}/analytics/timeseries` | Timeseries |
| GET | `/api/v1/admin/events/{event_id}/analytics/audience` | Audience |
| GET | `/api/v1/admin/events/{event_id}/analytics/promos` | Promos |
| GET | `/api/v1/admin/events/{event_id}/analytics/ambassadors` | Ambassadors |
| GET | `/api/v1/admin/events/{event_id}/analytics/export` | Event CSV |
| GET | `/api/v1/admin/analytics/events/leaderboard` | Cross-event ranking |
| GET | `/api/v1/admin/analytics/events/channels` | Platform channel mix |
| GET | `/api/v1/admin/analytics/events/compare` | Compare events (`event_ids`) |
| GET | `/api/v1/admin/analytics/events/export` | Events CSV |

### Analytics rules

- Hosts only see their own aggregates; per-event host endpoints 404 for other hosts’ events.
- Admins/finance use `analytics.view_platform`; CSV requires `analytics.export`.
- Clients cannot emit trusted actions (`payment_success`, `ticket_issued`, `checkin_success`, `review_submitted`, …).
- Metadata is scrubbed (no email/phone/card/private venue); see [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md).
- Host KPIs exclude bots by default; admins may pass `include_bots=true`.
- Aggregation helpers apply date-range filters and indexed counts — avoid ad-hoc heavy joins in routers.
- Platform fees are **configurable** via finance fee settings / host overrides (see [FINANCE.md](./FINANCE.md)). Older analytics copy may still mention a placeholder take-rate — checkout money uses fee settings + snapshots, not that placeholder.
- Support volume proxies refunds under review until a support-ticket model exists.
- Fraud signals are placeholders.
- Daily rollups: `python -m scripts.run_analytics_rollups` ([ANALYTICS_ROLLUPS.md](./ANALYTICS_ROLLUPS.md)).

## AI Copilot (Phase 15 + Phase 1 hardening)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/ai/status` | Public | Enabled flag, provider name, model (no secrets) |
| GET | `/api/v1/ai/host/features` | `ai.use_own` | Host feature catalog (+ `enabled` flags) |
| POST | `/api/v1/ai/host/generate` | `ai.use_own` | Host suggestion (optional `event_id`, `merch_product_id`, `notes`, scrubbed `extra`) |
| POST | `/api/v1/ai/host/events/{event_id}/generate` | Host | Event-scoped host suggestion |
| POST | `/api/v1/ai/host/generation-feedback` | `ai.use_own` | Record accepted / applied / rejected / dismissed |
| GET | `/api/v1/ai/admin/features` | `ai.use_platform` | Admin feature catalog |
| POST | `/api/v1/ai/admin/generate` | `ai.use_platform` | Admin suggestion (optional `support_ticket_id`) |
| POST | `/api/v1/ai/admin/support/tickets/{ticket_id}/generate` | `ai.use_platform` + support view | Ticket-scoped Support AI draft |
| POST | `/api/v1/ai/admin/generation-feedback` | `ai.use_platform` | Record applied / dismissed (never auto-sends) |
| POST | `/api/v1/ai/admin/support/summary` | Platform | Legacy support complaint summary shortcut |
| GET | `/api/v1/ai/health` | Public | Module health |
| GET | `/api/v1/ai/admin/controls/overview` | `admin.ai.view` | Control Center overview |
| GET | `/api/v1/ai/admin/controls/providers` | `admin.ai.manage_providers` / view | Provider profiles |
| POST/PATCH | `/api/v1/ai/admin/controls/providers` | `admin.ai.manage_providers` | Create/update profiles |
| POST | `/api/v1/ai/admin/controls/providers/{id}/test` | `admin.ai.test_connection` | Test profile |
| GET/PATCH | `/api/v1/ai/admin/controls/routes` | `admin.ai.manage_features` | Per-feature routing |
| GET | `/api/v1/ai/admin/controls/safety` | `admin.ai.manage_safety` | Safety overview |
| PATCH | `/api/v1/ai/admin/controls/settings` | `admin.ai.manage_settings` | Global enable + provider/model/base URL (not API key) |
| PATCH | `/api/v1/ai/admin/controls/spend` | `admin.ai.manage_spend` | Monthly spend cap + warning/hard-stop |
| POST | `/api/v1/ai/admin/controls/test-connection` | `admin.ai.test_connection` | Safe provider probe (no secrets in response) |
| GET | `/api/v1/ai/admin/controls/features` | `admin.ai.view` / `manage_features` | Per-feature toggle configs |
| PATCH | `/api/v1/ai/admin/controls/features/{feature_key}` | `admin.ai.manage_features` | Update feature limits / review flag |
| GET | `/api/v1/ai/admin/controls/usage` | `admin.ai.view_usage` | Usage aggregates (date filters) |
| GET | `/api/v1/ai/admin/controls/logs` | `admin.ai.view_logs` | Safe generation logs (no prompts/secrets) |

`AI_KILL_SWITCH=1` forces “Disabled by environment” — UI cannot enable AI. `AI_API_KEY` remains env-only.

### Phase 1 Event Studio features

| Feature key | Purpose |
| --- | --- |
| `host.event.title` | 3–5 title options (draft only) |
| `host.event.description` | One description draft |

Legacy aliases `generate_event_title` / `generate_event_description` still accepted and normalize to the keys above.

### Phase 1 Merch Studio features

| Feature key | Purpose |
| --- | --- |
| `host.merch.title` | 3–5 product title options (draft only) |
| `host.merch.description` | One product description draft |
| `host.merch.category` | One controlled-catalog category (`category_slug` + label) |
| `host.merch.tags` | 3–6 safe tags (`tags` array) |

### Phase 1 Support AI features

| Feature key | Purpose |
| --- | --- |
| `support.ticket.summary` | Staff-only ticket summary (issue / goal / status / next action) |
| `support.ticket.triage` | Category suggestion (`category_slug`) — staff Apply or Ignore |
| `support.ticket.priority` | Priority + reason (`priority`, `priority_reason`) — staff confirms |
| `support.ticket.reply_draft` | Public reply draft — Apply to composer only; Send is manual |
| `support.ticket.article_suggestions` | 3–5 KB articles from server catalog only (`articles[]`) |

### Phase 1 Admin AI summaries

| Feature key | Purpose | UI |
| --- | --- | --- |
| `admin.support.queue_summary` | Open/urgent themes + staff focus (advisory) | `/admin/support` |
| `admin.analytics.revenue_summary` | Period revenue/ticket/merch/refund notes + review ideas | `/admin/analytics` |
| `admin.reports.summary` | Report themes + suggested review order (no auto-moderation) | `/admin/reviews`, `/admin/message-reports` |
| `admin.operations.daily_summary` | On-demand daily ops snapshot + checklist | `/admin` |

### Phase 1 Blog CMS AI features

| Feature key | Purpose |
| --- | --- |
| `admin.blog.title` | 3–5 title options (click to apply title only) |
| `admin.blog.outline` | Markdown outline draft (apply/copy into body) |
| `admin.blog.excerpt` | Short excerpt draft |
| `admin.blog.seo_meta` | SEO title, meta description, slug, OG description |
| `admin.blog.tags` | Tags from existing blog catalog only |
| `admin.blog.social_snippets` | X/Twitter, Instagram, LinkedIn, WhatsApp copy-only drafts |

Requires `ai.use_platform` + `admin.blog.edit` (or `admin.blog.create`). Never auto-publishes (`admin.blog.publish` remains manual).

Legacy aliases `summarize_support_complaints` / `explain_revenue_trends` / `summarize_review_reports` canonicalize to the admin summary keys above.

Related ticket mutations (human-confirmed, not AI-driven):

| Method | Path | Purpose |
| --- | --- | --- |
| PATCH | `/api/v1/admin/support/tickets/{id}/category` | Apply category after staff confirm |
| PATCH | `/api/v1/admin/support/tickets/{id}/priority` | Apply priority after staff confirm |
| PATCH | `/api/v1/support/cases/{id}/category` | Staff desk category apply |
| PATCH | `/api/v1/support/cases/{id}/priority` | Staff desk priority apply |

### AI rules

- Optional: core ticket/payment/check-in flows never require AI.
- Provider keys stay on the server (`AI_API_KEY`); status endpoint never returns secrets.
- Context is scrubbed via `ai_context_scrubber` before provider calls (no secrets, QR, payments, private venues when privacy ≠ `full_public`, Vault, messages, admin/CRM notes, buyer PII, private fulfillment notes).
- Support ticket context loads server-side (public messages); extra redaction for emails/phones/payment refs/QR secrets; internal notes are not sent to the model in Phase 1.
- Admin summaries use aggregate counts / public titles / display names only (`admin_context.py`).
- Blog CMS AI uses scrubbed title/excerpt/body/category/tags only (`blog_context.py`); never admin notes or private user data.
- Feature toggles: `DEFAULT_FEATURE_ENABLED` + `AI_DISABLED_FEATURES` env; hard stop via `AI_KILL_SWITCH`.
- Suggestions always require human confirmation (`requires_human_confirmation: true`, `draft_only: true`).
- `can_auto_publish`, `can_auto_send`, and `can_modify_finance` are always `false`.
- Support AI never auto-sends replies, auto-closes tickets, or changes status/refunds/payouts/moderation.
- Admin AI summaries never moderate, refund, suspend, feature, hide, pay out, or message.
- Blog AI never publishes posts or sends social posts; tag suggestions are catalog-constrained.
- Usage written to `ai_usage_logs` (tokens, estimated cost micros, latency in `meta`); audit `ai.generation_*` actions — never store raw secrets.
- Output validation rejects banned policy/sales/merch overclaims and private-data echoes; merch categories must resolve to catalog slugs; support categories/priorities/articles are catalog-constrained; reply drafts reject refund/payment overclaims; admin summaries reject automated decision language; blog drafts reject fake policy/legal guarantees.
- If AI is disabled or the HTTP provider fails, a template fallback draft is returned (unless kill switch).
- Event Studio Basics, Merch Studio Basics, Support AI Assist, Admin AI Summary, and Blog AI Assist panels wire inline generate; applying fills fields or composer only — never publishes products/events/posts, never sends replies, and never changes price/inventory/finance.

## Sponsorship marketplace (Phase 16)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/sponsorships/public/slots` | Public | Published slots from verified hosts |
| GET | `/api/v1/sponsorships/public/slots/{id}` | Public | Slot detail |
| GET | `/api/v1/sponsorships/public/hosts` | Public | Verified hosts accepting sponsors |
| POST | `/api/v1/sponsorships/public/slots/{id}/inquire` | Optional | Submit sponsor inquiry (audited) |
| POST | `/api/v1/sponsorships/public/placements/{id}/impression` | Public | Placement impression counter |
| POST | `/api/v1/sponsorships/public/placements/{id}/click` | Public | Placement click counter |
| GET/PATCH | `/api/v1/sponsorships/host/settings` | `sponsorships.manage_own` | Host sponsorship settings |
| GET/POST | `/api/v1/sponsorships/host/slots` | Host | List / create slots |
| PATCH | `/api/v1/sponsorships/host/slots/{id}` | Host | Update / publish slot |
| GET | `/api/v1/sponsorships/host/inquiries` | Host | Manage inquiries |
| PATCH | `/api/v1/sponsorships/host/inquiries/{id}` | Host | Update inquiry status |
| GET/POST | `/api/v1/sponsorships/host/placements` | Host | Placements + analytics row |
| GET | `/api/v1/sponsorships/admin/slots` | `sponsorships.moderate` | Admin list |
| POST | `/api/v1/sponsorships/admin/slots/{id}/moderate` | Admin | Flag / approve / disable / remove |

## Sponsor profiles (workspace)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/sponsors/workspaces` | User | Sponsor workspaces (owned + team) |
| POST | `/api/v1/sponsors/profiles` | User | Create sponsor profile (assigns `sponsor` role) |
| GET/PATCH | `/api/v1/sponsors/me` | Owner/team | View / edit own sponsor (`sponsor_id` query for multi) |
| GET | `/api/v1/sponsors/me/inquiries` | `sponsors.view_inquiries` | Outbound marketplace inquiries |
| GET | `/api/v1/sponsors/public/directory` | Public | Verified public sponsors only |
| GET | `/api/v1/sponsors/public/{slug}` | Public | Rich partnership profile: basics, summary cards, `public_case_study` campaigns (moderation **approved** only), public sponsored events/placements, partnered hosts, locations/categories, related sponsors. **Excludes** budget, invoices, payments, team, internal notes, private campaigns, unlisted events, suspended hosts. Demo/Acme placeholder covers are stripped (`use_cover_fallback: true`). |
| GET | `/api/v1/admin/sponsors` | `admin.sponsors.view` | Admin list |
| GET | `/api/v1/admin/sponsors/{id}` | Admin | Detail + internal notes |
| POST | `/api/v1/admin/sponsors/{id}/verify` | `admin.sponsors.verify` | Approve / reject verification |
| POST | `/api/v1/admin/sponsors/{id}/status` | `admin.sponsors.restrict` | Restrict / suspend / archive |
| PATCH | `/api/v1/admin/sponsors/{id}/notes` | `admin.sponsors.moderate` | Internal notes |

### Sponsor team

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/sponsors/workspaces/{sponsor_id}/team` | `sponsors.view_own` | Members + pending invites |
| POST | `/api/v1/sponsors/workspaces/{sponsor_id}/team/invites` | Owner/admin + `sponsors.manage_team` | Invite by email |
| POST | `.../team/invites/{invite_id}/resend` | Owner/admin | Resend invite email |
| DELETE | `.../team/invites/{invite_id}` | Owner/admin | Cancel pending invite |
| PATCH | `.../team/members/{member_id}` | Owner/admin | Change role |
| DELETE | `.../team/members/{member_id}` | Owner/admin | Remove member |
| GET | `.../team/audit` | Owner/admin | Team audit feed |
| GET | `/api/v1/sponsors/team/invites/{token}` | Public | Invite preview |
| POST | `/api/v1/sponsors/team/invites/{token}/accept` | User | Accept invite |

### Sponsor saved items

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/sponsors/workspaces/{sponsor_id}/saved` | `sponsors.view_own` | List saved (filter `item_type`, sort) |
| POST | `/api/v1/sponsors/workspaces/{sponsor_id}/saved` | `sponsors.save_items` | Save (idempotent) |
| PATCH | `/api/v1/sponsors/workspaces/{sponsor_id}/saved/{saved_id}` | `sponsors.save_items` | Update private note |
| DELETE | `/api/v1/sponsors/workspaces/{sponsor_id}/saved/{saved_id}` | `sponsors.save_items` | Unsave |

**Sponsor campaigns** (`/api/v1/sponsors/workspaces/{sponsor_id}/campaigns*`)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `.../campaigns` | `sponsors.view_own` | List campaigns + counts |
| POST | `.../campaigns` | `sponsors.manage_campaigns` | Create (optional `sponsor_saved_item_id`) |
| GET/PATCH | `.../campaigns/{campaign_id}` | view / manage | Detail / update |
| POST | `.../campaigns/{campaign_id}/activate` | manage | Activate (moderation if public case study) |
| POST | `.../campaigns/{campaign_id}/pause` | manage | Pause |
| POST | `.../campaigns/{campaign_id}/archive` | manage | Archive (read-only after) |
| POST/DELETE | `.../campaigns/{campaign_id}/saved-items*` | manage | Link/unlink saved items |

**Admin sponsor campaigns** (`/api/v1/admin/sponsor-campaigns*`)

| Method | Path | Permission | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/sponsor-campaigns` | `admin.sponsor_campaigns.view` | Queue/list |
| GET | `/api/v1/admin/sponsor-campaigns/{id}` | view | Detail |
| POST | `.../approve` / `.../reject` | `admin.sponsor_campaigns.moderate` | Moderation |

Public slot inquire body may include optional `campaign_id` + `sponsor_id` when authenticated.

**Campaign recommendations**

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `.../campaigns/{campaign_id}/recommendations` | `sponsors.view_own` | Ranked host/event/slot matches |
| POST | `.../recommendations/{item_id}/feedback` | manage (click: view) | saved / dismiss / not_interested / etc. |
| GET | `/admin/sponsor-campaigns/{id}/recommendations/debug` | admin | Score breakdown + exclusions |

**Sponsor reports**

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/sponsors/workspaces/{sponsor_id}/reports/overview` | `sponsors.view_own` | Workspace aggregates |
| GET | `/sponsors/workspaces/{sponsor_id}/campaigns/{campaign_id}/reports` | view | Campaign funnel + placements |

### Sponsorship deals

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET/POST | `/host/sponsorship-deals` | host `sponsors.manage_slots` / view | Host proposals |
| GET/PATCH | `/host/sponsorship-deals/{deal_id}` | host | |
| POST | `/host/sponsorship-deals/{deal_id}/send` | host | draft → proposed |
| POST | `/host/sponsorship-deals/{deal_id}/cancel` | host | |
| GET | `/host/sponsorship-deals/reports/summary` | host `sponsors.view` | Pending/paid revenue |
| GET | `/sponsors/workspaces/{sponsor_id}/deals` | `sponsors.view_own` | |
| GET | `/sponsors/workspaces/{sponsor_id}/deals/{deal_id}` | view | |
| POST | `/sponsors/workspaces/{sponsor_id}/deals/{deal_id}/accept` | `sponsors.manage_campaigns` | Creates invoice |
| POST | `/sponsors/workspaces/{sponsor_id}/deals/{deal_id}/reject` | manage | |
| POST | `/sponsors/workspaces/{sponsor_id}/deals/{deal_id}/pay` | manage | Paystack init; webhook confirms |
| GET | `/admin/sponsorship-deals` | `admin.sponsorship_deals.view` | |
| GET | `/admin/sponsorship-deals/{deal_id}` | view | No raw provider payloads |
| POST | `/admin/sponsorship-deals/{deal_id}/cancel` | `admin.sponsorship_deals.manage` | |
| POST | `/admin/sponsorship-invoices/{invoice_id}/void` | `admin.sponsorship_deals.finance` | |

### Sponsorship deliverables

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/host/sponsorship-deals/{deal_id}/deliverables` | host | |
| PATCH | `/host/sponsorship-deals/{deal_id}/deliverables/{id}` | `sponsors.manage_slots` | Progress only |
| POST | `/host/sponsorship-deals/{deal_id}/deliverables/{id}/submit` | host manage | Proof URL |
| GET | `/sponsors/workspaces/{sponsor_id}/deals/{deal_id}/deliverables` | view | |
| POST | `…/deliverables/{id}/approve` | `sponsors.manage_campaigns` | |
| POST | `…/deliverables/{id}/reject` | manage | Revision reason |
| GET | `/admin/sponsorship-deals/{deal_id}/deliverables` | `admin.sponsorship_deals.view` | |
| PATCH | `/admin/sponsorship-deals/{deal_id}/deliverables/{id}` | `admin.sponsorship_deals.manage` | Override |

### Sponsorship rules

- Only **verified** hosts can publish slots; drafts allowed for unverified hosts.
- Public visibility requires published status, host verified + accepting sponsors, and moderation not `removed`.
- Sponsorship listings never auto-approve events or touch ticket/payment flows.
- Inquiries create/update a `sponsors` row and write audit logs.
- Admin moderation is audited (`sponsorships.moderate.*`).

## Advanced ticketing (Phase 17)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/tickets/{id}/transfer` | Owner | Transfer to registered user email |
| GET | `/api/v1/tickets/{id}/transfers` | Owner / host / admin | Ticket transfer history |
| GET | `/api/v1/tickets/events/{event_id}/transfers` | Host scanner / admin | Event transfer history |
| GET | `/api/v1/tickets/mine` | Buyer | Ticket cards with event/host display fields + safe `location_label` (no street/private venue; list omits QR payload) |
| GET | `/api/v1/tickets/{id}/pdf` | Owner | Downloadable PDF pass (`application/pdf`, `Content-Disposition: attachment`). Status variants: active (Valid ticket + static QR), used (Used + USED watermark, QR kept for audit), cancelled/refunded (watermark, no QR), pending (Pending confirmation, no valid-access copy/QR). |
| POST | `/api/v1/tickets/{id}/cancel` | Owner / super admin | Cancel ticket + revoke QR (body requires `password`; irreversible; wrong password → 403) |
| POST | `/api/v1/tickets/{id}/qr-mode` | Owner | `static` or `rotating` QR |
| POST | `/api/v1/tickets/{id}/bind-device` | Owner | Device-binding placeholder |
| GET/POST | `/api/v1/tickets/events/{event_id}/tables` | Host | Table reservations |
| PATCH | `/api/v1/tickets/tables/{id}/assign` | Host | Seat/table assignment placeholder |
| GET | `/api/v1/tickets/admin/list` | Admin / finance | Platform ticket list |
| GET | `/api/v1/tickets/admin/transfers` | Admin / finance | Transfer audit list |
| GET | `/api/v1/admin/events/{event_id}/buyers` | `admin.events.view` **and** `admin.events.export_buyers` | Filtered event buyers JSON (paginated; no private contact) |
| GET | `/api/v1/admin/events/{event_id}/buyers/export` | same + mode gates | CSV/JSON (`format`, `mode=public_summary\|operations\|finance`, filters, `reason`, `include_private_contact`); XLSX → 400 |
| GET | `/api/v1/admin/events/{event_id}/buyers/exports` | same base perms | Export audit history |
| GET | `/api/v1/tickets/admin/events/{event_id}/buyers/export.csv` | same base perms | Legacy CSV alias (`operations` mode) |

Buyer export modes: private email/phone needs `admin.events.export_private_contact` + reason; finance mode needs `admin.finance.export_event_sales` + reason. Hosts with only `payments.view` → 403. Details: [TICKETS.md](./TICKETS.md) · [ADMIN.md](./ADMIN.md).

| POST | `/api/v1/checkins/offline/sync` | Scanner | Sync offline scan batch |

### Advanced ticketing rules

- Transfer updates current owner (`buyer_user_id`), reissues QR, writes `ticket_transfers` + audit (`tickets.transfer`). Old owner loses access; old QR fails `jti` validation.
- Group/table types with `seats_per_unit > 1` issue multiple attendee tickets under `ticket_groups`.
- Rotating QR uses short-lived signed JWTs; validation still requires signature + event + current `jti` hash.
- Offline sync accepts/conflicts/invalidates per scan; already checked-in tickets become conflicts.
- Cancelled/refunded tickets fail check-in validation (unchanged invariant).
- Normal single-seat tickets continue to issue and scan as before.

## Taxonomy & content graph

Contract: [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md). SEO: [SEO.md](./SEO.md).

### Public

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/events` | Public | Published listed events; optional filters `q`, `category`, `city`, `location_kind`, `location_slug`, `weekend`, `paid`, `event_format`, `secret_location`, `sort` |
| GET | `/api/v1/events/padeya-picks` | Public | Up to 2 live Pàdéyá Picks (see rules below) |
| GET | `/api/v1/events/categories` | Public | Legacy active `event_categories` |
| GET | `/api/v1/taxonomy/categories` | Public | Active taxonomy categories (+ usage when admin-shaped) |
| GET | `/api/v1/taxonomy/categories/{slug}/subcategories` | Public | Active subcategories for a category |
| GET | `/api/v1/taxonomy/tags` | Public | Active tags |
| GET | `/api/v1/taxonomy/vibes` | Public | Active vibes |
| GET | `/api/v1/taxonomy/host-types` | Public | Active host types |
| GET | `/api/v1/taxonomy/audience-types` | Public | Active audience types |
| GET | `/api/v1/taxonomy/locations` | Public | Active locations; optional `kind`, `parent_id` |
| GET | `/api/v1/taxonomy/locations/{kind}/{slug}` | Public | Location detail + ancestors + children (always pass `kind` — slugs can collide) |
| GET | `/api/v1/taxonomy/health` | Public | Module health |

### Featured Placement Slots (admin)

Permission: `admin.full_access` or `events.approve`. Not sponsorship placements.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/admin/featured-placements/contexts` | List configured placement sets (`include_archived`) |
| GET | `/api/v1/admin/featured-placements/sets/{set_id}` | Get one set (`set_id` = Primary slot UUID) |
| PUT | `/api/v1/admin/featured-placements/sets` | Upsert Primary+Secondary set |
| POST | `/api/v1/admin/featured-placements/sets/{set_id}/status` | Body `{ "status": "active" \| "draft" \| "archived" }` |
| GET | `/api/v1/admin/featured-placements` | List slots for a context (`context_type`, `location_id`, `category_id`) |
| PUT | `/api/v1/admin/featured-placements/{slot_number}` | Assign/clear slot `1` or `2` (+ title/schedule/status) |
| POST | `/api/v1/admin/featured-placements/listing-picks` | Listing admin: assign published event to homepage/events_page (`event_id`, optional `slot_number`) |
| POST | `/api/v1/admin/featured-placements/listing-picks/clear` | Listing admin: clear event from homepage/events_page picks |
| POST | `/api/v1/admin/featured-placements/listing-picks/swap` | Swap Primary/Secondary for homepage/events_page |
| POST | `/api/v1/events/admin/{id}/padeya-pick` | Same assign via event admin (`?context_type=&slot_number=`) |
| POST | `/api/v1/events/admin/{id}/unpadeya-pick` | Same clear via event admin (`?context_type=`) |

### Fan host recommendations (rules-only)

Auth required except admin debug. See [HOST_RECOMMENDATIONS.md](./HOST_RECOMMENDATIONS.md).

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/hosts/recommendations` | Fan | Personalized ranked hosts (score 0–100) |
| POST | `/api/v1/hosts/recommendations/impressions` | Fan | Batch impression log |
| POST | `/api/v1/hosts/recommendations/{host_id}/dismiss` | Fan | Dismiss / hide host |
| POST | `/api/v1/hosts/recommendations/{host_id}/not-interested` | Fan | Dismiss + category penalty |
| POST | `/api/v1/hosts/recommendations/{host_id}/more-like-this` | Fan | Boost similar signals |
| POST | `/api/v1/hosts/recommendations/{host_id}/click` | Fan | Click feedback |
| POST | `/api/v1/hosts/recommendations/{host_id}/follow` | Fan | Follow feedback |
| POST | `/api/v1/hosts/recommendations/hide-category` | Fan | Hide category slug |
| GET | `/api/v1/admin/recommendations/hosts/debug` | `admin.full_access` | Per-user host scoring debug |

### Fan event recommendations (rules-only)

Auth required except admin debug. See [EVENT_RECOMMENDATIONS.md](./EVENT_RECOMMENDATIONS.md).

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/events/recommendations` | Fan | Personalized ranked events (`exclude_event_id`, `context_event_id`, `host_id` for detail context) |
| POST | `/api/v1/events/recommendations/impressions` | Fan | Batch impression log |
| POST | `/api/v1/events/recommendations/{event_id}/feedback` | Fan | Recommendation feedback actions |
| GET | `/api/v1/admin/recommendations/events/debug` | `admin.full_access` | Per-user event scoring debug |

### Host profile taxonomy

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/hosts/me` | Host | Includes `taxonomy` (types, categories, audience, city, niche) |
| PATCH | `/api/v1/hosts/me` | Host | Dual-write profile + optional `host_type_slugs`, `category_slugs`, `audience_slugs`, `primary_city_slug`, `service_area_slugs`, `niche_positioning` |

### Host team

True pending email invites, role/permission toggles, host-wide vs per-event scope, hybrid desk scan, workspace switch, audit feed. Overview: [TEAMS.md](./TEAMS.md) · catalog: [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) · deep: [HOST_TEAM.md](./HOST_TEAM.md).

Canonical routes:

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/host/team` | Host / `team.view` | List members (`host_id` or `X-Padeya-Host-Id`) |
| POST | `/api/v1/host/team/invites` | Host / `team.invite` | Invite by `invite_identifier` (email or `@username`); body may include `permissions_json`, `scope_json`, `selected_event_ids`. Response: `invite_id` + method-safe fields (masked email **or** username/display/avatar — never private email for username) |
| GET | `/api/v1/host/team/invites/lookup` | Host / `team.invite` | Live preview for invite field (`identifier=`); username → display/avatar/`found`; email → message only; never returns private email |
| GET | `/api/v1/host/team/invites` | Host / `team.view` | List pending invites |
| POST | `/api/v1/host/team/invites/{id}/revoke` | Host / `team.remove_members` | Revoke pending invite |
| PATCH | `/api/v1/host/team/members/{id}` | Host / `team.edit_permissions` | Update role / permissions / scope |
| POST | `/api/v1/host/team/members/{id}/suspend` | Host / `team.remove_members` | Suspend member |
| POST | `/api/v1/host/team/members/{id}/remove` | Host / `team.remove_members` | Soft-remove member |
| GET | `/api/v1/host/team/audit-log` | Host / `team.view` | Unified team + desk audit (actor, action, target, entity, safe metadata) |
| GET | `/api/v1/host/team/permissions` | Auth | Permission catalog |
| GET | `/api/v1/host/team/roles` | Auth | Role presets catalog |
| GET | `/api/v1/team/invites/{token}` | Public | Safe invite preview |
| POST | `/api/v1/team/invites/{token}/accept` | Invitee | Accept invite |
| GET | `/api/v1/me/team-workspaces` | Auth | Owned + team + event-staff workspaces |
| POST | `/api/v1/me/active-workspace` | Auth | Persist active host workspace (`host_id`) |
| GET | `/api/v1/admin/teams` | `admin.full_access` | Platform team overview |
| GET | `/api/v1/admin/teams/audit` | `admin.full_access` | Platform team audit |

Legacy routes under `/api/v1/hosts/me/team*`, `/hosts/{host_id}/team*`, and `/hosts/team-invites/*` remain available.

### Admin taxonomy (`admin.full_access` or `events.approve`)

Pattern for each resource (`categories`, `tags`, `locations`, `host-types`, `venue-types`):

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/taxonomy/admin/{resource}` | List (`include_archived` / `include_inactive`) |
| POST | `/api/v1/taxonomy/admin/{resource}` | Create |
| PATCH | `/api/v1/taxonomy/admin/{resource}/{id}` | Update |
| POST | `/api/v1/taxonomy/admin/{resource}/{id}/archive` | Soft archive |
| POST | `/api/v1/taxonomy/admin/{resource}/{id}/restore` | Restore |
| DELETE | `/api/v1/taxonomy/admin/{resource}/{id}` | **405** — hard delete blocked; use archive |
| GET | `/api/v1/taxonomy/admin/categories/{id}/subcategories` | List subcategories (`include_archived`) |
| POST | `/api/v1/taxonomy/admin/categories/{id}/subcategories` | Create subcategory |
| PATCH | `/api/v1/taxonomy/admin/subcategories/{id}` | Update subcategory |
| POST | `/api/v1/taxonomy/admin/subcategories/{id}/archive` | Soft archive subcategory |
| POST | `/api/v1/taxonomy/admin/subcategories/{id}/restore` | Restore subcategory |

### Rules

- **Location filter:** `location_kind` + `location_slug` return events at that node or any descendant (`location_id`). When `location_id` is null, free-text `city`/`state` may still match as a compatibility fallback. Legacy `city=` filters slugified `events.city` only.
- **Location privacy:** `location_visibility` ∈ `full_public` \| `area_only` \| `hidden_until_payment` \| `hidden_until_24h_before` \| `hidden_until_manual_approval` \| `online_only`. Public payloads never include redacted street addresses or private online URLs. Full access-level rules: Event Studio section above.
- **Pàdéyá Picks (`GET /events/padeya-picks`):** query `context` (placement_type or legacy alias; default events page), optional `location_kind`/`location_slug`/`category`. Returns ≤2 `EventPublic` in slot order. Live statuses only (`active`/`scheduled` within window). Privacy applied.
- **Placement types:** `homepage`, `events_page`, `country_page`, `state_page`, `city_page`, `area_page`, `category_page`, `city_category_page`. Legacy aliases: `global_homepage`→`homepage`, `events`→`events_page`, bare `country`/`state`/`city`/`area`/`category`/`city_category`.
- **Placement set upsert** creates both slots under `placement_key` (e.g. `homepage`, `city_page:{uuid}`, `area_page:{uuid}`, `city_category_page:{city}:{cat}`). Same event on both slots → `409`. Assign requires published + `listed`/`approval_required`. Cancelled/rejected/draft events cannot be activated. Support without `events.approve` / `admin.full_access` → `403`. Changes are audit-logged.
- Soft-archiving a category does not delete or 404 published events that still reference it.
- Host taxonomy sync rejects inactive/unknown slugs (`400`).
- Buyers and non-admin hosts receive `403` on `/taxonomy/admin/*` and `/admin/featured-placements/*`.