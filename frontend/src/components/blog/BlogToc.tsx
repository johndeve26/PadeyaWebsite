"use client";

import { useMemo } from "react";

/** Build a sticky TOC from h2/h3 in sanitized body HTML. */
export function BlogToc({ html }: { html: string }) {
  const items = useMemo(() => {
    const re = /<h([23])[^>]*>(.*?)<\/h\1>/gi;
    const out: { level: number; text: string; id: string }[] = [];
    let m: RegExpExecArray | null;
    while ((m = re.exec(html))) {
      const text = m[2].replace(/<[^>]+>/g, "").trim();
      if (!text) continue;
      const id = text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      out.push({ level: Number(m[1]), text, id });
    }
    return out;
  }, [html]);

  if (items.length < 2) return null;

  return (
    <nav
      aria-label="On this page"
      className="rounded-[var(--radius-lg)] border border-border bg-card/90 p-5 shadow-[var(--shadow-soft)] backdrop-blur-sm dark:bg-surface-elevated"
    >
      <p className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-heading">
        <span
          aria-hidden
          className="inline-block h-[3px] w-5 shrink-0 rounded-[1px] bg-primary"
        />
        On this page
      </p>
      <ul className="mt-4 max-h-[min(50vh,22rem)] space-y-1 overflow-y-auto border-t border-border pt-3">
        {items.map((item) => (
          <li key={`${item.level}-${item.id}`}>
            <a
              href={`#${item.id}`}
              className={
                item.level === 3
                  ? "block rounded-[var(--radius-sm)] py-1.5 pl-3 text-[13px] font-medium leading-snug text-foreground/65 transition-colors hover:bg-surface-muted hover:text-primary-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                  : "block rounded-[var(--radius-sm)] py-1.5 text-sm font-semibold leading-snug text-foreground/80 transition-colors hover:bg-surface-muted hover:text-primary-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
              }
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
