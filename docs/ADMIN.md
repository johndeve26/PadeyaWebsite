# Admin tools

## Maintenance & platform status

Admins can put Pàdéyá (or specific sections) into maintenance, schedule windows, notify users in advance, and issue short-lived bypass tokens.

**Modes:** `off` · `scheduled` · `active` (full-site) · `read_only` · `section_only`

| Surface | Path |
| --- | --- |
| Admin controls | `/admin/platform/maintenance` |
| History / audit | `/admin/platform/maintenance/history` |
| Advance notifications | `/admin/platform/maintenance/notifications` |
| Public status page | `/maintenance` |

**Permissions:** `admin.maintenance.view` · `manage` · `schedule` · `notify` · `bypass` (`admin.full_access` covers all). Support gets `view` by default.

**Enforcement:** `MaintenanceMiddleware` on every API request — 503 for hard maintenance, 423 for read-only writes. Always allows health, auth (incl. logout), public `/maintenance/status`, payment webhooks, and admin maintenance APIs. Admin panel stays online when `allow_admin_panel` is true and the caller has maintenance/view/manage or full access. Bypass via header `X-Maintenance-Bypass` (hashed session, TTL, audited; never logged as plaintext).

**Audit (no secrets/tokens):** `maintenance_enabled` · `maintenance_disabled` · `read_only_mode_enabled` · `section_maintenance_changed` · `schedule_*` · `notification_sent` · `bypass_used` · `bypass_token_regenerated`.

