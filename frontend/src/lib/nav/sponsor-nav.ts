import type { NavGroup } from "@/lib/nav/workspace";

export const SPONSOR_WORKSPACE_SWITCHER_LABEL = "Sponsor workspace";

export function sponsorNavGroups(): NavGroup[] {
  return [
    {
      label: "Home",
      items: [
        { href: "/sponsor", label: "Overview" },
        { href: "/sponsor/opportunities", label: "Opportunities" },
        { href: "/sponsor/saved", label: "Saved" },
      ],
    },
    {
      label: "Manage",
      items: [
        { href: "/sponsor/profile", label: "Sponsor profile" },
        { href: "/sponsor/campaigns", label: "Campaigns" },
        { href: "/sponsor/inquiries", label: "Inquiries" },
        { href: "/sponsor/deals", label: "Deals" },
        { href: "/sponsor/reports", label: "Reports" },
        { href: "/sponsor/settings", label: "Settings" },
        { href: "/sponsor/settings/team", label: "Team" },
      ],
    },
  ];
}

export function flatSponsorNav() {
  return sponsorNavGroups().flatMap((g) => g.items);
}

export function userHasSponsorWorkspace(
  workspaces: { sponsor_id: string }[] | null | undefined,
): boolean {
  return Boolean(workspaces && workspaces.length > 0);
}
