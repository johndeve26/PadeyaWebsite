import type {
  HostTeamPermissionKey,
  HostTeamPermissions,
} from "@/lib/types/lifecycle";

export const TEAM_ROLE_OPTIONS = [
  {
    value: "admin",
    label: "Admin — broad host management (no payout/bank or mark-paid by default)",
  },
  {
    value: "event_manager",
    label: "Event Manager — events, tickets, Ambassadors view",
  },
  {
    value: "ambassador_manager",
    label: "Ambassador Manager — campaigns, approvals (mark-paid optional)",
  },
  {
    value: "finance_manager",
    label: "Finance Manager — sales, payouts, mark Ambassador rewards paid",
  },
  {
    value: "scanner",
    label: "Scanner Staff — ticket QR / check-in (per-event by default)",
  },
  {
    value: "merch_staff",
    label: "Merch Staff — pickup QR / queue (per-event by default)",
  },
  {
    value: "support_staff",
    label: "Support Staff — buyer/attendee messages",
  },
  {
    value: "sponsor_manager",
    label: "Sponsor Manager — inquiries & slots",
  },
  {
    value: "viewer",
    label: "Viewer — read-only assigned areas",
  },
] as const;

export const PERMISSION_KEYS: HostTeamPermissionKey[] = [
  "events.view",
  "events.create",
  "events.edit",
  "events.publish",
  "events.cancel",
  "events.archive",
  "tickets.view",
  "tickets.scan_qr",
  "tickets.check_in",
  "tickets.manage_pricing",
  "tickets.manage_capacity",
  "tickets.export_attendees",
  "tickets.view_refunds",
  "merch.view",
  "merch.create",
  "merch.edit",
  "merch.manage_inventory",
  "merch.scan_pickup_qr",
  "merch.mark_picked_up",
  "merch.fulfill_orders",
  "merch.manage_shipping",
  "merch.manage_discounts",
  "merch.manage_bundles",
  "messages.view",
  "messages.reply",
  "messages.manage_templates",
  "messages.report_or_escalate",
  "sponsors.view",
  "sponsors.reply",
  "sponsors.manage_slots",
  "sponsors.accept_or_reject",
  "analytics.view_events",
  "analytics.view_merch",
  "analytics.view_sponsors",
  "analytics.export",
  "team.view",
  "team.invite",
  "team.edit_permissions",
  "team.remove_members",
  "finance.view_sales_summary",
  "finance.view_payouts",
  "finance.manage_payouts",
  "finance.manage_payout_settings",
  "ambassadors.view",
  "ambassadors.create_campaigns",
  "ambassadors.edit_campaigns",
  "ambassadors.pause_campaigns",
  "ambassadors.remove_participants",
  "ambassadors.view_conversions",
  "ambassadors.view_payouts",
  "ambassadors.approve_rewards",
  "ambassadors.reject_rewards",
  "ambassadors.mark_rewards_paid",
  "ambassadors.reverse_rewards",
  "ambassadors.export",
];

export const EMPTY_TEAM_PERMISSIONS: HostTeamPermissions = Object.fromEntries(
  PERMISSION_KEYS.map((k) => [k, false]),
) as HostTeamPermissions;

function enable(
  ...keys: HostTeamPermissionKey[]
): HostTeamPermissions {
  const next = { ...EMPTY_TEAM_PERMISSIONS };
  for (const key of keys) next[key] = true;
  return next;
}

const ALL_EVENTS: HostTeamPermissionKey[] = [
  "events.view",
  "events.create",
  "events.edit",
  "events.publish",
  "events.cancel",
  "events.archive",
];
const ALL_TICKETS_NO_DESK: HostTeamPermissionKey[] = [
  "tickets.view",
  "tickets.manage_pricing",
  "tickets.manage_capacity",
  "tickets.export_attendees",
  "tickets.view_refunds",
];
const ALL_MERCH_NO_DESK: HostTeamPermissionKey[] = [
  "merch.view",
  "merch.create",
  "merch.edit",
  "merch.manage_inventory",
  "merch.manage_shipping",
  "merch.manage_discounts",
  "merch.manage_bundles",
];
const ALL_MESSAGES: HostTeamPermissionKey[] = [
  "messages.view",
  "messages.reply",
  "messages.manage_templates",
  "messages.report_or_escalate",
];
const ALL_SPONSORS: HostTeamPermissionKey[] = [
  "sponsors.view",
  "sponsors.reply",
  "sponsors.manage_slots",
  "sponsors.accept_or_reject",
];
const ALL_ANALYTICS: HostTeamPermissionKey[] = [
  "analytics.view_events",
  "analytics.view_merch",
  "analytics.view_sponsors",
  "analytics.export",
];
const ALL_TEAM: HostTeamPermissionKey[] = [
  "team.view",
  "team.invite",
  "team.edit_permissions",
  "team.remove_members",
];
const AMBASSADOR_CAMPAIGN_OPS: HostTeamPermissionKey[] = [
  "ambassadors.view",
  "ambassadors.create_campaigns",
  "ambassadors.edit_campaigns",
  "ambassadors.pause_campaigns",
  "ambassadors.remove_participants",
  "ambassadors.view_conversions",
];

