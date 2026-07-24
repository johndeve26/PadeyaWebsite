import Link from "next/link";
import { type ReactNode } from "react";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

export function EmptyDiscoveryState({
  title,
  description,
  action,
  className = "",
  onClearFilters,
  suggestedCategories = [],
  nearbyHref = "/events",
}: {
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
  onClearFilters?: () => void;
  suggestedCategories?: { name: string; href: string }[];
  nearbyHref?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-[var(--radius-xl)] border border-border bg-muted px-6 py-12 text-center sm:py-16",
        className,
      )}
    >
      <div
        aria-hidden
        className="relative flex h-20 w-20 items-center justify-center overflow-hidden rounded-full bg-ink"
      >
        <div className="padeya-hero-glow absolute inset-0 opacity-90" />
        <div className="padeya-discovery-particles absolute inset-0 opacity-70" />
        <span className="relative text-2xl font-extrabold text-accent">?</span>
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-extrabold tracking-tight text-foreground sm:text-xl">
          {title}
        </h3>
        <p className="mx-auto max-w-md text-sm leading-relaxed text-muted-foreground sm:text-base">
          {description}
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
        {onClearFilters ? (
          <Button type="button" variant="primary" onClick={onClearFilters}>
            Clear filters
          </Button>
        ) : null}
        {action}
        <Link href={nearbyHref}>
          <Button variant="secondary">Browse all events</Button>
        </Link>
      </div>
      {suggestedCategories.length ? (
        <div className="w-full max-w-lg space-y-2 pt-2">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Try a category
          </p>
          <ul className="flex flex-wrap justify-center gap-2">
            {suggestedCategories.map((cat) => (
              <li key={cat.href}>
                <Link
                  href={cat.href}
                  className="inline-flex min-h-10 items-center rounded-full border border-border bg-card px-3.5 py-2 text-sm font-semibold text-foreground transition-colors hover:border-border-strong/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
                >
                  {cat.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
