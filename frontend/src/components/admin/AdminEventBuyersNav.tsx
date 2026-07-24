"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const TABS: { suffix: string; label: string }[] = [
  { suffix: "/buyers", label: "Buyers" },
  { suffix: "/attendees", label: "Attendees" },
  { suffix: "/exports", label: "Exports" },
  { suffix: "/analytics", label: "Analytics" },
];

export function AdminEventBuyersNav({ eventId }: { eventId: string }) {
  const pathname = usePathname() || "";
  const root = `/admin/events/${eventId}`;

  return (
    <div
      role="tablist"
      aria-label="Admin event buyer tools"
      className="flex min-w-0 gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {TABS.map((tab) => {
        const href = `${root}${tab.suffix}`;
        const selected = pathname.startsWith(href);
        if (selected) {
          return (
            <span
              key={tab.suffix}
              role="tab"
              aria-selected
              className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-xs font-bold text-paper"
            >
              {tab.label}
            </span>
          );
        }
        return (
          <Link
            key={tab.suffix}
            href={href}
            role="tab"
            aria-selected={false}
            className={cn(
              "shrink-0 rounded-full px-3 py-1.5 text-xs font-bold text-muted-foreground transition-colors",
              "hover:bg-surface-muted hover:text-foreground",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
