"use client";

import { useSyncExternalStore } from "react";

import { EVENTS_LG_MEDIA_QUERY } from "@/lib/events/marketplace-listing";

function subscribe(onStoreChange: () => void) {
  const mq = window.matchMedia(EVENTS_LG_MEDIA_QUERY);
  mq.addEventListener("change", onStoreChange);
  return () => mq.removeEventListener("change", onStoreChange);
}

function getSnapshot() {
  return window.matchMedia(EVENTS_LG_MEDIA_QUERY).matches;
}

function getServerSnapshot() {
  return false;
}

/** True at Tailwind `lg` (1024px+) — matches clampEventsViewForViewport. */
export function useEventsLgUp(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
