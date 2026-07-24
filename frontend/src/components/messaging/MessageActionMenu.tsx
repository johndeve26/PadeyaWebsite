"use client";

import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/cn";
import type { MessageItem } from "@/lib/types/messaging";

export type MessageAction =
  | "reply"
  | "edit"
  | "pin"
  | "unpin"
  | "star"
  | "unstar"
  | "copy"
  | "report"
  | "block"
  | "delete_for_me";

type MenuItem = {
  action: MessageAction;
  label: string;
  show: boolean;
  danger?: boolean;
};

export function MessageActionMenu({
  message,
  canReply,
  canPin = false,
  canStar = true,
  canReport = false,
  canBlock = false,
  onAction,
  mine,
  open: openControlled,
  onOpenChange,
  triggerClassName,
}: {
  message: MessageItem;
  canReply: boolean;
  canPin?: boolean;
  canStar?: boolean;
  canReport?: boolean;
  canBlock?: boolean;
  onAction: (action: MessageAction) => void;
  mine?: boolean;
  /** Controlled open state (e.g. from long-press on the bubble). */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  triggerClassName?: string;
}) {
  const [openUncontrolled, setOpenUncontrolled] = useState(false);
  const [nowMs] = useState(() => Date.now());
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const controlled = openControlled !== undefined;
  const open = controlled ? Boolean(openControlled) : openUncontrolled;

  function setOpen(next: boolean) {
    if (!controlled) setOpenUncontrolled(next);
    onOpenChange?.(next);
  }

  useEffect(() => {
    if (!open) return;
    function close() {
      if (!controlled) setOpenUncontrolled(false);
      onOpenChange?.(false);
    }
    function onDoc(ev: MouseEvent) {
      if (!rootRef.current?.contains(ev.target as Node)) close();
    }
    function onKey(ev: KeyboardEvent) {
      if (ev.key === "Escape") close();
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, controlled, onOpenChange]);

  const isSystem =
    message.message_type === "system" || message.sender_role === "system";
  const redacted =
    message.deleted_for_me ||
    message.status === "hidden" ||
    message.status === "deleted";
  const withinEditWindow = (() => {
    if (!message.created_at) return false;
    const ageMs = nowMs - new Date(message.created_at).getTime();
    return ageMs <= 24 * 60 * 60 * 1000;
  })();

  const pinAllowed = canPin && !redacted;
  const starShow =
    canStar &&
    ((!redacted && !message.is_starred) || Boolean(message.is_starred));
  const copyAllowed =
    Boolean(message.body?.trim()) && !isSystem && !message.deleted_for_me;
  const canDeleteForMe = !isSystem && !message.deleted_for_me;

  const items: MenuItem[] = isSystem
    ? [
        {
          action: message.is_starred ? "unstar" : "star",
          label: message.is_starred ? "Unstar" : "Star",
          show: starShow,
        },
        {
          action: message.is_pinned ? "unpin" : "pin",
          label: message.is_pinned ? "Unpin" : "Pin",
          show: pinAllowed,
        },
      ]
    : [
        { action: "reply", label: "Reply", show: canReply && !redacted },
        {
          action: "edit",
          label: "Edit",
          show: Boolean(
            message.is_mine && canReply && withinEditWindow && !redacted,
          ),
        },
        {
          action: message.is_starred ? "unstar" : "star",
          label: message.is_starred ? "Unstar" : "Star",
          show: starShow,
        },
        {
          action: message.is_pinned ? "unpin" : "pin",
          label: message.is_pinned ? "Unpin" : "Pin",
          show: pinAllowed,
        },
        { action: "copy", label: "Copy text", show: copyAllowed },
        {
          action: "delete_for_me",
          label: "Delete for me",
          show: canDeleteForMe,
          danger: true,
        },
        {
          action: "report",
          label: "Report",
          show: canReport && !message.deleted_for_me,
          danger: true,
        },
        {
          action: "block",
          label: "Block user",
          show: canBlock && !message.is_mine,
          danger: true,
        },
      ];

  const visible = items.filter((i) => i.show);
  if (!visible.length) return null;

  return (
    <div
      ref={rootRef}
      className={cn(
        "relative shrink-0",
        mine ? "order-first" : "order-last",
      )}
    >
      <button
        type="button"
        aria-label="Message actions"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        className={cn(
          "rounded-[var(--radius-sm)] px-1.5 py-0.5 text-xs font-bold",
          "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
          // Mobile: always show a small control. Desktop: reveal on row hover / focus / open.
          "opacity-100 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100",
          open ? "md:opacity-100" : null,
          triggerClassName,
        )}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
      >
        ···
      </button>
      {open ? (
        <ul
          id={menuId}
          role="menu"
          className={cn(
            "absolute z-30 mt-1 min-w-[10rem] overflow-hidden rounded-[var(--radius-md)]",
            "border border-border bg-card py-1 shadow-sm",
            mine ? "right-0" : "left-0",
          )}
        >
          {visible.map((item) => (
            <li key={item.action} role="none">
              <button
                type="button"
                role="menuitem"
                className={cn(
                  "block w-full px-3 py-1.5 text-left text-sm hover:bg-surface-muted",
                  item.danger
                    ? "font-semibold text-danger"
                    : "text-foreground",
                )}
                onClick={() => {
                  setOpen(false);
                  onAction(item.action);
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
