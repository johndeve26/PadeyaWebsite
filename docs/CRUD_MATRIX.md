# Pàdéyá CRUD / lifecycle matrix

Brand: **Pàdéyá** · API prefix: `/api/v1`

This matrix is the inventory audit of every listed platform resource.  
Pattern guide: [`CRUD_PATTERN.md`](./CRUD_PATTERN.md).

**Lifecycle is never optional.** Every product module — current and future — must have a complete lifecycle plan in this matrix, even when records are intentionally read-only or append-only for security/finance reasons. “No delete” and “append-only” are valid plans only when documented and enforced.

**CRUD does not always mean physical delete.** Prefer status transitions (pause, cancel, archive, disable, moderate) for commerce, trust, and audit data.

**Hard delete forbidden:** payments, webhook events, ledger, refunds, payouts, payout evidence, audit logs, issued tickets with commerce history, order fee snapshots.

## Canonical lifecycle rules (product)

1. **Events** — Hosts create/edit (draft/pending/published with restrictions); postpone dates on published/paused without re-review; delete draft only; archive completed/cancelled; never hard-delete with orders/tickets/payments; sales → cancel not delete. Published/paused events auto-complete when `end_datetime` passes (lazy on host/admin list + get-by-id); hosts may also mark completed early. Admin approve/reject/pause/restore; admin may archive, not hard-delete paid events.
2. **Ticket types** — Create/update before sales; deactivate after sales; hard delete only with no order/ticket refs; never corrupt existing orders.
3. **Tickets** — No hard delete after issuance; statuses active/transferred/cancelled/refunded/expired/checked_in; cancel by permission; QR revoke/regenerate; transfer history retained.
4. **Orders/payments** — No hard delete; archive failed/abandoned in UI only; webhook events immutable; status changes audited (gateway/webhook or admin correction).
5. **Ledger** — Append-only; corrections via reversal entries.
6. **Refunds/payouts** — Request create/review/approve/reject/cancel; paid payouts + evidence immutable; **super_admin only** mark paid; finance reviews but cannot mark paid.
7. **Reviews** — Buyer update/withdraw; hosts reply/report only; admin hide/restore with reason (audited); no host hard delete.
8. **Vault** — Host create/edit/archive; delete draft/unpurchased only; purchased → archive; admin moderate.
9. **Promos** — Create/update/disable; hard delete unused only.
10. **Ambassadors** — Host-curated create/update/deactivate; open Event Ambassadors self-join/leave (soft deactivate); hard delete only with no sales/clicks.
11. **CRM announcements** — Update drafts; cancel drafts; archive sent; recipients retained.
12. **Sponsorships** — Edit/archive slots; close/archive inquiries (no host hard delete); placements retained; admin moderate.
13. **Support** — Users create cases; staff reply/assign/escalate/resolve/close; notes append-only; archive not hard delete.
14. **Analytics** — Append-only; no user-facing delete.
15. **AI** — Admin create/update/deactivate templates; usage logs read-only.

| Status | Meaning |
|---|---|
| `complete` | Lifecycle plan implemented: create/read + update-or-lifecycle + correct end-of-life; FE where humans operate it |
| `partial` | Plan known but ops incomplete (nested-only, seed-only, FE gap, or missing restore/audit) — still must have a plan row |
| `missing` | No model/API **and** no approved lifecycle plan yet — treat as blocker before shipping the module |
| `planned-readonly` | Lifecycle plan is intentional: read-only, append-only, or immutable (document Create/Update/Delete columns as *system / never / reverse-only* with why) |

Do **not** use status to skip planning. Append-only modules (ledger, audit logs, analytics events) use `planned-readonly` or `complete` once create+read+immutability guards and tests exist — never “CRUD optional.”

---

## Core / Auth

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Users | `users` | Register | Self me + admin list/detail | `PATCH /users/me`; admin account-status / under-review / suspend / ban / selective restrictions | Soft status (`account_status`); hard delete **blocked** (`405`) | No | `/register`, `/login`, `/admin/users*` | `POST .../status`, `.../restrictions*`, `.../suspend\|unsuspend`, `DELETE .../admin/{id}` → 405; Activity drill-down `GET .../activity/{kind}` | **complete** | Role assign still seed/ops; Activity detail audited + finance-gated |
| User account status | `users.account_status` (+ JSON mirror) | Admin transition | Admin detail/list + `UserPublic` | Status change (reason required); `restricted` derived from active rows | Soft only; writable incl. restricted/banned | N/A | `/admin/users/[userId]` | `POST /admin/users/{id}/status` | **complete** | Audited `admin_user_status_changed`; migration `20260720_0095` |
| User restrictions | `user_restrictions` | Admin apply (keys / presets) | Admin Restrictions tab + keys on `/me` | Extend `ends_at`; revoke soft | Soft only (`active` → `expired` / `revoked`); **never** hard-delete | **Never** | `/admin/users/[userId]` Restrictions | `GET/POST/PATCH .../restrictions`, `POST .../revoke` | **complete** | Enforcement `assert_no_restriction`; audits `admin_user_restriction_*`; migration `20260720_0096` |
| Account suspensions | `account_suspensions` | Admin suspend / full-suspension preset | `/me` + `/me/suspension` (public fields) | Soft lift on unsuspend | Soft only (`active` → `lifted`) | **Never** | `/account/suspended` | Created via status / full-suspension preset | **complete** | Notify in-app/email/push; no internal notes; migration `20260720_0097` |
| Suspension appeals | `account_appeals` | Suspended user `POST /appeals` | Admin `/admin/appeals`; user pending on suspended page | Approve → unsuspend; reject + optional reply | Soft status (`pending` → `approved`/`rejected`) | **Never** | `/admin/appeals`, `/account/suspended` | `GET/POST /admin/appeals*`, `POST /appeals` | **complete** | Perm `admin.appeals.review`; audits `account_appeal_*` |
| User admin notes | `user_admin_notes` | Admin append (`note_type` catalog + body) | Admin list + nested in detail | — | Append-only (no edit/delete API); `updated_at` null until edit exists | **Never** | `/admin/users/[userId]` | `POST/GET /users/admin/{id}/notes` | **complete** | Admin-only; audited `admin_user_note_created` (no body in audit); secret content rejected; migration `20260720_0094` |
| User admin flags | `user_admin_flags` | Admin add flag (`flag_type` catalog + severity) | Admin list + nested in detail | Resolve/dismiss (soft close) | Soft close only (`active` → `resolved` \| `dismissed`); no hard delete | **Never** | `/admin/users/[userId]` | `POST/GET .../flags`, `POST .../flags/{id}/resolve\|dismiss` | **complete** | Audited `admin_user_flag_created` / `admin_user_flag_updated`; migration `20260720_0093` |
| User under review | `users.under_review_*` | Admin mark | Admin detail | Admin clear | Soft hold cleared on clear | N/A | `/admin/users/[userId]` | `POST .../under-review`, `.../clear-under-review` | **complete** | Distinct from suspend (`is_active`) |
| Roles | `roles` | Seed | Probe checks | Seed | — | No | — | `users/seed.py`; `GET /users/admin-check` | complete (ops) | No runtime role admin API |
| Permissions | `permissions`, `role_permissions` | Seed | Probe | Seed | — | No | — | seed; `GET /users/permission-check` | complete (ops) | Catalog = code + reseed |
| User roles | `user_roles` | Implicit (register/onboard/staff) | Nested in me | — | No revoke API | CASCADE only | — | onboard / staff assign | partial | No admin assign/revoke |
| Refresh tokens | `refresh_tokens` | Login/register | — | Rotate refresh | Logout revoke; admin revoke-all | Soft `revoked_at` | `api.ts` auth; `/admin/users/[userId]` | `POST /auth/login`, `/refresh`, `/logout`; `POST /users/admin/{id}/sessions/revoke-all` | **complete** | Never returns token values |
| Audit logs | `audit_logs` (`core/audit.py`) | System write | Admin list | Immutable | Never | **Never** | `/admin/audit-logs` | `write_audit_log()`; admin-user + impersonation dual-write | **complete** (planned-readonly) | Scrubbed; no export UI |
| Admin impersonation sessions | `admin_impersonation_sessions` | Admin start | Admin history + `/me/impersonation` | End / expire / revoke | Soft status lifecycle | **Never** | `/admin/users/[userId]` | `POST .../impersonation/start\|end` | **complete** | Target never notified |
| Admin impersonation audit | `admin_impersonation_audit_logs` | System on start/end/expire/block/request | Admin (via history / audit) | — | Append-only | **Never** | Banner + history | `record_impersonation_audit()` | **complete** | 11B field matrix; no bodies/secrets |


---

