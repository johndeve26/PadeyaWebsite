# Pàdéyá operations runbook

Brand: **Pàdéyá**. Related: [DEPLOYMENT.md](./DEPLOYMENT.md) · [EMAILS.md](./EMAILS.md) · [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md) · [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md).

## Email outbox worker

### Compose services

| File | Service | Container |
|------|---------|-----------|
| `docker-compose.yml` | `email_worker` | `padeya-email-worker` |
| `docker-compose.prod.yml` | `email_worker` | `padeya-prod-email-worker` |
| `docker-compose.yml` | `push_worker` | `padeya-push-worker` |
| `docker-compose.prod.yml` | `push_worker` | `padeya-prod-push-worker` |
| `docker-compose.yml` | `reservation_sweeper` | `padeya-reservation-sweeper` |
| `docker-compose.prod.yml` | `reservation_sweeper` | `padeya-prod-reservation-sweeper` |

### Start / restart

Local:

```bash
docker compose up -d backend email_worker push_worker reservation_sweeper
docker compose restart email_worker push_worker reservation_sweeper
docker compose logs email_worker push_worker reservation_sweeper --tail=100
```

Production:

```bash
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production up -d backend email_worker push_worker reservation_sweeper
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production restart email_worker push_worker reservation_sweeper
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production logs email_worker push_worker reservation_sweeper --tail=100
```

Manual one-shot (host or inside container):

```bash
cd backend && PYTHONPATH=. python scripts/process_email_outbox.py --once
PYTHONPATH=. python scripts/process_push_outbox.py --once
# Long-running (same as Docker `push_worker` — loop + subscription cleanup):
PYTHONPATH=. python scripts/process_email_outbox.py --loop
PYTHONPATH=. python scripts/process_push_outbox.py
# Equivalent explicit flags:
PYTHONPATH=. python scripts/process_push_outbox.py --loop --maintenance
PYTHONPATH=. python scripts/expire_order_reservations.py --once
PYTHONPATH=. python scripts/expire_order_reservations.py --loop
```

## Reservation sweeper

Releases inventory when pending checkout orders pass `reservation_expires_at` (Phase 6). Idempotent; safe to run frequently.

### Compose

`reservation_sweeper` runs `scripts/expire_order_reservations.py --loop` with `RESERVATION_SWEEPER_POLL_SECONDS` (default **60**).

### One-shot (cron / manual)

```bash
cd backend && PYTHONPATH=. python scripts/expire_order_reservations.py --once
```

Example host cron (if not using the Compose worker):

```cron
* * * * * cd /path/to/PadeyaWebsite/backend && PYTHONPATH=. /path/to/.venv/bin/python scripts/expire_order_reservations.py --once >> /var/log/padeya-reservation-sweeper.log 2>&1
```

### Render Cron Job (production API on Render)

If the backend runs on Render without Docker Compose workers:

1. Render dashboard → **New** → **Cron Job**
2. **Name:** `padeya-reservation-sweeper`
3. **Schedule:** `*/2 * * * *` (every 2 minutes; UTC)
4. **Root directory:** `backend`
5. **Build command:** `pip install -r requirements.txt`
6. **Start command:** `python scripts/expire_order_reservations.py --once`
7. **Environment:** copy the same env group as the web service (`DATABASE_URL`, `APP_ENV=production`, `SECRET_KEY`, etc.). Do not run against staging DB.
8. Enable the job and confirm first run logs `examined=… expired=… skipped=…` with no stack trace.

Repository reference: `infra/render/reservation-sweeper-cron.yaml` (documentation snippet; apply via dashboard if Blueprint is not linked).

## Push outbox worker

Product code only **enqueues** `push_events`. Compose `push_worker` (or the CLI above) drains them.

Push worker logs batch counts only (`attempted` / `sent` / `failed` / `skipped` / `deactivated_subscriptions`). It never logs title, body, endpoints, or VAPID material.

### Admin push (no redeploy)

1. Open `/admin/push/settings` as super_admin
2. Generate VAPID keys, set provider `log` (verify) then `web_push` for real browsers
3. Enable push → save → enable notifications on a device → **Send test push**
4. Worker picks up active DB settings on the next poll

