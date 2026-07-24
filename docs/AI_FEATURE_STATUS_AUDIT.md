# Pàdéyá AI feature status audit — “Future” in the Control Center

**Date:** 2026-07-22 (updated after pre-deploy hardening fixes)  
**Scope:** Audit of Future/blocked keys and shipped canonical AI; reflects post-hardening registry.  
**Brand:** Pàdéyá

---

## Executive summary

In the AI Control Center, **“Future” / “Blocked by safety”** are **compile-time registry flags** in `FUTURE_AI_FEATURES` and `SAFETY_REVIEW_FEATURES`. **`FUTURE_AI_FEATURES` contains two keys** (`fan.connect.explanation`, `discovery.why_recommended`). Both are **blocked by safety** in the UI — not wired to generation, templates, or product UI.

**Shipped canonical keys (24)** including **`host.announcements.draft`**, **`host.sponsorship.pitch`**, and **`fan.passport.bio`** are **active** in Control Center and product UI when global AI and per-feature routes are configured.

**Legacy host AI keys** (`generate_email_announcement`, pricing helpers, etc.) and **admin quarantined keys** (`recommend_featured_events`, …) are **disabled by default**, **not** on the generate allowlist, and **must not be enabled in production** without feature-specific context, validation, and routing review.

---

## 1. Where “Future” is defined

| Layer | Location | Behavior |
|--------|-----------|----------|
| **Backend registry** | `backend/app/ai/constants.py` — `FUTURE_AI_FEATURES` | **Two** keys — Control Center placeholders; disabled by default |
| **Labels** | `FEATURE_LABELS` in same file | Suffix `(future)` on blocked discovery/connect keys |
| **Default toggles** | `DEFAULT_FEATURE_ENABLED` | Both future keys **`False`**; **`LEGACY_HOST_AI_FEATURES`** and **`ADMIN_QUARANTINED_AI_FEATURES`** **`False`** |
| **Permissions** | `DEFAULT_FEATURE_PERMISSIONS` | **No entries** for future keys (empty if ever resolved) |
| **Template map** | `FEATURE_TEMPLATE_SLUG` | **No entries** for future keys |
| **Canonical aliases** | `FEATURE_CANONICAL` | **No entries** for future keys |
| **Phase 1 admin list** | `ADMIN_CONTROL_FEATURES` | **Excludes** future keys (only shipped Phase 1 keys) |
| **Feature routing seed** | `backend/app/ai/feature_routing.py` — `get_or_create_feature_route()` | If key ∈ `FUTURE_AI_FEATURES`: force `enabled_default = False`, `status="disabled"` |
| **Public route list** | `list_feature_routes_public()` | Sets `"future": key in FUTURE_AI_FEATURES`; `"enabled"` = `route.enabled AND status != "disabled"` (so Future rows always show as not operationally enabled) |
| **Safety overview** | `backend/app/ai/safety.py` | Exposes `future_features: list(FUTURE_AI_FEATURES)` |
| **DB table** | `ai_feature_routes` | Rows created on first list/edit; `status` column stores `"disabled"` for future seeds (not the string `"future"`) |
| **Legacy config table** | `ai_feature_configs` | Not seeded for future keys unless legacy `/admin/controls/features` path creates them |
| **Frontend constants** | **None** — no duplicate list in `frontend/` | UI uses API field `future: boolean` on each route |
| **Control Center UI** | `frontend/src/app/admin/ai/features/page.tsx` | If `row.future` → `<Badge>Future</Badge>` **instead of** On/Off (even if `enabled` were true in DB) |

There is **no** Alembic seed exclusively for Future keys; rows appear when an admin opens **Feature routing** or the routes API runs `get_or_create_feature_route()`.

---

## 2. What “Future” means today (and what it does not)

| Interpretation | Applies? | Evidence |
|----------------|----------|----------|
| Planned but not implemented | **Yes (primary meaning)** | Keys exist for routing/safety visibility only; no templates, no generate allowlist |
| Implemented but disabled | **No** | No end-to-end implementation for these keys |
| Backend exists, frontend missing | **Partially** | Generic `/api/v1/ai/host/generate` and `/admin/...` exist, but **these keys are not allowlisted** |
| Frontend exists, backend missing | **No** | No UI calls these `feature_key` strings |
| Disabled by product phase | **Yes** | Aligns with `docs/AI_INTEGRATION_AUDIT.md` Phase 2–3 deferrals |
| Disabled by feature toggle only | **Partially** | `DEFAULT_FEATURE_ENABLED` + route `status="disabled"`; also **hard-coded Future set** |
| Placeholder only | **Yes** | Registry + Control Center row + safety list |

**Important distinctions:**

- **`future` (API boolean)** — membership in `FUTURE_AI_FEATURES` (static until code changes).
- **`status` (DB)** — `"disabled"` on seed for future keys; can be PATCHed to `"active"` via `/admin/controls/routes/{feature_key}`, but that **does not** remove the `future` flag from API responses.
- **`enabled` (DB)** — toggle in edit modal; for Future keys, effective operational enablement is still blocked by `status == "disabled"` in `route_enabled()` unless an operator changes both.
- **“Needs configuration”** — used for **provider health**, not for Future features.

