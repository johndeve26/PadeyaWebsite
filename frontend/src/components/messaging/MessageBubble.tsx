"use client";

import {
  useCallback,
  useRef,
  useState,
  type MouseEvent,
  type PointerEvent,
} from "react";

import {
  MessageActionMenu,
  type MessageAction,
} from "@/components/messaging/MessageActionMenu";
import { MessageAttachmentBlock } from "@/components/messaging/MessageAttachmentBlock";
import { MessageMeta } from "@/components/messaging/MessageMeta";
import { MessageTimestamp } from "@/components/messaging/MessageTimestamp";
import { QuotedMessage } from "@/components/messaging/QuotedMessage";
import { cn } from "@/lib/cn";
import type { MessageItem } from "@/lib/types/messaging";

const LONG_PRESS_MS = 480;

export function MessageBubble({
  message,
  peerReadAt = null,
  canReply = false,
  canPin = false,
  canStar = true,
  canReport = false,
  canBlock = false,
  highlighted = false,
  onAction,
  onReplyTap,
}: {
  message: MessageItem;
  /** Real thread-level peer read cursor — never invent Read without this. */
  peerReadAt?: string | null;
  canReply?: boolean;
  canPin?: boolean;
  canStar?: boolean;
  canReport?: boolean;
  canBlock?: boolean;
  highlighted?: boolean;
  onAction?: (action: MessageAction, message: MessageItem) => void;
  onReplyTap?: (messageId: string, unavailable?: boolean) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const longPressTimer = useRef<number | undefined>(undefined);
  const longPressFired = useRef(false);

  const clearLongPress = useCallback(() => {
    if (longPressTimer.current !== undefined) {
      window.clearTimeout(longPressTimer.current);
      longPressTimer.current = undefined;
    }
  }, []);

  const startLongPress = useCallback(() => {
    if (!onAction) return;
    longPressFired.current = false;
    clearLongPress();
    longPressTimer.current = window.setTimeout(() => {
      longPressFired.current = true;
      setMenuOpen(true);
    }, LONG_PRESS_MS);
  }, [clearLongPress, onAction]);

  const pressHandlers = onAction
    ? {
        onPointerDown: (e: PointerEvent) => {
          // Touch / pen long-press opens the menu; mouse uses hover + button.
          if (e.pointerType === "mouse") return;
          startLongPress();
        },
        onPointerUp: clearLongPress,
        onPointerCancel: clearLongPress,
        onPointerLeave: clearLongPress,
        onContextMenu: (e: MouseEvent) => {
          e.preventDefault();
          setMenuOpen(true);
        },
        onClick: (e: MouseEvent) => {
          // Suppress the click that follows a long-press open.
          if (longPressFired.current) {
            e.preventDefault();
            e.stopPropagation();
            longPressFired.current = false;
          }
        },
      }
    : {};

  const menu = onAction ? (
    <MessageActionMenu
      message={message}
      canReply={canReply}
      canPin={canPin}
      canStar={canStar}
      canReport={canReport}
      canBlock={canBlock}
      mine={message.is_mine}
      open={menuOpen}
      onOpenChange={setMenuOpen}
      onAction={(action) => onAction(action, message)}
    />
  ) : null;

  if (message.message_type === "system" || message.sender_role === "system") {
    return (
      <div
        className={cn(
          "group flex w-full items-start justify-center gap-1 px-2",
          highlighted
            ? "rounded-[var(--radius-md)] bg-primary/10 ring-2 ring-primary/40"
            : null,
        )}
        id={`msg-${message.id}`}
        {...pressHandlers}
      >
        {menu}
        <div className="max-w-[min(100%,28rem)] rounded-[var(--radius-md)] border border-border/60 bg-surface-muted/80 px-3 py-2 text-center dark:bg-surface-elevated/80">
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
            {message.sender_display_name || "Pàdéyá"}
            {message.is_pinned ? " · Pinned" : ""}
            {message.is_starred ? " · Starred" : ""}
          </p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            {message.body}
          </p>
          <div className="mt-1 flex justify-center">
            <MessageTimestamp
              createdAt={message.created_at}
              alwaysVisible
              className="text-muted-foreground"
            />
          </div>
        </div>
      </div>
    );
  }

  if (message.deleted_for_me) {
    return (
      <div
        id={`msg-${message.id}`}
        className={cn(
          "group flex w-full items-start gap-1 rounded-[var(--radius-md)]",
          message.is_mine ? "justify-end" : "justify-start",
          highlighted ? "bg-primary/10 ring-2 ring-primary/40" : null,
        )}
      >
        {menu}
        <div className="min-w-0 max-w-[min(100%,28rem)] rounded-[var(--radius-lg)] border border-dashed border-border bg-surface-muted/50 px-3.5 py-2.5 dark:bg-surface-elevated/50">
          <p className="text-sm italic text-muted-foreground">Message deleted</p>
          <div className="mt-1">
            <MessageTimestamp
              createdAt={message.created_at}
              alwaysVisible
              className="text-muted-foreground"
            />
          </div>
        </div>
      </div>
    );
  }

  const attachments = message.attachments || [];
  const reply = message.reply_to;

  return (
    <div
      id={`msg-${message.id}`}
      className={cn(
        "group flex w-full items-start gap-1 rounded-[var(--radius-md)] transition-colors duration-500",
        message.is_mine ? "justify-end" : "justify-start",
        highlighted ? "bg-primary/10 ring-2 ring-primary/40" : null,
      )}
      {...pressHandlers}
    >
      {menu}
      <div
        className={cn(
          "min-w-0 max-w-[min(100%,28rem)] space-y-1 rounded-[var(--radius-lg)] px-3.5 py-2.5",
          message.is_mine
            ? "bg-primary text-primary-foreground"
            : "bg-surface-muted text-foreground dark:bg-surface-elevated",
        )}
      >
        <div className="flex items-center gap-2">
          {!message.is_mine ? (
            <p className="text-[11px] font-bold uppercase tracking-[0.08em] opacity-70">
              {message.sender_display_name}
            </p>
          ) : null}
          {message.is_pinned ? (
            <span className="text-[10px] font-bold uppercase tracking-wide opacity-70">
              Pinned
            </span>
          ) : null}
          {message.is_starred ? (
            <span className="text-[10px] font-bold uppercase tracking-wide opacity-70">
              Starred
            </span>
          ) : null}
        </div>
        {reply ? (
          <QuotedMessage
            reply={reply}
            mine={message.is_mine}
            onTap={onReplyTap}
          />
        ) : null}
        {message.body ? (
          <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
            {message.body}
          </p>
        ) : null}
        {attachments.length > 0 ? (
          <ul className="mt-1 min-w-0 space-y-2">
            {attachments.map((a) => (
              <li key={a.id} className="min-w-0">
                <MessageAttachmentBlock
                  attachment={a}
                  mine={message.is_mine}
                />
              </li>
            ))}
          </ul>
        ) : null}
        <MessageMeta
          message={message}
          peerReadAt={peerReadAt}
          mineTone={message.is_mine}
        />
      </div>
    </div>
  );
}
