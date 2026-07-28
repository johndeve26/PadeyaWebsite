# Pàdéyá production deployment

This guide covers Docker Compose production deploy for:

- Next.js frontend
- FastAPI backend
- Email outbox worker (`email_worker`)
- PostgreSQL
- Redis
- Alembic migrations
- Nginx reverse proxy + TLS

User-facing brand name: **Pàdéyá**. Internal/code names may remain `padeya`.

## Safety rules

- Never set `APP_ENV=production` with `DEMO_MODE=true`.
- Never seed demo data on production (`python -m scripts.seed_demo_data` refuses production).
- Schedule analytics rollups nightly (no Celery required) — see [ANALYTICS_ROLLUPS.md](./ANALYTICS_ROLLUPS.md).
- Never commit `backend/.env.production` or `frontend/.env.production`.
- Use strong `SECRET_KEY` / `QR_SIGNING_SECRET` (32+ characters).
- Set explicit HTTPS `CORS_ORIGINS` and `FRONTEND_URL` (no localhost).
- Keep Paystack / AI / SMTP secrets server-side only.
- `NEXT_PUBLIC_DEMO_MODE=false` for production builds.

## Files

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production stack (includes `email_worker`) |
| `backend/.env.production.example` | Backend boot secrets template (email/SMTP in admin, not env) |
| `frontend/.env.production.example` | Frontend + compose env template |
| `scripts/deploy.sh` | Pull, build, up, `alembic upgrade head`, health |
| `scripts/deploy-all.sh` | Optional backup + `deploy.sh` + worker status + `alembic current` |
| `scripts/prod-migrate.sh` | Manual Alembic upgrade |
| `scripts/prod-logs.sh` | Tail logs (`backend` / `frontend` / `email_worker`) |
| `scripts/prod-backup-db.sh` | Timestamped Postgres dump |
| `scripts/prod_preflight.py` | Read-only go-live preflight (env, demo data, integrations) |
| `backend/scripts/prod_preflight.py` | Same preflight (run from `backend/` with `PYTHONPATH=.`) |
| `infra/nginx/padeya.conf.example` | Nginx reverse proxy |
| [OPERATIONS.md](./OPERATIONS.md) | Email outbox ops runbook |

## Local production test (on your laptop)

```bash
cp backend/.env.production.example backend/.env.production
cp frontend/.env.production.example frontend/.env.production
```

Edit both files:

1. Generate secrets:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Set `SECRET_KEY` and `QR_SIGNING_SECRET` in `backend/.env.production`.
3. For a **local** prod-compose smoke test only, you may temporarily use:
   - `CORS_ORIGINS=http://localhost:3000`
   - `FRONTEND_URL=http://localhost:3000`
   - `NEXT_PUBLIC_API_URL=http://localhost:8000`  
   Note: the production Settings validator **rejects** localhost CORS/FRONTEND_URL when `APP_ENV=production`. For a true local compose smoke with production env, either:
   - put Nginx + hosts file aliases (recommended), or
   - set `APP_ENV=staging` in `backend/.env.production` for the local smoke only (staging still requires strong secrets).

Recommended local smoke with staging (compose reads `APP_ENV` from the env file):

```bash
# backend/.env.production
APP_ENV=staging
DEBUG=false
DEMO_MODE=false
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000
SECRET_KEY=<48+ char secret>
QR_SIGNING_SECRET=<48+ char secret>

# frontend/.env.production
APP_ENV=staging
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_MODE=false
POSTGRES_PASSWORD=<strong password>
```

Then:

```bash
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production up --build -d
curl -s http://127.0.0.1:8000/health
curl -sI http://127.0.0.1:3000/
```

On a real VPS, set `APP_ENV=production` in both env files (or omit it so compose defaults to production).

Backend entrypoint always runs `alembic upgrade head` before uvicorn.

## VPS deployment steps

### 1. Server prep

- Ubuntu 22.04+ (or similar)
- Docker Engine + Compose plugin
- Git
- Nginx + Certbot
- Firewall: allow 80/443; keep 3000/8000 bound to localhost if possible

### 2. Clone & env

