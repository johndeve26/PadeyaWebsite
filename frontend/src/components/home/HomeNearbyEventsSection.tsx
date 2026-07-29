"use client";

import Link from "next/link";
import { useState } from "react";

import { FeaturedEvents } from "@/components/home/FeaturedEvents";
import { Button, Container, SectionHeader } from "@/components/ui";
import { readStoredDiscoveryLocation } from "@/lib/discovery/geo-location";
import { DEFAULT_DISCOVERY_CITY } from "@/lib/discovery/default-market";
import type { EventItem } from "@/lib/types/events";

function buildViewAllHref(nearby: boolean): string {
  if (!nearby) return "/events";
  const location = readStoredDiscoveryLocation();
  if (!location) return "/events?near=1";
  const params = new URLSearchParams({
    lat: String(location.lat),
    lng: String(location.lng),
    radius: String(location.radiusKm),
    location_label: location.label,
  });
  return `/events?${params.toString()}`;
}

/**
 * Homepage discovery block — SSR defaults first; nearby only after consent.
 * Declined geo keeps popular/default events (never empty/broken).
 */
export function HomeNearbyEventsSection({
  initialEvents = null,
  defaultCityLabel,
}: {
  initialEvents?: EventItem[] | null;
  defaultCityLabel?: string;
} = {}) {
  const [mode, setMode] = useState<"nearby" | "trending" | "declined">(
    "trending",
  );
  const viewAllHref = buildViewAllHref(mode === "nearby");

  const title =
    mode === "nearby"
      ? "Events around you"
      : mode === "declined"
        ? `Popular events${defaultCityLabel ? ` in ${defaultCityLabel}` : ""}`
        : "Events around you";

  const eyebrow =
    mode === "nearby" ? "Near you" : mode === "declined" ? "Popular" : "Near you";

  return (
    <section className="bg-background py-10 sm:py-12">
      <Container className="space-y-5 sm:space-y-6">
        <SectionHeader
          variant="display"
          eyebrow={eyebrow}
          title={title}
          action={
            <Link href={viewAllHref} className="hidden sm:inline-flex">
              <Button variant="primary" size="lg">
                View all events
              </Button>
            </Link>
          }
        />
        <FeaturedEvents
          initialEvents={initialEvents}
          defaultCityLabel={defaultCityLabel}
          defaultCityLat={DEFAULT_DISCOVERY_CITY.lat}
          defaultCityLng={DEFAULT_DISCOVERY_CITY.lng}
          onModeChange={setMode}
        />
        <div className="sm:hidden">
          <Link href={viewAllHref} className="block w-full">
            <Button variant="primary" size="lg" className="w-full">
              View all events
            </Button>
          </Link>
        </div>
      </Container>
    </section>
  );
}
