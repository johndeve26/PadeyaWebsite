# Pàdéyá host team management

Brand: **Pàdéyá**. Hosts invite collaborators by **email or Pàdéyá username** (with or without `@`) to help manage a host workspace without sharing the owner account.

**Start here:** [TEAMS.md](./TEAMS.md) (product overview) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) (catalog + enforcement).

Related: [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md) · [CRUD_MATRIX.md](./CRUD_MATRIX.md) · [EMAILS.md](./EMAILS.md) · [SECURITY.md](./SECURITY.md) · [TICKETS.md](./TICKETS.md) · [MERCH.md](./MERCH.md).

## Product model

### Host owner

- Owns the host profile and always has full access.
- Not a team membership role — cannot be invited, suspended, or archived as a teammate.
- Payout / bank settings remain **owner-only** in v1 (finance/bank APIs use owner gate; stored `finance.*` flags are opt-in for a future grant path).
- Only the owner can grant `finance.manage_payout_settings` on a membership.

## Security & privacy

| Rule | Enforcement |
|---|---|
| Owner cannot be removed by non-owner | Suspend/remove/PATCH suspend reject `user_id == host.user_id` |
| Removed/suspended lose access immediately | Inactive membership blocks desk even with leftover staff; staff rows deactivated on suspend/remove |
| Invite tokens hashed | SHA-256 in `host_team_invites.token_hash`; raw token never in APIs |
| Accept requires matching email | Invitee email must match invite |
| Permissions server-side | `app.teams.permissions` + route gates (not FE-only) |
| Sensitive actions audited | Team + desk audit; denial audits for sensitive perms |
| Scanner minimal ticket data | Desk scan/search: name, code, type, status — **no** holder email/phone |
| Merch staff minimal pickup data | Desk scan nulls contact + shipping address |
| No payout/bank unless allowed | Owner-only APIs; member nav/FE routes blocked |
| No full payment refs | Audit + desk metadata sanitizer |
| No private CRM notes / Fan Connect graph | CRM + Fan Connect not exposed on host-team APIs |
| Shipping address | Decrypted only for owner / `merch.manage_shipping` |
| Hidden venue details | Desk list: public `location_label` only; secret `venue_name` withheld from non-owners |

### Team member

- Invited user who helps manage a host workspace.
- Can belong to multiple host teams and switch workspace (`GET /hosts/workspaces`).
- Role presets seed permissions; **every permission stays editable**.
- Actions are limited by permissions and hybrid scope (host-wide vs per-event).

### Scope model

| Scope | Meaning |
|---|---|
| **Host-wide** (`host_wide`) | Granted permissions apply across the full host workspace |
| **Selected events** (`selected_events`) | Event-bound permissions apply only to `scoped_event_ids` **and/or** `event_staff_assignments` |

Recommended defaults:

| Role | Default scope |
|---|---|
| Admin | Host-wide |
| Event Manager | Host-wide (can narrow to selected events) |
| Ambassador Manager | Host-wide |
| Finance Manager | Host-wide |
| Scanner Staff | Selected events only |
| Merch Staff | Selected events only |
| Support Staff | Host-wide (can narrow) |
| Sponsor Manager | Host-wide |
| Viewer | Selected events |

Selecting events on a membership syncs `event_staff_assignments` for desk roles when the invite is accepted / permissions saved. Scanner/merch can still be assigned only via Attendees without team-scoped IDs.

## Role presets

| Role | Intent | Notable defaults |
|---|---|---|
| **Owner** | Full access (not a team role) | Everything |
| **Admin** | Near-full host ops | Ambassadors approve/reject/reverse on; **not** desk scan, payout/bank, mark-paid, export |
| **Event Manager** | Run events | Events, tickets (desk off), event analytics, Ambassadors view + conversions |
| **Ambassador Manager** | Run Ambassadors | Campaigns, participants, conversions, approve/reject/reverse; mark-paid off |
| **Finance Manager** | Sales & payouts | Finance summary/payouts/manage + Ambassadors mark paid |
| **Scanner Staff** | Ticket QR / check-in | Host-wide scan **off**; assign per event |
| **Merch Staff** | Pickup QR / queue | Host-wide merch scan **off**; assign per event |
| **Support Staff** | Buyer/attendee messages | Messages + order/ticket context |
| **Sponsor Manager** | Sponsor inquiries/slots | Sponsors; no private buyer data beyond needed context |
| **Viewer** | Read-only | Assigned views; Ambassadors view only if granted |

Legacy aliases: `manager`/`co_host` → `admin`; `ops` → `event_manager`; `ambassador` → `ambassador_manager`; `finance` → `finance_manager`.

## Permission catalog (grouped toggles)