```bash
git clone <YOUR_REPO_URL> PadeyaWebsite
cd PadeyaWebsite
cp backend/.env.production.example backend/.env.production
cp frontend/.env.production.example frontend/.env.production
chmod 600 backend/.env.production frontend/.env.production
```

Fill production values:

```env
# backend/.env.production (excerpt)
APP_ENV=production
DEBUG=false
DEMO_MODE=false
SECRET_KEY=...
QR_SIGNING_SECRET=...
CORS_ORIGINS=https://padeya.com,https://www.padeya.com
FRONTEND_URL=https://padeya.com
# Paystack: Admin → Payment integration (test/live keys + webhook secrets)

# Transactional email — configure in Admin → Email settings after deploy
# Host secret only (not product SMTP config):
EMAIL_SETTINGS_ENCRYPTION_KEY=...

# frontend/.env.production (excerpt)
NEXT_PUBLIC_API_URL=https://api.padeya.com
NEXT_PUBLIC_APP_NAME=Pàdéyá
NEXT_PUBLIC_DEMO_MODE=false
POSTGRES_PASSWORD=...
```

### 3. DNS

Point A/AAAA records:

| Host | Target |
|------|--------|
| `padeya.com` | VPS IP |
| `www.padeya.com` | VPS IP |
| `api.padeya.com` | VPS IP |

Also configure **email auth DNS** for `padeya.com` before going live with SMTP:

- SPF
- DKIM
- DMARC  

Details: [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md).

### 4. Deploy stack

```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

Or manually:

```bash
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production up --build -d
./scripts/prod-migrate.sh   # optional; entrypoint already migrates
```

Ensure `email_worker` is up (drains `email_events`):

```bash
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production ps email_worker
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production logs email_worker --tail=50
```

Without `email_worker` (or an equivalent cron), purchase emails enqueue but are not delivered.

Ensure `reservation_sweeper` is up (releases expired checkout holds):

```bash
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production ps reservation_sweeper
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production logs reservation_sweeper --tail=50
```

Without `reservation_sweeper` (or an equivalent cron), pending orders past `reservation_expires_at` keep inventory reserved.

**Render (padeyawebsite.onrender.com):** if not using Compose, create a **Cron Job** in the Render dashboard — see [OPERATIONS.md](./OPERATIONS.md#reservation-sweeper).

### 5. Nginx + TLS

```bash
sudo cp infra/nginx/padeya.conf.example /etc/nginx/sites-available/padeya
sudo ln -sf /etc/nginx/sites-available/padeya /etc/nginx/sites-enabled/padeya
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d padeya.com -d www.padeya.com -d api.padeya.com
```

Ensure compose ports are only needed on localhost if Nginx is on the same host (optional hardening: change compose ports to `127.0.0.1:3000:3000` and `127.0.0.1:8000:8000`).

### 6. Paystack webhook

In Paystack dashboard, set webhook URL to:

```text
https://api.padeya.com/api/v1/payments/webhooks/paystack
```

(Confirm in [docs/PAYMENTS.md](./PAYMENTS.md) if the path ever changes.)

Use the **live webhook secret** from Admin → Payment integration. Do not skip signature verification.

### 7. Health checks

```bash
curl -s https://api.padeya.com/health
curl -sI https://padeya.com/
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production ps
# Email worker should log provider_mode=smtp and batch stats (no bodies/passwords)
docker compose -f docker-compose.prod.yml --env-file frontend/.env.production logs email_worker --tail=30
```

### 8. Production preflight (before traffic)

Run **read-only** checks (never modifies data, never prints secrets):

```bash
# From repo root
./scripts/prod_preflight.py

