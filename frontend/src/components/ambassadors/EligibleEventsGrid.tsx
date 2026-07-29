"use client";

import Link from "next/link";

import { Button, EmptyState } from "@/components/ui";
import { formatDateTime, formatPercent } from "@/lib/format";
import type { EligibleAmbassadorEvent } from "@/lib/types/promos";

export function EligibleEventsGrid({
  events,
  promoteHref,
}: {
  events: EligibleAmbassadorEvent[];
  /** Where “Promote this event” should land — public event page by default */
  promoteHref?: (event: EligibleAmbassadorEvent) => string;
}) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No open Ambassadors events yet"
        description="When hosts enable Event Ambassadors, those events appear here for anyone with a Pàdéyá account to promote."
        action={
          <Link href="/events">
            <Button size="sm" variant="primary">
              Browse all events
            </Button>
          </Link>
        }
      />
    );
  }

  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {events.map((event) => {
        const href =
          promoteHref?.(event) ?? `/events/${event.slug}#promote-ambassadors`;
        return (
          <li
            key={event.id}
            className="flex flex-col border border-border bg-card p-4 shadow-[var(--shadow-soft)]"
          >
            <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
              {event.city || "Event"}
            </p>
            <h3 className="mt-2 text-lg font-extrabold text-heading">{event.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {event.host_display_name ? `${event.host_display_name} · ` : ""}
              {formatDateTime(event.start_datetime)}
            </p>
            <p className="mt-3 text-sm text-body">
              Earn {formatPercent(event.open_ambassador_commission_percent)} on
              verified purchases
            </p>
            <div className="mt-auto pt-4">
              <Link href={href}>
                <Button className="w-full" size="sm">
                  Promote this event
                </Button>
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
