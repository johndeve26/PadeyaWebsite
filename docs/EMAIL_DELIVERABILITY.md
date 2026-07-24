# Pàdéyá email deliverability

From address: `noreply@padeya.com` (or your verified domain mailbox).  
Display name: **Pàdéyá**  
Reply-To: `support@padeya.com`

## Production SMTP + DNS setup

Emails **will not actually deliver** in production until admin config, an outbox worker, and DNS auth are all in place.

### 1. Application config

Configure everything in the admin dashboard — **not** backend `.env` (except the host encryption key below).

| Surface | What to set |
|---|---|
| **Admin → Email settings** (`/admin/email/settings`) | Provider, dev/log mode, SMTP host/port/TLS, username/password, from/reply-to, test send |
| **Admin → Runtime settings → Email** | Queue enabled, worker poll/batch, rate limits, log bodies in dev |
| **Admin → Runtime settings → Product** | `app_base_url`, `support_email` (links in templates) |

Host secret (Class A — stays in deployment secrets, not admin UI):

```bash
EMAIL_SETTINGS_ENCRYPTION_KEY=...   # Fernet key for encrypted SMTP/VAPID in DB
```

Never commit real SMTP credentials. Generate and store `EMAIL_SETTINGS_ENCRYPTION_KEY` on the host only.

### 2. Outbox worker

Pending rows stay in `email_events` until drained:

```bash
cd backend && PYTHONPATH=. python scripts/process_email_outbox.py
```

Run on a schedule (cron every minute is typical) or keep the API sweeper running. Without a worker, purchase emails enqueue but never send.

### 3. DNS checklist (`padeya.com`)

| Record | Purpose | Notes |
|---|---|---|
| SPF | Authorize sending IPs/providers | TXT include your SMTP/ESP |
| DKIM | Cryptographic signature | Publish selector TXT from provider |
| DMARC | Policy + reporting | Start `p=none`, then quarantine/reject |
| Custom return-path | Bounce domain | If provider supports it |

Verify records in your DNS host **before** flipping production traffic to SMTP.

### 4. Provider choice

v1 uses raw SMTP. Later you can plug Postmark / Brevo / Resend / SendGrid behind `EmailProvider` without changing product call sites.

## Environments

| Mode | Admin config | Behavior |
|---|---|---|
| Local | Email settings: **Log only** or dev/log mode **on** | Log / optional `tmp/email_outbox` — **no network** |
| Staging | SMTP to catch-all or provider sandbox | Real SMTP, restricted recipients |
| Production | Provider **SMTP**, dev/log mode **off**, worker + DNS | Live delivery |

`production_email_ready()` refuses real SMTP sends when dev mode is on or SMTP host/credentials are missing.

## Bounce / complaint (placeholder)

v1 does not ingest provider bounce webhooks yet. Plan:

1. Provider webhook → mark `email_events` / suppress list  
2. Never retry hard bounces  
3. Complaints → force `email_marketing=false`

## Local test send

1. Leave **Admin → Email settings** on log / dev mode (default after first open)  
2. Trigger register or a verified demo payment  
3. Run `PYTHONPATH=. python scripts/process_email_outbox.py`  
4. Inspect `/admin/emails` or application logs  

For real SMTP locally: **Admin → Email settings** — provider SMTP, dev mode off, fill SMTP fields, save, test send.