export const ROLE_PERMISSION_DEFAULTS: Record<string, HostTeamPermissions> = {
  // Safer: no desk scan, no payout/bank, no mark-paid/export; approve/reject/reverse on.
  admin: enable(
    ...ALL_EVENTS,
    ...ALL_TICKETS_NO_DESK,
    ...ALL_MERCH_NO_DESK,
    ...ALL_MESSAGES,
    ...ALL_SPONSORS,
    ...ALL_ANALYTICS,
    ...ALL_TEAM,
    ...AMBASSADOR_CAMPAIGN_OPS,
    "ambassadors.approve_rewards",
    "ambassadors.reject_rewards",
    "ambassadors.reverse_rewards",
    "finance.view_sales_summary",
  ),
  event_manager: enable(
    ...ALL_EVENTS,
    ...ALL_TICKETS_NO_DESK,
    "analytics.view_events",
    "ambassadors.view",
    "ambassadors.view_conversions",
  ),
  ambassador_manager: enable(
    ...AMBASSADOR_CAMPAIGN_OPS,
    "ambassadors.view_payouts",
    "ambassadors.approve_rewards",
    "ambassadors.reject_rewards",
    "ambassadors.reverse_rewards",
  ),
  finance_manager: enable(
    "finance.view_sales_summary",
    "finance.view_payouts",
    "finance.manage_payouts",
    "ambassadors.view_payouts",
    "ambassadors.mark_rewards_paid",
  ),
  scanner: enable("events.view", "tickets.view"),
  merch_staff: enable("events.view", "merch.view"),
  support_staff: enable("events.view", "tickets.view", ...ALL_MESSAGES),
  sponsor_manager: enable(...ALL_SPONSORS, "analytics.view_sponsors"),
  // ambassadors.view only if host grants it
  viewer: enable(
    "events.view",
    "tickets.view",
    "merch.view",
    "messages.view",
    "sponsors.view",
    "analytics.view_events",
    "team.view",
    "finance.view_sales_summary",
  ),
};

export const OWNER_ONLY_PERMISSION_KEYS: HostTeamPermissionKey[] = [
  "finance.manage_payout_settings",
];

