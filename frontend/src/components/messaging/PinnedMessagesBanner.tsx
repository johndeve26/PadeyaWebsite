"use client";

import { useState } from "react";

import { cn } from "@/lib/cn";
import type { MessageItem } from "@/lib/types/messaging";

function pinPreview(message: MessageItem): string {
  const body = (message.body || "").trim();
  if (body) return body.length > 80 ? `${body.slice(0, 77)}…` : body;
  if (message.attachments?.length) {
    const name = message.attachments[0]?.original_filename;
    return name || "Attachment";
  }
  return "Pinned message";
}

export function PinnedMessagesBanner({
  pinned,
  onSelect,
}: {
  pinned: MessageItem[];
  onSelect: (messageId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  if (!pinned.length) return null;

  const first = pinned[0];

  return (
    <div className="border-b border-border bg-surface-muted/60">
      <div className="flex items-start gap-2 px-4 py-2">
        <button
          type="button"
          className="min-w-0 flex-1 text-left"
          onClick={() => onSelect(first.id)}
        >
          <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
            Pinned · {pinned.length}
          </p>
          <p className="truncate text-xs font-semibold text-foreground">
            Pinned: {pinPreview(first)}
          </p>
        </button>
        <button
          type="button"
          className="shrink-0 text-xs font-bold text-foreground underline-offset-2 hover:underline"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Hide" : "All"}
        </button>
      </div>
      {open ? (
        <ul className="space-y-1 border-t border-border/70 px-4 py-2">
          {pinned.map((pm) => (
            <li key={pm.id}>
              <button
                type="button"
                className={cn(
                  "block w-full truncate rounded-[var(--radius-sm)] px-2 py-1.5",
                  "text-left text-xs font-semibold text-foreground",
                  "hover:bg-surface-muted",
                )}
                onClick={() => {
                  onSelect(pm.id);
                  setOpen(false);
                }}
              >
                {pinPreview(pm)}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
