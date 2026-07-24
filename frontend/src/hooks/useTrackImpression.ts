"use client";

import { useEffect, useRef, type RefObject } from "react";

import {
  IMPRESSION_THRESHOLD,
  trackEventCardImpression,
  type ListContext,
} from "@/lib/analytics";

export type UseTrackImpressionOptions = {
  targetEventId: string;
  hostId?: string;
  listContext: ListContext;
  cardPosition?: number;
  enabled?: boolean;
  /** When false, skip event_card_impression and only run onImpression. Default true. */
  trackCardImpression?: boolean;
  /** Override default 0.5 */
  visibleRatio?: number;
  /** Override default 500ms */
  dwellMs?: number;
  onImpression?: () => void;
};

/**
 * Fire an impression when the element is ≥50% visible for ≥500ms.
 * Deduped per event/list/session via analytics.ts.
 */
export function useTrackImpression<T extends Element = HTMLElement>(
  options: UseTrackImpressionOptions,
): RefObject<T | null> {
  const ref = useRef<T | null>(null);
  const firedRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onImpressionRef = useRef(options.onImpression);

  useEffect(() => {
    onImpressionRef.current = options.onImpression;
  }, [options.onImpression]);

  useEffect(() => {
    firedRef.current = false;
  }, [options.targetEventId, options.listContext]);

  const {
    enabled = true,
    targetEventId,
    hostId,
    listContext,
    cardPosition,
    trackCardImpression = true,
    visibleRatio = IMPRESSION_THRESHOLD.ratio,
    dwellMs = IMPRESSION_THRESHOLD.dwellMs,
  } = options;

  useEffect(() => {
    const el = ref.current;

    if (!enabled || !el || typeof IntersectionObserver === "undefined") {
      return;
    }

    const clearTimer = () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;
        if (firedRef.current) return;

        if (entry.isIntersecting && entry.intersectionRatio >= visibleRatio) {
          if (timerRef.current) return;
          timerRef.current = setTimeout(() => {
            if (firedRef.current) return;
            firedRef.current = true;
            if (trackCardImpression) {
              trackEventCardImpression({
                targetEventId,
                hostId,
                listContext,
                cardPosition,
              });
            }
            onImpressionRef.current?.();
            clearTimer();
            observer.disconnect();
          }, dwellMs);
        } else {
          clearTimer();
        }
      },
      { threshold: [0, visibleRatio, 1] },
    );

    observer.observe(el);
    return () => {
      clearTimer();
      observer.disconnect();
    };
  }, [
    enabled,
    targetEventId,
    hostId,
    listContext,
    cardPosition,
    trackCardImpression,
    visibleRatio,
    dwellMs,
  ]);

  return ref;
}