Editable toggles on each membership (`permissions_json`). Role presets seed defaults; every key stays editable.

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
| Ambassadors | `view` · `create_campaigns` · `edit_campaigns` · `pause_campaigns` · `remove_participants` · `view_conversions` · `view_payouts` · `approve_rewards` · `reject_rewards` · `mark_rewards_paid` · `reverse_rewards` · `export` |

**Sensitive rule:** `finance.manage_payout_settings` is owner-only unless the owner explicitly grants it (non-owners cannot turn it on).

**Enforced today:** hybrid desk (`tickets.scan_qr` / `tickets.check_in`, `merch.scan_pickup_qr` / `merch.mark_picked_up` + event staff), team routes (`team.view` / `invite` / `edit_permissions` / `remove_members`), owner invariants. Other keys are stored and UI-gated; domain enforcement lands with each module. Legacy flat keys still expand when reading old rows.

## Concepts

| Concept | Table / path | Purpose |
|---|---|---|
| Host team members | `host_team_members` | Accepted memberships (`host_id` = host workspace / profile id) |
| Host team invites | `host_team_invites` | Pending email invites (token hash, expiry, scope/permissions) |
| Host team audit | `host_team_audit_logs` | Immutable team actions (also mirrored to global `audit_logs`) |
| Desk scan audit | `desk_scan_audit_logs` | Ticket / merch scan attempts (merged into host audit feed) |
| Event staff | `event_staff_assignments` | Per-event desk; optional `team_member_id`, `assignment_type`, `status`, `expires_at` |
| Global role | `host_staff` | Granted on accept; removed on suspend/archive when no other team/event ties remain |
| Workspaces | `GET /hosts/workspaces` | Owned host + active team + event-staff hosts for switcher |

### Audit log

`GET /host/team/audit-log` returns a unified feed (team lifecycle + desk scans) with **actor**, **action**, **target**, **entity**, **timestamp**, and **safe metadata** only.

Audited actions include: invite sent / accepted / revoked · member added / suspended / removed · permissions changed · scope changed · ticket scanned · merch pickup scanned · denied sensitive permission attempts · payout/finance permission grant.

Metadata is sanitized on write and read (`app.teams.team_audit.sanitize_audit_metadata`). Secrets, invite tokens, and private payment references are never exposed.

**Hybrid authorization** — enforced centrally in `backend/app/teams/permissions.py` (not FE-only). Allow when any of:

1. User is the host owner (`hosts.user_id`), or
2. Active `host_team_members` with the required permission and **host-wide** scope, or
3. Valid `event_staff_assignments` for that event/action (`assignment_type` + optional `permissions_json`), or
4. Active team member with the required permission **scoped** to that event

Key helpers: `has_host_permission`, `has_event_permission`, `can_scan_ticket`, `can_scan_merch_pickup`, `require_host_permission`, `require_event_permission`. Call sites (`checkins`, merch desk, host team routes) must use these — do not rely on hiding buttons in the UI.

### Scanner rules

**Ticket scan** allow: owner · team `tickets.scan_qr` / `tickets.check_in` (host-wide or scoped) · active non-expired `event_staff_assignments` for that event.  
Deny: suspended/removed · missing scan permission · scoped to another event · other host team · inactive/expired staff.

**Merch pickup scan** allow: owner · team `merch.scan_pickup_qr` / `merch.mark_picked_up` (host-wide or scoped) · staff `assignment_type` merch_pickup/event_ops.  

Every attempt writes `desk_scan_audit_logs` (`actor_user_id`, `host_id`, `event_id`, `ticket_id` / `merch_order_item_id`, `action`, `result`, `denial_reason`, `created_at`).

## Invite flow

1. Host opens `/host/team` → **Invite team member**.
2. Host enters **email or Pàdéyá username** (`staff@…`, `@gatekeeper`, or `gatekeeper`), role preset, permission toggles, and scope (all host events or selected events).
3. Backend resolves username → existing user + account email (required); creates `host_team_invites` (`status=pending`, `invited_user_id` set), stores **hashed token only**, enqueues `team_invite` + in-app/push for known users (7-day expiry). Unknown username → `404` “No Pàdéyá user found with that username.” (no pending row). Username accept requires `user_id == invited_user_id`.
4. Invitee opens `/team/invite/[token]` → login/register if needed → email must match invite.
5. Accept creates `host_team_members` (`active`), marks invite `accepted`, notifies host (`team_invite_accepted` + in-app/push), audits the action.
6. Host may **revoke** a pending invite (`team_invite_revoked`); revoked/expired invites cannot be accepted. Re-inviting the same email replaces the open pending row.
7. Permission changes → `team_permission_updated`; suspend → `team_security_alert`; remove → `team_member_removed` (email + in-app/push when supported).

