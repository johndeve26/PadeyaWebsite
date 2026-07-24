"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useMessageSocket } from "@/hooks/useMessageSocket";
import { fetchUnreadCount } from "@/lib/messaging-api";
import type {
  MessagingSocketEvent,
  SocketConnectionStatus,
} from "@/lib/messaging/socket-types";

const POLL_LIVE_MS = 90_000;
const POLL_FALLBACK_MS = 20_000;

/**
 * Instant unread badge via WebSocket, with HTTP polling fallback when offline.
 */
export function useUnreadRealtime(enabled = true): {
  count: number;
  status: SocketConnectionStatus;
  refresh: () => Promise<void>;
} {
  const { user } = useAuth();
  const [count, setCount] = useState(0);

  const refresh = useCallback(async () => {
    if (!user || !enabled) return;
    try {
      setCount(await fetchUnreadCount());
    } catch {
      // keep last known count
    }
  }, [user, enabled]);

  const onEvent = useCallback(
    (event: MessagingSocketEvent) => {
      if (event.type === "thread.unread_count_updated") {
        setCount(Math.max(0, event.unread_count));
        return;
      }
      if (
        event.type === "message.created" ||
        event.type === "message.read" ||
        event.type === "thread.updated"
      ) {
        void refresh();
      }
    },
    [refresh],
  );

  const { status, isLive } = useMessageSocket(
    enabled && user ? onEvent : undefined,
    Boolean(enabled && user),
  );

  useEffect(() => {
    if (!user || !enabled) return;
    let alive = true;
    queueMicrotask(() => {
      if (alive) void refresh();
    });
    const interval = window.setInterval(
      () => {
        void refresh();
      },
      isLive ? POLL_LIVE_MS : POLL_FALLBACK_MS,
    );
    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, [user, enabled, isLive, refresh]);

  return {
    count: user && enabled ? count : 0,
    status: user && enabled ? status : "offline",
    refresh,
  };
}
