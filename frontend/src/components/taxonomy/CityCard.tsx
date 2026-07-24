import Link from "next/link";

import { cn } from "@/lib/cn";

export function CityCard({
  name,
  href,
  count,
  className = "",
}: {
  name: string;
  href: string;
  count?: number;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group block rounded-[var(--radius-lg)] border border-border bg-card p-5 text-card-foreground shadow-[var(--shadow-soft)]",
        "dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
        "padeya-card-hover transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className,
      )}
    >
      <h3 className="text-base font-bold tracking-tight text-heading sm:text-lg">
        {name}
      </h3>
      {typeof count === "number" ? (
        <p className="mt-1.5 text-sm text-muted-foreground">
          {count.toLocaleString()} {count === 1 ? "event" : "events"}
        </p>
      ) : null}
      <span className="mt-3 inline-block text-xs font-bold uppercase tracking-[0.08em] text-foreground opacity-0 transition-opacity group-hover:opacity-100">
        Explore →
      </span>
    </Link>
  );
}

/** Alias — location discovery cards share CityCard chrome. */
export const LocationCard = CityCard;
