# Sponsorships and sponsor profiles

Pàdéyá separates **sponsor identity** (brand workspace) from **host sponsorship marketplace** (slots and inquiries).

## Sponsor profile (workspace type)

- Users keep their **Fan passport** and may also own **Host** and **Sponsor** profiles.
- Sponsor is **not** merged with Host; hosts manage inbound inquiries; sponsors manage outbound inquiries.
- **No auto-approval** of sponsor accounts; **no direct fan messaging**; **no AI auto-matching** with hosts.

### Data

- Table: `sponsors` (extended profile fields + legacy marketplace contact fields)
- Team: `sponsor_team_members` (owner, admin, campaign_manager, viewer)
- API prefix: `/api/v1/sponsors` (profiles) vs `/api/v1/sponsorships` (marketplace)

### Lifecycle

| Stage | onboarding_status | verification_status | visibility |
| --- | --- | --- | --- |
| Draft | draft | unverified | private |
| Submitted | pending | pending | private |
| Live public | active | verified | public |

Archive/restrict via `status` (soft); prefer restrict/suspend over hard delete.

### Marketplace link

- Logged-in sponsors submitting slot inquiries attach to their **owned sponsor profile** when one exists.
- Hosts see sponsor identity on inquiries via existing sponsorship inquiry payloads + sponsor FK.

## Host marketplace (unchanged scope)

- Slots, inquiries, placements, analytics: see `docs/DATABASE.md` and `/api/v1/sponsorships/*`.
- Host team permissions `sponsors.*` remain **host-scoped** slot/inquiry tools — not sponsor workspace RBAC.

## Permissions

Platform RBAC:

- `sponsors.create`, `sponsors.view_own`, `sponsors.edit_own`, `sponsors.manage_team`, `sponsors.manage_campaigns`, `sponsors.view_inquiries`
- `admin.sponsors.view`, `admin.sponsors.moderate`, `admin.sponsors.verify`, `admin.sponsors.restrict`

Role `sponsor` is assigned on first sponsor profile creation.

## Sponsor team

- Tables: `sponsor_team_members`, `sponsor_team_invites`, `sponsor_team_audit_logs`
- Owner (account `owner_user_id`) + invited roles: admin, campaign_manager, viewer
- Only **owner** or **admin** with `sponsors.manage_team` may invite, resend, cancel, change roles, or remove members
- Accept path: `/sponsor/team/invite/{token}` → `POST /api/v1/sponsors/team/invites/{token}/accept`
- Audit actions: `sponsors.team_invite`, `sponsors.team_resend`, `sponsors.team_invite_cancel`, `sponsors.team_role_change`, `sponsors.team_remove`, `sponsors.team_accept`

## Saved hosts, events, and opportunities

- Table: `sponsor_saved_items` (unique per sponsor + type + id)
- Private notes for sponsor team; never on public sponsor profiles
- Targets must be public (verified host, published event, published sponsorship slot)
- `sponsors.save_items`: owner, admin, campaign_manager; viewers read-only

## Sponsor campaigns

- Tables: `sponsor_campaigns`, `campaign_saved_items`; `sponsorship_inquiries.campaign_id` (optional FK)
- Workspace-only by default (`visibility=private`); **public case study** requires admin moderation (`moderation_status=pending` → approve/reject)
- Lifecycle: draft → activate (or under_review if moderated) → pause / complete / archive
- RBAC: `sponsors.manage_campaigns` for create/edit/lifecycle/saved links; viewers read-only
- No AI host matching; no auto-contact; budget/goals never on public sponsor profile JSON

### APIs

- Workspace: `/api/v1/sponsors/workspaces/{sponsor_id}/campaigns/*`
- Admin: `/api/v1/admin/sponsor-campaigns/*` (`admin.sponsor_campaigns.view`, `admin.sponsor_campaigns.moderate`)
- Campaign recommendations: rules-only scoring + dismiss feedback (no AI auto-match)
- Workspace reports: aggregate inquiries, campaigns, saved items, placements (`/reports/overview`, per-campaign `/reports`)

## Frontend routes