## Hosts

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Host profiles | `hosts`, `host_profiles` | Onboard | Self; Legacy public | PATCH me | Suspend (none) | Soft `hosts.status` | `/host/onboarding`, `/host/*` | `POST /hosts/onboard`, `GET/PATCH /hosts/me` | partial | No admin suspend/list |
| Host verification | `host_verifications` | Auto pending on onboard | Admin list (+ host name / owner) | Approve/reject | — | Status fields | `/admin/hosts` | `GET /hosts/admin/verifications`, `POST .../approve\|reject` | **complete** | FE shows `host_display_name`; host actions menu |
| Host team members | `host_team_members` | Accept invite → member | Host list | Role/permissions/scope PATCH | Suspend / remove (`removed_at`); restore | Hard delete blocked | `/host/team`, `/host/team/[id]` | `/host/team`, `/host/team/members/*` (+ legacy `/hosts/.../team*`) | **complete** | `scope_json`; see [HOST_TEAM.md](./HOST_TEAM.md) |
| Host team invites | `host_team_invites` | Host invite | Host list (pending); invitee preview | Role/permissions/scope while pending | Expire / revoke / accept (→ member) | Hard delete blocked | `/host/team`, `/team/invite/[token]` | `/host/team/invites*`, `/team/invites/{token}*` (+ legacy) | **complete** | Token hash; resend rotates token |
| Host team audit | `host_team_audit_logs` | System on team actions | Host / admin team audit | — | Append-only | — | `/host/team` (audit) | `/host/team/audit-log`, `/admin/teams/audit` | **complete** | Mirrored to global `audit_logs` |
| Active workspace | `user_active_workspaces` | User selects workspace | Self | Replace host_id | — | Cascade with user/host | Host layout switcher | `GET /me/team-workspaces`, `POST /me/active-workspace` | **complete** | Client also mirrors to localStorage |
| Host followers | `host_followers` | Follow (manual) **or** system on paid purchase | Me + host lists | Marketing opt-in (manual default off; **buyers default on**) | Unfollow | Hard unfollow today | `/dashboard/following`, `/host/followers` | `/crm/follow*` | complete | Paid buyers auto-follow + notify on (`crm.buyer_follow`); optional soft unfollow history |
| Host recommendations (fan) | `host_recommendation_dismissals`, `host_recommendation_feedback`, `host_recommendation_impressions`, `host_recommendation_category_hides` | System scores | GET `/hosts/recommendations` | Dismiss / not-interested / more-like / hide category (append feedback) | Hide via dismiss + category hide TTL | N/A (feedback/impressions append-only) | `/dashboard`, `/hosts` rail + sort | `/hosts/recommendations*`, admin debug | **complete** (rules + integration) | No LLM ranking; safe reasons only |
| Event recommendations (fan) | `event_recommendation_*` dismissals, feedback, impressions, category/host hides | System scores | GET `/events/recommendations` | POST feedback (dismiss, not_interested, hide_*, more_like, etc.) | Hide via dismiss + category/host hide TTL | N/A (append-only) | `/dashboard`, `/events` rail + sort | `/events/recommendations*`, admin debug | **complete** (rules + integration) | No LLM ranking; safe reasons only |
| Host bank accounts | `host_bank_accounts` | Host | Host (last4 only) | PATCH | Archive/restore | Hard delete blocked | `/host/payouts` | `/hosts/me/bank-accounts*` | **complete** (API) | Payout still uses snapshot; no FE bank CRUD |

---

## Events

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Events | `events` | Host draft | Public/host/admin | PATCH (+ re-review, optional `slug`); postpone dates (no re-review) | pause/resume/postpone/cancel/complete; **auto-complete** when end passes; discard draft; admin **flag/clear-flag** (soft ops marker) | Draft/rejected only, no sales | **10-step Event Studio** (`/host/events/new`, `/edit?step=`), `/host/events` (Completed tab), admin review + `/admin/events/[id]/review` | `/events/*` lifecycle; `auto_complete_due_events`; `POST .../flag`, `.../clear-flag` | **complete** | Flag does not unpublish |
| Event categories | `event_categories` | Seed + admin | `GET /events/categories` | Admin PATCH | Deactivate/restore | Soft `is_active` | Studio select | `/events/admin/categories*` | **complete** (API) | No admin FE |
| Event venues | `event_venues` | Nested event write | Nested event | Nested upsert | Cascade w/ discard | Cascade | Studio privacy/location | Nested in EventCreate/Update | partial | No standalone venue API; flat fields duplicate |
| Event media | `event_media` | Upload/URL | Nested + list | Gallery URL upsert; banner fields | `DELETE .../media/{id}` | Hard delete row | Studio media + ConfirmAction remove | `/events/.../media*` | **complete** | Gallery sync preserves matching URLs |
| Agenda | `event_agenda_items` | Nested | Nested | Upsert-by-id on event PATCH | Omit → hard delete | Prefer omit/delete (no commerce refs) | `AgendaBuilder` + ConfirmAction | Nested create/update | **complete** | IDs preserved on save |
| People / speakers | `event_people` | Nested | Nested | Upsert-by-id on event PATCH | Omit → hard delete | Prefer omit/delete | `PeopleLineupBuilder` + ConfirmAction | Nested create/update | **complete** | IDs preserved on save |
| Checkout questions | `event_checkout_questions` | Nested | Nested (public active only) | Upsert-by-id; `status` active/archived | Omit answered → **archive**; unused → delete | Soft archive when `order_checkout_answers` exist | Studio Questions step + ConfirmAction | Nested create/update | **complete** | Answers immutable snapshots |
| Checkout answers | `order_checkout_answers` | With order | Buyer/admin on order | — | Immutable snapshot | Never | Checkout form + order receipt | `POST /orders` (`checkout_answers`) | **complete** | Host order answers UI later |
| Publish checklist | — (computed) | — | Host/admin on event | — | N/A | N/A | Studio Publish step | `build_publish_checklist` | **complete** | Not a DB table; `preview_checked` is client/session |
| Ticket types | `ticket_types` | Host | Host + public | PATCH | Deactivate; delete unused | Only if sold/reserved = 0 | Studio Tickets step + `/host/events/[id]/tickets` (`TicketTypeBuilder`) | ticket-type routes | **complete** | — |
| Event merch products | `event_merch_products` | Host (event-linked **or** standalone) | Host; public marketplace + catalog (active + listed + not hidden/removed); admin list | PATCH status/fields; admin moderate/feature | Soft archive (`archived_at`); admin hide/remove/pause | No hard delete after sales | `/merch`, `/host/.../merchandise`, `/admin/merchandise` | `GET /merch`, `GET /merch/{slug}`, `/host/merch*`, `/merch/events/.../products*`, `/merch/admin/products*` | **complete** | Host required; event optional; `marketplace_kind` + categories; Admin: `merch.moderate` |
| Merch categories | `merch_categories` | Admin seed/upsert | Public list | PATCH name/status/sort | Soft archive | Soft | `/admin/merch/categories` | `GET /merch/categories`, `/admin/merch/categories*` | **complete** | Browse taxonomy for marketplace |
| Event merch variants | `event_merch_variants` | Host (nested) | Host; public nested | PATCH stock/status | Soft archive | No hard delete after order refs | Host merch UI | `/merch/products/.../variants*`, `/merch/variants*` | **complete** | — |
| Merch bundles | `merch_bundles` | Host | Host list; public active in sales window | PATCH fields/status | Soft archive (`archived_at` + status) | No hard delete | `/host/events/[id]/bundles` | `/host/events/.../bundles*`, `GET /events/.../bundles`, expand on `POST /orders` | **complete** | Money on `orders`/`order_items` only; tickets+merch issue only after Paystack webhook; pack inventory + component inventories never oversold |
| Merch fulfillments | `merch_fulfillments` | System on paid finalize | Buyer `/merch/mine`; host/staff queue; admin orders (no amounts) | Mark fulfilled / collect_at_stand | Cancel on refund (unfulfilled); no hard delete | Never | `/dashboard/merchandise`, host pickup, `/admin/merchandise/orders` | `/merch/fulfillments*`, `/merch/admin/orders`, webhook finalize | **complete** | Restock only if `restock_on_refund`; snapshots for name/variant |
| Merch fulfillment events | `event_merch_fulfillment_events` | System / staff | Host/admin via fulfillment context | Append-only | Never mutate | Never | (timeline; audit companion) | Written on create/status/refund | **complete** | Append-only |
| Merch product reports | `merch_product_reports` | Buyer | Admin/support | Resolve / dismiss (+ optional moderate) | Close only | Never hard-delete open trail | `/admin/merchandise/reports` | `/merch/products/{id}/report`, `/merch/admin/reports*` | **complete** | Audited |
| Merch product reviews | `merch_reviews` | Verified buyer (paid + fulfillment) | Public published; buyer own; host inbox; admin | Buyer edit; host reply; admin hide/restore | Buyer remove (`removed_by_user`); admin hide | Hosts **cannot** delete (403) | Buyer merch detail; `/host/merchandise/reviews`; `/admin/merchandise/reviews`; public product | `/dashboard/merchandise/reviews*`, `/host/merchandise/reviews*`, `/admin/merchandise/reviews*`, `GET /merch/products/{id}/reviews` | **complete** | One per `order_item_id`; verified purchase badge; public serialize omits order/payment/contact; passport display when public/unlisted |
| Merch discount codes | `merch_discount_codes` | Host | Host list | PATCH fields/status | Pause / expire / soft archive | No hard delete | `/host/merchandise/discounts` | `/host/merchandise/discounts*`, `POST /merch/discounts/validate` | **complete** | Separate from ticket `promo_codes`; `usage_count` increments only after paid webhook; refund reverses |
| Merch discount redemptions | `merch_discount_redemptions` | System on order | System / host via usage | pending → paid / reversed | Reverse on refund | Never | (order breakdown) | Webhook finalize + refund cancel | **complete** | Append lifecycle; unpaid never counts |
| Merch POD integrations | `merch_print_on_demand_integrations` | Host upsert | Host list (no decrypted credentials) | Upsert provider/status/store ref/credentials_enc | Disable (`status=disabled`) | No hard delete | `/host/merchandise/print-on-demand` | `/host/merchandise/print-on-demand/integrations` | **complete** (provider-ready) | Credentials via `encrypt_sensitive`; live Printful/Printify sync is future |
| Merch POD jobs | `merch_pod_jobs` | System after verified Paystack payment only | Host list; admin list | Mark manually fulfilled; retry failed (stub) | Cancel status | Never hard-delete paid trail | Host + admin POD pages | `/host/.../print-on-demand*`, `/admin/.../print-on-demand*` | **complete** (manual now) | Idempotent per `order_item_id`; no parallel payment ledger |
| Merch size charts | `merch_size_charts` | Host | Host list; public active by id; nested on product serialize | PATCH fields/status (`active`/`inactive`) | Soft archive (`archived_at` + status) | No hard delete | `/host/merchandise/size-charts` | `/host/merchandise/size-charts*`, `GET /merch/size-charts/{id}` | **complete** | Reusable via `product.size_chart_id`; inactive/archived omitted from public GET + product attach |
| Merch carts | `merch_carts`, `merch_cart_items` | Buyer add/update lines | Buyer `/dashboard/cart` | Bump `last_activity_at`; revive abandoned on edit | Abandon → recover once → expire; convert only after paid webhook | Soft status only | `/dashboard/cart` | `merch/cart.py`; `POST/GET/DELETE /dashboard/cart*`; `scripts/run_merch_cart_recovery` | **complete** | Never invents paid state; no PII in `merch.cart_reminder`; sold-out / ended-event lines skipped |
| Merch shipping addresses | `merch_shipping_addresses` | Buyer on shipping checkout | Buyer hint (city/state/country); host fulfill decrypted | Never mutate after create | Order lifecycle only | Never | Checkout + host fulfillment queue | `shipping.py`; `POST /orders` + ship/deliver | **complete** | Encrypted PII; never public/analytics; existing order snapshot independent of zones |
| Merch shipping zones | `merch_shipping_zones` | Host | Host list | PATCH fields/status | Soft archive (`status=archived`) | No hard delete | `/host/merchandise/shipping-zones` | `GET/POST/PATCH …/shipping-zones*`, `POST …/archive` | **complete** | Only `active` used for new checkout fees; no buyer address on zone APIs; carrier label APIs **deferred** |
| Merch stock alerts | `merch_stock_alerts` | System on stock transitions | Host inbox | Ack / resolve (host) | Soft close | Never | `/host/merchandise/stock-alerts` | `stock_alerts.py`; host list API | **complete** (host) | Buyer multi-channel stock-alert preferences **deferred** |
| Merch revenue splits | `merch_revenue_splits` | System on paid finalize | Host + admin reports/CSV | Reverse on refund only | Append-only (+ reverse row) | Never | `/host/merchandise/revenue`, `/admin/merchandise/revenue` | `revenue.py`; webhook finalize | **complete** (append-only) | No buyer PII / payment secrets in CSV |
| Merch storefront settings | `host_profiles.merch_storefront_*` | Host onboarding / settings | Public `/u/{username}/merch` when enabled | PATCH storefront fields | Disable / visibility unlisted | Soft | `/host/merchandise` storefront card; `/u/[username]/merch` | `storefront.py`; `GET/PATCH` storefront | **complete** | Not a separate table — columns on `host_profiles` |
| Merch post-event drops | product flags on `event_merch_products` | Host drop create/patch | Host list; buyer eligible list; public when live | PATCH schedule/audience/status | Soft archive product | Soft | `/host/events/[id]/post-event-drops`; buyer dashboard | `post_event_drops.py`; completed-event merch-only checkout | **complete** | Uses product row + `storefront_visibility=post_event_drop` (not a separate drops table) |
| Event memories | `event_memories`, `event_memory_media` | Auto on complete; host/fan photo uploads | Public hub `/memories`, `/events/{slug}/memories`, Legacy alias | Host PATCH recap/external link; photo caption/cover/order; fan own caption | Soft hide photo/album; media DELETE (host); removed status | Prefer soft hide | `/memories`, `/events/[slug]/memories`, host Memories ops, admin photos | `/memories/*` albums + multipart photos; ticket-gated fans | **complete** | Host unpublish album still admin-only; verify phone upload sizes in prod |
| Event templates | `event_templates` | Host | Host | PATCH | Archive/restore | Hard delete blocked | Studio placeholder | `/events/templates*` | **complete** (API) | No Studio FE wiring |

