"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ScrollHintNav } from "@/components/ui/ScrollHintNav";
import { cn } from "@/lib/cn";

const HOST_LINKS: { suffix: string; label: string }[] = [
  { suffix: "", label: "Overview" },
  { suffix: "/tickets", label: "Tickets" },
  { suffix: "/merchandise", label: "Merch Studio" },
  { suffix: "/ambassadors", label: "Ambassador Campaigns" },
  { suffix: "/analytics", label: "Analytics" },
  { suffix: "/check-in", label: "Check-in" },
  { suffix: "/attendees", label: "Attendees" },
  { suffix: "/memory", label: "Memory" },
  { suffix: "/edit", label: "Studio" },
];

const ADMIN_LINKS: { suffix: string; label: string }[] = [
  { suffix: "/buyers", label: "Buyers" },
  { suffix: "/attendees", label: "Attendees" },
  { suffix: "/exports", label: "Exports" },
  { suffix: "/analytics", label: "Analytics" },
];

export function EventOpsNav({
  eventId,
  base = "host",
}: {
  eventId: string;
  base?: "host" | "admin";
}) {
  const pathname = usePathname() || "";
  const root =
    base === "admin"
      ? `/admin/events/${eventId}`
      : `/host/events/${eventId}`;
  const links = base === "admin" ? ADMIN_LINKS : HOST_LINKS;

  return (
    <ScrollHintNav
      aria-label="Event operations"
      scrollClassName="flex min-w-0 gap-1"
    >
      {links.map((link) => {
        const href = `${root}${link.suffix}`;
        const active =
          link.suffix === ""
            ? pathname === root || pathname === `${root}/`
            : pathname.startsWith(href);
        if (active) {
          return (
            <span
              key={link.suffix || "overview"}
              aria-current="page"
              className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-xs font-bold text-paper"
            >
              {link.label}
            </span>
          );
        }
        return (
          <Link
            key={link.suffix || "overview"}
            href={href}
            className={cn(
              "shrink-0 rounded-full px-3 py-1.5 text-xs font-bold text-muted-foreground transition-colors",
              "hover:bg-surface-muted hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </ScrollHintNav>
  );
}
