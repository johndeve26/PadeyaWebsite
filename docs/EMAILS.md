# Pàdéyá transactional email

**Brand in copy:** Pàdéyá only (never Padeya / Padéyá / Pàdéyé).  
**Domain:** padeya.com is fine in From addresses and footer links.

Full trigger map: [EMAIL_AUDIT.md](./EMAIL_AUDIT.md)  
Deliverability: [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md)  
Preferences + channel matrix: [NOTIFICATIONS.md](./NOTIFICATIONS.md)  
Browser push (separate outbox/worker): [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md)

## Architecture

```
Product flow → enqueue_template() → email_events (pending)
                                      ↓
                         process_pending_emails() / API sweeper / CLI worker
                                      ↓
                         EmailProvider (log | smtp | future ESP)
```

Module: `backend/app/email/`

| File | Role |
|---|---|
| `service.py` | `enqueue_template` / `send_template` |
| `queue.py` | Outbox insert + delivery + resend |
| `provider.py` | Log / SMTP abstraction |
| `templates.py` + `renderer.py` | HTML + plain text |
| `prefs.py` + `tokens.py` | Preferences + signed unsubscribe |
| `router.py` | Prefs, unsubscribe, admin outbox |
| `models.py` | `email_events`, `user_email_preferences` |

All features must call the email service — do not open SMTP in domain modules.

Legacy shim: `app.core.email.send_email` still exists for CRM announcement dispatch; prefer the outbox for new work.

## Running the outbox processor

Payment/webhook paths **only enqueue** rows. Something must drain `email_events` with `status=pending`.

### Docker Compose worker (recommended)

Local:

```bash
docker compose up -d backend email_worker
docker compose logs email_worker --tail=100
```

Production:

```bash
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production up -d email_worker
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production logs email_worker --tail=100
```

Service command:

```text
python scripts/process_email_outbox.py --loop
```

### CLI one-shot (cron / manual)

```bash
cd backend
source .venv/bin/activate   # if used
PYTHONPATH=. python scripts/process_email_outbox.py --once
```

Example cron (if not using the Compose worker):

```cron
* * * * * cd /path/to/backend && PYTHONPATH=. .venv/bin/python scripts/process_email_outbox.py --once >> /var/log/padeya-email-outbox.log 2>&1
```

### In-process API sweeper

When the API runs with email sending and queue enabled in **Admin → Runtime settings** (and `APP_ENV != test`), `main.py` also drains pending emails about every 20 seconds. Prefer the dedicated `email_worker` service in production.

### Admin drain / retry

- UI: `/admin/emails` → open event → **Resend**
- API: `POST /api/v1/admin/emails/{id}/resend`
- Drain now: `POST /api/v1/admin/emails/process-pending`

Operator SQL + checks: [OPERATIONS.md](./OPERATIONS.md).

### Local check

```bash
# 1) Trigger a flow (register or verified Paystack finalize)
# 2) Ensure worker is up, or:
PYTHONPATH=. python scripts/process_email_outbox.py --once
# 3) Inspect /admin/emails (dev may show body preview when log bodies in dev is on in runtime settings)
```

### Worker logs (safe)

Each batch logs counts + `provider_mode` only. Production never logs SMTP passwords or full email bodies.

## Admin-managed provider settings

Configure provider, SMTP, and test delivery from **Admin → Email settings** (`/admin/email/settings`). Queue/worker tunables and `app_base_url` / `support_email` live under **Admin → Runtime settings**.

| Action | API |
|---|---|
| View masked settings | `GET /api/v1/admin/email/settings` |
| Update (blank password = keep) | `PATCH /api/v1/admin/email/settings` |
| Test connection / send test | `POST /api/v1/admin/email/settings/test` |
| Activate settings row | `POST /api/v1/admin/email/settings/activate` |
| Disable sending | `POST /api/v1/admin/email/settings/disable` |

### Provider resolution order

1. Active `email_provider_settings` row (`is_active=true`)
2. Code defaults when no row yet (log + dev mode on until admin saves)
3. Safe `LogEmailProvider` when dev/log mode or provider is log

API + `email_worker` re-read the active row each batch (no rebuild).

### Encryption

