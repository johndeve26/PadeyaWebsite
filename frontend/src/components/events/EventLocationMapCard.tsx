"use client";

import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import { MapPreviewCard } from "@/components/events/MapPreviewCard";
import { eventMapMode } from "@/lib/event-maps";
import {
  canShowOnlineEventUrl,
  formatPublicVenueDetail,
} from "@/lib/event-privacy";
import type { EventItem } from "@/lib/types/events";

function MapPlaceholder({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="relative flex min-h-[180px] flex-col justify-center overflow-hidden rounded-[var(--radius-xl)] border border-dashed border-border-strong/40 bg-surface-inset px-5 py-8 text-center">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35] dark:opacity-[0.45]"
        style={{
          backgroundImage:
            "linear-gradient(to right, var(--border) 1px, transparent 1px), linear-gradient(to bottom, var(--border) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />
      <div className="relative space-y-2">
        <p className="text-sm font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
          {eyebrow}
        </p>
        <p className="text-base font-semibold text-heading">{title}</p>
        <p className="mx-auto max-w-md text-sm leading-relaxed text-body">
          {description}
        </p>
      </div>
    </div>
  );
}

export function EventLocationMapCard({ event }: { event: EventItem }) {
  const mode = eventMapMode(event);
  const venueLine = formatPublicVenueDetail(event);
  const privacyNote = event.location_privacy_message;
  const showOnline = canShowOnlineEventUrl(event);
  const lat = event.map_latitude;
  const lng = event.map_longitude;

  return (
    <EventDetailPanel title="Location">
      <div className="space-y-4">
        {mode === "none" ? (
          <MapPlaceholder
            eyebrow="Online event"
            title={
              event.map_label || event.public_location_label || "Online Event"
            }
            description={
              privacyNote ||
              "No physical venue map. Join details follow your ticket and reveal rules."
            }
          />
        ) : lat && lng && (mode === "exact" || mode === "approximate") ? (
          <MapPreviewCard
            latitude={lat}
            longitude={lng}
            mode={mode}
            label={event.map_label || venueLine}
            openUrl={event.map_open_url}
          />
        ) : (
          <MapPlaceholder
            eyebrow="Map unavailable"
            title={venueLine || "Location TBA"}
            description={
              privacyNote ||
              "Coordinates are not published for this event yet."
            }
          />
        )}

        <div className="space-y-2">
          <p className="text-base font-extrabold text-foreground">
            {venueLine || event.public_location_label || "Location TBA"}
          </p>
          {event.public_location_label &&
          venueLine &&
          event.public_location_label !== venueLine ? (
            <p className="text-sm text-muted-foreground">{event.public_location_label}</p>
          ) : null}
          {privacyNote ? (
            <p className="text-sm font-medium text-foreground">{privacyNote}</p>
          ) : null}
          {mode === "approximate" ? (
            <p className="text-xs leading-relaxed text-muted-foreground">
              Approximate area for guests. Exact venue address is not shown on this
              public page.
            </p>
          ) : null}
          {showOnline && event.online_event_url ? (
            <p className="text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">Online:</span>{" "}
              <a
                href={event.online_event_url}
                className="underline decoration-accent underline-offset-2"
                target="_blank"
                rel="noreferrer"
              >
                Join link
              </a>
            </p>
          ) : null}
        </div>
      </div>
    </EventDetailPanel>
  );
}
