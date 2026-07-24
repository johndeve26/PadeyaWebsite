import Link from "next/link";

import { cn } from "@/lib/cn";

export function VibeCard({
  name,
  href,
  className = "",
}: {
  name: string;
  href?: string;
  className?: string;
}) {
  const body = (
    <>
      <h3 className="text-base font-bold tracking-tight text-foreground">
        {name}
      </h3>
      {href ? (
        <span className="mt-2 inline-block text-xs font-bold uppercase tracking-[0.08em] text-foreground opacity-0 transition-opacity group-hover:opacity-100">
          Explore →
        </span>
      ) : null}
    </>
  );

  const shell = cn(
    "rounded-[var(--radius-lg)] border border-border bg-muted p-5",
    href ? "padeya-card-hover group block bg-card shadow-[var(--shadow-soft)]" : "",
    className,
  );

  if (href) {
    return (
      <Link href={href} className={shell}>
        {body}
      </Link>
    );
  }

  return <div className={shell}>{body}</div>;
}