SMTP username/password are stored as Fernet ciphertext (`smtp_username_encrypted`, `smtp_password_encrypted`) using `EMAIL_SETTINGS_ENCRYPTION_KEY` (host secret only — not in admin UI). Responses expose masked fingerprints / `smtp_password_configured` only — never plaintext.

## Host secret (not product email config)

| Variable | Role |
|---|---|
| `EMAIL_SETTINGS_ENCRYPTION_KEY` | **Required** stable Fernet key to decrypt admin SMTP/VAPID ciphertext in Postgres |

### Production readiness — emails will not actually send unless

1. `EMAIL_SETTINGS_ENCRYPTION_KEY` set on the host
2. Sending enabled in **Admin → Email settings** with provider `smtp` and **dev / log mode off**
3. SMTP host/username/password/from configured in admin
4. `email_worker` running (and queue enabled in runtime settings)
5. SPF / DKIM / DMARC for `padeya.com` — [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md)

## Templates

Auth: `welcome`, `verify_email`, `password_reset`, `security_alert`
Tickets: `ticket_confirmed`, `ticket_qr_ready`, `ticket_event_*`, `ticket_checked_in`, `ticket_refund_update`  
Merch: `merch_order_confirmed`, `merch_pickup_ready`, `merch_shipping_update`, `merch_picked_up`, `merch_refund_update`, `post_event_drop_available`, `merch_cart_reminder`  
Host / Fan Connect / Messaging / Sponsor / Admin / System — see [EMAIL_AUDIT.md](./EMAIL_AUDIT.md).  
Host team (true pending invite by email or Pàdéyá username): `team_invite` (required; subject “You’re invited to join a Pàdéyá host team”; CTA **Accept invite**), `team_invite_accepted`, `team_invite_revoked`, `team_member_removed`, `team_permission_updated`, `team_security_alert` — [TEAMS.md](./TEAMS.md#emails--notifications) · [HOST_TEAM.md](./HOST_TEAM.md). Legacy aliases: `host_team_invite`, `host_team_invite_accepted`.

### Ambassadors

Templates: `ambassador_joined`, `ambassador_first_sale`, `ambassador_commission_payable`, `ambassador_payout_ready`, `ambassador_campaign_paused`, `ambassador_campaign_ended`, `host_ambassador_milestone` — [AMBASSADORS.md](./AMBASSADORS.md#notifications-phase-15).

| Rule | Detail |
|---|---|
| Prefs | Ambassador self → `email_ticket_updates`; host milestone → `email_host_activity` |
| Copy | Event/campaign names + status words only — **no** buyer PII, payment refs, or order IDs |
| Module | `app/ambassadors/notifications.py` via `enqueue_template` |

`team_invite` lead copy by method:

- **Email:** “You’ve been invited to join [Host Name]’s Pàdéyá team.”
- **Username:** “[Host Name] invited your Pàdéyá account @username to join their team.”

Username invites resolve to the account email before enqueue (host never sees that address). Invite email never includes raw tokens in logs; accept CTA uses one-time link `/team/invite/[token]`. Known invitees also get in-app + push (`team.invite`); host gets `team_invite_accepted` (+ in-app/push) on accept.

## Trigger points (wired)

| Trigger | Template |
|---|---|
| Register | `welcome` |
| Paystack finalize + tickets | `ticket_confirmed`, `host_ticket_sale` |
| Paystack finalize + merch | `merch_order_confirmed`, `host_merch_sale` |
| Merch ready / ship / pickup / refund | matching `merch_*` |
| Event cancel | `ticket_event_cancelled` |
| Refund request / decision | `ticket_refund_update` |
| Host team invite / resend | `team_invite` |
| Host team invite accepted (host) | `team_invite_accepted` + in-app/push |
| Host team invite revoked | `team_invite_revoked` + in-app/push |
| Team member removed | `team_member_removed` + in-app/push |
| Team permissions updated | `team_permission_updated` + in-app/push |
| Team member suspended | `team_security_alert` + in-app/push |
| Sponsor inquiry | confirmation + host alert + status |
| Fan Connect request/accept | `fan_connect_*` (pref-gated) |
| Messaging (opt-in) | `new_message` / `attachment_received` |
| Reviews | `host_new_review`, `review_host_reply`, `admin_new_report` |

## Preferences & unsubscribe

- `GET/PATCH /api/v1/email/preferences`
- `POST /api/v1/email/unsubscribe` (signed token)
- FE: `/dashboard/settings/notifications`, `/unsubscribe?token=`, `/email/preferences?token=`

Security + verified purchase confirmations cannot be fully disabled.

## Admin platform notification templates

Admins receive **dedicated** emails for platform events (registrations, verified sales, support, moderation, finance). These are separate from fan/host transactional templates.

| Layer | Location |
|---|---|
| Registry defaults | `backend/app/email/admin_catalog.py` + `templates.py` (`admin_*` keys) |
| Editable overrides | DB table `email_admin_templates` |
| Dispatch | `admin_dispatch.notify_admins_platform_email()` |
| Product hooks | `admin_triggers.py` (registration, verified ticket/merch pay, support, events, sponsors, fraud) |

**Resolution order:** DB override (if active) → registry default → render with allowlisted `{{variables}}` → outbox.

**Admin UI**

- `/admin/emails/templates` — list, filter, enable/disable, recipient mode and count
- `/admin/emails/templates/[templateKey]` — edit subject/body, recipient mode (admin group / custom / both), comma-separated custom emails, preview, multi-recipient test send, restore default
- `/admin/emails/settings` — master switch + link to SMTP

**API** (`admin.emails.*` permissions; `admin.full_access` implies all):

- `GET/PATCH /api/v1/admin/emails/templates/{key}`
- `POST .../preview`, `.../test-send` (optional `test_recipient_emails`, returns `recipient_count`), `.../restore-default`
- `GET/PATCH /api/v1/admin/emails/notification-settings`

**Recipient modes** (`recipient_mode` on `email_admin_templates`):

| Mode | Behavior |
|---|---|
| `group` | Resolve active admin users in `recipient_group` (permission/role mapped) |
| `custom` | Send only to normalized custom addresses in `custom_recipient_emails` (JSON array) |
| `group_and_custom` | Union of group + custom; dedupe by email before send |

**Custom recipient emails:** Enter in admin UI as comma-separated text (optional spaces after commas; semicolons normalized to commas). Parsed by `parse_recipient_emails()` in `admin_recipients.py` — trim, lowercase, validate format, dedupe, max **20** addresses per template. Invalid addresses are rejected at save (not stored).

**Recipient groups:** `super_admin`, `support`, `moderation`, `finance`, `operations`, `marketing` — mapped to permission/role holders. Catalog default `custom` implies `recipient_mode=custom` until overridden.

**Sending:** `notify_admins_platform_email()` resolves recipients from template settings, then enqueues **one `email_events` row per recipient** (individual `To`, per-recipient dedupe key and delivery tracking). Test sends use the same parser (max **5** test addresses); rate-limited and audit-logged.

**Permissions:** View templates with `admin.emails.view`. Edit copy with `admin.emails.edit_templates`. Edit recipient mode, group, or custom list with `admin.emails.manage_recipients` (recipient addresses masked in API responses without this permission). Test send: `admin.emails.test_send`.

**Safety:** No raw payment payloads, card data, passwords, or private message bodies in admin templates. Template edits, recipient changes (`admin.emails.recipients_updated`), and test sends (`admin.emails.template_test_send`) are audit-logged.

**Delivery modes:** `instant` (default), `disabled`, `digest` (global digest flag; batch worker TBD). High-value templates may use `threshold_amount` (e.g. large ticket orders).

Run migrations `20260722_0124_email_admin_templates` and `20260722_0125_email_admin_recipient_mode` before using recipient modes.

## Admin (outbox)

- FE: `/admin/emails`, `/admin/emails/[id]`, `/admin/emails/templates`, `/admin/emails/settings`
- API: list / detail / resend / process-pending  
Body preview only in development when **Log email bodies in dev** is enabled in runtime settings.

## Testing

```bash
cd backend && alembic upgrade head
pytest tests/test_email_system.py -q
PYTHONPATH=. python scripts/process_email_outbox.py
```

## Privacy

Never put hidden venues, full payment refs, private chat bodies, attachment URLs, or Vault bodies in email. Ticket emails use public codes + dashboard CTA only.
