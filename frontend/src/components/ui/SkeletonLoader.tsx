import { cn } from "@/lib/cn";

export function SkeletonLoader({
  className = "",
  lines = 3,
}: {
  className?: string;
  lines?: number;
}) {
  return (
    <div className={cn("space-y-3", className)} aria-hidden>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "padeya-skeleton h-4 rounded-[var(--radius-sm)]",
            i === 0 ? "w-2/3" : i === lines - 1 ? "w-1/2" : "w-full",
          )}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex h-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        className,
      )}
      aria-hidden
    >
      <div className="padeya-skeleton aspect-[16/10] w-full shrink-0" />
      <div className="flex flex-1 flex-col space-y-3 p-4 sm:p-5">
        <div className="padeya-skeleton h-5 w-3/4 rounded-[var(--radius-sm)]" />
        <div className="padeya-skeleton h-4 w-1/2 rounded-[var(--radius-sm)]" />
        <div className="padeya-skeleton mt-auto h-4 w-24 rounded-[var(--radius-sm)]" />
      </div>
    </div>
  );
}