See [API.md](./API.md#maintenance--platform-status) · [CRUD_MATRIX.md](./CRUD_MATRIX.md).

## Admin Runtime Settings

Typed allowlist for **Class B** tunables (workers, rate limits, merch TTLs, analytics windows, soft product knobs) plus **Payment integration** Paystack keys (encrypted secrets + public key). Boot-critical Class A (`DATABASE_URL`, `SECRET_KEY`, encryption key, etc.) stays on `.env` / `Settings` only.

**Payment gateway:** Admin → System → **Payment integration** (`/admin/settings/runtime/payments`) — set Paystack secret, webhook secret, public key, and base URL. Secrets show as `Configured · ending in ####` only; requires `admin.settings.edit_secrets`. Env remains fallback when no DB override.

- UI: `/admin/settings` → `/admin/settings/runtime`, `/admin/settings/runtime/[category]`, `/admin/settings/runtime/audit`
- API: `/api/v1/admin/settings/runtime*` (see [API.md](./API.md))
- Permissions: `admin.settings.view` · `edit_runtime` · `edit_secrets` · `test_integrations` · `view_system_status` · `clear_overrides` · `view_audit` (`admin.full_access` covers all)
- Resolve order: DB `runtime_settings` → env / `Settings` → registry default
- Secrets: `Configured · ending in ####` / `Not configured` only — no reveal
- **Keep** email (`/admin/email/settings`) and push (`/admin/push/settings`) specialist tables; hub unifies via links/adapters — do not migrate SMTP/VAPID into `runtime_settings`
- Startup does not depend on DB runtime settings; missing optional config degrades gracefully

Canonical: [SETTINGS.md](./SETTINGS.md) · [ENVIRONMENT.md](./ENVIRONMENT.md) · [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md) · [SECURITY.md](./SECURITY.md).

## User impersonation

**Internal support/QA** — temporary view of Pàdéyá as a specific user. Fully audited. **Not** a real login. The target user is **never** notified (no email, in-app, or push).

Canonical detail: [SECURITY.md](./SECURITY.md#admin-user-impersonation) · [AUTH.md](./AUTH.md#admin-user-impersonation) · [API.md](./API.md#admin-user-impersonation).

### Guarantees

| Guarantee | Behavior |
| --- | --- |
| **Internal and audited** | Support/QA only. Every start / end / expiry / sensitive block / stamped request is logged (`admin_impersonation_*`). Dual-write to domain + `audit_logs`. |
| **Target user is not notified** | No email · no in-app · no push. |
| **No password access** | Passwords are never read, returned, or shared. |
| **No session hijacking** | Target refresh tokens are untouched. A separate short-lived impersonation access token is issued (no refresh). |
| **Sensitive actions blocked** | Always: 2FA, account delete, bank/payouts, checkout/payments, ticket transfer, content delete, Passport privacy, social/Fan Connect, API/provider keys, admin/support/finance mutations. Pack-gated: host studio (`host_events`), credentials (`credentials` / full pack only). Exact 403: `This action is disabled during admin impersonation.` |
| **Capability packs** | Role packs (not checkboxes): `view` (support/finance grant) · `host_events` (`admin` / `operations` + `admin.users.impersonate.host_events`) · `full` (`super_admin` / `admin.full_access` includes credentials). Prefer Admin Orders / Support desk / Message reports instead of impersonating to “just look”. |
| **Allowed while impersonating** | Per pack: reads always; host studio with `host_events`; password/email/phone with `credentials`; exit session. Checkout/payouts stay blocked. |
| **Max duration** | `15` / `30` / `60` minutes; **default 30**, **max 60**. Auto-expire; end on Exit / logout; end if admin or target disabled mid-session; no nested sessions; one active session per admin. |
| **Permission required** | `admin.users.impersonate` (view pack) · `admin.users.impersonate.host_events` (host pack) · credentials via `admin.full_access` only. Support/finance need **explicit** impersonate grant. Buyers / hosts / host staff never. |
| **Admin / session separation** | Current user = target; `actor_admin_id` stays the admin. Claims include `impersonation_scopes` / `impersonation_pack`. Admin tokens stashed client-side and restored on Exit. Admin permissions never leak; `/admin` blocked while impersonating. |
| **Audit logs retained** | Actor admin, target, reason, ticket, start / end / expiry, routes, blocked actions, plus `scopes` + `pack` on start. Never silently bypassed in demo mode. Admin banner only. Field matrix: see [Impersonation audit events](#impersonation-audit-events). |

### Impersonation audit events

Domain `admin_impersonation_audit_logs` (+ dual-write `audit_logs`, `resource_type=impersonation_session`):

| Action | When |
| --- | --- |
| `admin_impersonation_started` | Session start |
| `admin_impersonation_ended` | Exit / logout / safety end |
| `admin_impersonation_expired` | Timed-out token use |
| `admin_impersonation_sensitive_action_blocked` | Guard blocks a mutation |
| `admin_impersonation_request_made` | Stamped allowed request (no body) |

Fields: `impersonation_id`, `actor_admin_id`, `target_user_id`, `action`, `path`/`route`, `method`, `reason`, `support_ticket_id?`, `ip_address?`, `user_agent?`, `created_at`. Never stores request bodies, passwords, tokens, payment/QR payloads, or private message content.

### UI

- `/admin/users` — look up by UUID **or email** → open user
- `/admin/users/[userId]` — user detail, **Impersonate user** modal (requires permission), impersonation history
- `/admin/users/[userId]/impersonation` — standalone start form
- Modal: target summary, warning, required reason (≥ 3 chars), optional support ticket ID, duration 15/30/60, checkbox “I understand this session is audited and sensitive actions are blocked.” → **Start impersonation**
- After start: redirect as the target; sticky global banner (masked name/email, admin actor, countdown, Exit). Demo seeds also show **Demo seed account**.
- Exit → `/admin/users/[userId]`
- History columns: started by, reason, started_at, ended_at, status
- Demo QA: seed accounts still log in normally; `/demo` Impersonation QA shortcuts

### API (summary)

| Method | Path |
| --- | --- |
| POST | `/api/v1/admin/users/{user_id}/impersonation/start` |
| GET | `/api/v1/admin/users/{user_id}/impersonation/history` |
| POST | `/api/v1/admin/impersonation/end` |
| GET | `/api/v1/me/impersonation` |
| GET | `/api/v1/me/session` |
| GET | `/api/v1/users/admin/{user_id}` |
| GET | `/api/v1/users/admin/lookup?email=` |

Start body: `{ reason, support_ticket_id?, duration_minutes }` → `{ impersonation_id, target_user_id, expires_at, redirect_to, access_token }` (no `refresh_token`).  
End → `{ ended: true, return_to: "/admin/users/{user_id}" }`.

### Rules

- Blocked targets: self, `super_admin`, `support_agent`, `finance_admin`, security-locked, deleted/missing; suspended/inactive only for super_admin with reason
- While impersonating: buyer dashboard as target; host tools only if target has host access; safe reads allowed (tickets/orders/settings/Passport/Vault pages)
- Claims: `actual_user_id`, `actor_admin_id`, `impersonation_id`, `is_impersonating`, `started_at`, `expires_at`, `reason`, `support_ticket_id` (+ target-only roles/permissions)

## User management (safe actions)

Support and super-admin tooling for platform user lifecycle. **No hard delete**, password reveal, token reveal, payout overrides, or unsafe role editing.

| Route | Purpose |
| --- | --- |
| `/admin/users` | Directory — search, status/role filters, status + signal badges, UUID/email lookup |
| `/admin/users/[userId]` | Detail — tabs **Overview · Activity · Flags · Notes · Security · Audit**; safe actions + Impersonate when permitted |
| `/admin/users/[userId]/impersonation` | Standalone impersonation start (requires `admin.users.impersonate`) |

Canonical API: [API.md](./API.md#admin-user-management-safe-actions) · schema: [DATABASE.md](./DATABASE.md#admin-user-management) · lifecycle: [CRUD_MATRIX.md](./CRUD_MATRIX.md).

### Safe fields only

Admin list/detail JSON is scrubbed (`app.users.admin_response_safety`):

- **Never returned:** passwords / hashes, reset or verification tokens, refresh/access/session tokens, OAuth tokens, 2FA/TOTP secrets, QR payloads, merch pickup tokens, Paystack/provider secrets, private message bodies
- **Preferred instead:** `email` (full address on admin list/detail), `email_masked` (secondary), `phone_masked` / `phone_available`, `last_four`, `configured`, `status`, counts, timestamps
- Admin detail **always** returns the real email (same as the directory list). Phone and other private fields still require `admin.users.view_private_contact` when implemented. Opening detail audits `admin_user_private_contact_viewed` because email is exposed.

### Permissions

| Permission | Who (default seed) | Actions |
| --- | --- | --- |
| `admin.users.view` | `support_agent`, `super_admin` | List/detail directory; implies `view_activity` + `view_audit` |
| `admin.users.view_private_contact` | `super_admin` only | Phone / extended private fields on admin detail (email is always shown on admin users) |
| `admin.users.view_activity` | via `view` (or explicit) | Activity counters / activity slice |
| `admin.users.view_security` | `super_admin` only | Security lock reason + active session count |
| `admin.users.add_note` | `support_agent`, `super_admin` | Append internal notes |
| `admin.users.flag` | `super_admin` only | Add / resolve / dismiss flags |
| `admin.users.restrict` | `super_admin` only | Legacy umbrella: under-review + implies view/add/revoke restriction |
| `admin.users.view_restrictions` | via `view` / `restrict` (or explicit) | List restriction history on user detail |
| `admin.users.add_restriction` | `super_admin` only (or via `restrict`) | Apply / extend selective restrictions + presets |
| `admin.users.revoke_restriction` | `super_admin` only (or via `restrict`) | Revoke restriction rows (soft; never hard-delete) |
| `admin.users.suspend` | `super_admin` only | Full suspension / unsuspend (`account_status=suspended`); also reviews appeals |
| `admin.appeals.review` | `super_admin`, `support_agent` | List / approve / reject suspension appeals |
| `admin.users.ban` | `super_admin` only | Ban / restore from banned |
| `admin.users.force_logout` | `super_admin` only | Revoke all refresh sessions |
| `admin.users.force_password_reset` | `super_admin` only | Force password-reset email |
| `admin.users.view_audit` | via `view` (or explicit) | Per-user audit history |
| `admin.users.impersonate` | `super_admin` (explicit for support/finance; never for buyers/hosts/host_staff) | Audited impersonation |

`admin.full_access` (and therefore `super_admin`) satisfies every check. **Finance admins do not get user management by default** — grant `admin.users.*` explicitly. Support gets **view + add_note only** unless granted more. Cannot restrict **self**; normal admin cannot restrict `super_admin` / other platform admins (`admin.full_access`).

### Safe actions (product)

| Action | Behavior | Audited |
| --- | --- | --- |
| **Internal note** | Append-only (`user_admin_notes`); `note_type` catalog; admin-only (never shown to user); rejects password/token/payment/QR secret content; no edit/delete API | `admin_user_note_created` |
| **Admin flag** | Catalog `flag_type` + `severity` (`low`–`critical`); status `active` → resolve/dismiss; optional `internal_note`; no hard delete | `admin_user_flag_created` · `admin_user_flag_updated` |
| **Activity / audit** | Per-user recent activity + platform audit rows on detail | Read-only |
| **Force logout** | Revokes all refresh tokens; never returns token values | `admin_user_force_logout` |
| **Force password reset** | Invalidates unused reset tokens; emails user a reset link; never returns raw token | `admin_user_force_password_reset` |
| **Under review** | Soft ops hold via `account_status=under_review` (distinct from suspend) | `admin_user_status_changed` |
| **Selective restrictions** | Day-to-day tool: append-only `user_restrictions` rows (active / expired / revoked); reason required; optional `ends_at` / internal note; derives `account_status=restricted` when not suspended/banned/deleted; syncs `ambassadors_blocked` from ambassador keys | `admin_user_restriction_added` · `_revoked` · `_extended` · `_preset_applied` |
| **Restriction presets** | Messaging · Buyer · Host · Ambassador · Read-only · **Full suspension** (preset-only emergency path) | same as above (+ status change for full suspension) |
| **Suspend / unsuspend** | Product block: `account_status=suspended` + sessions revoked; user may still log in for `/account/suspended` + appeal only; notifies in-app / email / push (public category · duration · date only); prefer **Full suspension** preset for day-to-day | `admin_user_status_changed` · `admin_user_suspension_notified` · `admin_user_unsuspended` |
| **Suspension appeal** | Suspended user submits message; admin `/admin/appeals` approve (unsuspend) or reject (optional user-facing reply) | `account_appeal_submitted` · `account_appeal_approved` · `account_appeal_rejected` |
| **Ban** | Stronger permanent block (`account_status=banned`) | `admin_user_status_changed` |
| **Hard delete** | **Blocked** — `DELETE /users/admin/{id}` → `405` | — |

### Selective restrictions (primary moderation)

Source of truth: `user_restrictions` (not `users.account_restrictions` JSON mirror). Soft lifecycle only — **never hard-delete**.

| Preset | Keys |
| --- | --- |
| Messaging | `cannot_message`, `cannot_use_fan_connect` |
| Buyer | `cannot_buy_tickets`, `cannot_buy_merch`, `cannot_checkout`, `cannot_transfer_tickets` |
| Host | `cannot_create_events`, `cannot_publish_events`, `cannot_manage_events`, `cannot_scan_tickets`, `cannot_manage_merch`, `cannot_invite_host_team`, `cannot_manage_sponsorships`, `cannot_manage_host_ambassadors` |
| Ambassador | `cannot_join_ambassador_campaigns`, `cannot_promote_events`, `cannot_receive_ambassador_rewards`, `cannot_request_ambassador_payouts` |
| Read-only | `read_only_account` |
| Full suspension | All major `cannot_*` + `read_only_account` **and** `account_status=suspended` (product APIs blocked; login allowed for appeal surface only) |

Individual toggles are grouped: Personal/buyer · Community · Host · Ambassador · Account/security · Admin/support. Full catalog: `backend/app/users/account_status_constants.py`.

**Status derivation:** active selective rows → may set `restricted`; Full suspension → `suspended`; Ban → `banned`. Global statuses win until cleared. When all restrictions are revoked and user is not suspended/banned/deleted → return to `active` (or stay `under_review`).

**Enforcement:** `user_has_restriction` / `assert_no_restriction` at product gates (checkout, messaging, Fan Connect, reviews, host actions, ambassadors, …) → HTTP 403. End users see keys only on `/me` (never admin `reason` / `internal_note`); UI shows a generic “This action isn’t available on your account.”

### Audit log events

Platform `audit_logs` rows for admin user management (scrubbed details):

| Action | When |
| --- | --- |
| `admin_user_viewed` | Admin opens user detail |
| `admin_user_private_contact_viewed` | Admin opens user detail (real email is always included) |
| `admin_user_note_created` | Internal note added |
| `admin_user_flag_created` / `admin_user_flag_updated` | Flag add / resolve-dismiss |
| `admin_user_status_changed` | Account status transition |
| `admin_user_restriction_added` | Restriction row(s) created |
| `admin_user_restriction_revoked` | Restriction revoked |
| `admin_user_restriction_extended` | `ends_at` / duration extended |
| `admin_user_restriction_preset_applied` | Named preset applied |
| `restricted_user_blocked_from_action` | Enforcement blocked a restricted action |
| `admin_user_force_logout` | Force logout |
| `admin_user_force_password_reset` | Force password-reset email |
| `admin_user_suspension_notified` | Suspension notifications dispatched (in-app / email / push; no internal notes) |
| `account_appeal_submitted` | User submitted a suspension appeal |
| `account_appeal_approved` | Admin approved appeal (unsuspend) |
| `account_appeal_rejected` | Admin rejected appeal (optional user-facing reply) |
| `admin_user_unsuspended` | Account restored from suspension (e.g. via appeal approval) |

Detail fields: `admin_user_id`, `target_user_id`, `restriction_keys?`, `reason?`, `internal_note_present` (boolean only — **never** note body), `starts_at` / `ends_at`, `previous_status` / `new_status`, optional `before_json` / `after_json` (+ row `ip_address` / `user_agent` / `created_at`). Note/flag bodies and secrets are never stored.

Explicitly **out of scope**: password reveal, refresh/access token reveal, payout/refund overrides, runtime role assign/revoke UI.

### UI

- **List** (`/admin/users`) — search, status/role filters, badges, empty + permission-denied states
- **Detail** (`/admin/users/[userId]`) — Overview · **Restrictions** · Activity · Flags · Notes · Security · Audit
  - **Restrictions** tab (`AdminUserRestrictionsPanel`): current active rows + history, presets, grouped individual toggles, reason (required), optional internal note, duration (24h / 7d / 30d / indefinite / custom), confirm before apply, revoke / extend, Full suspension preset
  - Flags / notes / status / force logout / force password-reset gated by granular `admin.users.*`
  - **Impersonate user** (requires `admin.users.impersonate`) — modal: reason, duration (15/30/60), optional ticket, confirm → `/dashboard`
- Global **ImpersonationBanner** while active (full target email, actor admin, time remaining, Exit) — desktop/mobile, light/dark
- **Appeals** (`/admin/appeals`) — pending/approved/rejected queue; approve unsuspends; reject with optional user-facing reply (`admin.appeals.review` or `admin.users.suspend`)
- **Suspended user** (`/account/suspended` via `RequireAuth`) — category / duration / dates, Appeal + Logout

## Email outbox

- UI: `/admin/emails`, `/admin/emails/[id]`, `/admin/emails/templates`, `/admin/emails/settings`
- API: `/api/v1/admin/emails*` (outbox); `/api/v1/admin/emails/templates*` (editable admin platform templates)
- Permissions: `admin.emails.view`, `admin.emails.edit_templates`, `admin.emails.test_send`, `admin.emails.manage_recipients`, `admin.notifications.manage_settings` (`admin.full_access` includes all)
- Shows template, recipient, status, attempts, errors, provider message id
- Resend failed/pending events
- Body preview only in development / `EMAIL_DEV_MODE`

### Platform admin notification templates

Dedicated admin emails for platform events (not fan/host mail). Defaults in `admin_catalog.py`; overrides in `email_admin_templates`. Recipient groups: super_admin, support, moderation, finance, operations, marketing, custom. Ticket/merch sale admin emails fire only after verified payment (same hooks as buyer confirmations).

## Email / SMTP provider settings

- UI: `/admin/email/settings`
- API: `GET/PATCH /api/v1/admin/email/settings`, `POST .../test`, `POST .../activate`, `POST .../disable`
- Requires `admin.full_access` (super_admin)
- Providers: `log`, `smtp`, plus Postmark/Brevo/Resend/SendGrid placeholders
- SMTP username/password Fernet-encrypted (`EMAIL_SETTINGS_ENCRYPTION_KEY`); masked last4 only in API
- Blank password on save keeps the existing secret
- Active DB settings override env; worker picks up changes next batch (no rebuild)

See [EMAILS.md](./EMAILS.md) and [OPERATIONS.md](./OPERATIONS.md).

## Browser push settings

- UI: `/admin/push/settings` (alias `/admin/settings/push`)
- API: `GET/PATCH /api/v1/admin/push/settings`, `POST .../disable`, `POST .../test`, `POST .../test-user`, `GET .../subscriptions/lookup`, `GET /admin/push/deliveries`, `GET /admin/push/events`, `POST .../cleanup-subscriptions`
- Requires `admin.full_access` (super_admin)
- Providers: `log` (safe default) · `web_push`
- VAPID private key Fernet-encrypted; never returned to the frontend
- Test push uses fixed copy (*Pàdéyá test notification* / *Push notifications are working.*) and requires an active device subscription
- Delivery + outbox inspection on the same settings surface

See [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md) · [OPERATIONS.md](./OPERATIONS.md).

## Event buyers / attendees export

- UI: `/admin/events/[id]/buyers`, `/attendees`, `/exports`
- API: `GET /api/v1/admin/events/{event_id}/buyers`, `…/buyers/export`, `…/buyers/exports`
- Requires **both** `admin.events.view` and `admin.events.export_buyers` (not host `payments.view`)
- Modes: `public_summary` · `operations` (default) · `finance`
- Private email/phone only with `admin.events.export_private_contact` + `include_private_contact=true` + reason
- Finance depth requires `admin.finance.export_event_sales` + reason
- Formats: CSV (streamed) · JSON · XLSX returns 400
- Every successful export is audited (`admin_event_buyers_exported` / `_private_contact_` / `_finance_`)
- Never includes QR payloads, Paystack/provider refs, hidden venue/private address, vault/Fan Connect secrets

See [TICKETS.md](./TICKETS.md) · [API.md](./API.md) · [PRIVACY.md](./PRIVACY.md).

## Admin event buyer export

Platform tool for one event’s issued tickets (buyers / checked-in attendees).

| UI | API |
|---|---|
| `/admin/events/[id]/buyers` | `GET /api/v1/admin/events/{event_id}/buyers` |
| `/admin/events/[id]/attendees` | same list + `checked_in=true` |
| `/admin/events/[id]/exports` | `GET …/buyers/exports` (+ start export from Buyers) |
| Export download | `GET …/buyers/export?format=csv\|json&mode=…` |

**Permissions:** `admin.events.view` + `admin.events.export_buyers`. Private email: `admin.events.export_private_contact` + reason. Finance mode: `admin.finance.export_event_sales` + reason. Hosts cannot use these admin routes.

**Modes:** `public_summary` · `operations` (default; public + ops, no private contact) · `finance`.

**Always audited** (`admin_event_buyers_exported` / `_private_contact_exported` / `_finance_exported`). CSV is streamed with injection protection; XLSX unsupported.

Details: [TICKETS.md](./TICKETS.md#admin-event-buyers--attendees--exports) · [API.md](./API.md) · [PRIVACY.md](./PRIVACY.md).

## Finance (fees, earnings, platform revenue)

Canonical docs: [FINANCE.md](./FINANCE.md) · [HOST_EARNINGS.md](./HOST_EARNINGS.md) · [PAYOUTS.md](./PAYOUTS.md) · [PAYMENTS.md](./PAYMENTS.md).

| UI | Purpose |
| --- | --- |
| `/admin/finance` | Finance hub |
| `/admin/finance/fees` | Global fee schedules |
| `/admin/finance/host-overrides` | Per-host fee overrides |
| `/admin/hosts/[hostId]/fees` | Host-scoped overrides + preview |
| `/admin/finance/earnings` | Host earnings overview + drill-down |
| `/admin/hosts/[hostId]/earnings` | Single-host earnings |
| `/admin/events/[id]/earnings` | Event earnings |
| `/admin/finance/platform-revenue` | Platform ledger + revenue report + CSV |
| `/admin/ledger` | Host ledger + settlement |
| `/admin/payouts` | Payout review / mark paid |
| `/admin/refunds` | Refund review |

**Help copy (admin):**

- Buyer platform fee is paid by the buyer.
- Host commission is deducted from host earnings.
- Fee settings can differ by host.
- Order fee snapshots preserve the fee terms used at the time of sale.

**Permissions:** `admin.finance.view_fees` / `manage_fees` / `manage_host_overrides` / `export_event_sales`; `payouts.review`; mark paid = **super_admin only**. Support is blocked from ledgers, settlement, earnings, platform revenue, fee management, and payout completion.

**Exports** (platform revenue + host earnings CSV) are audited. Never expose raw Paystack payloads or full payment secrets.

## Other admin surfaces

Audit logs, refunds, payouts, merch moderation, message reports, Fan Connect reports, CMS, taxonomy — see [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).
