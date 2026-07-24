import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Static path segment → label. Unknown segments are title-cased.
 * Workspace root crumbs use shell `homeLabel` (Personal / Host: {name}), not these.
 * Keep `dashboard` in sync with PERSONAL_WORKSPACE_TITLE in host-access.ts.
 */
const SEGMENT_LABELS: Record<string, string> = {
  host: "Host",
  dashboard: "Personal",
  admin: "Admin",
  support: "Support",
  /** Match Personal sidebar Earn → Ambassadors (path stays singular). */
  ambassador: "Ambassadors",
  staff: "Staff",
  events: "Events",
  desk: "Tickets & Entry",
  roadmap: "Roadmap",
  notifications: "Alerts",
  connect: "Connect",
  messages: "Messages",
  new: "New",
  edit: "Edit",
  tickets: "Tickets",
  "check-in": "Check-in",
  "offline-check-in": "Offline check-in",
  analytics: "Analytics",
  attendees: "Attendees",
  tables: "Tables",
  memory: "Memory",
  ai: "AI Copilot",
  preview: "Preview",
  vault: "Vault",
  earnings: "Earnings",
  links: "Links",
  "how-it-works": "How it works",
  subscriptions: "Subscriptions",
  legacy: "Legacy",
  audience: "Audience",
  payouts: "Payouts",
  promos: "Promos",
  merchandise: "Merchandise",
  merch: "Merch",
  discounts: "Discounts",
  "size-charts": "Size charts",
  "stock-alerts": "Stock alerts",
  /** Personal `/dashboard/team` = my host workspaces; Host uses workspaceRoot override. */
  team: "Workspaces",
  settings: "Settings",
  followers: "Followers",
  announcements: "Announcements",
  ambassadors: "Ambassadors",
  sponsorships: "Sponsorships",
  templates: "Templates",
  "bank-accounts": "Bank accounts",
  reviews: "Reviews",
  orders: "Orders",
  refunds: "Refunds",
  following: "Following",
  passport: "Passport",
  badges: "Badges",
  transfer: "Transfer",
  hosts: "Hosts",
  users: "Users",
  payments: "Payments",
  ledger: "Ledger",
  cms: "CMS",
  blog: "Blog",
  banners: "Banners",
  faqs: "FAQs",
  categories: "Categories",
  memories: "Memories",
  "audit-logs": "Audit logs",
  review: "Review",
  cases: "Cases",
  inbox: "Inbox",
  revenue: "Revenue",
  tiers: "Tiers",
  tier: "Tier",
  "ai-summary": "AI summary",
  onboarding: "Onboarding",
};

/**
 * Host workspace crumb overrides — keep Personal `/dashboard` labels unchanged.
 * User-facing Host sidebar copy only (never expose code identifiers).
 */
const HOST_SEGMENT_LABELS: Record<string, string> = {
  merchandise: "Merch Studio",
  messages: "Host Inbox",
  ambassadors: "Ambassador Campaigns",
  audience: "Audience CRM",
  vault: "Vault Studio",
  team: "Host Team",
  settings: "Host Settings",
  desk: "Tickets & Entry",
  legacy: "Legacy Page",
};

/** Canonical overview homes show `homeLabel / Overview` (not a bare root crumb). */
const OVERVIEW_HOME_HREFS = new Set([
  "/dashboard",
  "/host",
  "/admin",
  "/support",
]);

export function isUuidSegment(segment: string): boolean {
  return UUID_RE.test(segment);
}

export function labelForSegment(
  segment: string,
  options?: { workspaceRoot?: string },
): string {
  if (
    options?.workspaceRoot === "host" &&
    HOST_SEGMENT_LABELS[segment]
  ) {
    return HOST_SEGMENT_LABELS[segment];
  }
  if (SEGMENT_LABELS[segment]) return SEGMENT_LABELS[segment];
  if (isUuidSegment(segment)) return "Details";
  return segment
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export type ResolvedLabel = {
  /** Path segment index that needs a dynamic title (event id, etc.) */
  index: number;
  kind: "event";
  id: string;
};

/**
 * Build breadcrumb items from a workspace pathname.
 * Dynamic UUID titles are filled later by the workspace breadcrumb component.
 */
export function buildPathBreadcrumbs(
  pathname: string,
  options: {
    homeLabel: string;
    homeHref: string;
  },
): { items: BreadcrumbItem[]; resolve: ResolvedLabel[] } {
  const { homeLabel, homeHref } = options;
  const clean = (pathname.split("?")[0]?.split("#")[0] ?? pathname).replace(
    /\/$/,
    "",
  ) || "/";
  const home = homeHref.replace(/\/$/, "") || "/";
  const parts = clean.split("/").filter(Boolean);
  const resolve: ResolvedLabel[] = [];

  // Exact workspace / role landing (e.g. `/host`, `/host/desk`, `/dashboard`).
  if (parts.length === 0 || clean === home) {
    if (OVERVIEW_HOME_HREFS.has(home)) {
      // Personal / Overview · Host: {name} / Overview
      return {
        items: [
          { label: homeLabel, href: homeHref },
          { label: "Overview" },
        ],
        resolve,
      };
    }
    // Role-specific landings (e.g. desk staff home `/host/desk`) stay a single chrome crumb.
    return { items: [{ label: homeLabel }], resolve };
  }

  const items: BreadcrumbItem[] = [
    {
      label: homeLabel,
      href: homeHref,
    },
  ];

  // Skip the workspace root segment (host|dashboard|admin|support) — home covers it.
  const workspaceRoot = parts[0];
  const rest = parts.slice(1);
  let href = `/${parts[0]}`;

  rest.forEach((segment, i) => {
    href = `${href}/${segment}`;
    const isLast = i === rest.length - 1;
    let label = labelForSegment(segment, { workspaceRoot });

    if (isUuidSegment(segment) && rest[i - 1] === "events") {
      resolve.push({ index: items.length, kind: "event", id: segment });
      label = "Event";
    }

    items.push({
      label,
      href: isLast ? undefined : href,
    });
  });

  if (rest.length === 0) {
    if (OVERVIEW_HOME_HREFS.has(home)) {
      return {
        items: [
          { label: homeLabel, href: homeHref },
          { label: "Overview" },
        ],
        resolve,
      };
    }
    return { items: [{ label: homeLabel }], resolve };
  }

  return { items, resolve };
}
