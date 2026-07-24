import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Compact uppercase section label — scannable, token-based, theme-safe. */
export function SectionLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground",
        className,
      )}
    >
      {children}
    </p>
  );
}
