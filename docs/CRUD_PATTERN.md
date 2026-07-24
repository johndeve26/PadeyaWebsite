# Pàdéyá CRUD / lifecycle pattern

Reusable pattern for every new resource. Companion inventory: [`CRUD_MATRIX.md`](./CRUD_MATRIX.md).  
Permission catalog: `backend/app/users/constants.py`.

## Non-negotiable: lifecycle is never optional

**Every current and future product module must have a complete lifecycle plan before merge.**

CRUD is not optional. “We only need a create endpoint” is incomplete.  
If a resource is intentionally **read-only**, **append-only**, or **immutable** (security/finance), that is still a lifecycle plan — it must be **written down and enforced**, not skipped.

A complete lifecycle plan answers, for each resource:

| Concern | Must document |
|---|---|
| Create | Who can create? How? Or: *system-only / never* + why |
| Read / list | Who can read? Public vs owner vs admin? Private fields? |
| Update | Who can update? Which statuses? Or: *immutable after create* + why |
| End-of-life | Archive / cancel / deactivate / withdraw / reverse — **or** *no delete ever* + why |
| Restore | Supported? Who? Or: *not restorable* + why |
| Permissions | Codes + roles |
| Commerce / history | What if orders, payments, tickets, or evidence exist? |
| Audit | Which actions write audit logs? |
| Frontend | List/detail/actions — or admin/system-only with no buyer UI + why |
| Tests | Create/read/update/lifecycle **or** immutability/append-only guards |

**Acceptable end-of-life modes** (pick one and enforce it):

1. Full CRUD with archive/restore  
2. Soft lifecycle (cancel / deactivate / hide) without hard delete  
3. Append-only (corrections via new rows / reversals)  
4. Immutable after create (read + maybe status transitions only)  
5. System-generated only (no user create; documented producers)

Skipping the plan, or shipping create without read/update/end-of-life decisions, is a defect.

**Principle:** CRUD does not always mean physical delete. Prefer status transitions (draft → active → archived / cancelled / deactivated) for anything with commerce, trust, or audit history. Prefer documenting “no hard delete” over leaving DELETE undefined.

---

## 1. Model status fields

Add only fields that fit the resource. Stay consistent with existing models.

| Field | When to add |
|---|---|
| `status` | Almost always — string lifecycle (`draft`, `active`, `published`, `cancelled`, `archived`, …) |
| `archived_at` / `archived_by` | Soft end-of-life you may restore |
| `is_archived` | Only if boolean is clearer than `status` + `archived_at` (prefer timestamps) |
| `deleted_at` | Soft delete already used in that domain; do not invent a second soft-delete style |
| `created_at` / `updated_at` | Always (`server_default=now()`, `onupdate` for updated) |
| `created_by` / `updated_by` | Host/admin-owned resources where attribution matters |
| Domain timestamps | e.g. `cancelled_at`, `published_at`, `deactivated_at`, `reviewed_at` |

**Do not** add finance/audit hard-delete columns. Immutable tables (payments, ledger, audit_logs, payout evidence) stay append-only or status-only.

Suggested SQLAlchemy shape:

```python
status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
created_by: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
updated_by: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
archived_by: Mapped[uuid.UUID | None] = mapped_column(
    Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False
)
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
)
```

Alembic: one focused migration per resource wave. Register the model in `alembic/env.py` and `tests/conftest.py`.

---

## 2. Route conventions

API prefix: `/api/v1`. Prefer REST + explicit lifecycle actions.

### Core CRUD

```http
GET    /resource
POST   /resource
GET    /resource/{id}
PATCH  /resource/{id}
DELETE /resource/{id}          # only when hard delete is allowed; else return 405
```

### Lifecycle actions (preferred over overloaded DELETE)

```http
POST /resource/{id}/archive
POST /resource/{id}/restore
POST /resource/{id}/cancel
POST /resource/{id}/deactivate
POST /resource/{id}/publish
POST /resource/{id}/submit
POST /resource/{id}/approve
POST /resource/{id}/reject
POST /resource/{id}/hide
POST /resource/{id}/moderate
```

