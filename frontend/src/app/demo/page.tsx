import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import {
  DemoSessionShortcuts,
  type DemoSessionShortcutGroup,
} from "@/components/demo/DemoSessionShortcuts";
import { DemoThemePanel } from "@/components/theme/DemoThemePanel";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  HostCard,
  SectionHeader,
} from "@/components/ui";
import { brand } from "@/lib/brand";
import { privateAreaMetadata } from "@/lib/seo/noindex";

export const dynamic = "force-dynamic";

export const metadata: Metadata = privateAreaMetadata("Demo");

const DEMO_PASSWORD = "DemoPass123!";

const DEMO_TEAM_INVITE_TOKEN = "demo-padeya-team-invite-afrobeats";

/** One-click login for DJ Maze host-team QA. */
const HOST_TEAM_QA_SHORTCUTS: DemoSessionShortcutGroup[] = [
  {
    title: "Host team",
    description:
      "Signs in with the shared demo password, then opens team / desk surfaces.",
    shortcuts: [
      {
        label: "Open Host Team",
        email: "host@demo.padeye.test",
        href: "/host/team",
        hint: "DJ Maze · members · invites · audit",
      },
      {
        label: "Open Gate Scanner account",
        email: "gate@demo.padeye.test",
        href: "/host/desk",
        hint: "tickets.scan_qr · Afrobeats Night Live only",
      },
      {
        label: "Open Pickup Staff account",
        email: "pickup@demo.padeye.test",
        href: "/host/desk",
        hint: "merch.scan_pickup_qr · Afrobeats Night Live only",
      },
      {
        label: "Open Team Audit Log",
        email: "host@demo.padeye.test",
        href: "/host/team/audit-log",
        hint: "Invite · accept · permission · desk scans",
      },
      {
        label: "Open Invite Accept page",
        email: "team-invitee@demo.padeye.test",
        href: `/team/invite/${DEMO_TEAM_INVITE_TOKEN}`,
        hint: "Pending Teammate · matching email required",
      },
      {
        label: "Open Event Ops Manager",
        email: "ops@demo.padeye.test",
        href: "/host/team",
        hint: "Admin · host-wide",
      },
      {
        label: "Open Sponsor Observer (host desk)",
        email: "sponsor-observer@demo.padeye.test",
        href: "/host/sponsorships",
        hint: "DJ Maze host team · not a sponsor brand login",
      },
    ],
  },
];

/** One-click login via existing /auth/login, then open Fan Connect QA. */
const FAN_CONNECT_QA_SHORTCUTS: DemoSessionShortcutGroup[] = [
  {
    title: "Fan Connect",
    description: "Signs in as the named fan (or admin), then opens Connect surfaces.",
    shortcuts: [
      {
        label: "Open Fan Connect",
        email: "fan1@demo.padeye.test",
        href: "/connect",
        hint: "Tolu · suggestions · requests · connections",
      },
      {
        label: "Open Tolu Fan Connect",
        email: "fan1@demo.padeye.test",
        href: "/connect",
        hint: "Suggested Amaka · pending Sade · blocked Bode",
      },
      {
        label: "Open Chidi connections",
        email: "fan3@demo.padeye.test",
        href: "/connect/connections",
        hint: "Connected with Bayo · Product Demo Night",
      },
      {
        label: "Open pending requests",
        email: "fan4@demo.padeye.test",
        href: "/connect/requests",
        hint: "Sade · incoming from Tolu",
      },
      {
        label: "Open fan-fan message thread",
        email: "fan3@demo.padeye.test",
        href: "fan-fan-thread",
        hint: "Chidi ↔ Bayo · Fan Connect chat",
      },
      {
        label: "Open Fan Connect admin reports",
        email: "admin@demo.padeye.test",
        href: "/admin/fan-connect/reports",
        hint: "Tolu → Bode open report",
      },
    ],
  },
];

