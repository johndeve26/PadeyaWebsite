"use client";

import Link from "next/link";

import { Button, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import type { MapEventPin } from "@/lib/maps/types";

import { eventMapCardChrome, eventMapPriceClass, eventMapTitleClass } from "@/components/events/map/event-map-card-chrome";

function formatTime(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-NG", {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function EventMapList({
  events,
  selectedId,
  onSelect,
  loading = false,
  className = "",
}: {
  events: MapEventPin[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading?: boolean;
  className?: string;
}) {
  if (loading && events.length === 0) {
    return (
      <div className={cn("space-y-3", className)} aria-busy="true">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-[var(--radius-lg)] bg-surface-muted dark:bg-ink/80"
          />
        ))}
      </div>
    );
  }

  if (!loading && events.length === 0) {
    return (
      <div
        className={cn(
          "rounded-[var(--radius-lg)] border border-border/70 bg-surface-muted px-4 py-8 text-center",
          "dark:border-white/10 dark:bg-ink",
          className,
        )}
      >
        <p className="text-sm font-semibold text-heading">
          No events in this area.
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Move the map or adjust your filters.
        </p>
        <Link href="/events" className="mt-4 inline-flex">
          <Button variant="secondary" className="min-h-10">
            View all events
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <ul className={cn("space-y-3", className)}>
      {events.map((event, index) => {
        const selected = event.id === selectedId;
        const cover = resolveEventImage(
          event.slug,
          event.title,
          event.banner_url,
          event.category_name || event.category_slug,
        );
        const time = formatTime(event.start_datetime);
        const place =
          event.public_location_label ||
          [event.area, event.city].filter(Boolean).join(", ") ||
          "Location TBA";
        const host = event.host_display_name?.trim() || null;
        const href = `/events/${event.slug}`;

        return (
          <li key={event.id}>
            <article
              className={cn(
                eventMapCardChrome({ selected }),
                "padeya-section-enter",
              )}
              style={{ animationDelay: `${Math.min(index, 8) * 30}ms` }}
            >
              <Link
                href={href}
                aria-pressed={selected}
                className="flex w-full min-w-0 gap-3 p-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                onClick={() => onSelect(event.id)}
              >
                <div className="relative h-[4.75rem] w-[5.5rem] shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-ink sm:h-24 sm:w-28">
                  {cover ? (
                    <Media
                      src={cover}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="padeya-hero-glow absolute inset-0 opacity-80" />
                  )}
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <p className={cn("line-clamp-2 text-sm", eventMapTitleClass)}>
                    {event.title}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(event.start_datetime)}
                    {time ? ` · ${time}` : ""}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">{place}</p>
                  {host ? (
                    <p className="truncate text-xs text-muted-foreground">
                      Host · {host}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap items-center gap-2 pt-0.5">
                    <span className={eventMapPriceClass}>
                      {event.price_label ||
                        (event.is_free ? "Free" : "See tickets")}
                    </span>
                    {event.distance_label ? (
                      <span className="text-[11px] text-muted-foreground">
                        {event.distance_label}
                      </span>
                    ) : null}
                  </div>
                </div>
              </Link>
            </article>
          </li>
        );
      })}
    </ul>
  );
}
