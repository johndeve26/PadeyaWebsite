"use client";

import Link from "next/link";
import { useMemo } from "react";
import { usePathname } from "next/navigation";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { useUnreadMessages } from "@/hooks/useUnreadMessages";
import { useUnreadNotifications } from "@/hooks/useUnreadNotifications";
import { cn } from "@/lib/cn";
import {
  hostMobileNavItems,
  resolveHostHomeHref,
} from "@/lib/nav/host-mobile-nav";

export function HostWorkspaceMobileBottomNav({ homeHref }: { homeHref: string }) {
  const pathname = usePathname();
  const { active } = useHostWorkspace();
  const messagesUnread = useUnreadMessages();
  const notificationsUnread = useUnreadNotifications();

  const onLiveScanner =
    pathname.includes("/check-in") && !pathname.includes("offline-check-in");

  const items = useMemo(() => {
    const resolvedHome = homeHref || resolveHostHomeHref(active);
    return hostMobileNavItems(active, resolvedHome);
  }, [active, homeHref]);

  if (onLiveScanner || items.length < 2) return null;

  const colClass =
    items.length === 3 ? "grid-cols-3" : items.length === 2 ? "grid-cols-2" : "grid-cols-4";

  return (
    <>
      <div
        aria-hidden
        className="h-[calc(3.5rem+env(safe-area-inset-bottom))] md:hidden"
      />
      <nav
        aria-label="Host workspace mobile navigation"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      >
        <ul className={cn("mx-auto grid max-w-lg", colClass)}>
          {items.map((item) => {
            const activeTab = item.match(pathname, homeHref);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex min-h-14 flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-semibold transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                    activeTab ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  <span
                    className={cn(
                      "h-1 w-6 rounded-full transition-colors",
                      activeTab ? "bg-primary" : "bg-transparent",
                    )}
                    aria-hidden
                  />
                  <span className="inline-flex items-center gap-1 truncate">
                    {item.label}
                    {item.badge === "messages" && messagesUnread > 0 ? (
                      <span className="inline-flex min-w-4 justify-center rounded-full bg-primary px-1 text-[9px] font-extrabold text-primary-foreground">
                        {messagesUnread > 9 ? "9+" : messagesUnread}
                      </span>
                    ) : null}
                    {item.badge === "notifications" && notificationsUnread > 0 ? (
                      <span className="inline-flex min-w-4 justify-center rounded-full bg-primary px-1 text-[9px] font-extrabold text-primary-foreground">
                        {notificationsUnread > 9 ? "9+" : notificationsUnread}
                      </span>
                    ) : null}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
