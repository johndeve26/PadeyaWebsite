"use client";

import { cn } from "@/lib/cn";

import { Button } from "./Button";

export function Pagination({
  page,
  pageCount,
  onPageChange,
  className = "",
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  className?: string;
}) {
  if (pageCount <= 1) return null;

  const safePage = Math.min(Math.max(1, page), pageCount);

  return (
    <nav
      aria-label="Pagination"
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-border bg-card px-3 py-2.5 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        className,
      )}
    >
      <p className="text-sm text-muted-foreground">
        Page <span className="font-bold text-heading">{safePage}</span> of{" "}
        <span className="font-bold text-heading">{pageCount}</span>
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={safePage <= 1}
          onClick={() => onPageChange(safePage - 1)}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={safePage >= pageCount}
          onClick={() => onPageChange(safePage + 1)}
        >
          Next
        </Button>
      </div>
    </nav>
  );
}
