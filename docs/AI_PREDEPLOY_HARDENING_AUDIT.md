# Pàdéyá AI — pre-deploy hardening audit

**Date:** 2026-07-22  
**Scope:** Pre-deploy hardening audit; **follow-up fixes applied** (announcement context, legacy quarantine, Control Center fan section, docs).  
**Brand:** Pàdéyá  

**Implemented product keys in scope (24):**

| Group | Keys |
|-------|------|
| Host | `host.event.title`, `host.event.description`, `host.merch.title`, `host.merch.description`, `host.merch.category`, `host.merch.tags`, `host.announcements.draft`, `host.sponsorship.pitch` |
| Fan | `fan.passport.bio` |
| Support | `support.ticket.triage`, `support.ticket.summary`, `support.ticket.reply_draft`, `support.ticket.priority`, `support.ticket.article_suggestions` |
| Admin | `admin.support.queue_summary`, `admin.analytics.revenue_summary`, `admin.reports.summary`, `admin.operations.daily_summary` |
| Blog | `admin.blog.title`, `admin.blog.outline`, `admin.blog.excerpt`, `admin.blog.seo_meta`, `admin.blog.social_snippets`, `admin.blog.tags` |

**Primary code references:** `backend/app/ai/constants.py`, `seed.py`, `service.py`, `feature_routing.py`, `feature_status.py`, `output_validation.py`, `context_scrubber.py`, `admin_controls.py`, `safety.py`, `frontend/src/app/admin/ai/features/page.tsx`.

---

## Executive verdict

| Area | Status |
|------|--------|
| Registry for 24 canonical keys | **Mostly consistent** — see legacy/extra keys below |
| Future / blocked keys | **Correctly non-runnable** |
| Templates + routing slugs | **Ready** for all 24 |
| Context allowlists (canonical 24) | **Generally sound** — legacy host path is weaker |
| Output validation (canonical 24) | **Dedicated validators present** |
| Human-review / no auto-execute | **API flags and UI patterns align** |
| Permissions | **Mostly correct** — minor gaps documented |
| Audit / usage logging | **Strong** — safe log API omits prompts |
| Control Center | **Active Fan** section shows `fan.passport.bio` |
| **Production readiness** | **Ready for controlled production** — smoke validation **passed** (§11). |

---

## 11. Final production smoke validation (2026-07-22)

**Method:** Automated backend smoke suite (`backend/tests/test_ai.py`, `backend/tests/test_ai_production_smoke.py`) against the test database; Alembic revision check on PostgreSQL; static UI verification for Control Center grouping.

**Result:** **PASS** (15/15 tests). No remaining code blockers from the hardening audit.

### 1. Migrations and seed

| Check | Result |
|-------|--------|
| Alembic at head | **PASS** — `20260722_0128` (includes `0127_ai_control_center`, `0128_ai_feature_auto_models`) |
| AI prompt templates for 24 canonical slugs | **PASS** — `test_templates_and_routes_seeded` |
| Feature routes for 24 + 2 future keys | **PASS** — `list_feature_routes_public` |
| Future keys disabled / blocked | **PASS** — `enabled=false`, `product_status=blocked`, `routing_editable=false` |
| Legacy/quarantined default toggles | **PASS** — all `False` in `DEFAULT_FEATURE_ENABLED` |

### 2. Provider setup

| Check | Result |
|-------|--------|
| Template fallback provider seeded | **PASS** — `ensure_default_provider_profiles` |
| Admin controls overview API | **PASS** — `GET /api/v1/ai/admin/controls/overview` |
| Global kill switch | **PASS** — `AI_KILL_SWITCH=1` → generate **503** |
| Network provider / env key | **Not exercised in smoke** — configure in deploy env + `/admin/ai/providers`; unrouted primary shows **Needs configuration** per `operational_status_for_route` |

### 3. Feature routing (canonical draft features)

Generate allowlist and templates confirmed for all **24** keys in `ADMIN_CONTROL_FEATURES` (host event/merch, announcements, sponsorship, fan passport, support×5, admin summaries×4, blog×6). Per-feature provider/model assignment remains an **operator** step in Control Center.

### 4. Draft-only behavior

| Check | Result |
|-------|--------|
| `can_auto_publish` / `can_auto_send` / `can_modify_finance` | **PASS** — false on successful host generate (`test_usage_logging`) |
| No auto-publish/send/refund/moderation endpoints in AI router | **PASS** — unchanged product invariant (code review + API surface) |

### 5. Blocked / quarantined behavior