### Ownership / admin nesting

| Audience | Pattern | Example |
|---|---|---|
| Host self | `/hosts/me/...` or `/resource` scoped in service | `/hosts/me/team` |
| Buyer self | `/resource/mine` or ownership check | `/vault/subscriptions/mine` |
| Admin | `/admin/...` or `/resource/admin/...` | `/admin/audit-logs`, `/hosts/admin/verifications` |
| Public read | No auth or optional auth; never leak private fields | `/cms/blog`, `/events` |

Return **405** with a clear message when hard delete is blocked (`Hard delete blocked; use POST .../archive`).

---

## 3. Permission naming

Format: `{resource}.{action}` or `{resource}.{action}_{scope}`.

Examples from the catalog:

- `events.create`, `events.update_own`, `events.archive_own`, `events.approve`
- `ticket_types.deactivate`, `ticket_types.delete_unused`
- `tickets.read_own`, `tickets.transfer`, `tickets.scan`
- `vault.moderate`, `vault.restore`
- `refunds.approve`, `payouts.mark_paid`, `support.escalate`
- `admin.full_access` — super-admin umbrella (implies all checks)

**Rules:**

1. Add new codes to `DEFAULT_PERMISSIONS` and `REQUIRED_PERMISSION_CODES` in `backend/app/users/constants.py`.
2. Grant via `ROLE_PERMISSIONS` (buyer / host / host_staff / support_agent / finance_admin / super_admin).
3. Prefer granular codes; keep umbrellas (`events.manage_own`) only when routers still need them — document in `PERMISSION_IMPLIES`.
4. Invariants:
   - Hosts **cannot** delete reviews.
   - Support **cannot** modify finance / mark payouts paid.
   - `payouts.mark_paid` → super_admin only.

Seed updates apply on boot (`seed_roles_and_permissions`) and in tests via `conftest`.

---

## 4. Service-layer pattern

Keep routers thin. Put logic in `{domain}/service.py` or focused `*_service.py` files.

Required functions (names may vary, behavior should not):

| Function | Responsibility |
|---|---|
| `create_resource` | Validate input, set status, set `created_by`, audit if sensitive |
| `get_resource` | Load + ownership/role check; 404 if out of scope |
| `list_resources` | Filters (`status`, `include_archived`); default hide archived |
| `update_resource` | Block updates on archived unless restored; set `updated_by` |
| `archive_or_delete_resource` | Prefer archive; hard delete only when safe |
| `restore_resource` | Clear archive fields; restore prior status when meaningful |
| Permission / ownership helpers | `require_user_host`, `user_has_permission`, role gates |
| Audit | `write_audit_log(...)` for sensitive transitions |

**Service checklist:**

- Never trust the client for payment success or privileged status jumps.
- If related orders/tickets/payments exist → cancel/archive/deactivate, do not hard delete.
- Public serializers must strip secrets (access codes, full bank numbers, hidden venue links **and** private street addresses / online meeting URLs).
- Raise `HTTPException` with stable, user-safe messages.

### Nested Event Studio subresources

Prefer **upsert-by-id** on parent `PATCH` over blind replace-all when children need stable IDs:

| Child | Sync rule | End-of-life |
|---|---|---|
| Agenda / people | Upsert rows that include `id`; create when missing | Omit → hard delete (no commerce refs) |
| Checkout questions | Same upsert | Drop unused → hard delete; drop answered → **archive** (`status` + `archived_at`); keep already-archived |
| Gallery media | Sync by URL list **or** dedicated `DELETE .../media/{id}` | Hard delete row; clear matching banner fields |
| Ticket types | **Separate** CRUD routes (not nested array replace) | Deactivate after sales; hard delete only if sold/reserved = 0 |

Computed read models (e.g. `publish_checklist`) are **not** tables — document as system/computed in [CRUD_MATRIX.md](./CRUD_MATRIX.md) and never invent persistence for client-only flags like `preview_checked`.

Pydantic schemas per resource:

- `Create`, `Update`, `Public` (read)
- List query/filter params
- Action bodies when needed (`Reject` with `notes`, moderate payload)

