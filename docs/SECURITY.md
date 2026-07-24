# Security

## Secrets

Use environment variables only (`backend/.env.example`). Never commit real keys.

- Paystack API keys stay server-side only (never sent to buyers). Admins may manage them under **Payment integration** (Fernet-encrypted + masked; env fallback). JWT `SECRET_KEY` and **`AI_API_KEY`** stay `.env` only
- Never expose AI provider keys to the frontend or client bundles
- Non-development `APP_ENV` **refuses to start** if `SECRET_KEY` is weak/default or shorter than 32 characters
- Boot-critical Class A (`DATABASE_URL`, `SECRET_KEY`, `EMAIL_SETTINGS_ENCRYPTION_KEY`, QR signing, etc.) is **never** admin-editable — see [ENVIRONMENT.md](./ENVIRONMENT.md)

## Admin Runtime Settings

Allowlisted Class B overrides in `runtime_settings`. Not a raw `.env` editor.

| Rule | Behavior |
|---|---|
| Class A | `.env` / `Settings` only; status configured/missing at most — never raw values |
| Class B | Editable with `admin.settings.edit_runtime`; DB override → env → default |
| Paystack | Secret + webhook encrypted in `runtime_settings` (`edit_secrets`); public key + base URL editable; checkout/webhook resolve via `paystack_runtime(db)` |
| Class C specialists | Email SMTP / push VAPID stay on specialist tables; unified UI links/adapters only |
| Secret display | `Configured · ending in ####` or `Not configured` — **no reveal** |
| Secret write | Blank/omit keeps existing; clear override → env/default |
| Permissions | `admin.settings.view` · `edit_runtime` · `edit_secrets` · `test_integrations` · `view_system_status` · `clear_overrides` · `view_audit` |
| Audit | `runtime_setting_updated` · `runtime_secret_replaced` · `runtime_setting_cleared_to_env` · `runtime_setting_tested` · `runtime_setting_validation_failed` · `runtime_setting_viewed_sensitive_status` |
| Startup | Must not depend on DB `runtime_settings`; optional features degrade when unconfigured |

See [SETTINGS.md](./SETTINGS.md) · [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md) · [ADMIN.md](./ADMIN.md).

## Auth

- bcrypt passwords, JWT access + hashed refresh rotation
- RBAC via roles/permissions
- Admin impersonation is a **separate** short-lived access token — see below and [AUTH.md](./AUTH.md)

## Admin user management

