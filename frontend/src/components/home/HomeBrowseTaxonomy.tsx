"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ExpandableDiscoverySection } from "@/components/home/ExpandableDiscoverySection";
import type { DiscoveryBranchItem } from "@/components/home/DiscoveryBranchCard";
import { Button, Container, SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";
import { fetchPublicBrowseTiles } from "@/lib/cms-api";
import {
  DEFAULT_BROWSE_TILES,
  type BrowseTileLink,
} from "@/lib/discovery/default-browse-tiles";
import { normalizeBrowseHref } from "@/lib/discovery/price-landing";
import type { CmsBrowseRail } from "@/lib/types/lifecycle";

const RAIL_META: Record<
  CmsBrowseRail,
  { label: string; title: string; description: string }
> = {
  interest: {
    label: "Scene",
    title: "Choose your kind of experience",
    description: "Scenes and vibes. Open the path that fits the night.",
  },
  city: {
    label: "Location",
    title: "Explore by location",
    description: "Jump into a city or area hub without scrolling listings.",
  },
  price: {
    label: "Budget",
    title: "Find events by budget",
    description: "From free nights to VIP. Filter before you browse.",
  },
  when: {
    label: "Schedule",
    title: "Browse by timing and access",
    description: "Weekend energy, format, or how you want to get in.",
  },
};

const RAIL_ORDER: CmsBrowseRail[] = ["interest", "city", "price", "when"];

function groupByRail(
  source: BrowseTileLink[],
): Record<CmsBrowseRail, DiscoveryBranchItem[]> {
  const out: Record<CmsBrowseRail, DiscoveryBranchItem[]> = {
    interest: [],
    city: [],
    price: [],
    when: [],
  };
  for (const item of source) {
    if (!(item.rail in out)) continue;
    out[item.rail].push({
      label: item.label,
      href: normalizeBrowseHref(item.href),
      hint: item.hint,
      image: item.image,
    });
  }
  return out;
}

/** Compact tabbed discovery branches for the homepage. */
export function HomeBrowseTaxonomy() {
  const [tiles, setTiles] = useState<Record<CmsBrowseRail, DiscoveryBranchItem[]>>(
    () => groupByRail(DEFAULT_BROWSE_TILES),
  );
  const [activeRail, setActiveRail] = useState<CmsBrowseRail>("interest");

  useEffect(() => {
    let alive = true;
    void fetchPublicBrowseTiles()
      .then((rows) => {
        if (!alive || !rows.length) return;
        const mapped: BrowseTileLink[] = rows.map((r) => ({
          rail: r.rail as CmsBrowseRail,
          label: r.label,
          hint: r.hint || "",
          href: r.href,
          image: r.image_url,
          sort_order: r.sort_order,
        }));
        setTiles(groupByRail(mapped));
      })
      .catch(() => {
        /* keep defaults */
      });
    return () => {
      alive = false;
    };
  }, []);

  const rails = useMemo(
    () => RAIL_ORDER.filter((r) => tiles[r].length > 0),
    [tiles],
  );

  const current = rails.includes(activeRail) ? activeRail : rails[0];
  const meta = current ? RAIL_META[current] : null;
  const items = current ? tiles[current] : [];

  if (!current || !meta) return null;

  return (
    <section className="border-y border-border bg-surface py-8 sm:py-10">
      <Container className="space-y-5">
        <SectionHeader
          variant="display"
          eyebrow="Discover"
          title="Find what fits, faster"
          description="Explore events by scene, location, budget, or schedule, with each path tailored to how you like to discover."
          action={
            <Link href="/events">
              <Button variant="secondary" size="md">
                View all events
              </Button>
            </Link>
          }
        />

        <div className="overflow-hidden rounded-[var(--radius-lg)] border border-border bg-muted/30 shadow-[var(--shadow-soft)]">
          <div
            role="tablist"
            aria-label="Discovery branches"
            className="flex gap-1 overflow-x-auto border-b border-border bg-surface-elevated p-2 sm:p-2.5"
          >
            {rails.map((rail) => {
              const selected = rail === current;
              return (
                <button
                  key={rail}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  id={`discover-tab-${rail}`}
                  aria-controls={`discover-panel-${rail}`}
                  onClick={() => setActiveRail(rail)}
                  className={cn(
                    "shrink-0 rounded-full px-3.5 py-2 text-sm font-semibold transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background",
                    selected
                      ? "bg-ink text-paper"
                      : "bg-transparent text-muted-foreground hover:bg-surface-muted hover:text-foreground",
                  )}
                >
                  {RAIL_META[rail].label}
                </button>
              );
            })}
          </div>

          <div
            role="tabpanel"
            id={`discover-panel-${current}`}
            aria-labelledby={`discover-tab-${current}`}
            className="space-y-3 p-3 sm:p-4"
          >
            <ExpandableDiscoverySection
              key={current}
              eyebrow={meta.label}
              title={meta.title}
              description={meta.description}
              items={items}
              compact
            />
          </div>
        </div>
      </Container>
    </section>
  );
}