/** One-click admin impersonation QA against seeded demo accounts. */
const IMPERSONATION_QA_SHORTCUTS: DemoSessionShortcutGroup[] = [
  {
    title: "Impersonation",
    description:
      "Seed logins still work normally. Impersonation opens the admin user record — start from the modal; banner shows for demo seeds; audit is never skipped.",
    shortcuts: [
      {
        label: "Impersonate Demo Buyer",
        email: "admin@demo.padeye.test",
        href: "impersonate:buyer@demo.padeye.test",
        hint: "Audited session · Demo seed account banner",
      },
      {
        label: "Impersonate Tolu (fan1)",
        email: "admin@demo.padeye.test",
        href: "impersonate:fan1@demo.padeye.test",
        hint: "Buyer RBAC only · Exit restores admin",
      },
      {
        label: "Impersonate DJ Maze host",
        email: "admin@demo.padeye.test",
        href: "impersonate:host@demo.padeye.test",
        hint: "Host tools if target has them",
      },
      {
        label: "Open Admin Users",
        email: "admin@demo.padeye.test",
        href: "/admin/users",
        hint: "Look up by email · e.g. buyer@demo.padeye.test",
      },
      {
        label: "Login as Demo Buyer (normal)",
        email: "buyer@demo.padeye.test",
        href: "/dashboard",
        hint: "Normal seed login — not impersonation",
      },
    ],
  },
];

/** One-click Ambassadors QA (DJ Maze · Afrobeats Night Live open campaign). */
const AMBASSADORS_QA_SHORTCUTS: DemoSessionShortcutGroup[] = [
  {
    title: "Ambassadors",
    description:
      "Open landing, event Promote CTA, Tolu / host / admin Ambassadors surfaces. Seed demo data first.",
    shortcuts: [
      {
        label: "Open Ambassadors landing",
        email: "fan1@demo.padeye.test",
        href: "/ambassadors",
        hint: "Public landing · eligible events · Afrobeats Night",
      },
      {
        label: "Open Event with Promote CTA",
        email: "fan1@demo.padeye.test",
        href: "/events/demo-afrobeats-night-live",
        hint: "Afrobeats Night Live · Promote this event",
      },
      {
        label: "Open Tolu Ambassador Dashboard",
        email: "fan1@demo.padeye.test",
        href: "/dashboard/ambassador",
        hint: "TOLUAFRO · clicks · pending / payable / leaderboard",
      },
      {
        label: "Open Host Ambassador Dashboard",
        email: "host@demo.padeye.test",
        href: "/host/ambassadors",
        hint: "DJ Maze · Afrobeats Night Ambassador Drive",
      },
      {
        label: "Open Admin Ambassador Conversions",
        email: "admin@demo.padeye.test",
        href: "/admin/ambassadors/conversions",
        hint: "Attributed · approved · reversed commission rows",
      },
    ],
  },
];