---

## 3. Feature-by-feature readiness

Legend: **Generate pipeline** = `generate_suggestion()` → template → context → provider → validation → `AIUsageLog`.

| Feature key | Label (UI) | UI status badge | Backend generate allowlist | Prompt template | Dedicated context builder | Feature-specific validation | Product UI entrypoint | Control Center route row | Usage/audit if called | Safe to enable now? | Reason |
|-------------|------------|-----------------|----------------------------|-----------------|---------------------------|----------------------------|------------------------|---------------------------|------------------------|---------------------|--------|
| `host.sponsorship.pitch` | Draft sponsorship pitch | **Active** | **Yes** | **Yes** | **Yes** (`sponsorship_context.py`) | **Yes** | `/host/sponsorships`, slot composer | **Yes** | **Yes** when global AI on | **Yes** | Shipped — draft-only; no auto-send to sponsors |
| `host.announcements.draft` | Draft host announcement | **Active** | **Yes** | **Yes** | **Yes** | **Yes** | `/host/announcements/new` | **Yes** | **Yes** | **Yes** | Shipped — draft-only |
| `fan.passport.bio` | Improve Fan Passport bio | **Active** | **Yes** | **Yes** | **Yes** (`passport_context.py`) | **Yes** | `/dashboard/passport/settings` | **Yes** | **Yes** when global AI on | **Yes** | Shipped — draft-only; manual save |
| `fan.connect.explanation` | Fan Connect explanation (future) | **Blocked by safety** | **No** | **No** | **No** | **No** | Connect — **no AI** | **Yes** | N/A | **No** | Safety review required |
| `discovery.why_recommended` | Discovery why recommended (future) | **Blocked by safety** | **No** | **No** | **No** | **No** | Discovery — **no AI** | **Yes** | N/A | **No** | Deferred Phase 3+ |

### Detail notes per feature

**`host.sponsorship.pitch`**  
- Shipped: `backend/app/ai/sponsorship_context.py`, `validate_host_sponsorship_pitch`, composer on `/host/sponsorships` and slot form. Draft-only; human review locked.

**`host.announcements.draft`**  
- Shipped: `HostAnnouncementContextResult` in `announcements_context.py` (named context fields). Draft composer on `/host/announcements/new`. Human review locked.

**Legacy host AI** (e.g. `generate_email_announcement`) — **not** the same as `host.announcements.draft`. Legacy slugs are in `LEGACY_HOST_AI_FEATURES`: **disabled by default**, **403** at generate, removed from host catalog API. Use Event Studio / announcements composer instead.

**`fan.passport.bio`**  
- Shipped: `POST /ai/fan/passport/generate`, `passport_context.py`, **Improve with AI** on Passport settings. Draft-only; human review locked.

**`fan.connect.explanation`**  
- Distinct from **`discovery.why_recommended`** and from **Fan Connect ranking** (explicitly out of scope in project rules).  
- Even “explanation” copy touches eligibility narrative — treat as **high policy sensitivity**.

**`discovery.why_recommended`**  
- `docs/AI_INTEGRATION_AUDIT.md` §5 / §16: personalized discovery and recommendations **avoid for now**.  
- Should remain **blocked_by_safety / future** until rules-first discovery exists.

---

## 4. Recommended status model

Use **one primary operational status** per feature (stored or derived), plus **tags** where needed. Avoid overloading “Future” with “off” or “misconfigured.”

| Status | Definition | Operator meaning |
|--------|------------|------------------|
| **active** | Implemented end-to-end; allowed to run when globally on, provider healthy, and route `enabled` | Normal production use |
| **disabled** | Fully implemented; deliberately off (toggle/env/route) | Turn on when ready |
| **needs_configuration** | Implemented but blocked on missing provider, model, or API key | Fix providers/keys |
| **future** | Not shipped; no template/generate/UI contract | Do not enable; plan work first |
| **partially_implemented** | Some of: template, context, UI, validation (list which in admin) | Engineering in progress |
| **blocked_by_safety** | Policy or risk gate (e.g. auto-send, ranking, discovery) | Requires legal/product sign-off |
| **blocked_by_provider** | Hard dependency on provider capability not available | Wait for provider or adapter |
| **deprecated** | Replaced by another key; kept for audit/history | Migrate routing; do not expand |

**Mapping from today:**

| Current signal | Recommended label |
|--------------|-------------------|
| `key in FUTURE_AI_FEATURES` | **future** |
| Phase 1 keys, `enabled=false` | **disabled** |
| Phase 1 keys, provider/key missing | **needs_configuration** |
| `discovery.why_recommended`, Fan Connect ranking-style work | **blocked_by_safety** (+ **future** until built) |
| `generate_email_announcement` vs `host.announcements.draft` | **partially_implemented** / **deprecated** alias story when consolidating keys |

---

## 5. UI recommendations (Control Center)

