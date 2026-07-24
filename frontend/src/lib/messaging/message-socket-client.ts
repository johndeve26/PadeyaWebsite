/**
 * Shared messaging WebSocket client (one connection per logged-in user).
 * REST remains send authority; this client is delivery + ephemeral typing/read.
 */

import { refreshTokens } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/storage";
import { messagingWebSocketUrl } from "@/lib/messaging-api";
import type {
  MessagingSocketEvent,
  MessagingSocketHandler,
  SocketConnectionStatus,
} from "@/lib/messaging/socket-types";

const PING_MS = 25_000;
const MAX_BACKOFF_MS = 30_000;
const DEDUPE_TTL_MS = 60_000;
const DEDUPE_MAX = 400;

type StatusHandler = (status: SocketConnectionStatus) => void;

function eventDedupeKey(event: MessagingSocketEvent): string | null {
  if ("event_id" in event && event.event_id) {
    return `eid:${event.event_id}`;
  }
  switch (event.type) {
    case "message.created":
      return `mc:${event.message.id}`;
    case "message.updated":
      return `mu:${event.message_id || event.message?.id || ""}:${event.status || ""}`;
    case "message.deleted":
      return `md:${event.message_id}`;
    case "message.read":
      return `mr:${event.thread_id}:${event.reader_id || ""}:${event.read_at || ""}`;
    case "thread.updated":
      return `tu:${event.thread_id}:${event.last_message_at || ""}:${event.status || ""}:${event.unread ? 1 : 0}`;
    case "thread.unread_count_updated":
      return `uc:${event.unread_count}`;
    case "notification.created":
      return `nc:${event.notification.id}`;
    case "thread.disabled":
      return `td:${event.thread_id}:${event.reason}:${event.status || ""}`;
    case "connection.accepted":
      return `ca:${event.connection_id}`;
    case "connection.removed":
      return `cr:${event.connection_id || ""}:${event.reason}`;
    default:
      return null;
  }
}

class MessageSocketClient {
  private ws: WebSocket | null = null;
  private listeners = new Set<MessagingSocketHandler>();
  private statusListeners = new Set<StatusHandler>();
  private userKey: string | null = null;
  private retry = 0;
  private reconnectTimer: number | undefined;
  private pingTimer: number | undefined;
  private intentionalClose = false;
  private status: SocketConnectionStatus = "offline";
  private recentKeys = new Map<string, number>();
  private refreshingAuth = false;

  getConnectionStatus(): SocketConnectionStatus {
    return this.status;
  }

  addListener(handler: MessagingSocketHandler): () => void {
    this.listeners.add(handler);
    return () => {
      this.listeners.delete(handler);
      if (this.listeners.size === 0 && this.statusListeners.size === 0) {
        this.teardown();
        this.userKey = null;
      }
    };
  }

  addStatusListener(handler: StatusHandler): () => void {
    this.statusListeners.add(handler);
    handler(this.status);
    return () => {
      this.statusListeners.delete(handler);
      if (this.listeners.size === 0 && this.statusListeners.size === 0) {
        this.teardown();
        this.userKey = null;
      }
    };
  }

  ensureConnected(userKey: string): void {
    if (typeof window === "undefined") return;
    if (this.userKey !== userKey) {
      this.teardown();
      this.userKey = userKey;
      this.retry = 0;
    }
    if (this.ws && this.ws.readyState <= WebSocket.OPEN) return;
    this.connect();
  }

  send(payload: Record<string, unknown>): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify(payload));
    return true;
  }

  sendTyping(threadId: string, isTyping = true): void {
    if (!threadId) return;
    this.send({
      type: isTyping ? "typing.start" : "typing.stop",
      thread_id: threadId,
    });
  }

  sendRead(threadId: string): void {
    if (!threadId) return;
    this.send({ type: "message.read", thread_id: threadId });
  }

  subscribeThread(threadId: string): void {
    if (!threadId) return;
    this.send({ type: "thread.subscribe", thread_id: threadId });
  }

  unsubscribeThread(threadId: string): void {
    if (!threadId) return;
    this.send({ type: "thread.unsubscribe", thread_id: threadId });
  }

  private setStatus(next: SocketConnectionStatus): void {
    if (this.status === next) return;
    this.status = next;
    this.statusListeners.forEach((fn) => {
      try {
        fn(next);
      } catch {
        // ignore
      }
    });
  }

  private connect(): void {
    const url = messagingWebSocketUrl();
    if (!url || !this.userKey) {
      this.setStatus("offline");
      return;
    }
    if (!getAccessToken()) {
      this.setStatus("offline");
      return;
    }

    this.intentionalClose = false;
    if (this.retry > 0) this.setStatus("reconnecting");

    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.retry = 0;
      this.setStatus("connected");
      if (this.pingTimer) window.clearInterval(this.pingTimer);
      this.pingTimer = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, PING_MS);
    };

    ws.onmessage = (ev) => {
      let event: MessagingSocketEvent;
      try {
        event = JSON.parse(String(ev.data)) as MessagingSocketEvent;
      } catch {
        return;
      }
      if (!this.shouldEmit(event)) return;
      this.listeners.forEach((fn) => {
        try {
          fn(event);
        } catch {
          // ignore
        }
      });
    };

    ws.onclose = (ev) => {
      if (this.pingTimer) window.clearInterval(this.pingTimer);
      this.pingTimer = undefined;
      this.ws = null;

      if (this.intentionalClose) {
        this.setStatus("offline");
        return;
      }

      // Auth failure / expired token
      if (ev.code === 4401 || ev.code === 1008) {
        void this.handleAuthClose();
        return;
      }

      this.scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  private async handleAuthClose(): Promise<void> {
    if (this.refreshingAuth) {
      this.scheduleReconnect();
      return;
    }
    this.refreshingAuth = true;
    this.setStatus("reconnecting");
    try {
      const tokens = await refreshTokens();
      if (!tokens) {
        this.setStatus("offline");
        return;
      }
      this.retry = 0;
      this.connect();
    } catch {
      this.setStatus("offline");
    } finally {
      this.refreshingAuth = false;
    }
  }

  private scheduleReconnect(): void {
    if (this.listeners.size === 0 && this.statusListeners.size === 0) {
      this.setStatus("offline");
      return;
    }
    this.setStatus("reconnecting");
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer);
    const delay = Math.min(MAX_BACKOFF_MS, 1000 * 2 ** this.retry);
    this.retry += 1;
    this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
  }

  private shouldEmit(event: MessagingSocketEvent): boolean {
    const key = eventDedupeKey(event);
    if (!key) return true;
    const now = Date.now();
    if (this.recentKeys.size > DEDUPE_MAX) {
      for (const [k, ts] of this.recentKeys) {
        if (now - ts > DEDUPE_TTL_MS) this.recentKeys.delete(k);
      }
    }
    const prev = this.recentKeys.get(key);
    if (prev !== undefined && now - prev < DEDUPE_TTL_MS) return false;
    this.recentKeys.set(key, now);
    return true;
  }

  private teardown(): void {
    this.intentionalClose = true;
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer);
    if (this.pingTimer) window.clearInterval(this.pingTimer);
    this.reconnectTimer = undefined;
    this.pingTimer = undefined;
    this.ws?.close();
    this.ws = null;
    this.setStatus("offline");
  }
}

export const messageSocketClient = new MessageSocketClient();
