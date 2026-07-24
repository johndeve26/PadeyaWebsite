# Events — host workspace

Brand: **Pàdéyá**. Public discovery: [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md). Event Studio steps: same doc § Event Studio. Host Command Center: [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) · permissions: [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md).

## Host routes (summary)

| Route | Purpose |
|---|---|
| `/host/events` | Operational event list (tabs, filters, view modes) |
| `/host/events/new` | Create event — Event Studio |
| `/host/events/[id]` | Event detail hub + ops subnav |
| `/host/events/[id]/edit` | Event Studio edit (`?step=` deep links) |
| `/host/events/[id]/preview` | Host preview (no workspace sidebar) |
| `/host/events/[id]/tickets` | Ticket tier builder |
| `/host/events/[id]/check-in` | Door QR scanner |
| `/host/events/[id]/merchandise` | Merch Studio |
| `/host/events/[id]/merch` | **308** alias → `…/merchandise` |

Per-event ops (analytics, ambassadors, memory, bundles, etc.) live under `/host/events/[id]/*` — see [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).

**Note:** `/host/events/[id]/studio` is documented in some places but **has no `page.tsx`**. Use `/host/events/[id]/edit?step=…` instead.

## Host event list (`/host/events`)

**File:** `frontend/src/app/host/events/page.tsx` · helpers: `frontend/src/lib/host-events-list.ts` · views: `components/host/events/HostEventsViews.tsx`.

### Data

- `GET /events/mine` via `fetchMyEvents()`
- Desk-focused staff: list filtered to **assigned events** (`fetchWorkspaceDeskEvents`)
- Ops metrics (sales, revenue, check-ins, merch pickups) loaded per visible row when role allows

### Tabs (`?tab=`)

Default tab when param omitted: **Upcoming**.

| Tab | Rule |
|---|---|
| **Upcoming** | `end_datetime >= now` and status ∈ `published`, `paused`, `draft`, `pending_review` |
| **Drafts** | status ∈ `draft`, `rejected` |
| **Published** | status === `published` |
| **Past** | `end_datetime < now` and status ∈ `published`, `completed`, `paused` |
| **Cancelled** | status === `cancelled` |
| **All** | no tab filter |

Command Center “View all upcoming” → `/host/events?tab=upcoming`.

### Search and filters

| Control | Behavior |
|---|---|
| **Search** | Client-side — title, `venue_name`, `city`, `slug` |
| **Status** | Single status pill (in addition to tab) |
| **City** | From event `city` values in loaded set |
| **Visibility** | `listed` · `unlisted` · `password_protected` · `approval_required` |
| **Date range** | Start date from / to (client filter on `start_datetime`) |

Server-side query params for search/sort: **not implemented** (client-only v1).

### Sort

`start_asc` (default for ops), `start_desc`, `created_desc`, `sales_desc`, `revenue_desc`, `title_asc`. Sales/revenue sorts use loaded analytics metrics.

### View modes

Persisted in `localStorage` (`padeya:host-events:view-mode`).

| Mode | Use |
|---|---|
| **Table** | **Default** — compact ops rows (`HostEventsTable`) |
| **List** | Medium density (`HostEventsListView`) |
| **Grid** | Marketing-style cards (`HostEventListCard`) |

### Row actions (permission-gated)

| Action | Route | Who |
|---|---|---|
| View | Public `/events/[slug]` or host preview | `events.view` |
| Edit | `/host/events/[id]/edit` | `events.edit` / `events.create` |
| Tickets | `/host/events/[id]/tickets` | edit grants |
| Scanner | `/host/events/[id]/check-in` | `tickets.scan_qr` / `check_in` |
| Merch | `/host/events/[id]/merchandise` | `merch.view` or desk merch |
| Ambassadors | `/host/events/[id]/ambassadors` | `ambassadors.view` or `events.edit` |
| Analytics | `/host/events/[id]/analytics` | `analytics.view_*` |

**Scanner-only staff:** View + Scanner on assigned events. **Merch-only:** Merch / pickup tools. **Desk-focused:** assigned events only.

### Empty states

Copy varies by tab (`emptyStateForTab` in `host-events-list.ts`) — e.g. Upcoming → create event CTA when user can edit.

## Command Center integration

Owner home at **`/host`** shows:

- Next best action + top roadmap gaps (links to `/host/roadmap`)
- Upcoming events (top 3) → **View all** to `/host/events?tab=upcoming`
- Today’s operations, sales snapshot, pending messages / ambassador / sponsor tasks when permitted

Team members with desk roles see **`MemberDeskOverview`** on `/host` and land on **`/host/desk`** by default — not the full owner grid.

## Admin buyers / attendees (platform)

Platform ops can list and export buyers for any event at `/admin/events/[id]/buyers` (attendees / exports siblings). Permissions, modes, and redaction rules: [TICKETS.md](./TICKETS.md#admin-event-buyers--attendees--exports) · [ADMIN.md](./ADMIN.md). Host attendee/sales exports stay on host paths and are separate.

## Admin buyers / attendees (platform)

Platform admins manage per-event buyers at `/admin/events/[id]/buyers` (attendees + export history tabs). Export modes, permissions, and privacy rules: [TICKETS.md](./TICKETS.md#admin-event-buyers--attendees--exports) · [ADMIN.md](./ADMIN.md#admin-event-buyer-export). Host desk exports (if any) are separate from these admin routes.

## Related

- Event lifecycle / CRUD: [CRUD_MATRIX.md](./CRUD_MATRIX.md)
- Tickets & check-in: [TICKETS.md](./TICKETS.md)
- Host teams & desk scope: [TEAMS.md](./TEAMS.md)
