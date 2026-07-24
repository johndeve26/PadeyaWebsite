"use client";

import { useCallback, useState } from "react";

import {
  clearStoredDiscoveryLocation,
  type DiscoveryLocation,
  type NearbyRadiusKm,
  queryGeolocationPermission,
  readStoredDiscoveryLocation,
  requestBrowserGeolocation,
  storeDiscoveryLocation,
} from "@/lib/discovery/geo-location";
import {
  clearGeoDeclinedSession,
  markGeoDeclinedSession,
  readGeoDeclinedSession,
} from "@/lib/discovery/geo-session";

/**
 * One-time / remembered discovery location for nearby search.
 * Does not upload coords to the server except as query params on nearby fetch.
 * Declined permission is session-sticky — we never re-prompt that session.
 */
export function useDiscoveryLocation() {
  const [location, setLocation] = useState<DiscoveryLocation | null>(() =>
    typeof window === "undefined" ? null : readStoredDiscoveryLocation(),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [declined, setDeclined] = useState(() =>
    typeof window === "undefined" ? false : readGeoDeclinedSession(),
  );
  const hydrated = true;

  const applyLocation = useCallback((next: DiscoveryLocation) => {
    storeDiscoveryLocation(next);
    clearGeoDeclinedSession();
    setDeclined(false);
    setLocation(next);
    setError(null);
  }, []);

  const clearLocation = useCallback(() => {
    clearStoredDiscoveryLocation();
    setLocation(null);
    setError(null);
  }, []);

  const noteDeclined = useCallback(() => {
    markGeoDeclinedSession();
    setDeclined(true);
    setError(null);
  }, []);

  const requestNearMe = useCallback(async () => {
    if (readGeoDeclinedSession()) {
      setDeclined(true);
      setError(null);
      throw new Error("Location permission declined this session.");
    }
    setBusy(true);
    setError(null);
    try {
      const coords = await requestBrowserGeolocation();
      const previous = readStoredDiscoveryLocation();
      applyLocation({
        lat: coords.lat,
        lng: coords.lng,
        label: "Near you",
        radiusKm: previous?.radiusKm ?? 25,
        source: "geo",
        savedAt: Date.now(),
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : "Location unavailable";
      if (/denied/i.test(message)) {
        noteDeclined();
      } else {
        setError(message);
      }
      throw e;
    } finally {
      setBusy(false);
    }
  }, [applyLocation, noteDeclined]);

  /**
   * Homepage-friendly locate: reuse stored coords, or silently refresh GPS
   * only when the browser already granted geolocation. Never prompts.
   * Skips entirely if the user declined this session.
   */
  const autoLocateIfAllowed = useCallback(async (): Promise<DiscoveryLocation | null> => {
    if (readGeoDeclinedSession()) {
      setDeclined(true);
      return null;
    }

    const stored = readStoredDiscoveryLocation();
    if (stored) {
      setLocation(stored);
      setError(null);
      return stored;
    }

    const permission = await queryGeolocationPermission();
    if (permission === "denied") {
      noteDeclined();
      return null;
    }
    if (permission !== "granted") {
      return null;
    }

    setBusy(true);
    setError(null);
    try {
      const coords = await requestBrowserGeolocation();
      const next: DiscoveryLocation = {
        lat: coords.lat,
        lng: coords.lng,
        label: "Near you",
        radiusKm: 25,
        source: "geo",
        savedAt: Date.now(),
      };
      applyLocation(next);
      return next;
    } catch (e) {
      const message = e instanceof Error ? e.message : "";
      if (/denied/i.test(message)) {
        noteDeclined();
      } else {
        setError(null);
      }
      return null;
    } finally {
      setBusy(false);
    }
  }, [applyLocation, noteDeclined]);

  const setManual = useCallback(
    (opts: {
      lat: number;
      lng: number;
      label: string;
      radiusKm?: NearbyRadiusKm;
    }) => {
      const previous = readStoredDiscoveryLocation();
      applyLocation({
        lat: opts.lat,
        lng: opts.lng,
        label: opts.label,
        radiusKm: opts.radiusKm ?? previous?.radiusKm ?? 25,
        source: "manual",
        savedAt: Date.now(),
      });
    },
    [applyLocation],
  );

  const setRadius = useCallback(
    (radiusKm: NearbyRadiusKm) => {
      const current = readStoredDiscoveryLocation();
      if (!current) return;
      applyLocation({ ...current, radiusKm });
    },
    [applyLocation],
  );

  return {
    location,
    busy,
    error,
    declined,
    hydrated,
    requestNearMe,
    autoLocateIfAllowed,
    setManual,
    setRadius,
    clearLocation,
    setError,
    noteDeclined,
  };
}
