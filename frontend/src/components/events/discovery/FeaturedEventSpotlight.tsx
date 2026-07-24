"use client";

import Link from "next/link";

import { Badge, Button, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
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
 * Featured event spotlight for marketplace / homepage discovery.
 * Prefer `event.featured`; callers should pass fallback nearest-upcoming.
 */
export function FeaturedEventSpotlight({
  event,
  className = "",
  eyebrow = "Featured",
}: {
  event: EventItem;
  className?: string;
  eyebrow?: string;
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
  const host = event.host_display_name || null;

  return (
    <section
      className={cn(
        "relative min-w-0 overflow-hidden rounded-[var(--radius-xl)] border border-paper/10 bg-ink",
        className,
      )}
      aria-label={`${eyebrow}: ${event.title}`}
    >
      <div className="absolute inset-0">
        <Media src={cover} alt="" className="h-full w-full object-cover opacity-45" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/85 to-ink/40" />
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-transparent to-ink/30" />
      </div>

      <div className="relative grid gap-6 p-5 sm:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] sm:p-7 lg:p-8">
        <div className="flex min-w-0 flex-col justify-end space-y-3 sm:space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">{eyebrow}</Badge>
            {event.category?.name ? (
              <Badge
                tone="outline"
                className="border-paper/25 text-paper/80 ring-paper/25"
              >
                {event.category.name}
              </Badge>
            ) : null}
          </div>
          <h2 className="text-balance text-2xl font-extrabold tracking-tight text-paper sm:text-3xl lg:text-[2.15rem] lg:leading-tight">
            {event.title}
          </h2>
          <div className="space-y-1 text-sm text-paper/70">
            {when ? <p>{when}</p> : null}
            {place ? <p>{place}</p> : null}
            {host ? <p>Hosted by {host}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link href={`/events/${event.slug}`}>
              <Button size="lg">View event</Button>
            </Link>
            <span className="text-sm font-semibold text-primary">
              {priceFrom(event)}
            </span>
          </div>
        </div>

        <div className="relative hidden min-h-[14rem] overflow-hidden rounded-[var(--radius-lg)] border border-paper/15 sm:block">
          <Media src={cover} alt="" className="absolute inset-0 h-full w-full object-cover" />
        </div>
      </div>
    </section>
  );
}
