import type { MessageItem } from "@/lib/types/messaging";

export type SocketConnectionStatus =
  | "connected"
  | "reconnecting"
  | "offline";

export type MessagingSocketEvent =
  | { type: "connected"; user_channel?: string }
  | { type: "pong" }
  | {
      type: "message.created";
      thread_id: string;
      message: MessageItem;
      event_id?: string;
    }
  | {
      type: "message.updated";
      thread_id: string;
      message_id?: string;
      status?: string;
      message?: MessageItem;
      event_id?: string;
    }
  | {
      type: "message.deleted";
      thread_id: string;
      message_id: string;
      message?: MessageItem;
      event_id?: string;
    }
  | {
      type: "message.read";
      thread_id: string;
      reader_id?: string;
      read_at?: string | null;
      event_id?: string;
    }
  | {
      type: "message.typing";
      thread_id: string;
      is_typing: boolean;
      user_id?: string;
      /** Safe public display name only — never email/phone/contact. */
      display_name?: string;
    }
  | {
      type: "thread.updated";
      thread_id: string;
      status?: string;
      is_request?: boolean;
      blocked?: boolean;
      can_reply?: boolean;
      last_message_preview?: string | null;
      last_message_at?: string | null;
      unread?: boolean;
      disabled_reason?: string;
      request_event?: string;
      event_id?: string;
    }
  | {
      type: "thread.unread_count_updated";
      unread_count: number;
      event_id?: string;
    }
  | {
      type: "notification.created";
      event_id?: string;
      unread_count?: number;
      notification: {
        id: string;
        kind: string;
        title: string;
        body: string;
        link_path?: string | null;
        thread_id?: string | null;
        created_at?: string | null;
      };
    }
  | {
      type: "thread.disabled";
      thread_id: string;
      reason: string;
      status?: string;
      can_reply?: boolean;
      blocked?: boolean;
      event_id?: string;
    }
  | {
      type: "connection.accepted";
      thread_id: string;
      connection_id: string;
      status?: string;
      event_id?: string;
    }
  | {
      type: "connection.removed";
      reason: string;
      connection_id?: string;
      event_id?: string;
    }
  | {
      type: "attachment.ready";
      attachment: {
        id: string;
        url: string;
        content_type: string;
        byte_size: number;
      };
      event_id?: string;
    }
  | { type: "attachment.failed"; detail: string; event_id?: string }
  | {
      type: "message.pinned";
      thread_id: string;
      message_id: string;
      pinned_messages: MessageItem[];
      event_id?: string;
    }
  | {
      type: "message.unpinned";
      thread_id: string;
      message_id: string;
      pinned_messages: MessageItem[];
      event_id?: string;
    }
  | { type: "thread.subscribed"; thread_id: string }
  | { type: "thread.unsubscribed"; thread_id: string }
  | { type: "thread.subscribe_denied"; thread_id: string };

export type MessagingSocketHandler = (event: MessagingSocketEvent) => void;
