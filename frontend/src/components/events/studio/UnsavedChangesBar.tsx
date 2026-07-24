"use client";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

/**
 * Sticky save affordance when Event Studio has unsaved edits.
 * Complements browser beforeunload — visible in-page warning.
 */
export function UnsavedChangesBar({
  dirty,
  lastSavedAt,
  saving = false,
  onSave,
  className,
}: {
  dirty: boolean;
  lastSavedAt?: string | null;
  saving?: boolean;
  onSave?: () => void;
  className?: string;
}) {
  if (!dirty && !lastSavedAt) {
    return (
      <div
        className={cn(
          "flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground",
          className,
        )}
      >
        <p>Draft session — not saved yet</p>
      </div>
    );
  }

  if (!dirty) {
    return (
      <div
        className={cn(
          "flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-primary/25 bg-[color-mix(in_srgb,var(--brand-green)_8%,transparent)] px-3 py-2 text-sm",
          className,
        )}
      >
        <p className="font-medium text-foreground">
          All changes saved
          {lastSavedAt ? (
            <span className="font-normal text-muted-foreground">
              {" "}
              · Last saved {lastSavedAt}
            </span>
          ) : null}
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-warning/40 bg-card px-3 py-2.5 shadow-[var(--shadow-soft)] dark:bg-surface-elevated",
        className,
      )}
      role="status"
    >
      <div className="min-w-0">
        <p className="text-sm font-bold text-foreground">Unsaved changes</p>
        <p className="text-xs text-muted-foreground">
          {lastSavedAt
            ? `Last saved ${lastSavedAt}. Save before leaving this page.`
            : "Save a draft so you don’t lose this work."}
        </p>
      </div>
      {onSave ? (
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={saving}
          onClick={onSave}
        >
          {saving ? "Saving…" : "Save draft"}
        </Button>
      ) : null}
    </div>
  );
}
