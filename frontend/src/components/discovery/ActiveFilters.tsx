"use client";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

export type ActiveFilterItem = {
  id: string;
  label: string;
  /** Hub-locked facets cannot be removed — hierarchy context stays visible. */
  locked?: boolean;
};

export function ActiveFilters({
  items,
  onRemove,
  onClearAll,
  className = "",
}: {
  items: ActiveFilterItem[];
  onRemove: (id: string) => void;
  onClearAll: () => void;
  className?: string;
}) {
  if (!items.length) return null;
  const removable = items.some((i) => !i.locked);

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {items.map((item) => {
        if (item.locked) {
          return (
            <span
              key={item.id}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border border-ink bg-ink px-3 py-1.5",
                "text-xs font-semibold text-paper",
              )}
              title="Locked by this landing page"
            >
              {item.label}
            </span>
          );
        }
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onRemove(item.id)}
            className={cn(
              "padeya-section-enter inline-flex min-h-9 items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1.5",
              "text-xs font-semibold text-foreground transition-colors",
              "hover:border-border-strong/40 hover:bg-card",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            )}
          >
            <span>{item.label}</span>
            <span aria-hidden className="text-muted-foreground">
              ×
            </span>
            <span className="sr-only">Remove {item.label}</span>
          </button>
        );
      })}
      {removable ? (
        <Button type="button" variant="ghost" size="sm" onClick={onClearAll}>
          Clear all
        </Button>
      ) : null}
    </div>
  );
}
