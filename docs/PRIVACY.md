# Privacy (product index)

How Pàdéyá keeps contact data, payments, private venues, and locked content out of public and peer surfaces.

**Browser storage:** public route `/cookies` · internal inventory [COOKIES_AND_STORAGE.md](./COOKIES_AND_STORAGE.md).

## In-app messaging

- Fan ↔ host by default. Fan ↔ fan only after **Fan Connect** mutual accept (`fan_fan` threads).
- Serializers omit email, phone, WhatsApp, bank/payment links, order/payment IDs, private street addresses, locked Vault bodies, and CRM notes.
- Related-event chips expose `id`, `title`, `slug`, `path`, optional `banner_url` only — never venue address or `location_visibility` secrets.
- Notifications use generic copy (“You have a new message.”) — not full message bodies. Attachment notices never include file contents or private download URLs.
- **Attachments:** public allowlist only (`id`, `url`, `content_type`, `byte_size`, `original_filename`, dims, `status`). Never `storage_key`, filesystem paths, checksums, EXIF/GPS, or uploader internals. Files are private (not under `/media`); downloads require auth + thread membership.
- **WebSocket:** participant-scoped bodies; Redis envelopes sanitized (`ws_sanitize.py`); typing payloads use safe display names only; admins do not join private threads by role alone.
- **Chat features privacy:**
  - **Reply previews** — same-thread only; sanitized; hidden/deleted/delete-for-me → unavailable placeholder (no storage paths / contact fields)
  - **Pins** — shared in-thread; hidden/deleted messages drop from the public pin list (soft unpin)
  - **Stars** — personal to the viewer (`is_starred` viewer-scoped); peer never sees or is notified; inaccessible threads omitted from starred list
  - **Edit history** — stored in `message_edits` for audit; not exposed as a participant history UI
  - **Inbox preview** — redacts hidden/deleted last messages; search never ILIKE-matches hidden/deleted bodies
- Block + report; admins review reported threads only (audited hide/restore + attachment moderation; report-scoped).
- Host **owners** cannot message their **own** host from Personal ([HOST_AS_FAN.md](./HOST_AS_FAN.md)).
- Demo seed enforces safe copy via `app/demo/messaging_privacy.py`.

