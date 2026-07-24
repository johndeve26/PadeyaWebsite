"use client";

import Link from "next/link";

import { TrackImpression } from "@/components/analytics/TrackImpression";
import { cn } from "@/lib/cn";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import { formatDateTime, formatNgn } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import {
  trackEventCardClick,
  type ListContext,
} from "@/lib/analytics";
import type { EventItem } from "@/lib/types/events";

import { Badge } from "./Badge";
import { Media } from "./Media";

function priceFrom(event: EventItem): string | null {
  const types = event.ticket_types ?? [];
  if (!types.length) return null;
  const prices = types
    .map((t) => Number(t.price))
    .filter((n) => Number.isFinite(n));
  if (!prices.length) return null;
  const min = Math.min(...prices);
  if (min === 0) return "Free";
  return `From ${formatNgn(min)}`;
}

function availability(event: EventItem): string | null {
  const types = event.ticket_types ?? [];
  if (!types.length) return null;
  const total = types.reduce((sum, t) => sum + (t.quantity ?? 0), 0);
  if (total <= 0) return "Sold out";
  if (total < 40) return "Selling fast";
  return "Tickets available";
}

export function EventCard({
  event,
  className = "",
  listContext = "events_grid",
  cardPosition,
}: {
  event: EventItem;
  className?: string;
  listContext?: ListContext;
  cardPosition?: number;
}) {
  const price = priceFrom(event);
  const stock = availability(event);
  const image = resolveEventImage(
    event.slug,
    event.title,
    event.banner_url,
    event.category?.name || event.category?.slug,
  );
  const when = formatDateTime(event.start_datetime);
  const place = formatPublicPlaceLabel(event) || "Location TBA";

  return (
    <TrackImpression
      targetEventId={event.id}
      hostId={event.host_id}
      listContext={listContext}
      cardPosition={cardPosition}
      className={cn("h-full", className)}
    >
      <Link
        href={`/events/${event.slug}`}
        className="group block h-full"
        onClick={() => {
          trackEventCardClick({
            targetEventId: event.id,
            hostId: event.host_id,
            listContext,
            clickTarget: "card",
          });
        }}
      >
        <article
          className={cn(
            "padeya-card-hover flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-soft)]",
            "dark:border-border dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
            "transition-[border-color,box-shadow] group-hover:border-border-strong/25",
          )}
        >
          <div className="relative aspect-[16/10] w-full shrink-0 overflow-hidden bg-surface-dark">
            <Media
              src={image}
              alt=""
              className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
            />
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-ink/80 to-transparent" />
            <div className="absolute left-3 top-3 flex flex-wrap gap-2">
              {event.featured ? <Badge tone="accent">Featured</Badge> : null}
              {event.category ? (
                <Badge tone="dark">{event.category.name}</Badge>
              ) : null}
            </div>
            {stock === "Sold out" || stock === "Selling fast" ? (
              <div className="absolute right-3 top-3">
                <Badge
                  tone={stock === "Sold out" ? "danger" : "warning"}
                  size="sm"
                >
                  {stock}
                </Badge>
              </div>
            ) : null}
            <div className="absolute inset-x-3 bottom-3 flex items-end justify-between gap-2">
              {price ? (
                <p className="text-sm font-extrabold text-paper drop-shadow sm:text-base">
                  {price}
                </p>
              ) : (
                <span />
              )}
              {stock && stock !== "Sold out" && stock !== "Selling fast" ? (
                <span className="rounded-full bg-ink/55 px-2.5 py-1 text-xs font-bold uppercase tracking-[0.08em] text-paper/85 backdrop-blur-sm">
                  {stock}
                </span>
              ) : null}
            </div>
          </div>
          <div className="flex flex-1 flex-col gap-2.5 p-4 sm:p-5">
            <h3 className="line-clamp-2 text-balance text-base font-extrabold leading-snug tracking-tight text-foreground sm:text-lg">
              {event.title}
            </h3>
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground/85">
                {when}
              </p>
              <p className="line-clamp-1 text-sm text-muted-foreground">{place}</p>
              {event.distance_label &&
              (listContext === "homepage_nearby" ||
                listContext === "events_near_me") ? (
                <p className="text-xs font-semibold text-primary/90">
                  {event.distance_label}
                </p>
              ) : null}
              {event.host_display_name ? (
                <p className="line-clamp-1 text-sm font-semibold text-muted-foreground">
                  {event.host_display_name}
                </p>
              ) : null}
            </div>
            <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-3">
              <span className="text-sm font-semibold text-muted-foreground">
                Secure tickets
              </span>
              <span className="text-sm font-bold uppercase tracking-[0.08em] text-foreground opacity-70 transition-opacity group-hover:opacity-100">
                View →
              </span>
            </div>
          </div>
        </article>
      </Link>
    </TrackImpression>
  );
}