| Key / set | Expected | Result |
|-----------|----------|--------|
| `fan.connect.explanation`, `discovery.why_recommended` | Not generatable | **PASS** — 400/403 (`test_future_ai_keys_not_generatable`) |
| `LEGACY_HOST_AI_FEATURES` | HTTP 403 | **PASS** — e.g. `generate_email_announcement` |
| `ADMIN_QUARANTINED_AI_FEATURES` | HTTP 403 | **PASS** — e.g. `recommend_featured_events`, `fraud_risk_summary` |

### 6. Logs and safety

| Check | Result |
|-------|--------|
| Usage log on generate | **PASS** — `AIUsageLog` row, correct `host_id`, `feature_key` |
| Meta: validation, latency, cost | **PASS** — `validation_result`, `latency_ms`, `estimated_cost_micros` |
| Safe admin logs API | **PASS** — `GET /api/v1/ai/admin/controls/logs` — no `system_prompt` / `user_prompt` / raw key patterns in payload |
| Audit on log view | **PASS** — `safe_generation_logs` writes `ai.logs.viewed` when `audit_view=true` |

### 7. UI checks

| Surface | Result |
|---------|--------|
| `/admin/ai/features` — **Active Fan** section | **PASS (static)** — `frontend/src/app/admin/ai/features/page.tsx` |
| Future/blocked rows not editable | **PASS (API)** — `routing_editable=false` for future keys |
| Overview / providers / usage / logs routes | **PASS (API)** — overview + routes + logs exercised; providers/usage pages use same APIs |

**Not run in this pass:** Live browser walkthrough of `/admin/ai/*` (recommend manual spot-check after deploy).

### Smoke conclusion

**Pàdéyá AI is ready for controlled production use** for the **24 canonical draft-only features**, after operators configure provider profiles, per-feature routing, spend caps, and global AI settings. Keep **`fan.connect.explanation`** and **`discovery.why_recommended`** blocked; do not enable legacy or quarantined keys.

### Production preflight integration

Go-live preflight (`backend/scripts/prod_preflight.py`, `GET /api/v1/admin/platform/readiness`) runs the same AI checks via `backend/app/platform/ai_readiness.py`:

- CLI prints **`AI_READY: PASS|WARN|FAIL`** (never secrets).
- Admin **AI readiness** card on `/admin/platform/go-live` mirrors templates, routes, providers, kill switch, blocked/quarantined keys, and spend cap.
- **`AI_KILL_SWITCH`** and template-only provider setups produce **WARN**, not platform **BLOCKED**, unless other non-AI checks fail.

---

*This document is the pre-deploy hardening audit companion to `docs/AI_FEATURE_STATUS_AUDIT.md` and `docs/AI_INTEGRATION_AUDIT.md`.*

---

## 1. Feature registry consistency

### 1.1 Announcement context (fixed)

**`host.announcements.draft`** now uses `HostAnnouncementContextResult` in `announcements_context.py` with named fields `scrubbed_context`, `host_id`, and `redactions`. `service.py` reads those fields directly — no ambiguous tuple unpack.

**Legacy host AI:** Keys in `LEGACY_HOST_AI_FEATURES` are removed from the generate allowlist, default **disabled**, marked **deprecated** in Control Center readiness, and rejected in `generate_suggestion()` with HTTP 403. Revenue/ticket **metrics are no longer attached** to host AI context.

**Admin placeholders:** `recommend_featured_events`, `identify_high_risk_hosts`, and `fraud_risk_summary` are in `ADMIN_QUARANTINED_AI_FEATURES` — not in `ADMIN_FEATURES`, default **disabled**, hard-blocked at generate with HTTP 403.

> **Legacy AI keys are disabled by default and should not be enabled in production without feature-specific context, validation, and routing review.**

### 1.1 (historical) Critical defect — resolved

~~Context builder return tuple mismatch~~ — fixed as above.

### 1.2 Canonical 24 — cross-registry matrix

| Surface | All 24 present? | Notes |
|---------|-----------------|-------|
| `ADMIN_CONTROL_FEATURES` | Yes | Control Center route list |
| `FEATURE_LABELS` | Yes | Duplicate key `host.announcements.draft` appears twice in dict (harmless in Python, sloppy) |
| `DEFAULT_FEATURE_ENABLED` | Yes (all `True`) | Future keys explicitly `False` |
| `FEATURE_TEMPLATE_SLUG` | Yes | Slug = canonical key for all 24 |
| `ensure_templates()` needed list | Yes | Backfills missing slugs on older DBs |
| `seed_ai_prompt_templates()` | Yes | One row per canonical slug (+ legacy aliases) |
| `DEFAULT_FEATURE_PERMISSIONS` | Yes for 23 | `fan.passport.bio` → `[]` (route metadata; enforcement is passport + auth) |
| `feature_group()` / category | Yes | Fan key → `"fan"` |
| Generate allowlists | Yes | Canonical host + fan + support/admin/blog only; legacy/quarantined excluded |
| Docs | Yes | Updated post-hardening |