### Event Studio field & lifecycle notes

**Event Studio** (`/host/events/new`, `/host/events/[id]/edit?step=`): `basics` → `location` → `schedule` → `tickets` → `media` → `lineup` → `questions` → `policies` → `seo` → `merchandise` (optional) → `publish`. Merchandise is never required to publish.

| Concern | Create / update | Read (public) | End-of-life |
|---|---|---|---|
| Core + taxonomy | `category_id` + `location_id` dual-write primary category / place labels | Listed discovery only | Discard draft/rejected with **no** ticket sales; else cancel/archive |
| Location privacy | `location_visibility`, reveal rules, private `address`, `public_location_label` | Serializer redacts street/online URL; SEO scrubbed | Host/admin always full; buyer after paid ticket when rules allow |
| Map discovery pins | Location fields already on `events` (lat/lng, area, approximate_*, Places ids) | **Read-only** `GET /events/map` (bounds + filters) → compact privacy-safe pins (`discovery_point`); no street/`formatted_address`/`google_place_id`; hidden/undisclosed → approximate or omit; unlisted never listed | N/A (append-only discovery read) |
| Agenda / people | Nested upsert-by-id on event PATCH | Nested on public detail | Omit → hard delete (no commerce refs) |
| Checkout questions | Nested upsert; `status` active/archived | **Active only** on public/checkout | Omit answered → archive; unused → delete |
| Checkout answers | Created with order | Buyer/admin on order | Immutable snapshots — never delete |
| Media | Upload / `gallery_urls` sync | Nested URLs | `DELETE .../media/{id}` hard-deletes row |
| Ticket types | Separate CRUD | Public types only (codes stripped) | Deactivate always; hard delete only if sold=reserved=0; post-sales structural PATCH blocked |
| Publish checklist | Computed on host/admin serialize | `null` on public | Not a table; `preview_checked` is FE session only |

**Ticket type post-sales protection:** after `quantity_sold` or `quantity_reserved` > 0, PATCH cannot change price/type/name/quantity/seats/min/max — deactivate to stop sales.

**Public privacy invariant:** public list/detail never leak hidden street addresses or private online URLs (see [SECURITY.md](./SECURITY.md), [API.md](./API.md) Event Studio).

---

## Ticketing

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Orders | `orders` | Checkout (buyer or guest; purchase_mode; gift flags; guest_* + claim tokens) | Buyer/admin; guest via claim | Webhook status | Cancel unpaid **missing** | Never | `/dashboard/orders`, checkout, `/checkout/claim` | `POST /orders` (optional auth), payments | partial | Guest merch requires login; no cancel-pending |
| Order attendees | `order_attendees` | With order | Nested on order | — | Cascade with order | Soft via order | Checkout attendee step | `persist_order_attendees` | **complete** (by design) | Never claim `recipient_user_id` by email alone |
| Order items | `order_items` | With order (`ticket` \| `merch`) | Nested | — | Cascade | N/A | Order detail | Nested polymorphic | **complete** (by design) | Immutable post-create; merch never issues tickets |
| Tickets | `tickets` | Webhook only (holder from attendees; guest `buyer_user_id` nullable until claim) | Buyer/admin; host search | Transfer/QR/check-in; claim | Cancel status (password required) | Never | `/dashboard/tickets`; `/checkout/claim` | `/tickets/*`, claim endpoints | **complete** | Claim hashed token + expire; never QR pre-confirm |
| Ticket QR tokens | `ticket_qr_tokens` | Internal | Nested ticket | Rotate/revoke internal | Soft revoke | Soft | Ticket pass UI | `tickets/qr.py` | partial | No admin force-revoke API |
| Ticket transfers | `ticket_transfers` | Buyer | Buyer/host/admin | — | Immediate complete | No | `/dashboard/tickets/[id]/transfer` | `/tickets/.../transfer` | partial | No accept/decline flow |
| Group tickets | `ticket_groups`, `ticket_group_members` | Issuance (group/table) | Schema only | — | Status unused via API | Soft intended | Type config only | Created in issue path | partial | No list/manage group API/UI |
| Table reservations | `table_reservations` | Host / auto on purchase | Host | Assign | Cancel | Soft status | `/host/events/[id]/tables` | `/tickets/events/.../tables`, `POST .../tables/{id}/cancel` | **complete** (API) | — |
| Offline scan batches | `offline_scan_batches`, `offline_scan_items` | Sync | Service list unwired | — | Append-only statuses | Soft sync status | Offline check-in page | `POST /checkins/offline/sync` | partial | No GET history for hosts |

---

