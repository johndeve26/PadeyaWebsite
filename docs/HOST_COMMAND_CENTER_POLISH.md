# Host Command Center polish — Pàdéyá

**Status: completed (2026-07-20)**  
**Scope: frontend-only polish** — no route moves, no Personal↔Host data merge, no backend permission model changes.

Related: [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) · [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md) · [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md).

---

## Summary

`/host` already shipped as the Host Command Center. This pass polished framing, desk safety, labels, and permission-gated CTAs **without rebuilding** the Command Center.

| Invariant | Result |
| --- | --- |
| Routes | **Unchanged** — Personal `/dashboard/*` · Host `/host/*` · Admin `/admin/*` · Support `/support/*` |
| Permissions | **Unchanged** — existing helpers only (`canScanTickets`, `canScanMerch`, `canAccessHostPath`, desk nav filters) |
| Owner CC | Still owner-only (`OwnerCommandCenter`); host admins stay on `MemberDeskOverview` |
| Phase 2 chrome | Preserved (Personal top-nav, public Hosts, switcher, vertical sidebar, mobile drawer) |

---

## What was polished

### 1. Owner Command Center header

- Eyebrow: **Host Command Center**
- H1: **Overview** (shell already shows `Host: {name}`)
- Verified / Unverified + status badges kept
- Ops-focused description; bio/location as secondary meta
- CTA: **Legacy Page** (not “Legacy studio”)
- No in-body workspace switcher

### 2. Member overview

- Eyebrow: **Overview**
- Role/action titles (Scanner workspace, Merch pickup desk, Sponsor workspace, Read-only host workspace, …)
- Desk CTAs → `/host/desk`; viewers with event access → `/host/events`
- `OwnerCommandCenter` remains **`is_owner` only**

### 3. Today’s operations actions

- Scanner → `canScanTickets` only
- Pickup → `canScanMerch` only (not unlocked by `merch.view`)
- Optional `assignedEventIds` for `selected_events` desk scope
- Defaults closed without grants

### 4. Host switch refetch

- Data effects depend on `active?.host_id`
- Clear stale snapshot + cancel in-flight fetches on Host A → Host B
- Parent remount: `OwnerCommandCenter key={active.host_id}`

### 5. Pending tasks label

- Eyebrow: **Needs attention** (not Inbox — avoids clash with Host Inbox)

### 6. `/host/events` grid desk safety

- Desk staff coerced off Grid → Table (`effectiveViewMode`)
- Grid toggle hidden for desk-focused staff
- Assigned events only via `fetchWorkspaceDeskEvents`
- Grid cards reuse `HostEventRowActions` (scanner-only / merch-only / desk matrix)
- No Edit / Delete / Tickets / Analytics for desk-constrained roles
- Desk cards skip portfolio analytics/revenue fetch

### 7. Event action labels (routes unchanged)

| Label | Path |
| --- | --- |
| Merch Studio | `/host/events/[id]/merchandise` |
| Ambassador Campaigns | `/host/events/[id]/ambassadors` |

Also updated event ops nav chips (`EventOpsNav`) and Upcoming row Merch Studio CTA.

### 8. Host sidebar labels (already shipped; preserved)

**Home:** Overview · Roadmap  
**Operate:** Events · Tickets & Entry · Merch Studio · Host Inbox  
**Grow:** Ambassador Campaigns · Sponsorships · Audience CRM · Legacy Page · Vault Studio  
**Manage:** Analytics · Host Team · Host Settings · Support  

Public marketplace stays **Hosts** → `/hosts` (not renamed).

---

## Explicit non-goals (this pass)

- Rebuild `/host` or remount full CC for host admins
- Move routes or add `/dashboard/host`
- Merge buyer tickets/orders into host home
- Weaken `HostAccessGuard` / `canAccessHostPath`
- Backend alembic / permission grant changes

---

## Verification

From `frontend/`:

```bash
npm run lint
npm run build
npm run test:pwa
npm run test:theme
npm run test:host-command-center
npm run test:workspace-privacy
npm run test:buyer-dashboard-nav   # nav chrome
```

Backend pytest **skipped** (frontend-only). Manual route checklist: [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md#host-command-center-polish).
