# Pàdéyá AI Assistant (Ask Pàdéyá / Pàdéyá Copilot)

Conversational public concierge and authenticated dashboard copilot. One backend system; product naming is context-aware.

| Mode | Product name | Audience |
|------|--------------|----------|
| Public (logged out) | **Ask Pàdéyá** | Visitors |
| Authenticated | **Pàdéyá Copilot** | Fans, hosts, ambassadors, sponsors, admins |

Existing **AI Control Center** (`backend/app/ai/`) remains the provider/router for draft Copilot features. This assistant **reuses** `get_ai_provider` / scrubbing / kill-switch patterns and does **not** duplicate provider HTTP clients.

Feature flags default **OFF**. Do not enable in production until migration, knowledge sync, and staged rollout below are complete.

---

## Architecture

```
Browser widget (lazy)
  → POST /api/v1/assistant/chat/stream (SSE)
    → feature flags + rate limit + session
    → intent classify (deterministic first)
    → tool registry (RBAC server-side)
    → knowledge FTS retrieve (sitemap/pages)
    → live structured APIs (events, tickets, …)
    → provider complete (or deterministic fallback)
    → structured envelope (answer, citations, cards, actions)
```

**Domains**

| Area | Path |
|------|------|
| Assistant package | `backend/app/assistant/` |
| Knowledge (sitemap/FTS) | `backend/app/assistant/knowledge/` |
| Tools | `backend/app/assistant/tools/` |
| Route registries | `backend/app/assistant/routes/` |
| Widget | `frontend/src/components/assistant/` |
| Migration | `20260805_0220_assistant_tables` |

---

## Public vs authenticated modes

**Public:** discover events/pages, explain product areas, cite public sources, open Support Center. No account data.

**Authenticated:** dashboard navigation, permitted account summaries, drafts, Level‑4 confirmed mutations only when `assistant_actions_enabled`. Never invent account state.

---

## Source hierarchy

1. **Live structured APIs** — prices, availability, tickets, orders, earnings (never sitemap HTML).
2. **Route registries** — validated navigation (public + role-aware).
3. **Knowledge index** — sitemap-ingested public pages + Help/Resources text (untrusted content; cannot override system rules).
4. **Deterministic fallbacks** — when the model provider is down: event search + route lookup + support links still work.

---

## Sitemap ingestion

- CLI: `python -m scripts.sync_assistant_knowledge`
- Requires `ASSISTANT_KNOWLEDGE_SYNC_ENABLED=true`
- Parses sitemap index + nested urlsets; same-origin only; excludes private prefixes (`/admin`, `/dashboard`, `/checkout`, auth, API, …)
- Content hash; update only when changed; archive missing; FTS chunks (no pgvector in v1)
- **Not** run inside Alembic migrations

Admin:

- `POST /api/v1/admin/assistant/knowledge/sync` (`admin.ai.manage_settings`)
- `GET /api/v1/admin/assistant/knowledge/status`

---

## Tool safety levels

| Level | Meaning | Confirmation |
|------:|---------|--------------|
| 0 | Information | No |
| 1 | Navigation | No |
| 2 | Private read | Auth + RBAC |
| 3 | Draft / prepare | User review |
| 4 | Low-risk mutation | Explicit confirmation card + idempotency |
| 5 | High-risk | **Never execute** — explain + navigate only |

Level 5 examples: publish/cancel event, refunds, payouts, bank details, delete account, mass messages, finance ledger changes, suspend users.

---

## Confirmation policy

Level 4 tools return a confirmation payload (`action_id`, tool, sanitized args, effect, expiry, idempotency key, user binding). Confirm revalidates auth and executes once. The model must never claim success before the tool confirms.

---

## Role matrix (assistant)

| Role | Navigate | Private read | Draft | Confirmed mutate | Finance / admin mutate |
|------|----------|--------------|-------|------------------|------------------------|
| Anonymous | Public | — | — | — | — |
| Fan | Own dashboard | Own tickets/orders/saved | Support draft | Save/follow (when enabled) | — |
| Host | Host workspace | Own events/sales summaries | Event description / draft | Unpublished draft (when enabled) | — |
| Ambassador | Ambassador area | Own links/earnings | — | — | — |
| Sponsor | Sponsor workspace | Own applications | Pitch draft | — | — |
| Admin | Admin pages | Permitted reads | — | — | **Forbidden via chat** |

All tool authorization is server-derived from the authenticated user. Model-supplied role/user/entity claims are ignored.

---

## Privacy & retention

- Redact secrets/PII before provider calls (`privacy.py` + AI scrubber patterns).
- Anonymous HttpOnly session cookie; short retention (`assistant_public_session_retention_hours`).
- Authenticated sessions: `assistant_session_retention_days`.
- Do not log raw message bodies in standard app logs; operational metrics use trace IDs, tool names, latency, prompt version.
- Clear conversation supported via session delete.

Cleanup CLI: `python -m scripts.cleanup_assistant_sessions`

---

## Prompt-injection defence

Crawled pages, event descriptions, Memories captions, and tool text are **untrusted data**. They cannot redefine the assistant role, authorize tools, or override RBAC. System instructions are versioned server-side (`assistant-system-v1`); prompt version is recorded in traces, not shown publicly.

