# Pàdéyá Ambassadors

Brand: **Pàdéyá**. Public product name: **Ambassadors** (Event Ambassadors, Pàdéyá Ambassadors).

**Ambassador = promoter/referrer. Host Team = operations/staff. Keep them completely separate.** Joining never creates host-team membership, staff assignment, scanner access, or workspace access.

Related: [PROMO_CODES.md](./PROMO_CODES.md) · [PAYMENTS.md](./PAYMENTS.md) · [TICKETS.md](./TICKETS.md) · [MERCH.md](./MERCH.md) · [CHECKOUT.md](./CHECKOUT.md) · [HOST_AS_FAN.md](./HOST_AS_FAN.md) · [PRIVACY.md](./PRIVACY.md#ambassadors) · [SECURITY.md](./SECURITY.md#ambassadors-fraud-controls) · [API.md](./API.md#ambassadors-domain-api-phase-10) · [DEMO_DATA.md](./DEMO_DATA.md#open-event-ambassadors-demo)

## Product model (summary)

| Topic | Rule |
|---|---|
| [Open participation](#open-participation-model) | Eligible logged-in users self-join a live `public_open` / `active` campaign — not invite-only |
| [Who can join](#who-may-participate) | Active account + terms + live open campaign + not blocked/suspended |
| [Campaign types](#campaign-types-v1) | `event_tickets` · `event_merch` (host-wide deferred); one open campaign per type per event |
| [Referral links / codes](#referral-links-and-codes) | Unique code per campaign; `?ref=` / `?amb=` on event or merch URLs |
| [Attribution](#attribution-rules) | Last-click cookie (default 30 days); **explicit checkout code wins** over cookie/link |
| [Commission](#commission-invariants) | `%` / flat / reward-only; hold period; caps; free-ticket-after-X; leaderboard reward |
| [Payment verification](#payment-integration-phase-11) | Commission **only** after verified paid webhook — never from FE success |
| [Refund reversal](#payment-integration-phase-11) | Approved refund / ticket cancel reverses v1 sales + domain conversions |
| [Privacy](#privacy-phase-13) | No buyer PII, payment refs, QRs, attendee lists, shipping, or host-team data |
| [Fraud](#fraud-controls-phase-14) | Self-referral block · host-owner guard · rate limits · hashed IP/UA · click spikes |

## Open participation model

Open Event Ambassadors is **self-serve**:

1. Host creates a live Ambassadors campaign for an event (`public_open` / domain `active` + `visibility=public_open`) — which sets `events.open_ambassadors_enabled`.
2. Any eligible fan browses `/ambassadors` or an event **Promote this event** CTA.
3. They accept terms, receive a unique **Ambassador code** + share link/QR.
4. Buyers land with `?ref=` / enter the code at checkout → pending order may store attribution.
5. **Verified Paystack payment** creates commission rows; refunds reverse them.

Paused / ended campaigns block new joins and new click attribution. Platform kill-switch: `ambassador_platform_settings.enabled`.

Not the same as: ticket [promo codes](./PROMO_CODES.md), merch discount codes, host team, or event staff.

## Core product rules

### Who may participate

Anyone can join **open** Ambassadors when **all** of these are true:

1. They have a Pàdéyá account  
2. Their account is **active** (`users.is_active`)  
3. They **accept Ambassador terms** (recorded with `terms_version`)  
4. The campaign is **joinable** (live status + public visibility + optional start/end window)  
5. They are **not blocked/suspended** (`users.ambassadors_blocked`, `ambassador_profiles.status`, or removed from that campaign)  
6. Host owners cannot join their own campaign unless `allow_host_owner_commission` is true  

Logged-out users must sign in before join.

### Ambassadors do **not** get

| Never granted | Belongs to |
|---|---|
| Host dashboard access | Host owner / host team |
| Scanner / check-in access | Event staff / host team desk perms |
| Merch pickup access | Event staff / host team desk perms |
| Buyer private data | Orders / support / host ops |
| Attendee lists | Host / staff |
| Payment references | Host finance / gateway (hidden from ambassador dashboards) |
| Event staff permissions | `event_staff_assignments` |
| Host team permissions | `host_team_members` ([TEAMS.md](./TEAMS.md)) |

## Notifications (phase 15)

Uses existing email + in-app + push (`enqueue_template` / `notify_user`). Module: `app/ambassadors/notifications.py`.

| Template | When | Audience |
|---|---|---|
| `ambassador_joined` | Join / rejoin campaign | Ambassador |
| `ambassador_first_sale` | First verified sale/conversion | Ambassador |
| `ambassador_commission_payable` | Reward approved (host/team/admin) | Ambassador |
| `ambassador_payout_ready` | Reward marked paid | Ambassador |
| `ambassador_reward_rejected` | Reward rejected | Ambassador |
| `ambassador_reward_reversed` | Reward reversed | Ambassador |
| `ambassador_campaign_paused` | Host pauses campaign | Active participants |
| `ambassador_campaign_ended` | Host ends campaign | Active participants |
| `host_ambassador_milestone` | Campaign hits 1 / 10 / 25 / 50 sales | Host owner |
| `host_ambassador_team_reward_action` | Team member approved / marked paid | Host owner |
| `host_ambassador_suspicious_reversal` | Reversal with open fraud flag | Host owner |
| Admin fraud / high-value / suspicious reversal | Open fraud flag, high-value mark-paid, flagged reverse | Super admins (`notify_admins_report`) |

Copy rules: event/campaign names and status words only — no buyer PII, payment refs, order IDs, or raw IP. Prefs: ambassador self → `email_ticket_updates` / `push_ticket_updates`; host milestone / team reward → `email_host_activity` / `push_host_activity`.

High-value admin alert threshold: `AMBASSADOR_HIGH_VALUE_REWARD_NGN` (default `50000`; `0` disables).

## Fraud controls (phase 14)

| Control | Behavior |
|---|---|
| Self-referral | **Always blocked** when buyer user == ambassador user (attach + finalize, v1 + domain); approve also re-checks |
| Host-owner commission | Blocked unless `ambassador_campaigns.allow_host_owner_commission` is true (join + attach + finalize). Part of [Host-as-Fan](./HOST_AS_FAN.md) — owners do not earn reward on their own host by default |
| Own-host checkout | Owner cannot buy own-host tickets/merch (defense-in-depth with commission + self-referral) — [CHECKOUT.md](./CHECKOUT.md) |
| Track rate limit | `POST /ambassadors/track-click` and `POST /promos/referrals/click` → 429 via `ambassador_track_rate_limit_per_minute` (default 60) |
| Hashed signals | IP + UA stored as salted hashes only (`hash_ip` / `hash_user_agent`); raw IP never persisted |
| Click spikes | Open `ambassador_fraud_flags` (`click_spike`) when hashed IP + participant exceeds threshold in window |
| Suspicious conversion flag | Host/team: `POST /host/ambassadors/conversions/{id}/flag` → `suspicious_conversion` flag (+ admin notify) |
| Host remove | `POST /host/ambassadors/participants/{id}/remove` (and v1 campaign remove) |
| Admin block | `POST /admin/ambassadors/participants/{id}/block` (+ platform `ambassadors_blocked`) |
| Test / admin inflation | Test/admin flows must not create commission or public ranking lift; no live Paystack for owner own-host QA; future test orders must be metric-excluded |
| Refunds | Full refund approve reverses v1 sales + domain conversions; refunded orders cannot be marked paid |
| Ticket cancel | `cancel_ticket` reverses commission for the order (idempotent) |
| Admin override | Platform admin may force status changes / reverse via oversight endpoint |

Admin UI: `/admin/ambassadors/fraud` lists open click spikes + reversed conversions.  
Config: `ambassador_track_rate_limit_per_minute`, `ambassador_click_spike_window_seconds`, `ambassador_click_spike_threshold`, `ambassador_high_value_reward_ngn`.  
Code: `app/ambassadors/fraud.py`, `app/ambassadors/rate_limit.py`, `app/ambassadors/reward_audit.py`. Tests: `tests/test_ambassador_fraud.py`, `tests/test_ambassador_host_rewards.py`.

## Privacy (phase 13)

Ambassadors must **never** see:

- Buyer email or phone
- Private attendee lists
- Ticket QR or merch pickup QR
- Payment references / Paystack refs
- Internal order IDs
- Hidden venue / private street address
- Shipping address
- Fan Connect graph
- Host team data (members, invites, desk perms)

Ambassadors **may** see:

- Clicks
- Number of verified sales
- Eligible sales total (`revenue_amount` / `gross_eligible`)
- Estimated commission and commission status
- Timestamps (`created_at`, `hold_until`, joined_at)
- Campaign / event / merch **names** (and public slug for share links)

**Hosts / team** (conversion ledger) may see: ambassador name/user, campaign, conversion timestamp, eligible sale amount, commission amount, status, payout status, optional payout reference/note (ops meta — not a payment gateway ref).

**Hosts / team must not see:** buyer email/phone, full order/payment refs, attendee lists, ticket/merch pickup QRs, hidden venue/private address, Fan Connect graph, shipping address (unless a separate shipping role needs it on merch routes).

Enforcement:

- Allowlist sale rows via `app/ambassadors/privacy.py` (`sale_row_for_ambassador`)
- Self DTOs: `AmbassadorSaleSelfPublic` / `AmbassadorSelfDashboard` (no `order_id` / `order_reference`)
- Host conversion DTO (`serialize_conversion`) omits `order_id` by default; admin oversight may include order refs
- Tests: `tests/test_ambassador_privacy.py`, `tests/test_ambassador_host_rewards.py::test_host_conversion_dto_hides_buyer_private_data`

Also: [PRIVACY.md](./PRIVACY.md#ambassadors) · [SECURITY.md](./SECURITY.md#ambassadors-privacy)

## What it is

Any eligible logged-in Pàdéyá user can become an ambassador for an **eligible** event, get a unique **Ambassador link** / **Ambassador code**, promote the event, and earn **Ambassador earnings** (commission) when **verified paid purchases** happen through their link/code.

| This is | This is not |
|---|---|
| Open participation for eligible events | Invite-only |
| Referral / promotion | Host team access ([TEAMS.md](./TEAMS.md)) |
| Attribution after Paystack webhook | Scanner / staff desk access |
| Commission on attributed paid orders | Ticket promo codes or merch discount codes |

## Domain schema (phase 9)

Target tables (migration `20260719_0084`). Services still use v1 (`ambassadors`, `promo_clicks`, `ambassador_sales`) until cutover.

| Table | Purpose | Lifecycle |
|---|---|---|
| `ambassador_profiles` | One identity per user | `active` / `suspended` / `blocked` |
| `ambassador_campaigns` | Campaign rules + visibility + cookie/hold | Soft end/archive; extended columns coexist with v1 |
| `ambassador_participants` | Profile enrolled in a campaign + code | `active` / `paused` / `removed` / `blocked` |
| `ambassador_clicks` | Append-only click funnel | Never delete |
| `ambassador_attributions` | Attribution window (`link` / `code` / `qr`) | Expire via `expires_at` |
| `ambassador_conversions` | Commission ledger + `dedupe_key` | Reverse / reject only |
| `ambassador_payouts` | Payout requests | Cancel soft; paid immutable |
| `ambassador_audit_logs` | Domain audit (`metadata_json`) | Append-only |

Models: `backend/app/promos/ambassador_domain.py` (+ campaign columns on `AmbassadorCampaign`).

## Programs

| Kind | Who creates | Scope | Code uniqueness |
|---|---|---|---|
| `host_curated` | Host (existing Phase 8) | Host-wide partners | Unique `(host_id, referral_code)` when `event_id` is null |
| `open_event` | Self-serve join via live campaign | One event / campaign | Unique `(event_id, referral_code)` and `(event_id, user_id)` |

### Campaign types (v1)

| Type | Public name | Commission from |
|---|---|---|
| `event_tickets` | Event Ambassador | Verified **ticket** sales for that event |
| `event_merch` | Event Merch Ambassador | Verified **event-linked merch** orders |
| `host` | Host Ambassador | Out of scope for v1 (host-wide eligible events) |

An event may have **one open campaign per type** (tickets + merch side by side). Users join a specific type and get a link/code for that campaign. Attribution uses the ambassador’s campaign type — ticket campaigns never earn on merch lines, and merch campaigns never earn on ticket lines.

### Host campaigns

Hosts enable open promotion by creating an **Ambassador campaign** for an event.

| Field | Notes |
|---|---|
| `campaign_type` | `event_tickets` (default) or `event_merch` |
| `status` | Default `public_open`; also `paused`, `ended` (`invite_only` later) |
| `commission_type` | `percentage` (default), `flat`, or `reward_only` |
| `commission_value` | Percent (0–100) or flat NGN; `0` for reward-only |
| `commission_percent` | Legacy mirror of percentage value; snapshotted at join for % campaigns |
| `applies_to` | `tickets`, `merch`, or `tickets_and_merch` |
| `hold_period_days` | Default `7`; sale `hold_until` gates approval / payable |
| `payout_minimum` | Optional minimum before payout (nullable) |
| `max_commission_per_order` | Optional cap per attributed order |
| `free_ticket_after_sales` | Optional; sets `ambassadors.free_ticket_earned_at` after X confirmed sales |
| `leaderboard_reward_*` | Optional non-cash leaderboard reward flag + description |
| `merch_included` | Derived from type (`true` only for `event_merch`) |
| `starts_at` / `ends_at` | Optional window; outside window → not live |

### Commission invariants

- Commission is created only after **verified paid** payment (`order.status=paid`).
- Pending / failed payments never create `ambassador_sales`.
- Duplicate webhooks are idempotent (`uq_ambassador_sales_order_id` + early return).
- Refunded / cancelled orders reverse commission (`status=reversed`); admin fraud reverse remains available.
- Flat tickets = value × ticket qty; flat merch = value once per merch order; percentage uses commissionable revenue after `applies_to` filter.

Host routes: `/host/ambassadors`, `/host/ambassadors/campaigns`, `/host/ambassadors/campaigns/new`, `/host/ambassadors/campaigns/[id]`, `/host/ambassadors/conversions`, `/host/ambassadors/payouts`, `/host/events/[id]/ambassadors`.

Hosts can pause/resume/end, remove abusive ambassadors (`status=removed`), view leaderboard + clicks/sales/conversions + payout summary, and **manage rewards for host-owned campaigns**.

### Reward status — two endpoints (host normal, admin oversight)

**Status transitions (v1 sales ledger):**

| From | To | Notes |
|---|---|---|
| `attributed` | `approved` | Verified paid order; past hold; not self-referral |
| `attributed` / `approved` | `rejected` | Reason required (≥3 chars) → `rejection_reason` |
| `approved` | `paid` | Optional `payout_reference` / `payout_note`; not refunded/cancelled order |
| `attributed` / `approved` / `rejected` | `reversed` | Reason required; paid → reverse via finance first |
| (admin) | `attributed` | Oversight reopen only |

**Normal host-owned workflow does not require `admin.full_access`.** Hosts approve and mark rewards paid for their own Ambassadors via the host endpoint. Admin controls stay for oversight and are **not** exclusive. Marking paid records host payout meta — it is **not** the platform host-balance payout rail ([PAYMENTS.md](./PAYMENTS.md)).

| Path | Who | Purpose |
|---|---|---|
| `POST /host/ambassadors/conversions/{conversion_id}/reward-status` | Host owner or team with `ambassadors.*` / finance perms | **Normal** approve / reject / mark paid / reverse for **host-owned** campaigns |
| `POST /promos/admin/conversions/{sale_id}/reward-status` | Platform admin (`admin.full_access`) | **Oversight only** — fraud intervention, support escalation, platform-wide campaigns, emergency correction |
| `POST /host/ambassadors/conversions/{id}/flag` | Host / team (`view_conversions` / reward perms) | Flag suspicious conversion |
| `GET /host/ambassadors/conversions/{id}/audit` | Host / team | Per-conversion reward audit |
| `GET /host/ambassadors/reward-audit` | Host / team | Host workspace reward audit feed |
| `GET /admin/ambassadors/reward-audit` | Admin | Platform-wide reward audit |

Admin endpoint uses:
- Platform oversight across all hosts  
- Fraud intervention / forced reverse  
- Support escalation when a host cannot resolve  
- **Platform-wide** campaigns (`source=platform`) — host/team cannot manage these  
- Emergency correction (including `attributed` reopen)

Host endpoint uses:
- Day-to-day approval and payout workflow for campaigns the host owns  
- Active host workspace ownership check  
- Team permission gates (`approve_rewards`, `mark_rewards_paid` / `finance.manage_payouts`, etc.)

Denied on host path: random users; ambassadors on their own rewards; suspended/removed team members; other hosts’ teams; host/team access to **platform** campaigns.

| Team permission | Action |
|---|---|
| `ambassadors.view` | View campaigns / analytics |
| `ambassadors.create_campaigns` | Create campaigns |
| `ambassadors.edit_campaigns` | Edit campaign settings |
| `ambassadors.pause_campaigns` | Pause / end campaigns |
| `ambassadors.remove_participants` | Remove participants |
| `ambassadors.view_conversions` | List conversions |
| `ambassadors.view_payouts` | View Ambassador payout summary |
| `ambassadors.approve_rewards` | Approve **or** reject |
| `ambassadors.reject_rewards` | Reject only (finer grant) |
| `ambassadors.mark_rewards_paid` **or** `finance.manage_payouts` | Mark paid |
| `ambassadors.reverse_rewards` | Reverse with reason |
| `ambassadors.export` **or** `finance.view_payouts` | CSV export |

Host UI: `/host/ambassadors/conversions`, `/host/ambassadors/payouts` · Admin UI: `/admin/ambassadors/conversions`

Host body: `{ status: approved|rejected|paid|reversed, reason?, payout_reference?, payout_note? }`

- Conversion must belong to a host-owned campaign for the active host workspace  
- `rejected` / `reversed` require `reason` (≥3 chars)  
- `paid` requires `ambassadors.mark_rewards_paid` or `finance.manage_payouts`  
- Approve requires verified `order.status=paid` (not pending/failed/refunded) and blocks self-referral  
- Duplicate same-status calls are idempotent; `paid` may refresh payout meta  
- Also: `GET .../conversions`, `GET .../conversions/export`, legacy `POST .../reverse`

### Reward audit logs

Every status change writes `audit_logs` via `app/ambassadors/reward_audit.py`:

| Action | When |
|---|---|
| `ambassador_reward_approved` | Host owner / team approves |
| `ambassador_reward_rejected` | Host owner / team rejects |
| `ambassador_reward_marked_paid` | Host owner / team marks paid |
| `ambassador_reward_reversed` | Host owner / team reverses |
| `ambassador_reward_status_changed_by_admin` | Platform admin oversight path |

Details include: `actor_user_id`, `actor_type` (`host_owner` \| `team_member` \| `platform_admin`), `host_profile_id`, `campaign_id`, `conversion_id`, `old_status`, `new_status`, `reason`, `payout_reference`, timestamp, optional IP/UA.

### Admin

Admin routes: `/admin/ambassadors`, `/admin/ambassadors/campaigns`, `/admin/ambassadors/conversions`, `/admin/ambassadors/payouts`, `/admin/ambassadors/reports`.

| Capability | Notes |
|---|---|
| View all campaigns | Host + platform sources |
| Create platform campaigns | `source=platform` for any event (still event-scoped) |
| Global enable/disable | `ambassador_platform_settings.enabled` — blocks join + eligible listings when off |
| Pause suspicious campaigns | Admin pause/resume with audit |
| Block abusive ambassadors | Sets `users.ambassadors_blocked` |
| Reverse fraudulent conversions | Sale → `reversed` (immutable reason); excluded from earnings |
| Manage reward status | **Oversight / emergency** for all campaigns; not required for normal host-owned approval |
| Audit logs | Actions under `ambassadors.*` / `users.ambassadors_block` |

## Eligibility (open Event Ambassadors)

Host enables on the event:

- `open_ambassadors_enabled` (default `false`)
- `open_ambassador_commission_percent` (default `5.00`; snapshotted onto the ambassador row at join)

Join body: `{ "accept_terms": true }` — required. Stores `terms_accepted_at` + `terms_version` (`AMBASSADOR_TERMS_VERSION`).

Platform block: admin `POST /users/admin/{id}/ambassadors/block` (unblock counterpart). Blocked users cannot join; their codes stop earning new attribution.

Re-joining an inactive enrollment reactivates it (terms accepted again). Leaving sets `status=inactive` (soft).

## Referral links and codes

Each open enrollment gets a **readable Ambassador code** (unique per campaign) and event-specific links:

| Link | Example |
|---|---|
| Event | `/events/{slug}?ref=TOLUAFRO` |
| Alias | `/events/{slug}?amb=TOLUAFRO` (`amb` = `ref`) |
| Merch | `/events/{slug}/merch?ref=TOLUAFRO` |

Dashboards support copy link, copy code, and download/share QR card (`qrcode.react`).

### Referral click tracking (canonical)

All referral landings flow through **`ReferralTrackingService`** (`backend/app/ambassadors/referral_tracking.py`):

| Endpoint | Notes |
|---|---|
| `POST /promos/referrals/click` | Event, merch, and host-wide landings (frontend default) |
| `POST /ambassadors/track-click` | Domain/campaign payloads — same service |

Rows are stored in **`referral_clicks`** (canonical). Legacy `promo_clicks` / `ambassador_clicks` may still exist historically; dashboards prefer `referral_clicks` with fallback.

**Metrics (dashboards):**

| Metric | Meaning |
|---|---|
| **Total clicks** | Referral landings after **30s** anti-duplicate (refresh/Strict Mode/double tab) |
| **Unique clicks** | First visit per privacy-safe visitor key per ambassador scope within **24h** (campaign-configurable later) |
| **Conversions** | Confirmed paid orders credited to the ambassador — **rewards use conversions, not raw clicks** |

**Visitor key (hashed, never shown to hosts):** logged-in user id → first-party anonymous id (`padeya_anonymous_id`) → salted IP+UA fallback. Raw IP/UA are not stored.

**Click vs checkout attribution:** Updating the `padeya_amb_ref_v1` cookie (last-click) is separate from inserting duplicate click rows within 30s. Checkout credit order unchanged: explicit code → URL `ref`/`amb` → cookie.

**Fraud (soft flags only):** click spikes (rate limit + hashed IP window), `click_inflation_suspect` when total ≫ unique in 24h. See admin Fraud flags.

Internal inventory: [COOKIES_AND_STORAGE.md](./COOKIES_AND_STORAGE.md) · stats helpers: `referral_click_stats.py`.

### Attribution rules

1. Landing with `?ref=` / `?amb=` records a click and sets a **30-day** last-click HTTP cookie (`padeya_amb_ref_v1`) for that event. Details: [COOKIES_AND_STORAGE.md](./COOKIES_AND_STORAGE.md).
2. At checkout, precedence is: **explicit Ambassador code field** → URL `ref`/`amb` → cookie.
3. Explicit checkout code is never overwritten by a later link/cookie source (`orders.referral_attribution_source`).
4. `POST /orders` resolves the code to an active ambassador (open enrollment first, then host-curated). Same code on ticket + merch campaigns prefers the type matching the cart.
5. **Self-referral blocked** — buyer matching the ambassador’s linked user is not attached.
6. On verified payment webhook, `finalize_promo_and_attribution` creates v1 `ambassador_sales`, and `finalize_ambassador_conversions` creates domain `ambassador_conversions` (`dedupe_key` = `{type}:{order}:{participant}:{campaign}`). Pending/failed orders never create commission. Refunds reverse both ledgers with audit.

### Payment integration (phase 11)

| Step | Behavior |
|---|---|
| Checkout | FE sends `referral_code` + `referral_source` (and optional `ambassador_attribution_id` / `referral_session_id`). Server stores participant on the **pending** order — no conversion yet. |
| Verified payment | Paystack webhook / free-order finalize only → ticket and/or merch conversions |
| Dedupe | Unique `dedupe_key` per campaign + participant + order + conversion type |
| Refund | Finance approve → reverse v1 sale + domain conversions (`status=reversed`, `refunded_at`) |
| Frontend | Success page must never create commission |

Ambassador-facing dashboards expose allowlisted aggregates only (see Privacy phase 13). Host conversion ledger omits order/payment refs; admin oversight may still see order ids.

Host “mark paid” records optional `payout_reference` / `payout_note` on the conversion — off-platform settlement evidence for host-owned Ambassadors rewards. Platform host-balance payouts stay on [PAYMENTS.md](./PAYMENTS.md).

## API (phase 10 domain — preferred)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/ambassadors/eligible-events` | Public | Joinable events |
| POST | `/ambassadors/join` | User | Join (`accept_terms` + `campaign_id` or `event_id`) |
| GET | `/ambassadors/me` | User | Profile |
| GET | `/ambassadors/me/campaigns` | User | Participations |
| GET | `/ambassadors/me/links` | User | Share links/codes |
| GET | `/ambassadors/me/earnings` | User | Earnings from `ambassador_conversions` |
| GET | `/ambassadors/campaigns/{id}` | Public | Campaign detail |
| GET | `/events/{slug}/ambassador-status` | Optional | Enabled + joined |
| POST | `/events/{slug}/ambassador/join` | User | Join by slug |
| GET | `/events/{slug}/ambassador/link` | User | Own link |
| POST | `/ambassadors/track-click` | Public | Click + attribution |
| POST | `/ambassadors/track-checkout-started` | Optional | Checkout attribution |
| GET/POST | `/host/ambassadors/campaigns` | Host | Campaign CRUD |
| POST | `/host/ambassadors/campaigns/{id}/pause\|end` | Host | Lifecycle |
| GET | `/host/ambassadors/campaigns/{id}/participants` | Host | Participants |
| POST | `/host/ambassadors/participants/{id}/remove` | Host | Remove |
| GET | `/host/ambassadors/analytics` | Host / team `ambassadors.view` | Stats |
| GET | `/host/ambassadors/payouts` | Host / team | Payouts |
| GET | `/host/ambassadors/conversions` | Host / team `view_conversions` | Conversion ledger (no buyer/order refs) |
| GET | `/host/ambassadors/conversions/export` | Host / team `export` | CSV export |
| GET | `/host/ambassadors/conversions/{id}/audit` | Host / team | Per-conversion reward audit |
| GET | `/host/ambassadors/reward-audit` | Host / team | Workspace reward audit feed |
| POST | `/host/ambassadors/conversions/{id}/reward-status` | Host / team reward perms | Normal host-owned approve / reject / mark paid / reverse |
| POST | `/host/ambassadors/conversions/{id}/flag` | Host / team | Flag suspicious conversion |
| POST | `/host/ambassadors/conversions/{id}/reverse` | Host / team `reverse_rewards` | Reverse |
| GET | `/admin/ambassadors` | Admin | Profiles |
| GET | `/admin/ambassadors/campaigns\|conversions\|payouts` | Admin | Ledgers |
| GET | `/admin/ambassadors/reward-audit` | Admin | Platform reward audit |
| GET | `/admin/ambassadors/fraud-flags` | Admin | Fraud flags |
| POST | `/admin/ambassadors/participants/{id}/block` | Admin | Block |
| POST | `/admin/ambassadors/conversions/{id}/reverse` | Admin | Reverse |

Legacy `/promos/*` Ambassadors routes remain until FE cutover. Full table: [API.md](./API.md).

## API (legacy open program `/promos`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/promos/ambassadors/eligible-events` | Public | Published events with open Ambassadors |
| GET | `/promos/events/{event_id}/ambassadors/program` | Public | `{ enabled, commission_percent, terms_version }` |
| POST | `/promos/events/{event_id}/ambassadors/join` | User | Body `{ accept_terms: true }` — join / reactivate |
| GET | `/promos/events/{event_id}/ambassadors/me` | User | Own enrollment for event (404 if none) |
| POST | `/promos/events/{event_id}/ambassadors/leave` | User | Deactivate own open enrollment |
| GET | `/promos/ambassador/enrollments` | User | All linked ambassador rows (open + curated; no payment refs) |
| GET | `/promos/ambassador/earnings-summary` | User | Estimated / approved / payable / payout status |
| POST | `/users/admin/{user_id}/ambassadors/block` | Admin | Block from Ambassadors |
| POST | `/users/admin/{user_id}/ambassadors/unblock` | Admin | Unblock |
| GET/PATCH | `/promos/admin/settings` | Admin | Global Ambassadors enable/disable |
| GET/POST | `/promos/admin/campaigns` | Admin | List all / create platform campaign |
| POST | `/promos/admin/campaigns/{id}/pause\|resume` | Admin | Pause/resume any campaign |
| GET | `/promos/admin/ambassadors` | Admin | Search enrollments |
| POST | `/promos/admin/ambassadors/{id}/block\|unblock` | Admin | Block linked user |
| GET | `/promos/admin/conversions` | Admin | Conversion ledger |
| POST | `/promos/admin/conversions/{id}/reverse` | Admin | Reverse fraudulent sale |
| POST | `/promos/admin/conversions/{id}/reward-status` | Admin | Oversight / fraud / platform campaigns / emergency (not exclusive for host-owned) |
| GET | `/promos/admin/reports/summary` | Admin | Platform totals |

Host-curated CRUD remains under `/promos/ambassadors*`. Event flags are set via Event Studio (`EventUpdate`).

## Frontend (public user flow)

| Route | Role |
|---|---|
| `/ambassadors` | Public landing — hero, how it works, eligible events, earnings explainer, FAQ, CTA |
| `/ambassadors/events` | Browse ambassador-eligible events → **Promote this event** |
| `/ambassadors/how-it-works` | Step-by-step explainer |
| `/dashboard/ambassador` | Auth overview (clicks, sales, earnings snapshot) |
| `/dashboard/ambassador/events` | Active campaigns |
| `/dashboard/ambassador/links` | Referral links, promo codes, QR cards |
| `/dashboard/ambassador/earnings` | Estimated / approved / payable + confirmed sales |
| `/dashboard/ambassador/leaderboard` | Personal campaign ranking |
| `/dashboard/ambassador/payouts` | Payout & reward status |
| Event public `#promote-ambassadors` | **Promote this event** card (commission summary) → modal (join / copy link/code) |
| `/host/ambassadors/campaigns*` | Campaign create, commission settings, participants, leaderboard, payout summary |
| `/host/ambassadors*` | Host-curated partners + open joiners |
| `/admin/ambassadors*` | Campaigns, conversions, fraud flags, payout status, reports |
| Event Studio → Policies | Enable open Ambassadors + commission % |

Legacy `/ambassador` and `/ambassador/earnings` redirect into `/dashboard/ambassador*`.

## Lifecycle

See [CRUD_MATRIX.md](./CRUD_MATRIX.md) (Ambassadors / Open Event Ambassadors rows). Prefer deactivate over hard delete; hard delete only with no sales/clicks (host path).

## Local demo data

DJ Maze · **Afrobeats Night Live** · campaign **Afrobeats Night Ambassador Drive** with participants Tolu / Amaka / Chidi (`TOLUAFRO` · `AMAKA20` · `CHIDILIVE`), clicks, pending checkouts, verified ticket/merch conversions, and pending / payable / reversed commission samples. Seed: `app/demo/ambassadors_seed.py`. Shortcuts on `/demo`. Details: [DEMO_DATA.md](./DEMO_DATA.md#open-event-ambassadors-demo).

## Tests (phase 17)

| Area | Location |
| --- | --- |
| Checklist (join auth, pause, merch conversion, payout math, remove/block) | `backend/tests/test_ambassador_phase17.py` |
| Open join / attribution / self-referral | `tests/test_open_ambassadors.py` |
| Campaigns / host remove | `tests/test_ambassador_campaigns.py` |
| Payment / duplicate webhook / refund | `tests/test_ambassador_payment_integration.py` |
| Fraud | `tests/test_ambassador_fraud.py` |
| Privacy (no buyer PII) | `tests/test_ambassador_privacy.py` |
| Domain API v2 | `tests/test_ambassadors_api_v2.py` |
| Frontend smoke | `npm run test:ambassadors` → `frontend/scripts/ambassadors-smoke.mjs` |

Run backend: `pytest tests/test_ambassador*.py tests/test_open_ambassadors.py tests/test_demo_open_ambassadors_seed.py` (plus payments / tickets / merch / privacy suites as needed).

## Distinctions

- **Host team** — workspace permissions; not Ambassadors. See [TEAMS.md](./TEAMS.md).
- **Event staff / scanners** — desk check-in; not Ambassadors.
- **Ticket `promo_codes`** — buyer discounts; not referral commission. See [PROMO_CODES.md](./PROMO_CODES.md).
- **Merch discount codes** — merch-only discounts; separate tables. See [MERCHANDISE.md](./MERCHANDISE.md).

## Related docs (phase 18)

| Doc | Ambassadors coverage |
|---|---|
| [PROMO_CODES.md](./PROMO_CODES.md) | Ticket discounts vs referral codes |
| [TICKETS.md](./TICKETS.md#ambassadors-ticket-attribution) | Ticket issue vs attribution |
| [MERCH.md](./MERCH.md#ambassadors-merch-attribution) · [MERCHANDISE.md](./MERCHANDISE.md) | Merch campaign attribution |
| [PAYMENTS.md](./PAYMENTS.md) | Webhook finalize + refund reverse |
| [EMAILS.md](./EMAILS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md) | Templates + channel matrix |
| [API.md](./API.md#ambassadors-domain-api-phase-10) · [DATABASE.md](./DATABASE.md#promos--ambassadors-phase-8--open-event-ambassadors) | Routes + schema |
| [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) | Public / dashboard / host / admin routes |
| [SECURITY.md](./SECURITY.md#ambassadors-fraud-controls) · [PRIVACY.md](./PRIVACY.md#ambassadors) | Fraud + privacy |
| [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md) | Verification status |
