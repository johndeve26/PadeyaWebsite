# Pàdéyá email audit

**Brand (user-facing copy only):** Pàdéyá  
**Do not use in email copy:** Padeya · Padéyá · Pàdéyé  
**Domain may remain:** padeya.com

This document is the product email map. It separates **historical baseline**, **what is implemented now**, and **remaining gaps**.

Do not add emails that are not listed here without updating this map.

---

## Before implementation (historical baseline — 2026-07-19 pre-work)

> **Not current status.** These bullets describe the codebase *before* the central email system shipped. Do not treat them as today’s truth.

| Piece | Then | Gap then |
|---|---|---|
| Delivery | `app/core/email.py` — log-only `EMAIL_PROVIDER=log` | No SMTP, no HTML templates, no outbox |
| Ticket email | Sync `send_ticket_email` inside Paystack finalize | Included order reference; not queued |
| Merch paid email | Sync plain text in `notify_buyer_merch_paid` | Host sale in-app only |
| Cart recovery | Opt-in via host `marketing_opt_in` | No platform preference model |
| Messaging / Fan Connect | In-app only (messaging email stub always off) | No prefs / outbox |
| Auth | Register/login only | No welcome / verify / reset email |
| Queue | Send inside webhook request | No `email_events` |
| Admin | None | No email event log / resend |

Exploratory audits that documented this baseline (now superseded by implementation):

- Existing email code inventory
- Auth / payments / merch trigger map
- Messaging / Fan Connect / sponsors / vault / reviews map

---

## Implemented now (current codebase)

| Piece | Status |
|---|---|
| Module | `backend/app/email/` (`service`, `queue`, `provider`, `templates`, `renderer`, `prefs`, `router`, …) |
| Migration | `20260719_0060` → `email_events` + `user_email_preferences` |
| Providers | `LogEmailProvider` + `SmtpEmailProvider` (ESP-ready protocol) |
| API | `enqueue_template` / `send_template` |
| Worker | `scripts/process_email_outbox.py` + in-process sweeper when queue enabled |
| FE | `/dashboard/settings/notifications`, `/unsubscribe`, `/email/preferences`, `/admin/emails` |
| Brand | Templates assert **Pàdéyá**; domain `padeya.com` allowed in footer/from |

**Critical invariant (still enforced):** ticket/merch purchase emails are enqueued only after verified Paystack finalize (`payments/webhook.py` → `finalize_successful_payment`). Never on client “payment success”.

**Privacy fix shipped:** ticket bodies use public codes + CTA — not `order.reference`.

**Idempotency shipped:** dedupe keys such as `order:{id}:ticket_confirmed` / `order:{id}:merch_order_confirmed`.

### Production readiness (emails will not actually leave the server unless all of these are true)

1. **Admin → Email settings:** sending enabled, provider `smtp`, **dev / log mode off**
2. SMTP host, port, username, password, from name/email configured in admin
3. **Admin → Runtime settings:** queue enabled (if using worker)
4. Outbox drained by `process_email_outbox.py` (or equivalent cron/worker) — or the API sweeper running
5. Host `EMAIL_SETTINGS_ENCRYPTION_KEY` set (decrypts SMTP secrets in DB)
6. SPF / DKIM / DMARC configured for `padeya.com` — see [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md)

Local default after first open of email settings: log provider + dev mode (safe; no network send).

---

## Notification map

Status legend: `shipped` · `partial` · `missing` · `template-ready` (template exists, product flow absent)