/** One-click login via existing /auth/login, then open the QA surface. */
const MESSAGE_QA_SHORTCUTS: DemoSessionShortcutGroup[] = [
  {
    title: "Buyer",
    description: "Signs in as the named fan, then opens their inbox.",
    shortcuts: [
      {
        label: "Open Tolu inbox",
        email: "fan1@demo.padeye.test",
        href: "/dashboard/messages",
        hint: "3 active · unread · archived · blocked",
      },
      {
        label: "Open Tolu ↔ DJ Maze thread",
        email: "fan1@demo.padeye.test",
        href: "tolu-maze-thread",
        hint: "Edit · reply · pin · star · entry-flow attachment",
      },
      {
        label: "Open Chidi ↔ Bayo thread",
        email: "fan3@demo.padeye.test",
        href: "fan-fan-thread",
        hint: "Fan Connect · reply · pin · edit · star · read demo",
      },
      {
        label: "Open Starred messages",
        email: "fan1@demo.padeye.test",
        href: "starred-messages",
        hint: "Tolu’s saved DJ Maze QR tip",
      },
      {
        label: "Open pinned message demo",
        email: "fan1@demo.padeye.test",
        href: "pinned-demo-thread",
        hint: "Pinned Afrobeats Night Live context",
      },
      {
        label: "Open Amaka inbox",
        email: "fan2@demo.padeye.test",
        href: "/dashboard/messages",
        hint: "Unread + Vault-related thread",
      },
      {
        label: "Open Chidi inbox",
        email: "fan3@demo.padeye.test",
        href: "/dashboard/messages",
        hint: "Includes reported thread",
      },
      {
        label: "Open Ada message request test",
        email: "fan7@demo.padeye.test",
        href: "/dashboard/messages?filter=requests",
        hint: "Request filter · Ada ↔ Praise",
      },
    ],
  },
  {
    title: "Host",
    description: "Signs in as the host owner, then opens host messages.",
    shortcuts: [
      {
        label: "Open DJ Maze inbox",
        email: "host@demo.padeye.test",
        href: "/host/messages",
        hint: "4 threads · unread · archived",
      },
      {
        label: "Open Lagos Comedy Hub inbox",
        email: "host2@demo.padeye.test",
        href: "/host/messages",
        hint: "Blocked + follower + inquiry",
      },
      {
        label: "Open Tech Connect Africa inbox",
        email: "tech@demo.padeye.test",
        href: "/host/messages",
        hint: "Vault · reported · ticket-holder",
      },
      {
        label: "Open Praise Experience message requests",
        email: "praise@demo.padeye.test",
        href: "/host/messages?filter=requests",
        hint: "Ada request waiting",
      },
      {
        label: "Open Mainland Vibes inbox",
        email: "mainland@demo.padeye.test",
        href: "/host/messages",
        hint: "2 active threads",
      },
    ],
  },
  {
    title: "Admin",
    description: "Uses the same login API — admin for reports/users, Amaka for notifications QA.",
    shortcuts: [
      {
        label: "Open Message Reports",
        email: "admin@demo.padeye.test",
        href: "/admin/message-reports",
      },
      {
        label: "Open Reported Thread",
        email: "admin@demo.padeye.test",
        href: "reported-thread",
        hint: "Prefers reviewing / open report",
      },
      {
        label: "Open Admin Users",
        email: "admin@demo.padeye.test",
        href: "/admin/users",
      },
      {
        label: "Open Notifications",
        email: "fan2@demo.padeye.test",
        href: "/dashboard/notifications",
        hint: "Amaka · unread message notices",
      },
    ],
  },
];

const ACCOUNT_GROUPS = [
  {
    title: "Buyer",
    accounts: [{ email: "buyer@demo.padeye.test", name: "Demo Buyer", role: "buyer" }],
  },
  {
    title: "Hosts",
    accounts: [
      { email: "host@demo.padeye.test", name: "DJ Maze", role: "host" },
      { email: "host2@demo.padeye.test", name: "Lagos Comedy Hub", role: "host" },
      { email: "mainland@demo.padeye.test", name: "Mainland Vibes", role: "host" },
      { email: "tech@demo.padeye.test", name: "Tech Connect Africa", role: "host" },
      { email: "praise@demo.padeye.test", name: "Praise Experience", role: "host" },
    ],
  },
  {
    title: "DJ Maze host team",
    accounts: [
      {
        email: "ops@demo.padeye.test",
        name: "Event Ops Manager",
        role: "admin · host-wide",
      },
      {
        email: "gate@demo.padeye.test",
        name: "Gate Scanner",
        role: "scanner · Afrobeats only",
      },
      {
        email: "pickup@demo.padeye.test",
        name: "Pickup Staff",
        role: "merch · Afrobeats only",
      },
      {
        email: "sponsor-observer@demo.padeye.test",
        name: "Sponsor Observer (host desk)",
        role: "DJ Maze team · host sponsorship read-only — not sponsor brand",
      },
      {
        email: "team-invitee@demo.padeye.test",
        name: "Pending Teammate",
        role: "pending invite",
      },
    ],
  },
  {
    title: "Staff & ops",
    accounts: [
      { email: "staff@demo.padeye.test", name: "Gate Staff", role: "host_staff" },
      { email: "support@demo.padeye.test", name: "Demo Support Agent", role: "support_agent" },
      { email: "finance@demo.padeye.test", name: "Finance Admin", role: "finance_admin" },
      { email: "admin@demo.padeye.test", name: "Demo Super Admin", role: "super_admin" },
    ],
  },
  {
    title: "Sponsor brand workspaces",
    accounts: [
      {
        email: "sponsor-owner-neonpalm-drinks@demo.padeya.test",
        name: "NeonPalm Drinks",
        role: "owner · verified public profile",
      },
      {
        email: "sponsor-owner-korawave-pay@demo.padeya.test",
        name: "KoraWave Pay",
        role: "owner · verified public profile",
      },
      {
        email: "sponsor-viewer-neonpalm-drinks@demo.padeya.test",
        name: "NeonPalm Viewer",
        role: "read-only sponsor team",
      },
    ],
  },
  {
    title: "Named fans (Passport)",
    accounts: [
      { email: "fan1@demo.padeye.test", name: "Tolu Nightlife Explorer (@toluwave)", role: "buyer" },
      { email: "fan2@demo.padeye.test", name: "Amaka Concert Lover (@amakaconcerts)", role: "buyer" },
      { email: "fan3@demo.padeye.test", name: "Chidi Tech Regular (@chiditech)", role: "buyer" },
      { email: "fan4@demo.padeye.test", name: "Sade Comedy Fan (@sadecomedy)", role: "buyer" },
      { email: "fan5@demo.padeye.test", name: "Kunle VIP Regular (@kunlevip)", role: "buyer" },
      { email: "fan6@demo.padeye.test", name: "Mira Lagos Explorer (@miralagos)", role: "buyer" },
      { email: "fan7@demo.padeye.test", name: "Ada First Timer (@adafirsttimer)", role: "buyer" },
      { email: "fan8@demo.padeye.test", name: "Bayo Campus Fan (@bayocampus)", role: "buyer" },
    ],
  },
] as const;

