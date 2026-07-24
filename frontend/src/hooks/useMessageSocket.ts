"use client";

import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { messageSocketClient } from "@/lib/messaging/message-socket-client";
import type {
  MessagingSocketHandler,
  SocketConnectionStatus,
} from "@/lib/messaging/socket-types";

export type {
  MessagingSocketEvent,
  SocketConnectionStatus,
} from "@/lib/messaging/socket-types";

export type MessageSocketApi = {
  status: SocketConnectionStatus;
  /** True when the live socket is connected (not polling-only). */
  isLive: boolean;
  sendTyping: (threadId: string, isTyping?: boolean) => void;
  sendRead: (threadId: string) => void;
  subscribeThread: (threadId: string) => void;
  unsubscribeThread: (threadId: string) => void;
};

const stableSendTyping = (threadId: string, isTyping?: boolean) =>
  messageSocketClient.sendTyping(threadId, isTyping);
const stableSendRead = (threadId: string) =>
  messageSocketClient.sendRead(threadId);
const stableSubscribe = (threadId: string) =>
  messageSocketClient.subscribeThread(threadId);
const stableUnsubscribe = (threadId: string) =>
  messageSocketClient.unsubscribeThread(threadId);

/**
 * Shared messaging socket for the logged-in user.
 * Auto-reconnect + ping; token refresh on auth close; offline when unavailable.
 */
export function useMessageSocket(
  onEvent?: MessagingSocketHandler,
  enabled = true,
): MessageSocketApi {
  const { user } = useAuth();
  const [status, setStatus] = useState<SocketConnectionStatus>(
    messageSocketClient.getConnectionStatus(),
  );
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!user || !enabled) return;
    messageSocketClient.ensureConnected(String(user.id));
    const offStatus = messageSocketClient.addStatusListener(setStatus);
    const offEvent = messageSocketClient.addListener((event) => {
      onEventRef.current?.(event);
    });
    return () => {
      offStatus();
      offEvent();
    };
  }, [user, enabled]);

  return {
    status: user && enabled ? status : "offline",
    isLive: Boolean(user && enabled && status === "connected"),
    sendTyping: stableSendTyping,
    sendRead: stableSendRead,
    subscribeThread: stableSubscribe,
    unsubscribeThread: stableUnsubscribe,
  };
}

/** @deprecated Prefer useMessageSocket — kept for transitional imports. */
export function useMessagingSocket(
  onEvent: MessagingSocketHandler,
  enabled = true,
) {
  const api = useMessageSocket(onEvent, enabled);
  return {
    sendTyping: api.sendTyping,
    sendRead: api.sendRead,
    subscribeThread: api.subscribeThread,
    unsubscribeThread: api.unsubscribeThread,
  };
}

export type MessagingSocketHandle = {
  sendTyping: (threadId: string, isTyping?: boolean) => void;
  sendRead: (threadId: string) => void;
  subscribeThread: (threadId: string) => void;
  unsubscribeThread: (threadId: string) => void;
};
