"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ScrollHintNav } from "@/components/ui/ScrollHintNav";
import { cn } from "@/lib/cn";
import type { EventStatus } from "@/lib/types/events";

const HOST_LINKS: { suffix: string; label: string }[] = [
  { suffix: "", label: "Overview" },
  { suffix: "/tickets", label: "Tickets" },
  { suffix: "/merchandise", label: "Merch Studio" },
  { suffix: "/ambassadors", label: "Ambassador Campaigns" },
  { suffix: "/analytics", label: "Analytics" },
  { suffix: "/check-in", label: "Check-in" },
  { suffix: "/attendees", label: "Attendees" },
  { suffix: "/memory", label: "Memories" },
  { suffix: "/edit", label: "Studio" },
];

const ADMIN_LINKS: { suffix: string; label: string }[] = [
  { suffix: "/buyers", label: "Buyers" },
  { suffix: "/attendees", label: "Attendees" },
  { suffix: "/exports", label: "Exports" },
  { suffix: "/analytics", label: "Analytics" },
];

function hostLinksForStatus(status?: EventStatus) {
  if (status !== "completed") return HOST_LINKS;
  // After completion, Memories sits next to Overview as the main post-night surface.
  const memories = HOST_LINKS.find((l) => l.suffix === "/memory");
  if (!memories) return HOST_LINKS;
  return [
    HOST_LINKS[0],
    memories,
    ...HOST_LINKS.filter((l) => l.suffix !== "" && l.suffix !== "/memory"),
  ];
}

export function EventOpsNav({
  eventId,
  base = "host",
  eventStatus,
}: {
  eventId: string;
  base?: "host" | "admin";
  /** When completed, Memories is promoted near the front of the nav. */
  eventStatus?: EventStatus;
}) {
  const pathname = usePathname() || "";
  const root =
    base === "admin"
      ? `/admin/events/${eventId}`
      : `/host/events/${eventId}`;
  const links =
    base === "admin" ? ADMIN_LINKS : hostLinksForStatus(eventStatus);
  const completed = eventStatus === "completed";

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
        const emphasizeMemories =
          completed && link.suffix === "/memory" && !active;
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
              "shrink-0 rounded-full px-3 py-1.5 text-xs font-bold transition-colors",
              emphasizeMemories
                ? "bg-primary text-primary-foreground shadow-[var(--shadow-soft)] hover:bg-primary-hover"
                : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </ScrollHintNav>
  );
}