---

## 5. Frontend list / detail / create / edit / archive pattern

Stack: Next.js App Router under `frontend/src/app/`, API clients in `frontend/src/lib/*-api.ts`, UI kit in `frontend/src/components/ui/`.

### List page

- `DashboardShell` + `PageHeader` / eyebrow
- Search / status filter when useful (`FilterBar`, `SearchBar`, `Select`)
- `DataTable` (auto mobile cards) **or** card grid
- `StatusBadge` for lifecycle
- `EmptyState` with optional create CTA
- Create button only if the user can create

### Detail page

- Summary (status, key fields, timestamps)
- Related records / links
- Lifecycle status badge
- Actions gated by status **and** permission (hide what the user cannot do)

### Create form

- Validation (required fields, JSON/domain rules)
- Helper / hint text on inputs
- Loading (`busy` / disabled submit)
- Error (`Alert` + toast)
- Success (toast + redirect or list refresh)

### Edit form

- Prefill from GET
- Save / update button
- `useUnsavedChanges(dirty)` when the form is non-trivial
- Block edit while archived (prompt restore first)

### Archive / deactivate / cancel / delete

- `ConfirmAction` modal — never bare `window.confirm` for lifecycle
- Explain consequences in the description
- `requireReason` for sensitive admin/finance/moderation actions
- Loading state on confirm; success/error `useToast`
- Do not render the action if status/permission forbids it

### Restore

- `ConfirmAction` + permission check
- Only when `archived_at` / inactive status allows restore

### Mobile

- Prefer `DataTable` (table ≥ `lg`, cards below)
- Keep action buttons wrapping (`flex flex-wrap gap-2`)
- Avoid horizontal overflow on list toolbars

### API client

```ts
// frontend/src/lib/{domain}-api.ts
export async function archiveThing(id: string) {
  return apiRequest(`/things/${id}/archive`, { method: "POST" });
}
```

Add nav entries in `frontend/src/lib/nav/workspace.ts` and overview hubs when the surface is operator-facing.

---

## 6. Hard delete vs soft delete vs archive

| Strategy | Use when | Examples |
|---|---|---|
| **Hard delete** | No commerce/history refs; truly disposable draft | Unused ticket type (0 sold/reserved); unused checkout question; unused agenda/person; draft event with no sales; draft vault with no purchases |
| **Archive** | End-of-life but retain history; may restore | Checkout questions with answers; host team; bank accounts; event templates; CMS posts; completed events |
| **Cancel / deactivate** | Stop activity without removing the row | Events with sales; ticket types after sales; promos; ambassadors; announcements; subscriptions |
| **Never delete** | Money, audit, evidence, issued tickets with history | Payments, ledger, refunds, payouts, evidence, audit_logs, webhook events, `order_checkout_answers` |

Default choice for a new host/admin resource: **archive + restore**, `DELETE` → 405.

If payments/orders/tickets reference the row: **cancel/deactivate/archive only**.

---

## 7. Audit log requirements

Use `write_audit_log` from `app.core.audit`.

**Always audit:**

- Admin approve / reject / moderate / hide / feature
- Finance: refund decisions, payout review/approve/reject/mark-paid, evidence attach
- Host verification review
- Sensitive archive/restore of trust or money-adjacent resources (bank accounts, team, payouts)
- User deactivate / restore

**Usually audit:**

- Create/update that changes money, access, or public trust (events publish path, vault moderate, review withdraw by admin)

**Optional / skip:**

- High-volume read-only list
- Pure draft autosave noise (batch into meaningful saves if needed)

Admin read API: `GET /admin/audit-logs` (immutable — no update/delete endpoints).

Include `actor_user_id`, `action` (`domain.verb`), `resource_type`, `resource_id`, and safe `details` (no secrets/full PANs).

---

## 8. Tests required for every new resource

Add backend tests (FastAPI `TestClient` + seeded roles) covering:

