# Pàdéyá host teams

Brand: **Pàdéyá**. Hosts invite collaborators by email to help run a **host workspace** without sharing the owner login.

Deep reference (API tables, CRUD, tests, demo): [HOST_TEAM.md](./HOST_TEAM.md) · Permissions catalog: [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) · RBAC roles: [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md)

**Not Ambassadors.** Pàdéyá Ambassadors are promoters/referrers only — joining Ambassadors never grants host team, scanner, merch pickup, or staff permissions. Host team members may manage Ambassadors **campaigns/rewards** only when the host grants `ambassadors.*` toggles (see [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) and [AMBASSADORS.md](./AMBASSADORS.md)).

## What a host team is

| Actor | Meaning |
|---|---|
| **Host owner** | Owns `hosts` / profile; full access; **not** a team membership role |
| **Team member** | Accepted `host_team_members` row with role + permission toggles + scope |
| **Pending invite** | `host_team_invites` — true email invite (hashed token, 7-day TTL) |
| **Event staff** | `event_staff_assignments` — per-event desk (ticket / merch / ops); may link to a team member |

Members can belong to multiple host workspaces and switch via the workspace switcher.

## True pending invite (email or username)

Hosts invite from **one field** — email or Pàdéyá username (with or without `@`).

| Input | Behavior |
|---|---|
| `staff@example.com` | Email invite flow (below) — supports people **not yet on Pàdéyá** |
| `@gatekeeper` / `gatekeeper` | Username invite flow (below) — **requires** an existing Pàdéyá user; unknown → error, no pending row |

### Email invite flow

API create: `POST /api/v1/host/team/invites` with `invite_identifier`, optional `permissions_json` / `scope_json` / `selected_event_ids`. Response is method-safe (`invite_id`, `invite_method`, masked email **or** username/display/avatar).

1. Host enters an email address.
2. If that email belongs to an existing user → create pending invite and **tie** `invited_user_id` when possible.
3. If no account exists → still create a **pending** `host_team_invites` row for that email (no member yet).
4. Enqueue `team_invite` through the email outbox (hashed token only; CTA **Accept invite** → `/team/invite/[token]`).
5. Invitee **registers or logs in** (if no account yet), then accepts.
6. Acceptance requires the signed-in email to **match** the invited email (case-insensitive); otherwise `403`.
7. Accept creates active `host_team_members`, marks invite `accepted`, grants `host_staff` when needed, syncs desk staff for scoped events, notifies host (`team_invite_accepted`).

Revoke / expiry / already-accepted block accept. Re-inviting the same email replaces the open pending row. Raw tokens never appear in list/detail APIs; preview returns an email hint only.

### Username invite flow

Requires an **existing** Pàdéyá user. Unknown usernames never create pending invites (only bare emails may).

1. Host enters `@username` or `username`.
2. Backend finds the user (Fan Passport username, then host Legacy slug) — case-insensitive; leading `@` stripped.
3. If found → pending invite with `invited_user_id` set and `email` = that account’s email.
4. Enqueue `team_invite` outbox email to the account email (username lead copy).
5. In-app + push (`team.invite`) when prefs allow.
6. User logs in and accepts.
7. Acceptance requires authenticated `user_id` **==** `invited_user_id`. A different logged-in user gets `403`: **This invite was sent to another Pàdéyá account.**
8. Create active `host_team_members`.
9. Mark invite `accepted`; notify host (`team_invite_accepted` + in-app/push).
10. Audit invite sent (`hosts.team_invite` / resend) and accepted (`hosts.team_accept`).

If username does not exist → `404` with: **No Pàdéyá user found with that username.**

### Invite acceptance rules (both methods)

| Case | Result |
|---|---|
| Username invite, wrong logged-in user | `403` — This invite was sent to another Pàdéyá account. |
| Email invite, email mismatch | `403` — sign in with invited email |
| Email invite, no account yet | Register / login with that email, then accept |
| Expired | Cannot accept |
| Revoked | Cannot accept |
| Already accepted | Cannot reuse (idempotent only if same active member) |

### Privacy — username invites

Host-facing APIs/UI for username invites expose only:

- display name  
- `@username`  
- avatar **if** the Fan Passport is public/unlisted  
- invite / member status  

They must **not** expose: account email, phone, private Passport fields, or other private memberships.  
Invite email is still sent internally using the stored account email (`host_team_invites.email`); that column is omitted from host serializers when `invite_method=username`. Audit metadata for username invites stores `@username`, not the email.

## Team roles (presets)

Presets **seed** `permissions_json`; every toggle stays editable after invite.

