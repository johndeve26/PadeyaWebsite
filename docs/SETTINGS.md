# Admin Runtime Settings

Brand: **Pàdéyá**. Canonical inventory and product decisions: [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md).  
Related: [ADMIN.md](./ADMIN.md) · [ENVIRONMENT.md](./ENVIRONMENT.md) · [SECURITY.md](./SECURITY.md) · [API.md](./API.md) · [OPERATIONS.md](./OPERATIONS.md).

**Status (2026-07-20):** Module shipped in code — `backend/app/runtime_settings/` (model, registry, service, router, migration `20260720_0089`), FE hub under `/admin/settings/runtime*`, permissions seeded as `admin.settings.*`. Dedicated pytest suite may still be landing; treat consumer wiring (workers reading via resolver) as incremental.

---

## Architecture decision (locked)

| Concern | Owner |
|---------|--------|
| Class B tunables (workers, rate limits, merch TTLs, analytics windows, soft product strings, attachment **limits**) | `runtime_settings` table + Admin Runtime Settings UI |
| Email SMTP / provider secrets | Keep `email_provider_settings` + `/admin/email/settings` |
| Push VAPID / provider | Keep `push_provider_settings` + `/admin/push/settings` |
| Boot-critical Class A | `.env` / `Settings` only — never admin-editable |
| Unify UX | Runtime Settings hub links / thin adapters — **do not** migrate SMTP/VAPID into `runtime_settings` |

---

## Classes at a glance

| Class | Meaning | Admin |
|-------|---------|-------|
| **A** | Boot-critical / infra | Never editable — status only |
| **B** | Optional non-secret | Editable via Runtime Settings |
| **C** | Optional secret | Specialist UIs (email/push); masked |
| **D** | Read-only status | Visible, not editable |
| **E** | Deprecated / alias | Document only |

Full key lists: [ADMIN_RUNTIME_SETTINGS_AUDIT.md](./ADMIN_RUNTIME_SETTINGS_AUDIT.md) · [ENVIRONMENT.md](./ENVIRONMENT.md).

---

## Resolution order (`RuntimeSettingsService`)

For allowlisted optional keys:

1. DB `runtime_settings` row (present + valid)  
2. Environment / `Settings` fallback  
3. Registry code default  
4. Missing / unconfigured (secrets → `None` / “Not configured”)

Rules:

- Class A is always read from `get_settings()` / `.env` — never from the DB table.
- Specialist keys (`managed_by=email_provider_settings|push_provider_settings`) read/write through existing specialist services; no duplicate secret columns in `runtime_settings`.
- In-memory cache (~30s); invalidated on admin update / clear.
- Resolve failures degrade to default / `None` — **never crash startup**.

---

## Secret masking

Admin API and UI show **only**:

- `Configured · ending in ####`
- `Not configured`

No reveal endpoint. No plaintext in responses or audit details. Blank secret on save keeps the existing value; clear override falls back to env/default.

---

## Permissions

| Code | Intent |
|------|--------|
| `admin.settings.view` | Hub + category list (non-secrets + masks) |
| `admin.settings.edit_runtime` | Edit Class B overrides |
| `admin.settings.edit_secrets` | Replace/clear allowlisted optional secrets |
| `admin.settings.test_integrations` | Safe category tests |
| `admin.settings.view_system_status` | System status panel |
| `admin.settings.clear_overrides` | Delete DB override → env/default |
| `admin.settings.view_audit` | Settings audit table |

`super_admin` via `admin.full_access` satisfies all. Support gets view/status by default; finance gets view/status + `edit_runtime` (not secrets). Every mutation is audited.

---

## Surfaces

| Layer | Path |
|-------|------|
| FE hub | `/admin/settings` → `/admin/settings/runtime` |
| FE category | `/admin/settings/runtime/[category]` |
| FE audit | `/admin/settings/runtime/audit` |
| API | `/api/v1/admin/settings/runtime*` — see [API.md](./API.md) |
| Module | `backend/app/runtime_settings/` |
| Registry | `backend/app/runtime_settings/registry.py` (allowlist — not a free-form `.env` editor) |

Categories (registry): `runtime`, `email`, `push`, `ai`, `payments`, `notifications`, `storage`, `integrations`, `security-runtime`, `system-status`.

---

## Startup safety

- Process start depends on Class A env + DB connectivity — **not** on rows in `runtime_settings`.
- Missing optional settings → graceful degrade (email/push/AI/payments/storage).
- Production validators on `Settings` (`APP_ENV`, `DEBUG`, `DEMO_MODE`, `SECRET_KEY`, CORS, `FRONTEND_URL`, …) remain authoritative.
