import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

export function FacetedFilterBar({
  children,
  trailing,
  className = "",
  sticky = false,
}: {
  children: ReactNode;
  trailing?: ReactNode;
  className?: string;
  sticky?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-4 rounded-[var(--radius-xl)] border border-border bg-card/95 p-4 shadow-[var(--shadow-soft)] sm:p-5",
        "dark:border-border dark:bg-surface-elevated/95 dark:shadow-[var(--shadow)]",
        sticky && "padeya-sticky-filters",
        className,
      )}
    >
      <div className="grid min-w-0 gap-3.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5 [&_>_*]:min-w-0 [&_label]:min-h-[2.75rem] [&_select]:min-h-11 [&_input]:min-h-11">
        {children}
      </div>
      {trailing ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Sort & refine
          </p>
          <div className="flex flex-wrap items-center gap-2">{trailing}</div>
        </div>
      ) : null}
    </div>
  );
}