Platform user directory and safe lifecycle actions on `/admin/users` and `/admin/users/[userId]` (API `/api/v1/admin/users*`). Product: [ADMIN.md](./ADMIN.md#user-management-safe-actions).

| Rule | Behavior |
|---|---|
| **Safe fields only** | List/detail scrubbed — **no** passwords, hashes, reset/access/refresh tokens, OAuth/2FA secrets, QR/payment payloads, or private message bodies. **Email is always the real address** on admin users; `email_masked` is secondary |
| **No password / token reveal** | Force password-reset emails a link; force logout revokes sessions; neither returns raw secrets |
| **Hard delete blocked** | Soft status transitions only (`active` / `under_review` / `restricted` / `suspended` / `banned`, …); `DELETE` → 405 |
| **Flags** | Catalog `flag_type` + severity; soft-close `resolved`/`dismissed`; audited |
| **Notes** | Append-only internal notes; never shown to the user; audited without body in `audit_logs` |
| **Selective restrictions** | Primary moderation: `user_restrictions` history rows; reason required; cannot restrict self; normal admin cannot restrict `super_admin` / platform admins; enforcement via `assert_no_restriction` (403) |
| **Full suspension** | Preset-only path (`preset=full_suspension`) → major restriction rows + `account_status=suspended`; product APIs blocked; login allowed only for appeal / me / auth; not the day-to-day default |
| **Suspension notify + appeals** | On suspend: in-app + email (if present) + push (if enabled); public category/duration/date only. User may appeal; admin `/admin/appeals` approve (unsuspend) or reject (optional reply). Audited |
| **Status changes** | Reason required; writes `admin_user_status_changed`; global statuses win over `restricted` |
| **Audit logs** | `admin_user_viewed`, `admin_user_private_contact_viewed`, `admin_user_note_created`, `admin_user_flag_*`, `admin_user_status_changed`, `admin_user_restriction_*`, `restricted_user_blocked_from_action`, `admin_user_force_logout`, `admin_user_force_password_reset`, `admin_user_suspension_notified`, `account_appeal_*`, `admin_user_unsuspended` |
| **Permissions** | Granular `admin.users.*` (+ `admin.appeals.review`). Finance has **no** default access; support defaults to view + notes (+ appeal review) |

## Admin user impersonation

**Internal support/QA sessions** — audited temporary view as a user. **Not** a real login. The target user is **never** notified (no email, in-app, or push).

| Guarantee | Behavior |
|---|---|
| **Internal and audited** | Support/QA only. Events: `admin_impersonation_started` / `_ended` / `_expired` / `_sensitive_action_blocked` / `_request_made`. Dual-write to `admin_impersonation_audit_logs` + `audit_logs`; no bodies/secrets. |
| **Target user is not notified** | No email · no in-app · no push |
| **No password access** | Passwords never read, returned, or shared |
| **No session hijacking** | Target refresh tokens are **not** reused, revoked, or rotated; impersonation token has **no refresh** |
| **Sensitive actions blocked** | See [Blocked / allowed during impersonation](#blocked--allowed-during-impersonation). Exact 403: `This action is disabled during admin impersonation.` |
| **Max duration** | `15` / `30` / `60` min; **default 30**, **max 60**; auto-expire; one active session per admin |
| **Permission required** | `admin.users.impersonate` only — `super_admin` (via `admin.full_access`); support/finance **only** with explicit grant. Buyers / host owners / host staff never. |
| **Admin / session separation** | `current_user` = target; `actor_admin_id` + `impersonation_id` separate (`GET /me/session`); admin tokens stashed client-side; admin perms **never** leak; `/admin` blocked while impersonating |
| **Audit logs retained** | Actor admin, target user, reason, support ticket ID (if provided), start time, end time, expiry, visited routes/actions, blocked sensitive actions. Retained for demo seeds too. Admin banner only. Fields: `impersonation_id`, `actor_admin_id`, `target_user_id`, `action`, `path`/`route`, `method`, `reason`, `support_ticket_id?`, `ip`/`ua`/`created_at`. No request bodies or secrets. |

| Rule | Behavior |
|---|---|
| Token | Separate short-lived **impersonation access token**. Admin session stays stashed — not permanently replaced |
| Session | Each request validates active + unexpired DB session; JWT role claims are informational — RBAC uses target DB perms only |
| Expiry & safety | Auto-expire on timeout; end on Exit / logout; end if admin or target account is disabled mid-session; no nested impersonation; one active session per admin (must end first) |
| Claims | `actual_user_id`, `actor_admin_id`, `impersonation_id`, `is_impersonating`, `started_at`, `expires_at`, `reason`, `support_ticket_id` (+ target-only `roles` / `permissions`) |
| Allowed while impersonating | View dashboard/tickets/orders/merch/refunds/settings/Passport/Vault; reproduce navigation; exit via `POST /admin/impersonation/end` |
| Start form | Required reason + confirmation; optional support ticket ID + duration |
| Session lifecycle | Default **30** min / max **60**; auto-expire; end on Exit; end on logout; no nested impersonation; `/admin` blocked; admin perms never leak |
| Blocked targets | Self; `super_admin`; `support_agent` / platform admins (`admin.full_access`); `finance_admin`; security-locked users; deleted / banned accounts; suspended/inactive unless **super_admin** with reason |
| Persistence | `admin_impersonation_sessions` + `admin_impersonation_audit_logs` (migration `20260720_0089`) |
| Demo / seed | Seed accounts log in normally; fans/hosts/buyers with `@demo.padeye.test` remain impersonatable when permitted; banner shows **Demo seed account** + **Audited session** |
| Host-as-Fan rules | Impersonation does **not** bypass own-host **owner** checkout / follow / review / messaging / commission guards. Team/staff may still buy as fans. No production bypass. Live Paystack must not be used for owner own-host tests. A separate local test-order helper (if added later) must be explicit and excluded from public metrics. |
| API | `POST /admin/users/{id}/impersonation/start` · `GET /admin/users/{id}/impersonation/history` · `POST /admin/impersonation/end` · `GET /me/impersonation` · `GET /me/session` · `GET /users/admin/{id}` · `GET /users/admin/lookup?email=` |
| UI | `/admin/users` — UUID or email lookup; `/admin/users/[userId]` — **Impersonate user** modal (reason, duration, ticket, confirm) + history; global banner while active (full target email, admin, time remaining, Exit) — desktop/mobile, light/dark |

### Blocked / allowed during impersonation

Enforced by `app.admin.impersonation_guards` + middleware. Exact 403 detail: `This action is disabled during admin impersonation.`

**Blocked**
- Changing password, email, phone; enabling/disabling 2FA; deleting account
- Changing payout / bank details; requesting payouts; all finance mutations
- Buying tickets/merch with real payment; creating checkout payment attempts; cart checkout path
- Transferring tickets; deleting user content
- Changing Passport privacy settings
- Connecting / disconnecting social accounts (incl. Fan Connect)
- Changing API keys / provider keys
- All admin routes; support-queue actions

**Allowed**
- Viewing dashboard, tickets, orders, merch, refunds
- Viewing Passport / Vault pages and settings safely (read-only)
- Reproducing UI / navigation issues
- `POST /admin/impersonation/end` (exit)

See [ADMIN.md](./ADMIN.md#user-impersonation) · [AUTH.md](./AUTH.md#admin-user-impersonation) · [PRIVACY.md](./PRIVACY.md#admin-user-impersonation).

## Admin event buyer export

- Base: `admin.events.view` + `admin.events.export_buyers` (hosts/buyers → 403 on admin routes)
- Private contact: `admin.events.export_private_contact` + required reason
- Finance mode: `admin.finance.export_event_sales` + required reason
- CSV cells neutralize formula injection (`=`, `+`, `-`, `@`); streaming response; max 10 000 rows
- Audit actions: `admin_event_buyers_exported`, `admin_event_buyers_private_contact_exported`, `admin_event_buyers_finance_exported` (ip/user-agent when available)
- Never export QR/jti, provider payloads, passwords, private venue/address, device_binding

See [TICKETS.md](./TICKETS.md#admin-event-buyers--attendees--exports).

## Admin event buyer export

- Gate: `admin.events.view` **and** `admin.events.export_buyers` (hosts/normal users → 403; host exports stay separate)
- Elevated: `admin.events.export_private_contact` (email/phone) and `admin.finance.export_event_sales` (finance mode); both require a non-empty reason
- CSV formula-injection neutralization for cells starting with `= + - @`; stable column allowlist; no QR/`jti`/Paystack/venue columns
- Streaming CSV download; max row safety cap; audit every success with IP + user-agent

See [TICKETS.md](./TICKETS.md) · [ADMIN.md](./ADMIN.md) · [PRIVACY.md](./PRIVACY.md).

## Payments

- Do not trust frontend payment success
- Verify Paystack webhook signatures
- Idempotent webhook processing
- Tickets issued only after verified payment finalize
- Merch inventory and pickup fulfillments created only after verified payment finalize (never from the browser)

## Event merch

- Shipping addresses encrypted with `encrypt_sensitive`; never in public serializers, analytics, or badge meta
- Merch pickup QR uses `typ=padeya.merch.pickup` — ticket QR types are rejected at the merch desk scan endpoint
- Vault-exclusive merch returns teasers only when locked; no Vault content leaks
- Money truth: inventory commit, merch discount redemptions, POD jobs, append-only revenue splits, and Fan Passport merch badges run only after verified Paystack webhook finalize (idempotent). Abandoned carts never invent paid state.
- POD is **provider-ready** (manual jobs + placeholder Printful/Printify providers). Live carrier / Printful sync is not required and not claimed as shipped.

Full product rules: [MERCHANDISE.md](./MERCHANDISE.md) · [COMMERCE.md](./COMMERCE.md).

- Pickup codes (`MRCH-*`) are **desk identifiers** for collecting goods — not payment secrets and not substitutes for signed ticket QR
- Public catalog / storefront expose only sellable (or teaser) products; drafts/paused/archived stay host-only; `hidden`/`removed` moderation never public or purchasable
- Merch pickup copy respects event location privacy — private venue streets are not exposed in public catalog or unpaid `/merch/mine` / `/dashboard/merchandise` rows; post-purchase detail still honors address reveal rules
- Merch APIs do not expose buyer email/phone, payment IDs/card data, private order secrets, or host private contact; `fulfillment_notes` are desk-only
- Product reviews: verified paid purchase only; hosts cannot delete (API returns 403); admin hide/restore audited
- Notification bodies include event/product names (or badge name) only — never Paystack refs, amounts, or card data
- Messaging may attach `related_merch_order_item_id` + system context (`This conversation is about {product}.`) — serializers still scrub contact
- Listing create/update blocks off-platform payment links, contact extraction, and basic banned product terms; buyers can report; admins moderate via report queue
- All merch payments stay inside Pàdéyá checkout (no external payment links in listings)
- Permissions:
  - Host (`merch.manage_own` + event ownership): catalog/pricing, orders, fulfill, discounts, size charts, storefront, POD manual
  - Host staff (`merch.fulfill` / `merch.view_fulfillment` + event assignment or scan): desk only — **not** product/pricing edit
  - Buyer: own purchases (`/merch/mine`, `/dashboard/merchandise`); checkout eligibility server-side; report listings; own reviews
  - Admin (`merch.moderate` / `merch.view_admin`): moderate/hide/reports/reviews; order views omit payment amounts, Paystack refs, payment IDs
  - Support (`merch.view_admin` only): support visibility — **no** `merch.moderate`, **no** ledger/refund approve
- Moderation (`merch.moderate`) is audited; hide/archive/restore require a reason
- Admin-hidden merch is not public/purchasable; hosts see `moderation_status` + reason and cannot reactivate until restore
- Merch reports: `open` / `reviewing` / `resolved` / `dismissed` with product snapshot + admin notes

## Check-in (Phase 5)

- QR payloads are signed JWTs (`typ=padeya.ticket.qr`) — no plain ticket UUID
- Validate signature, event binding, and `jti` hash before check-in
- Ticket / merch desk scan is **hybrid**: host owner, **active** host-team member with matching permission + scope, assigned `event_staff_assignments`, or admin — [TEAMS.md](./TEAMS.md#hybrid-scan-authorization) · [HOST_TEAM.md](./HOST_TEAM.md)
- Suspended/removed team members lose desk access immediately (staff assignments deactivated; membership status hard-denies scan even with leftover staff rows)
- Host staff limited to assigned events; cross-host teams cannot scan another host’s events
- Scanner APIs return **minimal** attendee data (name, public code, ticket type, status) — never holder email/phone or payment refs (`DeskAttendeePublic`)
- Merch desk scan nulls buyer email / shipping / QR token; shipping decrypt gated on owner / `merch.manage_shipping`
- Duplicate scans logged and rejected; every attempt audited in `desk_scan_audit_logs`
- Refunded/cancelled/expired/invalid/transferred tickets rejected
- Admin override requires reason + audit log (`checkins.override`)

## Ambassadors fraud controls

- Self-referral blocked (buyer == ambassador user) at attach + finalize
- Host-owner commission blocked unless campaign `allow_host_owner_commission`
- Track-click / referral-click rate-limited (429)
- Click signals store salted IP/UA hashes only — never raw IP
- Suspicious click spikes write `ambassador_fraud_flags` for admin review (`/admin/ambassadors/fraud`)
- Hosts/team can flag a conversion (`POST /host/ambassadors/conversions/{id}/flag` → `suspicious_conversion`)
- Approve requires verified paid order; refunded/cancelled cannot mark paid; unverified cannot approve
- Reward status changes audited (`ambassador_reward_*` / `…_by_admin`) with actor type + old/new status
- Paused campaigns block new joins and new attribution
- Hosts can remove participants; admins can block participants / platform-block users
- Refunds and ticket cancels reverse commission (idempotent); FE success never creates commission
- Admin oversight (`POST /promos/admin/conversions/{id}/reward-status`) for fraud / platform campaigns / emergency — not required for normal host-owned approval

Details: [AMBASSADORS.md](./AMBASSADORS.md#fraud-controls-phase-14).

## Ambassadors privacy

Ambassadors are promoters — not buyers, desk staff, or host-team members.

- Self APIs (`/promos/ambassador/*`, `/ambassadors/me/*`) never return buyer email/phone, attendee lists, ticket/merch pickup QRs, payment refs, internal order IDs, hidden venues, shipping addresses, Fan Connect graphs, or host-team data.
- Sale rows for self use an allowlist (`app/ambassadors/privacy.py` → `AmbassadorSaleSelfPublic`): event/campaign name, unit counts, eligible sales total, commission + status, timestamps.
- Host conversion ledger (`serialize_conversion`) omits `order_id` / payment refs by default; still no buyer PII. Admin oversight may include order refs.
- Team reward permissions do not expand buyer/order visibility.
- Joining never grants host dashboard, scanner, or merch pickup access.

Details: [AMBASSADORS.md](./AMBASSADORS.md#privacy-phase-13) · [PRIVACY.md](./PRIVACY.md#ambassadors).

## Host team privacy

Full matrix: [TEAMS.md](./TEAMS.md#security--privacy-summary) · [HOST_TEAM.md](./HOST_TEAM.md#security--privacy) · [PRIVACY.md](./PRIVACY.md#host-team). Highlights:

- Invite tokens hashed (`token_hash`); accept requires matching email / `invited_user_id`; raw tokens never in list APIs
- Username invites: host APIs omit account email — show `@username`, display name, public avatar, status only
- Shipping addresses decrypted only for owner / `merch.manage_shipping`
- Payout and bank settings stay owner-scoped in v1 (FE + API)
- Team staff do not get CRM private notes or Fan Connect graph data via host-team routes
- Audit metadata sanitized (no invite tokens, secrets, bank/payment refs; username invites omit email)

## Advanced ticketing (Phase 17)

- **Transfers** reissue QR (`jti` rotation) so the previous owner’s payload cannot check in; actions write `ticket_transfers` + `tickets.transfer` audit
- **Rotating QR** uses short-lived signed tokens; scanners must validate the current `jti` hash (old rotations fail)
- **Device binding** stores a fingerprint hash only — not enforced at the door yet (placeholder)
- **Offline sync** is authenticated (`tickets.scan`); already-checked-in tickets surface as conflicts, not silent overrides
- **Cancellation** requires the actor’s account **password** (prevents accidental one-click cancel); revokes QR immediately; cancelled tickets fail validation like refunds and cannot be restored from the cancel action
- Existing Paystack finalize → issue → scan path remains unchanged for normal tickets

## PWA / offline (Phase 18)

- Service worker precaches **shell assets only** (icons, brand, `/offline`, manifest)
- **Never cache** `/api/*`, Vault routes, checkout, login/register, admin, or support via the SW
- Buyer ticket cache is **display-only** in `localStorage` (QR for the owner’s screen); door validation remains server-side
- Locked Vault body/content must not be stored for offline reading
- Offline scanner queues scans locally and syncs through authenticated Phase 17 offline sync — conflicts stay visible
- **Browser push is implemented** (`app/push` outbox + Web Push / log providers):
  - Permission only after the user clicks **Enable notifications** (never on page load)
  - User-facing kinds declare push eligibility in `app/notifications/channel_registry.py`; payloads use `app/push/templates.py` + `privacy.py` (no QR, payment refs, or chat bodies in push copy). Check-in success uses `ticket.checked_in` with event title + deep link only. Matrix: [NOTIFICATION_PUSH_AUDIT.md](./NOTIFICATION_PUSH_AUDIT.md)
  - VAPID private key Fernet-encrypted in `push_provider_settings`; never returned to clients
  - Subscription `p256dh` / `auth` encrypted at rest; inactive / 410 devices auto-deactivate
  - Wire + SW payloads are whitelisted/scrubbed — no chat bodies, venues, payments, codes, Vault, or attendee lists
  - Worker / Compose `push_worker` logs batch counts only
  - Details: [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md)
- Install prompt uses the browser `beforeinstallprompt` flow; no custom sideloading

## Verified reviews (Phase 6)

- Eligibility enforced server-side: checked-in ticket + event ended + one review per ticket/event
- Hosts cannot delete, edit, or hide reviews (DELETE always 403)
- Hosts may reply (`reviews.reply`) or report
- Moderation (`hide` / `restore`) requires `reviews.moderate` or `admin.full_access` plus a reason
- All create / reply / report / moderate actions write audit logs

## AI Copilot (Phase 15 + Phase 1 hardening)

- AI is **optional** (`AI_ENABLED=false` by default) and isolated from core commerce flows
- All model calls run **server-side** via the provider abstraction; frontend only receives suggestion text
- **Context redaction** (`app.ai.context_scrubber`): never send passwords, tokens, secrets, Paystack payloads, QR/ticket secrets, private venues (when `location_visibility` ≠ `full_public`), Vault bodies, private messages, admin/CRM notes, or buyer PII
- **Feature routing**: DB `ai_feature_routes` (primary/fallback/template per feature) + `AI_DISABLED_FEATURES`; kill switch `AI_KILL_SWITCH=1`
- **Admin AI Control Center** (`/admin/ai`, providers, features, usage, logs, safety, settings): multi-provider profiles, routing matrix, spend, safe logs
- **API keys**: Global `AI_API_KEY` env optional; per-provider keys may be stored Fernet-encrypted on `ai_provider_profiles` (same key as SMTP: `EMAIL_SETTINGS_ENCRYPTION_KEY`) — masked in UI, never returned in full
- Providers: DB `ai_provider_profiles` + abstraction (`template_fallback`, OpenAI-compatible, anthropic, gemini, grok)
- **Fallback chain**: primary profile → fallback profile → template (logged in `meta.provider_chain`)
- Audit: `ai.providers.*`, `ai.features.route_updated`, `ai.settings.*`, `ai.logs.viewed`, `ai.generation_*`
- Permissions: `admin.ai.view`, `admin.ai.manage_providers`, `admin.ai.manage_features`, `admin.ai.manage_safety`, `admin.ai.manage_spend`, `admin.ai.manage_settings`, `admin.ai.view_usage`, `admin.ai.view_logs`, `admin.ai.test_connection`
- **Output validation**: length bounds, banned overclaim phrases, private-data echo checks for Event Studio drafts
- Usage is logged in `ai_usage_logs` (feature, provider, fallback flag, tokens, latency/cost in `meta`) — never store API keys or raw unsafe prompts in logs
- Soft rate-limit (`AI_RATE_LIMIT_PER_HOUR`) per user
- When the provider is disabled/unavailable, return a template fallback draft (`used_fallback=true`) unless kill switch
- Permissions for product AI: `ai.use_own` (hosts), `ai.use_platform` (support/finance/admin)
- Responses set `requires_human_confirmation` from feature config (default true), `draft_only=true`, and forbid auto publish / auto send / finance writes
- Event Studio Basics: inline title/description generate applies to form fields only — never publishes the event
- Merch Studio Basics: inline title / description / category / tags (`host.merch.*`) — draft apply only; never auto-publishes or changes price/inventory/fulfillment/finance
- Merch categories constrained to controlled catalog (`MERCH_CATEGORY_SLUGS`); tags validated for safe length/charset
- Support ticket AI Assist (`support.ticket.*`) on `/admin/support/[ticketId]` and `/support/cases/[id]`: summarize, suggest category/priority, draft reply, suggest KB articles — **never** auto-sends, auto-closes, or changes status/refunds/payouts/moderation
- Support context built server-side from the ticket (public messages only by default); scrubber redacts emails/phones/payment refs/QR secrets; reply drafts reject refund/payment overclaims and blame language
- Help article suggestions may only pick from a server-built KB catalog (no invented URLs)
- Category/priority apply only after staff confirm (`PATCH …/category` / `…/priority`); Send reply remains manual
- Admin AI summaries (`admin.support.queue_summary`, `admin.analytics.revenue_summary`, `admin.reports.summary`, `admin.operations.daily_summary`) are advisory aggregates only — never moderate, refund, suspend, feature, hide, pay out, or message
- Admin summary context uses counts/titles/display names only; no buyer PII, payment payloads, Vault, QR secrets, or private venues
- Blog CMS AI (`admin.blog.*`) on `/admin/blog/new` and `/admin/blog/[postId]/edit`: title ideas, outline, excerpt, SEO meta, catalog tags, social snippets — **never** auto-publishes or sends social posts
- Blog context scrub excludes admin notes, secrets, private venues, tickets, payments, Vault, and private messages; outputs reject fake policy/legal overclaims
- Fan Passport bio AI (`fan.passport.bio`) on `/dashboard/passport/settings`: 2–3 draft bio options from public Passport fields + user notes only — **never** auto-publishes or changes visibility; blocked during impersonation (`POST /ai/fan/passport/generate`); respects `cannot_edit_passport` / read-only restrictions
- SEO apply confirms before overwriting existing slug/SEO fields; `admin.blog.publish` stays a separate manual action
- Permissions: `ai.use_platform` plus `admin.support.view` / `analytics.view_platform` / `reviews.moderate` / `admin.blog.edit` (or create) as scoped
- Phase 1 feature keys: `host.event.title`, `host.event.description`, `host.merch.title`, `host.merch.description`, `host.merch.category`, `host.merch.tags`, `support.ticket.triage`, `support.ticket.summary`, `support.ticket.reply_draft`, `support.ticket.priority`, `support.ticket.article_suggestions`, `admin.support.queue_summary`, `admin.analytics.revenue_summary`, `admin.reports.summary`, `admin.operations.daily_summary`, `admin.blog.title`, `admin.blog.outline`, `admin.blog.excerpt`, `admin.blog.seo_meta`, `admin.blog.social_snippets`, `admin.blog.tags`

## In-app messaging privacy

- Fan ↔ host by default. Fan ↔ fan only after Fan Connect accept (`fan_fan` threads) — no global random DMs.
- Serializers never expose email, phone, WhatsApp, order/payment IDs, private venues, or locked Vault bodies.
- Related-event chips are title/path/banner only — no street address or hidden venue fields.
- Hosts cannot message Directory-only fans without a follow/ticket/check-in/review/prior thread.
- Message requests for weak relationships; block + report supported; admin sees reported threads only.
- Settings `blocked_users` returns display names only (no emails/phones).
- In-app / email / push notifications use generic copy (“You have a new message on Pàdéyá.”) — not full bodies. Attachment notices never include file contents or private attachment URLs. Email uses `email_messages` preference; push uses `push_messages` (default **on**, away-only) + device subscription. See [NOTIFICATION_PUSH_AUDIT.md](./NOTIFICATION_PUSH_AUDIT.md).
- Transactional email: SMTP username/password via Admin → Email settings, Fernet-encrypted with `EMAIL_SETTINGS_ENCRYPTION_KEY` (`smtp_*_encrypted`). Active DB settings override env fallbacks. Never return/log decrypted secrets; audit records “SMTP password updated” only. Production fails loudly when provider=smtp without host/credentials. Payment webhooks enqueue only. See [EMAILS.md](./EMAILS.md).
- **WebSocket** (`WS /api/v1/messages/ws?token=`): JWT required on connect (close `4401` if invalid/expired). Message bodies and attachment URLs only to authorized thread participants; `attachment.ready` is uploader-only. Client may send `ping`, `typing.start/stop`, `message.read`, `thread.subscribe` after participant checks — **no** `send_message` or file upload over WS.
- **WS client reconnect:** FE refreshes tokens on auth close (`4401`/`1008`), exponential backoff otherwise; JWT in the query string is short-lived access only — never put refresh tokens on the socket URL.
- **WS permissions:** Enforced server-side on publish + delivery (`ws_permissions.py`). Blocked/closed/disconnected Fan Connect pairs cannot receive or emit active thread events. Admin roles cannot subscribe to private threads unless they are a party. Never rely on frontend checks alone.
- **WS multi-worker:** Redis pub/sub (`user:{id}:messages`, `thread:{id}:messages`) carries sanitized envelopes only (no email/phone/shipping/order/payment/private venue). If Redis is unavailable, in-memory fan-out is single-worker only (multi-worker **requires** Redis).
- **Attachments:** safe v1 allowlist (JPEG/PNG/WebP, PDF, text/plain, CSV, DOCX); reject SVG/HTML/ZIP/exec/scripts/unknown binaries and MIME mismatches; configurable caps (default images 5MB, docs 10MB, total 15MB, max 4); bind only uploader-owned unused IDs; moderated messages redact attachment URLs. Files are private (not under `/media`); downloads require auth + thread membership + `ready` status via `GET /messages/attachments/{id}` (or short-lived signed `?d=`).
- **Attachment file safety:** validates size, extension, MIME, magic bytes, SHA-256; sanitizes display filenames; storage keys are never user-controlled (path traversal rejected). Images verified with Pillow (dimensions; optional EXIF strip). PDFs/docs download as `attachment` disposition (not unsafe inline render). **Not antivirus-scanned in v1** — see `app/messaging/attachment_scan.py` (`MESSAGING_ATTACHMENT_SCANNER=noop`; ClamAV hook reserved).
- **Attachment permissions:** follow message send rules. Blocked users cannot upload/send files. Fan↔fan requires accepted Fan Connect. **No attachments in message requests** until accepted. Admins download attachments only for reported threads (`admin.full_access` + existing `message_reports` row) — not a private-attachment browser.
- **Attachment privacy:** serializers/WS allowlist via `attachment_privacy.py` — no storage keys, local paths, checksums, rejection internals, or EXIF/GPS. Signed download URLs only for the authorized viewer. Contact, private venue, and payment/order fields stay denylisted in `ws_sanitize.py`.
- **Attachment moderation:** admins act only on reported threads — hide / restore / soft-delete (`deleted_at`, storage retained) / mark reviewed; audited. Hiding a message also soft-hides its ready attachments. Participants never download `hidden`/`deleted` files.
- **Chat feature permissions** (`app.messaging.permissions`): fan↔host and fan↔fan gates unchanged; send/edit/pin/reply require open (non-blocked / non-closed / non-reported) access; fan_fan also requires accepted Fan Connect. Stars need read access only (personal). Replies validated same-thread + sanitized preview. Pins are shared; stars never fan out over WS.
- **Admin message hide/restore:** report-scoped (same gate as attachments) — UUID alone is not enough; audited; clears pins; does not use the participant edit path.
- Demo seed enforces banned substrings via `app/demo/messaging_privacy.py` (contact, payment, private address, locked Vault).
- See [MESSAGING.md](./MESSAGING.md), [PRIVACY.md](./PRIVACY.md), [DEMO_DATA.md](./DEMO_DATA.md).

## Fan Passport privacy

- Fan Passport visibility defaults to **private**; public/unlisted require explicit opt-in (`docs/FAN_PASSPORT.md`)
- Public `/api/v1/f/{username}` returns **404** for private or admin-hidden profiles (no existence leak beyond username guess)
- Unlisted profiles load by direct link only — they never appear on `/fans`
- **Fan Passport Directory** (`/fans` / `GET /api/v1/fans`) lists only `visibility=public` **and** `appear_in_directory=true` (opt-in). There is no global public list of every fan
- Public attended events omit amounts, ticket types, and hidden venues; secret/invite/unlisted events are excluded when `hide_private_events_always` is on
- Vault on public Passport exposes unlock **titles** only — never locked bodies or media URLs
- Directory / public serializers never expose email, phone, orders, payments, refunds, CRM segments, or locked Vault content
- Settings PATCH is always scoped to the authenticated user’s own passport
- Admin hide/restore of Fan Passports is audited (`passport.admin.hide` / `passport.admin.restore`)
- **Own Passport self-actions:** a user viewing their own public Fan Passport may edit, preview, and share — never Connect, Message, Follow, Report, or Block themselves. Ownership is `current_user.id === passport.user_id` (not username). Backend denies self Connect / Message / Follow / Report / Block with exact product copy (`You can’t … yourself.`). UI hides those CTAs on own Passport and own directory cards (`FanPassportSafetyMenu` returns null when own).

## Event location privacy (Event Studio)

- Private street addresses, exact coordinates, Google Maps place/share URLs, and online meeting URLs are stored for hosts but **redacted at serialize time** for public access (`app/events/privacy.py` + `maps.py`)
- When exact location is hidden, public maps may show **approximate** pins only (`approximate_*` or city centroid) — never the private street pin
- Access levels: `public` · `buyer` (paid ticket) · `host` · `admin` — never trust the client for reveal
- Public list/detail, hubs, breadcrumbs, Pàdéyá Picks, sitemap, and SEO/JSON-LD must never emit hidden street fragments, exact geo when unrevealed, or private join links
- FE mirrors with `lib/event-privacy.ts` and `lib/seo/event-metadata.ts` (`scrubPrivateAddress`); Studio preview must use the public location label
- Checkout questions: only **active** questions on public/checkout; answers are immutable order snapshots — archive questions that already have answers instead of hard-deleting
- Discard/hard-delete events only when draft/rejected **and** no ticket sales; ticket types with sales/holds must be deactivated, not deleted

## Product invariants

- Hosts cannot delete reviews
- Support cannot modify financial records (no refund approval, no payout review/completion, no host/platform ledger access, no fee management)
- Manual payouts require immutable evidence before `paid`
- Only **super admin** can mark payouts as paid
- Host `ledger_entries` and platform `platform_ledger_entries` are append-only (never edited/deleted in app code; corrections via adjustment / reverse entries)
- Paid payouts cannot be casually reversed
- Financial actions write audit logs (including fee CRUD and finance CSV exports)
- Checkout fees are calculated server-side; Paystack amount must match `order.total_amount`; fee snapshots are immutable
- Buyer checkout never receives host commercial terms; platform revenue APIs mask payment references and never return raw Paystack payloads
- **AI cannot** approve payouts/refunds, modify ledger/balances, publish events, or send announcements
- Public APIs must not leak hidden venue addresses or private online URLs

See [FINANCE.md](./FINANCE.md) · [PAYMENTS.md](./PAYMENTS.md) · [PAYOUTS.md](./PAYOUTS.md).
