# Environment variables (Pàdéyá)

Companion to Admin Runtime Settings. Canonical classification: [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md).  
Loader: [`backend/app/core/config.py`](../backend/app/core/config.py) (`Settings` + `get_settings()`).  
Templates: `backend/.env.example`, `backend/.env.production.example`. Ops: [OPERATIONS.md](./OPERATIONS.md) · [DEPLOYMENT.md](./DEPLOYMENT.md). Product settings UX: [SETTINGS.md](./SETTINGS.md).

**Out of scope here:** Frontend `NEXT_PUBLIC_*` (build-time).

---

## How env relates to Admin Runtime Settings

| Class | Editable in admin? | Storage |
|-------|-------------------|---------|
| **A — boot-critical** | **Never** | Host `.env` / secret manager only |
| **B — optional tunable** | Yes (`runtime_settings` DB override) | Env is fallback when no DB row |
| **C — optional secret** | Specialist UIs only (email/push) | Encrypted specialist tables; admin UI |
| **D — status** | No | Derived from env / probes / specialist status |
| **E — alias / unused** | No | Document only |

Resolver order for Class B: **DB override → env / Settings → code default → missing**. See [SETTINGS.md](./SETTINGS.md).

Startup **does not** require any `runtime_settings` rows. Missing optional config must degrade gracefully.

---

## Class A — boot-critical (never admin-editable)

Status panel may show configured/missing, `APP_ENV`, version, build SHA, last boot — **never raw values**.

| Env | Why |
|-----|-----|
| `APP_ENV` | Gates production safety validators |
| `DEBUG` | Prod must be false; boot-checked |
| `DEMO_MODE` | Prod must be false; boot-checked |
| `DATABASE_URL` | Required before DB access |
| `REDIS_URL` | Infra URL (secret-like) |
| `SECRET_KEY` | JWT + crypto fallback |
| `QR_SIGNING_SECRET` | Ticket signing |
| `EMAIL_SETTINGS_ENCRYPTION_KEY` | Fernet for admin SMTP/VAPID ciphertext |
| `CORS_ORIGINS` | Prod allowlist; boot-checked |
| `FRONTEND_URL` | Prod origin; boot-checked |
| `API_PREFIX` | Wired at app construction |
| `JWT_ALGORITHM` | Auth crypto policy |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session policy |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Session policy |
| `IMPERSONATION_TOKEN_EXPIRE_MINUTES` | Admin impersonation TTL |
| `AI_API_KEY` | Provider secret — env only |
| `MEDIA_STORAGE_PROVIDER` | `local` (dev) or `r2` (production public media) |
| `MEDIA_ROOT` | Filesystem mount / path (local provider + legacy `/media`) |
| `R2_BUCKET_NAME` | Cloudflare R2 bucket (when provider=`r2`) |
| `R2_ENDPOINT` | R2 S3-compatible endpoint (when provider=`r2`) |
| `R2_ACCESS_KEY_ID` | R2 API token access key — env only |
| `R2_SECRET_ACCESS_KEY` | R2 API token secret — env only |
| `R2_PUBLIC_URL` | Public media origin (e.g. `https://media.padeya.com`) |
| `MESSAGING_ATTACHMENT_STORAGE_PROVIDER` | Storage backend wiring |
| `MESSAGING_ATTACHMENT_STORAGE_ROOT` | Private storage path |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose infra only |
| `PYTHONPATH` / `NODE_ENV` | Process wiring |

Aliases **not used** as separate fields: `JWT_SECRET`, `ACCESS_TOKEN_SECRET`, `COOKIE_SECRET`, `SESSION_SECRET`, `ENVIRONMENT`, `SETTINGS_ENCRYPTION_KEY` — map conceptually to `SECRET_KEY` / `APP_ENV` / `EMAIL_SETTINGS_ENCRYPTION_KEY`.

---

## Class B — admin-editable via Runtime Settings

Non-secret tunables. Env remains fallback. Registry keys live in `backend/app/runtime_settings/registry.py`.