# Or from backend/
cd backend && PYTHONPATH=. python scripts/prod_preflight.py
```

Preflight verifies:

- `APP_ENV=production`, `DEMO_MODE=false`, `DEBUG=false`
- Strong `SECRET_KEY` / QR signing secret
- `DATABASE_URL`, Redis URL (+ ping when in production)
- `FRONTEND_URL` HTTPS, `CORS_ORIGINS` without localhost
- Paystack **live** keys + webhook secret (Admin → Payment integration)
- Email SMTP configured, dev/log mode off, queue/worker expected
- `NEXT_PUBLIC_DEMO_MODE=false` (documented for frontend builds)
- **No demo data** in DB (`@demo.padeye.test` users, `demo-*` events, demo host slugs, demo markers)
- Alembic migrations at head (including AI ≥ `20260722_0128`)
- Backup script present
- **AI readiness** (`AI_READY: PASS|WARN|FAIL`): 24 canonical templates/routes, blocked/quarantined keys, providers, kill switch, safe logs (see [AI_PREDEPLOY_HARDENING_AUDIT.md](./AI_PREDEPLOY_HARDENING_AUDIT.md))

Final status: **`READY_FOR_PRODUCTION`** or **`BLOCKED`**. CLI also prints **`AI_READY`**. Exit code `1` when blocked.

Super admins can also open **`/admin/platform/go-live`** (alias **`/admin/platform/readiness`**) — permission `admin.platform.view_readiness`. The **AI readiness** card summarizes templates, routes, providers, kill switch, blocked/quarantined keys, and spend cap.

**Fresh database strongly recommended.** Do not restore a Postgres dump from a machine where `seed_demo_data` ran. Preflight fails if demo rows exist. Never run `seed_demo_data` or `reset_demo_data` with `APP_ENV=production`.

See also [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md).

Email ops (pending/failed counts, resend, SQL): [OPERATIONS.md](./OPERATIONS.md).

## Migrations

Automatic on backend container start (`backend/scripts/docker-entrypoint.sh`).

Manual:

```bash
./scripts/prod-migrate.sh
```

## Backups

```bash
./scripts/prod-backup-db.sh
# files land in ./backups/padeya-postgres-<UTC>.sql.gz
```

Store backups off-box. Test restore on a staging DB before you need it.

## Logs

```bash
./scripts/prod-logs.sh
# SERVICES=backend ./scripts/prod-logs.sh
```

Do not paste logs containing Authorization headers, Paystack secrets, or JWT material into tickets/chat.

## Rollback

1. `git log` → identify last good commit  
2. `git checkout <good-sha>`  
3. `./scripts/deploy.sh` with `SKIP_GIT_PULL=1` if you already checked out  
4. If a migration must roll back, use a deliberate Alembic downgrade only after backup — prefer forward-fix migrations.

```bash
./scripts/prod-backup-db.sh
SKIP_GIT_PULL=1 ./scripts/deploy.sh
```

## Common errors

| Symptom | Likely cause |
|---------|----------------|
| Backend exits on start with SECRET_KEY error | Weak/short secret in production |
| Backend exits on CORS/FRONTEND_URL | Localhost left in production env |
| Backend exits on DEMO_MODE | `DEMO_MODE=true` with `APP_ENV=production` |
| Frontend calls localhost API | Rebuild frontend with correct `NEXT_PUBLIC_API_URL` build arg |
| 502 from Nginx | Containers down / wrong upstream ports |
| Migrations fail | Postgres not healthy / bad `DATABASE_URL` |
| Paystack webhook 401 | Wrong webhook secret / signature path |
| `email_worker` crash-loop | SMTP misconfigured in Admin → Email settings (dev mode on, or missing host/credentials) |
| Emails stuck `pending` | Worker down — restart `email_worker` or run `--once` |
| Emails skipped | Email sending disabled in admin or preference opt-out |

## Demo mode warning

Demo accounts, `/demo`, and seed scripts are **local development only**. Production examples set:

- `DEMO_MODE=false`
- `NEXT_PUBLIC_DEMO_MODE=false`

Never run `python -m scripts.seed_demo_data` against production.

## Related

- Smoke checklist: [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md)
- Email architecture: [EMAILS.md](./EMAILS.md)
- Email ops runbook: [OPERATIONS.md](./OPERATIONS.md)
- Deliverability DNS: [EMAIL_DELIVERABILITY.md](./EMAIL_DELIVERABILITY.md)
- Payments: [PAYMENTS.md](./PAYMENTS.md)
- Security notes: [SECURITY.md](./SECURITY.md)
