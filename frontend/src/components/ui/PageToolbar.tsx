import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * Consistent action row under DashboardShell headers.
 * Relies on parent space-y — do not add extra vertical margin.
 */
export function PageToolbar({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 sm:gap-3",
        className,
      )}
    >
      {children}
    </div>
  );
}