| Role | Intent | Default scope |
|---|---|---|
| **Owner** | Not a team role — full access to everything | — |
| Admin | Near-full host ops; Ambassadors approve/reject/reverse on; no desk scan, payout/bank, or mark-paid/export by default | Host-wide |
| Event Manager | `events.*`, ticket ops (desk off), `analytics.view_events`, Ambassadors view + conversions | Host-wide (can narrow) |
| Ambassador Manager | Campaigns, participants, conversions, payouts view, approve/reject/reverse — mark-paid off unless granted | Host-wide |
| Finance Manager | Sales summary, payouts, manage payouts, Ambassadors payout view + mark paid | Host-wide |
| Scanner Staff | Ticket QR / check-in | Selected events |
| Merch Staff | Pickup QR / queue | Selected events |
| Support Staff | Buyer/attendee messages | Host-wide (can narrow) |
| Sponsor Manager | Sponsor inquiries / slots | Host-wide |
| Viewer | Read-only areas; `ambassadors.view` only if granted | Selected events |

Legacy aliases: `manager` / `co_host` → `admin`; `ops` → `event_manager`; `ambassador` → `ambassador_manager`; `finance` → `finance_manager`.

Owner is never invited, suspended, or removed as a teammate.

## Permission toggles

Grouped keys on each membership / invite (events · tickets · merch · messages · sponsors · analytics · team · finance · **ambassadors**). Full catalog and enforcement status: [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md).

**Ambassadors rewards (team):** with `ambassadors.approve_rewards` / `reject_rewards` / `mark_rewards_paid` (or `finance.manage_payouts`) / `reverse_rewards`, an active team member can run the same host-owned reward workflow as the owner on `/host/ambassadors/conversions` — approve, reject, mark paid, reverse. Without the toggle → denied. Does not grant platform admin oversight or access to other hosts’ campaigns. Joining Ambassadors as a promoter never creates a team membership.

**Sensitive:** `finance.manage_payout_settings` is owner-only unless the owner explicitly grants it. Platform host-balance payout/bank **APIs remain owner-scoped in v1** (distinct from Ambassadors reward mark-paid).

## Host-wide vs per-event scope

| Scope | Meaning |
|---|---|
| `host_wide` | Granted permissions apply across the host workspace |
| `selected_events` | Event-bound actions apply only to `scoped_event_ids` and/or linked staff rows |

Scanner / merch presets default to **selected events** with host-wide desk scan **off**. Saving scope for desk roles upserts `event_staff_assignments`.

## Hybrid scan authorization

Central checker: `backend/app/teams/permissions.py`.

Allow a ticket or merch desk action when **any** of:

1. User is the **host owner**, or
2. **Active** team member with the required permission and **host-wide** scope, or
3. Valid **`event_staff_assignments`** for that event/action (`assignment_type` + optional JSON), or
4. Active team member with the required permission **scoped** to that event

**Hard deny:** suspended / removed membership (even if a leftover staff row exists — suspend/remove deactivate staff). Cross-host teams cannot scan another host’s events.

### Ticket scanner

