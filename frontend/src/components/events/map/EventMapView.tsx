"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { EventMap, boundsFromPins } from "@/components/events/map/EventMap";
import { eventMapCardChrome, eventMapPriceClass } from "@/components/events/map/event-map-card-chrome";
import { EventMapList } from "@/components/events/map/EventMapList";
import { MapMobileBottomSheet } from "@/components/events/map/MapMobileBottomSheet";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  fetchMapEvents,
  type MapEventCompact,
} from "@/lib/events-api";
import { eventDiscoveryCoords } from "@/lib/events/marketplace-listing";
import type { MapBounds, MapEventPin, MapLatLng, MapViewport } from "@/lib/maps/types";
import type { MapController } from "@/lib/maps/provider";
import type { EventItem } from "@/lib/types/events";

export type EventMapFilters = {
  city?: string;
  date?: string;
  price?: "any" | "free" | "paid";
  category?: string;
  host?: string;
  lat?: number;
  lng?: number;
  radius_km?: number;
};

const LAGOS: MapLatLng = { lat: 6.5244, lng: 3.3792 };
const DEFAULT_BOUNDS: MapBounds = {
  north: 6.7,
  south: 6.35,
  east: 3.6,
  west: 3.2,
};

function eventItemToPin(event: EventItem): MapEventPin | null {
  const point = eventDiscoveryCoords(event);
  if (!point) return null;
  const free =
    event.ticket_types?.some((t) => Number(t.price) === 0) &&
    event.ticket_types.every((t) => Number(t.price) === 0);
  const prices =
    event.ticket_types
      ?.filter((t) => t.visibility === "public")
      .map((t) => Number(t.price))
      .filter((n) => Number.isFinite(n)) ?? [];
  const min = prices.length ? Math.min(...prices) : null;
  let price_label = "See tickets";
  if (min === 0 || free) price_label = "Free";
  else if (min != null) price_label = `From ₦${Math.round(min).toLocaleString("en-NG")}`;

  return {
    id: event.id,
    slug: event.slug,
    title: event.title,
    banner_url: event.banner_url,
    start_datetime: event.start_datetime,
    end_datetime: event.end_datetime,
    price_label,
    min_price: min,
    is_free: min === 0 || Boolean(free),
    category_name: event.category?.name,
    category_slug: event.category?.slug,
    host_display_name: event.host_display_name,
    public_location_label: event.public_location_label,
    city: event.city,
    area: event.area,
    latitude: String(point.lat),
    longitude: String(point.lng),
    location_visibility: event.location_visibility,
    location_map_mode: event.location_map_mode || (point.approximate ? "approximate" : "exact"),
    location_privacy_message: event.location_privacy_message,
    distance_km: event.distance_km ?? null,
    distance_label: event.distance_label ?? null,
    distance_is_approximate: event.distance_is_approximate ?? point.approximate,
  };
}

function compactToPin(row: MapEventCompact): MapEventPin {
  return { ...row };
}

