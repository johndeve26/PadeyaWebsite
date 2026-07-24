"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/events/StatusBadge";
import { Button } from "@/components/ui";
import { fetchHostEventAnalyticsOverview } from "@/lib/analytics-api";
import { formatDateTime } from "@/lib/format";
import type { EventItem } from "@/lib/types/events";

type EventActions = {
  canEdit: boolean;
  canScan: boolean;
  canMerch: boolean;
  canAnalytics: boolean;
};

export function UpcomingEventRow({
  event,
  actions,
}: {
  event: EventItem;
  actions: EventActions;
}) {
  const [ticketsSold, setTicketsSold] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    void fetchHostEventAnalyticsOverview(event.id)
      .then((overview) => {
        if (active) setTicketsSold(overview.purchases);
      })
      .catch(() => {
        if (active) setTicketsSold(null);
      });
    return () => {
      active = false;
    };
  }, [event.id]);

  return (
    <div className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/host/events/${event.id}`}
              className="font-extrabold text-foreground hover:text-accent"
            >
              {event.title}
            </Link>
            <StatusBadge status={event.status} />
          </div>
          <p className="text-sm text-muted-foreground">
            {formatDateTime(event.start_datetime)} ·{" "}
            {[event.venue_name, event.city].filter(Boolean).join(", ") ||
              "Venue TBA"}
          </p>
          <p className="text-sm text-muted-foreground">
            Tickets sold:{" "}
            <span className="font-bold tabular-nums text-foreground">
              {ticketsSold === null ? "—" : ticketsSold}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {actions.canEdit ? (
            <Link href={`/host/events/${event.id}/edit`}>
              <Button size="sm" variant="secondary">
                Edit
              </Button>
            </Link>
          ) : null}
          {actions.canScan ? (
            <Link href={`/host/events/${event.id}/check-in`}>
              <Button size="sm" variant="secondary">
                Scanner
              </Button>
            </Link>
          ) : null}
          {actions.canEdit ? (
            <Link href={`/host/events/${event.id}/tickets`}>
              <Button size="sm" variant="secondary">
                Tickets
              </Button>
            </Link>
          ) : null}
          {actions.canMerch ? (
            <Link href={`/host/events/${event.id}/merchandise`}>
              <Button size="sm" variant="secondary">
                Merch Studio
              </Button>
            </Link>
          ) : null}
          {actions.canAnalytics ? (
            <Link href={`/host/events/${event.id}/analytics`}>
              <Button size="sm" variant="secondary">
                Analytics
              </Button>
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}
