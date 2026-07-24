"use client";

import { useEffect, useRef } from "react";

import {
  trackLocationPageView,
  type LocationAnalyticsMeta,
} from "@/lib/analytics";

/**
 * Fires country/state/city/area_page_view once per mount for a location hub.
 */
export function LocationPageViewTracker({
  kind,
  country,
  state,
  city,
  area,
  category,
}: LocationAnalyticsMeta & {
  kind: "country" | "state" | "city" | "area";
}) {
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;
    trackLocationPageView({
      kind,
      country,
      state,
      city,
      area,
      category,
    });
  }, [kind, country, state, city, area, category]);

  return null;
}
