"use client";

import Link from "next/link";

import { cn } from "@/lib/cn";
import type { AssistantCard } from "@/lib/types/assistant";

export function RouteCard({ card }: { card: AssistantCard }) {
  const href = card.url || undefined;

  const body = (
    <div className="min-w-0 flex-1">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
        Go to
      </p>
      <p className="truncate text-sm font-bold text-heading">{card.title}</p>
      {card.subtitle ? (
        <p className="truncate text-xs text-muted-foreground">{card.subtitle}</p>
      ) : null}
    </div>
  );

  const className = cn(
    "flex w-full items-center gap-3 rounded-[var(--radius-md)] border border-border bg-card p-2.5 text-left transition-colors",
    href
      ? "hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
      : null,
  );

  if (href?.startsWith("/")) {
    return (
      <Link href={href} className={className}>
        {body}
        <span className="shrink-0 text-primary-text" aria-hidden>
          →
        </span>
      </Link>
    );
  }
  if (href) {
    return (
      <a
        href={href}
        className={className}
        rel="noopener noreferrer"
        target="_blank"
      >
        {body}
        <span className="shrink-0 text-primary-text" aria-hidden>
          →
        </span>
      </a>
    );
  }
  return <div className={className}>{body}</div>;
}
