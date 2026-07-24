"use client";

import { useEventsLgUp } from "@/hooks/useEventsLgUp";
import { cn } from "@/lib/cn";
import type { EventsViewMode } from "@/lib/events/marketplace-listing";

const MODES: {
  value: EventsViewMode;
  label: string;
  /** Omitted from switcher below lg — desktop split/list/map only. */
  desktopOnly?: boolean;
}[] = [
  { value: "grid", label: "Grid" },
  { value: "list", label: "List", desktopOnly: true },
  { value: "calendar", label: "Calendar" },
  { value: "map", label: "Map", desktopOnly: true },
];

/** View switcher for /events — Grid | List | Calendar | Map (List/Map at lg+ only). */
export function EventViewSwitcher({
  value,
  onChange,
  className = "",
}: {
  value: EventsViewMode;
  onChange: (v: EventsViewMode) => void;
  className?: string;
}) {
  const isLgUp = useEventsLgUp();
  const modes = MODES.filter((mode) => isLgUp || !mode.desktopOnly);

  return (
    <div
      role="group"
      aria-label="View mode"
      className={cn(
        "inline-flex min-h-10 max-w-full flex-wrap items-center gap-0.5 rounded-[var(--radius-md)] border border-border bg-surface-elevated p-0.5 dark:bg-surface-muted",
        className,
      )}
    >
      {modes.map((mode) => {
        const active = value === mode.value;
        return (
          <button
            key={mode.value}
            type="button"
            onClick={() => onChange(mode.value)}
            aria-pressed={active}
            className={cn(
              "inline-flex min-h-9 items-center rounded-[calc(var(--radius-md)-2px)] px-2.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background sm:px-3",
              active
                ? "bg-ink text-paper shadow-[var(--shadow-soft)]"
                : "text-muted-foreground hover:bg-surface-inset hover:text-foreground",
            )}
          >
            {mode.label}
          </button>
        );
      })}
    </div>
  );
}

/** @deprecated Prefer EventViewSwitcher — kept for existing imports. */
export const EventsViewToggle = EventViewSwitcher;
