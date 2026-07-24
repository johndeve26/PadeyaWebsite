"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useMessageSocket } from "@/hooks/useMessageSocket";
import type { MessagingSocketEvent } from "@/lib/messaging/socket-types";
import type { SocketConnectionStatus } from "@/lib/messaging/socket-types";
import type { MessageItem, ThreadListItem } from "@/lib/types/messaging";

export type ThreadRealtimeHandlers = {
  onMessageCreated?: (threadId: string, message: MessageItem) => void;
  onMessageUpdated?: (event: Extract<MessagingSocketEvent, { type: "message.updated" }>) => void;
  onMessageDeleted?: (event: Extract<MessagingSocketEvent, { type: "message.deleted" }>) => void;
  onMessagePinned?: (
    event: Extract<
      MessagingSocketEvent,
      { type: "message.pinned" | "message.unpinned" }
    >,
  ) => void;
  onThreadUpdated?: (event: Extract<MessagingSocketEvent, { type: "thread.updated" }>) => void;
  onThreadDisabled?: (event: Extract<MessagingSocketEvent, { type: "thread.disabled" }>) => void;
  onConnectionAccepted?: (
    event: Extract<MessagingSocketEvent, { type: "connection.accepted" }>,
  ) => void;
  onConnectionRemoved?: (
    event: Extract<MessagingSocketEvent, { type: "connection.removed" }>,
  ) => void;
};

/**
 * Thread-scoped realtime: subscribe when open, peer read receipts, event fan-out.
 * Message/event id dedupe is handled in the shared socket client.
 */
export function useThreadRealtime(
  threadId: string | null | undefined,
  handlers: ThreadRealtimeHandlers = {},
  enabled = true,
): {
  status: SocketConnectionStatus;
  isLive: boolean;
  peerReadAt: string | null;
  hydratePeerReadAt: (readAt: string | null | undefined) => void;
  sendRead: () => void;
} {
  const activeThread = threadId || "";
  const [peerReadAt, setPeerReadAt] = useState<string | null>(null);
  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  const onEvent = useCallback(
    (event: MessagingSocketEvent) => {
      const h = handlersRef.current;
      switch (event.type) {
        case "message.created":
          h.onMessageCreated?.(event.thread_id, event.message);
          break;
        case "message.updated":
          h.onMessageUpdated?.(event);
          break;
        case "message.deleted":
          h.onMessageDeleted?.(event);
          break;
        case "message.pinned":
        case "message.unpinned":
          h.onMessagePinned?.(event);
          break;
        case "message.read":
          // Peer marked the thread read — update Read cursor (server sets reader_id).
          if (
            activeThread &&
            event.thread_id === activeThread &&
            event.read_at
          ) {
            setPeerReadAt(event.read_at);
          }
          break;
        case "thread.updated":
          h.onThreadUpdated?.(event);
          break;
        case "thread.disabled":
          h.onThreadDisabled?.(event);
          break;
        case "connection.accepted":
          h.onConnectionAccepted?.(event);
          break;
        case "connection.removed":
          h.onConnectionRemoved?.(event);
          break;
        default:
          break;
      }
    },
    [activeThread],
  );

  const {
    status,
    isLive,
    sendRead: socketSendRead,
    subscribeThread,
    unsubscribeThread,
  } = useMessageSocket(onEvent, enabled);

  useEffect(() => {
    let alive = true;
    queueMicrotask(() => {
      if (alive) setPeerReadAt(null);
    });
    if (!enabled || !activeThread || !isLive) {
      return () => {
        alive = false;
      };
    }
    subscribeThread(activeThread);
    return () => {
      alive = false;
      unsubscribeThread(activeThread);
    };
  }, [activeThread, enabled, isLive, subscribeThread, unsubscribeThread]);

  const hydratePeerReadAt = useCallback((readAt: string | null | undefined) => {
    if (!readAt) return;
    setPeerReadAt((prev) => {
      if (!prev) return readAt;
      return new Date(readAt).getTime() >= new Date(prev).getTime()
        ? readAt
        : prev;
    });
  }, []);

  const sendRead = useCallback(() => {
    if (activeThread) socketSendRead(activeThread);
  }, [activeThread, socketSendRead]);

  return {
    status,
    isLive,
    peerReadAt,
    hydratePeerReadAt,
    sendRead,
  };
}

/** Helpers for merging thread list rows from realtime events (inbox). */
export function patchThreadListItem(
  items: ThreadListItem[],
  threadId: string,
  patch: Partial<ThreadListItem>,
): ThreadListItem[] {
  const idx = items.findIndex((t) => t.id === threadId);
  if (idx < 0) return items;
  const next = [...items];
  next[idx] = { ...next[idx], ...patch };
  return next;
}

export function upsertMessage(
  messages: MessageItem[],
  message: MessageItem,
): MessageItem[] {
  if (messages.some((m) => m.id === message.id)) return messages;
  return [...messages, message];
}