## Payments / Finance

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Payments | `payments` | Checkout / webhook | Admin list | Webhook status only | Never | **Never** | Checkout; `/admin/payments` | `/payments/*` | **complete** (planned-readonly) | Buyer via orders only; no hard delete |
| Payment webhook events | `payment_webhook_events` | Webhook ingest (system) | Ops read **missing** | Processing status only | Never | **Never** | — | Paystack webhook processor | **planned-readonly** (partial ops) | Immutable ingest; add admin read/replay later |
| Refunds | `refunds` | On approve request | Indirect | Status | Never | **Never** | Via refund request UIs | Side-effect of review | partial | No dedicated refund list |
| Refund requests | `refund_requests` | Buyer | Buyer/support/finance | Escalate/review | Close via decision | Never | `/dashboard/refunds`, `/support/refunds`, `/admin/refunds` | `/finance/refunds*` | **complete** | Buyer cancel open request |
| Host balances | `host_balances` | System | Host | System ledger | Never | N/A | `/host/payouts`, `/host/earnings` | `GET /finance/host/balance`, `GET /finance/host/earnings` | **complete** | Earnings report = gross after discounts − host fees − ambassadors − refunds; buyer fees excluded from gross |
| Ledger entries | `ledger_entries` | System (append-only) | Host/admin | Immutable; corrections via reversal entries | Never | **Never** | Host; `/admin/ledger` | `/finance/.../ledger` | **complete** (planned-readonly) | Support blocked (by design) |
| Platform ledger entries | `platform_ledger_entries` | System on paid webhook / refund / payout | Finance admin | **Immutable**; corrections via `adjustment` | Never | **Never** | `/admin/finance/platform-revenue` | `append_platform_ledger_entry`; `/finance/admin/platform-revenue*` | **complete** (planned-readonly) | Unique `dedupe_key`; masked payment refs; no raw Paystack payloads |
| Payout requests | `payout_requests` | Host | Host/admin | Review / mark-paid | Reject/close | **Never** | `/host/payouts`, `/admin/payouts` | `/finance/.../payouts` | **complete** | Support ≠ finance |
| Payout evidence | `payout_evidence` | With mark-paid (system) | Nested payout | Immutable | Never | **Never** | `/admin/payouts` | Required for mark-paid | **complete** (planned-readonly) | URL only; no dedicated upload |
| Platform fee settings | `platform_fee_settings` | Finance admin | Finance admin | PATCH current/future rows; version via `effective_from`/`effective_to` | Disable (`enabled=false`) / end via `effective_to` | No hard delete once referenced by snapshots | `/admin/finance/fees*` | `FeeSettingsService`; `/finance/admin/fees/settings*` | **complete** | Wired into checkout via `calculate_checkout_fees`; buyer service fee default payer=buyer; host commission payer=host |
| Host fee overrides | `host_fee_overrides` | Finance admin | Finance admin | PATCH; host override beats global when enabled + in window | Disable / end via `effective_to` | No hard delete once referenced | `/admin/finance/host-overrides`, `/admin/hosts/[hostId]/fees` | `HostFeeOverrideService`; `/finance/admin/fees/overrides*` | **complete** | Audited; support cannot manage |
| Order fee snapshots | `order_fee_snapshots` | System at order create (before Paystack) | Finance/system; buyer sees buyer lines only | **Immutable** | Never | **Never** | Checkout order summary (buyer lines) | `create_order` + `FeeCalculationService.create_order_fee_snapshot` | **complete** (planned-readonly) | Integer minor units; Paystack amount = `order.total_amount` including buyer fees |

---

## Check-in

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Scanner sessions | `scanner_sessions` | Start | — | End | Soft end | Soft status | Check-in workspace | `POST /checkins/sessions`, `.../end` | partial | No session history list |
| Check-ins | `checkins` | Scan | Host/staff list + stats | — | Immutable | Never | Check-in, attendees | `/checkins/scan`, list/stats | **complete** | No undo (by design) |
| Manual overrides | Same `checkins` (`method=override`) | Override | In check-in list | — | Immutable | Never | **FE action missing** | `POST /checkins/override` | partial | Backend OK; no FE client |
| Staff assignments | `event_staff_assignments` | Host assign / team scope sync | List | Optional type/perms/status | Unassign / expire | Hard remove row | `/host/events/[id]/attendees` | staff routes | **complete** | Optional `team_member_id`, `assignment_type` |

---

## Legacy / Reviews

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Legacy page settings | `host_legacy_pages` + profile | Auto on first open | Public/me/studio | PATCH `/host/legacy` | Host status | Soft | `/u/[username]`, `/host/legacy*` | `/host/legacy`, `/u/.../legacy` | **ok** | Phase 2: richer FAQ/gallery editors |
| Legacy content blocks | `host_legacy_content_blocks` | Defaults + POST | Host; public visible only | PATCH/toggle/reorder | Archive core / delete optional | Soft archive | `/host/legacy/content` | `/host/legacy/content-blocks*` | **ok** | Vault Preview: title/desc, auto/manual source, layout, `config.vault_item_ids`; gallery/video/FAQ content UI |
| Legacy featured items | `host_legacy_featured_items` | Host upsert | Host + public placement | Upsert / clear placement | Clear placement | Soft clear | `/host/legacy/content` | `/host/legacy/featured-items*` | **ok** | Media/sponsor pickers |
| Host social links | `host_social_links` | Host replace | Public visible | Replace via PATCH | Soft replace | Soft | `/host/legacy/edit` | `/host/legacy` | **ok** | — |
| Host contact settings | `host_contact_settings` | Auto | Public-safe fields | PATCH contact | Preference `none` | Soft | `/host/legacy/edit` | `/host/legacy` | **ok** | Form inbox later |
| Legacy tiers | `legacy_tiers` | Seed | Admin | Admin PATCH | `is_active` | Soft | `/admin/legacy/tiers` | `/legacy/admin/tiers*` | partial | No admin create tier |
| Legacy score history | `host_legacy_scores`, `host_legacy_score_history` | Recalc | Admin history; host tier progress | Immutable history | Never | Never | Admin legacy; host tier | `/legacy/admin/hosts/.../history` | partial | Host cannot read own history |
| Verified reviews | `verified_reviews` | Eligible buyer | Me/host/Legacy (visible only) | Buyer PATCH (edit; withdrawn → restore); host reply; admin hide/restore | Buyer soft withdraw (`DELETE`); admin hide | Soft only — hosts **cannot** delete (403) | `/dashboard/reviews`; `/host/reviews`; `/admin/reviews` | `POST/PATCH/DELETE /reviews*`, host reply/report, admin moderate | **complete** | Hidden reviews buyer-locked (admin restore); replies/reports still soft-only |
| Review replies | `review_replies` | Host upsert | Nested | Overwrite | None | No | Host reviews | `POST /reviews/{id}/reply` | partial | No delete/hide reply |
| Review reports | `review_reports` | Auth user | Admin reported | Resolve via moderate | Soft resolve | Soft | Host report; admin triage | report + moderate | partial | No reporter inbox |

---

## Vault

**Definition:** exclusive host content fans unlock through following, buying tickets, attending events, VIP access, invite, or one-time purchase. Canonical rules: [VAULT.md](./VAULT.md).

**Host create flow:** Content → Media → Access → Related → Preview & Publish (`/host/vault/new`).

**Item types:** `text_post`, `image_gallery`, `video`, `audio`, `file_download`, `early_access`, `discount_drop`, `ticket_holder_recap`, `vip_content`, `external_link`, `announcement`.

**Access types:** `free`, `followers_only`, `ticket_holder_only`, `checked_in_attendee_only`, `vip_ticket_holder_only`, `one_time_unlock`, `invite_only`, `admin_hidden`.

**Public read invariant:** locked responses omit `body` / private media; Legacy `vault_preview` and event/memory related teasers use the same redaction. Paid unlocks require verified webhook → grant + `vault_sale` (never tickets).

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Vault items | `vault_items` | Host studio | Public teasers / owner full / buyer when unlocked / admin | Host PATCH (own only); publish/unpublish/schedule; admin moderate | draft → published/scheduled → expired/archived/hidden_by_admin; restore archived/expired → draft; hard delete **draft only** if no unlock history | Soft + conditional hard | `/host/vault*`, `/admin/vault`, public `/u/.../vault*` | `/vault/host/items*` lifecycle; `/vault/admin/items` | **complete** | Support lacks `vault.moderate` by default |
| Vault media | `vault_media` | Nested replace | Preview public / private owner+unlocked | Replace-all on PATCH | Soft with item | Soft | Vault creator / editor | Nested in item payload | **ok** | Per-media endpoints later |
| Vault access rules | `vault_access_rules` | With item | Public metadata (no raw invite code) | Upsert on PATCH | Soft with item | Soft | Access step / AccessRuleEditor | Nested `access` + `access.py` | **ok** | Invite deep-link token deferred; one rule per item |
| Vault purchases | `vault_purchases` | Unlock + webhook | Buyer purchases | Payment status only | Never | Never | `/dashboard/vault` | `/vault/unlock`, `/me/purchases*` | **ok** | Idempotent grant + ledger; pending reuse |
| Vault access grants | `vault_access_grants` | Finalize unlock / invite / grant | Entitlement check | Immutable | Never | Never | — | Internal | **ok** | `UNIQUE(item,user)` |
| Vault unlock attempts | `vault_unlock_attempts` | Checkout start | Host/admin audit | Append-only | Never | Never | — | Internal | **ok** | No entitlement |
| Vault subscriptions | `vault_subscriptions` | Buyer | Buyer + host | — | Cancel/archive/restore | Hard delete blocked | `/host/vault/subscriptions` | `/vault/subscriptions*` | **complete** (API) | Does not unlock content; no paid billing webhook |
| Vault views | `vault_views` | Internal on public fetch | Aggregates in earnings | Append-only | Never | Soft N/A | Counts only | Internal | partial | No drill-down API |