| Group | Env keys |
|-------|----------|
| Soft product | `APP_NAME`, `SUPPORT_EMAIL`, `APP_BASE_URL`, `MEDIA_PUBLIC_BASE_URL`, `EMAIL_LOG_BODY_IN_DEV` |
| Email workers | `EMAIL_QUEUE_ENABLED`, `EMAIL_WORKER_POLL_SECONDS`, `EMAIL_WORKER_BATCH_SIZE`, `EMAIL_RATE_LIMIT_PER_USER_PER_HOUR` |
| Push workers | `PUSH_QUEUE_ENABLED`, `PUSH_WORKER_POLL_SECONDS`, `PUSH_WORKER_BATCH_SIZE`, `PUSH_MESSAGE_RATE_LIMIT_PER_HOUR` |
| Merch cart | `MERCH_CART_ABANDON_AFTER` (+ hours alias), `MERCH_CART_EXPIRE_AFTER_DAYS`, `MERCH_CART_RECOVERY_MIN_GAP_HOURS` |
| Messaging limits | `MESSAGING_ATTACHMENT_MAX_*`, `MESSAGING_ATTACHMENT_ORPHAN_HOURS`, `MESSAGING_ATTACHMENT_CLEANUP_INTERVAL_SECONDS`, `MESSAGING_ATTACHMENT_DOWNLOAD_TTL_SECONDS`, `MESSAGING_ATTACHMENT_STRIP_IMAGE_METADATA`, `MESSAGING_ATTACHMENT_SCANNER` |
| Analytics | `ANALYTICS_*` dedupe windows, rate limit, batch/metadata caps |
| Ambassadors | `AMBASSADOR_TRACK_RATE_LIMIT_PER_MINUTE`, `AMBASSADOR_CLICK_SPIKE_*`, `AMBASSADOR_HIGH_VALUE_REWARD_NGN` |
| AI knobs (non-secret) | `AI_ENABLED`, `AI_PROVIDER`, `AI_MODEL`, `AI_BASE_URL`, `AI_MAX_TOKENS`, `AI_TIMEOUT_SECONDS`, `AI_RATE_LIMIT_PER_HOUR` |

Clearing a DB override restores env/default for that key.

### Paystack (admin Payment integration)

Per [Paystack authentication](https://paystack.com/docs/api/authentication/): **test** and **live** use the same API base URL; **which keys you use** selects the environment (`sk_test_`/`pk_test_` vs `sk_live_`/`pk_live_`).

Set under **Admin → System → Payment integration** (`/admin/settings/runtime/payments`). **Not in `.env`.**

| Registry key | Storage | Notes |
|--------------|---------|--------|
| `paystack_mode` | Plain | `test` (default) or `live` — selects active key pair |
| `paystack_secret_key` | Encrypted | **Test** secret (`sk_test_…`) |
| `paystack_public_key` | Plain | **Test** public (`pk_test_…`) |
| `paystack_webhook_secret` | Encrypted | Test webhook HMAC; falls back to test secret |
| `paystack_live_secret_key` | Encrypted | **Live** secret (`sk_live_…`) |
| `paystack_live_public_key` | Plain | **Live** public (`pk_live_…`) |
| `paystack_live_webhook_secret` | Encrypted | Live webhook HMAC; falls back to live secret |
| `paystack_base_url` | Plain | Default `https://api.paystack.co` |

Resolve order: DB override → registry default. Checkout, webhooks, and Paystack HTTP calls use `paystack_runtime(db)` for the **active mode**.

### Google Geocoding (admin Integrations)

Server-only **Google Places / Geocoding** key for admin event re-geocode. **Not in `.env`.** Set `google_places_api_key` under **Admin → System → Integrations** (`/admin/settings/runtime/integrations`). Never use `NEXT_PUBLIC_*` for this key.

---

## Class C — specialist secrets (not in `runtime_settings`)

| Domain | Configuration | Admin surface |
|--------|---------------|---------------|
| Email / SMTP | **Admin → Email settings** (`email_provider_settings`) — not `.env` | `/admin/email/settings` |
| Push / VAPID | Generate/store in admin | `/admin/push/settings` → `push_provider_settings` |

Do **not** migrate SMTP/VAPID into `runtime_settings`. Unified hub links to these specialists.

---

## Class D — read-only / status-only

| Item | Display |
|------|---------|
| Paystack public key (active mode) | Masked / last4 + configured |
| Paystack secret / webhook configured? | Boolean only |
| `AI_API_KEY` configured? | Boolean only |
| Redis reachable? | Health probe when cheap |
| Active email/push provider | Link to specialist pages |
| Ambassador platform `enabled` | `/admin/ambassadors` (not env) |
| System | `APP_ENV`, version, build SHA, last boot |

---

## Class E — deprecated / unused / alias

| Env | Notes |
|-----|-------|
| `EMAIL_*` / `SMTP_*` (product email) | **Not used** — configure in Admin → Email settings + runtime settings |
| `SMTP_FROM` | Legacy alias (Settings only); prefer admin from address |
| `MERCH_CART_ABANDON_AFTER_HOURS` | Alias of `MERCH_CART_ABANDON_AFTER` |
| `OPENAI_*` / `ANTHROPIC_*` / `GEMINI_*` / `CLOUDFLARE_*` | Not in Settings |
| `ENVIRONMENT` | Not used — use `APP_ENV` |
| `PAYSTACK_ENABLED`, `MAINTENANCE_MODE`, `S3_*`, Cloudinary, Slack, reCAPTCHA server keys | **Not implemented** — do not invent |

---

## Doc gaps

- Some `PUSH_*` / `EMAIL_RATE_LIMIT_*` / `SMTP_USE_SSL` knobs exist on `Settings` but may be incomplete in `.env.example` — prefer registry + this doc + OPERATIONS for truth.
- Never commit real `.env` / `.env.production` files.