---

## Model routing

Reuses the **AI Control Center** via feature key `platform.assistant.chat`:

1. **Admin → Pàdéyá AI → Providers** — configure primary network provider + model (same as Host/Fan Copilot).
2. **Admin → Pàdéyá AI → Features** — enable `platform.assistant.chat` and assign primary/fallback providers.
3. **Env** — `AI_ENABLED=true`, `AI_API_KEY=…`, and optional `AI_PROVIDER` / `AI_MODEL` for the default env-backed profile.

The assistant does **not** read frontend env vars. If Control Center is configured but chat still uses template fallback, check backend logs for `assistant.provider_fallback` (missing key, wrong model, or provider HTTP error). Template fallback keeps event search + navigation working when the network provider is down or spend-capped.

Do not retry mutations blindly.

---

## Streaming

`POST /api/v1/assistant/chat/stream` — SSE events: `session`, `status`, `token`, `citation`, `card`, `action`, `tool_started`, `tool_completed`, `confirmation`, `done`, `error`. Private tool arguments are not streamed.

---

## Rate limits

| Audience | Default |
|----------|---------|
| Anonymous | 30 / hour |
| Authenticated | 120 / hour |

Separate Redis keys; friendly 429 without infrastructure detail.

---

## Support escalation

Uses existing Support Center / `support.service`. Offer Support Center, draft ticket (Level 3), create after confirm (Level 4). Never fabricate SLA or claim submission before backend confirmation.

---

## Analytics (safe)

`assistant_open`, `assistant_close`, `assistant_message_sent`, `assistant_new_chat`, plus backend-ready names for cards/confirmations/escalation. **Never** attach raw messages, email, balances, or ticket bodies.

---

## Feature flags

| Env | Default | Effect |
|-----|---------|--------|
| `ASSISTANT_ENABLED` | false | Global kill |
| `ASSISTANT_PUBLIC_ENABLED` | false | Ask Pàdéyá |
| `ASSISTANT_AUTHENTICATED_ENABLED` | false | Copilot reads |
| `ASSISTANT_ACTIONS_ENABLED` | false | Level 4 mutations |
| `ASSISTANT_EVENT_SEARCH_ENABLED` | true* | Live event tools (*when assistant on) |
| `ASSISTANT_SUPPORT_DRAFTS_ENABLED` | false | Support drafts |
| `ASSISTANT_ADMIN_ENABLED` | false | Admin assistant surface |
| `ASSISTANT_KNOWLEDGE_SYNC_ENABLED` | false | Sync job gate |

Hiding the widget in the frontend is **not** security — tools enforce flags server-side.

---

## Widget UI

- Lazy `PadeyaAssistantLoader` in root layout
- Hidden on checkout paths
- Desktop: bottom-right launcher + panel
- Mobile: full-screen / bottom sheet with safe areas
- No auto-open on load

---

## How to add a tool

1. Define `ToolDefinition` in `tools/registry.py` (safety level, auth, permissions, confirmation).
2. Implement handler in the appropriate `tools/*.py` module (call existing domain services only).
3. Register in `tools/executor.py`.
4. Add auth + IDOR tests.
5. Do not expose unfinished tools behind enabled flags.

## How to add a route

1. Add entry to `routes/public_registry.py` or `routes/auth_registry.py` (key, path, roles, synonyms, intents).
2. Navigation tools resolve only registry keys — never model-invented URLs.

## How to add a knowledge source

1. Ensure the URL is public, same-origin, and not in the forbidden prefix list.
2. Publish/update content on the site; run knowledge sync (or rely on scheduled sync).
3. Live prices/availability must still use APIs, not page text.

---

## Failure modes

| Failure | Behavior |
|---------|----------|
| Provider down | Deterministic event search + routes + support links |
| Rate limit | Friendly retry message |
| Tool denied | Explain permission; no data leak |
| Low confidence | Uncertain + navigation options + Support |
| Flag off | 404 / widget hidden |

---

## Deployment & rollback (when approved)

1. Apply migration `20260805_0220`.
2. Deploy backend with all assistant flags **false**.
3. Run sitemap knowledge sync; verify status.
4. Enable public for internal testers → verify search/citations/support.
5. Deploy frontend widget (already inert when flags off).
6. Enable authenticated read-only → verify RBAC boundaries.
7. Enable confirmed actions only after read-only verification.
8. Keep finance/admin mutations disabled forever in chat.

**Rollback:** set `ASSISTANT_ENABLED=false` (or more specific flags). Core site is independent of the widget.

---

## Tests & eval

- `backend/tests/test_assistant_*.py`
- `backend/tests/eval/assistant_eval_cases.json`
- Frontend: `checkout-guard.test.ts`, `welcome-prompts.test.ts`
- Playwright: `frontend/e2e/assistant-public.spec.ts`

See also: `docs/AI_INTEGRATION_AUDIT.md` (feature Copilot), `docs/CRUD_MATRIX.md` (Assistant section), `docs/ROLES_AND_PERMISSIONS.md`.