---

## CRM / Promos

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Host followers | (see Hosts) | — | — | — | — | — | — | — | complete | — |
| Audience segments | `audience_segments` | Host custom | Host | — | Delete custom (not system) | Custom hard OK | `/host/audience` (filters + segment C/D) | `/crm/host/segments*` | partial | No PATCH filters; members are derived (not host-CRUD); superfans empty |
| Announcements | `host_announcements` | Host | Host | — | Cancel draft/scheduled; dispatch | Soft cancel | `/host/announcements*` | `/crm/host/announcements*` | partial | No edit-after-create |
| Announcement recipients | `announcement_recipients` | With announcement | Nested detail | Dispatch statuses | Soft statuses | Soft | Nested UI | Nested | partial | No retry-failed |
| Promo codes | `promo_codes` | Host | Host | PATCH | Deactivate status | Soft | `/host/promos` | `/promos/codes*` | partial | Near-complete |
| Ambassadors (host-curated) | `ambassadors` (`program_kind=host_curated`) | Host | Host / ambassador me | PATCH status/rate | Soft deactivate; hard delete if no sales/clicks | Soft preferred | `/host/ambassadors*`, `/ambassador` | `/promos/ambassadors*` | partial | Payouts later |
| Open Event Ambassadors | `ambassadors` (`program_kind=open_event`, `event_id`, `campaign_id`) | Active user + accept terms + live `public_open` campaign + not blocked | Owner me + host leaderboard (phase 13 allowlist only — no buyer PII / order refs / QRs / venue / shipping / Fan Connect / host team) | Leave → inactive; host remove → `removed` | Soft leave/remove; hard delete if unused | Soft preferred | Event **Promote this event**, `/dashboard/ambassador` | `/promos/events/{id}/ambassadors/*`, enrollments | partial | Never grants host team/staff; privacy `app/ambassadors/privacy.py` |
| Ambassador campaigns | `ambassador_campaigns` | Host or admin (`source=platform`); type `event_tickets` \| `event_merch` (v1) / `event\|merch\|host\|platform` (domain); commission + visibility + cookie window | Host own / admin all | PATCH + pause/resume/end; admin pause | End / archive (soft); no hard delete | Soft preferred | `/host/ambassadors/campaigns*`, `/admin/ambassadors/campaigns` | `/promos/campaigns*`, `/promos/admin/campaigns*` | partial | One open campaign per `(event, type)` v1; domain cutover later |
| Ambassador profiles | `ambassador_profiles` | System on first join / terms accept | Owner + admin | Status suspend/block; terms | Soft suspend/block; no hard delete | Soft preferred | `/dashboard/ambassador*` | domain services TBD | schema | One row per `user_id` |
| Ambassador participants | `ambassador_participants` | Join / invite into campaign | Owner + host + admin | Pause/remove/block | Soft remove/block | Soft preferred | dashboards | domain services TBD | schema | Unique `(campaign, profile)` + `(campaign, code)` |
| Ambassador clicks | `ambassador_clicks` | Public/system on referral land | Aggregates (no raw PII) | — | Append-only | Never | — | domain services TBD | schema | Hashed ip/ua/fingerprint only |
| Ambassador attributions | `ambassador_attributions` | System on link/code/qr | System + ops aggregates | — | Expire via `expires_at`; no hard delete | Append / expire | — | domain services TBD | schema | Cookie window from campaign |
| Ambassador conversions (domain) | `ambassador_conversions` | System after verified payment webhook only | Host/admin/ambassador aggregates | Status transitions; reverse on refund/fraud | Reverse / reject only; no hard delete | Reverse-only | admin conversions + earnings | `finalize_ambassador_conversions` + finance refund | yes | Unique `dedupe_key`; never FE success page |
| Ambassador payouts | `ambassador_payouts` | Admin / system when payable | Owner + admin | Approve/pay/cancel | Cancel (soft); no hard delete after paid | Soft cancel | `/admin/ambassadors/payouts`, `/dashboard/ambassador/payouts` | domain services TBD | schema | Evidence rules later |
| Ambassador audit logs | `ambassador_audit_logs` | System on domain actions | Admin | — | Append-only | Never | admin | domain services TBD | schema | Separate from global `audit_logs` |
| Ambassador sales (commission) | `ambassador_sales` | System only after paid webhook | Host/admin/ambassador aggregates | Admin reward status after hold; reverse on refund/fraud | Reverse (immutable reason); no hard delete | Reverse-only | dashboards + `/admin/ambassadors/conversions` | finalize + finance refund hook | yes | **v1** until cutover to `ambassador_conversions` |
| Ambassador platform settings | `ambassador_platform_settings` | Seed row | Admin | PATCH enabled | N/A (singleton) | Never | `/admin/ambassadors` | `/promos/admin/settings` | partial | Global kill switch |
| Ambassador program block | `users.ambassadors_blocked` | Admin | Admin | Admin block/unblock | Unblock restores eligibility | N/A | `/admin/ambassadors` | `/promos/admin/ambassadors/*/block`, `/users/admin/{id}/ambassadors/block\|unblock` | partial | Separate from account deactivate |
| Event open-ambassador flags | `events.open_ambassadors_*` | Host studio / campaign sync | Public when listing event | Host PATCH enable + commission % | Disable blocks new joins (existing stay active) | N/A (event fields) | Event Studio Policies | Event create/update + public serialize | partial | — |
| Ambassador sales | `ambassador_sales` | Payment attribution (no self-referral) | Nested + admin conversions | Reward status; reverse → `reversed` | Never hard; reverse-only for fraud | Soft / reverse | `/admin/ambassadors/conversions`, payouts | `/promos/admin/conversions*` | partial | Paid reverse blocked; full payout rails later |
| Promo clicks | `promo_clicks` | Public click | Aggregates | — | Append-only | Never | Event/checkout track | `POST /promos/referrals/click` | partial | **v1**; domain uses `ambassador_clicks` |
| Promo redemptions | `promo_redemptions` | Checkout/payment | Aggregates | pending→redeemed/released | Soft | Soft | — | Internal | partial | No host redemption ledger |

---

## Fan Passport

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Passports | `fan_passports` | Ensure on read (system) | Me + public/unlisted by username; directory opt-in list | Profile/privacy PATCH (owner); admin hide/restore | Soft via visibility=private or admin hide | Never hard-delete | `/dashboard/passport`, `/fans`, `/f/[username]`, `/admin/fans` | `GET /fans`, `GET/PATCH …/settings`, `GET /f/{username}`, admin hide/restore | partial | Directory = public ∧ appear_in_directory; private → 404 |
| Badges (catalog) | `fan_badges` | Seed | Via me/badges | Seed `is_active` | Soft | Soft | `/dashboard/badges` | seed + read | partial | No admin badge CRUD |
| User badges | `user_badges` | Auto-award (incl. merch after paid webhook) | Me badges; public when `show_badges` | — | Merch: revoke on refund re-eval when criteria fail | Soft intended for non-merch | Badges page | Award on passport load + merch webhook; revoke via `badges_hook` | partial | Meta: criteria_key/source only — never spend/orders |
| Loyalty records | `loyalty_records` | Upsert on passport (system) | Nested me | System only | Never | Never | Nested passport | Nested | **planned-readonly** (partial) | Hosts cannot see loyalty (by design) |

---

## Fan Connect

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Connect settings | `fan_connect_settings` | Ensure on register + read | Owner | Owner PATCH | Soft via disable flags | Never | `/connect/settings` | `GET/PATCH /fan-connect/settings` | **shipped** | Defaults on; fans can untick; `request_policy` |
| Connection requests | `fan_connections` (`request_sent`) | Authenticated fan when eligible | Parties | Accept/decline/cancel | Soft statuses + 14d decline cooldown | Soft | `/connect/requests` | `/fan-connect/requests*` | **shipped** | Safe `reasons_json` only |
| Connections | `fan_connections` (`connected`) | Via accept | Parties | Remove/block/report | Soft `removed`/`blocked` | Soft | `/connect/connections` | accept → `fan_fan` thread | **shipped** | Messaging only while `connected` |
| Blocks | `fan_connection_blocks` | Blocker | Parties + admin | — | Soft (row kept) | Soft | `/admin/fan-connect/blocks` + user history | `/fan-connect/block` + admin list | **shipped** | Display names only |
| Reports | `fan_connection_reports` | Reporter (`POST /report`) | Admin | Resolve/dismiss | Soft statuses | Soft | `/admin/fan-connect/reports` + user history | `/fan-connect/report` + `/admin/fan-connect/reports*` | **shipped** | Safe connection context; no private payload |
| Suggestions | `fan_connect_suggestions` cache + derived | System (`FanConnectScoringService`) | Opted-in viewers | — | Cap/expiry; score ≥ 40 | Soft | `/connect/suggestions` | `/fan-connect/suggestions` | **shipped** | Safe reasons + labels only; diversity mixer for `mode=mixed` |
| Suggestion dismissals | `fan_connect_suggestion_dismissals` | Viewer dismiss | Self | Soft expire | Exclude while `expires_at`; else −30 | Soft | Suggestions card | `POST …/suggestions/{id}/dismiss` | **shipped** | Migration `20260720_0106` |
| Suggestion feedback | `fan_connect_suggestion_feedback` | System / viewer | Self | Append-only | Keep | Soft | — | dismiss / more-like-this / connect_request (+ FE impressions) | **shipped** | Personalization signals |
| Location preferences | `fan_connect_location_preferences` | Explicit save | Self | Update / clear | Soft delete | Soft | Near-me controls | `POST/GET/DELETE …/location/preference` | **shipped** | City/area only by default; no raw GPS from suggestions GET |