const LINK_GROUPS = [
  {
    title: "Public",
    links: [
      { href: "/", label: "Home" },
      { href: "/events", label: "Events" },
      { href: "/hosts", label: "Hosts" },
      { href: "/@djmaze", label: "Host Legacy — DJ Maze (Message Host)" },
      { href: "/@lagoscomedyhub", label: "Host Legacy — Lagos Comedy Hub" },
      { href: "/@techconnectafrica", label: "Host Legacy — Tech Connect Africa" },
      { href: "/@praiseexperience", label: "Host Legacy — Praise Experience" },
      { href: "/@mainlandvibes", label: "Host Legacy — Mainland Vibes" },
      { href: "/fans", label: "Fan Passport Directory" },
      { href: "/f/toluwave", label: "Public Fan Passport (@toluwave)" },
      { href: "/f/amakaconcerts", label: "Public Fan Passport (@amakaconcerts)" },
      { href: "/f/chiditech", label: "Public Fan Passport (@chiditech)" },
      { href: "/f/kunlevip", label: "Public Fan Passport (@kunlevip, not in directory)" },
      { href: "/f/bayocampus", label: "Unlisted Fan Passport (@bayocampus, direct link)" },
      { href: "/sponsorships", label: "Sponsorships marketplace" },
      { href: "/sponsorships/hosts", label: "Sponsor hosts" },
      { href: "/login", label: "Login" },
      { href: "/register", label: "Register" },
    ],
  },
  {
    title: "Personal",
    links: [
      { href: "/dashboard", label: "Personal" },
      { href: "/dashboard/tickets", label: "Tickets" },
      { href: "/dashboard/messages", label: "Messages" },
      { href: "/dashboard/messages/settings", label: "Message settings (fan)" },
      { href: "/dashboard/notifications", label: "Notifications" },
      { href: "/dashboard/messages/notifications", label: "Message notifications" },
      { href: "/dashboard/passport", label: "Passport" },
      { href: "/dashboard/vault", label: "Vault" },
      { href: "/dashboard/reviews", label: "Reviews" },
      { href: "/dashboard/refunds", label: "Refunds" },
    ],
  },
  {
    title: "Host",
    links: [
      { href: "/host", label: "Host home" },
      { href: "/host/team", label: "Host team" },
      { href: "/host/team/members", label: "Team members" },
      { href: "/host/team/invites", label: "Team invites" },
      { href: "/host/team/audit-log", label: "Team audit log" },
      { href: "/host/desk", label: "Desk (scanner / pickup)" },
      { href: `/team/invite/${DEMO_TEAM_INVITE_TOKEN}`, label: "Invite accept (demo token)" },
      { href: "/host/events", label: "Events" },
      { href: "/host/messages", label: "Messages" },
      { href: "/host/messages/settings", label: "Message settings (host)" },
      { href: "/host/messages/notifications", label: "Message notifications" },
      { href: "/host/legacy", label: "Legacy" },
      { href: "/host/vault", label: "Vault" },
      { href: "/host/audience", label: "Audience" },
      { href: "/host/followers", label: "Followers" },
      { href: "/host/analytics", label: "Analytics" },
      { href: "/host/payouts", label: "Payouts" },
      { href: "/host/promos", label: "Promos" },
      { href: "/host/ambassadors", label: "Ambassadors" },
      { href: "/host/sponsorships", label: "Sponsorships" },
    ],
  },
  {
    title: "Admin & support",
    links: [
      { href: "/admin", label: "Admin" },
      { href: "/admin/events", label: "Admin events" },
      { href: "/admin/users", label: "Admin users (impersonation)" },
      { href: "/admin/reviews", label: "Reviews" },
      { href: "/admin/message-reports", label: "Message reports" },
      { href: "/admin/fans", label: "Fan Passports" },
      { href: "/admin/payouts", label: "Payouts" },
      { href: "/admin/analytics", label: "Analytics" },
      { href: "/admin/vault", label: "Vault" },
      { href: "/admin/sponsorships", label: "Sponsorships" },
      { href: "/support", label: "Support inbox" },
      { href: "/support/refunds", label: "Support refunds" },
    ],
  },
] as const;

