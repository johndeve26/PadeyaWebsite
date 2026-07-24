"use client";

import Link from "next/link";

import {
  eventMapCardChrome,
  eventMapPriceClass,
  eventMapTitleClass,
} from "@/components/events/map/event-map-card-chrome";
import { Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import type { MapEventPin } from "@/lib/maps/types";

function formatTime(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-NG", {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function EventMapPreviewCard({
  event,
  selected = false,
  onSelect,
  className = "",
}: {
  event: MapEventPin;
  selected?: boolean;
  onSelect?: (id: string) => void;
  className?: string;
}) {
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
  const approx = event.location_map_mode === "approximate";
  const href = `/events/${event.slug}`;

  return (
    <article className={cn(eventMapCardChrome({ selected }), className)}>
      <Link
        href={href}
        aria-pressed={selected}
        className="flex w-full min-w-0 gap-3 p-2.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        onClick={() => onSelect?.(event.id)}
      >
        <div className="relative h-20 w-24 shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-ink">
          {cover ? (
            <Media src={cover} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="padeya-hero-glow absolute inset-0 opacity-80" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <p className={cn("truncate text-sm", eventMapTitleClass)}>
            {event.title}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatDate(event.start_datetime)}
            {time ? ` · ${time}` : ""}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {place}
            {approx ? " · Area" : ""}
          </p>
          <div className="flex flex-wrap items-center gap-2 pt-0.5">
            <span className={eventMapPriceClass}>
              {event.price_label || (event.is_free ? "Free" : "See tickets")}
            </span>
            {event.distance_label ? (
              <span className="text-[11px] text-muted-foreground">
                {event.distance_label}
              </span>
            ) : null}
          </div>
          {event.location_privacy_message ? (
            <p className="text-[11px] text-muted-foreground">
              {event.location_privacy_message}
            </p>
          ) : null}
        </div>
      </Link>
    </article>
  );
}