**Missing from canonical 24 only:** None identified for the shipped keys above.

### 1.3 Extra keys (quarantined — not in the 24-key product list)

| Keys | Where | Status after hardening |
|------|--------|-------------------------|
| Legacy host slugs | `LEGACY_HOST_AI_FEATURES` | Default **off**; **403** at generate; not in `HOST_FEATURES_PUBLIC` |
| Admin placeholders | `ADMIN_QUARANTINED_AI_FEATURES` | Removed from `ADMIN_FEATURES`; default **off**; **403** at generate |
| Legacy admin aliases | `FEATURE_CANONICAL` | Map to canonical admin summary keys — OK when canonical key used |

---

## 2. Future / blocked status

| Key | Generate allowlist | Seed template | Default enabled | Route seed | Control Center edit |
|-----|-------------------|---------------|-----------------|------------|---------------------|
| `fan.connect.explanation` | No (`FAN_FEATURES` only has passport bio) | No | `False` | `status=disabled`, `enabled_default=False` | Blocked — `update_feature_route` rejects `FUTURE_AI_FEATURES`; UI `routing_editable=false` |
| `discovery.why_recommended` | No | No | `False` | Same | Same |

Both are in `FUTURE_AI_FEATURES` and `SAFETY_REVIEW_FEATURES` → **`product_status=blocked`** in Control Center (shown under “Blocked by safety”, not active Future).

They are **not** in `ADMIN_CONTROL_FEATURES` as runnable product keys. Even DB tampering cannot remove the static `future` flag from API responses; generation still fails allowlist checks without templates/context.

---

## 3. Template readiness (24 implemented features)

| Check | Result |
|-------|--------|
| Prompt seed per canonical key | **Pass** — `backend/app/ai/seed.py` slugs match constants |
| Template slug map | **Pass** — `FEATURE_TEMPLATE_SLUG` identity map for all 24 |
| `_get_template()` resolution | Uses slug map + audience (`host` / `admin`; fan passport seed uses fan audience) |
| Structured fields vs frontend | **Pass** for wired UIs — event/merch options, announcement triple, sponsorship blocks, passport options, support fields, blog SEO/social/tags, admin summary text |
| Fallback template provider | **Pass** — `ensure_default_provider_profiles()` seeds `template_fallback`; routes default `template_fallback_enabled=True`; spend cap can force template-only |
| Startup seed | `main.py` lifespan calls `seed_ai_prompt_templates()` when DB available (non-test) |

---

## 4. Context safety (by category)

Global scrubber: `context_scrubber.py` — `FORBIDDEN_CONTEXT_KEYS` drops passwords, tokens, Paystack, QR secrets, buyer PII, vault bodies, admin/CRM notes, raw messages, hidden addresses, etc.

| Category | Builder | Allowlist / behavior | Flags |
|----------|---------|----------------------|-------|
| Event copy | Event studio scrub | Public event fields; venue gated by `location_visibility` | OK for canonical keys |
| Merch | Merch studio scrub | Product + public event bits | OK |
| Announcement | `announcements_context.py` | `ANNOUNCEMENT_SAFE_KEYS`; no recipient PII | OK **once unpack bug fixed** |
| Sponsorship | `sponsorship_context.py` | Public host metrics, public event summaries, no buyer data | OK; aggregate stats from legacy metrics helpers |
| Passport | `passport_context.py` | Bio, public interests, visible badges, optional city stats | OK — no tickets/spend/graph |
| Support | `support_context.py` | Ticket allowlist + conversation body redaction | Staff-only; permission-gated reply draft |
| Admin summaries | `admin_context.py` | `ADMIN_SUMMARY_SAFE_KEYS`; aggregates only | Revenue/reports/queue are **admin-intended** — not fan-facing |
| Blog | `blog_context.py` | `BLOG_STUDIO_SAFE_KEYS` | Draft post fields only |

**Accidental inclusion risks (non-canonical paths):**

- **Legacy host AI** (not in the 24): client `extra` merged then generic `scrub_context` — **no strict allowlist**; **`metrics`** may include revenue/ticket counts (`_host_metrics_context`).
- **Admin placeholder features:** generic `_admin_context()` may expose snapshot JSON depending on feature — still staff-only but less reviewed than canonical admin summaries.

