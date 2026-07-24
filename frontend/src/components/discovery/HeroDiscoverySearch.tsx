"use client";

import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { EventCategory, EventItem } from "@/lib/types/events";

export type HeroDiscoverySearchValues = {
  q: string;
  category: string;
  city: string;
  weekend: boolean;
};

type Suggestion = {
  id: string;
  label: string;
  kind: "recent" | "popular" | "trending" | "event" | "category" | "city";
  apply: Partial<HeroDiscoverySearchValues>;
};

const RECENT_KEY = "padeya.discovery.recentSearches";

function readRecent(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x): x is string => typeof x === "string").slice(0, 6);
  } catch {
    return [];
  }
}

function writeRecent(term: string) {
  if (typeof window === "undefined") return;
  const next = [term, ...readRecent().filter((t) => t !== term)].slice(0, 6);
  try {
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* ignore quota */
  }
}

/**
 * Compact hero search — Location, Date, Category, Search.
 * Wires into existing discovery filter state (no new APIs).
 */
export function HeroDiscoverySearch({
  values,
  onChange,
  onSearch,
  categories,
  cities,
  events,
  className = "",
  lockedCategory,
  lockedCity,
  lockedWeekend,
}: {
  values: HeroDiscoverySearchValues;
  onChange: (next: Partial<HeroDiscoverySearchValues>) => void;
  onSearch: () => void;
  categories: EventCategory[];
  /** City options as hub slugs + labels (matches discovery filter `city`). */
  cities: { slug: string; name: string }[];
  events: EventItem[];
  className?: string;
  lockedCategory?: boolean;
  lockedCity?: boolean;
  lockedWeekend?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [recent, setRecent] = useState<string[]>(() => readRecent());
  const wrapRef = useRef<HTMLDivElement>(null);

  const suggestions = useMemo(() => {
    const q = values.q.trim().toLowerCase();
    const items: Suggestion[] = [];

    if (!q) {
      for (const term of recent) {
        items.push({
          id: `recent-${term}`,
          label: term,
          kind: "recent",
          apply: { q: term },
        });
      }
      for (const cat of categories.slice(0, 4)) {
        items.push({
          id: `popular-cat-${cat.slug}`,
          label: cat.name,
          kind: "popular",
          apply: { category: cat.slug, q: "" },
        });
      }
      const trending = [...events]
        .filter((e) => e.featured)
        .slice(0, 3);
      for (const event of trending) {
        items.push({
          id: `trend-${event.id}`,
          label: event.title,
          kind: "trending",
          apply: { q: event.title },
        });
      }
      return items.slice(0, 8);
    }

    for (const cat of categories) {
      if (!cat.name.toLowerCase().includes(q) && !cat.slug.includes(q)) continue;
      items.push({
        id: `cat-${cat.slug}`,
        label: cat.name,
        kind: "category",
        apply: { category: cat.slug, q: "" },
      });
    }
    for (const city of cities) {
      if (
        !city.name.toLowerCase().includes(q) &&
        !city.slug.toLowerCase().includes(q)
      ) {
        continue;
      }
      items.push({
        id: `city-${city.slug}`,
        label: city.name,
        kind: "city",
        apply: { city: city.slug, q: "" },
      });
    }
    for (const event of events) {
      if (!event.title.toLowerCase().includes(q)) continue;
      items.push({
        id: `event-${event.id}`,
        label: event.title,
        kind: "event",
        apply: { q: event.title },
      });
      if (items.length >= 10) break;
    }
    return items.slice(0, 8);
  }, [values.q, recent, categories, cities, events]);

  function submit() {
    const term = values.q.trim();
    if (term) {
      writeRecent(term);
      setRecent(readRecent());
    }
    setOpen(false);
    onSearch();
  }

  const fieldClass =
    "h-11 w-full rounded-[var(--radius-md)] border border-border bg-surface-inset px-3 text-sm font-semibold text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background disabled:opacity-45";

  return (
    <div
      ref={wrapRef}
      className={cn(
        "rounded-[var(--radius-xl)] border border-paper/15 bg-card/95 p-3 shadow-[0_20px_60px_rgb(0_0_0/0.35)] backdrop-blur-md sm:p-4",
        "dark:border-border dark:bg-surface-elevated/95",
        className,
      )}
    >
      <form
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1.1fr_1fr_1fr_auto]"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        role="search"
        aria-label="Discover events"
      >
        <label className="space-y-1.5">
          <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Location
          </span>
          <select
            className={fieldClass}
            value={values.city}
            disabled={lockedCity}
            onChange={(e) => onChange({ city: e.target.value })}
            aria-label="Location"
          >
            <option value="all">Anywhere</option>
            {cities.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1.5">
          <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Date
          </span>
          <select
            className={fieldClass}
            value={values.weekend ? "weekend" : "any"}
            disabled={lockedWeekend}
            onChange={(e) => onChange({ weekend: e.target.value === "weekend" })}
            aria-label="Date"
          >
            <option value="any">Any date</option>
            <option value="weekend">This weekend</option>
          </select>
        </label>

        <label className="space-y-1.5">
          <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Category
          </span>
          <select
            className={fieldClass}
            value={values.category}
            disabled={lockedCategory}
            onChange={(e) => onChange({ category: e.target.value })}
            aria-label="Category"
          >
            <option value="all">All categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <div className="relative space-y-1.5 sm:col-span-2 lg:col-span-1">
          <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground lg:invisible lg:block">
            Search
          </span>
          <div className="flex gap-2">
            <div className="relative min-w-0 flex-1">
              <input
                type="search"
                value={values.q}
                onChange={(e) => {
                  onChange({ q: e.target.value });
                  setOpen(true);
                }}
                onFocus={() => setOpen(true)}
                onBlur={() => {
                  window.setTimeout(() => setOpen(false), 150);
                }}
                placeholder="Search events…"
                aria-label="Search events"
                aria-autocomplete="list"
                aria-controls="hero-search-suggestions"
                className={cn(fieldClass, "pr-3")}
                autoComplete="off"
              />
              {open && suggestions.length > 0 ? (
                <ul
                  id="hero-search-suggestions"
                  className="absolute left-0 right-0 top-[calc(100%+0.35rem)] z-30 max-h-64 overflow-auto rounded-[var(--radius-md)] border border-border bg-card py-1 shadow-[var(--shadow)]"
                >
                  {suggestions.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm font-semibold text-foreground hover:bg-surface-muted focus-visible:bg-muted focus-visible:outline-none"
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          onChange(s.apply);
                          setOpen(false);
                          if (s.apply.q) {
                            writeRecent(s.apply.q);
                            setRecent(readRecent());
                          }
                        }}
                      >
                        <span className="truncate">{s.label}</span>
                        <span className="shrink-0 text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                          {s.kind}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <Button
              type="submit"
              variant="primary"
              size="md"
              className="padeya-btn-ripple shrink-0 px-5"
            >
              Search
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
