import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

export function FilterBar({
  children,
  trailing,
  className = "",
}: {
  children: ReactNode;
  trailing?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-card p-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)] sm:p-4",
        className,
      )}
    >
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4 [&_>_*]:min-w-0">
        {children}
      </div>
      {trailing ? (
        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          {trailing}
        </div>
      ) : null}
    </div>
  );
}
