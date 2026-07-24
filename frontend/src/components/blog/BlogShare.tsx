"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import { publicShareOrigin } from "@/lib/seo/site";

const shareLinkClass = cn(
  "inline-flex h-9 min-h-9 items-center justify-center gap-2 rounded-[var(--radius-sm)] px-3.5 text-sm font-semibold tracking-tight",
  "border border-border bg-surface-elevated text-foreground shadow-[var(--shadow-soft)]",
  "transition-all duration-200 hover:border-border-strong/50 hover:bg-surface-muted active:bg-surface-muted",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
);

export function BlogShare({
  title,
  path,
  compact = false,
}: {
  title: string;
  path: string;
  compact?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const [url, setUrl] = useState(() => {
    const safePath = path.startsWith("/") ? path : `/${path}`;
    return `https://padeya.com${safePath}`;
  });

  // Resolve share origin after mount to avoid SSR/client hydration mismatch.
  useEffect(() => {
    const safePath = path.startsWith("/") ? path : `/${path}`;
    setUrl(`${publicShareOrigin()}${safePath}`);
  }, [path]);

  const encoded = encodeURIComponent(url);
  const text = encodeURIComponent(title);

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <div
      className={cn("flex flex-wrap items-center gap-2")}
      role="group"
      aria-label={`Share “${title}”`}
    >
      {!compact ? (
        <span className="text-xs font-bold uppercase tracking-[0.14em] text-heading">
          Share
        </span>
      ) : null}
      <a
        className={shareLinkClass}
        href={`https://twitter.com/intent/tweet?url=${encoded}&text=${text}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        X / Twitter
      </a>
      <a
        className={shareLinkClass}
        href={`https://www.facebook.com/sharer/sharer.php?u=${encoded}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        Facebook
      </a>
      <a
        className={shareLinkClass}
        href={`https://wa.me/?text=${text}%20${encoded}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        WhatsApp
      </a>
      <Button
        size="sm"
        variant="ghost"
        type="button"
        onClick={() => void copy()}
        aria-label={copied ? "Link copied" : "Copy article link"}
      >
        {copied ? "Copied" : "Copy link"}
      </Button>
    </div>
  );
}