Details: [MESSAGING.md](./MESSAGING.md) · [SECURITY.md](./SECURITY.md#in-app-messaging-privacy) · [DEMO_DATA.md](./DEMO_DATA.md).

## Host recommendations (fan)

- Rules-only scoring for signed-in fans; no LLM re-ranking.
- Reason chips use fixed public copy (`REASON_LABELS`) — never ticket tier, spend, VIP/table, private venue address, Vault bodies, message content, or other fans’ names.
- Impression rows store host id, surface, position, score, and reason **codes** only — not page context or financial data.
- Admin debug is `admin.full_access` only.

Details: [HOST_RECOMMENDATIONS.md](./HOST_RECOMMENDATIONS.md).

## Event recommendations (fan)

- Same rules-only model as host recommendations; fixed `REASON_LABELS` in `backend/app/events/recommendations/constants.py`.
- Social reasons use aggregate copy (“Popular with fans you’re connected to”) — never named peers unless future product explicitly allows it.
- Impression/feedback rows exclude message content, spend, and exact GPS.

Details: [EVENT_RECOMMENDATIONS.md](./EVENT_RECOMMENDATIONS.md).

## Fan Connect

- Discoverability defaults **on** (`fan_connect_enabled`, `allow_connection_requests`, `discoverable_for_same_events`, `discoverable_for_similar_interests`, `show_public_city` default true; fans can disable anytime). `request_policy` defaults to `same_event`.
- `/fans` directory visibility is **separate** — directory alone never enables Connect.
- Target must have a **public** Passport; private / unlisted / admin-hidden fans are never suggested.
- **Self-actions denied:** users cannot Connect with, message, follow, report, or block themselves; self is excluded from suggestions and connection counts.
- Shared context uses public-safe attendance / hosts / categories / dual-opt-in city / public badges only — never private events, hidden venues, ticket types, VIP/table, orders, payments, spend, or locked Vault.
- Safe reason codes only (`shared_upcoming_event`, `shared_checked_in`, `shared_public_event`, `shared_host`, `shared_category`, `shared_city`, `shared_badge`).
- Chat (`fan_fan`) unlocks only after accepted connection; remove/block disables messaging **and attachments** (`can_attach` false).
- Connect reports ≠ message reports; admins do not browse unreported `fan_fan` threads or private attachment stores.

Details: [FAN_CONNECT.md](./FAN_CONNECT.md).

## Admin event buyer export

- Default export (`operations`) is public profile + operational ticket fields — **not** private contact and not a full finance dump.
- Email/phone only with `admin.events.export_private_contact` + non-empty `reason` (`include_private_contact=true`).
- Finance-depth columns only with `admin.finance.export_event_sales` + reason (`mode=finance`).
- Visibility-gated passport fields (`avatar_url`, `public_bio`, passport URL) only when the Fan Passport is publicly reachable; city/country/social columns stay empty until those public fields exist on passport.
- **Never** exported: QR secrets/jti, Paystack raw refs/payloads, passwords, hidden venue/private address, device_binding, Fan Connect graph, private messages, vault secrets.
- Every successful download is audited (mode, filters, row count, reason when required).

Details: [TICKETS.md](./TICKETS.md#admin-event-buyers--attendees--exports) · [ADMIN.md](./ADMIN.md#admin-event-buyer-export).

## Fan Passport

- Default visibility **public** with `appear_in_directory=true` on signup; fans can go private/unlisted or leave the directory anytime. Directory still requires `public` + `appear_in_directory`.
- Public / directory serializers never expose email, phone, amounts, hidden venues, or locked Vault content.
- Users may **view and share** their own public Passport; own page shows Edit / Personal dashboard / Share instead of Connect / Message / Follow / Report / Block.
- Self Connect, Message, Follow, Report, and Block are denied server-side (same user id).

Details: [FAN_PASSPORT.md](./FAN_PASSPORT.md) · [SECURITY.md](./SECURITY.md#fan-passport-privacy).

## Host-as-Fan

- Hosts remain Personal/Fan users and may fan **other** hosts normally.
- Own-host owner blocks: checkout, public reviews, Personal fan messaging, follow, and (by default) ambassador commission on own campaigns.
- Self-referral commission remains blocked for every actor.
- Test/admin/demo flows must not inflate Legacy, discover, or trust metrics.

Details: [HOST_AS_FAN.md](./HOST_AS_FAN.md) · [CHECKOUT.md](./CHECKOUT.md) · [REVIEWS.md](./REVIEWS.md).

## Event location

- Private streets, exact geo, and private join URLs redacted at serialize time for public access.
- Access levels: public · buyer · host · admin — never trust the client for reveal.

Details: [SECURITY.md](./SECURITY.md#event-location-privacy-event-studio) · [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md).

## Admin event buyer export

- Default list/export excludes buyer/holder email and phone; private contact is opt-in with `admin.events.export_private_contact` + reason.
- Public profile fields respect Fan Passport visibility (private profiles do not leak bio/avatar URLs in `public_summary`).
- Never exported: QR tokens/secrets, Paystack/provider refs or raw payloads, passwords, Fan Connect graph, private messages, vault secrets, hidden venue / private street address.
- Successful exports append audited `audit_logs` rows (mode, filters, row count, reason, IP, user-agent).

Details: [TICKETS.md](./TICKETS.md) · [ADMIN.md](./ADMIN.md) · [SECURITY.md](./SECURITY.md).

## Vault

- Locked public views omit `body`, private media URLs, and invite codes.
- Unlock only after verified payment webhook (or server free/demo finalize).

Details: [VAULT.md](./VAULT.md).

## Event merch

- Public catalog, storefront (`/u/{username}/merch`), and unpaid buyer rows never expose private/hidden venue streets, buyer email/phone, payment secrets, or desk-only fulfillment notes.
- **Shipping privacy:** full street, phone, and delivery notes are encrypted at rest; never returned on public APIs, analytics, reviews, badges, or abandoned-cart payloads. Buyers see city/state/country (+ status/tracking) only; host fulfill staff may decrypt ship-to for shipping lines.
- **Desk pickup:** scan responses null buyer email / shipping / QR token; decrypt requires owner or `merch.manage_shipping` — [MERCH.md](./MERCH.md#host-team-desk).
- Vault-exclusive merch returns teasers when locked — never Vault body, media URLs, or invite codes.
- Merch messaging context uses product name snapshots only — no contact leakage.
- Notification copy uses event/product names (or badge name for `merch.badge_earned`) only — no amounts or Paystack refs in body text.
- Verified product reviews use Passport-safe author labels; hosts cannot delete reviews.

See [COMMERCE.md](./COMMERCE.md) · [MERCHANDISE.md](./MERCHANDISE.md#privacy-rules) · [SECURITY.md](./SECURITY.md#event-merch).

## Host team

- Invite tokens stored as **hash only**; accept requires matching email / `invited_user_id`; list/preview APIs never return raw tokens.
- **Username invites:** host sees display name, `@username`, public avatar, status only — **not** account email, phone, or private Passport data. Delivery still uses the internal account email.
- Ticket desk: no holder email/phone/payment refs — name, public code, type, status only ([TICKETS.md](./TICKETS.md#privacy-at-the-door)).
- Merch desk: no buyer email/shipping/payment refs on scan; shipping decrypt gated.
- Team audit feed: sanitized metadata only (no secrets, tokens, bank/Paystack refs; username invites omit email).
- Payouts/bank remain owner-only in v1; CRM private notes and Fan Connect graphs stay off host-team routes.
- Suspended/removed members lose desk access immediately.

Overview: [TEAMS.md](./TEAMS.md#privacy--username-invites) · [SECURITY.md](./SECURITY.md#host-team-privacy).

## Ambassadors

Open participation lets eligible users promote events — they still see **attribution metrics only**. Never: buyer contact data, attendee lists, ticket/merch QRs, payment or order IDs, hidden venues, shipping addresses, Fan Connect graphs, or host-team data.

Allowed: clicks, verified sales counts, eligible sales totals, estimated commission + status, timestamps, campaign/event/merch names (and public slugs for share links).

Click / fraud analytics store **hashed** IP and user-agent only (salted with `secret_key`). Raw IPs are never persisted on Ambassadors click tables — same policy as [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md). Email/push Ambassadors templates use event/campaign names only (no buyer PII).

**Hosts / team conversion ledger** may see ambassador identity, campaign, timestamps, eligible amount, commission, status, payout status, and optional host payout meta (`payout_reference` / `payout_note`). They must **not** see buyer email/phone, full order/payment refs, attendee lists, ticket/merch QRs, hidden venues, shipping addresses, or Fan Connect graphs.

Enforcement: `app/ambassadors/privacy.py` allowlist + self DTOs without `order_*` fields. Host `serialize_conversion(..., include_order_refs=False)` by default; admin oversight lists may include order refs. Reward status changes and flags are audited without storing buyer PII.

Details: [AMBASSADORS.md](./AMBASSADORS.md#privacy-phase-13) · [SECURITY.md](./SECURITY.md#ambassadors-privacy) · fraud: [AMBASSADORS.md](./AMBASSADORS.md#fraud-controls-phase-14).

## Analytics

- Host/admin analytics scrub emails, phones, raw IPs, and private venue fragments.

Details: [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md).

## Admin user management

Support/super-admin access to platform users is **internal-only** and permission-gated (`admin.users.*`). Guarantees:

- **Safe fields only** — admin APIs never return passwords, hashes, or tokens; admin list/detail show the **real email**; `email_masked` remains available as a secondary field
- **Private contact** — email on admin users is always visible (audited); phone / extended private fields still require `admin.users.view_private_contact` when present
- **Notes & flags** — internal; **never** shown to the end user; audit rows omit note/flag bodies
- **Selective restrictions** — admin `reason` / `internal_note` stay admin-only; `/me` exposes **keys only**; end-user UI uses a generic message (“This action isn’t available on your account.”); audit stores `internal_note_present` boolean, never the note text
- **Status / security actions** — reason-required; force password-reset notifies the user of a reset email only (not of admin notes/flags/restrictions)
- **Routes:** `/admin/users`, `/admin/users/[userId]` (Restrictions tab)

Details: [ADMIN.md](./ADMIN.md#user-management-safe-actions) · [SECURITY.md](./SECURITY.md#admin-user-management) · [API.md](./API.md#admin-user-management-safe-actions).

## Admin user impersonation

**Internal support/QA** may view the product as a user under a fully **audited** impersonation session. Guarantees:

- **Internal and audited** — not a customer-facing alert flow; admin audit + session logs only
- **Target user is not notified** — no email, in-app, or push
- **No password access** and **no hijack** of the user’s live refresh session
- **Admin / session separation** — effective user is the target; actor admin is recorded separately for audit
- **Sensitive actions blocked** (including Passport privacy settings mutations); FE locks Passport settings UI during the session
- **Max duration** 60 minutes (default 30); permission `admin.users.impersonate` required
- **Audit logs retained** — actor admin, target, reason, ticket (if any), start/end/expiry, routes/actions, blocked sensitive actions

Details: [SECURITY.md](./SECURITY.md#admin-user-impersonation) · [AUTH.md](./AUTH.md#admin-user-impersonation) · [ADMIN.md](./ADMIN.md#user-impersonation).

## Demo data

Local seed must never put contact/payment/private venue/Vault secrets into messages or notification summaries. See [DEMO_DATA.md](./DEMO_DATA.md).

## Transactional email

- Ticket/merch emails: public codes + CTA only — never full Paystack references, hidden venues, or private streets.
- Messaging / Fan Connect emails: generic copy only — no message bodies or attachment URLs.
- Shipping address only on the buyer’s own merch confirmation when the flow requires it.
- Admin outbox hides body preview in production.
- Full rules: [EMAILS.md](./EMAILS.md), [EMAIL_AUDIT.md](./EMAIL_AUDIT.md).

## Browser push + in-app alerts

Push and toast payloads must stay public-safe. Never include:

- Private chat bodies or attachment / download URLs
- Hidden venues, private streets, private join URLs
- Payment / Paystack / order references
- Full pickup or entry codes
- Shipping addresses, phone numbers, emails
- Locked Vault content
- Fan Connect graphs or private attendee lists

Enforcement: context whitelist + scrub in `app/push/privacy.py`, wire `PushPayload` whitelist, service worker `ALLOWED_PUSH_KEYS` (`public/sw.js`). Messaging default: “You have a new message on Pàdéyá.” Opt-in `push_message_previews` may use the sender display name only — never full chat text. Action URLs are same-origin relative paths; Vault/checkout deep links are rejected.

Details: [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md#privacy-rules) · [NOTIFICATIONS.md](./NOTIFICATIONS.md) · [SECURITY.md](./SECURITY.md#pwa--offline-phase-18).

## Sponsor profiles

- Public sponsor pages expose only verified, admin-approved fields (name, logo, industry/categories, safe description, website when verified) plus **aggregated public partnership data**: approved `public_case_study` campaigns, active/completed placements on **listed** events with **active** hosts, deliverable **labels** only (no proof URLs unless explicitly public later), partnered host cards, and location/category chips. Placeholder/Acme demo artwork is not used as hero cover (`use_cover_fallback`).
- **Never public:** private budget (unless a future explicit public flag), invoice/payment data, sponsor team, internal admin notes, draft/private campaigns, unlisted/private events, suspended hosts, private inquiries, fan/attendee/buyer data, unreleased contact details.
- Public **campaign_goals** and summary cards use human-readable partnership labels on the profile API — not raw workspace budget fields.
- Sponsors **cannot** message or blast fans without an approved host/channel; marketplace inquiries stay host-mediated.
- Logged-in sponsor inquiries link to the sponsor profile FK; hosts see sponsor type/verification on inquiry records — not fan private data.
- **Sponsorship deals:** notifications and APIs expose deal title, status, and safe amounts only — never attendee lists, buyer PII, fan names, or raw Paystack webhook payloads (admin UI included).
- **Deliverables:** proof URLs and titles only; no fan/attendee/buyer fields; sponsors cannot edit host proof metadata.
- Campaign recommendation reasons are fixed labels only (category, location, budget, verified host, activity) — never attendee names, buyer spend, or private venue data.
- Sponsor reports return counts and aggregates only (inquiries, campaigns, placements, public-safe reach) — no fan names, buyer contact fields, or ticket-level spend.