**Fan-facing canonical keys** (`fan.passport.bio`) do not use host metrics or support ticket bodies.

---

## 5. Output validation

| Feature set | Validator | Overclaims / policy / auto-send / refunds / urgency / private echo |
|-------------|-----------|----------------------------------------------------------------------|
| Event title/description | `validate_title_options`, `validate_description` | Shared `BANNED_PHRASES`, `_POLICY_OVERCLAIM`, `_PRIVATE_ECHO` |
| Merch | Merch-specific bans + category/tag validators | Merch overclaim regex |
| Announcement draft | `validate_host_announcement_draft` | Draft structure + banned phrasing |
| Sponsorship pitch | `validate_host_sponsorship_pitch` | Audience/revenue wording guards |
| Passport bio | `validate_fan_passport_bio` | Bio safety patterns |
| Support (5) | Dedicated support validators | Reply draft treated as high-risk copy |
| Admin summaries (4) | `validate_admin_summary` | Advisory tone; banned promises |
| Blog (6) | Blog validators incl. SEO/social/tags | SEO/social in `HIGH_RISK_HUMAN_REVIEW_LOCKED` |

**Gap:** Legacy host/admin keys not in the table above hit `_validate_output` default → **`sanitize_draft_text` only** (lighter than product validators).

---

## 6. Human-review locks (must never auto-execute)

| Action | Enforced how |
|--------|----------------|
| Publish blog | No auto-publish API; `can_auto_publish: false` on all responses; blog UI applies fields manually |
| Send support replies | Draft only; `FEATURE_SUPPORT_REPLY_DRAFT` locked; staff sends via existing support flows |
| Send announcements / sponsor messages | Draft-only components; `can_auto_send: false`; CRM/composer manual send |
| Passport visibility | AI only suggests bio text; save via passport settings |
| Create tickets / change prices / refunds / payouts / suspensions | **No AI endpoints** perform these; `can_modify_finance: false` |

**`HIGH_RISK_HUMAN_REVIEW_LOCKED`:** reply draft, blog SEO/social, announcements, sponsorship, passport bio — Control Center cannot turn off `requires_human_review` for these (`safety.py`).

**Note:** Host event/merch canonical keys are **not** in `HIGH_RISK_HUMAN_REVIEW_LOCKED` but still return draft-only flags and studio “apply to field” UX (not publish/send).

---

## 7. Permissions

| Surface | Enforcement |
|---------|-------------|
| Host AI | `require_user_host`; event/merch `event.host_id` check; `ai.use_own` or `admin.full_access` on generate |
| Fan passport | `assert_can_edit_passport`; `/ai/fan/passport` on impersonation block list; no `ai.use_own` (fans) |
| Support AI | `ai.use_platform` + generate; ticket loaded server-side; **reply draft** → `assert_support_reply_permission` |
| Admin summaries | `ai.use_platform` + per-feature checks in `admin_context._assert_feature_permission` (support view, analytics, reports, daily ops) |
| Blog AI | `assert_blog_ai_permission` in `blog_context` |
| Impersonation | Fan passport AI blocked; host/admin paths rely on broader impersonation middleware for sensitive routes |

**Gaps / notes:**

- `DEFAULT_FEATURE_PERMISSIONS` for `fan.passport.bio` is empty on route rows — informational; real gate is auth + passport restrictions.
- `FEATURE_ADMIN_DAILY_OPS` route permissions list only `ai.use_platform`, but context build requires **`analytics.view_platform`** (stricter at generation time — good).

---

## 8. Audit and usage logging

| Event | Location |
|-------|----------|
| Generation success | `AIUsageLog` + audit `ai.generation_created` |
| Generation failure (incl. validation) | Failed log + audit `ai.generation_failed` |
| Feedback applied/dismissed | `record_generation_feedback` → audit `ai.generation_applied` / `ai.generation_dismissed` |

**Logged fields (typical):** `feature_key`, actor `user_id`, `host_id` (when correct), resource ids in `meta` (`event_id`, `merch_product_id`, `support_ticket_id`, `blog_post_id`), `provider`, `model_name`, `latency_ms`, `estimated_cost_micros`, `validation_result`, `redaction_applied`, `redaction_actions`, `used_fallback`, `prompt_template_slug` (not full prompt text).

**Frontend feedback wiring:** Host studio/merch/announcements/sponsorship → `recordHostAIGenerationFeedback`; fan passport → `recordFanAIGenerationFeedback`; support + blog + admin summaries → `recordAdminAIGenerationFeedback`.

**Safe logs API:** `safe_generation_logs()` returns metadata only — **no user/system prompt bodies**.

---

## 9. AI Control Center

