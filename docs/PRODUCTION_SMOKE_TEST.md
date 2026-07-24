# Pàdéyá production smoke test

Run after deploy (staging or production). Do **not** seed demo data on production. Do **not** run live Paystack charges unless intentionally testing with a small known amount / Paystack test mode on staging.

Brand check: UI copy should say **Pàdéyá**.

## Preflight

- [ ] Run `./scripts/prod_preflight.py` (or `backend/scripts/prod_preflight.py`) → **`READY_FOR_PRODUCTION`** and review **`AI_READY`** (PASS preferred; WARN acceptable if AI is off or template-only)
- [ ] Or review **`/admin/platform/go-live`** as super admin (includes **AI readiness** card)
- [ ] `https://api.<domain>/health` returns `"status":"ok"`
- [ ] `https://<domain>/` loads over HTTPS
- [ ] `APP_ENV=production` (or staging for pre-prod)
- [ ] `DEMO_MODE=false` and `NEXT_PUBLIC_DEMO_MODE=false`
- [ ] `/demo` returns 404 in production builds

### If preflight is BLOCKED

| Failure | Meaning |
|--------|---------|
| Demo users / events / hosts / markers | Production DB still contains local demo seed — use a **fresh** Postgres or clean staging clone (never `reset_demo_data` in production) |
| Paystack live | Mode or live keys/webhook not set in Admin → Payment integration |
| Email SMTP / log mode | Still on log/dev provider — configure SMTP in Admin → Email settings |
| Migrations | Run `alembic upgrade head` / `./scripts/prod-migrate.sh` (need ≥ `20260722_0128` for AI Control Center) |
| AI_READY FAIL | Missing canonical templates/routes, or blocked future keys misconfigured — see **AI** section on go-live page |
| AI_READY WARN | `AI_KILL_SWITCH` on, template-only providers, missing spend cap while AI enabled — fix before relying on AI in prod |
| APP_ENV / DEMO_MODE / CORS / FRONTEND_URL | Fix `backend/.env.production` and rebuild frontend if needed |

Details and fix text: re-run preflight or open `/admin/platform/go-live`.

## AI (Pàdéyá Copilot — canonical 24 features)

After preflight **AI_READY: PASS** (or WARN if AI intentionally off):

- [ ] Global AI enabled in Admin → AI → Settings (if product should use network providers)
- [ ] `AI_KILL_SWITCH` unset in production env
- [ ] Provider profile configured (or accept template-only drafts)
- [ ] Per-feature routes assigned in `/admin/ai/features` (including **Active Fan** → `fan.passport.bio`)
- [ ] Do **not** enable legacy host keys or `recommend_featured_events`
- [ ] `fan.connect.explanation` / `discovery.why_recommended` remain **Blocked by safety**

See [AI_PREDEPLOY_HARDENING_AUDIT.md](./AI_PREDEPLOY_HARDENING_AUDIT.md).

## Public

- [ ] Home loads (hero, featured/events sections)
- [ ] `/events` lists published events
- [ ] Event detail loads banner, tickets, sticky CTA
- [ ] Legacy Page `/@username` (or `/u/username`) loads
- [ ] Vault page loads; locked content remains locked / preview-only
- [ ] Memory page loads when published

## Auth

- [ ] Register creates buyer account
- [ ] Login works
- [ ] Logout clears session
- [ ] Protected routes redirect when logged out

## Personal workspace (`/dashboard`)

- [ ] Personal dashboard loads (`/dashboard` — shell title **Personal**)
- [ ] Home shows **Personal Command Center** (eyebrow / framing) — not lifetime metric cards + roles dump
- [ ] Empty / new account: welcome CTAs (Browse events, Set up Passport, Promote) — no wall of zero cards
- [ ] With tickets: Next up shows event + Open QR (modal) — no raw QR token as text
- [ ] With merch ready: pickup reminder appears; optional sections hide when empty
- [ ] With unread messages / Connect pending: community strip shows counts only
- [ ] With ambassador activity: Ambassadors strip shows; hidden when not enrolled
- [ ] No host finance, scanner, desk, team, admin, or support queues on `/dashboard` home
- [ ] `/dashboard/tickets`, `/dashboard/orders`, `/dashboard/merchandise`, `/dashboard/refunds`, `/dashboard/ambassador`, `/dashboard/settings` still load
- [ ] Checkout page loads for a published event
- [ ] Order init works (Paystack redirect or free checkout path)
- [ ] After confirmed payment (webhook), tickets appear in `/dashboard/tickets`
- [ ] Ticket QR page shows large QR + public code (no plain UUID emphasis)
- [ ] Offline/cached ticket note behaves if tested offline
- [ ] Mobile viewport + dark / light mode on Command Center home