### Inspect pending / failed push

**Admin UI:** `/admin/push/settings` (deliveries + events).

**Admin API:**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/admin/push/events?status=pending&limit=50"

curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/admin/push/deliveries?status=failed&limit=50"
```

**SQL (read-only — no payload dump in shared logs):**

```sql
SELECT status, count(*) FROM push_events GROUP BY status;

SELECT id, template, status, attempts, error_message, updated_at
FROM push_events
WHERE status = 'failed'
ORDER BY updated_at DESC
LIMIT 20;
```

### Push env (optional)

Prefer admin DB settings for VAPID / enable. Worker knobs:

```env
PUSH_QUEUE_ENABLED=true
PUSH_WORKER_POLL_SECONDS=20
PUSH_WORKER_BATCH_SIZE=50
PUSH_MESSAGE_RATE_LIMIT_PER_HOUR=12
```

Encryption for VAPID private + subscription keys uses the same Fernet key family as email SMTP secrets (`EMAIL_SETTINGS_ENCRYPTION_KEY`). Never commit real keys.

### Required production host secret

Configure SMTP and sending mode in **Admin → Email settings**. Queue/worker tunables in **Admin → Runtime settings → Email**.

```env
EMAIL_SETTINGS_ENCRYPTION_KEY=...   # required — Fernet key for admin SMTP/VAPID secrets in DB
```

Never commit real SMTP credentials. Never expect the worker to print passwords or full email bodies in production.

### Admin SMTP (no redeploy)

1. Open `/admin/email/settings` as super_admin
2. Set provider `smtp`, turn **off** dev/log mode, fill host/port/user/password/from
3. Save → Send test email
4. Worker picks up active DB settings on the next poll (no rebuild)

### Verify SMTP mode

Worker batch logs should include `provider_mode=smtp` (not `dev_log` / `disabled`).

```bash
docker compose logs email_worker --tail=50 | grep provider_mode
```

If production SMTP is misconfigured, the worker **logs a loud error** and keeps polling so you can fix settings in the admin dashboard without restarting.

### Inspect pending / failed emails

**Admin UI:** `/admin/emails` (filter by status) · `/admin/emails/[id]` · Resend button.

**Admin API:**

```bash
# List (admin JWT)
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/admin/emails?status=pending&limit=50"

curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/admin/emails?status=failed&limit=50"

# Resend one
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/admin/emails/<id>/resend"

# Drain pending now
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/admin/emails/process-pending?limit=50"
```

**SQL (read-only checks):**

```sql
-- Pending count
SELECT count(*) FROM email_events WHERE status = 'pending';

-- Failed count
SELECT count(*) FROM email_events WHERE status = 'failed';

-- Last sent
SELECT id, template, recipient_email, subject, sent_at, provider
FROM email_events
WHERE status = 'sent'
ORDER BY sent_at DESC NULLS LAST
LIMIT 10;

-- Recent failures (no body)
SELECT id, template, recipient_email, attempts, error_message, updated_at
FROM email_events
WHERE status = 'failed'
ORDER BY updated_at DESC
LIMIT 20;
```

Via compose:

```bash
docker compose exec postgres psql -U padeya -d padeya -c \
  "SELECT status, count(*) FROM email_events GROUP BY status;"
```

### Worker log / health behavior

Each batch logs (no bodies, no SMTP password):

- `pending_before`
- `attempted` / `sent` / `failed_batch` / `skipped`
- `still_pending` / `failed_total`
- `provider_mode`

When `EMAIL_ENABLED=false`, drains mark/skip with a clear skipped reason.

### DNS (deliverability)

Confirm SPF / DKIM / DMARC for `padeya.com` — [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md).

## Related ops

- Deploy: `./scripts/deploy.sh`
- Logs: `./scripts/prod-logs.sh` (includes `email_worker` by default; also tail `push_worker`)
- DB backup: `./scripts/prod-backup-db.sh`
- Push deep dive: [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md)