| Area | Trigger | Recipient | Email type | Required? | Template name | Status |
|---|---|---|---|---|---|---|
| Auth | Successful register | New user | Transactional | Yes | `welcome` | **shipped** |
| Auth | Email verification | User | Security | Yes when flow ships | `verify_email` | template-ready (API absent) |
| Auth | Password reset | User | Security | Yes when flow ships | `password_reset` | template-ready (API absent) |
| Auth | Security alert | User | Security | Optional | `security_alert` | template-ready (no device tracking) |
| Tickets | Paystack paid + tickets issued | Buyer | Transactional | **Yes** | `ticket_confirmed` | **shipped** (outbox + dedupe) |
| Tickets | QR ready | Buyer | Transactional | Merged | `ticket_qr_ready` | covered by confirmed CTA |
| Tickets | Payment failed | Buyer | Transactional | Optional | — | missing |
| Tickets | 24h reminder | Ticket holders | Reminder | Prefer | `ticket_event_reminder` | missing (no scheduler) |
| Tickets | Event updated / postponed | Ticket holders | Transactional | Prefer | `ticket_event_updated` | missing |
| Tickets | Event cancelled | Ticket holders | Transactional | **Yes** | `ticket_event_cancelled` | **shipped** |
| Tickets | Checked in | Buyer | Optional | Optional | `ticket_checked_in` | missing |
| Tickets | Refund request / decision | Buyer | Transactional | Prefer | `ticket_refund_update` | **shipped** |
| Merch | Verified merch payment | Buyer | Transactional | **Yes** | `merch_order_confirmed` | **shipped** |
| Merch | Ready for pickup | Buyer | Transactional | Prefer | `merch_pickup_ready` | **shipped** |
| Merch | Shipped / delivered | Buyer | Transactional | Prefer | `merch_shipping_update` | **shipped** |
| Merch | Picked up | Buyer | Transactional | Prefer | `merch_picked_up` | **shipped** |
| Merch | Merch refunded | Buyer | Transactional | Prefer | `merch_refund_update` | **shipped** |
| Merch | Post-event drop | Eligible buyers | Marketing | Opt-in | `post_event_drop_available` | **shipped** (pref-gated) |
| Merch | Abandoned cart | Buyer | Marketing | Opt-in | `merch_cart_reminder` | **shipped** (host opt-in + marketing pref) |
| Host | New ticket sale | Host | Activity | Prefer | `host_ticket_sale` | **shipped** (pref-gated) |
| Host | New merch sale | Host | Activity | Prefer | `host_merch_sale` | **shipped** (pref-gated) |
| Host | Event published | Host | Activity | Optional | — | missing |
| Host | Event / merch review | Host | Activity | Prefer | `host_new_review` | **shipped** |
| Host | New fan message | Host | Activity | Opt-in | `host_new_message` / `new_message` | **shipped** (messages pref) |
| Host | Sponsor inquiry | Host | Activity | Prefer | `sponsor_inquiry_host_alert` | **shipped** |
| Host | Payout update | Host | Transactional | Prefer | `host_payout_update` | template-ready (not wired to finance review yet) |
| Host | CRM announcement | Followers | Marketing | Opt-in | host body | partial (legacy sync `send_email`, not outbox) |
| Fan Connect | Request / accepted | Fans | Social | Opt-in | `fan_connect_*` | **shipped** (`email_fan_connect`, default off) |
| Fan Connect | Declined | Requester | Social | Optional | — | in-app only (by design) |
| Messaging | New message / attachment | Recipient | Social | Opt-in | `new_message` / `attachment_received` | **shipped** (generic copy; `email_messages` default off) |
| Messaging | Message request | Recipient | Social | Opt-in | `message_request` | template-ready (kind exists; limited wiring) |
| Sponsor | Inquiry confirm / host alert / status | Brand + host | Transactional | Prefer | `sponsor_inquiry_*` | **shipped** |
| Sponsor | Placement reminder | Host/brand | Optional | Optional | — | missing |
| Vault | Access granted / new content | Buyer / followers | Mixed | Prefer / opt-in | — | missing (merch unlock stays in-app) |
| Reviews | Host reply | Buyer | Activity | Prefer | `review_host_reply` | **shipped** |
| Reviews | Reported | Admin | Moderation | Prefer | `admin_new_report` / `admin_safety_report` / `admin_abuse_report` / `admin_message_report` | **shipped** (group + permission routing) |
| Admin | Platform events (38+ keys) | Staff by group | Ops/finance/mod | Configurable | `admin_*` catalog | **shipped** (editable DB + `/admin/emails/templates`) |
| Admin | Support ticket opened | Support | Ops | Prefer | `admin_new_support_ticket` | **shipped** |
| Admin | Verified ticket / merch sale | Finance/ops | Finance | Optional | `admin_new_ticket_sale` / `admin_new_merch_sale` | **shipped** (post-payment only) |
| Admin | Payment / dispute | Finance | Finance | Required | `admin_payment_issue` / `admin_chargeback_or_dispute` | template + dispatch ready |
| System | Prefs updated | User | Confirmation | Prefer | `email_preferences_updated` | **shipped** |
| System | Marketing unsubscribe | User | Confirmation | Prefer | prefs page | **shipped** (`/unsubscribe`) |

