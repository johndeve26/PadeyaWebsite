"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { useMessageSocket } from "@/hooks/useMessageSocket";
import { apiRequest } from "@/lib/api";
import type { MessagingSocketEvent } from "@/lib/messaging/socket-types";

const POLL_LIVE_MS = 90_000;
const POLL_FALLBACK_MS = 30_000;

/**
 * In-app notification unread count (independent of browser push).
 * WebSocket `notification.created` + HTTP fallback.
 */
export function useUnreadNotifications(): number {
  const { user } = useAuth();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(async () => {
    if (!user) {
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
  }, [user]);

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

  const { isLive } = useMessageSocket(user ? onEvent : undefined, Boolean(user));

  useEffect(() => {
    if (!user) return;
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
  }, [user, isLive, refresh, pathname]);

  return user ? unread : 0;
}