---

## In-app messaging

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Threads | `message_threads` | REST / Connect accept | Participants | Archive/block/report/close | Soft statuses + per-side archive | Soft | `/dashboard/messages`, `/host/messages` | `/messages*`, `/host/messages*` | **shipped** | Gates unchanged; WS push-only |
| Messages | `messages` | REST send (+ optional `reply_to`) | Thread + WS `message.created` | Own body edit within 24h (`edited_at`/`edit_count` + `message_edits`); system lines | Hide / soft-delete (moderation); pins cleared on hide | Soft | Composer + bubbles + action menu | `…/send`, `PATCH /messages/{message_id}`, admin hide/restore | **shipped** | Admins do not edit user bodies — hide/restore only |
| Message edits | `message_edits` | System on participant edit | Internal / audit | Append-only | — | Soft (cascade with message) | — (history not public UI) | Written by edit service | **shipped** | No hard delete; previous/new body retained |
| Message pins | `message_pins` | Participant with thread access | Shared GET pins / thread detail | Re-pin clears `unpinned_at` | Soft unpin (`unpinned_at`); auto on hide/delete | Soft | Pinned banner + drawer | `GET …/threads/{id}/pins`, `POST …/{id}/pin|unpin` | **shipped** | Max 3 active; system msgs allowed |
| Message stars | `message_stars` | Participant star (personal) | Viewer starred list | Re-star clears `unstarred_at` | Soft unstar (`unstarred_at`) | Soft | Starred messages filter + scroll-to | `GET …/starred`, `POST …/{id}/star|unstar` | **shipped** | Peer never notified; hidden/deleted redacted in list |
| Thread message search | — (query) | Participant | In-thread results | — | — | — | Thread header search + chips | `GET …/threads/{id}/search` | **shipped** | Body ILIKE only; optional star/pin/attachment filters; no FTS |
| Message deletions | `message_deletions` | Participant (for_me) | Viewer-scoped placeholder | — | Soft for_me hide | Never hard-delete message row | “Message deleted” bubble | `POST …/{id}/delete` | **shipped** | `for_everyone` blocked until product-approved |
| Attachments | `message_attachments` | Upload to thread then bind on send | Via message serializer + authorized download; admin report view | Status lifecycle + admin hide/restore/review | Soft `hidden`/`deleted_at` (no hard delete by default) | Soft | Composer + admin report moderation | `POST/GET …/attachments*` + admin hide/restore/delete/review | **shipped** | Report-scoped admin only; retention keeps bytes |

---

## Admin Runtime Settings

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Runtime settings (Class B) | `runtime_settings` | Admin upsert allowlisted key | Admin list/category (masked secrets) | PUT value; blank secret keeps existing | Clear override (DELETE row) → env/default; prefer reset over hard-delete of audit | Soft clear only | `/admin/settings/runtime`, `/[category]`, `/audit` | `/admin/settings/runtime*` | **shipped** | Class A never stored; Section 16 tests in `tests/test_runtime_settings.py`; email/push secrets stay specialist |
| Email provider settings | `email_provider_settings` | *(see Transactional email)* | — | — | — | — | Specialist — **not** migrated into `runtime_settings` | — | **complete** | Unified via Runtime Settings UI links/adapters |
| Push provider settings | `push_provider_settings` | *(see Notifications)* | — | — | — | — | Specialist — **not** migrated into `runtime_settings` | — | **complete** | Unified via Runtime Settings UI links/adapters |

Permissions: `admin.settings.*` (see [SETTINGS.md](./SETTINGS.md)). Audit: `runtime_setting_*`. Resolve: DB → env → default. Startup does not depend on this table.

## Maintenance & platform status

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Global settings | `maintenance_settings` | System seed on first access | Admin + public status (safe fields) | Admin PATCH mode/messages | Prefer mode `off` over delete | Never | `/admin/platform/maintenance` | PATCH `/admin/platform/maintenance` | **shipped** | Singleton row |
| Sections | `maintenance_sections` | System seed from catalog | Admin + public active list | Admin PATCH enable/mode/window | Prefer disable (`enabled=false`) | Never | Same + section notices | PATCH `…/sections/{key}` | **shipped** | Catalog in `sections.py` |
| Schedules | `maintenance_schedules` | Admin create | Admin list | Auto activate/complete; cancel | Cancel pending; complete when ends | Soft status only | Schedule form on admin page | POST schedules + cancel | **shipped** | Middleware applies due windows |
| Notifications | `maintenance_notifications` | Admin compose / test | Admin list | Status + delivery_count | Prefer sent/cancelled; no hard delete | Soft | `/admin/platform/maintenance/notifications` | POST notifications (+ test) | **shipped** | Audience hosts/ticket buyers still ≈ all users (capped) |
| Audit logs | `maintenance_audit_logs` | System on actions | Admin history | Append-only | Never | Never | `/admin/platform/maintenance/history` | GET history | **shipped** | No tokens/secrets |
| Bypass sessions | `maintenance_bypass_sessions` | Admin issue | Self via header validate | last_used; revoke | Expire / revoke | Soft revoke | Bypass UI on admin page | POST bypass | **shipped** | Hash only stored |

Permissions: `admin.maintenance.view|manage|schedule|notify|bypass`. Tests: `tests/test_maintenance.py`.

## Transactional email

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Email events (outbox) | `email_events` | System enqueue after product triggers | Admin list/detail | Resend → pending; drain updates status | Prefer `skipped`/`failed`/`sent`; never hard-delete | Never | `/admin/emails`, `/admin/emails/[id]` | `/admin/emails*` | **complete** | Bodies hidden in production |
| User email preferences | `user_email_preferences` | Auto on first access | Self + token | PATCH prefs / unsubscribe | Marketing opt-out (`unsubscribed_marketing_at`); security always on | Soft only | `/dashboard/settings/notifications`, `/unsubscribe` | `/email/preferences*` | **complete** | — |
| Email provider settings | `email_provider_settings` | Safe defaults on first admin GET; activate row | Admin masked GET | Admin PATCH (blank password keeps existing) | Disable sending / deactivate; keep inactive rows for audit; no hard delete | Never | `/admin/email/settings` | `GET/PATCH /admin/email/settings`, test, activate, disable | **complete** | Fernet `EMAIL_SETTINGS_ENCRYPTION_KEY` on host |

## Notifications (in-app + push)

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| In-app notifications | `in_app_notifications` | System via `notify_user` / domain `notify_*` / `triggers.py` | Self list + popup + category filter | Mark read / mark all / popup ack | Archive (`archived_at`); never hard-delete | Soft | `/dashboard/notifications` + header/sidebar unread | `/notifications*` | **complete** | Works without browser push |
| Push subscriptions | `push_subscriptions` | User subscribe (multi-device) | Self list (no keys) | Upsert keys / device label | Soft deactivate (`is_active` + `revoked_at`); 410 / repeated failures auto-deactivate | Soft | Device list on settings/notifications | `/push/subscriptions*` | **complete** | Keys Fernet-encrypted (`p256dh`/`auth`) |
| Push provider settings | `push_provider_settings` | Admin generate/upsert | Admin masked | PATCH + generate keys + provider mode | Disable push globally; deactivate extras | Never | `/admin/push/settings` (alias `/admin/settings/push`) | `/admin/push/settings*` | **complete** | VAPID private encrypted; provider `log`/`web_push` |
| Push delivery events | `push_delivery_events` | System on send | Admin list/summary | Status only | Append-only | Never | Delivery table on push settings | `/admin/push/deliveries` | **complete** | Failed attempts visible; no secrets |
| Push outbox events | `push_events` | System `enqueue_push` / `notify_user` | Admin list | Status + attempts | Soft statuses only | Never | `/admin/push/settings` (events API) | `/admin/push/events` | **complete** | Templates in `app/push/templates.py`; worker drain; dedupe; pref skip |
| Push preferences | columns on `user_email_preferences` | Auto | Self | PATCH `/push/preferences` | Soft toggles (`push_security` locked on) | Soft | Settings notifications | `/push/preferences` | **complete** | Master `push_enabled` defaults on; marketing respects unsubscribe |
| Notification type settings | `notification_settings` | Seed on boot | Admin | PUT `/admin/notifications/settings/{type}` | Disable type (critical = super_admin only) | Soft | `/admin/notifications/settings` | Admin notifications | **complete** | Channels, audience, cooldown, classification |
| Notification templates | `notification_templates` | Admin create / system seed | Admin | PATCH | Soft archive | Soft | `/admin/notifications/templates` | Admin notifications | **complete** | Placeholders `{{host_name}}` etc. |
| Notification campaigns | `notification_campaigns` + recipients | Admin compose | Admin | Draft → send / cancel | Cancel draft/scheduled; archive later | Soft | `/admin/notifications/campaigns*` | Admin notifications | **complete** | Custom multi-channel; safe CTA paths only |
| Notification deliveries | `notification_deliveries` | System on send | Admin | Status only | Append-only | Never | Campaign detail deliveries | Admin notifications | **complete** | Per channel status / errors |
| Notification audit logs | `notification_audit_logs` | System | Admin (via Audit) | Append-only | Never | Never | `/admin/audit-logs` | Admin notifications | **complete** | Mirrored to platform audit |
| Admin team members | `admin_team_members` | Invite / provision | Admin (`admin.team.view`) | PATCH role | Disable / remove (soft) | Soft; strip RBAC roles | `/admin/team`, `/admin/team/[id]` | Admin team | **complete** | Super admin only for high-level |
| Admin roles | `admin_roles` + `admin_role_permissions` | System seed + custom create | Admin | Custom PATCH | Soft archive (custom) | Soft | `/admin/team/roles*` | Admin team | **complete** | System roles immutable |
| Admin invites | `admin_invites` | Admin invite | Admin | — | Expire / accept | Soft status | `/admin/team/invite` | Admin team | **complete** | Token hashed; never in audit |
| Admin team audit logs | `admin_audit_logs` | System on team actions + login | Admin (`admin.team.view_audit`) | Append-only | Never | Never | Member detail | Admin team | **complete** | No secrets/tokens |

