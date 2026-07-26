"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PlacesAutocompleteInput } from "@/components/events/PlacesAutocompleteInput";
import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import {
  Button,
  EmptyState,
  EventCard,
  SkeletonCard,
} from "@/components/ui";
import { useDiscoveryLocation } from "@/hooks/useDiscoveryLocation";
import { DEFAULT_DISCOVERY_CITY } from "@/lib/discovery/default-market";
import { GEO_DECLINED_COPY } from "@/lib/discovery/geo-session";
import { readStoredDiscoveryLocation } from "@/lib/discovery/geo-location";
import type { PlaceSelection } from "@/lib/google-maps";
import { HOMEPAGE_EVENT_LIMIT } from "@/lib/home/diversify-events";
import { fetchNearbyEvents } from "@/lib/events-api";
import {
  enrichMarketplaceEventsWithDistance,
  sortMarketplaceByProximity,
} from "@/lib/events/marketplace-listing";
import type { EventItem } from "@/lib/types/events";

type NearbyMode = "default" | "nearby" | "loading" | "declined";

export function FeaturedEvents({
  initialEvents = null,
  defaultCityLabel,
  defaultCityLat = DEFAULT_DISCOVERY_CITY.lat,
  defaultCityLng = DEFAULT_DISCOVERY_CITY.lng,
  onModeChange,
}: {
  /** SSR/cached featured or default-city events — shown immediately. */
  initialEvents?: EventItem[] | null;
  defaultCityLabel?: string;
  defaultCityLat?: number;
  defaultCityLng?: number;
  onModeChange?: (mode: "nearby" | "trending" | "declined") => void;
} = {}) {
  const {
    location,
    busy: locBusy,
    hydrated,
    declined,
    requestNearMe,
    autoLocateIfAllowed,
    setManual,
    setError: setLocError,
    noteDeclined,
  } = useDiscoveryLocation();

  const fallbackEvents = useMemo(() => initialEvents ?? [], [initialEvents]);

  const proximitySortedFallback = useMemo(
    () =>
      sortMarketplaceByProximity(
        enrichMarketplaceEventsWithDistance(
          fallbackEvents,
          defaultCityLat,
          defaultCityLng,
        ),
      ).slice(0, HOMEPAGE_EVENT_LIMIT),
    [fallbackEvents, defaultCityLat, defaultCityLng],
  );

  const [events, setEvents] = useState<EventItem[] | null>(
    fallbackEvents.length ? proximitySortedFallback : null,
  );
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<NearbyMode>("default");
  const [chooseCityOpen, setChooseCityOpen] = useState(false);
  const locateStarted = useRef(false);

  const applyProximitySortedFallback = useCallback(
    (lat: number, lng: number, nextMode: NearbyMode) => {
      const sorted = sortMarketplaceByProximity(
        enrichMarketplaceEventsWithDistance(fallbackEvents, lat, lng),
      ).slice(0, HOMEPAGE_EVENT_LIMIT);
      setEvents(sorted);
      setMode(nextMode === "declined" ? "declined" : "nearby");
      onModeChange?.(nextMode === "declined" ? "declined" : "nearby");
    },
    [fallbackEvents, onModeChange],
  );

  const loadNearby = useCallback(
    async (lat: number, lng: number, radiusKm: number, label?: string) => {
      setError(null);
      setMode("loading");
      onModeChange?.("nearby");
      try {
        const res = await fetchNearbyEvents({
          lat,
          lng,
          radius_km: radiusKm,
          limit: HOMEPAGE_EVENT_LIMIT,
          location_label: label,
        });
        let next = sortMarketplaceByProximity([...res.items]).slice(
          0,
          HOMEPAGE_EVENT_LIMIT,
        );

        if (next.length < HOMEPAGE_EVENT_LIMIT && fallbackEvents.length) {
          const seen = new Set(next.map((e) => e.id));
          const fill = enrichMarketplaceEventsWithDistance(
            fallbackEvents.filter((e) => !seen.has(e.id)),
            lat,
            lng,
          );
          next = sortMarketplaceByProximity([...next, ...fill]).slice(
            0,
            HOMEPAGE_EVENT_LIMIT,
          );
        }

        if (next.length === 0) {
          applyProximitySortedFallback(lat, lng, "nearby");
          return;
        }
        setEvents(next);
        setMode("nearby");
        onModeChange?.("nearby");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Nearby search failed");
        applyProximitySortedFallback(
          lat,
          lng,
          declined ? "declined" : "nearby",
        );
      }
    },
    [fallbackEvents, onModeChange, applyProximitySortedFallback, declined],
  );

  const loadNearbyFromDefaultMarket = useCallback(async () => {
    const label = defaultCityLabel || DEFAULT_DISCOVERY_CITY.label;
    await loadNearby(defaultCityLat, defaultCityLng, 50, `Around ${label}`);
  }, [defaultCityLabel, defaultCityLat, defaultCityLng, loadNearby]);

  // Geo-first without unsolicited prompts: stored → silent if already granted → default market.
  // Browser permission UI only via explicit "Show events near me".
  useEffect(() => {
    if (!hydrated || locateStarted.current) return;
    locateStarted.current = true;
    const t = window.setTimeout(() => {
      void (async () => {
        if (declined) {
          applyProximitySortedFallback(
            defaultCityLat,
            defaultCityLng,
            "declined",
          );
          return;
        }
        const stored = readStoredDiscoveryLocation();
        if (stored) {
          await loadNearby(
            stored.lat,
            stored.lng,
            stored.radiusKm,
            stored.label,
          );
          return;
        }
        const found = await autoLocateIfAllowed();
        if (found) {
          await loadNearby(found.lat, found.lng, found.radiusKm, found.label);
          return;
        }
        await loadNearbyFromDefaultMarket();
      })();
    }, 0);
    return () => window.clearTimeout(t);
  }, [
    hydrated,
    declined,
    autoLocateIfAllowed,
    loadNearby,
    loadNearbyFromDefaultMarket,
    applyProximitySortedFallback,
    defaultCityLat,
    defaultCityLng,
  ]);

  async function handleUseLocation() {
    if (declined) return;
    setLocError(null);
    setError(null);
    setMode("loading");
    try {
      await requestNearMe();
      const stored = readStoredDiscoveryLocation();
      if (stored) {
        await loadNearby(
          stored.lat,
          stored.lng,
          stored.radiusKm,
          stored.label,
        );
      } else {
        await loadNearbyFromDefaultMarket();
      }
    } catch {
      noteDeclined();
      applyProximitySortedFallback(
        defaultCityLat,
        defaultCityLng,
        "declined",
      );
    }
  }

  function handlePlace(place: PlaceSelection) {
    const lat = Number(place.latitude);
    const lng = Number(place.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
    const label =
      place.cityHint || place.name || place.formattedAddress || "Selected city";
    setManual({ lat, lng, label });
    setChooseCityOpen(false);
    void loadNearby(lat, lng, 25, label);
  }

  const displayEvents = events ?? proximitySortedFallback;
  const showCta =
    mode === "default" &&
    !location &&
    !declined &&
    displayEvents.length > 0 &&
    !locBusy;
  const showDeclinedHelp = mode === "declined" || declined;

  return (
    <div className="space-y-5">
      {showCta ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <Button
            type="button"
            size="md"
            onClick={() => void handleUseLocation()}
            disabled={locBusy}
          >
            {locBusy ? "Finding events near you…" : "Show events near me"}
          </Button>
          <Button
            type="button"
            size="md"
            variant="secondary"
            onClick={() => setChooseCityOpen((v) => !v)}
          >
            {GEO_DECLINED_COPY.chooseCityCta}
          </Button>
          <p className="text-sm text-muted-foreground">
            Optional. We only use location to sort by distance.
          </p>
        </div>
      ) : null}

      {showDeclinedHelp && mode !== "nearby" ? (
        <div className="space-y-3 rounded-[var(--radius-lg)] border border-border bg-muted/40 px-4 py-3">
          <p className="text-sm font-semibold text-foreground">
            {GEO_DECLINED_COPY.eyebrow}
          </p>
          <p className="text-sm text-muted-foreground">
            {GEO_DECLINED_COPY.message}
          </p>
          <p className="text-sm text-muted-foreground">
            {GEO_DECLINED_COPY.chooseCity}
          </p>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => setChooseCityOpen(true)}
            >
              {GEO_DECLINED_COPY.chooseCityCta}
            </Button>
            <Link href="/events">
              <Button type="button" size="sm" variant="ghost">
                {GEO_DECLINED_COPY.browseAll}
              </Button>
            </Link>
            <Link href="/events/this-weekend">
              <Button type="button" size="sm" variant="ghost">
                {GEO_DECLINED_COPY.thisWeekend}
              </Button>
            </Link>
            <Link href="/events?view=grid">
              <Button type="button" size="sm" variant="ghost">
                {GEO_DECLINED_COPY.useSearch}
              </Button>
            </Link>
          </div>
          <p className="text-xs text-muted-foreground">
            {GEO_DECLINED_COPY.browsePicks}
            {defaultCityLabel ? ` · Popular in ${defaultCityLabel}` : null}
          </p>
        </div>
      ) : null}

      {chooseCityOpen ? (
        <PlacesAutocompleteInput
          label="Choose your city"
          hint="Browse events around a city without sharing precise GPS."
          types={["(cities)"]}
          onPlaceSelected={handlePlace}
        />
      ) : null}

      {mode === "loading" && !displayEvents.length ? (
        <HomeCardCarousel
          label="Finding events near you"
          until="sm"
          desktopGridClassName="sm:grid-cols-2 lg:grid-cols-4"
          slideClassName="w-[min(82vw,19.5rem)]"
        >
          {Array.from({ length: HOMEPAGE_EVENT_LIMIT }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </HomeCardCarousel>
      ) : displayEvents.length === 0 ? (
        <EmptyState
          title="No published events yet"
          description={
            error ||
            "When hosts publish, verified upcoming shows will appear here."
          }
          action={
            <Link href="/events">
              <Button size="sm">{GEO_DECLINED_COPY.browseAll}</Button>
            </Link>
          }
        />
      ) : (
        <HomeCardCarousel
          label={
            mode === "nearby" || mode === "loading"
              ? "Events around you"
              : "Popular events"
          }
          until="sm"
          desktopGridClassName="sm:grid-cols-2 lg:grid-cols-4"
          slideClassName="w-[min(82vw,19.5rem)]"
        >
          {displayEvents.map((event, index) => (
            <EventCard
              key={event.id}
              event={event}
              className="h-full"
              listContext={
                mode === "nearby" ? "homepage_nearby" : "homepage_featured"
              }
              cardPosition={index}
            />
          ))}
        </HomeCardCarousel>
      )}
    </div>
  );
}