export const PERMISSION_GROUPS: {
  title: string;
  hint?: string;
  keys: { key: HostTeamPermissionKey; label: string }[];
}[] = [
  {
    title: "Events",
    keys: [
      { key: "events.view", label: "View events" },
      { key: "events.create", label: "Create events" },
      { key: "events.edit", label: "Edit events" },
      { key: "events.publish", label: "Publish events" },
      { key: "events.cancel", label: "Cancel events" },
      { key: "events.archive", label: "Archive events" },
    ],
  },
  {
    title: "Tickets",
    hint: "Host-wide scan/check-in is off for scanner staff by default — assign per event.",
    keys: [
      { key: "tickets.view", label: "View tickets / order context" },
      { key: "tickets.scan_qr", label: "Scan ticket QR (all events)" },
      { key: "tickets.check_in", label: "Check in attendees (all events)" },
      { key: "tickets.manage_pricing", label: "Manage pricing" },
      { key: "tickets.manage_capacity", label: "Manage capacity" },
      { key: "tickets.export_attendees", label: "Export attendees" },
      { key: "tickets.view_refunds", label: "View refunds" },
    ],
  },
  {
    title: "Merch",
    hint: "Host-wide pickup scan is off for merch staff by default — assign per event.",
    keys: [
      { key: "merch.view", label: "View merch / pickup queue" },
      { key: "merch.create", label: "Create merch" },
      { key: "merch.edit", label: "Edit merch" },
      { key: "merch.manage_inventory", label: "Manage inventory" },
      { key: "merch.scan_pickup_qr", label: "Scan pickup QR (all events)" },
      { key: "merch.mark_picked_up", label: "Mark picked up (all events)" },
      { key: "merch.fulfill_orders", label: "Fulfill merch orders (all events)" },
      { key: "merch.manage_shipping", label: "Manage shipping" },
      { key: "merch.manage_discounts", label: "Manage discounts" },
      { key: "merch.manage_bundles", label: "Manage bundles" },
    ],
  },
  {
    title: "Ambassadors",
    hint: "Reward and payout permissions allow this team member to approve or mark Ambassador rewards paid for your campaigns.",
    keys: [
      { key: "ambassadors.view", label: "View Ambassadors" },
      { key: "ambassadors.create_campaigns", label: "Create campaigns" },
      { key: "ambassadors.edit_campaigns", label: "Edit campaigns" },
      { key: "ambassadors.pause_campaigns", label: "Pause / end campaigns" },
      { key: "ambassadors.remove_participants", label: "Remove participants" },
      { key: "ambassadors.view_conversions", label: "View conversions" },
      { key: "ambassadors.view_payouts", label: "View Ambassador payouts" },
      { key: "ambassadors.approve_rewards", label: "Approve / reject rewards" },
      { key: "ambassadors.reject_rewards", label: "Reject rewards only" },
      { key: "ambassadors.mark_rewards_paid", label: "Mark rewards paid" },
      { key: "ambassadors.reverse_rewards", label: "Reverse rewards" },
      { key: "ambassadors.export", label: "Export conversions / payouts" },
    ],
  },
  {
    title: "Messages",
    keys: [
      { key: "messages.view", label: "View messages" },
      { key: "messages.reply", label: "Reply to messages" },
      { key: "messages.manage_templates", label: "Manage templates" },
      { key: "messages.report_or_escalate", label: "Report or escalate" },
    ],
  },
  {
    title: "Sponsors",
    keys: [
      { key: "sponsors.view", label: "View sponsor inquiries" },
      { key: "sponsors.reply", label: "Reply to sponsors" },
      { key: "sponsors.manage_slots", label: "Manage slots" },
      { key: "sponsors.accept_or_reject", label: "Accept or reject" },
    ],
  },
  {
    title: "Analytics",
    keys: [
      { key: "analytics.view_events", label: "View event analytics" },
      { key: "analytics.view_merch", label: "View merch analytics" },
      { key: "analytics.view_sponsors", label: "View sponsor analytics" },
      { key: "analytics.export", label: "Export analytics" },
    ],
  },
  {
    title: "Team",
    keys: [
      { key: "team.view", label: "View team" },
      { key: "team.invite", label: "Invite members" },
      { key: "team.edit_permissions", label: "Edit permissions" },
      { key: "team.remove_members", label: "Suspend / remove members" },
    ],
  },
  {
    title: "Finance",
    hint: "finance.manage_payout_settings is owner-only unless explicitly granted. manage_payouts can also mark Ambassador rewards paid.",
    keys: [
      { key: "finance.view_sales_summary", label: "View sales summary" },
      { key: "finance.view_payouts", label: "View payouts" },
      { key: "finance.manage_payouts", label: "Manage payouts" },
      {
        key: "finance.manage_payout_settings",
        label: "Manage payout settings (owner grant)",
      },
    ],
  },
];

export function permissionsForRole(role: string): HostTeamPermissions {
  return {
    ...(ROLE_PERMISSION_DEFAULTS[role] ?? ROLE_PERMISSION_DEFAULTS.scanner),
  };
}

export function mergePermissions(
  base: Partial<HostTeamPermissions> | null | undefined,
): HostTeamPermissions {
  return { ...EMPTY_TEAM_PERMISSIONS, ...base };
}

export type TeamScope = "host_wide" | "selected_events";

export const SCOPE_OPTIONS: { value: TeamScope; label: string; hint: string }[] =
  [
    {
      value: "host_wide",
      label: "Host-wide",
      hint: "Permissions apply across the full host workspace.",
    },
    {
      value: "selected_events",
      label: "Selected events",
      hint: "Permissions apply only to chosen events (and event staff assignments).",
    },
  ];

/** Recommended default scope per role preset. */
export const ROLE_DEFAULT_SCOPES: Record<string, TeamScope> = {
  admin: "host_wide",
  event_manager: "host_wide",
  ambassador_manager: "host_wide",
  finance_manager: "host_wide",
  scanner: "selected_events",
  merch_staff: "selected_events",
  support_staff: "host_wide",
  sponsor_manager: "host_wide",
  viewer: "selected_events",
};

export function defaultScopeForRole(role: string): TeamScope {
  return ROLE_DEFAULT_SCOPES[role] ?? "selected_events";
}
