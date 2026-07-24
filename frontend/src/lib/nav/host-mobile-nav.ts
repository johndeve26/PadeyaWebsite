import { hostHomePathForWorkspace } from "@/lib/host-access";
import { canSeeNavHref } from "@/lib/nav/host-nav";
import { isNavItemActive } from "@/lib/nav/workspace";
import type { HostWorkspace } from "@/lib/types/host-workspace";

export type HostMobileNavItem = {
  href: string;
  label: string;
  match: (pathname: string, homeHref: string) => boolean;
  badge?: "messages" | "notifications";
};

const HOST_MOBILE_NAV: Omit<HostMobileNavItem, "match">[] = [
  { href: "__home__", label: "Home" },
  { href: "/host/notifications", label: "Alerts", badge: "notifications" },
  { href: "/host/messages", label: "Inbox", badge: "messages" },
  { href: "/host/events", label: "Events" },
];

export function hostMobileNavItems(
  workspace: HostWorkspace | null,
  homeHref: string,
): HostMobileNavItem[] {
  const items: HostMobileNavItem[] = HOST_MOBILE_NAV.map((item) => {
    const href = item.href === "__home__" ? homeHref : item.href;
    return {
      ...item,
      href,
      match: (pathname, home) => {
        if (item.href === "__home__") {
          return isNavItemActive(pathname, { href: home, label: "Home" }, home);
        }
        if (item.href === "/host/events") {
          return (
            pathname.startsWith("/host/events") ||
            pathname.startsWith("/host/desk")
          );
        }
        return isNavItemActive(
          pathname,
          { href: item.href, label: item.label },
          home,
        );
      },
    };
  });

  if (!workspace) return items;

  return items.filter((item) => {
    if (item.href === homeHref) return true;
    if (item.href === "/host/notifications") return true;
    return canSeeNavHref(workspace, item.href);
  });
}

export function resolveHostHomeHref(workspace: HostWorkspace | null): string {
  if (workspace) return hostHomePathForWorkspace(workspace);
  return "/host";
}
