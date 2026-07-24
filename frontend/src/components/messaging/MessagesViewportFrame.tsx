import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * Full-height messages pane below site header + workspace breadcrumbs.
 * Fixed positioning keeps the composer visible (page body / footer must not scroll the thread).
 */
export function MessagesViewportFrame({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
        className={cn(
          "messages-viewport-frame fixed z-10 flex flex-col overflow-hidden bg-surface",
        "inset-x-0",
        "bottom-[calc(3.5rem+env(safe-area-inset-bottom))] md:bottom-0",
        "top-[calc(4rem+2.75rem)] sm:top-[calc(4.25rem+2.75rem)]",
        "md:left-80",
        "px-4 pb-2 pt-1 sm:px-6 lg:px-8",
        className,
      )}
    >
      <div className="flex h-full min-h-0 w-full flex-col">{children}</div>
    </div>
  );
}
