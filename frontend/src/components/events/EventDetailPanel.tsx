import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Content panel with a bordered header rail — used on the public event page. */
export function EventDetailPanel({
  title,
  action,
  children,
  className = "",
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-soft)]",
        "dark:border-border dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3 border-b border-border bg-muted/80 px-5 py-3.5 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden
            className="h-5 w-1 shrink-0 rounded-full bg-accent"
          />
          <h2 className="truncate text-base font-extrabold tracking-tight text-foreground sm:text-lg">
            {title}
          </h2>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className="px-5 py-5 sm:px-6 sm:py-6">{children}</div>
    </section>
  );
}

/** Bordered sub-block inside an EventDetailPanel (accessibility, refund, entry…). */
export function EventInfoTile({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-md)] border border-border bg-muted/40 p-4",
        className,
      )}
    >
      <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-foreground">
        {label}
      </p>
      <div className="mt-2 space-y-1.5 text-sm leading-relaxed text-foreground">
        {children}
      </div>
    </div>
  );
}
