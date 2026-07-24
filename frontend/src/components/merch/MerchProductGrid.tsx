"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Props = {
  children: ReactNode;
  compact?: boolean;
  className?: string;
};

/** Responsive merch product grid: 1 / 2 / 3 columns. */
export function MerchProductGrid({
  children,
  compact = false,
  className,
}: Props) {
  return (
    <ul
      className={cn(
        "grid gap-4",
        compact
          ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
          : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
        className,
      )}
    >
      {children}
    </ul>
  );
}
