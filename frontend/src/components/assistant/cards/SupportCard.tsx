"use client";

import Link from "next/link";

import type { AssistantCard } from "@/lib/types/assistant";

export function SupportCard({ card }: { card: AssistantCard }) {
  const href =
    card.url ||
    (typeof card.meta?.support_url === "string" ? card.meta.support_url : null) ||
    "/support";

  const linkClass =
    "inline-flex h-9 min-h-9 items-center justify-center gap-2 rounded-[var(--radius-sm)] border border-border bg-surface-elevated px-3.5 text-sm font-semibold text-foreground shadow-[var(--shadow-soft)] transition-all hover:border-border-strong/50 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

  return (
    <div className="rounded-[var(--radius-md)] border border-border bg-card p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
        Support
      </p>
      <p className="mt-1 text-sm font-bold text-heading">{card.title}</p>
      {card.subtitle ? (
        <p className="mt-1 text-xs text-muted-foreground">{card.subtitle}</p>
      ) : null}
      <div className="mt-3">
        {href.startsWith("/") ? (
          <Link href={href} className={linkClass}>
            Open support
          </Link>
        ) : (
          <a
            href={href}
            className={linkClass}
            rel="noopener noreferrer"
            target="_blank"
          >
            Open support
          </a>
        )}
      </div>
    </div>
  );
}
