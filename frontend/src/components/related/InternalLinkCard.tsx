import Link from "next/link";

import { cn } from "@/lib/cn";

export function InternalLinkCard({
  title,
  description,
  href,
  className = "",
}: {
  title: string;
  description?: string;
  href: string;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group block rounded-[var(--radius-lg)] border border-border bg-card p-5 shadow-[var(--shadow-soft)]",
        "padeya-card-hover",
        className,
      )}
    >
      <h3 className="text-base font-bold tracking-tight text-foreground">
        {title}
      </h3>
      {description ? (
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      ) : null}
      <span className="mt-3 inline-block text-xs font-bold uppercase tracking-[0.08em] text-foreground opacity-0 transition-opacity group-hover:opacity-100">
        Open →
      </span>
    </Link>
  );
}
