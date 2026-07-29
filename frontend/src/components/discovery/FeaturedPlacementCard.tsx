"use client";

import Link from "next/link";

import { TrackImpression } from "@/components/analytics/TrackImpression";
import { Badge, Button, Media } from "@/components/ui";
import {
  trackPadeyaPickClick,
  trackPadeyaPickImpression,
  type LocationAnalyticsMeta,
} from "@/lib/analytics";
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

function hostInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

export type FeaturedPlacementCardAnalytics = LocationAnalyticsMeta & {
  placementContext: string;
  slotNumber: 1 | 2;
  fromPlacement?: boolean;
  enabled?: boolean;
};

/** @deprecated Prefer FeaturedPlacementCardAnalytics */
export type PadeyaPickAnalytics = FeaturedPlacementCardAnalytics;

/**
 * Public / preview card for a featured placement (Pàdéyá Pick).
 */
export function FeaturedPlacementCard({
  event,
  variant = "primary",
  className = "",
  analytics,
  badgeText = "Pàdéyá Pick",
  slotLabel,
}: {
  event: EventItem;
  variant?: "primary" | "secondary";
  className?: string;
  analytics?: FeaturedPlacementCardAnalytics;
  badgeText?: string;
  /** Optional admin preview label e.g. "Primary Spotlight". */
  slotLabel?: string;
}) {
  const primary = variant === "primary";
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
  const category = event.category?.name || null;
  const host = event.host_display_name || null;
  const price = priceFrom(event);
  const stock = ticketAvailabilityLabel(event);
  const trackingEnabled = Boolean(analytics && analytics.enabled !== false);

  function onPickClick() {
    if (!trackingEnabled || !analytics) return;
    trackPadeyaPickClick({
      eventId: event.id,
      placementContext: analytics.placementContext,
      slotNumber: analytics.slotNumber,
      fromPlacement: analytics.fromPlacement,
      country: analytics.country,
      state: analytics.state,
      city: analytics.city,
      area: analytics.area,
      category: analytics.category,
    });
  }

  const card = (
    <article
      className={cn(
        "padeya-discovery-card group flex h-full min-w-0 flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-soft)]",
        "dark:border-border dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        className,
      )}
    >
      <Link
        href={`/events/${event.slug}`}
        className={cn(
          "relative block overflow-hidden bg-ink",
          primary ? "aspect-[16/9] sm:aspect-[16/8]" : "aspect-[16/10]",
        )}
        onClick={onPickClick}
      >
        {cover ? (
          <Media
            src={cover}
            alt=""
            className="padeya-image-zoom h-full w-full object-cover"
          />
        ) : (
          <div aria-hidden className="padeya-hero-glow absolute inset-0" />
        )}
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-ink/80 via-ink/15 to-transparent"
        />
        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          <Badge tone="accent" size="sm">
            {badgeText}
          </Badge>
          {slotLabel ? (
            <Badge tone="neutral" size="sm">
              {slotLabel}
            </Badge>
          ) : null}
          {category ? (
            <Badge tone="dark" size="sm">
              {category}
            </Badge>
          ) : null}
        </div>
        {stock ? (
          <div className="absolute right-3 top-3">
            <Badge
              tone={stock === "Sold out" ? "danger" : "warning"}
              size="sm"
            >
              {stock}
            </Badge>
          </div>
        ) : null}
        <p
          className={cn(
            "absolute bottom-3 left-3 font-extrabold text-paper drop-shadow",
            primary ? "text-lg sm:text-xl" : "text-base sm:text-lg",
          )}
        >
          {price}
        </p>
      </Link>

      <div
        className={cn(
          "flex flex-1 flex-col gap-3",
          primary ? "p-5 sm:p-6" : "p-4 sm:p-5",
        )}
      >
        <div className="space-y-2.5">
          {when ? (
            <p
              className={cn(
                "font-bold uppercase tracking-[0.12em] text-muted-foreground",
                primary ? "text-xs sm:text-sm" : "text-[11px]",
              )}
            >
              {when}
            </p>
          ) : null}
          <Link
            href={`/events/${event.slug}`}
            className="block"
            onClick={onPickClick}
          >
            <h3
              className={cn(
                "text-balance font-extrabold tracking-tight text-foreground",
                primary ? "text-2xl sm:text-3xl" : "text-xl sm:text-2xl",
              )}
            >
              {event.title}
            </h3>
          </Link>
          <div
            className={cn(
              "space-y-1 text-muted-foreground",
              primary ? "text-sm sm:text-base" : "text-sm",
            )}
          >
            {place ? <p>{place}</p> : null}
          </div>
          {host ? (
            <div className="flex items-center gap-2.5 pt-1">
              <span
                aria-hidden
                className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-ink text-xs font-extrabold text-accent"
              >
                {hostInitials(host)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-foreground">
                  {host}
                </p>
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                  Host
                </p>
              </div>
            </div>
          ) : null}
        </div>

        <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <p
            className={cn(
              "font-extrabold text-foreground",
              primary ? "text-base sm:text-lg" : "text-sm sm:text-base",
            )}
          >
            {price}
          </p>
          <Link href={`/events/${event.slug}`} onClick={onPickClick}>
            <Button
              size={primary ? "md" : "sm"}
              variant="primary"
              className="padeya-btn-ripple"
            >
              View event
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );

  if (!trackingEnabled || !analytics) return card;

  return (
    <TrackImpression
      targetEventId={event.id}
      hostId={event.host_id}
      listContext={analytics.placementContext}
      cardPosition={analytics.slotNumber}
      trackCardImpression={false}
      className={cn("h-full w-full min-w-0", className)}
      onImpression={() => {
        trackPadeyaPickImpression({
          eventId: event.id,
          placementContext: analytics.placementContext,
          slotNumber: analytics.slotNumber,
          fromPlacement: analytics.fromPlacement,
          country: analytics.country,
          state: analytics.state,
          city: analytics.city,
          area: analytics.area,
          category: analytics.category,
        });
      }}
    >
      {card}
    </TrackImpression>
  );
}
