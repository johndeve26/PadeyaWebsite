"use client";

import { EventsViewToggle } from "@/components/events/marketplace/EventsViewToggle";
import { cn } from "@/lib/cn";
import type { SortKey } from "@/lib/discovery/event-filters";
import {
  EVENTS_SORT_OPTIONS,
  type EventsViewMode,
} from "@/lib/events/marketplace-listing";
import { fieldControlClass } from "@/lib/ui/field";

const controlSurfaceClass =
  "h-10 border-border bg-surface-elevated shadow-none dark:bg-surface-muted";

export function EventsResultsToolbar({
  total,
  visible,
  loading = false,
  sort,
  onSortChange,
  view,
  onViewChange,
  className = "",
}: {
  total: number;
  visible: number;
  loading?: boolean;
  sort: SortKey;
  onSortChange: (v: SortKey) => void;
  view: EventsViewMode;
  onViewChange: (v: EventsViewMode) => void;
  className?: string;
}) {
  const countLabel = loading
    ? "Loading…"
    : total === 0
      ? "No events"
      : `${visible} of ${total}`;

  return (
    <div
      className={cn(
        "flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2",
        className,
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2.5 sm:gap-3">
        <p
          className="min-w-0 truncate text-xs font-medium tabular-nums text-muted-foreground sm:text-sm"
          aria-live="polite"
        >
          {countLabel}
          {!loading && total > 0 ? (
            <span className="sr-only">
              {" "}
              event{total === 1 ? "" : "s"} shown
            </span>
          ) : null}
        </p>
      </div>

      <div className="flex min-w-0 shrink-0 flex-wrap items-center gap-2">
        <label className="relative block w-[9.75rem] max-w-full shrink-0">
          <span className="sr-only">Sort</span>
          <select
            value={sort}
            onChange={(e) => onSortChange(e.target.value as SortKey)}
            className={fieldControlClass({
              className: cn(
                "appearance-none px-3 pr-9 text-sm font-medium",
                controlSurfaceClass,
              ),
            })}
          >
            {EVENTS_SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <span
            aria-hidden
            className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground"
          >
            ▾
          </span>
        </label>

        <EventsViewToggle
          value={view}
          onChange={onViewChange}
          className="shrink-0"
        />
      </div>
    </div>
  );
}
