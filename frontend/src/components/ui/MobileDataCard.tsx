import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

export type MobileDataRow = {
  label: string;
  value: ReactNode;
};

export function MobileDataCard({
  title,
  subtitle,
  rows,
  actions,
  className = "",
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  rows: MobileDataRow[];
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        className,
      )}
    >
      {title || subtitle ? (
        <div className="mb-3 space-y-1 border-b border-border pb-3">
          {title ? (
            <div className="text-base font-extrabold tracking-tight text-heading">
              {title}
            </div>
          ) : null}
          {subtitle ? (
            <div className="text-sm text-muted-foreground">{subtitle}</div>
          ) : null}
        </div>
      ) : null}
      <dl className="space-y-2.5">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-start justify-between gap-3 text-sm"
          >
            <dt className="shrink-0 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
              {row.label}
            </dt>
            <dd className="min-w-0 text-right font-medium text-foreground">
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
      {actions ? (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-border pt-3">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
