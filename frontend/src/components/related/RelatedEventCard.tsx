import Link from "next/link";

import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";

export function RelatedEventCard({
  title,
  slug,
  city,
  category,
  className = "",
}: {
  title: string;
  slug: string;
  city?: string | null;
  category?: string | null;
  className?: string;
}) {
  return (
    <Link
      href={`/events/${slug}`}
      className={cn(
        "group block w-56 shrink-0 rounded-[var(--radius-md)] border border-border bg-card p-3.5 shadow-[var(--shadow-soft)] sm:w-64",
        "padeya-card-hover",
        className,
      )}
    >
      <h3 className="line-clamp-2 text-sm font-bold tracking-tight text-foreground">
        {title}
      </h3>
      {(city || category) && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {city ? (
            <Badge tone="neutral" size="sm">
              {city}
            </Badge>
          ) : null}
          {category ? (
            <Badge tone="dark" size="sm">
              {category}
            </Badge>
          ) : null}
        </div>
      )}
    </Link>
  );
}
