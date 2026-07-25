"use client";

import { useUnreadRealtime } from "@/hooks/useUnreadRealtime";

/** Unread badge count (WebSocket + HTTP polling fallback). */
export function useUnreadMessages(enabled = true): number {
  const { count } = useUnreadRealtime(enabled);
  return count;
}

export { useUnreadRealtime } from "@/hooks/useUnreadRealtime";
