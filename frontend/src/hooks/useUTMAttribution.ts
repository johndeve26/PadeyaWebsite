"use client";

import { useSyncExternalStore } from "react";

import {
  captureUtmAttribution,
  readUtmAttribution,
} from "@/lib/analytics";

export type UtmAttribution = {
  source?: string;
  medium?: string;
  campaign?: string;
  term?: string;
  content?: string;
  landingPage?: string;
  capturedAt: string;
};

let cachedClient: UtmAttribution | null | undefined;

function subscribeNoop() {
  return () => {};
}

function getClientSnapshot(): UtmAttribution | null {
  if (cachedClient !== undefined) return cachedClient;
  try {
    cachedClient = captureUtmAttribution();
  } catch {
    cachedClient = readUtmAttribution();
  }
  return cachedClient;
}

function getServerSnapshot(): UtmAttribution | null {
  return null;
}

/** Capture UTM on the client and expose session-persisted attribution. */
export function useUTMAttribution(): UtmAttribution | null {
  return useSyncExternalStore(subscribeNoop, getClientSnapshot, getServerSnapshot);
}
