"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { useMessageSocket } from "@/hooks/useMessageSocket";
import { apiRequest } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/storage";
import type { MessagingSocketEvent } from "@/lib/messaging/socket-types";

const POLL_LIVE_MS = 90_000;
const POLL_FALLBACK_MS = 30_000;

/**
 * In-app notification unread count (independent of browser push).
 * WebSocket `notification.created` + HTTP fallback.
 */
export function useUnreadNotifications(enabled = true): number {
  const { user } = useAuth();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);
  const active = Boolean(enabled && user);

  const refresh = useCallback(async () => {
    if (!active || !getAccessToken()) {
      setUnread(0);
      return;
    }
    try {
      const data = await apiRequest<{ unread_count: number }>(
        "/notifications/unread-count",
      );
      setUnread(data.unread_count || 0);
    } catch {
      /* keep last */
    }
  }, [active]);

  const onEvent = useCallback(
    (event: MessagingSocketEvent) => {
      if (event.type === "notification.created") {
        if (typeof event.unread_count === "number") {
          setUnread(Math.max(0, event.unread_count));
        } else {
          void refresh();
        }
      }
    },
    [refresh],
  );

  const { isLive } = useMessageSocket(
    active ? onEvent : undefined,
    active,
  );

  useEffect(() => {
    if (!active) {
      setUnread(0);
      return;
    }
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void refresh();
    });
    const id = window.setInterval(
      () => void refresh(),
      isLive ? POLL_LIVE_MS : POLL_FALLBACK_MS,
    );
    const onChanged = () => void refresh();
    window.addEventListener("padeya:notifications-changed", onChanged);
    return () => {
      cancelled = true;
      window.removeEventListener("padeya:notifications-changed", onChanged);
      window.clearInterval(id);
    };
  }, [active, isLive, refresh, pathname]);

  return active ? unread : 0;
}
