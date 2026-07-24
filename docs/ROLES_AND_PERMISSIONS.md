# Roles and permissions

Phase 2 implements RBAC with seeded roles/permissions.

## Roles

| Role | Intent |
| --- | --- |
| `buyer` | Default attendee / ticket buyer (assigned on register) |
| `host` | Event host / creator |
| `host_staff` | Host team member / event desk staff with limited tools (granted on host-team accept or event staff assign) |
| `support_agent` | Customer support (no finance mutations) |
| `finance_admin` | Finance and payouts oversight |
| `super_admin` | Platform super administrator (`admin.full_access`) |

## Permissions

| Code |
| --- |
| `users.read` |
| `users.manage` |
| `hosts.create` |
| `hosts.manage_own` |
| `hosts.verify` |
| `events.create` |
| `events.manage_own` |
| `events.review` |
| `events.approve` |
| `tickets.scan` |
| `tickets.manage` |
| `payments.view` |
| `refunds.review` |
| `refunds.approve` |
| `payouts.request` |
| `payouts.review` |
| `payouts.mark_paid` |
| `reviews.reply` |
| `reviews.moderate` |
| `vault.create` |
| `vault.moderate` |
| `support.reply` |
| `admin.full_access` |
| `admin.users.view` |
| `admin.users.view_private_contact` |
| `admin.users.view_activity` |
| `admin.users.view_security` |
| `admin.users.add_note` |
| `admin.users.flag` |
| `admin.users.restrict` |
| `admin.users.view_restrictions` |
| `admin.users.add_restriction` |
| `admin.users.revoke_restriction` |
| `admin.users.suspend` |
| `admin.appeals.review` |
| `admin.users.ban` |
| `admin.users.force_logout` |
| `admin.users.force_password_reset` |
| `admin.users.view_audit` |
| `admin.users.impersonate` |
| `admin.events.view` |
| `admin.events.export_buyers` |
| `admin.events.export_private_contact` |
| `admin.finance.export_event_sales` |
| `admin.settings.view` |
| `admin.settings.edit_runtime` |
| `admin.settings.edit_secrets` |
| `admin.settings.test_integrations` |
| `admin.settings.view_system_status` |
| `admin.settings.clear_overrides` |
| `admin.settings.view_audit` |

## Default role → permission map

| Role | Permissions |
| --- | --- |
| `buyer` | _(none yet — public + own account flows)_ |
| `host` | `hosts.create`, `hosts.manage_own`, `events.create`, `events.manage_own`, `tickets.scan`, `tickets.manage`, `payments.view`, `payouts.request`, `reviews.reply`, `vault.create` |
| `host_staff` | `events.manage_own`, `events.read_own`, `events.update_own`, `tickets.scan`, `tickets.manage`, `ticket_types.update`, `ticket_types.deactivate`, `reviews.reply`, `merch.view_fulfillment`, `merch.fulfill` |
| `finance_admin` | `payments.view`, `refunds.review`, `refunds.approve`, `payouts.review`, `legacy.manage`, `vault.moderate`, `admin.events.view`, `admin.events.export_buyers`, `admin.finance.export_event_sales`, `admin.settings.view`, `admin.settings.view_system_status`, `admin.settings.edit_runtime` (no secrets). **No `admin.users.*` by default.** |
| `support_agent` | `admin.users.view`, `admin.users.add_note`, `admin.appeals.review`, `support.reply`, `reviews.moderate`, `events.review`, `refunds.review`, `admin.events.view`, `admin.events.export_buyers`, `admin.events.export_private_contact`, `admin.settings.view`, `admin.settings.view_system_status` (no flag/suspend/ban/add_restriction / force_* / vault.moderate / settings edit by default) |
| `super_admin` | `admin.full_access` (treated as all permissions, including all `admin.users.*`); **only role that marks payouts paid** |
| `support_agent` / `finance_admin` | **No** impersonation by default — requires explicit `admin.users.impersonate` grant |
| `buyer` / `host` / `host_staff` | **Cannot** impersonate (not seeded; hard-blocked even if the permission is mistakenly granted) |

Source of truth for the full map: `backend/app/users/constants.py` (`ROLE_PERMISSIONS`).

## Host team (org) vs event staff

Canonical docs: [TEAMS.md](./TEAMS.md) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) · [HOST_TEAM.md](./HOST_TEAM.md).

| Layer | Behavior |
|---|---|
| Host owner | Full access; cannot be team-removed; only grantor of finance/team-sensitive flags |
| Role presets | Admin · Event Manager · Scanner · Merch · Support · Sponsor Manager · Viewer — all editable after invite |
| Permission toggles | Grouped: events · tickets · merch · messages · sponsors · analytics · team · finance |
| Host team (`host_team_invites` → `host_team_members`) | True pending email invite → accept; host-scoped toggles. Desk scan defaults **off** (prefer per-event). Enforced by `app/teams/permissions.py` |
| Sensitive | `finance.manage_payout_settings` owner-only unless explicitly granted |
| Event staff (`event_staff_assignments`) | Per-event door/merch desk; synced from team scope for desk roles |
| Hybrid scan | Owner **or** active team perm **or** event assignment |
| Workspaces | `/workspaces` + switcher; persist `POST /me/active-workspace` |

Owner or members with `team.invite` / `team.edit_permissions` / `team.remove_members` manage the roster (`/host/team`). Payouts/bank stay owner-only in v1.

Seed via app lifespan (non-test) or:

```bash
cd backend && PYTHONPATH=. python scripts/seed_rbac.py
```

## Frontend shells

| Route | Allowed roles |
| --- | --- |
| `/dashboard` | any authenticated user |
| `/host` | `host`, `host_staff`, `super_admin` |
| `/admin` | `super_admin`, `finance_admin` |
| `/support` | `support_agent`, `super_admin` |

## Hard product rules

1. **Hosts cannot delete reviews.**
2. **Support cannot modify financial records.**
3. **Manual payouts require immutable evidence.**
4. **Only super admin can mark payouts as paid.**
5. Admin and finance sensitive actions must write **audit logs**.
6. Ticket issuance follows **verified payment webhooks**, not frontend success callbacks.
7. Check-in uses **signed QR payloads**.
8. Ledger entries are **append-only**.

## Enforcement

- Backend: `get_current_user`, `require_role`, `require_permission`
- Frontend: route guards hide/deny UI only — API remains authoritative
