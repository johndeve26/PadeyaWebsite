"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  Button,
  EmptyState,
  StatusBadge,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import {
  countDeskEventsByFilter,
  DESK_EVENT_FILTERS,
  emptyCopyForDeskFilter,
  filterDeskEvents,
  type DeskEventFilter,
} from "@/lib/host-desk-events";
import type { HostDeskEvent } from "@/lib/types/host-workspace";

type Props = {
  events: HostDeskEvent[];
  showTicketScanner: boolean;
  showHostCheckIn?: boolean;
  showMerchPickup: boolean;
  showEventLink?: boolean;
};

export function HostDeskEventList({
  events,
  showTicketScanner,
  showHostCheckIn = false,
  showMerchPickup,
  showEventLink = true,
}: Props) {
  const [filter, setFilter] = useState<DeskEventFilter>("ready");
  const counts = useMemo(() => countDeskEventsByFilter(events), [events]);
  const visible = useMemo(
    () => filterDeskEvents(events, filter),
    [events, filter],
  );
  const empty = emptyCopyForDeskFilter(filter);

  return (
    <div className="space-y-4">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div
          role="tablist"
          aria-label="Desk event filters"
          className="flex min-w-0 flex-1 gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {DESK_EVENT_FILTERS.map((tab) => {
            const selected = filter === tab.value;
            const count = counts[tab.value];
            return (
              <button
                key={tab.value}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setFilter(tab.value)}
                className={cn(
                  "inline-flex shrink-0 items-center gap-1.5 rounded-[calc(var(--radius-md)-2px)] px-3 py-2 text-sm font-semibold transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  selected
                    ? "bg-muted text-foreground ring-1 ring-border"
                    : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
                )}
              >
                {tab.label}
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums",
                    selected
                      ? "bg-surface-elevated text-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
        <p className="shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
          {visible.length} of {events.length}
        </p>
      </div>

      {visible.length === 0 ? (
        <EmptyState title={empty.title} description={empty.description} />
      ) : (
        <div className="space-y-3">
          {visible.map((event) => (
            <div
              key={event.id}
              className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-lg font-extrabold text-foreground">
                      {event.title}
                    </p>
                    <StatusBadge status={event.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {formatDateTime(event.start_datetime)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {showTicketScanner ? (
                    <Link href={event.staff_check_in_path}>
                      <Button size="sm">Ticket scanner</Button>
                    </Link>
                  ) : null}
                  {showHostCheckIn ? (
                    <Link href={event.host_check_in_path}>
                      <Button size="sm" variant="secondary">
                        Host check-in
                      </Button>
                    </Link>
                  ) : null}
                  {showMerchPickup ? (
                    <Link
                      href={`/host/events/${event.id}/merchandise/fulfillment`}
                    >
                      <Button
                        size="sm"
                        variant={showTicketScanner ? "secondary" : "primary"}
                      >
                        Merch pickup
                      </Button>
                    </Link>
                  ) : null}
                  {showEventLink ? (
                    <Link href={`/host/events/${event.id}`}>
                      <Button size="sm" variant="ghost">
                        Event
                      </Button>
                    </Link>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
