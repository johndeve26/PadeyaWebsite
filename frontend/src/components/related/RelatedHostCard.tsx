import Link from "next/link";

import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";

export function RelatedHostCard({
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
      className={cn(
        "group block w-52 shrink-0 rounded-[var(--radius-md)] border border-border bg-card p-3.5 shadow-[var(--shadow-soft)] sm:w-56",
        "padeya-card-hover",
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <h3 className="truncate text-sm font-bold tracking-tight text-foreground">
          {displayName}
        </h3>
        {verified ? (
          <Badge tone="accent" size="sm">
            Verified
          </Badge>
        ) : null}
      </div>
      {city ? (
        <p className="mt-1.5 truncate text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
          {city}
        </p>
      ) : null}
    </Link>
  );
}
