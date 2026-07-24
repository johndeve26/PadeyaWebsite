"use client";

import type { ComposerReplyTarget } from "@/components/messaging/composer-types";

/** Composer chip showing the message being replied to. */
export function ReplyPreview({
  replyTo,
  onCancel,
}: {
  replyTo: ComposerReplyTarget;
  onCancel?: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-[var(--radius-md)] border border-border bg-surface-muted px-3 py-2">
      <div className="min-w-0">
        <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
          Replying to {replyTo.senderName}
        </p>
        <p className="line-clamp-2 text-xs text-foreground">{replyTo.preview}</p>
      </div>
      {onCancel ? (
        <button
          type="button"
          className="shrink-0 text-xs font-bold text-muted-foreground hover:text-foreground"
          onClick={onCancel}
        >
          Cancel
        </button>
      ) : null}
    </div>
  );
}