---

## Sponsorships

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Sponsors | `sponsors` (+ team) | User onboard | Owner/team; public directory | Owner PATCH; admin verify; team | Archive/suspend | Soft | `/sponsor/*` | `/sponsors/*` | **ok** | — |
| Sponsor saved items | `sponsor_saved_items` | Owner/admin/campaign_manager | Team viewers | Note PATCH | DELETE unsave | Soft | `/sponsor/saved` | `/sponsors/workspaces/{id}/saved*` | **ok** | — |
| Sponsor campaigns | `sponsor_campaigns` (+ links) | Owner/admin/campaign_manager | Team viewers | PATCH + lifecycle | Archive | Soft | `/sponsor/campaigns/*` | `/sponsors/workspaces/{id}/campaigns*` | **ok** | — |
| Sponsor reports | derived aggregates | Team w/ `view_own` | Same | N/A (read-only) | N/A | N/A | `/sponsor/reports` | `/sponsors/workspaces/{id}/reports*` | **ok** | No PII in payloads |
| Sponsorship slots | `sponsorship_slots` (+ host settings) | Host | Public/host/admin | Host PATCH; admin moderate | Delete → `disabled` (soft); restore to draft | Soft | `/host/sponsorships`, `/new`, `/[id]/edit` | `/sponsorships/host/slots*` | **ok** | Host CRUD; hard delete N/A |
| Sponsorship inquiries | `sponsorship_inquiries` | Public | Host + sponsor inbox | Host PATCH status | Soft close | Soft | Marketplace + host + `/sponsor/inquiries` | inquire + host PATCH + `/sponsors/me/inquiries` | partial | Placement create FE |
| Sponsorship placements | `sponsorship_placements` | Deal webhook / host API | Host list | — | Soft status | Soft | Host deals active state | `POST /host/placements` + deal pay | partial | Primary path: paid deal |
| Sponsorship deals | `sponsorship_deals` | Host proposal | Host/sponsor/admin | Host PATCH; sponsor accept/reject | Cancel/reject | Soft | `/host/sponsorships/deals*` | `/host/sponsorship-deals*` | **ok** | — |
| Sponsorship invoices | `sponsorship_invoices` | On accept | Parties + admin | Pay init; webhook paid | void (admin) | Soft | `/sponsor/deals*` | sponsor `/deals/{id}/pay` | **ok** | Return URL ≠ paid |
| Sponsorship payment events | `sponsorship_payment_events` | Paystack webhook | System audit | Append-only | — | Immutable | — | `PDY-SPN-*` webhook | **ok** | Redacted payload |
| Sponsorship deliverables | `sponsorship_deliverables` | Deal active seed | Host/sponsor/admin | Host submit; sponsor approve/reject | completed/cancelled | Soft | Deal detail checklists | `…/deliverables*` | **ok** | No auto-complete |
| Sponsorship analytics | `sponsorship_analytics` | Auto w/ placement | Nested | Impression/click POST | Counters | Soft | Unused tracking FE | public impression/click | partial | FE not wired to track |

---

## Support

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Support tickets | `support_cases` (+ messages, notes, attachments, events, assignments, settings, deflection) | User / host / visitor / admin | Own + host-related; staff by permission | Reply / assign / priority / status | Resolve / close / reopen / archive | Prefer archive | `/support*` (guided Help-first), `/dashboard/support*`, `/host/support*`, `/admin/support*` | `/api/v1/support/tickets*`, `/deflection-events`, `/api/v1/admin/support/*` | **complete** | Help suggestions before ticket; deflection metadata on staff detail; email templates optional |
| Support messages | `support_messages` | Requester + staff | Same as ticket; internal flag filtered | Append-only | — | Soft via ticket archive | Conversation UIs | reply endpoints | **complete** | — |
| Internal notes | `support_internal_notes` | Staff (`admin.support.internal_notes`) | Staff only — never public | Append-only | Never | Never | Admin/staff detail only | `/internal-note`, `/notes` | **complete** | — |
| Demo support | `demo_support_cases` | Seed | Demo | — | — | Demo | — | demo seed only | **legacy** | Not product SoT |
| Internal notes | Demo column / refund notes | Refund escalate notes | — | — | — | Soft | Refund UIs | Refund fields | **missing** (as entity) | No note history resource |
| Escalations | No entity | Refund escalate | — | Status under_review | Soft | Soft | `/support/refunds` | `POST .../refunds/.../escalate` | partial | Refund-only; not general cases |

---

## Analytics

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Analytics events | `analytics_events` | Track (append-only) | Aggregates + CSV | Never | Never | Never | Host/admin analytics | `POST /analytics/track/event` | **complete** (planned-readonly) | No raw event query (by design) |
| Page views | `page_views` | Track (append-only) | Aggregates | Never | Never | Never | Track helpers | `.../track/page-view` | **complete** (planned-readonly) | — |
| Event impressions | `event_impressions` | Track (append-only) | Aggregates | Never | Never | Never | Track helpers | `.../track/impression` | **complete** (planned-readonly) | — |
| Event clicks | `event_clicks` | Track (append-only) | Aggregates | Never | Never | Never | Track helpers | `.../track/click` | **complete** (planned-readonly) | — |
| Conversion events | `conversion_events` | Track (append-only) | Aggregates | Never | Never | Never | Track helpers | `.../track/conversion` | **complete** (planned-readonly) | — |

---

## AI

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Prompt templates | `ai_prompt_templates` | Seed | Used at generate | Seed `is_active` | Soft intended | Soft | — | `ai/seed.py` | partial | No admin template CRUD |
| AI usage logs | `ai_usage_logs` | On generate (system) | Response id only | Immutable | Never | Never | Host/admin AI pages | Generate endpoints | **planned-readonly** (partial) | No usage dashboard API yet |
| AI settings | Env/config only | Deploy/env | `GET /ai/status` | Env deploy | Never | N/A (not DB) | Indirect | `core/config.py` | **planned-readonly** | Secrets stay in env — not a DB CRUD resource |

Generate (not content CRUD): `POST /ai/host/generate`, `.../events/{id}/generate`, `/ai/admin/generate`, `/ai/admin/support/summary`.

---

## CMS / Content

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Blog posts | `blog_posts` (+ categories/tags/authors) | Admin (`admin.blog.create`) | Public published only; admin all | PATCH | Publish / unpublish / schedule / archive | Prefer archive | `/blog*`, `/admin/blog*` | `/api/v1/blog/*`, `/api/v1/admin/blog/*` | **complete** | Legacy `cms_blog_posts` migrated; markdown + sanitize |
| Blog comments | `blog_comments` (+ `blog_comment_edits`) | Guest (name + body + honeypot) or authenticated; replies via `POST /blog/comments/{id}/reply` (one-level) | Public `published` only (threaded); admin all | Owner PATCH (`blog.comments.edit_own`) or staff PATCH (`admin.blog.comments.edit_any` / moderate) | Author withdraw (archive); admin hide / restore / archive | Prefer archive (no hard delete) | `/blog/[slug]` comments; `/admin/blog/comments` | `GET\|POST /blog/posts/{slug}/comments`, `POST /blog/comments/{id}/reply`, `PATCH\|DELETE /blog/comments/{id}`, `/admin/blog/comments*` | **complete** | One-level threading (`parent_comment_id`, `depth` 0\|1); edit history private; emails never public; staff badge `Pàdéyá`/`Moderator` |
| Knowledge Base / Help articles | `knowledge_base_articles` (+ categories/tags/feedback/search_logs) | Admin (`admin.knowledge_base.create`) | Public published only; admin all | PATCH | Publish / unpublish / schedule / archive | Prefer archive (DELETE soft-archives) | `/help*`, `/admin/knowledge-base*` (+ insights), `/dashboard\|host\|admin/help` | `/api/v1/help/*` (incl. suggestions), `/api/v1/admin/knowledge-base/*` | **complete** | Markdown + sanitize; safe embeds; topic suggestions for Support deflection; feedback + search-term insights |
| CMS blog (legacy) | `cms_blog_posts` | — | Migrated into `blog_posts` | — | — | — | Redirect `/admin/cms/blog` → `/admin/blog` | `/cms/admin/blog*` (legacy) | **superseded** | Use Blog module |
| Pages (CMS) | **None** | — | Static Next pages | — | — | — | App routes | — | **missing** | Generic pages still absent |
| FAQs | `cms_faqs` | Admin | Public published + admin | PATCH | Publish/archive/restore | Hard delete blocked | — | `/cms/faqs`, `/cms/admin/faqs*` | **complete** (API) | No FE |
| Homepage banners | `cms_homepage_banners` | Admin | Public published + admin | PATCH | Publish/archive/restore | Hard delete blocked | `/` hardcoded | `/cms/banners`, `/cms/admin/banners*` | **complete** (API) | Homepage not wired to API |
| Homepage browse tiles | `cms_browse_tiles` | Admin + seed defaults | Public published + admin | PATCH (image_url, label, href, rail, sort) | Publish/archive/restore | Hard delete blocked | `/admin/cms/browse-tiles`, homepage `HomeBrowseTaxonomy` | `/cms/browse-tiles`, `/cms/admin/browse-tiles*` | **complete** | Image via URL paste; FE falls back to defaults if empty |
| Featured events | `events.featured` flag | Admin feature | Public list | Feature/unfeature | Flag | Soft flag | Homepage `FeaturedEvents` | `POST /events/admin/{id}/feature\|unfeature` | **complete** | Orthogonal to Pàdéyá Picks |
| Pàdéyá Picks / Featured Placement Slots | `featured_placements` (Primary+Secondary per placement_type) | System ensure draft rows per key | Public picks + admin | Assign/clear + schedule overrides; listing quick-assign | Archive / clear → draft | Prefer archive; slot rows kept | `/admin/events/picks`, `/admin/events` (+ review), `/admin/featured-placements`, homepage + discovery | `GET /events/padeya-picks?context=…`, `POST /events/admin/{id}/padeya-pick\|unpadeya-pick`, admin featured-placements (+ listing-picks) | **complete** | Listing admin manages homepage/events_page; hub contexts stay on featured-placements; statuses: draft/active/scheduled/expired/archived |

