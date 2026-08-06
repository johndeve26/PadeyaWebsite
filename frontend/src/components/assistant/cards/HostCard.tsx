"use client";

import Link from "next/link";

import { cn } from "@/lib/cn";
import type { AssistantCard } from "@/lib/types/assistant";

export function HostCard({ card }: { card: AssistantCard }) {
  const href = card.url || undefined;

  const body = (
    <>
      {card.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={card.image_url}
          alt=""
          className="h-12 w-12 shrink-0 rounded-full object-cover"
        />
      ) : (
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-surface-muted text-sm font-extrabold text-muted-foreground"
          aria-hidden
        >
          {card.title.slice(0, 1).toUpperCase()}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-heading">{card.title}</p>
        {card.subtitle ? (
          <p className="truncate text-xs text-muted-foreground">{card.subtitle}</p>
        ) : (
          <p className="text-xs text-muted-foreground">Host</p>
        )}
      </div>
    </>
  );

  const className = cn(
    "flex w-full items-center gap-3 rounded-[var(--radius-md)] border border-border bg-surface-elevated p-2.5 text-left transition-colors",
    href
      ? "hover:border-border-strong/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
      : null,
  );

  if (href?.startsWith("/")) {
    return (
      <Link href={href} className={className}>
        {body}
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
      </a>
    );
  }
  return <div className={className}>{body}</div>;
}
