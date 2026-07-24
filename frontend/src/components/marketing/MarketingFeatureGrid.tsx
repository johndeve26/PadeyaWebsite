import Link from "next/link";

import { cn } from "@/lib/cn";

export type MarketingFeature = {
  title: string;
  body: string;
  href?: string;
  /**
   * Optional CTA text when `href` is set.
   * Omit (or pass `null`) to keep the card linkable without “Learn more” noise.
   */
  linkLabel?: string | null;
};

type MarketingFeatureGridProps = {
  items: readonly MarketingFeature[];
  columns?: 2 | 3 | 4 | 5;
  tone?: "light" | "dark";
  /** Softer surface — fewer hard card borders for feature pillars. */
  density?: "cards" | "pillars";
};

export function MarketingFeatureGrid({
  items,
  columns = 3,
  tone = "light",
  density = "cards",
}: MarketingFeatureGridProps) {
  const dark = tone === "dark";
  const pillars = density === "pillars";
  const colClass =
    columns === 2
      ? "sm:grid-cols-2"
      : columns === 4
        ? "sm:grid-cols-2 lg:grid-cols-4"
        : columns === 5
          ? "sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
          : "sm:grid-cols-2 lg:grid-cols-3";

  return (
    <ul className={cn("grid gap-4 sm:gap-5", colClass)}>
      {items.map((item) => {
        const showLinkLabel =
          Boolean(item.href) && item.linkLabel !== null && item.linkLabel !== undefined;

        const card = (
          <>
            <p
              className={cn(
                "font-extrabold tracking-tight",
                pillars
                  ? "text-lg sm:text-xl"
                  : "text-base sm:text-lg",
                dark ? "text-paper" : "text-heading",
              )}
            >
              {item.title}
            </p>
            <p
              className={cn(
                "mt-2.5 flex-1 leading-relaxed",
                pillars ? "text-sm sm:text-base" : "text-sm sm:text-[0.95rem]",
                dark ? "text-paper/70" : "text-muted-foreground",
              )}
            >
              {item.body}
            </p>
            {showLinkLabel ? (
              <span
                className={cn(
                  "mt-5 text-sm font-semibold",
                  dark ? "text-primary" : "text-primary-text",
                )}
              >
                {item.linkLabel} →
              </span>
            ) : null}
          </>
        );

        const className = cn(
          "group relative flex h-full flex-col overflow-hidden rounded-[var(--radius-xl)] p-5 sm:p-6",
          pillars
            ? dark
              ? "border border-paper/12 bg-paper/[0.05] shadow-[var(--shadow-glow)]"
              : "border border-border/80 bg-gradient-to-br from-card via-card to-surface-muted shadow-[var(--shadow-soft)] dark:from-surface-elevated dark:via-surface-elevated dark:to-surface-inset"
            : dark
              ? "border border-paper/12 bg-paper/[0.03]"
              : "border border-border bg-card dark:bg-surface-elevated",
          item.href &&
            "transition duration-200 hover:-translate-y-0.5 hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
          item.href && dark && "hover:border-primary/50 focus-visible:ring-primary",
        );

        return (
          <li key={item.title} className="min-w-0">
            {item.href ? (
              <Link href={item.href} className={className}>
                {pillars ? (
                  <span
                    aria-hidden
                    className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-primary/10 blur-2xl transition group-hover:bg-primary/20"
                  />
                ) : null}
                {card}
              </Link>
            ) : (
              <div className={className}>
                {pillars ? (
                  <span
                    aria-hidden
                    className="pointer-events-none absolute -right-6 -top-8 h-24 w-24 rounded-full bg-primary/10 blur-2xl"
                  />
                ) : null}
                {card}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