export function EventMapView({
  seedEvents = [],
  filters,
  userLocation,
  onOpenFilters,
  className = "",
}: {
  /** Client-filtered marketplace events used as optimistic seed / fallback. */
  seedEvents?: EventItem[];
  filters?: EventMapFilters;
  userLocation?: MapLatLng | null;
  onOpenFilters?: () => void;
  className?: string;
}) {
  const seedPins = useMemo(
    () =>
      seedEvents
        .map(eventItemToPin)
        .filter((p): p is MapEventPin => p != null),
    [seedEvents],
  );

  const [pins, setPins] = useState<MapEventPin[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mobilePane, setMobilePane] = useState<"list" | "map">("map");
  const [searchPending, setSearchPending] = useState(false);
  const [bounds, setBounds] = useState<MapBounds>(DEFAULT_BOUNDS);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<MapController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastFetchKey = useRef("");
  const initialFitDone = useRef(false);
  const filtersRef = useRef(filters);
  const seedEventsRef = useRef(seedEvents);
  const seedPinsRef = useRef(seedPins);
  const userLocationRef = useRef(userLocation);

  useEffect(() => {
    filtersRef.current = filters;
    seedEventsRef.current = seedEvents;
    seedPinsRef.current = seedPins;
    userLocationRef.current = userLocation;
  }, [filters, seedEvents, seedPins, userLocation]);

  const center = userLocation ?? LAGOS;
  const displayPins = pins ?? seedPins;

  const selected = useMemo(
    () => displayPins.find((p) => p.id === selectedId) ?? null,
    [displayPins, selectedId],
  );

  async function loadForBounds(next: MapBounds, opts?: { force?: boolean }) {
    const f = filtersRef.current;
    const seeds = seedEventsRef.current;
    const seedPinRows = seedPinsRef.current;
    const loc = userLocationRef.current;
    const key = [
      next.north.toFixed(4),
      next.south.toFixed(4),
      next.east.toFixed(4),
      next.west.toFixed(4),
      f?.city,
      f?.date,
      f?.price,
      f?.category,
      f?.host,
      f?.lat,
      f?.lng,
    ].join("|");
    if (!opts?.force && key === lastFetchKey.current) return;
    lastFetchKey.current = key;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchMapEvents({
        ...next,
        lat: f?.lat ?? loc?.lat,
        lng: f?.lng ?? loc?.lng,
        radius_km: f?.radius_km,
        city: f?.city && f.city !== "all" ? f.city : undefined,
        category: f?.category,
        date: f?.date,
        price: f?.price,
        host: f?.host,
        limit: 120,
      });
      let nextPins = res.items.map(compactToPin);
      if (seeds.length > 0) {
        const allowed = new Set(seeds.map((e) => e.id));
        nextPins = nextPins.filter((p) => allowed.has(p.id));
        const have = new Set(nextPins.map((p) => p.id));
        for (const seed of seedPinRows) {
          if (have.has(seed.id)) continue;
          const lat = Number(seed.latitude);
          const lng = Number(seed.longitude);
          if (
            Number.isFinite(lat) &&
            Number.isFinite(lng) &&
            lat >= next.south &&
            lat <= next.north &&
            lng >= next.west &&
            lng <= next.east
          ) {
            nextPins.push(seed);
          }
        }
      }
      setPins(nextPins);
      setSearchPending(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load map events");
      if (seedPinRows.length) setPins(seedPinRows);
    } finally {
      setLoading(false);
    }
  }

  // Filter-driven refresh (async — avoids sync setState-in-effect).
  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      void loadForBounds(bounds, { force: true });
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- filter-driven refresh
  }, [
    filters?.city,
    filters?.date,
    filters?.price,
    filters?.category,
    filters?.host,
    filters?.lat,
    filters?.lng,
  ]);

  function onViewportIdle(vp: MapViewport) {
    if (!vp.bounds) return;
    setBounds(vp.bounds);
    setSearchPending(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void loadForBounds(vp.bounds!);
    }, 450);
  }

  function searchThisArea() {
    const vp = controllerRef.current?.getViewport();
    if (vp?.bounds) {
      void loadForBounds(vp.bounds, { force: true });
    } else {
      void loadForBounds(bounds, { force: true });
    }
  }

  function useMyLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const next = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        controllerRef.current?.setCenter(next);
        controllerRef.current?.setZoom(13);
      },
      () => {
        /* permission denied — ignore */
      },
      { enableHighAccuracy: false, timeout: 8000 },
    );
  }

  function resetView() {
    const fit = boundsFromPins(displayPins) ?? DEFAULT_BOUNDS;
    controllerRef.current?.fitBounds(fit);
    setSelectedId(null);
  }

  function selectEvent(id: string) {
    setSelectedId(id);
    const pin = displayPins.find((p) => p.id === id);
    if (pin?.latitude && pin.longitude) {
      controllerRef.current?.panTo({
        lat: Number(pin.latitude),
        lng: Number(pin.longitude),
      });
    }
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches) {
      setMobilePane("map");
    }
  }

  function onMapReady(controller: MapController) {
    if (initialFitDone.current) return;
    initialFitDone.current = true;
    const fit = boundsFromPins(seedPins.length ? seedPins : displayPins);
    if (fit) controller.fitBounds(fit);
    else if (userLocation) {
      controller.setCenter(userLocation);
      controller.setZoom(12);
    }
  }

  const mapPane = (
    <div className="relative h-full min-h-[20rem] w-full">
      <EventMap
        events={displayPins}
        selectedId={selectedId}
        center={center}
        onSelect={selectEvent}
        onViewportIdle={onViewportIdle}
        onReady={onMapReady}
        controllerRef={controllerRef}
        className="h-full min-h-[20rem] lg:min-h-[32rem]"
      />

      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex flex-wrap gap-2 p-3">
        <div className="pointer-events-auto flex flex-wrap gap-2">
          {searchPending ? (
            <Button
              type="button"
              size="sm"
              className="min-h-10 shadow-[var(--shadow-strong)]"
              onClick={searchThisArea}
            >
              Search this area
            </Button>
          ) : null}
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="min-h-10 bg-card/95 shadow-[var(--shadow-soft)] backdrop-blur-md"
            onClick={useMyLocation}
          >
            Use my location
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="min-h-10 bg-card/95 shadow-[var(--shadow-soft)] backdrop-blur-md"
            onClick={() => {
              const z = controllerRef.current?.getViewport().zoom ?? 11;
              controllerRef.current?.setZoom(Math.min(18, z + 1));
            }}
          >
            Zoom +
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="min-h-10 bg-card/95 shadow-[var(--shadow-soft)] backdrop-blur-md"
            onClick={() => {
              const z = controllerRef.current?.getViewport().zoom ?? 11;
              controllerRef.current?.setZoom(Math.max(3, z - 1));
            }}
          >
            Zoom −
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="min-h-10 bg-card/95 shadow-[var(--shadow-soft)] backdrop-blur-md"
            onClick={resetView}
          >
            Reset
          </Button>
          {onOpenFilters ? (
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="min-h-10 bg-card/95 shadow-[var(--shadow-soft)] backdrop-blur-md"
              onClick={onOpenFilters}
            >
              Filter
            </Button>
          ) : null}
        </div>
      </div>

      {loading ? (
        <div className="pointer-events-none absolute inset-x-0 top-14 z-10 flex justify-center">
          <span className="rounded-full border border-border bg-card/95 px-3 py-1 text-xs font-semibold text-muted-foreground shadow-[var(--shadow-soft)] backdrop-blur-md">
            Updating map…
          </span>
        </div>
      ) : null}

      <MapMobileBottomSheet
        event={selected}
        open={Boolean(selected) && mobilePane === "map"}
        onClose={() => setSelectedId(null)}
        onSelect={selectEvent}
        className="lg:hidden"
      />

      {/* Optional horizontal cards under map on tablet/mobile */}
      {mobilePane === "map" && displayPins.length > 0 ? (
        <div className="absolute inset-x-0 bottom-[7.5rem] z-10 overflow-x-auto px-3 pb-1 lg:hidden">
          <div className="flex w-max gap-2">
            {displayPins.slice(0, 12).map((pin) => (
              <Link
                key={pin.id}
                href={`/events/${pin.slug}`}
                onClick={() => selectEvent(pin.id)}
                className={cn(
                  eventMapCardChrome({
                    selected: pin.id === selectedId,
                    className:
                      "max-w-[11rem] shrink-0 px-3 py-2 text-left text-xs backdrop-blur-md",
                  }),
                )}
              >
                <p className="truncate font-bold text-heading dark:text-paper">
                  {pin.title}
                </p>
                <p className={cn("truncate", eventMapPriceClass)}>
                  {pin.price_label}
                </p>
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );

  return (
    <div className={cn("space-y-3", className)}>
      {/* Mobile List | Map toggle */}
      <div
        role="group"
        aria-label="Map or list"
        className="inline-flex rounded-[var(--radius-md)] border border-border bg-muted p-0.5 lg:hidden"
      >
        {(["list", "map"] as const).map((pane) => (
          <button
            key={pane}
            type="button"
            aria-pressed={mobilePane === pane}
            onClick={() => setMobilePane(pane)}
            className={cn(
              "min-h-10 rounded-[calc(var(--radius-md)-2px)] px-4 text-xs font-bold capitalize",
              mobilePane === pane
                ? "bg-ink text-accent"
                : "text-muted-foreground",
            )}
          >
            {pane}
          </button>
        ))}
      </div>

      {error ? (
        <p className="text-sm text-danger">
          {error}{" "}
          <Link href="/events" className="underline underline-offset-2">
            View all events
          </Link>
        </p>
      ) : null}

      {/* Desktop split: scrollable list + sticky map */}
      <div className="hidden gap-5 lg:grid lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] xl:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <div className="max-h-[calc(100vh-8rem)] space-y-3 overflow-y-auto overscroll-contain pr-1">
          <EventMapList
            events={displayPins}
            selectedId={selectedId}
            onSelect={selectEvent}
            loading={loading}
          />
        </div>
        <div className="sticky top-24 h-[calc(100vh-8rem)] min-h-[32rem]">
          {mapPane}
        </div>
      </div>

      {/* Mobile / tablet panes */}
      <div className="lg:hidden">
        {mobilePane === "list" ? (
          <EventMapList
            events={displayPins}
            selectedId={selectedId}
            onSelect={selectEvent}
            loading={loading}
          />
        ) : (
          <div className="relative h-[min(70vh,36rem)] w-full overflow-hidden">
            {mapPane}
          </div>
        )}
      </div>
    </div>
  );
}
