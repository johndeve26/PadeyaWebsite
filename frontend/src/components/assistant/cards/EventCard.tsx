"use client";

import Link from "next/link";

import { cn } from "@/lib/cn";
import type { AssistantCard } from "@/lib/types/assistant";

export function EventCard({ card }: { card: AssistantCard }) {
  const href = card.url || undefined;
  const meta = card.meta ?? {};
  const when =
    typeof meta.starts_at === "string"
      ? meta.starts_at
      : typeof meta.date === "string"
        ? meta.date
        : null;
  const location =
    typeof meta.location === "string"
      ? meta.location
      : typeof meta.city === "string"
        ? meta.city
        : null;

  const body = (
    <>
      {card.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={card.image_url}
          alt=""
          className="h-14 w-14 shrink-0 rounded-[var(--radius-sm)] object-cover"
        />
      ) : (
        <div
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-primary/15 text-xs font-extrabold text-primary-text"
          aria-hidden
        >
          Event
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-heading">{card.title}</p>
        {card.subtitle ? (
          <p className="truncate text-xs text-muted-foreground">{card.subtitle}</p>
        ) : null}
        {when || location ? (
          <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
            {[when, location].filter(Boolean).join(" · ")}
          </p>
        ) : null}
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
