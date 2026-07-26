import Link from "next/link";

import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";

export function TaxonomyHostCard({
  displayName,
  href,
  city,
  verified,
  className = "",
}: {
  displayName: string;
  href: string;
  city?: string | null;
  verified?: boolean;
  className?: string;
}) {
  return (
    <Link
      href={href}
      prefetch={false}
      className={cn(
        "group block rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] sm:p-5",
        "padeya-card-hover",
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-bold tracking-tight text-foreground">
          {displayName}
        </h3>
        {verified ? <Badge tone="accent">Verified</Badge> : null}
      </div>
      {city ? (
        <p className="mt-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
          {city}
        </p>
      ) : null}
      <span className="mt-3 inline-block text-xs font-bold uppercase tracking-[0.08em] text-foreground opacity-0 transition-opacity group-hover:opacity-100">
        View →
      </span>
    </Link>
  );
}