const EVENT_LINKS = [
  { href: "/events/demo-afrobeats-night-live", label: "Afrobeats Night Live", tag: "DJ Maze" },
  { href: "/events/demo-detty-friday-live", label: "Detty Friday Rooftop", tag: "Completed" },
  { href: "/events/demo-mainland-after-dark", label: "Mainland After Dark", tag: "DJ Maze" },
  { href: "/events/demo-lagos-comedy-jam", label: "Laugh Lagos Live", tag: "Comedy" },
  { href: "/events/demo-island-comedy-night", label: "Sunday Comedy Room", tag: "Completed" },
  { href: "/events/demo-founders-mixer-lagos", label: "Founders Mixer Lagos", tag: "Tech" },
  { href: "/events/demo-startup-demo-evening", label: "Product Demo Night", tag: "Completed" },
  { href: "/events/demo-praise-experience-live", label: "Choir & Community Live", tag: "Gospel" },
  { href: "/events/demo-worship-under-stars", label: "Worship Night Ibadan", tag: "Completed" },
  { href: "/events/demo-food-and-flow", label: "Mainland Food & Culture Fest", tag: "Completed" },
  { href: "/events/demo-mainland-vibes-summer", label: "Lagos Creative Market", tag: "Lifestyle" },
  {
    href: "/events/demo-afrobeats-night-live/checkout",
    label: "Afrobeats checkout",
    tag: "Checkout",
  },
  {
    href: "/u/djmaze/memories/demo-detty-friday-live",
    label: "Detty Friday Memory",
    tag: "Memory",
  },
  { href: "/@djmaze", label: "DJ Maze Legacy", tag: "Legacy" },
  { href: "/@djmaze/vault", label: "DJ Maze Vault", tag: "Vault" },
] as const;

const FLOWS = [
  {
    title: "Buyer journey",
    steps:
      "Browse events → checkout → payment/free → My Tickets QR → Fan Passport → reviews",
  },
  {
    title: "Door check-in",
    steps: "Gate Staff → event check-in → camera/manual scan → door stats",
  },
  {
    title: "Host team",
    steps:
      "DJ Maze → /host/team → invite → Gate Scanner / Pickup Staff on Afrobeats desk → audit log",
  },
  {
    title: "Host ops",
    steps: "DJ Maze → events → analytics → promos, ambassadors, audience, Vault, payouts",
  },
  {
    title: "Support & finance",
    steps: "Support refunds (escalate) → Finance approve/reject → Super Admin mark payouts paid",
  },
  {
    title: "Admin & sponsors",
    steps: "Admin analytics → moderate reviews/Vault → sponsorship marketplace inquiries",
  },
  {
    title: "Admin impersonation (demo)",
    steps:
      "admin@ → /admin/users (email lookup) → Impersonate buyer/fan/host → banner shows Demo seed account → Exit; audit always written (target is not notified)",
  },
] as const;

