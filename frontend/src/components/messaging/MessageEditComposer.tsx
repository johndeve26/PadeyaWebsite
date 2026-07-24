"use client";

import type { ComposerEditTarget } from "@/components/messaging/composer-types";

/** Composer chrome when editing an existing message body. */
export function MessageEditComposer({
  editTarget,
  onCancel,
}: {
  editTarget: ComposerEditTarget;
  onCancel?: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-[var(--radius-md)] border border-border bg-surface-muted px-3 py-2">
      <div className="min-w-0">
        <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
          Editing message
        </p>
        <p className="truncate text-xs text-foreground">{editTarget.body}</p>
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
