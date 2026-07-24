"use client";

import { useUnreadRealtime } from "@/hooks/useUnreadRealtime";

/** Unread badge count (WebSocket + HTTP polling fallback). */
export function useUnreadMessages(): number {
  const { count } = useUnreadRealtime();
  return count;
}

export { useUnreadRealtime } from "@/hooks/useUnreadRealtime";
