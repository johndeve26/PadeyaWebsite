"use client";

import { useEffect, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";

import { trackPageView } from "@/lib/analytics";

/**
 * Track a page view once per path (+ optional event scope) for the session window.
 * Safe to call from layouts or page shells — never blocks render.
 */
export function useTrackPageView(opts?: {
  targetEventId?: string;
  hostId?: string;
  trackedAction?: string;
  /** When false, skip tracking (e.g. still loading). Default true. */
  enabled?: boolean;
}): void {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const lastKey = useRef<string | null>(null);
  const enabled = opts?.enabled !== false;

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;
    const search = searchParams?.toString() ?? "";
    const path = search ? `${pathname}?${search}` : pathname;
    const key = `${path}|${opts?.targetEventId ?? ""}|${opts?.trackedAction ?? ""}`;
    if (lastKey.current === key) return;
    lastKey.current = key;
    trackPageView({
      path: pathname,
      targetEventId: opts?.targetEventId,
      hostId: opts?.hostId,
      trackedAction: opts?.trackedAction,
    });
  }, [
    enabled,
    pathname,
    searchParams,
    opts?.targetEventId,
    opts?.hostId,
    opts?.trackedAction,
  ]);
}
