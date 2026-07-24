# Host team permissions

Brand: **Pàdéyá**. Product overview: [TEAMS.md](./TEAMS.md). Platform RBAC (buyer/host/admin roles): [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md).

Host-team permissions are **org toggles** on `host_team_members` / `host_team_invites` (`permissions_json`), separate from global RBAC codes like `tickets.scan`.

## Enforcement entrypoint

| Helper | Package | Use |
|---|---|---|
| `has_host_permission` | `app.teams.permissions` | Host-scoped action (no event) |
| `has_event_permission` | same | Hybrid host + scope + staff |
| `can_scan_ticket` / `can_scan_merch_pickup` | same | Desk allow/deny |
| `require_host_permission` / `require_event_permission` | same | Raise 403 (+ sensitive denial audit) |
| `require_host_for_permission` | `app.hosts.team_access` | Resolve workspace + permission for team routes |

Do **not** rely on hiding buttons in the UI.

## Role presets → defaults

Presets live in `app.hosts.team_permissions` (`ROLE_DEFAULTS`, `permissions_for_role`). Desk scan keys default **off** for Admin/Scanner/Merch host-wide; use selected events + staff sync.

| Preset | Seeds (summary) |
|---|---|
| **Owner** | Not a preset — full access via `is_host_owner` |
| `admin` | Near-full host ops; Ambassadors campaign + approve/reject/reverse; **not** desk scan, payout/bank, mark-paid, or export |
| `event_manager` | `events.*`, ticket ops (desk off), `analytics.view_events`, `ambassadors.view` + `view_conversions` |
| `ambassador_manager` | Ambassadors campaign/participant/conversion/payout view + approve/reject/reverse; mark-paid off |
| `finance_manager` | `finance.view_sales_summary` · `view_payouts` · `manage_payouts` + `ambassadors.view_payouts` · `mark_rewards_paid` |
| `scanner` | `events.view`, `tickets.view` (desk via scope/staff) |
| `merch_staff` | `events.view`, `merch.view` (desk via scope/staff) |
| `support_staff` | View + messages |
| `sponsor_manager` | Sponsors (+ sponsor analytics) |
| `viewer` | Read-only views — **no** `ambassadors.view` unless granted |

## Permission catalog (toggles)

| Group | Keys |
|---|---|
| Events | `events.view` · `create` · `edit` · `publish` · `cancel` · `archive` |
| Tickets | `tickets.view` · `scan_qr` · `check_in` · `manage_pricing` · `manage_capacity` · `export_attendees` · `view_refunds` |
| Merch | `merch.view` · `create` · `edit` · `manage_inventory` · `scan_pickup_qr` · `mark_picked_up` · `manage_shipping` · `manage_discounts` · `manage_bundles` |
| Messages | `messages.view` · `reply` · `manage_templates` · `report_or_escalate` |
| Sponsors | `sponsors.view` · `reply` · `manage_slots` · `accept_or_reject` |
| Analytics | `analytics.view_events` · `view_merch` · `view_sponsors` · `export` |
| Team | `team.view` · `invite` · `edit_permissions` · `remove_members` |
| Finance | `finance.view_sales_summary` · `view_payouts` · `manage_payouts` · `manage_payout_settings` |
| Ambassadors | `ambassadors.view` · `create_campaigns` · `edit_campaigns` · `pause_campaigns` · `remove_participants` · `view_conversions` · `view_payouts` · `approve_rewards` · `reject_rewards` · `mark_rewards_paid` · `reverse_rewards` · `export` |

Reward / payout-sensitive Ambassadors actions default **off** on role presets — host owner grants explicitly. Host owner always may manage rewards on host-owned campaigns via `/host/ambassadors/conversions*` (**no** `admin.full_access` required). Platform admin endpoint remains for oversight/fraud/platform campaigns only — not the exclusive path for host-owned rewards. Platform campaigns remain admin-only.

Cross-rules: approve/reject → `ambassadors.approve_rewards` (reject also accepts `reject_rewards`); mark paid → `ambassadors.mark_rewards_paid` **or** `finance.manage_payouts`; export → `ambassadors.export` **or** `finance.view_payouts`. See [AMBASSADORS.md](./AMBASSADORS.md).

**Team member reward approval:** active member with the matching toggle may approve / reject / mark paid / reverse on the host’s campaigns. Suspended/removed members and members without the toggle are denied (403). FE toggles show a hint that reward/payout permissions let the member approve or mark Ambassadors rewards paid — backend still enforces.