| Check | Result |
|-------|--------|
| Provider/model per feature | Edit modal when `routing_editable`; primary/fallback + template fallback flag |
| Missing provider / key | `operational_status=needs_configuration` via `_provider_needs_configuration` |
| Future rows | Not editable (`routing_editable=false`); PATCH blocked in `safety.update_feature_route` |
| Blocked safety rows | Both future keys show blocked badge + safety note |
| Usage dashboard | Aggregates `AIUsageLog` by `feature_key` — includes any key that ran |
| Logs privacy | No prompt text in list API |

**UI gap:** ~~`fan.passport.bio`~~ — **Fixed:** **Active Fan** section on `/admin/ai/features`.

---

## 10. Deployment readiness checklist

Run after deploy (in order):

1. **Database migrations** — at minimum `20260722_0127_ai_control_center.py`, `20260722_0128_ai_feature_auto_models.py` (see `docs/DATABASE.md` AI tables).
2. **Prompt template seed** — automatic on app boot (`seed_ai_prompt_templates`); confirm non-empty `ai_prompt_templates` for all 24 slugs.
3. **Feature route seed** — opening Control Center or calling routes API runs `get_or_create_feature_route()` for `ADMIN_CONTROL_FEATURES` + future keys.
4. **Provider setup** — create/enable provider profiles in `/admin/ai` (or env `AI_API_KEY` profile); assign primary per feature; template fallback remains last resort.
5. **Global AI switch** — platform setting `ai_enabled` (and env `AI_ENABLED` where used); note: **`generate_suggestion` checks `AI_KILL_SWITCH` but not `ai_enabled`** — network path uses routed profiles; disable features or kill switch for hard off.
6. **Env kill switch** — verify `AI_KILL_SWITCH` unset/false in production unless incident response.
7. **Optional hardening** — set `AI_DISABLED_FEATURES` for legacy host/placeholder admin keys not wanted in prod.
8. **Fix announcement context unpack** before enabling `host.announcements.draft` in production.

---

## Summary tables

### Ready areas

- Canonical 24-key registry, seeds, templates, and `_validate_output` coverage.
- Future/blocked keys isolated from generation pipeline.
- Draft-only response contract (`can_auto_publish`, `can_auto_send`, `can_modify_finance` all false).
- Support/admin/blog permission layering and safe generation log API.
- Impersonation guard for fan passport AI path.

### Risks found (post-fix)

| Severity | Item | Status |
|----------|------|--------|
| ~~Blocker~~ | Announcement context unpack | **Fixed** — `HostAnnouncementContextResult` |
| ~~Medium~~ | Legacy host AI default-on + metrics | **Mitigated** — quarantined, metrics removed |
| ~~Medium~~ | `recommend_featured_events` default on | **Mitigated** — quarantined + 403 at generate |
| ~~Low~~ | Fan Control Center section | **Fixed** — Active Fan |
| ~~Low~~ | Stale five future keys doc | **Fixed** in status audit |
| **Low** | Global `ai_enabled` not checked at start of every generate | Open — use kill switch + toggles |

### Missing mappings

- None for the 24 canonical keys across constants, labels, defaults, permissions (except empty fan permission list by design), template slugs, Control Center list, and seed.
- **Not mapped to product UI / strict readiness:** legacy host keys and three admin placeholder keys (by design).

### Unsafe context risks (canonical 24)

- **Low** with dedicated builders. Legacy keys cannot run via generate API after quarantine.

### Validation gaps

- Quarantined legacy/placeholder keys are not reachable in production generate paths.

### Permission gaps

- Minor: route `allowed_permissions` vs runtime checks for fan passport and daily ops (runtime is stricter or alternate path).

### Required deploy steps

See §10 (migrations → seed → routes → providers → global switch → kill switch verification). Legacy keys remain off by default — do not re-enable without review.

### Is AI ready for production?

**Yes, for the 24 canonical keys**, subject to operational setup (provider profiles, per-feature routes, spend caps, global AI settings, `AI_KILL_SWITCH` off). Automated smoke validation **passed** — see **§11**. **`host.announcements.draft`**, **`host.sponsorship.pitch`**, and **`fan.passport.bio`** are active with dedicated context and validation. **`fan.connect.explanation`** and **`discovery.why_recommended`** remain **blocked by safety** and must not be enabled. **Legacy host** and **admin quarantined** keys remain **disabled** and return HTTP 403 if invoked.

---

*This document is the pre-deploy hardening audit companion to `docs/AI_FEATURE_STATUS_AUDIT.md` and `docs/AI_INTEGRATION_AUDIT.md`.*