**Implemented (2026-07-22):** `/admin/ai/features` now separates **Product status** and **Operational status**, groups Future and safety-blocked features into dedicated sections, locks routing for Future keys, and exposes an implementation readiness checklist in the details drawer. See `backend/app/ai/feature_status.py` for server-side labels.

**Problem (resolved):** The **Future** badge previously hid **On/Off**, so operators could not tell “not built” from “built but off.” Edit routing still allowed toggling **Feature enabled** on Future rows, which was **misleading**.

**Recommended copy**

| Badge | Tooltip / helper text |
|-------|------------------------|
| **Future** | “Planned capability — not connected to Pàdéyá AI yet. Enabling here does not activate product UI or generation.” |
| **Off** | “Implemented — turned off in routing.” |
| **On** | “Implemented — active when global AI and provider health allow.” |
| **Needs configuration** | “Implemented — assign a working provider and API key.” |
| **Blocked (safety)** | “Unavailable by product policy until review.” |
| **Partial** | “In development — some of template, context, or UI missing.” |

**UX changes (when implementing — not done in this audit)**

1. ~~Show **Future** as a **read-only** ribbon; separate **Operational** badge~~ **Done**
2. ~~Disable **Feature enabled** toggle~~ **Done** (drawer + API reject PATCH)
3. ~~Add section **“Future & blocked”**~~ **Done**
4. Link each row to this doc — **Done** (header alert + drawer reference)
5. On **Safety**, clarify `future_features` = registry placeholders

---

## 6. Next safe implementation order

Based on existing product surfaces and `docs/AI_INTEGRATION_AUDIT.md` (Phase / privacy / human review):

| Order | Feature key | Rationale |
|-------|-------------|-----------|
| 1 | `host.announcements.draft` | Align with CRM announcements + existing `generate_email_announcement` pattern; host-only; never auto-send |
| 2 | `host.sponsorship.pitch` | Sponsorship host UI exists; public metrics only in context; draft-only |
| 3 | `fan.passport.bio` | Requires **fan AI API** + passport scrubber; medium privacy; human review |
| 4 | `fan.connect.explanation` | Only after explicit product sign-off; must not alter ranking/eligibility |
| — | `discovery.why_recommended` | **Stay blocked** until rules-first discovery; Phase 3+ |

**Should stay blocked for now**

- `discovery.why_recommended` (recommendation/explanation surface)  
- Any enablement that implies **Fan Connect ranking** or **discovery personalization** without new safety review  
- Turning on Future keys in routing **without** removing from `FUTURE_AI_FEATURES` and completing template + allowlist + UI (would still fail or confuse)

---

## 7. Code references (quick index)

| Concern | File |
|---------|------|
| Future registry | `backend/app/ai/constants.py` — `FUTURE_AI_FEATURES`, `DEFAULT_FEATURE_ENABLED`, `FEATURE_LABELS` |
| Route seeding | `backend/app/ai/feature_routing.py` — `get_or_create_feature_route`, `list_feature_routes_public`, `route_enabled` |
| Generate gate | `backend/app/ai/service.py` — `generate_suggestion` (`HOST_FEATURES` / `ADMIN_FEATURES` allowlist) |
| Templates | `backend/app/ai/service.py` — `_get_template`; `backend/app/ai/seed.py` — no future slugs |
| Toggles | `backend/app/ai/feature_toggles.py` — `assert_feature_enabled` |
| Safety list | `backend/app/ai/safety.py` — `future_features` |
| UI badge | `frontend/src/app/admin/ai/features/page.tsx` — `row.future` |
| Product deferrals | `docs/AI_INTEGRATION_AUDIT.md` — §5, §16, Fan/Discovery tables |

---

## 8. Summary table (blocked / future keys)

| Key | Implemented? | Placeholder? | Enable in Control Center safe? |
|-----|--------------|--------------|--------------------------------|
| `host.sponsorship.pitch` | **Yes** | No | **Yes** (when global AI on) |
| `host.announcements.draft` | **Yes** | No | **Yes** (when global AI on; human review locked) |
| `fan.passport.bio` | **Yes** | No | **Yes** — shown under **Active Fan** in Control Center |
| `fan.connect.explanation` | No | Yes (blocked) | **No** |
| `discovery.why_recommended` | No | Yes (blocked) | **No** |

Promoting blocked keys requires: remove from `FUTURE_AI_FEATURES` / safety set, add to shipped allowlists, seed prompts, dedicated context + validation, product UI, and update this document.

## 9. Legacy and quarantined keys (not in the 24)

| Set | Examples | Production |
|-----|----------|------------|
| `LEGACY_HOST_AI_FEATURES` | `generate_email_announcement`, `suggest_ticket_pricing`, … | **Disabled** — 403 at generate; deprecated in readiness |
| `ADMIN_QUARANTINED_AI_FEATURES` | `recommend_featured_events`, `fraud_risk_summary`, … | **Disabled** — featured/recommendation AI not allowed without safety review |

> Legacy AI keys are disabled by default and should not be enabled in production without feature-specific context, validation, and routing review.