---

## Taxonomy

| Resource | Model | Create | Read | Update | Delete / lifecycle | Hard delete? | Frontend | Backend (key) | Status | Primary gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Categories | `taxonomy_categories` (+ legacy `event_categories`) | Admin | Public + admin | PATCH | Archive/restore | Blocked when in use | `/admin/taxonomy/categories` | `/taxonomy/admin/categories*` | **partial** | Dual-write cutover pending |
| Tags | `taxonomy_tags` | Admin | Public + admin | PATCH | Archive/restore | Prefer archive | `/admin/taxonomy/tags` | `/taxonomy/admin/tags*` | **partial** | Usage counts soft |
| Locations | `locations` | Admin | Public + admin + hubs | PATCH | Archive/restore | Prefer archive | `/events/location`, `/events/{country\|state\|city\|area}/…`, `/admin/taxonomy/locations` | `/taxonomy/locations*`, event `location_kind`/`location_slug` | **partial** | GPS near-me deferred |
| Host types | `host_types` | Admin | Public + admin | PATCH | Archive/restore | Prefer archive | `/admin/taxonomy/host-types` | `/taxonomy/admin/host-types*` | **partial** | — |
| Venue types | `venue_types` | Admin | Public + admin | PATCH | Archive/restore | Prefer archive | `/admin/taxonomy/venue-types` | `/taxonomy/admin/venue-types*` | **partial** | Venue catalog Phase B |
| Host taxonomy links | `host_taxonomy_links` / `host_location_links` | Host PATCH | Host me | Replace sync | Soft replace | Soft | `/host/settings` | `PATCH /hosts/me` | **partial** | Public Legacy surfacing |
| Content relationships | `content_relationships` | System/seed | Internal | Weight/expire | Expire | Soft | Related rails (live queries Wave 0) | Demo seed + Wave 5 job | **partial** | Graph job deferred |

See [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md).

---

## Security invariants (must not regress)

1. Support agents **cannot** modify financial records or mark payouts paid.
2. Hosts **cannot** delete or edit buyer reviews (`DELETE`/`PATCH /reviews/{id}` owner-only; hosts get 403/404).
3. Public APIs **must not** leak hidden venue addresses or online links.
4. Payments, ledger, refunds, payouts, audit logs: **no hard delete**.
5. Tickets with sales history: cancel/transfer only — no hard delete.
6. Manual payouts require **immutable evidence**.

---

## Scoreboard (inventory)

| Area | complete | partial | missing |
|---|---|---|---|
| Core/Auth | refresh tokens; roles/perms (ops); users API; audit read | user roles | — |
| Hosts | followers; verification API; team; bank accounts | profile (no admin suspend) | — |
| Events | events; ticket types; media; agenda; people; questions; memories; templates; categories admin | venue | — |
| Ticketing | tickets; tables (+ cancel) | orders; items; QR; transfers; groups; offline batches | — |
| Finance | payments; refund requests; balances; ledger; payouts; evidence | webhook events; refund rows | — |
| Check-in | check-ins; staff | sessions; overrides FE | — |
| Legacy/Reviews | verified reviews (buyer CRUD + admin moderate) | replies/reports/tiers/score history | — |
| Vault | subscriptions API | items/media/rules/purchases/views | — |
| CRM/Promos | followers | segments; announcements; promos; ambassadors; clicks/redemptions | — |
| Passport | — | all four | — |
| Sponsorships | — | all five (placement FE gap) | — |
| Support | cases/messages/notes API | refund escalate FE | — |
| Analytics | all five track types | — | — |
| AI | generate flows | templates; usage logs | — (settings = env) |
| CMS | blog/FAQ/banner API; featured admin | homepage still hardcoded | generic pages |
| Taxonomy | categories/tags/locations/host-types/venue-types APIs + hubs | host links; graph job; cutover | vault/memory taxonomy links |

---

## Highest-impact remaining gaps

1. **Frontend wiring** for new lifecycle APIs (CMS, host team/bank, templates, featured, audit read).
2. **Sponsorship placements** — backend create exists; frontend create missing.
4. **Webhook event admin read** — still write-only.
5. **Generic CMS pages** — still absent (blog/FAQ/banners done).
6. **Manual check-in override** — API exists; frontend not wired.
7. **Host admin suspend/list** — profile lifecycle still partial.

---

## Implementation log

| Date | Change |
|---|---|
| 2026-07-17 | Taxonomy: vocab tables, hubs, Studio/host taxonomy, demo seed, discovery FE |
| 2026-07-17 | Lifecycle wave: event pause/resume/cancel/discard; ticket-type deactivate/delete; staff unassign; CRM segment delete + announcement cancel; host Event ops UI |
| 2026-07-17 | Full inventory audit of all listed modules → this matrix |
| 2026-07-17 | Canonical rules applied: event archive + admin pause/restore; order archive; refund cancel; review update/withdraw; vault delete/archive; promo/ambassador unused delete; announcement draft PATCH + archive; support cases module; AI template admin CRUD; QR regenerate; ticket-type post-sales field protection |
| 2026-07-17 | Missing lifecycles: host team/bank/verification; event templates; categories + featured admin; vault subscriptions; CMS blog/FAQ/banners; user deactivate; audit log list; table cancel (`20260717_0020`) |
| 2026-07-17 | Frontend lifecycle UI: host team/bank/templates/vault subs; admin verification/categories/CMS/audit/users; buyer settings + vault subs; ConfirmAction+toast; table cancel; nav wiring |
| 2026-07-17 | Vault item lifecycle: draft/published/scheduled/expired/archived/hidden_by_admin; publish/unpublish/schedule/restore; draft-only delete; admin hide/restore; audited actions |
| 2026-07-17 | Vault docs + checklist tests: access matrix, Legacy/event/memory teasers, grants/attempts, analytics funnel, FE `test:vault` smoke |
| 2026-07-17 | Invariant: lifecycle never optional — even read-only/append-only modules require an explicit plan (`CRUD_PATTERN.md` + matrix status `planned-readonly`) |
| 2026-07-17 | Subresource lifecycle: agenda/people upsert-by-id; checkout questions archive-when-answered (`20260717_0030`); media DELETE; event restore; Studio ConfirmAction parity |
| 2026-07-17 | Docs: Event Studio fields, location privacy, subresource/ticket/question CRUD, publish checklist across API / DATABASE / FRONTEND_ROUTES / CRUD_* / TAXONOMY / SECURITY / ROADMAP; tests `test_event_studio_lifecycle.py` + `npm run test:studio` |
| 2026-07-18 | CMS homepage browse tiles: image/label/href editable from admin; public `/cms/browse-tiles`; seed defaults; homepage wired with static fallback (`20260718_0037`) |
| 2026-07-19 | Verified reviews buyer CRUD: PATCH edit + restore-from-withdrawn; DELETE soft withdraw; `/dashboard/reviews` create/edit/withdraw UI; API + matrix updated |
| 2026-07-21 | Blog comments: guest + authenticated create; public `passport_path` only when Fan Passport is public; author withdraw + admin hide/restore/archive (`20260721_0118`) |
| 2026-07-21 | Blog comment editing: owner + admin/moderator PATCH, `blog_comment_edits` history, edited labels, `/admin/blog/comments` UI (`20260721_0119`) |
| 2026-07-21 | Blog comment replies: one-level threading (`parent_comment_id`/`depth`), `POST /blog/comments/{id}/reply`, staff badges, guest replies follow guest policy (`20260721_0120`) |
