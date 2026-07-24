"use client";

import { useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { useToast } from "@/components/ui";
import { useMessageSocket } from "@/hooks/useMessageSocket";
import {
  ackPopupNotifications,
  fetchPopupNotifications,
  type InAppNotification,
} from "@/lib/notifications-api";
import { safeToastActionHref, safeToastCopy, isMessageInboxNotificationKind } from "@/lib/notifications-toast";
import { playInAppNotificationSound } from "@/lib/ui-sounds";
import type { MessagingSocketEvent } from "@/lib/messaging/socket-types";

const POLL_LIVE_MS = 45_000;
const POLL_FALLBACK_MS = 12_000;
const HIDDEN_POLL_MS = 90_000;

/**
 * In-app popup toasts — prefers WebSocket `notification.created`,
 * falls back to polling `/notifications/popup` when offline.
 */
export function NotificationPopupBridge() {
  const { user } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const seen = useRef(new Set<string>());

  const showOne = useCallback(
    (item: Pick<InAppNotification, "id" | "kind" | "title" | "body" | "link_path">) => {
      if (seen.current.has(item.id)) return false;
      if (isMessageInboxNotificationKind(item.kind)) {
        seen.current.add(item.id);
        return true;
      }
      seen.current.add(item.id);
      const copy = safeToastCopy({
        kind: item.kind,
        title: item.title,
        body: item.body,
      });
      const href = safeToastActionHref(item.link_path);
      toast.push({
        id: `notif-${item.id}`,
        tone: "info",
        title: copy.title,
        description: copy.description,
        href,
        actionLabel: "View",
        durationMs: 5500,
        onAction: () => {
          router.push(href);
        },
      });
      playInAppNotificationSound();
      return true;
    },
    [toast, router],
  );

  const pollPopup = useCallback(async () => {
    if (!user) return;
    try {
      const data = await fetchPopupNotifications();
      const ids: string[] = [];
      for (const item of data.items.slice(0, 3)) {
        showOne(item);
        ids.push(item.id);
      }
      for (const item of data.items) {
        if (!ids.includes(item.id)) ids.push(item.id);
      }
      if (ids.length) {
        await ackPopupNotifications(ids);
      }
    } catch {
      /* logged-out / network */
    }
  }, [user, showOne]);

  const onSocketEvent = useCallback(
    (event: MessagingSocketEvent) => {
      if (event.type !== "notification.created") return;
      const n = event.notification;
      if (!n?.id) return;
      showOne({
        id: n.id,
        kind: n.kind,
        title: n.title,
        body: n.body,
        link_path: n.link_path ?? null,
      });
      void ackPopupNotifications([n.id]).catch(() => undefined);
    },
    [showOne],
  );

  const { isLive } = useMessageSocket(
    user ? onSocketEvent : undefined,
    Boolean(user),
  );

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    let timer: number | undefined;

    function schedule() {
      if (timer !== undefined) window.clearTimeout(timer);
      const visible = document.visibilityState === "visible";
      const delay = !visible
        ? HIDDEN_POLL_MS
        : isLive
          ? POLL_LIVE_MS
          : POLL_FALLBACK_MS;
      timer = window.setTimeout(() => {
        void pollPopup().finally(() => {
          if (!cancelled) schedule();
        });
      }, delay);
    }

    function onVisible() {
      if (document.visibilityState === "visible") {
        void pollPopup();
        schedule();
      }
    }

    void pollPopup().finally(() => {
      if (!cancelled) schedule();
    });
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);

    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
    };
  }, [user, isLive, pollPopup]);

  return null;
}
