# Frontend routes

Host team / workspace overview: [TEAMS.md](./TEAMS.md#frontend-routes-quick). Desk + roster routes require the matching host-team permission (or owner); members land on `/host/access-denied` when blocked. Active host resolves via switcher / `POST /me/active-workspace`.

**Workspace chrome (Option A — shipped; Personal Phase 2 labels + Phase 3 Command Center home):**

| Surface | Route tree | Shell title | Notes |
| --- | --- | --- | --- |
| **Personal** | `/dashboard/*` | Personal | Buyer/fan tools; `buyerNav` / `buyerNavGroups` |
| **Personal home** | `/dashboard` | Personal | **Personal Command Center** (Phase 3) — Next up / activity / messages / identity; routes unchanged |
| **Host** | `/host/*` | Host: {display_name} | Host org tools; `navGroupsForWorkspace` |
| **Shared chrome** | — | — | One `WorkspaceShell`; mode-pure nav configs (not a mega-sidebar) |
| **Site header** | — | — | Public **Hosts** → `/hosts`; single **Personal** entry → `/dashboard`; **no** private peer **Host** link |
| **Switcher** | in-shell | — | **Personal account** · **Host: {name}**; zero hosts → **Become a host**; Host landing via `hostHomePathForWorkspace` |
| **Personal sidebar** | — | — | **Workspaces** → `/dashboard/team` (was Team); group **Earn** (was Growth) → Ambassadors; Connect → `/connect` |
| **Admin** | `/admin/*` | Admin | Separate shell — not a switcher option |
| **Support** | `/support/*` | Support | Separate shell — not a switcher option |

No `/dashboard/host`, `/personal`, or `/workspace/personal` trees. Privacy: Personal shows own-data only ([BUYER_DASHBOARD_AUDIT.md](./BUYER_DASHBOARD_AUDIT.md) §12). Audits: [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md) · [BUYER_DASHBOARD_AUDIT.md](./BUYER_DASHBOARD_AUDIT.md). Smokes: `npm run test:buyer-dashboard-nav` · `test:host-command-center` · `test:workspace-privacy` · `test:personal-command-center` · `test:impersonation`.

| Route | Purpose | Status |
| --- | --- | --- |
| `/about` | About Pàdéyá | Public |
| `/pricing` | Platform pricing overview | Public |
| `/contact` | Contact → Support Center | Public |
| `/faq` | FAQ (CMS + fallbacks) | Public |
| `/terms` | Terms of Service | Public |
| `/privacy` | Privacy Policy | Public |
| `/cookies` | Cookie Policy | Public |
| `/refund-policy` | Refund Policy | Public |
| `/ticket-policy` | Ticket Policy | Public |
| `/community-guidelines` | Community Guidelines | Public |
| `/safety` | Safety Center | Public |
| `/report` | Report abuse → support tickets | Public |
| `/accessibility` | Accessibility statement | Public |
| `/events/today` | Today’s events hub | Public |
| `/events/search` | Event search marketplace | Public |
| `/checkout/success` | Checkout success (noindex) | Public |
| `/checkout/failed` | Checkout failed (noindex) | Public |
| `/unauthorized` | Permission denied (noindex) | Public |
| `/account/appeal` | Suspension appeal (auth, noindex) | Auth |
| `/hosts/[slug]` | Redirect → `/u/[slug]` | Alias |
| `/passport/[username]` | Redirect → `/f/[username]` | Alias |
| `/` | Public home | Foundation UI |
| `/dashboard` | Personal Command Center home (Next up, activity, community, identity, Vault, Ambassadors, quick actions) | **Implemented** (Phase 3) — URL unchanged |
| `/events` | Public discovery hub (location filter + facets + cards) | Implemented |
| `/events/location` | Events by Location index | Implemented |
| `/events/country/[countrySlug]` | Country landing (premium sections) | Implemented |
| `/events/state/[stateSlug]` | State landing (premium sections) | Implemented |
| `/events/state/[stateSlug]/[categorySlug]` | State × category hub | Implemented |
| `/events/c/[categorySlug]` | Category hub | Implemented |
| `/events/city/[citySlug]` | City landing (premium sections) | Implemented |
| `/events/city/[citySlug]/[categorySlug]` | City × category hub | Implemented |
| `/events/area/[areaSlug]` | Area landing (premium sections) | Implemented |
| `/events/this-weekend` | Weekend discovery preset | Implemented |
| `/events/free` | Free events hub | Implemented |
| `/events/vip` | VIP / paid-premium soft hub | Implemented |
| `/blog` | Public blog index (featured + grid + filters) | Implemented |
| `/blog/[slug]` | Blog post detail (TOC, share, comments, related, JSON-LD) | Implemented |
| `/blog/category/[slug]` | Posts by category | Implemented |
| `/blog/tag/[slug]` | Posts by tag | Implemented |
| `/blog/author/[slug]` | Author profile + posts | Implemented |
| `/admin/blog` | Blog CMS list (seed / publish / archive) | Admin (`admin.blog.*`) |
| `/admin/blog/new` | Create draft / publish + AI writing assistant (draft-only) | Admin |
| `/admin/blog/[postId]/edit` | Edit + SEO + schedule + AI writing assistant (never auto-publish) | Admin |
| `/admin/blog/comments` | Moderate / edit blog comments | Admin (`admin.blog.comments.*` / `admin.blog.edit`) |
| `/admin/blog/categories` | Blog categories | Admin |
| `/admin/blog/tags` | Blog tags | Admin |
| `/admin/analytics/blog` | Blog engagement + editorial analytics | Admin (`analytics.view_platform` / `admin.blog.view`) |
| `/admin/cms/blog*` | Legacy redirect → `/admin/blog*` | Implemented |
| `/events/near-me` | Near-me placeholder | Implemented |
| `/admin/featured-placements` | Featured Placement Slots list | Implemented |
| `/admin/featured-placements/new` | Create placement set | Implemented |
| `/admin/featured-placements/[id]/edit` | Edit placement set | Implemented |
| `/admin/events/featured` | Redirect → `/admin/featured-placements` | Implemented |
| `/events/[slug]` | Public event detail (+ sticky Get tickets on mobile) | Implemented |
| `/events/[slug]/checkout` | Checkout → Paystack (+ mobile sticky pay bar) | Implemented |
| `/admin/taxonomy` | Taxonomy overview | Admin |
| `/admin/taxonomy/categories` | Categories admin | Admin |
| `/admin/taxonomy/tags` | Tags admin | Admin |
| `/admin/taxonomy/locations` | Locations tree admin | Admin |
| `/admin/taxonomy/host-types` | Host types admin | Admin |
| `/admin/taxonomy/venue-types` | Venue types admin | Admin |
| `/offline` | Graceful offline fallback shell (theme-aware) | PWA (Phase 18) |
| `/demo` | Local QA control center (+ theme panel + messaging one-click login shortcuts) | Dev / demo (`DEMO_MODE=true`) |
| `/host/promos` | Host ticket promo codes ([PROMO_CODES.md](./PROMO_CODES.md)) | Host workspace |
| `/host/ambassadors` | Curated ambassador partners ([AMBASSADORS.md](./AMBASSADORS.md)) | Host workspace |
| `/host/ambassadors/[id]` | Partner performance | Host workspace |
| `/host/ambassadors/campaigns` | Open Ambassadors campaigns | Host workspace |
| `/host/ambassadors/campaigns/new` | Create campaign | Host / `create_campaigns` |
| `/host/ambassadors/campaigns/[id]` | Campaign detail, leaderboard, remove | Host / Ambassadors view+ |
| `/host/ambassadors/conversions` | Conversion ledger + approve / reject / mark paid / reverse + audit | Host owner or team reward perms |
| `/host/ambassadors/payouts` | Ambassador payout summary (host-owned rewards) | Host / `view_payouts` |
| `/host/events/[id]/ambassadors` | Per-event Ambassadors enable/manage | Host workspace |
| `/admin/ambassadors` | Ambassadors overview + global toggle + block | Admin |
| `/admin/ambassadors/campaigns` | All campaigns + create platform campaign | Admin |
| `/admin/ambassadors/conversions` | Oversight ledger, approve, reverse (not exclusive for host-owned) | Admin |
| `/admin/ambassadors/fraud` | Fraud flags (click spikes + flagged / reversed conversions) | Admin |
| `/admin/ambassadors/payouts` | Oversight reward payable / mark paid | Admin |
| `/admin/ambassadors/reports` | Platform Ambassadors summary + audit links | Admin |
| `/ambassadors` | Public Ambassadors landing (hero, how it works, eligible events, FAQ) | Public |
| `/ambassadors/events` | Browse open Ambassadors events | Public |
| `/ambassadors/how-it-works` | How Ambassadors works | Public |
| `/dashboard/ambassador` | Ambassadors overview | Buyer auth |
| `/dashboard/ambassador/events` | Active campaigns / my promoted events | Buyer auth |
| `/dashboard/ambassador/links` | Referral links, Ambassador codes, QR cards | Buyer auth |
| `/dashboard/ambassador/earnings` | Clicks/sales + estimated/approved earnings | Buyer auth |
| `/dashboard/ambassador/leaderboard` | Personal campaign ranking | Buyer auth |
| `/dashboard/ambassador/payouts` | Payout & reward status | Buyer auth |
| `/host/audience` | Audience dashboard + filters | Host workspace |
| `/host/followers` | Follower list | Host workspace |
| `/host/announcements` | Announcement history + dispatch | Host workspace |
| `/host/announcements/new` | Create announcement draft (+ **Generate with AI**, draft-only) | Host workspace |
| `/dashboard/following` | Followed hosts + marketing opt-in | Attendee dashboard |
| `/dashboard/hosts-for-you` | Personalized host recommendations (rules-based) | Attendee dashboard |
| `/hosts?sort=recommended` | Directory sorted by personalized recommendations (signed-in) | Public `/hosts` |
| `/dashboard/events-for-you` | Personalized event recommendations (rules-based) | Attendee dashboard |
| `/events?sort=recommended` | Event directory sorted by personalized recommendations (signed-in) | Public `/events` |
| `/events/[slug]` | Event detail; signed-in **More events you may like** (`event_detail_recommended`); logged-out related discovery | Public |
| `/admin/discovery/event-recommendations` | Redirect → runtime `event-recommendations` settings | Admin |
| `/dashboard/refunds` | My refund requests | Attendee dashboard |
| `/dashboard/refunds/new` | Request full refund | Attendee dashboard |
| `/host/payouts` | Host balance + payout requests | Host workspace |
| `/host/earnings` | Host gross / net after Pàdéyá fees + CSV | Host workspace |
| `/host/events/[id]/earnings` | Per-event host earnings | Host workspace |
| `/admin/refunds` | Refund review / escalate | Admin / support / finance |
| `/admin/payouts` | Payout review + mark paid | Finance / super admin |
| `/admin/ledger` | Append-only host ledger + settlement | Finance / super admin |
| `/admin/finance` | Finance hub (fees, earnings, platform revenue) | Finance admin |
| `/admin/finance/fees` | Global fee schedules | `admin.finance.view_fees` |
| `/admin/finance/host-overrides` | Per-host fee overrides | `admin.finance.view_fees` |
| `/admin/finance/earnings` | Host earnings overview | Finance admin |
| `/admin/finance/platform-revenue` | Platform ledger + revenue report + CSV | Finance admin |
| `/admin/hosts/[hostId]/fees` | Host fee overrides + preview | Finance admin |
| `/admin/hosts/[hostId]/earnings` | Single-host earnings | Finance admin |
| `/admin/events/[id]/earnings` | Event earnings (admin) | Finance admin |
| `/support/refunds` | Support refund escalate queue | Support |
| `/ambassador` | Redirect → `/dashboard/ambassador` | Legacy |
| `/ambassador/earnings` | Redirect → `/dashboard/ambassador/earnings` | Legacy |
| `/dashboard/tickets` | My tickets — summary + tabs (upcoming / past / cancelled / all), grouped by event (+ offline list cache) | Implemented |
| `/dashboard/tickets/[id]` | Ticket + large QR (+ offline display cache) + Download PDF | Implemented |
| `/dashboard/tickets/[id]/transfer` | Transfer ticket ownership | Implemented |
| `/merch-guide` | Educational merch resource (formats, how it works, fees, policies) — marketplace lives at `/merch` | Implemented |
| `/merch` | Merch marketplace homepage (featured, event merch, host shops, drops, Vault, categories) | Implemented |
| `/merch/[slug]` | Public marketplace product detail (standalone + event-attached) | Implemented |
| `/merch/drops` | Post-event drops browse | Implemented |
| `/merch/vault` | Vault-exclusive teasers (safe locked state) | Implemented |
| `/merch/hosts/[username]` | Host shop via marketplace path | Implemented |
| `/u/[username]/shop` | Redirect → `/merch/hosts/[username]` | Implemented |
| `/dashboard/merchandise` | Buyer event merch pickups (code, status, event, message host) | Implemented — [MERCHANDISE.md](./MERCHANDISE.md) |
| `/dashboard/merchandise/[orderItemId]` | Buyer merch detail (pickup QR `padeya.merch.pickup`, review) | Implemented |
| `/dashboard/cart` | Abandoned / active merch cart (not paid until checkout) | Implemented |
| `/dashboard/merch` | Legacy redirect → `/dashboard/merchandise` | Implemented |
| `/u/[username]/merch` | Host merch storefront (also `/@username/merch` via rewrite) | Implemented |
| `/u/[username]/merch/[productId]` | Storefront product detail (size guide, reviews, exclusives) | Implemented |
| `/dashboard/orders/[id]` | Order receipt (ticket + merch lines; message host on merch) | Implemented |
| `/events/[slug]` | Public event (merch section when catalog non-empty) | Implemented |
| `/events/[slug]/merch` | Public event merch catalog | Implemented |
| `/events/[slug]/merch/[productId]` | Public merch product detail (sticky mobile CTA) | Implemented |
| `/events/[slug]/checkout` | Ticket + merch checkout (same cart) | Implemented |
| `/host/merchandise` | Host merch across all events + standalone shop | Host workspace |
| `/host/merchandise/new` | Create merch (standalone or attach to event) — Basics includes **Generate with AI** for title/description/category/tags (draft apply only) | Host workspace |
| `/host/merchandise/[id]/edit` | Edit merch product — same Merch Studio AI assists | Host workspace |
| `/host/merchandise/orders` | Host-wide orders hub → event queues | Host workspace |
| `/host/merchandise/fulfillment` | Host-wide fulfillment hub → event desks | Host workspace |
| `/host/merchandise/discounts` | Merch discount codes (≠ ticket promos) | Host workspace |
| `/host/merchandise/size-charts` | Size chart library | Host workspace |
| `/host/merchandise/shipping-zones` | Flat shipping zone fees (archive soft) | Host workspace |
| `/host/merchandise/revenue` | Merch revenue splits (no PII) | Host workspace |
| `/host/merchandise/stock-alerts` | Stock alert inbox | Host workspace |
| `/host/merchandise/reviews` | Product review reply inbox (hosts cannot delete) | Host workspace |
| `/host/merchandise/print-on-demand` | POD jobs / integrations (manual; live sync future) | Host workspace |
| `/host/events/[id]/merchandise` | Merch Studio (stats + product table) | Host workspace |
| `/host/events/[id]/merchandise/new` | Merch Studio create (sections + preview; shared `HostMerchProductForm` AI assists) | Host workspace |
| `/host/events/[id]/merchandise/[merchId]/edit` | Merch Studio editor (shared AI assists) | Host workspace |
| `/host/events/[id]/merchandise/orders` | Event merch orders | Host workspace |
| `/host/events/[id]/merchandise/fulfillment` | Fulfillment desk (search/filters/notes/QR scan/message buyer) | Host workspace |
| `/host/events/[id]/merch` | Legacy redirect → `/host/events/[id]/merchandise` (308) | Host workspace |
| `/host/events/[id]/studio` (`?step=merchandise`) | Optional Event Studio merch step (not required to publish) | Host workspace |
| `/host/events/[id]/tables` | Table / seat assignment | Host workspace |
| `/host/events/[id]/offline-check-in` | Offline scan buffer + sync | Host workspace |
| `/admin/tickets` | Admin tickets + transfer audit | Admin / finance |
| `/dashboard/orders` | My orders | Implemented |
| `/dashboard/orders/[id]` | Order receipt | Implemented |
| `/admin/orders` | Admin order lookup | Implemented |
| `/admin/payments` | Admin payment lookup | Implemented |
| `/hosts` | Jump to Legacy Page by username | Implemented |
| `/@{username}` | Public Legacy Page | Implemented (rewrite → `/u/[username]`) |
| `/@{username}/vault` | Public Vault catalog (locked/unlocked cards, filters, featured drop, follow/Legacy CTAs) | Implemented (rewrite → `/u/[username]/vault`) |
| `/@{username}/vault/[itemSlug]` | Vault item detail (locked panel CTAs vs unlocked content) | Implemented |
| `/@{username}/memories/[eventSlug]` | Public Event Memory (+ related Vault teasers) | Implemented (rewrite → `/u/[username]/memories/...`) |
| `/u/[username]` | Legacy Page internal route (Vault Preview teasers only) | Implemented |
| `/u/[username]/vault` | Vault catalog internal | Implemented |
| `/u/[username]/vault/[itemSlug]` | Vault item detail (locked preview / unlocked content + related drops) | Implemented |
| `/u/[username]/memories/[eventSlug]` | Event Memory internal | Implemented |
| `/host/events/[id]/memory` | Host memory overview | Host workspace |
| `/host/events/[id]/memory/edit` | Edit recap + gallery | Host workspace |
| `/admin/memories` | Memory moderation | Admin (`memories.moderate`) |
| `/host/analytics` | Host portfolio analytics | Host (`analytics.view_own`) |
| `/host/events/[id]/analytics` | Per-event funnel, sources, tickets, audience | Host workspace |
| `/admin/analytics` | Platform analytics overview + “Explain this period” AI summary (advisory) | Admin (`analytics.view_platform`) |
| `/admin/analytics/revenue` | Revenue analytics | Admin |
| `/admin/analytics/events` | Event leaderboard / compare / channels | Admin |
| `/admin/analytics/hosts` | Host rankings | Admin |
| `/admin/analytics/blog` | Blog funnel, top posts, publishing cadence, AI Studio usage | Admin (`analytics.view_platform` / `admin.blog.view`) |
| `/admin/analytics/support` | Support proxy + fraud placeholders | Admin |
| `/admin/events/[id]/analytics` | Per-event analytics (any event) | Admin |
| `/admin/events/[id]/buyers` | Event buyers list + audited export modal (modes/filters/reason) | Admin (`admin.events.view` + `admin.events.export_buyers`) |
| `/admin/events/[id]/attendees` | Checked-in attendees list + same export modal | Admin (same perms) |
| `/admin/events/[id]/exports` | Buyer export audit history (start export from Buyers) | Admin (same perms) |
| `/host/ai` | Host AI Copilot | Host (`ai.use_own`) |
| `/host/events/[id]/ai` | Event-scoped AI drafts | Host workspace |
| `/admin/ai` | Pàdéyá AI Control Center overview | Admin (`admin.ai.view`) |
| `/admin/ai/providers` | Provider profiles (multi-vendor) | Admin (`admin.ai.manage_providers`) |
| `/admin/ai/features` | Feature routing matrix | Admin (`admin.ai.manage_features`) |
| `/admin/ai/usage` | Usage dashboard | Admin (`admin.ai.view_usage`) |
| `/admin/ai/logs` | Safe generation logs | Admin (`admin.ai.view_logs`) |
| `/admin/ai/safety` | Safety rules and kill switch | Admin (`admin.ai.manage_safety`) |
| `/admin/ai/settings` | Global switch + spend (+ link to runtime AI) | Admin (`admin.ai.manage_settings`) |
| `/admin/ai/playground` | Operator draft playground | Admin (`ai.use_platform`) |
| `/admin/settings/runtime/ai` | Advanced runtime env overrides (de-emphasized; links to Control Center) | Admin (`admin.settings.view`) |
| `/admin/support/ai-summary` | Legacy support AI summary shortcut (canonical key: `admin.support.queue_summary`) | Admin / support |
| `/sponsorships` | Public sponsorship marketplace + sponsor directory | Public |
| `/sponsors/[slug]` | Public verified sponsor partnership profile (rich sections; privacy-safe API) | Public |
| `/sponsorships/hosts` | Verified hosts open to sponsors | Public |
| `/sponsors` | Redirect → `/sponsorships` | Public |
| `/sponsors/hosts` | Redirect → `/sponsorships/hosts` | Public |
| `/sponsor` | Sponsor workspace overview | Sponsor owner/team |
| `/sponsor/create` | Sponsor onboarding | Authenticated |
| `/sponsor/profile` | Edit sponsor profile | Sponsor workspace |
| `/sponsor/saved` | Saved hosts, events, opportunities | Sponsor workspace |
| `/sponsor/opportunities` | Browse slots with save actions | Sponsor workspace |
| `/sponsor/campaigns` | Sponsor campaigns list | Sponsor workspace |
| `/sponsor/campaigns/new` | Create campaign | `sponsors.manage_campaigns` |
| `/sponsor/campaigns/[id]` | Campaign detail | Sponsor workspace |
| `/sponsor/campaigns/[id]/edit` | Edit campaign | `sponsors.manage_campaigns` |
| `/sponsor/reports` | Sponsor workspace analytics | Sponsor team (`sponsors.view_own`) |
| `/sponsor/campaigns/[id]/reports` | Campaign analytics | Sponsor team |
| `/sponsor/deals` | Sponsorship deals list | Sponsor workspace |
| `/sponsor/deals/[id]` | Proposal accept/reject/pay | `sponsors.manage_campaigns` for actions |
| `/host/sponsorships/deals` | Host deal list | Host sponsorship grants |
| `/host/sponsorships/deals/[id]` | Host deal detail | Host sponsorship grants |
| `/admin/sponsorship-deals` | All deals | `admin.sponsorship_deals.view` |
| `/admin/sponsorship-deals/[id]` | Deal/invoice admin | view/manage/finance |
| `/sponsor/inquiries` | Outbound inquiries inbox | Sponsor workspace |
| `/sponsor/settings` | Verification / visibility status | Sponsor workspace |
| `/sponsor/settings/team` | Sponsor team members & invites | Owner/admin |
| `/sponsor/team/invite/[token]` | Accept sponsor team invite | Authenticated invitee |
| `/admin/sponsors` | Sponsor profile moderation | `admin.sponsors.view` |
| `/admin/sponsor-campaigns` | Sponsor campaign moderation | `admin.sponsor_campaigns.view` |
| `/admin/sponsors/[id]` | Verify / restrict / notes | Admin sponsor perms |
| `/host/sponsorships` | Host slots + inquiries (+ **Generate sponsorship pitch with AI**, draft-only) | Host (`sponsorships.manage_own`) |
| `/host/sponsorships/new` | Create sponsorship slot (+ AI assist on package copy) | Host workspace |
| `/admin/sponsorships` | Sponsorship moderation | Admin (`sponsorships.moderate`) |
| `/host/vault` | Vault Studio dashboard (metrics, filters, drop cards) | Host workspace |
| `/host/vault/new` | Multi-step creator: Content → Media → Access → Related → Preview & Publish | Host workspace |
| `/host/vault/[id]` | Drop detail hub (status, actions) | Host workspace |
| `/host/vault/[id]/edit` | Edit drop + access/media + feature on Legacy | Host workspace |
| `/host/vault/[id]/preview` | Fan locked vs owner preview | Host workspace |
| `/host/vault/preview` | Studio catalog / fan-facing preview | Host workspace |
| `/host/vault/earnings` | Vault unlock earnings (`vault_sale`) | Host workspace |
| `/host/vault/subscriptions` | Subscriber list (does not unlock content yet) | Host workspace |
| `/dashboard/vault` | Fan Vault library (unlocked, followed, ticket, unlockable, activity) | Attendee dashboard |
| `/dashboard/vault/[itemId]` | Unlocked item detail (server re-checks access) | Attendee dashboard |
| `/messages` | Redirect into buyer/host inbox | Auth |
| `/messages/[threadId]` | Redirect into role inbox thread | Auth |
| `/dashboard/messages` | Fan inbox (`?filter=` all/unread/requests/event/**starred**/archived) | Attendee dashboard |
| `/dashboard/messages/[threadId]` | Fan thread detail (`?m=` scroll-to message from starred/pin/search) | Attendee dashboard |
| `/dashboard/messages/settings` | Fan messaging prefs + blocked list | Attendee dashboard |
| `/dashboard/messages/notifications` | Fan message notifications | Attendee dashboard |
| `/dashboard/notifications` | In-app notification center (filters, mark read, open `link_path`) | Attendee dashboard |
| `/host/messages` | Host inbox (same filters, incl. starred) | Host workspace |
| `/host/messages/[threadId]` | Host thread detail (`?m=` scroll-to) | Host workspace |
| `/host/messages/settings` | Host messaging prefs + auto-reply + blocked | Host workspace |
| `/host/messages/notifications` | Host message notifications | Host workspace |
| `/admin/message-reports` | Reported conversations queue + “Summarize reports” AI (advisory only) | Admin |
| `/admin/message-reports/[id]` | Report detail + message/attachment moderation | Admin |
| `/connect` | Fan Connect hub (opt-in peer graph) | Attendee (auth) |
| `/connect/suggestions` | Shared event energy suggestions | Attendee (auth) |
| `/connect/events` | Public-safe nights for Connect | Attendee (auth) |
| `/connect/requests` | Incoming / outgoing Connect requests | Attendee (auth) |
| `/connect/connections` | Accepted connections | Attendee (auth) |
| `/connect/settings` | Fan Connect privacy & settings (off by default) | Attendee (auth) |
| `/dashboard/connect` · `/dashboard/connect/*` | Redirect aliases → `/connect` · `/connect/*` | Attendee (auth) |
| `/admin/fan-connect` | Fan Connect moderation overview | Admin |
| `/admin/fan-connect/settings` | Default decline cooldown (requester-only; default 30 days) | Admin |
| `/admin/fan-connect/reports` | Connect reports (+ safe context; not chat browse) | Admin |
| `/admin/fan-connect/blocks` | Connect block history | Admin |
| `/admin/fan-connect/users/[userId]` | Per-fan Connect block / report history | Admin |
| `/admin/users` | **Added** — Admin Users directory: search, status/role filters, badges, UUID or email lookup | `admin.users.view` (mutations use granular `admin.users.*`) |
| `/admin/users/[userId]` | **Added** — detail tabs Overview · **Restrictions** · Activity · Flags · Notes · Security · Audit; Restrictions panel (presets, toggles, reason, revoke/extend, Full suspension preset); safe actions (notes, flags, status, force logout, force password-reset); Impersonate modal + history when permitted; **safe fields only** (no passwords/tokens); restricted end-users see disabled actions via keys-only helpers | `admin.users.view` + granular perms per action (`add_note`, `flag`, `view_restrictions`, `add_restriction`, `revoke_restriction`, `restrict`, `suspend`, `ban`, `force_logout`, `force_password_reset`, `view_private_contact`, `view_security`, `impersonate`) |
| `/admin/appeals` | Suspension appeals queue — approve (unsuspend) / reject with optional user-facing reply | `admin.appeals.review` or `admin.users.suspend` |
| `/account/suspended` | Suspended account page — category / duration / dates, Appeal form, Logout | Authenticated (suspended) |
| `/admin/users/[userId]/impersonation` | Standalone impersonation start form | `admin.users.impersonate` |
| `/fans` | Fan Passport Directory (opt-in public Passports only) | Public |
| `/dashboard/passport` | Fan Passport (private loyalty, attendance, completion) | Attendee dashboard |
| `/dashboard/passport/settings` | Fan Passport privacy + Public discovery (+ **Improve with AI** on bio, draft-only; locked while impersonating) | Attendee dashboard |
| `/dashboard/settings` | Account settings + Appearance (light / dark / system) | Attendee dashboard |
| `/workspaces` | Post-login workspace chooser (Personal + host workspaces) | Auth |
| `/host/desk` | Ticket scanner / merch pickup for assigned events | Host team (desk perms) |
| `/host/access-denied` | Permission denied (“You do not have access…”) | Host workspace |
| `/host/team` | Host team overview (members, invites, roles, assignments, audit) | Host workspace |
| `/host/team/members` | Accepted team members list | Host workspace |
| `/host/team/invites` | Pending invites + invite modal | Host workspace |
| `/host/team/audit-log` | Team audit trail | Host workspace |
| `/host/team/[id]` | Member edit: role, status, permissions, scope, suspend/remove | Host workspace |
| `/team/invite/[token]` | Accept / decline host team invite | Public → auth |
| `/dashboard/team` | Teams / workspaces the user owns or joined | Attendee dashboard |
| `/dashboard/team/workspaces` | Set active host workspace | Attendee dashboard |
| `/dashboard/settings/notifications` | Email + push preferences, browser push enable / devices | Attendee dashboard |
| `/unsubscribe` | Marketing unsubscribe (signed token) | Public |
| `/email/preferences` | Token prefs management | Public |
| `/admin/emails` | Email outbox log | Admin |
| `/admin/email/settings` | Email / SMTP provider settings (specialist) | Admin (`admin.full_access`) |
| `/admin/emails/[id]` | Email event detail + resend | Admin |
| `/admin/push/settings` | Browser push: VAPID, provider, test push, deliveries (specialist) | Admin (`admin.full_access`) |
| `/admin/settings` | Redirect → `/admin/settings/runtime` | Admin (`admin.settings.view`) |
| `/admin/settings/runtime` | Runtime Settings dashboard (Class B + status cards) | Admin (`admin.settings.view`) |
| `/admin/settings/runtime/[category]` | Category editor (registry-driven) | Admin (`admin.settings.view` / `edit_runtime`) |
| `/admin/settings/runtime/audit` | Runtime settings audit table | Admin (`admin.settings.view_audit`) |
| `/admin/settings/email` | Redirect → `/admin/settings/runtime/email` (links to specialist) | Admin |
| `/admin/settings/push` | Redirect → `/admin/push/settings` | Admin |
| `/admin/settings/[category]` | Legacy flat alias → `/admin/settings/runtime/[category]` | Admin |
| `/admin/platform/maintenance` | Platform maintenance controls (mode, sections, schedule, bypass) | Admin (`admin.maintenance.view` / `manage`) |
| `/admin/platform/maintenance/history` | Maintenance audit history | Admin (`admin.maintenance.view`) |
| `/admin/platform/maintenance/notifications` | Advance maintenance notices | Admin (`admin.maintenance.notify`) |
| `/maintenance` | Public maintenance status page | Public |
| `/host/settings/notifications` | Redirect → `/dashboard/settings/notifications` (308) | Host workspace |
| `/f/[username]` | Public / unlisted Fan Passport (+ Connect / Message CTAs) | Public (404 if private/admin-hidden) |
| `/admin/fans` | Fan Passport Directory moderation (hide/restore) | Admin |
| `/dashboard/badges` | Badge catalog + earned state | Attendee dashboard |
| `/admin/vault` | Vault moderation (filter, hide/archive/restore, unlock summary) | Admin (`vault.moderate`) |
| `/admin/merchandise` | Merch products moderation (view/hide/restore/archive) | Admin (`merch.view_admin` / `merch.moderate`) |
| `/admin/merch` | Alias → `/admin/merchandise` | Admin |
| `/admin/merch/orders` | Alias → `/admin/merchandise/orders` | Admin |
| `/admin/merch/reports` | Alias → `/admin/merchandise/reports` | Admin |
| `/admin/merch/categories` | Marketplace category management | Admin (`merch.moderate`) |
| `/admin/merchandise/[id]` | Merch product detail + moderate | Admin (`merch.view_admin` / `merch.moderate`) |
| `/admin/merchandise/orders` | Merch fulfillments / issues (no payment amounts) | Admin (`merch.view_admin`) |
| `/admin/merchandise/reports` | Reported merch (`open`/`reviewing`/`resolved`/`dismissed`) | Admin (`merch.moderate`) |
| `/admin/merchandise/reviews` | Merch product review moderation | Admin (`merch.moderate`) |
| `/admin/merchandise/revenue` | Platform merch revenue splits (no buyer PII) | Admin (`merch.view_admin`) |
| `/admin/merchandise/print-on-demand` | POD job oversight (manual fulfill) | Admin (`merch.view_admin`) |
| `/host/legacy` | Legacy Studio overview + preview | Host workspace |
| `/host/legacy/edit` | Edit Legacy identity / CTAs / contact | Host workspace |
| `/host/legacy/content` | Content blocks + `vault_preview` config + feature Vault/events/reviews/memories | Host workspace |
| `/host/legacy/preview` | Full public preview | Host workspace |
| `/host/legacy/tier` | Tier progress + history | Host workspace |
| `/admin/legacy` | Host tiers + recalculate | Admin (`legacy.manage`) |
| `/admin/legacy/tiers` | Edit tier thresholds | Admin |
| `/host/reviews` | Reply / report reviews | Host workspace |
| `/dashboard/reviews` | Create / edit / withdraw / restore my verified reviews | Attendee dashboard |
| `/admin/reviews` | Moderate reported reviews + “Summarize reports” AI (never auto-hides) | Admin / support |
| `/login` | Auth login | Implemented |
| `/register` | Auth register | Implemented |
| `/dashboard` | Personal Command Center home (Phase 3; URL unchanged) | Protected shell |
| `/host` | Host Command Center home | Protected |
| `/host/dashboard` | Legacy alias redirect → `/host` (308) | Protected |
| `/host/roadmap` | Launch checklist (inferred from workspace data) | Host workspace |
| `/host/onboarding` | Become a host (first-time signup); existing hosts → `/host/roadmap` (302 client guard) | Authenticated |
| `/host/settings` | Host profile + taxonomy / niche + Appearance (light / dark / system) | Host workspace |
| `/host/support` | Host support ticket list + create | Host workspace |
| `/host/support/new` | Create host support ticket | Host workspace |
| `/host/support/[ticketId]` | Host ticket conversation | Host workspace |
| `/host/events` | Host event list — tabs (`?tab=`), search, filters, sort; view modes **Table** (default), List, Grid; desk staff see assigned events only | Host workspace |
| `/host/events/new` | Create event (Event Studio, 10 steps) | Host workspace |
| `/host/events/[id]` | Event detail + submit/media | Host workspace |
| `/host/events/[id]/edit` | Edit event (Event Studio; `?step=` deep-link) | Host workspace |
| `/host/events/[id]/tickets` | Ticket tiers (`TicketTypeBuilder` + Studio link) | Host workspace |
| `/host/events/[id]/check-in` | Door QR scanner (mobile UX + offline queue) | Host workspace |
| `/host/events/[id]/attendees` | Attendee search + staff assign | Host workspace |
| `/host/events/[id]/check-in/analytics` | Check-in stats | Host workspace |
| `/staff/check-in/[eventId]` | Assigned staff scanner | `host_staff` / host / admin |
| `/admin` | Admin home + on-demand daily operations AI summary | Protected |
| `/admin/events` | All events (review any + flag + Pàdéyá Pick) | Admin (`events.approve`) |
| `/admin/events/picks` | Listing Pàdéyá Picks (homepage / events page Primary+Secondary) | Admin (`events.approve`) |
| `/admin/events/review` | Approve/reject pending queue | Admin |
| `/admin/events/[id]/review` | Per-event review / flag / pause / Pàdéyá Pick | Admin (`events.approve`) |
| `/support` | Public Support Center landing | Public |
| `/support/new` | Create support ticket (auth or visitor) | Public |
| `/support/tickets/lookup` | Track ticket by number + email | Public |
| `/support/tickets/[ticketNumber]` | Public ticket tracking (email/token) | Public |
| `/support/desk` | Staff agent inbox | Support agent |
| `/support/cases` | Staff case queue | Support agent |
| `/support/cases/new` | Staff create case | Support agent |
| `/support/cases/[id]` | Staff case detail + AI Assist (draft-only) | Support agent |
| `/support/refunds` | Refund escalate queue | Support |
| `/dashboard/support` | Personal support tickets | Buyer auth |
| `/dashboard/support/new` | Create personal ticket | Buyer auth |
| `/dashboard/support/[ticketId]` | Personal ticket detail (no internal notes) | Buyer auth |
| `/admin/support` | Admin support queue + filters + “Summarize queue” AI | Admin (`admin.support.view`) |
| `/admin/support/[ticketId]` | Admin ticket detail + AI Assist (summarize / triage / reply draft / articles — never auto-send) | Admin |
| `/admin/support/settings` | Support center settings | Admin (`admin.support.manage_settings`) |

## Discovery hierarchy & breadcrumbs

Canonical entities stay `/events/[slug]` and `/@{username}`. Discovery hubs nest under `/events/…` (see [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md)).

| Kind | Example trail |
| --- | --- |
| All events | Home → Events |
| Country | Home → Events → Nigeria |
| State | Home → Events → Nigeria → Lagos |
| City | Home → Events → Nigeria → Lagos |
| Area | Home → Events → Nigeria → Lagos → Lekki |
| Category | Home → Events → Nightlife |
| City × category | Home → Events → Lagos → Nightlife |
| Event detail | Home → Events → [Country → State → City → Area] → Category → {Title} (taxonomy trail when `location_id` set; else city + category fallback) |

Rules: parents linked; current page not linked; privacy-safe labels only. Helpers: `lib/marketplace-breadcrumbs.ts`, `MarketplaceBreadcrumbs`. SEO/JSON-LD: [SEO.md](./SEO.md).

**Reserved segments** (not event slugs): `location`, `country`, `state`, `area`, `c`, `city`, `tag`, `vibe`, `free`, `vip`, `this-weekend`, `near-me`.

**Deferred hubs:** `/events/tag/*`, `/events/vibe/*`, `/hosts/c/*`, `/hosts/type/*`.

**Location URL facets:** `location_kind` + `location_slug` (cascade filter on `/events`). Premium landings: country/state/city/area via `LocationLandingClient` (hero, stats, picks, related).

**SEO / crawl:** `sitemap.ts` includes listed events + taxonomy location hubs + category hubs; excludes non-`listed` visibility. `robots.ts` disallows `/host/`, `/dashboard/`, `/admin/`, `/support/`, `/ambassador/`, `/staff/`, `/api/`, `/login`, `/register`. Vault private items are not sitemap entries (catalog is public routes only when items are listed by Vault rules). See [SEO.md](./SEO.md).

### Vault (public / host / buyer / admin)

Product rules: [VAULT.md](./VAULT.md). FE smoke: `npm run test:vault`.

| Surface | Behavior |
| --- | --- |
| Public catalog / detail | Locked: teaser + unlock CTAs only. Unlocked: body, private media, downloads. Related event/memory links. |
| Legacy Preview | Teaser cards on `/@{username}` only — never unlock payload ([LEGACY_PAGE.md](./LEGACY_PAGE.md)) |
| Host create flow | `/host/vault/new` multi-step: Content → Media → Access → Related → Preview & Publish |
| Buyer library | `/dashboard/vault` groups unlocked / followed / ticket / unlockable; access re-checked server-side |
| Admin | `/admin/vault` moderation (reason required for hide/archive/restore) |

Event detail and Event Memory pages also render related Vault teasers (same redaction rules).

### Featured Placement Slots (admin)

| Route | Notes |
| --- | --- |
| `/admin/featured-placements` | List sets |
| `/admin/featured-placements/new` | Create Primary+Secondary set |
| `/admin/featured-placements/[id]/edit` | Edit set (`id` = Primary slot UUID) |
| `/admin/events/featured` | Redirect → list |

Public surface: **Pàdéyá Picks** on homepage + discovery hubs (`PadeyaPicksSection`). APIs: `/api/v1/admin/featured-placements/*`, `GET /api/v1/events/padeya-picks`. Contract: [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md).

## Personal workspace (`/dashboard`)

Canonical **Personal** tools for the signed-in account (tickets, orders, merch wallet, Passport, Ambassadors promote & earn, account settings). Shell title **Personal**; in-shell switcher to Host when the user has (or can create) a host workspace.

**Sidebar groups** (`buyerNav` / `buyerNavGroups` in `frontend/src/lib/nav/workspace.ts`):

| Group | Items |
| --- | --- |
| **Home** | Overview (`/dashboard`), Alerts |
| **Activity** | Tickets, Orders, Merch (`/dashboard/merchandise`), Refunds |
| **Community** | Messages, Team, Connect, Following |
| **Identity** | Passport, Badges, Vault, Reviews |
| **Growth** | Ambassadors (`/dashboard/ambassador`) |
| **Account** | Settings |

Smoke: `npm run test:buyer-dashboard-nav`.

## Host Command Center

Brand: **Pàdéyá**. Host workspace stays on **`/host/*`** (not under `/dashboard`). Audit: [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md). Polish (FE-only, routes/permissions unchanged): [HOST_COMMAND_CENTER_POLISH.md](./HOST_COMMAND_CENTER_POLISH.md). Permissions + role landing: [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md). Unification chrome: [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md).

| Route | Role |
| --- | --- |
| **`/host`** | **Canonical** Host Command Center home — owner overview (`OwnerCommandCenter`) or team desk/read-only summary |
| `/host/dashboard` | **308** alias → `/host` (`next.config.ts` + defensive page) |
| `/host/roadmap` | Launch checklist (inferred from workspace data); hidden for desk-focused / read-only members |
| `/host/onboarding` | First-time become-a-host; existing hosts redirect → `/host/roadmap` |
| `/host/desk` | Ticket scanner / merch pickup for assigned events — default landing for desk-focused staff |
| `/host/support` | Host help entry → `/support` inbox |

**Sidebar groups** (`frontend/src/lib/nav/workspace.ts`, filtered by `navGroupsForWorkspace` in `host-nav.ts`):

| Group | Items (labels · paths unchanged) |
| --- | --- |
| **Home** | Overview (`/host`), Roadmap (`/host/roadmap`) |
| **Operate** | Events · Tickets & Entry (`/host/desk`) · Merch Studio (`/host/merchandise`) · Host Inbox (`/host/messages`) |
| **Grow** | Ambassador Campaigns (`/host/ambassadors`) · Sponsorships · Audience CRM (`/host/audience`) · Legacy Page · Vault Studio (`/host/vault`) |
| **Manage** | Analytics · Host Team (`/host/team`) · Host Settings (`/host/settings`) · Support (`/host/support`) |

Shell title: **Host: {display_name}**. Labels disambiguate from Personal (`buyerNav`); routes stay under `/host/*`.

Payouts, promos, templates, AI, announcements, followers, and bank accounts stay **off** the primary sidebar (deep links from Command Center, settings, or event ops).

**Role-aware landing** (`hostHomePathForWorkspace` in `host-access.ts` — used by workspace switcher; never hardcode `/host/events`):

| Actor | Default after workspace switch / invite accept |
| --- | --- |
| Host owner | `/host` |
| Desk-focused scanner / merch staff | `/host/desk` |
| Sponsor manager (when `sponsors.view` / `manage_slots`) | `/host/sponsorships` |
| Viewer / event manager / other team members | `/host` |

**Server redirects (308):** `/host/dashboard` → `/host` · `/host/events/[id]/merch` → `…/merchandise` · `/host/settings/notifications` → `/dashboard/settings/notifications`. **No** `/dashboard/host` alias.

**Event list** (`/host/events`): URL tab `?tab=` (`upcoming` default, `drafts`, `published`, `past`, `cancelled`, `all`); client search (title, venue, city, slug); status / city / visibility / date-range filters; sort (start, created, sales, revenue, title); view mode persisted in `localStorage` — **Table** default, plus List and Grid. Desk-focused staff: assigned events only; Grid coerced to Table; scanner-only rows View + Scanner; merch-only Pickup + Merch Studio (paths unchanged). Command Center “View all” → `/host/events?tab=upcoming`.

Smoke: `npm run test:host-command-center` · `npm run test:workspace-privacy`.

## Auth gates

- `/host/*` requires login; workspace pages require an onboarded host profile **or** active team membership / desk assignment for that host
- Team members see grouped nav filtered by permission toggles (`navGroupsForWorkspace` / `navForWorkspace`); payouts/bank stay owner-only
- Blocked paths → `/host/access-denied` via `canAccessHostPath` + `HostAccessGuard`
- `/host/desk` — ticket/merch tabs when `canScanTickets` / `canScanMerch` for the active workspace
- `/admin/*` requires `super_admin`, `finance_admin`, or `support_agent` (event approve API still needs `events.approve` / `admin.full_access`)
- `/admin/*` uses `RequireAuth` with **`denyWhileImpersonating`** — while an admin is impersonating a user, Admin shell shows “Admin unavailable while impersonating” (personal `/dashboard` remains available as the target)
- Site header hides Admin / Support links during impersonation
- `/admin/users` and `/admin/users/[userId]` require `admin.users.view` (or `admin.full_access`); Impersonate CTAs require `admin.users.impersonate`
- Admin user surfaces never show passwords, hashes, or raw tokens — **email is shown in full** on `/admin/users*`; phone stays gated by `admin.users.view_private_contact` when present
- Global `ImpersonationBanner` mounts in the root layout whenever a session is active (Exit restores the stashed admin session). Banner is **admin-visible only**; the target user is **not** notified (no email / in-app / push).
- Impersonation is **internal and audited** — see [AUTH.md](./AUTH.md#admin-user-impersonation)
- `/admin/taxonomy/*` and `/admin/featured-placements/*` use the admin gate; APIs require `admin.full_access` or `events.approve`

Auth product notes: [AUTH.md](./AUTH.md) · [ADMIN.md](./ADMIN.md#user-management-safe-actions) · [SECURITY.md](./SECURITY.md#admin-user-management).

## Event Studio

Host create/edit uses **Event Studio** (`components/events/studio/`):

| Layout | Behavior |
| --- | --- |
| Desktop (`lg+`) | Left step nav · center form · sticky right preview + publishing checklist |
| Mobile | Horizontal stepper · form · collapsible guest preview · sticky Save / Continue |

**10 steps:** `basics` → `location` → `schedule` → `tickets` → `media` → `lineup` → `questions` → `policies` → `seo` → `publish`. Deep-link with `?step=tickets` (legacy `venue` → `location`, `guest` → `lineup`). Access rules (`event_type` / `visibility`) live on **Tickets & Access**; location privacy stays on **Location & Privacy**.

### Step → fields (Studio FE)

| Step | Primary UI / fields |
| --- | --- |
| `basics` | Title, description, short tagline, category, vibe; **Generate with AI** for title ideas + description drafts (`StudioAIAssist`; apply fills fields only — never publishes) |
| `location` | Taxonomy cascade (`location_id`), venue name/type, private `address`, `public_location_label`, `LocationPrivacySelector` (`location_visibility`, `reveal_timing`, `reveal_note`, online URL + reveal rule) |
| `schedule` | Start/end/doors/timezone + `AgendaBuilder` |
| `tickets` | `TicketTypeBuilder` drafts (synced via ticket-type API); visibility/event access |
| `media` | Banner / mobile / gallery / teaser / share image; ConfirmAction remove → `DELETE .../media/{id}` |
| `lineup` | `PeopleLineupBuilder` |
| `questions` | Checkout question builder (types, required, options, help text); archive-when-answered via API |
| `policies` | Refund type, safety, door/re-entry, logistics, capacity |
| `seo` | SEO + social copy; preview shows **public** location label only (`scrubPrivateAddress`) |
| `publish` | `PublishChecklist`, guest preview, submit / archive / discard draft (`ConfirmAction`) |

### Client-only / privacy UX

- **`preview_checked`** is not an API field. Studio stores it in `sessionStorage` under `padeya:studio:preview_checked:{eventId}` and gates local `ready_to_submit`.
- Preview panel (`EventPreviewPanel`) approximates guest view: never show private street when visibility ≠ `full_public`.
- Public event page: `EventPublicView` + `lib/event-privacy.ts` honor `location_address_revealed` / privacy message from API.
- Destructive actions (discard draft, remove media/agenda/person/question, deactivate ticket) use `ConfirmAction` — not bare `window.confirm`.
- Smoke check (no browser): `npm run test:studio` → `scripts/studio-smoke.mjs`.

## Components

Reusable UI under `frontend/src/components/ui/` plus:

- `components/events/studio/*` — Event Studio (canonical host create/edit)
- `components/events/studio/StudioAIAssist.tsx` — Phase 1 title/description AI drafts (human apply only)
- `components/events/EventForm.tsx` — **deprecated**; do not use for new routes
- `components/events/StatusBadge.tsx`
- `components/hosts/RequireHost.tsx` · `HostTaxonomyFields`
- `components/discovery/*`, `components/taxonomy/*`, `components/related/*` — marketplace discovery (see [TAXONOMY_AND_CONTENT_GRAPH.md](./TAXONOMY_AND_CONTENT_GRAPH.md))
- Location: `LocationFilterBar`, `LocationSelector`, `LocationChips`, `LocationLandingHero`, `LocationStats`, `RelatedLocations`
- Picks: `PadeyaPicksSection`, `FeaturedPlacementCard`
- Admin placements: `AdminPlacementForm`, `PlacementPreview`
- `components/layout/MarketplaceBreadcrumbs.tsx` · `MobileBottomNav.tsx` · `HostScannerDock.tsx`
- `components/admin/taxonomy/*` — TaxonomyManager / VocabAdminPage / LocationsAdminPage / SubcategoryAdminPanel
- Discovery hubs emit `CollectionPage` + `BreadcrumbList` JSON-LD (`lib/seo/hub-page.tsx`)
- Facet state is URL-synced (`EventDiscoveryView` + locked hub chips)
- `components/events/studio/TaxonomyFields.tsx` · `SeoPreviewCard.tsx`
- `components/pwa/*` — install prompt, offline banner, SW registration (`PushNotificationOptIn` re-exports `PushSettingsPanel`)
- `components/notifications/*` — toast bridge, bell, push settings panel, permission prompt
- `components/analytics/*` — `AnalyticsProvider`, `TrackImpression`, `LocationPageViewTracker`, `EventAnalyticsDashboard`, funnel/trend panels

## Analytics (Phase 14)

Product reference: [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md), privacy [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md).

**Client instrumentation** (SSR-safe queue/batch): `lib/analytics.ts`, `lib/analytics-client.ts`, hooks under `hooks/useAnalytics.ts` (+ impression/page/UTM hooks). Wired on listing cards (`EventCard`), public event detail (`EventPublicView`), events list, checkout, location filter/landings, and Pàdéyá Picks. Root layout wraps `AnalyticsProvider`.

**Host:** portfolio at `/host/analytics`; per-event funnel/sources/tickets at `/host/events/[id]/analytics`.  
**Admin:** platform pages under `/admin/analytics/*`; per-event at `/admin/events/[id]/analytics`.  
Door stats remain `/host/events/[id]/check-in/analytics`.

**Smoke:** `npm run test:analytics`, `npm run test:taxonomy`, `npm run test:discovery`.

## Messaging + demo QA

Product docs: [MESSAGING.md](./MESSAGING.md) · [FAN_CONNECT.md](./FAN_CONNECT.md) · [DEMO_DATA.md](./DEMO_DATA.md) · [PRIVACY.md](./PRIVACY.md) · [SECURITY.md](./SECURITY.md#in-app-messaging-privacy).

**CTAs:** `StartMessageButton` (Message Host on Legacy/events) · `HostMessageFanButton` (Message Fan on Passport when allowed) · `ConnectButton` (Fan Connect / Message on Passport after accept).

**Chat UI** (`components/messaging/`): `MessageBubble` · `MessageTimestamp` · `MessageStatus` · `MessageMeta` · `MessageActionMenu` / `MessageContextMenu` · `QuotedMessage` · `ReplyPreview` · `MessageEditComposer` · `PinnedMessagesBar` · `ThreadSearch` · `DateSeparator` · `StarredMessagesList` · `MessagesInbox`.

| UX | Behavior |
| --- | --- |
| Timestamps | Bubble clock (mobile always / desktop hover); day separators; thread-list relative times (`format-message-time.ts`) |
| Edit / reply | Composer edit mode + reply chip; bubble quote; scroll + brief highlight on tap |
| Pins | Shared banner / drawer at top of thread |
| Stars | Personal indicator + inbox `?filter=starred`; open via `?m=` |
| Status | Own Sent/Delivered/Read/Failed + Edited from real `peer_read_at` / status |
| Actions | ··· menu (desktop hover) · long-press / always-visible ··· (mobile) |

**Realtime UX:** `useMessageSocket` + `MessagingSocketStatus`; typing; live unread; pin/edit merge; attach only when `can_attach` (hidden for requests / blocked / pre–Fan Connect). No star WS.

**`/demo` shortcuts** (login via auth API + `DemoPass123!`): Tolu ↔ DJ Maze thread · Chidi ↔ Bayo thread · Starred messages · pinned message demo · Tolu/Amaka/Chidi/Ada inboxes · host inboxes · admin message reports · Fan Connect hub / connections / pending / admin Connect reports. Prefer `?filter=requests` for Ada/Praise request QA.

**Smoke:** `npm run test:messaging` (composer/attachments/WS/theme tokens) · `npm run test:fan-connect` · `npm run test:theme` · `npm run test:pwa`.

## Theme

- Preference: light / dark / system (`padeya-theme`); `<html class="dark">` only
- Controls: header/topbar toggle; Appearance on `/dashboard/settings` + `/host/settings`; `/demo` panel
- Ticket QR: high-contrast white plate (`TicketQrPanel`) — scannable in dark mode
- Docs: [DARK_MODE_QA.md](./DARK_MODE_QA.md) · [BRAND_GUIDE.md](./BRAND_GUIDE.md)

## PWA (Phase 18)

- Manifest: `/manifest.webmanifest` (`theme_color` `#0a0a0a`, `background_color` `#000000`)
- Runtime browser chrome: `theme-color` metas follow resolved light/dark (`THEME_COLOR` in `lib/theme.ts`)
- Icons: `/icons/icon-192.png`, `/icons/icon-512.png`, `/icons/apple-touch-icon.png`
- Service worker: `/sw.js` (production only; unregisters in `next dev`) — push receive + `notificationclick` → `action_url` (`padeya-pwa-v24`)
- Browser push UX: `/dashboard/settings/notifications` · admin `/admin/push/settings` · admin per-type channels `/admin/notifications/settings` · docs [PUSH_NOTIFICATIONS.md](./PUSH_NOTIFICATIONS.md) · [NOTIFICATION_PUSH_AUDIT.md](./NOTIFICATION_PUSH_AUDIT.md)
- Mobile buyer nav includes **Alerts** → `/dashboard/notifications`
- Smoke tests: `npm run test:pwa` (includes notification settings, permission/unsupported states, toast, mark-read wiring)
