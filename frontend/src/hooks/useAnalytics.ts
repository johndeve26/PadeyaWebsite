"use client";

import { useCallback } from "react";

import {
  flushAnalytics,
  track,
  trackBuyTicketClick,
  trackCheckoutAbandoned,
  trackCheckoutPageView,
  trackCheckoutPaymentStarted,
  trackEventCardClick,
  trackEventCardImpression,
  trackFollowHostClick,
  trackHostProfileClick,
  trackLegacyClick,
  trackPageView,
  trackPromoCodeEntered,
  trackPromoCodeResult,
  trackRefundPolicyView,
  trackSaveEventClick,
  trackShareClick,
  trackTicketPanelView,
  trackTicketTypeImpression,
  trackTicketTypeSelected,
  trackVaultClick,
  type ListContext,
  type TrackOptions,
} from "@/lib/analytics";
import type { TrackedActionName } from "@/lib/analytics-taxonomy";

/** Stable fire-and-forget analytics helpers for client components. */
export function useAnalytics() {
  const trackAction = useCallback(
    (action: TrackedActionName | string, options?: TrackOptions) => {
      track(action, options);
    },
    [],
  );

  return {
    track: trackAction,
    flush: flushAnalytics,
    trackPageView,
    trackEventCardImpression,
    trackEventCardClick,
    trackBuyTicketClick,
    trackShareClick,
    trackFollowHostClick,
    trackSaveEventClick,
    trackLegacyClick,
    trackVaultClick,
    trackHostProfileClick,
    trackTicketPanelView,
    trackTicketTypeImpression,
    trackTicketTypeSelected,
    trackRefundPolicyView,
    trackCheckoutPageView,
    trackPromoCodeEntered,
    trackPromoCodeResult,
    trackCheckoutPaymentStarted,
    trackCheckoutAbandoned,
  };
}

export type { ListContext };
