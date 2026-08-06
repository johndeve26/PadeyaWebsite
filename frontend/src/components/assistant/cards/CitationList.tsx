"use client";

import Link from "next/link";

import type { AssistantCitation } from "@/lib/types/assistant";

export function CitationList({ citations }: { citations: AssistantCitation[] }) {
  if (!citations.length) return null;

  return (
    <div className="mt-2 space-y-1.5">
      <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
        Sources
      </p>
      <ul className="space-y-1">
        {citations.map((c, i) => {
          const key = `${c.url}-${i}`;
          const inner = (
            <>
              <span className="font-semibold text-heading">{c.title}</span>
              {c.snippet ? (
                <span className="mt-0.5 block text-[11px] text-muted-foreground line-clamp-2">
                  {c.snippet}
                </span>
              ) : null}
            </>
          );
          return (
            <li key={key}>
              {c.url.startsWith("/") ? (
                <Link
                  href={c.url}
                  className="block rounded-[var(--radius-sm)] border border-border/70 bg-surface-muted/50 px-2.5 py-1.5 text-xs transition-colors hover:border-border-strong/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring dark:bg-surface-elevated/50"
                >
                  {inner}
                </Link>
              ) : (
                <a
                  href={c.url}
                  className="block rounded-[var(--radius-sm)] border border-border/70 bg-surface-muted/50 px-2.5 py-1.5 text-xs transition-colors hover:border-border-strong/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring dark:bg-surface-elevated/50"
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {inner}
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