const FEATURED_HOSTS = [
  {
    displayName: "DJ Maze",
    username: "djmaze",
    bio: "Afrobeats & Detty nights",
    city: "Lagos",
    avatarUrl: "/demo/hosts/djmaze-avatar.svg",
    verified: true,
    tier: "Icon",
  },
  {
    displayName: "Lagos Comedy Hub",
    username: "lagoscomedyhub",
    bio: "Island comedy culture",
    city: "Lagos",
    avatarUrl: "/demo/hosts/lagoscomedyhub-avatar.svg",
    verified: true,
    tier: "Established",
  },
  {
    displayName: "Tech Connect Africa",
    username: "techconnectafrica",
    bio: "Founders & builders",
    city: "Lagos",
    avatarUrl: "/demo/hosts/techconnectafrica-avatar.svg",
    verified: true,
    tier: "Established",
  },
] as const;

function demoEnabled(): boolean {
  const flag = (process.env.NEXT_PUBLIC_DEMO_MODE || "").toLowerCase();
  if (flag === "true" || flag === "1") return true;
  const env = (process.env.NODE_ENV || "").toLowerCase();
  return env === "development";
}

export default function DemoPage() {
  if (!demoEnabled()) {
    notFound();
  }

  return (
    <main className="relative min-h-screen min-w-0 overflow-x-clip bg-ink text-paper">
      <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0" />
      <div aria-hidden className="padeya-grain pointer-events-none absolute inset-0 opacity-40" />

      <Container className="relative min-w-0 space-y-10 py-10 sm:space-y-12 sm:py-16">
        <header className="max-w-3xl space-y-4">
          <Badge tone="accent">Local only</Badge>
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-accent">
            {brand.name} demo control center
          </p>
          <h1 className="text-balance text-3xl font-extrabold tracking-tight sm:text-5xl">
            Best starting point for testing
          </h1>
          <p className="text-base leading-relaxed text-subtle-foreground sm:text-lg">
            Credentials, seeded hosts/events, role-grouped quick links, and recommended
            QA flows — for local development only.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Link href="/login">
              <Button size="lg">Go to login</Button>
            </Link>
            <Link href="/events">
              <Button size="lg" variant="outline-dark">
                Browse events
              </Button>
            </Link>
          </div>
        </header>

        <Alert
          tone="warning"
          title="Never use this page in production"
          className="border-accent/40 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--primary)_12%,transparent),transparent_55%)] text-paper [&_*]:text-inherit"
        >
          <p className="text-subtle-foreground">
            Demo seed/reset is blocked when{" "}
            <code className="text-accent">APP_ENV=production</code>. Shared password for
            all accounts:{" "}
            <code className="rounded bg-ink/50 px-1.5 py-0.5 font-mono text-accent">
              {DEMO_PASSWORD}
            </code>
          </p>
        </Alert>

        <DemoThemePanel />

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Host team QA"
            title="One-click DJ Maze team shortcuts"
            description="Owner, Gate Scanner, Pickup Staff, audit log, and pending invite accept. Seed demo data first."
          />
          <DemoSessionShortcuts groups={HOST_TEAM_QA_SHORTCUTS} />
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Fan Connect QA"
            title="One-click Fan Connect shortcuts"
            description="Switches session with the shared demo password, then opens Connect. Seed demo data first."
          />
          <DemoSessionShortcuts groups={FAN_CONNECT_QA_SHORTCUTS} />
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Ambassadors QA"
            title="One-click Ambassadors shortcuts"
            description="DJ Maze · Afrobeats Night Ambassador Drive (TOLUAFRO / AMAKA20 / CHIDILIVE). Seed demo data first."
          />
          <DemoSessionShortcuts groups={AMBASSADORS_QA_SHORTCUTS} />
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Impersonation QA"
            title="One-click seed impersonation shortcuts"
            description="Normal seed login still works. Impersonation from admin opens the user record — banner shows Demo seed account; auditing is never skipped in demo mode."
          />
          <DemoSessionShortcuts groups={IMPERSONATION_QA_SHORTCUTS} />
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Messaging QA"
            title="One-click inbox shortcuts"
            description="Switches session with the shared demo password (existing login API), then opens the route. Seed messaging data first."
          />
          <DemoSessionShortcuts groups={MESSAGE_QA_SHORTCUTS} />
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Credentials"
            title="Demo accounts by role"
            description="Copy an email, use the shared password, then open the matching workspace."
          />
          <div className="grid gap-4 lg:grid-cols-3">
            {ACCOUNT_GROUPS.map((group) => (
              <Card key={group.title} variant="dark" className="space-y-3">
                <h3 className="text-lg font-extrabold text-paper">{group.title}</h3>
                <ul className="space-y-3">
                  {group.accounts.map((account) => (
                    <li
                      key={account.email}
                      className="border-b border-paper/10 pb-3 last:border-0 last:pb-0"
                    >
                      <p className="font-semibold">{account.name}</p>
                      <p className="text-xs uppercase tracking-wide text-subtle-foreground">
                        {account.role}
                      </p>
                      <code className="mt-1 block break-all text-sm text-accent">
                        {account.email}
                      </code>
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Flows"
            title="Recommended user journeys"
            description="Run these paths to cover the product end to end."
          />
          <div className="grid gap-4 md:grid-cols-2">
            {FLOWS.map((flow) => (
              <Card key={flow.title} variant="dark" className="space-y-2">
                <h3 className="font-extrabold text-paper">{flow.title}</h3>
                <p className="text-sm leading-relaxed text-subtle-foreground">{flow.steps}</p>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Quick links"
            title="Jump by surface"
          />
          <div className="grid gap-4 md:grid-cols-2">
            {LINK_GROUPS.map((group) => (
              <Card key={group.title} variant="dark" className="space-y-3">
                <h3 className="font-extrabold">{group.title}</h3>
                <div className="flex flex-wrap gap-2">
                  {group.links.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="rounded-full border border-paper/15 px-3 py-1.5 text-xs font-semibold transition-colors hover:border-accent hover:text-accent"
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Seeded"
            title="Featured demo hosts"
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURED_HOSTS.map((host) => (
              <HostCard key={host.username} {...host} />
            ))}
          </div>
        </section>

        <section className="space-y-6">
          <SectionHeader
            tone="dark"
            eyebrow="Events & Legacy"
            title="Featured demo deep links"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            {EVENT_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-paper/15 px-4 py-3 transition-colors hover:border-accent"
              >
                <span className="font-semibold">{link.label}</span>
                <Badge tone="accent">{link.tag}</Badge>
              </Link>
            ))}
          </div>
        </section>

        <section className="space-y-4 border-t border-paper/10 pt-8">
          <h2 className="text-xl font-extrabold">Seed / reset (backend)</h2>
          <Card variant="dark" className="space-y-3">
            <p className="text-sm text-subtle-foreground">
              Run from the repo root in a local environment only.
            </p>
            <ul className="space-y-2 font-mono text-sm text-accent">
              <li className="break-all rounded-[var(--radius-md)] bg-ink/40 px-3 py-2">
                cd backend
              </li>
              <li className="break-all rounded-[var(--radius-md)] bg-ink/40 px-3 py-2">
                python -m scripts.seed_demo_data
              </li>
              <li className="break-all rounded-[var(--radius-md)] bg-ink/40 px-3 py-2">
                python -m scripts.seed_demo_data --reset
              </li>
              <li className="break-all rounded-[var(--radius-md)] bg-ink/40 px-3 py-2">
                python -m scripts.reset_demo_data
              </li>
            </ul>
          </Card>
        </section>
      </Container>
    </main>
  );
}
