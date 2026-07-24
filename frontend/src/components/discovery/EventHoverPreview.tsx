"use client";

import Link from "next/link";

import { Badge, Button, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import { ticketAvailabilityLabel } from "@/lib/discovery/marketplace-groups";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import { formatDateTime, formatNgn } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import type { EventItem } from "@/lib/types/events";

function priceFrom(event: EventItem): string {
  const types = event.ticket_types ?? [];
  if (!types.length) return "See tickets";
  const prices = types
    .map((t) => Number(t.price))
    .filter((n) => Number.isFinite(n));
  if (!prices.length) return "See tickets";
  const min = Math.min(...prices);
  if (min === 0) return "Free";
  return `From ${formatNgn(min)}`;
}

/**
 * Desktop hover preview popover — uses existing card/event fields only.
 */
export function EventHoverPreview({
  event,
  className = "",
}: {
  event: EventItem;
  className?: string;
}) {
  const cover = resolveEventImage(
    event.slug,
    event.title,
    event.banner_url,
    event.category?.name || event.category?.slug,
  );
  const when = event.start_datetime
    ? formatDateTime(event.start_datetime)
    : null;
  const place = formatPublicPlaceLabel(event);
  const stock = ticketAvailabilityLabel(event);
  const blurb =
    event.short_tagline ||
    (event.description
      ? event.description.replace(/\s+/g, " ").trim().slice(0, 140)
      : null);

  return (
    <div
      role="tooltip"
      data-hover-preview
      className={cn(
        "pointer-events-none absolute left-1/2 top-0 z-40 hidden w-[min(22rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-[calc(100%+0.75rem)]",
        "rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-strong)] dark:bg-surface-elevated",
        "opacity-0 transition-opacity duration-200",
        "group-hover:pointer-events-auto group-hover:opacity-100",
        "lg:block",
        className,
      )}
    >
      <div className="relative aspect-[16/10] overflow-hidden rounded-t-[var(--radius-lg)] bg-ink">
        {cover ? (
          <Media src={cover} alt="" className="h-full w-full object-cover" />
        ) : (
          <div aria-hidden className="padeya-hero-glow absolute inset-0" />
        )}
        <div className="absolute left-2.5 top-2.5 flex flex-wrap gap-1.5">
          {event.category?.name ? (
            <Badge tone="dark" size="sm">
              {event.category.name}
            </Badge>
          ) : null}
          {stock ? (
            <Badge tone={stock === "Sold out" ? "danger" : "warning"} size="sm">
              {stock}
            </Badge>
          ) : null}
        </div>
      </div>
      <div className="space-y-2.5 p-4">
        <h4 className="text-base font-extrabold tracking-tight text-foreground">
          {event.title}
        </h4>
        {when ? (
          <p className="text-sm font-medium text-foreground/80">{when}</p>
        ) : null}
        {place ? <p className="text-sm text-muted-foreground">{place}</p> : null}
        {event.host_display_name ? (
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
            Hosted by {event.host_display_name}
          </p>
        ) : null}
        {blurb ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {blurb}
            {blurb.length >= 140 ? "…" : ""}
          </p>
        ) : null}
        <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
          <p className="text-sm font-extrabold text-foreground">
            {priceFrom(event)}
          </p>
          <Link href={`/events/${event.slug}`} tabIndex={-1}>
            <Button size="sm" variant="secondary">
              View event
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
