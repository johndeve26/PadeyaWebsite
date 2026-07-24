"use client";

import { cn } from "@/lib/cn";

export type CheckInTab = "scanner" | "attendees" | "stats" | "offline";

const tabs: { id: CheckInTab; label: string }[] = [
  { id: "scanner", label: "Scanner" },
  { id: "attendees", label: "Attendees" },
  { id: "stats", label: "Door stats" },
  { id: "offline", label: "Offline buffer" },
];

export function CheckInTabNav({
  active,
  onSelect,
  className,
}: {
  active: CheckInTab;
  onSelect: (tab: CheckInTab) => void;
  className?: string;
}) {
  return (
    <nav
      className={cn(
        "sticky top-0 z-20 -mx-1 flex gap-1 overflow-x-auto rounded-[var(--radius-lg)] border border-border bg-surface-elevated/95 p-1 backdrop-blur-md",
        className,
      )}
      aria-label="Check-in sections"
    >
      {tabs.map((tab) => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onSelect(tab.id)}
            className={cn(
              "shrink-0 rounded-[var(--radius-md)] px-3 py-2 text-xs font-extrabold tracking-tight transition-colors",
              isActive
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
            aria-current={isActive ? "page" : undefined}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
