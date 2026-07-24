import { cn } from "@/lib/cn";

export function SearchResultsHeader({
  title,
  count,
  subtitle,
  className = "",
}: {
  title: string;
  count?: number;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 space-y-2", className)}>
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
        What’s on
      </p>
      <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
        {title}
      </h2>
      {subtitle ? (
        <p
          className="max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base"
          aria-live="polite"
        >
          {subtitle}
        </p>
      ) : typeof count === "number" ? (
        <p
          className="text-sm leading-relaxed text-muted-foreground sm:text-base"
          aria-live="polite"
        >
          Showing {count.toLocaleString()} verified{" "}
          {count === 1 ? "event" : "events"}
        </p>
      ) : null}
    </div>
  );
}