## API (prefix `/api/v1`)

Canonical surface (preferred):

| Method | Path | Who |
|---|---|---|
| GET | `/host/team` | Owner / `team.view` — members only |
| POST | `/host/team/invites` | Owner / `team.invite` |
| GET | `/host/team/invites` | Owner / `team.view` — pending invites |
| POST | `/host/team/invites/{invite_id}/revoke` | Owner / `team.remove_members` |
| PATCH | `/host/team/members/{member_id}` | Owner / `team.edit_permissions` |
| POST | `/host/team/members/{member_id}/suspend` · `/remove` | Owner / `team.remove_members` |
| GET | `/host/team/audit-log` | Owner / `team.view` |
| GET | `/host/team/permissions` · `/roles` | Authenticated (catalog) |
| GET/POST | `/team/invites/{token}` · `/accept` | Invitee (preview public) |
| GET | `/me/team-workspaces` | Authenticated user |
| POST | `/me/active-workspace` | Authenticated user (persist selection) |
| GET | `/admin/teams` · `/admin/teams/audit` | `admin.full_access` |

Workspace context: query `host_id` or header `X-Padeya-Host-Id`, else persisted active workspace, else owned host.

Legacy (kept for compatibility):

| Method | Path | Who |
|---|---|---|
| GET | `/hosts/workspaces` | Authenticated user |
| GET | `/hosts/workspaces/{host_id}/desk-events` | Workspace member |
| GET/POST… | `/hosts/me/team*` · `/hosts/{host_id}/team*` | Owner / team admin |
| GET/POST | `/hosts/team-invites/{token}`… | Invitee |

## Frontend

- `/host/team` — overview sections (members, invites, roles, event assignments, audit)
- `/host/team/members` · `/host/team/invites` · `/host/team/audit-log`
- `/host/team/[id]` — member edit (role, status, permissions, scope, suspend/remove)
- Invite modal — email or Pàdéyá username, role preset, permission toggles, scope, event picker; scanner/merch quick desk setup
- `/team/invite/[token]` — accept/decline
- `/dashboard/team` · `/dashboard/team/workspaces` — joined/owned workspaces + active selection
- `/workspaces` — after login: Personal account + Host workspace: [Name]
- Workspace switcher (host + buyer shells) — same options; nav/actions filtered by permissions
- `/host/desk` — scanner / merch pickup for assigned events
- `/host/access-denied` — “You do not have access to this area.”

## Demo data

DJ Maze team seed (`app/demo/team_seed.py`): Event Ops Manager, Gate Scanner + Pickup Staff (Afrobeats Night Live), Sponsor Observer, pending invite token `demo-padeya-team-invite-afrobeats`. Shortcuts on `/demo`. See [DEMO_DATA.md](./DEMO_DATA.md).

## Tests

### Backend

| Area | Files |
|---|---|
| Invites / accept / revoke / duplicate | `test_host_team.py`, `test_host_team_apis.py` |
| Permissions / hybrid scan / staff | `test_teams_permissions.py`, `test_scanner_integration.py` |
| Audit + privacy | `test_team_audit.py`, `test_team_security_privacy.py` |
| Notifications | `test_team_notifications.py` |
| Demo seed | `test_demo_team_seed.py` |

Coverage includes: pending invite + email outbox, hashed tokens, accept (existing/new user), email match, expired/revoked, active member creation, duplicate invite replace, owner protect, suspend/remove + immediate access loss, role presets, permission toggles, host-wide / per-event scan allow-deny, merch pickup + cross-host deny, finance defaults, permission/scan/denied audits, `event_staff_assignments`.

### Frontend smoke

`npm run test:host-team` → `frontend/scripts/host-team-smoke.mjs`  
Checks: `/host/team` + invite modal (presets/toggles/scope), pending invites/revoke, accept page, member edit/suspend/remove, audit log columns, workspace switcher, scanner/merch nav gating, access-denied, responsive + theme tokens.

### Suggested local run

```bash
cd backend && alembic upgrade head
cd backend && pytest tests/test_host_team.py tests/test_host_team_apis.py \
  tests/test_teams_permissions.py tests/test_scanner_integration.py \
  tests/test_team_audit.py tests/test_team_security_privacy.py \
  tests/test_team_notifications.py tests/test_demo_team_seed.py -q
cd frontend && npm run lint && npm run build
cd frontend && npm run test:pwa && npm run test:theme && npm run test:host-team
```

## Out of scope (v1)

Full Event Studio co-ownership for every permission key, host-scoped finance APIs for `manage_payouts`, replacing `event_staff_assignments`.