## Workspace chrome (Option A + Personal Phase 2)

Site header + in-shell switcher — see [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md) · [BUYER_DASHBOARD_AUDIT.md](./BUYER_DASHBOARD_AUDIT.md).

- [ ] Top nav has **no** private **Host** peer link
- [ ] Public **Hosts** marketplace link still opens `/hosts`
- [ ] **Personal** top-nav entry opens `/dashboard` (not labeled Dashboard; not `/host`)
- [ ] Shell title on `/dashboard` is **Personal**; on `/host` is **Host: {name}**
- [ ] Workspace switcher shows **Personal account**
- [ ] Host users see **Host: {name}** (e.g. Host: DJ Maze) in the switcher
- [ ] Personal-only users see **Personal account** + **Become a host**
- [ ] Switching to Host uses role-aware landing (`hostHomePathForWorkspace` — not hardcoded `/host/events`)
- [ ] Scanner / merch desk staff land on `/host/desk`
- [ ] Personal sidebar shows **Workspaces** (not Team) → `/dashboard/team`
- [ ] Personal sidebar group **Earn** (not Growth) with Ambassadors
- [ ] Sidebar items stack vertically; no horizontal dashboard-wide nav overflow
- [ ] Mobile drawer shows the same grouped nav
- [ ] Dark / light mode works in Personal and Host shells
- [ ] Admin and Support are **not** workspace-switcher options (separate `/admin`, `/support`)
- [ ] `/dashboard/host` is **not** a route (404 / absent)

## Host workspace (`/host`)

- [ ] Host onboarding and `/host` Command Center load for host role (shell title **Host: {name}**)
- [ ] `/host/dashboard` permanently redirects (308) to `/host`
- [ ] `/host/roadmap`, `/host/desk`, `/host/events`, `/host/merchandise`, `/host/ambassadors`, `/host/team` load (when permitted)
- [ ] Create event works
- [ ] Event appears in host events list
- [ ] Host analytics page loads without errors

### Host Command Center polish

See [HOST_COMMAND_CENTER_POLISH.md](./HOST_COMMAND_CENTER_POLISH.md). Routes and permissions unchanged.

- [ ] Owner `/host`: eyebrow **Host Command Center**, H1 **Overview** (not repeated host name)
- [ ] Host admin on `/host` gets member overview — **not** full owner Command Center / finance
- [ ] Scanner / merch staff land on `/host/desk`; viewer stays read-only
- [ ] Sponsor manager lands on `/host/sponsorships` when granted
- [ ] Today’s ops shows Scanner/Pickup only when `canScanTickets` / `canScanMerch` allow
- [ ] Pending tasks eyebrow is **Needs attention** (not Inbox)
- [ ] Switching Host A → Host B refreshes Command Center (no stale metrics)
- [ ] `/host/events` desk staff: assigned events only; Grid coerced to Table; no Edit/Delete/Tickets for scanner/merch-only
- [ ] Event action chips say **Merch Studio** / **Ambassador Campaigns** (URLs unchanged)
- [ ] Sidebar labels match Home / Operate / Grow / Manage IA; public **Hosts** marketplace still `/hosts`

## Admin / support (separate shells)

- [ ] Admin dashboard loads for admin roles (`/admin` — not via workspace switcher)
- [ ] Approve pending event (review queue)
- [ ] Admin analytics loads
- [ ] Support inbox / refund queue loads (`/support` — not via workspace switcher)
- [ ] Support cannot mark payouts paid
- [ ] Finance/super-admin refund approve path respects permissions
- [ ] Payout “mark paid” requires evidence (super admin)

## Check-in

- [ ] Host or staff check-in page loads
- [ ] Manual public-code check-in validates
- [ ] Duplicate scan shows warning state
- [ ] Invalid ticket shows invalid state
- [ ] Door stats page updates

## Payments webhook

- [ ] Paystack webhook URL configured to API HTTPS endpoint
- [ ] Webhook signature verification rejects bad signatures
- [ ] Confirmed payment issues tickets (no frontend-only “success” inventing tickets)

## PWA

- [ ] `/manifest.webmanifest` loads over HTTPS
- [ ] Icons 192/512 present
- [ ] Install prompt / standalone smoke on mobile if desired
- [ ] Service worker / offline ticket behavior does not break online checkout

## Security spot checks

- [ ] API docs (`/docs`) restricted or acceptable for your threat model
- [ ] No secrets in browser Network tab response bodies
- [ ] CORS rejects unknown origins
- [ ] Vault locked media not downloadable without access

## Sign-off

| Env | Date | Tester | Pass/Fail | Notes |
|-----|------|--------|-----------|-------|
|     |      |        |           |       |
