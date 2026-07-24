"use client";

import { cn } from "@/lib/cn";
import type { EventPublishChecklist } from "@/lib/types/events";

import {
  missingChecklistLabels,
  PUBLISH_CHECKLIST_ITEMS,
} from "./checklist-utils";

export function PublishChecklist({
  checklist,
  previewChecked,
  onPreviewChecked,
  compact = false,
}: {
  checklist?: EventPublishChecklist | null;
  previewChecked: boolean;
  onPreviewChecked: (value: boolean) => void;
  compact?: boolean;
}) {
  const local: EventPublishChecklist = {
    basics_complete: checklist?.basics_complete ?? false,
    category_complete: checklist?.category_complete ?? false,
    venue_privacy_complete: checklist?.venue_privacy_complete ?? false,
    date_complete: checklist?.date_complete ?? false,
    has_ticket_type: checklist?.has_ticket_type ?? false,
    banner_ready: checklist?.banner_ready ?? false,
    refund_policy_selected: checklist?.refund_policy_selected ?? false,
    check_in_settings_complete: checklist?.check_in_settings_complete ?? false,
    seo_complete: checklist?.seo_complete ?? false,
    preview_checked: previewChecked,
    ready_to_submit: false,
  };
  local.ready_to_submit = missingChecklistLabels(local).length === 0;

  const missing = missingChecklistLabels({
    ...local,
    preview_checked: previewChecked,
  });

  return (
    <div className="space-y-3">
      {!compact ? (
        <p className="text-sm leading-relaxed text-muted-foreground">
          Before you submit, make sure each item below is ready. Use{" "}
          <span className="font-semibold text-foreground">Preview</span> to open
          the full guest event page and confirm venue privacy looks right.
        </p>
      ) : null}
      <ul className="space-y-1.5">
        {PUBLISH_CHECKLIST_ITEMS.map((item) => {
          const done =
            item.key === "preview_checked"
              ? previewChecked
              : Boolean(local[item.key]);
          return (
            <li
              key={item.key}
              className={cn(
                "flex items-center justify-between gap-3 rounded-[var(--radius-md)] border px-3 py-2.5 text-sm transition-colors",
                done
                  ? "border-primary/25 bg-[color-mix(in_srgb,var(--brand-green)_10%,transparent)]"
                  : "border-border bg-muted/40",
              )}
            >
              <span className="flex min-w-0 items-center gap-2 font-medium text-foreground">
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-extrabold",
                    done
                      ? "bg-ink text-accent"
                      : "bg-surface-inset text-muted-foreground ring-1 ring-border",
                  )}
                  aria-hidden
                >
                  {done ? "✓" : "·"}
                </span>
                <span className="truncate">{item.label}</span>
              </span>
              <span className="shrink-0 text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                {done ? "Ready" : "Needed"}
              </span>
            </li>
          );
        })}
      </ul>

      {missing.length > 0 ? (
        <div className="rounded-[var(--radius-md)] border border-border bg-muted/60 px-3 py-2.5 text-sm">
          <p className="font-semibold text-foreground">Validation summary</p>
          <p className="mt-1 text-muted-foreground">
            Still needed: {missing.join(" · ")}
          </p>
        </div>
      ) : (
        <div className="rounded-[var(--radius-md)] border border-primary/25 bg-[color-mix(in_srgb,var(--brand-green)_10%,transparent)] px-3 py-2.5 text-sm font-semibold text-foreground">
          Ready to submit for review
        </div>
      )}

      <label className="flex flex-col gap-1 text-sm text-foreground">
        <span className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={previewChecked}
            onChange={(e) => onPreviewChecked(e.target.checked)}
          />
          I reviewed the live preview and venue privacy copy
        </span>
        <span className="pl-6 text-xs text-muted-foreground">
          Required before submit. Open the full preview and check title, date,
          location label, and ticket prices — and that the street address is not
          leaking if it should stay secret.
        </span>
      </label>
    </div>
  );
}
