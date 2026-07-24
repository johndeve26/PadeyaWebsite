# Pàdéyá Admin Runtime Settings — Audit (canonical)

Phase 1 inventory and product decisions for Admin Runtime Settings.  
**Status:** audit complete · core implementation shipped (`runtime_settings` module + FE hub); see [SETTINGS.md](./SETTINGS.md) · [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md).  
**Brand:** Pàdéyá.

## Related docs

| Doc | Role |
|-----|------|
| [ADMIN.md](./ADMIN.md) | Admin tools including Runtime Settings summary |
| [SETTINGS.md](./SETTINGS.md) | Companion settings overview (resolver, perms, surfaces) |
| [SECURITY.md](./SECURITY.md) | Secrets, masking, runtime settings rules |
| [ENVIRONMENT.md](./ENVIRONMENT.md) | Env catalog by Class A–E |
| [API.md](./API.md) | `/api/v1/admin/settings/runtime*` HTTP surface |
| [DATABASE.md](./DATABASE.md) | `runtime_settings` table |
| [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) | `/admin/settings/runtime*` routes |

Also: [CRUD_MATRIX.md](./CRUD_MATRIX.md) · [EMAILS.md](./EMAILS.md) · [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · [PAYMENTS.md](./PAYMENTS.md) · [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md) · [OPERATIONS.md](./OPERATIONS.md) · [DEPLOYMENT.md](./DEPLOYMENT.md).

**Canonical loader today:** [`backend/app/core/config.py`](../backend/app/core/config.py) (`Settings` + `get_settings()`).  
**Sources inventoried:** Settings fields, `backend/.env.example`, `backend/.env.production.example`, `docker-compose.yml`, `docker-compose.prod.yml`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`.  
**Out of scope:** Frontend `NEXT_PUBLIC_*` (build-time).

---

## Classification legend

| Class | Meaning | Admin |
|-------|---------|-------|
| **A** | Boot-critical / infra | `.env` only — never editable; status at most |
| **B** | Optional non-secret tunable | Editable via `runtime_settings` + Admin Runtime Settings |
| **C** | Optional secret | Encrypted/masked specialist UIs only (not a raw key editor) |
| **D** | Read-only runtime status | Visible, not editable |
| **E** | Deprecated / unused / alias | Document only; do not surface as first-class |

---

## §1 — Hard Class A (never edit in admin)

Boot-critical and infra secrets stay on `Settings` / host `.env` / secret manager. Admin may show **status only** — never raw values, never edit.

### Status panel may show ONLY

- configured / missing (boolean or badge)
- environment name (`APP_ENV`)
- app version
- build SHA
- last boot time

### Never show raw values for Class A · never allow editing Class A

### Hard never-edit list (user + Padeya mapping)

| Name / alias | Padeya status | Why Class A |
|--------------|---------------|-------------|
| `DATABASE_URL` | **Exists** (`Settings.database_url`) | Required before DB access |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | **Compose infra only** (not Settings fields) | Postgres container wiring |
| `REDIS_URL` | **Exists** | Infra URL; secret-like |
| `SECRET_KEY` | **Exists** | JWT + crypto fallback |
| `JWT_SECRET` / `ACCESS_TOKEN_SECRET` / `REFRESH_TOKEN_SECRET` / `COOKIE_SECRET` / `SESSION_SECRET` | **N/A** — not separate fields; aliased conceptually to `SECRET_KEY` | — |
| `EMAIL_SETTINGS_ENCRYPTION_KEY` | **Exists** — Padeya Fernet key for admin SMTP/VAPID ciphertext | Required to decrypt admin-managed secrets |
| `SETTINGS_ENCRYPTION_KEY` / `FERNET_KEYS` / `MULTIFERNET_KEYS` / `ENCRYPTION_KEY` | **N/A** — map to `EMAIL_SETTINGS_ENCRYPTION_KEY` | — |
| `APP_ENV` | **Exists** (`ENVIRONMENT` **not used**) | Gates production safety validators |
| `DEBUG` | **Exists** | Prod must be false; boot-checked |
| `DEMO_MODE` | **Exists** | Prod must be false; boot-checked |
| `CORS_ORIGINS` | **Exists** | Prod allowlist; boot-checked before safe operation |
| `FRONTEND_URL` | **Exists** | Prod origin; boot-checked |
| `QR_SIGNING_SECRET` | **Exists** | Ticket signing; never expose |
| `API_PREFIX` | **Exists** | Wired at app construction |
| `JWT_ALGORITHM` | **Exists** | Auth crypto policy — deploy-time |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | **Exists** | Session policy — deploy-time |
| `REFRESH_TOKEN_EXPIRE_DAYS` | **Exists** | Session policy — deploy-time |
| `IMPERSONATION_TOKEN_EXPIRE_MINUTES` | **Exists** | Admin session policy — deploy-time |
| `AI_API_KEY` | **Exists** | Provider secret; stay env (CRUD matrix) |
| `MEDIA_ROOT` | **Exists** | Filesystem mount / path |
| `MESSAGING_ATTACHMENT_STORAGE_PROVIDER` | **Exists** | Storage backend wiring |
| `MESSAGING_ATTACHMENT_STORAGE_ROOT` | **Exists** | Private storage path |
| `PYTHONPATH` / `NODE_ENV` | **Process/runtime wiring** (compose / frontend) | Not Settings product knobs |
| `ADMIN_BOOTSTRAP_EMAIL` / `ADMIN_BOOTSTRAP_PASSWORD` | **Unused** — not in Settings, compose, or `.env.example` | — |

Any key required **before DB access** or **to decrypt admin settings** is Class A.

---

## §2 — Class B (optional runtime — `runtime_settings` owns these)

Non-secret tunables. Env remains fallback when no DB override. **This is what `runtime_settings` is for.**

| Group | Keys (exist in `Settings` today) |
|-------|----------------------------------|
| Workers / queues | `EMAIL_QUEUE_ENABLED`, `EMAIL_WORKER_POLL_SECONDS`, `EMAIL_WORKER_BATCH_SIZE`, `EMAIL_RATE_LIMIT_PER_USER_PER_HOUR`, `PUSH_QUEUE_ENABLED`, `PUSH_WORKER_POLL_SECONDS`, `PUSH_WORKER_BATCH_SIZE`, `PUSH_MESSAGE_RATE_LIMIT_PER_HOUR` |
| Merch cart | `MERCH_CART_ABANDON_AFTER` (+ hours alias), `MERCH_CART_EXPIRE_AFTER_DAYS`, `MERCH_CART_RECOVERY_MIN_GAP_HOURS` |
| Messaging attachments (limits only) | `MESSAGING_ATTACHMENT_MAX_*`, `MESSAGING_ATTACHMENT_ORPHAN_HOURS`, `MESSAGING_ATTACHMENT_CLEANUP_INTERVAL_SECONDS`, `MESSAGING_ATTACHMENT_DOWNLOAD_TTL_SECONDS`, `MESSAGING_ATTACHMENT_STRIP_IMAGE_METADATA`, `MESSAGING_ATTACHMENT_SCANNER` |
| Analytics | `ANALYTICS_*` dedupe windows, rate limit, batch/metadata caps |
| Ambassadors (fraud knobs) | `AMBASSADOR_TRACK_RATE_LIMIT_PER_MINUTE`, `AMBASSADOR_CLICK_SPIKE_*`, `AMBASSADOR_HIGH_VALUE_REWARD_NGN` |
| Soft product knobs | `APP_NAME`, `SUPPORT_EMAIL`, `APP_BASE_URL`, `MEDIA_PUBLIC_BASE_URL`, `EMAIL_LOG_BODY_IN_DEV` |

---

## §3 — Class C (optional secret — specialist UIs stay)

Keep on current specialist pages/services. **Do not fold into a raw key editor. Do not migrate SMTP/VAPID into `runtime_settings`.**

| Env / field | Surface today |
|-------------|----------------|
| SMTP host/port/TLS/SSL/from/reply + credentials | `/admin/email/settings` → `email_provider_settings` |
| Email enable / provider / dev mode | Same specialist page (DB only; safe defaults on first open) |
| VAPID private (+ public) | `/admin/push/settings` → `push_provider_settings` |

Product email (provider, SMTP, dev mode, from/reply) is **not** configured in `.env`. Host-only: `EMAIL_SETTINGS_ENCRYPTION_KEY`.

---

## §4 — Class D (read-only status)

| Item | Display |
|------|---------|
| Paystack public key (active mode) | Masked / last4 + `configured` |
| Paystack secret configured? | Boolean only |
| AI enablement / provider / model / base URL / limits | Status from env (no edit in v1 unless later allowlisted as B) |
| `AI_API_KEY` configured? | Boolean only |
| Redis reachable? | Health probe if cheap |
| Active email/push provider mode | Link to specialist pages |
| Ambassador platform `enabled` | Already `/admin/ambassadors` — link only |

---

## §5 — Class E (deprecated / unused / alias)

| Env | Notes |
|-----|-------|
| `SMTP_FROM` | Legacy alias → `SMTP_FROM_EMAIL` |
| `MERCH_CART_ABANDON_AFTER_HOURS` | Alias of `MERCH_CART_ABANDON_AFTER` |
| `OPENAI_*` / `ANTHROPIC_*` / `GEMINI_*` / `CLOUDFLARE_*` | **Not present** in Settings or compose |
| `ENVIRONMENT` | **Not used** — use `APP_ENV` |
| Separate JWT/cookie/session secret names | **N/A** — see Class A mapping |

---

## §6 — Class counts (existing inventory)

Approximate counts from current codebase (Settings + compose + specialist tables; excluding `NEXT_PUBLIC_*`):

| Class | Count (approx.) | Notes |
|-------|-----------------|-------|
| **A** | ~28 | Including compose `POSTGRES_*`, process `PYTHONPATH`/`NODE_ENV`, unused bootstrap marked N/A |
| **B** | ~40 | Worker/merch/messaging/analytics/ambassador knobs + soft product strings |
| **C** | ~15 | Email/SMTP + push VAPID family (admin specialist tables) |
| **D** | ~10 status items | Booleans / masked hints / health |
| **E** | ~6 | Aliases + absent provider env families |
| **Proposed / not implemented** | see §8 | Feature toggles, S3/Cloudinary, Slack, reCAPTCHA, etc. |

**Existing vs proposed (suggested product keys):** ~85+ keys/fields already exist in Settings or specialist tables; ~20+ suggested keys are **proposed / not implemented yet** (see §8).

---

## §7 — Doc gaps / implementation status

- `PUSH_*` worker knobs live in Settings + [OPERATIONS.md](./OPERATIONS.md) / compose but may still be incomplete in `backend/.env.example`.
- `EMAIL_RATE_LIMIT_PER_USER_PER_HOUR` and `SMTP_USE_SSL` live in Settings but may be incomplete in `.env.example`.
- [SETTINGS.md](./SETTINGS.md) and [ENVIRONMENT.md](./ENVIRONMENT.md) now exist as companions; this audit remains the detailed A–E inventory.
- **Shipped:** `backend/app/runtime_settings/` (models, registry, service, schemas, router, test_actions), Alembic `20260720_0089`, FE `/admin/settings/runtime*`, `admin.settings.*` permissions. **Partial:** dedicated pytest suite / full consumer wiring may still land.

---

## §8 — Suggested keys vs current codebase

Legend: **exists** = in `Settings` and/or specialist table/UI today · **proposed** = not in Settings — do not invent implementation in Phase 1.

### Email / SMTP

| Key / field | Status | Class |
|-------------|--------|-------|
| `EMAIL_*` / `SMTP_*` / from / reply | **Exists** (`email_provider_settings` only; admin UI) | C (+ B for queue/worker knobs) |
| Specialist UI `/admin/email/settings` | **Exists** | C surface |

### Push / VAPID

| Key / field | Status | Class |
|-------------|--------|-------|
| Push enable / provider / VAPID | **Exists** (`push_provider_settings` + `/admin/push/settings`) | C |
| `PUSH_QUEUE_*` / rate limit | **Exists** (Settings) | B |

### AI

| Key / field | Status | Class |
|-------------|--------|-------|
| `AI_ENABLED`, `AI_PROVIDER`, `AI_MODEL`, `AI_BASE_URL`, limits | **Exists** (Settings / env-only) | D status in v1; key stays A |
| `AI_API_KEY` | **Exists** (env) | A — never admin plaintext |
| AI provider settings **table** | **Not implemented** — only `ai_prompt_templates` + `ai_usage_logs` | — |
| Separate `OPENAI_*` / `ANTHROPIC_*` / `GEMINI_*` | **Not present** | E / proposed |

### Payments (Paystack)

| Key / field | Status | Class |
|-------------|--------|-------|
| `paystack_mode`, test/live secrets, public keys, webhook secrets, `paystack_base_url` | **Implemented** — `runtime_settings` (`/admin/settings/runtime/payments`) | B (secrets encrypted; not in `.env`) |
| `PAYSTACK_ENABLED` | **Proposed / not implemented yet** | — |

### Storage (S3 / Cloudinary)

| Key / field | Status | Class |
|-------------|--------|-------|
| `MEDIA_ROOT`, messaging attachment local paths | **Exists** | A (paths) / B (limits) |
| `S3_*` / `CLOUDINARY_*` / AWS keys | **Proposed / not implemented yet** | — |
| `MESSAGING_ATTACHMENT_STORAGE_PROVIDER=s3\|r2` | Reserved string in Settings; adapters **not wired** | A when used |

### Integrations (Maps / reCAPTCHA / Slack)

| Key / field | Status | Class |
|-------------|--------|-------|
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Frontend build-time only | Out of scope for runtime_settings |
| `google_places_api_key` | **Implemented** — `runtime_settings` (Integrations); server re-geocode only | B (encrypted; not in `.env`) |
| Server-side Maps / reCAPTCHA / Slack tokens | **Proposed / not implemented yet** | — |

### Feature toggles

| Key / field | Status | Class |
|-------------|--------|-------|
| Ambassador platform `enabled` | **Exists** — `ambassador_platform_settings` (not env) | Specialist / D link |
| `AMBASSADORS_ENABLED` env | **Not used** — DB singleton instead | E vs specialist |
| `MAINTENANCE_MODE` | **Proposed / not implemented yet** | — |
| Other global kill-switches beyond email/push DB flags | **Proposed / not implemented yet** | — |

---

## §9 — Admin route map

### Hub & specialist

| Route | Role | Status |
|-------|------|--------|
| `/admin/email/settings` | Class C email specialist | **Exists** |
| `/admin/push/settings` | Class C push specialist | **Exists** |
| `/admin/ambassadors` (platform toggle) | Ambassador enable | **Exists** |
| `/admin/settings` | Redirect → runtime hub | **Shipped** |
| `/admin/settings/runtime` | Runtime Settings dashboard | **Shipped** |
| `/admin/settings/runtime/[category]` | Category editor (registry categories) | **Shipped** |
| `/admin/settings/runtime/audit` | Settings audit table | **Shipped** |
| `/admin/settings/email` | Redirect → `/admin/settings/runtime/email` (specialist link) | **Shipped** |
| `/admin/settings/push` | Alias → `/admin/push/settings` | **Shipped** |
| `/admin/settings/[category]` | Legacy flat alias → runtime category | **Shipped** |
| Categories `ai` · `payments` · `notifications` · `storage` · `integrations` · `security-runtime` · `system-status` · `runtime` | Via `/admin/settings/runtime/[category]` | **Shipped** (registry-driven) |

### Frontend components (shipped under `frontend/src/components/admin/runtime-settings/`)

- `RuntimeSettingsDashboard`
- `RuntimeSettingsCategoryPage`
- `RuntimeSettingField`
- `SecretSettingField`
- `RuntimeSettingSourceBadge`
- `RuntimeSettingTestButton`
- `RuntimeSettingsAuditTable`

Admin UI **renders fields from the registry** (`backend/app/runtime_settings/registry.py`), not from ad-hoc forms per key.

---

## §10 — Settings storage model

Table: **`runtime_settings`** (`backend/app/runtime_settings/models.py`, migration `20260720_0089`).

| Field | Notes |
|-------|-------|
| `id` | UUID PK |
| `category` | Registry category |
| `key` | Unique allowlisted key |
| `value_encrypted` | Nullable — secrets only |
| `value_plain` | Nullable — non-secrets (JSON-capable) |
| `value_type` | `string` \| `number` \| `boolean` \| `json` \| `secret` |
| `is_secret` | Drives storage + display rules |
| `is_editable` | Registry/admin gate |
| `is_required_for_runtime` | Must stay false for optional features |
| `source` | `db` \| `env` \| `default` (display; resolver recomputes) |
| `description` | Admin copy |
| `validation_schema_json` | Nullable |
| `last_four` | Nullable — masked secrets only |
| `updated_by_admin_id` | Nullable FK → users |
| `updated_at` / `created_at` | Timestamps |

### Storage rules

- Secrets → `value_encrypted` only (+ `last_four`); never plaintext in DB.
- Non-secrets → `value_plain`.
- **Never** store boot-critical Class A secrets here (`SECRET_KEY`, `DATABASE_URL`, `EMAIL_SETTINGS_ENCRYPTION_KEY`, Paystack secrets, etc.).
- `source` tracks whether the effective value is from db override, env, or code default.

---

## §11 — Settings resolver

**Service:** `RuntimeSettingsService` (`backend/app/runtime_settings/service.py`).

### Resolution order

1. DB `runtime_settings` row if present + valid  
2. Env / `Settings` fallback  
3. Code default (registry / Settings default)  
4. Missing / unconfigured

### Methods

- `get_runtime_setting(key)` — non-secret / typed value  
- `get_runtime_secret(key)` — decrypt for server-side use only; never return to admin API as plaintext  

### Rules

- Boot-critical stays on `Settings` / `.env` — resolver must not own Class A.
- Optional services use `RuntimeSettingsService` for Class B (and only allowlisted optional secrets if ever added).
- Cache results; **invalidate on admin update**.
- **Never crash startup** if optional settings are missing.

---

## §12 — Runtime settings registry

**File:** `backend/app/runtime_settings/registry.py`.

Each allowlisted entry documents:

| Field | Purpose |
|-------|---------|
| `key` | Stable id |
| `category` | UI grouping |
| `label` / `description` | Admin copy |
| `type` | string / number / boolean / json / secret |
| `is_secret` | Encryption + mask |
| `editable` | Admin write gate |
| `env_var` | Fallback env name |
| `default` | Code default |
| `required_for_feature` | Feature flag coupling |
| `validation` | min/max / enum / schema |
| `restart_required` | Warn if deploy-time only |
| `sensitive_level` | Display / audit depth |

Admin UI renders exclusively from this registry (allowlist — not a free-form `.env` editor).

---

## §13 — Secret display rules

Admin APIs and UI display **only**:

- `Configured · ending in {last4}`  
- or `Not configured`

**Never** display full secrets, keys, tokens, passwords, webhook secrets, or encryption keys.

### Updates

- Replace secret (write new ciphertext + new `last_four`)  
- Clear DB override (fall back to env/default)  
- **No reveal** endpoint  
- **No logging** of secret values  
- Persist `last_four` only for mask hints  

Response shape for secrets (example):

```json
{
  "key": "example_optional_secret",
  "is_secret": true,
  "configured": true,
  "masked_value": "Configured · ending in a1b2",
  "source": "db",
  "last_four": "a1b2"
}
```

No `value`, no plaintext, no env dump.

---

## §14 — Permission rules

Seeded in `backend/app/users/constants.py` (email/push specialists still use `admin.full_access`):

| Code | Intent |
|------|--------|
| `admin.settings.view` | View runtime settings hub (non-secret values + masks) |
| `admin.settings.edit_runtime` | Edit Class B non-secrets |
| `admin.settings.edit_secrets` | Replace/clear allowlisted optional secrets |
| `admin.settings.test_integrations` | Run test actions |
| `admin.settings.view_system_status` | Class D / system-status panel |
| `admin.settings.clear_overrides` | Reset DB override → env/default |
| `admin.settings.view_audit` | View settings audit table |

### Rules

- **support** defaults: `view` + `view_system_status` — no secret edit.  
- **finance** defaults: `view` + `view_system_status` + `edit_runtime` (Paystack secrets remain Class A / not editable).  
- Secrets require `edit_secrets`.  
- **super_admin** (`admin.full_access`) has all.  
- **Every save is audited.**

See [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md) · [SECURITY.md](./SECURITY.md) · [SETTINGS.md](./SETTINGS.md).

---

## §15 — Existing systems connection (**locked decision**)

### Decision (least risk — locked)

**Keep specialized tables as source of truth.**  
**Do not migrate SMTP / VAPID (or other specialist secrets) into `runtime_settings`.**

The unified Admin Runtime Settings UI exposes those domains via:

1. **Links / embeds** to existing specialist pages and APIs, and/or  
2. **Thin adapters** that **READ status** from those tables and **WRITE through existing services** (`email/settings_service.py`, `notifications/settings_service.py`, `promos/admin_service.py`).

### What exists today

| System | Storage | Admin UI / API | Notes |
|--------|---------|----------------|-------|
| Email / SMTP | `email_provider_settings` (admin DB) | `/admin/email/settings` · `GET/PATCH /api/v1/admin/email/settings` (+ test/activate/disable) | Fernet via `EMAIL_SETTINGS_ENCRYPTION_KEY` on host |
| Browser push / VAPID | `push_provider_settings` | `/admin/push/settings` · `/api/v1/admin/push/settings*` | Private key encrypted; never returned |
| AI | **Env-only** `AI_*` on `Settings`; tables `ai_prompt_templates`, `ai_usage_logs` only | Host/admin AI generate surfaces — **no AI provider settings table** | `AI_API_KEY` stays env (Class A) |
| Payments | **Env-only** Paystack keys on `Settings` | No payment-settings table; payment rows are transactions | Secrets Class A; public key Class D |
| Ambassadors | `ambassador_platform_settings` singleton (`enabled`) | `/promos/admin/settings` + admin ambassadors UI | Not an env flag |

Host-scoped settings (`message_settings`, `fan_connect_settings`, etc.) are **out of scope** for platform runtime settings.

### What stays (do not migrate)

- All SMTP / VAPID ciphertext and specialist CRUD  
- Paystack / `SECRET_KEY` / Fernet boot key on `.env`  
- Ambassador platform enable on its singleton table  
- AI API key on env until a deliberate future design (not this phase)

### What `runtime_settings` owns

- **Class B tunables only** (workers, rate limits, merch TTLs, analytics windows, soft product strings, attachment **limits**, etc.)  
- Optional future allowlisted non-boot secrets only if explicitly added to the registry (none of SMTP/VAPID/Paystack/SECRET in v1)

### Why migrate is deferred

- Specialist modules already have encryption, masking, audit, test endpoints, and worker merge logic.  
- Duplicating SMTP/VAPID into `runtime_settings` doubles secret surfaces and drift risk.  
- Boot and payment safety validators already assume env/`Settings`.  
- Least-risk path: hub + adapters; revisit migration only with an explicit later phase.

---

## §16 — Backend API (shipped)

Base path: **`/api/v1/admin/settings/runtime`** (`backend/app/runtime_settings/router.py`). Also documented in [API.md](./API.md).

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| `GET` | `/api/v1/admin/settings/runtime` | `admin.settings.view` | List allowlisted settings (grouped); secrets as `masked_value` only |
| `GET` | `/api/v1/admin/settings/runtime/status` | `view_system_status` or `view` | Class D / system status |
| `GET` | `/api/v1/admin/settings/runtime/audit` | `view_audit` | Settings audit entries |
| `GET` | `/api/v1/admin/settings/runtime/{category}` | `view` | Category list |
| `PUT` | `/api/v1/admin/settings/runtime/{category}/{key}` | `edit_runtime` (+ `edit_secrets` if secret) | Upsert; body `{ value?, clear?, reason? }` |
| `DELETE` | `/api/v1/admin/settings/runtime/{category}/{key}/override` | `clear_overrides` (+ `edit_secrets` if secret) | Clear DB override → env/default |
| `POST` | `/api/v1/admin/settings/runtime/{category}/test` | `test_integrations` | Safe category test |

### Secret response example

```json
{
  "key": "example_optional_secret",
  "category": "integrations",
  "is_secret": true,
  "configured": true,
  "masked_value": "Configured · ending in 9f3c",
  "source": "db",
  "editable": true
}
```

Never include full secrets or raw env values.

---

## §17 — Test actions

Permission: `admin.settings.test_integrations` (or `admin.full_access`).  
All tests **audited**, **safe**, **no secrets logged**.

| Domain | Behavior |
|--------|----------|
| Email | Use existing test-send path; no credential echo |
| Push | Fixed safe copy via existing test endpoints |
| AI | Connectivity/status only; no key material in logs |
| Payments | **No real charge** — config/verify status only |
| Storage | Tiny object upload/delete **only if** provider safely supports it; else status-only |
| Maps | Status-only (frontend key is build-time) |

---

## §18 — Audit logs

Actions (settings domain):

- `runtime_setting_updated`
- `runtime_secret_replaced`
- `runtime_setting_cleared_to_env`
- `runtime_setting_tested`
- `runtime_setting_validation_failed`
- `runtime_setting_viewed_sensitive_status`

Suggested detail fields:

| Field | Notes |
|-------|-------|
| `admin_user_id` | Actor |
| `category` / `key` | Registry identity |
| `action` | One of the above |
| `old_source` / `new_source` | `db` \| `env` \| `default` |
| `old_value_masked` / `new_value_masked` | Never full secrets |
| `reason` | Optional |
| `ip_address` / `user_agent` | Request meta |
| `created_at` | Timestamp |

**Never log full secrets or raw env values.** Prefer existing `audit_logs` + action string convention used by email/push admin.

---

## §19 — Safety and startup rules

- Startup **does not depend** on DB `runtime_settings`.  
- Process must start with DB + boot-critical envs even if optional settings are missing.  
- Graceful degrade for email / push / AI / payments / storage when unconfigured.  
- Admin UI states: `missing` · `disabled` · `needs configuration` · `using env fallback` · `using DB override`.

Production validators on `Settings` (`APP_ENV`, `DEBUG`, `DEMO_MODE`, `SECRET_KEY`, CORS, `FRONTEND_URL`, etc.) remain authoritative — unchanged by this feature.

---

## §20 — Explicit non-goals (v1)

- No raw `.env` upload/editor  
- No editing Class A from admin  
- No plaintext secrets in API/UI/logs  
- No migrating Paystack / AI / QR / `SECRET_KEY` / Fernet boot key into editable admin  
- No migrating email SMTP or push VAPID into `runtime_settings`  
- Do not rebuild email/push specialist UIs — hub links / thin adapters only  
- Do not invent S3/Cloudinary/Slack/reCAPTCHA/`MAINTENANCE_MODE` until product asks  

---

## Summary / follow-ups

**Done:** registry + `RuntimeSettingsService` + APIs + FE hub + `admin.settings.*` seed + companion docs ([SETTINGS.md](./SETTINGS.md), [ENVIRONMENT.md](./ENVIRONMENT.md), [ADMIN.md](./ADMIN.md), [API.md](./API.md), [DATABASE.md](./DATABASE.md), [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md), [CRUD_MATRIX.md](./CRUD_MATRIX.md), [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md), [SECURITY.md](./SECURITY.md)).

**Keep locked (§15):** specialist tables remain SoT for Class C (email/push).

**Still incremental:** dedicated pytest coverage; wire more hot-path consumers to the resolver; tighten `.env.example` comments for Class A vs B.