**Not the same as host-balance payouts:** `ambassadors.mark_rewards_paid` records off-platform settlement meta on the conversion; it does **not** mark platform `payouts` paid (super-admin + evidence only — [PAYMENTS.md](./PAYMENTS.md)).

APIs: `GET /host/team/permissions`, `GET /host/team/roles`.

## Scope interaction

| Scope | Effect on toggles |
|---|---|
| `host_wide` | Permission applies to all events under the host |
| `selected_events` | Event-bound permissions need event id in `scope_json.event_ids` **or** a covering staff assignment |

Hybrid evaluation order for desk: owner → (active membership not suspended/removed) → staff row → active team + permission + scope. See [TEAMS.md](./TEAMS.md#hybrid-scan-authorization).

## Enforced vs stored

| Area | Status |
|---|---|
| Team routes (`team.*`) | **Enforced** |
| Ticket desk (`tickets.scan_qr` / `check_in`) | **Enforced** (hybrid) |
| Merch desk (`merch.scan_pickup_qr` / `mark_picked_up`) | **Enforced** (hybrid) |
| Shipping reveal (`merch.manage_shipping`) | **Enforced** on decrypt |
| Finance / bank APIs | **Owner-only** in v1 (flags stored for future grant path) |
| Ambassadors rewards | **Enforced** on `/host/ambassadors/conversions*` (+ audit / flag / reward-audit; admin oversight separate) |
| Ambassadors campaigns / participants / analytics | **Enforced** via `require_host_for_permission` on host Ambassadors routes |
| Other catalog keys | Stored + FE-gated; domain modules enforce as they land |

## Owner-only / sensitive

- `finance.manage_payout_settings` — non-owners cannot enable on a membership
- Granting `finance.view_payouts` / `manage_payout_settings` writes `hosts.team_finance_permission_grant` audit
- Denied attempts for sensitive keys write `hosts.team_permission_denied` (see `SENSITIVE_PERMISSIONS` in `app.teams.team_audit`)

## Frontend gating

| Helper | File |
|---|---|
| `hasHostPermission` / `canScanTickets` / `canScanMerch` / `canAccessHostPath` | `frontend/src/lib/host-access.ts` |
| `hostHomePathForWorkspace` / `isDeskFocusedStaff` / `isScannerOnlyStaff` / `isMerchOnlyStaff` / `isHostReadOnlyMember` | `frontend/src/lib/host-access.ts` |
| `navGroupsForWorkspace` / `navForWorkspace` | `frontend/src/lib/nav/host-nav.ts` |
| Role + toggle UI | `frontend/src/lib/host-team-roles.ts` · `TeamPermissionToggles` |

Members hitting blocked paths land on `/host/access-denied`.

### Role-aware Command Center UX

Canonical host home is **`/host`** (Host Command Center). **`/host/dashboard`** is a **308** alias only — not a second home.

| Actor | Default landing | Sidebar (primary nav) |
|---|---|---|
| **Host owner** | `/host` | Full **Home / Operate / Grow / Manage** groups |
| **Desk-focused scanner / merch** (`isDeskFocusedStaff`) | `/host/desk` | Minimal **Operate** — Tickets & Entry, Events (filtered to assignments), Merch when granted; **no** Roadmap, Grow, or Manage |
| **Scanner-only** (`isScannerOnlyStaff`) | `/host/desk` | Same minimal Operate; event list row actions → View + Scanner only |
| **Merch-only** (`isMerchOnlyStaff`) | `/host/desk` | Operate + Merch; row actions → Merch / pickup tools |
| **Sponsor manager** (with sponsor perms) | `/host/sponsorships` | Permission-gated Grow + Manage subset |
| **Viewer / read-only** (`isHostReadOnlyMember`) | `/host` | Overview + granted read modules; Roadmap hidden |
| **Platform admin** | `/admin` — not host workspace | Separate admin shell |

**Roadmap** (`/host/roadmap`): owner and members with `events.create` / `events.edit` / `team.invite`; denied for desk-focused and read-only members.

**Path guards:** `canAccessHostPath` mirrors nav rules — e.g. `/host/payouts` and `/host/bank-accounts` deny all non-owners in v1; check-in paths require ticket scan perms; Legacy/Vault/promos require `events.edit` / `team.edit_permissions` (or owner).

Workspace switcher and post-invite CTAs use `hostHomePathForWorkspace`. See [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md#host-command-center).
