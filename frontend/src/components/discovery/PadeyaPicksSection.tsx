"use client";

import {
  FeaturedPlacementCard,
  type FeaturedPlacementCardAnalytics,
} from "@/components/discovery/FeaturedPlacementCard";
import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { Container } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { LocationAnalyticsMeta } from "@/lib/analytics";
import {
  PADEYA_PICKS_TITLE,
} from "@/lib/discovery/padeya-picks";
import type { EventItem } from "@/lib/types/events";

export type PadeyaPicksSectionAnalytics = LocationAnalyticsMeta & {
  placementContext: string;
  /** Event IDs that came from admin featured placements (vs fallback pool). */
  placementEventIds?: ReadonlySet<string> | readonly string[];
  enabled?: boolean;
};

/** @deprecated Prefer PadeyaPicksSectionAnalytics */
export type FeaturedSectionAnalytics = PadeyaPicksSectionAnalytics;

function isPlacementEvent(
  eventId: string,
  ids?: ReadonlySet<string> | readonly string[],
): boolean {
  if (!ids) return false;
  if (ids instanceof Set) return ids.has(eventId);
  return Array.from(ids).includes(eventId);
}

/**
 * Public Pàdéyá Picks section (Primary + Secondary spotlight).
 */
export function PadeyaPicksSection({
  events,
  title = PADEYA_PICKS_TITLE,
  description,
  eyebrow,
  className = "",
  layout: _layout = "spotlight",
  analytics,
  showSlotLabels = false,
}: {
  events: EventItem[];
  title?: string;
  description?: string;
  /** Optional context line above the section title (e.g. Lagos). */
  eyebrow?: string;
  className?: string;
  /** Kept for callers; both modes use a full-width 2-column grid. */
  layout?: "spotlight" | "equal";
  analytics?: PadeyaPicksSectionAnalytics;
  /** Show Primary/Secondary labels on cards (admin preview). */
  showSlotLabels?: boolean;
}) {
  void _layout;
  const picks = events.slice(0, 2);
  if (!picks.length) return null;

  function cardAnalytics(
    event: EventItem,
    slotNumber: 1 | 2,
  ): FeaturedPlacementCardAnalytics | undefined {
    if (!analytics || analytics.enabled === false) return undefined;
    return {
      placementContext: analytics.placementContext,
      slotNumber,
      fromPlacement: isPlacementEvent(event.id, analytics.placementEventIds),
      country: analytics.country,
      state: analytics.state,
      city: analytics.city,
      area: analytics.area,
      category: analytics.category,
      enabled: true,
    };
  }

  return (
    <section
      aria-label={title}
      className={cn(
        "border-b border-border bg-muted/60 py-8 sm:py-10",
        className,
      )}
    >
      <Container className="space-y-6">
        <div className="max-w-3xl space-y-2">
          <p className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.2em] text-heading">
            <span
              aria-hidden
              className="inline-block h-[3px] w-7 shrink-0 rounded-[1px] bg-primary"
            />
            <span>{eyebrow ?? "Featured by Pàdéyá"}</span>
          </p>
          <h2 className="text-2xl font-extrabold tracking-tight text-heading sm:text-3xl">
            {title}
          </h2>
          {description ? (
            <p className="text-sm leading-relaxed text-foreground/75 sm:text-base">
              {description}
            </p>
          ) : null}
        </div>

        <HomeCardCarousel
          label={title}
          until="sm"
          desktopGridClassName="sm:grid-cols-2"
          slideClassName="w-[min(88vw,22rem)]"
        >
          {picks.map((event, index) => (
            <FeaturedPlacementCard
              key={event.id}
              event={event}
              variant="primary"
              className="h-full w-full"
              analytics={cardAnalytics(event, (index + 1) as 1 | 2)}
              slotLabel={
                showSlotLabels
                  ? index === 0
                    ? "Primary Spotlight"
                    : "Secondary Spotlight"
                  : undefined
              }
            />
          ))}
        </HomeCardCarousel>
      </Container>
    </section>
  );
}

/** @deprecated Prefer PadeyaPicksSection */
export const DiscoveryFeaturedSection = PadeyaPicksSection;
