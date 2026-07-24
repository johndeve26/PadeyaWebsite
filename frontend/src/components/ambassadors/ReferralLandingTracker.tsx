"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef } from "react";

import { readAmbassadorCodeFromSearchParams } from "@/lib/ambassador-referral";
import { trackAmbassadorReferralLanding } from "@/lib/referral-click-track";

/**
 * Records Ambassador referral clicks on landing pages that are not an event
 * detail (e.g. `/` or `/events?ref=` for host-wide partners).
 */
function ReferralLandingTrackerInner() {
  const searchParams = useSearchParams();
  const tracked = useRef<string | null>(null);
  const code = readAmbassadorCodeFromSearchParams(searchParams);

  useEffect(() => {
    if (!code) return;
    const landing =
      typeof window !== "undefined"
        ? `${window.location.pathname}${window.location.search}`
        : undefined;
    const key = `${code}:${landing || ""}`;
    if (tracked.current === key) return;
    tracked.current = key;
    void trackAmbassadorReferralLanding({
      referral_code: code,
      landing_path: landing,
      source: "host_page",
    });
  }, [code]);

  return null;
}

export function ReferralLandingTracker() {
  return (
    <Suspense fallback={null}>
      <ReferralLandingTrackerInner />
    </Suspense>
  );
}