| Case | Assert |
|---|---|
| Create | 201 + persisted fields / status |
| Read / list | 200; filters; archived hidden by default |
| Update | 200; rejected when archived if that is the rule |
| Delete / archive / deactivate | Correct status transition |
| Restore | Clears archive; status back to usable |
| Ownership | Other host/buyer → 403/404 |
| Role restrictions | Wrong role → 403 |
| Unsafe hard-delete blocked | 405 (or explicit business error) when history exists |
| Audit | `AuditLog` row for required actions |

Frontend: at minimum smoke that the route renders for an authorized shell; prefer exercising ConfirmAction-gated flows when the resource is operator-critical. Event Studio: `npm run test:studio` (routes/stepper/preview/privacy/mobile shell).

For Event Studio / location privacy also cover: public address redaction, buyer reveal after payment, SEO scrub, ticket deactivate-vs-delete, discard blocked with sales, checkout question required validation (`tests/test_event_studio_lifecycle.py`).

Register new ORM models in `backend/tests/conftest.py` so SQLite create_all includes them.

---

## Backend file layout (new domain)

```text
backend/app/{domain}/
  models.py
  schemas.py
  service.py          # or create_service / archive_service splits
  router.py
backend/alembic/versions/YYYYMMDD_NNNN_{domain}.py
backend/tests/test_{domain}_lifecycle.py
```

Wire router in `backend/app/main.py`.

---

## Frontend file layout (new surface)

```text
frontend/src/lib/types/{domain}.ts
frontend/src/lib/{domain}-api.ts
frontend/src/app/{host|admin|dashboard|support}/{resource}/page.tsx          # list
frontend/src/app/.../{resource}/new/page.tsx                                 # create (optional)
frontend/src/app/.../{resource}/[id]/page.tsx                                # detail/edit
```

Reuse: `ConfirmAction`, `DataTable`, `EmptyState`, `StatusBadge`, `useToast`, `useUnsavedChanges`.

---

## Developer checklist

For **every** current or future feature, answer before merging.  
“N/A — intentional” is allowed **only with a reason** (e.g. append-only ledger). Blank answers are not.

1. **Can users create it?** — Who? Which permission? Which create schema/UI? Or system-only / never + why?
2. **Can users view/list it?** — Public vs owner vs admin filters? Private fields stripped?
3. **Can users edit it?** — Which statuses allow PATCH? Prefill + unsaved warning? Or immutable + why?
4. **Can users delete/archive/cancel it?** — Which verb? Confirm modal + consequences? Or never + why?
5. **Can it be restored?** — `POST .../restore` + permission + UI action? Or not restorable + why?
6. **Who has permission?** — Codes added to catalog + role grants + router/service checks?
7. **What happens if it has payments/orders/history?** — Block hard delete; cancel/archive/reverse only?
8. **Does it need audit logs?** — Which actions call `write_audit_log`? Or none + why?
9. **Does it expose private data?** — Bank numbers, access codes, hidden venues, PII?
10. **Does it need frontend actions?** — List/detail/create/edit + lifecycle buttons? Or operator/system-only + why?
11. **Does it need tests?** — Create/read/update/lifecycle/ownership/roles/hard-delete **or** immutability/append-only guards?

If any answer is unclear, default to: **no hard delete, archive + restore, audit sensitive changes, hide unauthorized actions, add lifecycle tests.**  
Update [`CRUD_MATRIX.md`](./CRUD_MATRIX.md) in the same change.

---

## Quick “done” definition

A resource is lifecycle-complete when:

- [ ] Lifecycle plan documented (matrix row + answers above — including intentional read-only/append-only)  
- [ ] Model + migration + schemas exist (or N/A justified for computed/seed-only)  
- [ ] Service enforces ownership/roles and the chosen end-of-life mode  
- [ ] REST + lifecycle routes match conventions (or explicit 405 / no-delete)  
- [ ] Permissions seeded and granted (or system-only documented)  
- [ ] Audit written where required  
- [ ] Frontend list/detail/actions exist where humans operate the resource, with ConfirmAction for destructive/lifecycle ops  
- [ ] Tests cover the chosen mode (mutable lifecycle **or** immutability/append-only)  
- [ ] `CRUD_MATRIX.md` status updated — never leave a product module as “missing” without an owner plan  