| Route | Purpose |
| --- | --- |
| `/sponsorships` | Marketplace + verified sponsor directory |
| `/sponsorships/hosts` | Host directory for brands |
| `/sponsors/[slug]` | Public sponsor partnership profile (hero, summary cards, about, public campaigns, sponsored events, partnered hosts, location chips, host inquiry CTAs) |
| `/sponsors`, `/sponsors/hosts` | Permanent redirects to `/sponsorships*` |
| `/sponsor/*` | Private sponsor workspace |
| `/sponsor/campaigns` | Campaign list |
| `/sponsor/campaigns/new` | Create campaign |
| `/sponsor/campaigns/[id]` | Campaign detail |
| `/sponsor/campaigns/[id]/edit` | Edit campaign |
| `/admin/sponsors` | Admin moderation |
| `/admin/sponsor-campaigns` | Campaign moderation |

## Sponsorship deals, invoices, and payment

Inquiry → host **proposal** → sponsor **accept** → **invoice** → Paystack → **verified webhook** → placement **active**. No auto-approval; no activation before verified payment when payment is required.

### Tables (migration `20260723_0138`)

- `sponsorship_deals` — lifecycle statuses: draft → proposed → accepted → invoice_pending → payment_pending → paid/active → completed (or cancelled/rejected/expired)
- `sponsorship_invoices` — issued/payment_pending/paid/void; Paystack reference prefix `PDY-SPN-`
- `sponsorship_payment_events` — idempotent provider events; **redacted** payload only (never full card/secrets)

### Payment rule

Only `POST /api/v1/payments/webhooks/paystack` (verified signature) marks invoice paid and deal active. Sponsor return URL (`?payment=return`) is informational only.

### APIs

- Host: `/api/v1/host/sponsorship-deals/*` (+ `/reports/summary` revenue pending/paid)
- Sponsor: `/api/v1/sponsors/workspaces/{sponsor_id}/deals/*` (accept/reject/pay)
- Admin: `/api/v1/admin/sponsorship-deals/*`, `POST /api/v1/admin/sponsorship-invoices/{invoice_id}/void`

### Frontend

| Route | Purpose |
| --- | --- |
| `/host/sponsorships/deals` | Host deal list + revenue summary |
| `/host/sponsorships/deals/[id]` | Host deal detail |
| `/sponsor/deals` | Sponsor proposals and invoices |
| `/sponsor/deals/[id]` | Accept/reject/pay |
| `/admin/sponsorship-deals` | Admin deal list |
| `/admin/sponsorship-deals/[id]` | Invoice status, cancel/void (no raw Paystack JSON) |

Reports: sponsor overview/campaign reports include `deals` (committed/paid spend, pending invoices, active/completed counts).

See also: [SPONSORSHIP_PRODUCTION_SMOKE.md](./SPONSORSHIP_PRODUCTION_SMOKE.md) for pre-deploy validation (migrations `20260723_0133`–`0139`, pytest gate, payment test-mode rules).

## Local rich demo seed (non-production)

Six fictional sponsor workspaces for end-to-end QA: directory, **rich public profiles** (campaign cards with objectives/locations/linked counts, sponsored event cards with deliverable chips, partner host counts, up to 3 related sponsors), team, saved items, campaigns, recommendations, inquiries, deals/invoices, placements, deliverables, and reports.

```bash
python -m scripts.seed_demo_data          # hosts/events/slots first
DEMO_MODE=true python -m scripts.seed_sponsor_demo_data --force
```

Details: [DEMO_DATA.md](./DEMO_DATA.md#rich-sponsor-demo-6-fictional-brands) · `backend/app/demo/sponsor_demo_seed.py` + `sponsor_demo_portfolio.py` · tests `tests/test_sponsor_demo_seed.py`.

## Deliverables & fulfillment (migration `20260723_0139`)

Table `sponsorship_deliverables` tracks checklist items per active deal.

- Created automatically when a deal becomes **active** from `deal.deliverables` JSON (strings or typed objects).
- Host: progress notes, mark in progress, submit proof URL (no auto-complete).
- Sponsor: approve (→ `completed`) or reject with revision reason; viewers read-only.
- Admin: list + status override with audit log.
- When all deliverables are terminal and `ends_at` allows, deal/placement may move to **completed**.

APIs under host/sponsor/admin deal paths (`…/deliverables`). Notifications: submitted, approved, rejected, all complete — safe copy only.