Required team keys: `tickets.scan_qr` and/or `tickets.check_in`.  
Staff types: `ticket_scanner`, `event_ops`.  
Desk payloads are **minimal** (name, public code, type, status) — no holder email/phone.  
Details: [TICKETS.md](./TICKETS.md#host-team--desk-scan).

### Merch pickup scanner

Required team keys: `merch.scan_pickup_qr` and/or `merch.mark_picked_up`.  
Staff types: `merch_pickup`, `event_ops`.  
Scan response nulls buyer contact + shipping address. Full shipping decrypt requires owner / `merch.manage_shipping`.  
Details: [MERCH.md](./MERCH.md#host-team-desk).

Every attempt writes `desk_scan_audit_logs` (success and denied).

## `event_staff_assignments` integration

| Field | Role |
|---|---|
| `team_member_id` | Optional link back to `host_team_members` |
| `assignment_type` | `ticket_scanner` · `merch_pickup` · `event_ops` |
| `status` / `expires_at` | Inactive or expired → no desk access |
| `permissions_json` | Optional per-assignment overrides |

Team scope sync creates/updates rows for scanner/merch/event_manager/viewer when scope is `selected_events`. Pure Attendees-page staff (no team row) still works.

## Workspace switching

| Surface | Behavior |
|---|---|
| `/workspaces` | After login: Personal account + **Host: [Name]** |
| Switcher | Always on Personal (`/dashboard`, `/connect`) and Host (`/host`) shells — **Personal account** · **Host: {name}**; empty list shows Become a host |
| Persist | Active host: `POST /me/active-workspace` → `user_active_workspaces` + `padeya-active-host-id`. Last mode: `padeya-workspace-mode` (`personal` \| `host`) for top-nav Dashboard entry |
| Resolve | Query `host_id`, header `X-Padeya-Host-Id`, else active workspace, else owned host |
| Nav | `navForWorkspace` — members see only granted tools (desk / team / sponsors / …) |
| Denied | `/host/access-denied` — “You do not have access to this area.” |

APIs: `GET /me/team-workspaces`, legacy `GET /hosts/workspaces`.

## Audit logs

Unified host feed: `GET /host/team/audit-log` (team lifecycle + desk scans).

| UI column | Source |
|---|---|
| Actor | `actor_label` / user |
| Action | `action_label` (invite sent, permissions changed, ticket scanned, …) |
| Target | Member / invitee |
| Entity | `entity_type` · `entity_id` |
| Timestamp | `created_at` |
| Details | **Safe** metadata only |

Audited: invite sent/accepted/revoked · member added/suspended/removed · permissions/scope changed · finance permission grant · ticket/merch scans · denied sensitive permission attempts.

Never in metadata: invite tokens, secrets, account numbers, Paystack/payment refs. Sanitizer: `app.teams.team_audit.sanitize_audit_metadata`.

## Security & privacy (summary)

| Rule | Rule of thumb |
|---|---|
| Owner protect | Non-owners cannot remove/suspend the owner |
| Immediate revoke | Suspend/remove deactivates staff + blocks desk |
| Invite safety | Hashed token · matching email · expiry/revoke enforced |
| Server-side perms | FE gates are secondary |
| Desk PII | Minimal ticket/merch payloads |
| Finance | No bank / host-balance payout UI/API for members in v1 |
| Ambassadors rewards | Team may approve/mark paid only with `ambassadors.*` / finance toggles; conversion DTO strips buyer/order refs |
| Shipping | Decrypt only with `merch.manage_shipping` / owner |
| CRM / Fan Connect | Not exposed on host-team APIs |
| Venues | Desk list uses public `location_label`; secret `venue_name` withheld from non-owners on hidden events |

Full matrix: [HOST_TEAM.md](./HOST_TEAM.md#security--privacy) · [SECURITY.md](./SECURITY.md) · [PRIVACY.md](./PRIVACY.md).

## Frontend routes (quick)

| Path | Purpose |
|---|---|
| **`/host`** | Host Command Center home (canonical — not `/host/dashboard`) |
| `/host/dashboard` | **308** alias → `/host` |
| `/host/roadmap` | Launch checklist (existing hosts; not first-time onboarding) |
| `/host/onboarding` | Become-a-host form only — redirects to `/host/roadmap` when host exists |
| `/host/desk` | Scanner / pickup — default landing for desk-focused scanner / merch staff |
| `/host/team` · `/members` · `/invites` · `/audit-log` | Roster + audit |
| `/host/team/[id]` | Edit member |
| `/team/invite/[token]` | Accept / decline → lands on `hostHomePathForWorkspace()` (usually `/host` or `/host/desk`) |
| `/host/ambassadors/conversions` · `/payouts` | Ambassadors rewards (permission-gated) |
| `/workspaces` · switcher | Workspace choose / switch |

**Sidebar:** grouped **Home / Operate / Grow / Manage** (`navGroupsForWorkspace`) — members see only granted items; desk staff get a minimal Operate subset. Details: [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md#host-command-center) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md#role-aware-command-center-ux).

## Emails & notifications

Template: **`team_invite`** (required; CTA **Accept invite** → `/team/invite/[token]`).

| Invite method | Email lead copy | In-app / push |
|---|---|---|
| Email | “You’ve been invited to join [Host Name]’s Pàdéyá team.” | Yes when invitee already has a Pàdéyá account (`invited_user_id`) |
| Username | “[Host Name] invited your Pàdéyá account @username to join their team.” | Always (known user) — push if prefs allow |

| Event | Email | In-app / push |
|---|---|---|
| Invite / resend | `team_invite` (copy above) | username always; email when account exists |
| Accepted (to host) | `team_invite_accepted` | yes |
| Revoked | `team_invite_revoked` | yes |
| Removed | `team_member_removed` | yes |
| Permissions updated | `team_permission_updated` | yes |
| Suspended | `team_security_alert` | yes |

Username invites still deliver email to the account’s stored address; host APIs never expose that email. [EMAILS.md](./EMAILS.md) · [NOTIFICATIONS.md](./NOTIFICATIONS.md).

## Tests

Backend checklist: `backend/tests/test_team_invite_methods.py` (email + username invite, privacy, accept rules, self/active blocks, outbox, in-app, audit `invite_method`). Related coverage also in `test_host_team.py`, `test_team_notifications.py`, `test_team_invite_lookup.py`.

Frontend checklist: `npm run test:host-team` (`frontend/scripts/host-team-smoke.mjs`) — modal accepts email / `@username` / bare username, preview + unknown-username error, pending list username-safe, mobile + theme tokens.

## Demo

DJ Maze seed: Event Ops Manager, Gate Scanner, Pickup Staff (Afrobeats Night Live), Sponsor Observer, pending invite token. Shortcuts on `/demo`. [DEMO_DATA.md](./DEMO_DATA.md#dj-maze-host-team).
