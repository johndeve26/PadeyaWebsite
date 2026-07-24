"use client";

import dynamic from "next/dynamic";

import { EventResultRow } from "@/components/events/marketplace/EventResultRow";
import type { EventMapFilters } from "@/components/events/map/EventMapView";
import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { TaxonomyEventCard } from "@/components/taxonomy/TaxonomyEventCard";
import { Button } from "@/components/ui";
import {
  EVENT_LISTING_CAROUSEL_SLIDE,
  EVENT_LISTING_GRID_MARKETPLACE,
} from "@/lib/discovery/event-listing-layout";
import type { EventsViewMode } from "@/lib/events/marketplace-listing";
import type { MapLatLng } from "@/lib/maps/types";
import type { EventItem } from "@/lib/types/events";

/** Map / calendar stay out of the default marketplace bundle until selected. */
const MarketplaceCalendarView = dynamic(
  () =>
    import("@/components/events/discovery/MarketplaceCalendarView").then(
      (m) => m.MarketplaceCalendarView,
    ),
  {
    ssr: false,
    loading: () => (
      <div
        className="min-h-[28rem] animate-pulse rounded-xl bg-surface-muted"
        aria-hidden
      />
    ),
  },
);

const EventMapView = dynamic(
  () =>
    import("@/components/events/map/EventMapView").then((m) => m.EventMapView),
  {
    ssr: false,
    loading: () => (
      <div
        className="min-h-[28rem] animate-pulse rounded-xl bg-surface-muted"
        aria-hidden
      />
    ),
  },
);

export function EventsResults({
  events,
  view,
  hasMore,
  onShowMore,
  hasLocationFilter = false,
  /** Full filtered set for calendar / map (not paginated). */
  calendarEvents,
  mapFilters,
  userLocation,
  onOpenFilters,
  dateFilterActive = false,
  onClearDateFilter,
}: {
  events: EventItem[];
  view: EventsViewMode;
  hasMore: boolean;
  onShowMore: () => void;
  hasLocationFilter?: boolean;
  calendarEvents?: EventItem[];
  mapFilters?: EventMapFilters;
  userLocation?: MapLatLng | null;
  onOpenFilters?: () => void;
  dateFilterActive?: boolean;
  onClearDateFilter?: () => void;
}) {
  if (view === "calendar") {
    return (
      <MarketplaceCalendarView
        events={calendarEvents ?? events}
        hasLocationFilter={hasLocationFilter}
        dateFilterActive={dateFilterActive}
        onClearDateFilter={onClearDateFilter}
      />
    );
  }

  if (view === "map") {
    return (
      <EventMapView
        seedEvents={calendarEvents ?? events}
        filters={mapFilters}
        userLocation={userLocation}
        onOpenFilters={onOpenFilters}
      />
    );
  }

  return (
    <div className="space-y-5">
      {view === "grid" ? (
        <HomeCardCarousel
          label="Events"
          until="sm"
          desktopGridClassName={EVENT_LISTING_GRID_MARKETPLACE}
          slideClassName={EVENT_LISTING_CAROUSEL_SLIDE}
        >
          {events.map((event, index) => (
            <div
              key={event.id}
              className="padeya-section-enter min-w-0 h-full"
              style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
            >
              <TaxonomyEventCard event={event} />
            </div>
          ))}
        </HomeCardCarousel>
      ) : null}

      {view === "list" ? (
        <div className="space-y-3">
          {events.map((event) => (
            <EventResultRow key={event.id} event={event} />
          ))}
        </div>
      ) : null}

      {hasMore ? (
        <div className="flex justify-center pt-2">
          <Button type="button" variant="secondary" onClick={onShowMore}>
            Show more
          </Button>
        </div>
      ) : null}
    </div>
  );
}
