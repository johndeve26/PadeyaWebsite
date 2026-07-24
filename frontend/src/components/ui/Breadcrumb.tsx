import Link from "next/link";

import { cn } from "@/lib/cn";

export type BreadcrumbItem = {
  label: string;
  href?: string;
};

function Chevron() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70"
      fill="none"
    >
      <path
        d="M6 3.5 10.5 8 6 12.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

type DisplayEntry =
  | { type: "item"; item: BreadcrumbItem; index: number; isLast: boolean }
  | { type: "ellipsis"; key: string };

/**
 * Desktop: full trail.
 * Mobile (long trails): Home > Events > … > penultimate > current.
 */
function toDisplayEntries(items: BreadcrumbItem[]): {
  mobile: DisplayEntry[];
  desktop: DisplayEntry[];
} {
  const desktop: DisplayEntry[] = items.map((item, index) => ({
    type: "item",
    item,
    index,
    isLast: index === items.length - 1,
  }));

  if (items.length <= 4) {
    return { mobile: desktop, desktop };
  }

  const mobile: DisplayEntry[] = [
    {
      type: "item",
      item: items[0],
      index: 0,
      isLast: false,
    },
  ];

  if (items[1]?.label === "Events") {
    mobile.push({
      type: "item",
      item: items[1],
      index: 1,
      isLast: false,
    });
  }

  mobile.push({ type: "ellipsis", key: "mobile-ellipsis" });

  const penultimate = items.length - 2;
  const last = items.length - 1;
  mobile.push({
    type: "item",
    item: items[penultimate],
    index: penultimate,
    isLast: false,
  });
  mobile.push({
    type: "item",
    item: items[last],
    index: last,
    isLast: true,
  });

  return { mobile, desktop };
}

function CrumbRow({ entries }: { entries: DisplayEntry[] }) {
  return (
    <ol className="flex min-w-0 items-center gap-1">
      {entries.map((entry, position) => {
        if (entry.type === "ellipsis") {
          return (
            <li
              key={entry.key}
              className="flex items-center gap-1 text-muted-foreground"
            >
              {position > 0 ? <Chevron /> : null}
              <span
                aria-hidden
                className="px-1 text-[12px] font-semibold tracking-tight"
              >
                …
              </span>
            </li>
          );
        }

        const { item, index, isLast } = entry;
        return (
          <li
            key={`${item.label}-${index}`}
            className="flex min-w-0 items-center gap-1"
          >
            {position > 0 ? <Chevron /> : null}
            {item.href && !isLast ? (
              <Link
                href={item.href}
                className="group inline-flex max-w-[9rem] shrink-0 items-center truncate rounded-[var(--radius-sm)] px-1.5 py-0.5 text-[12px] font-semibold tracking-tight text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground sm:max-w-[16rem]"
              >
                <span className="truncate">{item.label}</span>
              </Link>
            ) : (
              <span
                aria-current={isLast ? "page" : undefined}
                className={cn(
                  "inline-flex max-w-[10rem] truncate rounded-[var(--radius-sm)] px-1.5 py-0.5 text-[12px] tracking-tight sm:max-w-[20rem]",
                  isLast
                    ? "font-extrabold text-foreground"
                    : "font-semibold text-muted-foreground",
                )}
                title={item.label}
              >
                {item.label}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function Breadcrumb({
  items,
  className = "",
}: {
  items: BreadcrumbItem[];
  className?: string;
}) {
  if (items.length === 0) return null;

  const { mobile, desktop } = toDisplayEntries(items);

  return (
    <nav aria-label="Breadcrumb" className={cn("min-w-0", className)}>
      <div className="sm:hidden">
        <CrumbRow entries={mobile} />
      </div>
      <div className="hidden sm:block">
        <CrumbRow entries={desktop} />
      </div>
    </nav>
  );
}
