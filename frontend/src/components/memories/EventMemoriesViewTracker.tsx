"use client";

import { useEffect } from "react";

import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";

export function EventMemoriesViewTracker({ eventId }: { eventId: string }) {
  useEffect(() => {
    track(TrackedAction.EVENT_MEMORIES_VIEW, { targetEventId: eventId });
  }, [eventId]);
  return null;
}
