import Link from "next/link";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  isFreeEvent,
  minTicketPrice,
} from "@/lib/discovery/event-filters";
import { ticketAvailabilityLabel } from "@/lib/discovery/marketplace-groups";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import { formatDate, formatNgn } from "@/lib/format";
import type { EventItem } from "@/lib/types/events";

function priceLabel(event: EventItem): string {
  if (isFreeEvent(event)) return "Free";
  const min = minTicketPrice(event);
  if (min == null) return "—";
  return formatNgn(min);
}

export function EventCompactRow({
  event,
  className = "",
}: {
  event: EventItem;
  className?: string;
}) {
  const place = formatPublicPlaceLabel(event);
  const stock = ticketAvailabilityLabel(event);

  return (
    <div
      className={cn(
        "grid min-w-0 grid-cols-[4.5rem_1fr_auto] items-center gap-2 border-b border-border py-2.5 sm:grid-cols-[5.5rem_minmax(0,1.4fr)_minmax(0,0.8fr)_5.5rem_auto] sm:gap-3",
        className,
      )}
    >
      <p className="text-xs font-bold text-muted-foreground sm:text-sm">
        {formatDate(event.start_datetime)}
      </p>
      <Link
        href={`/events/${event.slug}`}
        prefetch={false}
        className="min-w-0 truncate text-sm font-bold text-foreground hover:underline sm:text-base"
      >
        {event.title}
      </Link>
      <p className="hidden min-w-0 truncate text-sm text-muted-foreground sm:block">
        {place || "—"}
      </p>
      <p className="text-right text-sm font-extrabold text-foreground">
        {priceLabel(event)}
      </p>
      <div className="col-span-3 flex items-center justify-between gap-2 sm:col-span-1 sm:justify-end">
        <span className="text-xs text-muted-foreground sm:hidden">
          {place || stock || ""}
        </span>
        <Link href={`/events/${event.slug}`} prefetch={false}>
          <Button size="sm" variant="secondary">
            View
          </Button>
        </Link>
      </div>
    </div>
  );
}
