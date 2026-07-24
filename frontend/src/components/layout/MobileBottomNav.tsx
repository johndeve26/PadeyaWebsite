"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { useUnreadMessages } from "@/hooks/useUnreadMessages";
import { useUnreadNotifications } from "@/hooks/useUnreadNotifications";
import { userHasRole } from "@/lib/auth/permissions";
import { cn } from "@/lib/cn";

const personalItems = [
  { href: "/dashboard", label: "Home", match: (p: string) => p === "/dashboard" },
  {
    href: "/dashboard/notifications",
    label: "Alerts",
    match: (p: string) => p.startsWith("/dashboard/notifications"),
    badge: "notifications" as const,
  },
  {
    href: "/dashboard/messages",
    label: "Messages",
    match: (p: string) => p.startsWith("/dashboard/messages"),
    badge: "messages" as const,
  },
  {
    href: "/events",
    label: "Events",
    match: (p: string) => p.startsWith("/events"),
  },
];

export function MobileBottomNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const messagesUnread = useUnreadMessages();
  const notificationsUnread = useUnreadNotifications();

  const onPersonalSurface =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/connect") ||
    pathname === "/events" ||
    pathname === "/hosts";

  const isHostSurface =
    pathname.startsWith("/host") || pathname.startsWith("/staff");

  if (!user || isHostSurface || !onPersonalSurface) return null;
  if (userHasRole(user, "host", "host_staff") && pathname.startsWith("/host")) {
    return null;
  }

  return (
    <>
      {/* Spacer so page content clears the fixed bar (only when nav is shown) */}
      <div
        aria-hidden
        className="h-[calc(3.5rem+env(safe-area-inset-bottom))] md:hidden"
      />
      <nav
        aria-label="Personal mobile navigation"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      >
        <ul className="mx-auto grid max-w-lg grid-cols-4">
          {personalItems.map((item) => {
            const active = item.match(pathname);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex min-h-14 flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-semibold transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                    active ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  <span
                    className={cn(
                      "h-1 w-6 rounded-full transition-colors",
                      active ? "bg-primary" : "bg-transparent",
                    )}
                    aria-hidden
                  />
                  <span className="inline-flex items-center gap-1 truncate">
                    {item.label}
                    {"badge" in item &&
                    item.badge === "messages" &&
                    messagesUnread > 0 ? (
                      <span className="inline-flex min-w-4 justify-center rounded-full bg-primary px-1 text-[9px] font-extrabold text-primary-foreground">
                        {messagesUnread > 9 ? "9+" : messagesUnread}
                      </span>
                    ) : null}
                    {"badge" in item &&
                    item.badge === "notifications" &&
                    notificationsUnread > 0 ? (
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
