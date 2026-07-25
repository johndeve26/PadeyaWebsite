export type HostNavGroupId = "home" | "operate" | "grow" | "manage";

export type BuyerNavGroupId =
  | "home"
  | "activity"
  | "community"
  | "identity"
  | "earn"
  | "account";

export type AdminNavGroupId =
  | "platform"
  | "finance"
  | "moderation"
  | "content"
  | "system";

export type NavIconId = "users";

export type NavItem = {
  href: string;
  label: string;
  /** Show unread badge when set */
  badge?: "messages" | "notifications";
  /** Optional sidebar icon (rendered when the nav UI supports it). */
  icon?: NavIconId;
  /**
   * When set, the item is shown only if the user has any of these permissions
   * (or `admin.full_access` / super_admin via permission helpers).
   */
  permissions?: string[];
  /** Sidebar section — used when flattening grouped nav. */
  group?: HostNavGroupId | BuyerNavGroupId | AdminNavGroupId;
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

const HOST_GROUP_LABELS: Record<HostNavGroupId, string> = {
  home: "Home",
  operate: "Operate",
  grow: "Grow",
  manage: "Manage",
};

function hostNavItem(
  group: HostNavGroupId,
  item: Omit<NavItem, "group">,
): NavItem {
  return { ...item, group };
}

const BUYER_GROUP_LABELS: Record<BuyerNavGroupId, string> = {
  home: "Home",
  activity: "Activity",
  community: "Community",
  identity: "Identity",
  earn: "Earn",
  account: "Account",
};

function buyerNavItem(
  group: BuyerNavGroupId,
  item: Omit<NavItem, "group">,
): NavItem {
  return { ...item, group };
}

const ADMIN_GROUP_LABELS: Record<AdminNavGroupId, string> = {
  platform: "Platform",
  finance: "Finance",
  moderation: "Moderation",
  content: "Content",
  system: "System",
};

function adminNavItem(
  group: AdminNavGroupId,
  item: Omit<NavItem, "group">,
): NavItem {
  return { ...item, group };
}

/** Path aliases for nav active states (legacy redirects / canonical routes). */
const NAV_ACTIVE_ALIASES: Record<string, (pathname: string) => boolean> = {
  /** Canonical Fan Connect + legacy `/dashboard/connect` aliases. */
  "/connect": (pathname) =>
    pathname === "/connect" ||
    pathname.startsWith("/connect/") ||
    pathname === "/dashboard/connect" ||
    pathname.startsWith("/dashboard/connect/"),
  "/dashboard/connect": (pathname) =>
    pathname === "/connect" ||
    pathname.startsWith("/connect/") ||
    pathname === "/dashboard/connect" ||
    pathname.startsWith("/dashboard/connect/"),
  "/host": (pathname) =>
    pathname === "/host/dashboard" || pathname.startsWith("/host/dashboard/"),
  "/dashboard/help": (pathname) =>
    pathname === "/dashboard/help" ||
    pathname.startsWith("/dashboard/help/") ||
    pathname === "/help" ||
    pathname.startsWith("/help/"),
  "/host/help": (pathname) =>
    pathname === "/host/help" ||
    pathname.startsWith("/host/help/") ||
    pathname === "/help" ||
    pathname.startsWith("/help/"),
  "/admin/help": (pathname) =>
    pathname === "/admin/help" || pathname.startsWith("/admin/help/"),
  "/admin/knowledge-base": (pathname) =>
    pathname === "/admin/knowledge-base" ||
    pathname.startsWith("/admin/knowledge-base/"),
  "/host/support": (pathname) =>
    pathname === "/host/support" || pathname.startsWith("/host/support/"),
  "/dashboard/support": (pathname) =>
    pathname === "/dashboard/support" ||
    pathname.startsWith("/dashboard/support/"),
  "/admin/support": (pathname) =>
    pathname === "/admin/support" || pathname.startsWith("/admin/support/"),
  "/admin/ai": (pathname) =>
    pathname === "/admin/ai" || pathname.startsWith("/admin/ai/"),
  "/support/desk": (pathname) =>
    pathname === "/support/desk" || pathname.startsWith("/support/desk/"),
  /** Email settings specialist + runtime category hub. */
  "/admin/email/settings": (pathname) =>
    pathname === "/admin/email/settings" ||
    pathname.startsWith("/admin/email/settings/") ||
    pathname === "/admin/settings/runtime/email" ||
    pathname === "/admin/settings/email" ||
    pathname.startsWith("/admin/emails/settings"),
  /** Push settings specialist + runtime category hub. */
  "/admin/push/settings": (pathname) =>
    pathname === "/admin/push/settings" ||
    pathname.startsWith("/admin/push/settings/") ||
    pathname === "/admin/settings/runtime/push" ||
    pathname === "/admin/settings/push" ||
    pathname.startsWith("/admin/settings/push"),
  /** Runtime settings hub — exact only (category siblings are more specific). */
  "/admin/settings/runtime": (pathname) =>
    pathname === "/admin/settings/runtime" || pathname === "/admin/settings",
};

/**
 * Workspace overview roots — exact match (+ aliases) only.
 * Prevents `/host` Overview from staying active on every `/host/*` route
 * when homeHref is a desk-focused landing (e.g. `/host/desk`).
 */
const EXACT_MATCH_NAV_HREFS = new Set(["/dashboard", "/host", "/admin"]);

export function isNavItemActive(
  pathname: string,
  item: NavItem,
  homeHref: string | undefined,
  /** Full workspace nav — used so parents defer to more specific siblings. */
  siblings?: NavItem[],
): boolean {
  if (pathname === item.href) return true;

  const alias = NAV_ACTIVE_ALIASES[item.href];
  if (alias?.(pathname)) return true;

  // Overview / workspace home must not highlight for all nested routes.
  if (EXACT_MATCH_NAV_HREFS.has(item.href) || item.href === homeHref) {
    return false;
  }

  if (!pathname.startsWith(`${item.href}/`)) {
    return false;
  }

  // e.g. `/admin/settings/runtime` should highlight Runtime settings, not Settings.
  if (siblings?.length) {
    const moreSpecificSibling = siblings.some(
      (other) =>
        other.href !== item.href &&
        other.href.length > item.href.length &&
        other.href.startsWith(`${item.href}/`) &&
        (pathname === other.href || pathname.startsWith(`${other.href}/`)),
    );
    if (moreSpecificSibling) return false;
  }

  return true;
}

/**
 * Prefer the most specific (longest href) active item.
 * e.g. `/admin/users/[id]` → Users; `/admin/events/review` → Event review
 * (not the broader Events item).
 */
export function resolveActiveNavItem(
  pathname: string,
  items: NavItem[],
  homeHref: string | undefined,
): NavItem | undefined {
  let best: NavItem | undefined;
  for (const item of items) {
    if (!isNavItemActive(pathname, item, homeHref, items)) continue;
    if (!best || item.href.length > best.href.length) {
      best = item;
    }
  }
  return best;
}

/** Build grouped sidebar sections from flat host nav items. */
export function groupNavItems(items: NavItem[]): NavGroup[] {
  const order: HostNavGroupId[] = ["home", "operate", "grow", "manage"];
  return order
    .map((id) => ({
      label: HOST_GROUP_LABELS[id],
      items: items.filter((item) => item.group === id),
    }))
    .filter((group) => group.items.length > 0);
}

/** Build grouped sidebar sections from flat buyer nav items. */
export function groupBuyerNavItems(items: NavItem[]): NavGroup[] {
  const order: BuyerNavGroupId[] = [
    "home",
    "activity",
    "community",
    "identity",
    "earn",
    "account",
  ];
  return order
    .map((id) => ({
      label: BUYER_GROUP_LABELS[id],
      items: items.filter((item) => item.group === id),
    }))
    .filter((group) => group.items.length > 0);
}

export const buyerNav: NavItem[] = [
  buyerNavItem("home", { href: "/dashboard", label: "Overview" }),
  buyerNavItem("home", {
    href: "/dashboard/notifications",
    label: "Alerts",
    badge: "notifications",
  }),
  buyerNavItem("activity", { href: "/dashboard/tickets", label: "Tickets" }),
  buyerNavItem("activity", { href: "/dashboard/orders", label: "Orders" }),
  buyerNavItem("activity", {
    href: "/dashboard/merchandise",
    label: "Merch",
  }),
  buyerNavItem("activity", { href: "/dashboard/refunds", label: "Refunds" }),
  buyerNavItem("community", {
    href: "/dashboard/messages",
    label: "Messages",
    badge: "messages",
  }),
  buyerNavItem("community", {
    href: "/dashboard/team",
    label: "Workspaces",
  }),
  buyerNavItem("community", { href: "/connect", label: "Connect" }),
  buyerNavItem("community", {
    href: "/dashboard/following",
    label: "Following",
  }),
  buyerNavItem("community", {
    href: "/dashboard/hosts-for-you",
    label: "Hosts for you",
  }),
  buyerNavItem("community", {
    href: "/dashboard/events-for-you",
    label: "Events for you",
  }),
  buyerNavItem("identity", { href: "/dashboard/passport", label: "Passport" }),
  buyerNavItem("identity", { href: "/dashboard/badges", label: "Badges" }),
  buyerNavItem("identity", { href: "/dashboard/vault", label: "Vault" }),
  buyerNavItem("identity", { href: "/dashboard/reviews", label: "Reviews" }),
  buyerNavItem("earn", {
    href: "/dashboard/ambassador",
    label: "Ambassadors",
  }),
  buyerNavItem("account", { href: "/dashboard/help", label: "Help" }),
  buyerNavItem("account", { href: "/dashboard/support", label: "Support" }),
  buyerNavItem("account", { href: "/dashboard/settings", label: "Settings" }),
];

/** Grouped buyer sidebar for desktop + mobile drawer. */
export const buyerNavGroups: NavGroup[] = groupBuyerNavItems(buyerNav);

/**
 * Flat host nav — labels disambiguate from Personal (`buyerNav`).
 * Sidebar title comes from shell: `Host: {display_name}` (not these item labels).
 * Hrefs stay under `/host/*`; do not rename paths here.
 * Payouts/promos stay off primary nav (deep links only).
 *
 * Groups: Home · Operate · Grow · Manage
 * Disambiguated vs Personal: Merch Studio, Host Inbox, Ambassador Campaigns,
 * Audience CRM, Vault Studio, Host Team, Host Settings, Tickets & Entry.
 */
export const hostNav: NavItem[] = [
  hostNavItem("home", { href: "/host", label: "Overview" }),
  hostNavItem("home", {
    href: "/host/notifications",
    label: "Alerts",
    badge: "notifications",
  }),
  hostNavItem("home", { href: "/host/roadmap", label: "Roadmap" }),
  hostNavItem("operate", { href: "/host/events", label: "Events" }),
  hostNavItem("operate", { href: "/host/desk", label: "Tickets & Entry" }),
  hostNavItem("operate", { href: "/host/merchandise", label: "Merch Studio" }),
  hostNavItem("operate", {
    href: "/host/messages",
    label: "Host Inbox",
    badge: "messages",
  }),
  hostNavItem("grow", {
    href: "/host/ambassadors",
    label: "Ambassador Campaigns",
  }),
  hostNavItem("grow", { href: "/host/sponsorships", label: "Sponsorships" }),
  hostNavItem("grow", { href: "/host/audience", label: "Audience CRM" }),
  hostNavItem("grow", { href: "/host/legacy", label: "Legacy Page" }),
  hostNavItem("grow", { href: "/host/vault", label: "Vault Studio" }),
  hostNavItem("manage", { href: "/host/analytics", label: "Analytics" }),
  hostNavItem("manage", { href: "/host/earnings", label: "Earnings" }),
  hostNavItem("manage", { href: "/host/team", label: "Host Team" }),
  hostNavItem("manage", { href: "/host/settings", label: "Host Settings" }),
  hostNavItem("manage", { href: "/host/help", label: "Help" }),
  hostNavItem("manage", { href: "/host/support", label: "Support" }),
];

/** Grouped host sidebar for desktop + mobile drawer. */
export const hostNavGroups: NavGroup[] = groupNavItems(hostNav);

export function flattenNavGroups(groups: NavGroup[]): NavItem[] {
  return groups.flatMap((group) => group.items);
}

/** Build grouped sidebar sections from flat admin nav items. */
export function groupAdminNavItems(items: NavItem[]): NavGroup[] {
  const order: AdminNavGroupId[] = [
    "platform",
    "finance",
    "moderation",
    "content",
    "system",
  ];
  return order
    .map((id) => ({
      label: ADMIN_GROUP_LABELS[id],
      items: items.filter((item) => item.group === id),
    }))
    .filter((group) => group.items.length > 0);
}

/**
 * Admin sidebar — Platform group matches product IA; other groups keep
 * existing admin tools discoverable without a flat dump.
 *
 * Platform order: Overview → Users → commerce → growth → settings.
 * Nested `/admin/users/*` keeps Users highlighted (see `isNavItemActive`).
 * Desktop + mobile drawer share this grouped vertical list (no horizontal strip).
 */
export const adminNav: NavItem[] = [
  adminNavItem("platform", { href: "/admin", label: "Overview" }),
  adminNavItem("platform", {
    href: "/admin/users",
    label: "Users",
    icon: "users",
    permissions: ["admin.users.view"],
  }),
  adminNavItem("platform", { href: "/admin/hosts", label: "Hosts" }),
  adminNavItem("platform", { href: "/admin/events", label: "Events" }),
  adminNavItem("platform", { href: "/admin/orders", label: "Orders" }),
  adminNavItem("platform", { href: "/admin/tickets", label: "Tickets" }),
  adminNavItem("platform", { href: "/admin/merchandise", label: "Merch" }),
  adminNavItem("platform", { href: "/admin/ambassadors", label: "Ambassadors" }),
  adminNavItem("platform", {
    href: "/admin/sponsorships",
    label: "Sponsorships",
  }),
  adminNavItem("platform", {
    href: "/admin/sponsors",
    label: "Sponsor profiles",
    permissions: ["admin.sponsors.view"],
  }),
  adminNavItem("platform", {
    href: "/admin/message-reports",
    label: "Reports",
  }),

  adminNavItem("finance", {
    href: "/admin/finance",
    label: "Overview",
    permissions: [
      "admin.finance.view_fees",
      "admin.finance.manage_fees",
      "payments.view",
      "payouts.review",
      "admin.full_access",
    ],
  }),
  adminNavItem("finance", {
    href: "/admin/finance/fees",
    label: "Fees",
    permissions: [
      "admin.finance.view_fees",
      "admin.finance.manage_fees",
      "admin.full_access",
    ],
  }),
  adminNavItem("finance", {
    href: "/admin/finance/host-overrides",
    label: "Host fee overrides",
    permissions: [
      "admin.finance.view_fees",
      "admin.finance.manage_host_overrides",
      "admin.full_access",
    ],
  }),
  adminNavItem("finance", {
    href: "/admin/finance/earnings",
    label: "Earnings",
    permissions: [
      "payments.view",
      "payouts.review",
      "admin.finance.view_fees",
      "admin.full_access",
    ],
  }),
  adminNavItem("finance", {
    href: "/admin/finance/platform-revenue",
    label: "Platform revenue",
    permissions: [
      "admin.finance.view_fees",
      "admin.finance.export_event_sales",
      "payouts.review",
      "admin.full_access",
    ],
  }),
  adminNavItem("finance", { href: "/admin/payouts", label: "Payouts" }),
  adminNavItem("finance", { href: "/admin/refunds", label: "Refunds" }),
  adminNavItem("finance", { href: "/admin/payments", label: "Payments" }),
  adminNavItem("finance", { href: "/admin/ledger", label: "Ledger" }),
  adminNavItem("finance", { href: "/admin/analytics", label: "Analytics" }),

  adminNavItem("moderation", {
    href: "/admin/events/review",
    label: "Event review",
  }),
  adminNavItem("moderation", {
    href: "/admin/support",
    label: "Support",
    permissions: ["admin.support.view", "admin.full_access"],
  }),
  adminNavItem("moderation", {
    href: "/admin/appeals",
    label: "Appeals",
    permissions: ["admin.appeals.review", "admin.users.suspend"],
  }),
  adminNavItem("moderation", {
    href: "/admin/fan-connect",
    label: "Connect",
  }),
  adminNavItem("moderation", { href: "/admin/fans", label: "Fan Passports" }),
  adminNavItem("moderation", { href: "/admin/vault", label: "Vault" }),
  adminNavItem("moderation", { href: "/admin/reviews", label: "Reviews" }),

  adminNavItem("content", {
    href: "/admin/knowledge-base",
    label: "Knowledge Base",
    permissions: [
      "admin.knowledge_base.view",
      "admin.knowledge_base.create",
      "admin.knowledge_base.edit",
      "admin.knowledge_base.publish",
      "admin.full_access",
    ],
  }),
  adminNavItem("content", {
    href: "/admin/blog",
    label: "Blog",
    permissions: [
      "admin.blog.view",
      "admin.blog.create",
      "admin.blog.edit",
      "admin.blog.publish",
      "admin.full_access",
    ],
  }),
  adminNavItem("content", { href: "/admin/help", label: "Help Center" }),
  adminNavItem("content", { href: "/admin/cms", label: "CMS" }),
  adminNavItem("content", { href: "/admin/emails", label: "Emails" }),

  adminNavItem("system", {
    href: "/admin/notifications",
    label: "Notifications",
    permissions: [
      "admin.notifications.view",
      "admin.notifications.manage_settings",
      "admin.notifications.send_custom",
      "admin.full_access",
    ],
  }),
  adminNavItem("system", {
    href: "/admin/notifications/settings",
    label: "Notification settings",
    permissions: [
      "admin.notifications.manage_settings",
      "admin.notifications.view",
      "admin.full_access",
    ],
  }),
  adminNavItem("system", {
    href: "/admin/team",
    label: "Team",
    icon: "users",
    permissions: ["admin.team.view", "admin.full_access"],
  }),
  // Distinct integration settings (System group)
  adminNavItem("system", {
    href: "/admin/platform",
    label: "Platform ops",
    permissions: [
      "admin.platform.view_readiness",
      "admin.maintenance.view",
      "admin.full_access",
    ],
  }),
  adminNavItem("system", {
    href: "/admin/platform/maintenance",
    label: "Maintenance",
    permissions: [
      "admin.maintenance.view",
      "admin.maintenance.manage",
      "admin.full_access",
    ],
  }),
  adminNavItem("system", {
    href: "/admin/platform/go-live",
    label: "Go live",
    permissions: ["admin.platform.view_readiness", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/settings/runtime",
    label: "Runtime overview",
    permissions: ["admin.settings.view", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/email/settings",
    label: "Email",
    permissions: ["admin.settings.view", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/push/settings",
    label: "Push",
    permissions: ["admin.settings.view", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/ai",
    label: "Pàdéyá AI",
    permissions: [
      "admin.ai.view",
      "admin.ai.manage_settings",
      "admin.ai.view_usage",
      "admin.full_access",
    ],
  }),
  adminNavItem("system", {
    href: "/admin/settings/runtime/ai",
    label: "AI (runtime)",
    permissions: ["admin.settings.view", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/settings/runtime/payments",
    label: "Payment integration",
    permissions: ["admin.settings.view", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/settings/runtime/storage",
    label: "Storage",
    permissions: ["admin.settings.view", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/settings/runtime/integrations",
    label: "Integrations",
    permissions: ["admin.settings.view", "admin.full_access"],
  }),
  adminNavItem("system", {
    href: "/admin/ai/features",
    label: "Feature toggles",
    permissions: [
      "admin.ai.view",
      "admin.ai.manage_features",
      "admin.settings.view",
      "admin.full_access",
    ],
  }),
  adminNavItem("system", {
    href: "/admin/settings/runtime/system-status",
    label: "System status",
    permissions: [
      "admin.settings.view_system_status",
      "admin.settings.view",
      "admin.full_access",
    ],
  }),
  adminNavItem("system", {
    href: "/admin/settings/runtime/audit",
    label: "Settings audit",
    permissions: ["admin.settings.view_audit", "admin.full_access"],
  }),
  adminNavItem("system", { href: "/admin/audit-logs", label: "Audit" }),
];

/** Grouped admin sidebar for desktop + mobile drawer. */
export const adminNavGroups: NavGroup[] = groupAdminNavItems(adminNav);

export const supportNav: NavItem[] = [
  { href: "/support/desk", label: "Inbox" },
  { href: "/support/cases", label: "Cases" },
  { href: "/support/refunds", label: "Refunds" },
];