---

## Remaining gaps

1. Password-reset / email-verify **product APIs** (templates exist).  
2. Event reminder **scheduler** (`ticket_event_reminder`).  
3. Event updated / postponed buyer blast.  
4. Optional checked-in confirmation.  
5. Wire `host_payout_update` into finance payout review/mark-paid.  
6. Wire remaining admin templates (refunds, restrictions, host verify, stock alerts) where product hooks are still TODO.  
7. Move CRM announcement dispatch onto the outbox.  
8. Bounce/complaint webhook ingestion (placeholder in deliverability doc).  
9. Vault access / new-content email alerts.

---

## Preference rules

| Preference key | Default | Can disable? | Covers |
|---|---|---|---|
| `email_security` | on | **No** | reset, verify, security_alert |
| `email_ticket_updates` | on | Soft (purchase confirm still sends) | cancel, refunds, updates |
| `email_merch_updates` | on | Soft (paid confirm still sends) | pickup/shipping/picked up/refund |
| `email_event_reminders` | on | Yes | reminder job (when built) |
| `email_messages` | off | Yes | messaging emails |
| `email_fan_connect` | off | Yes | connect request/accepted |
| `email_sponsor_updates` | on | Yes | inquiry confirm/status |
| `email_host_activity` | on | Yes | sales, reviews, sponsor inquiry |
| `email_marketing` | off | Yes | cart + post-event drops |

**Always send:** verified purchase confirmations + security emails.

---

## Privacy rules (email bodies)

Never include hidden venues, full payment refs, private chat bodies, attachment URLs, locked Vault bodies, private CRM notes, or Fan Connect graph details.  
Tickets: public codes + dashboard CTA. Merch pickup codes only after paid. Messages: generic “You have a new message on Pàdéyá” + CTA.

---

## Admin platform email audit actions

| Audit action | When |
|---|---|
| `admin.emails.template_updated` | Admin saves template copy or settings |
| `admin.emails.recipients_updated` | Recipient mode, group, or custom list changed (`admin.emails.manage_recipients`) |
| `admin.emails.template_test_send` | Test send (includes `recipient_count` in details; max 5 parsed addresses; rate limit per admin) |
| `admin.emails.template_restored` | Restore registry defaults |
| `admin.emails.notification_settings_updated` | Global admin notification master/digest toggles |

Custom recipient addresses are stored normalized in `email_admin_templates.custom_recipient_emails` (JSON). Production sends create one outbox event per resolved recipient.

---

## Related docs

- [EMAILS.md](./EMAILS.md) — architecture, env, outbox worker, testing  
- [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md) — SPF/DKIM/DMARC + production SMTP  
- [NOTIFICATIONS.md](./NOTIFICATIONS.md) — prefs matrix  
- API / DATABASE / ADMIN / PRIVACY / SECURITY / EXECUTION_TRACKER  

---

*Verified against codebase: 2026-07-19.*
