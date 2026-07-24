"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { SponsorDirectoryCardView } from "@/components/sponsors/SponsorDirectoryCard";
import { EmptyState, SectionHeader, SkeletonCard } from "@/components/ui";
import { fetchSponsorDirectory, type SponsorDirectoryCard } from "@/lib/sponsor-profiles-api";

export function SponsorBrandDirectory() {
  const [rows, setRows] = useState<SponsorDirectoryCard[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [industry, setIndustry] = useState("");
  const [category, setCategory] = useState("all");
  const [verifiedOnly, setVerifiedOnly] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      setLoadError(false);
      try {
        const data = await fetchSponsorDirectory({
          industry: industry.trim() || undefined,
          verified: verifiedOnly || undefined,
        });
        if (active) setRows(data);
      } catch {
        if (active) {
          setRows([]);
          setLoadError(true);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [industry, verifiedOnly]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const row of rows ?? []) {
      for (const c of row.categories) {
        if (c) set.add(c);
      }
    }
    return [...set].sort();
  }, [rows]);

  const filtered = useMemo(() => {
    let list = rows ?? [];
    if (category !== "all") {
      list = list.filter((r) =>
        r.categories.some((c) => c.toLowerCase() === category.toLowerCase()),
      );
    }
    return list;
  }, [rows, category]);

  return (
    <section id="sponsor-directory" className="scroll-mt-20 space-y-5">
      <SectionHeader
        eyebrow="Directory"
        title="Verified sponsor profiles"
        description="Explore partnership-ready brands on Pàdéyá — public campaigns, placements, and host relationships. Open marketplace slots are below."
      />
      <div className="flex flex-wrap items-end gap-3 rounded-[var(--radius-lg)] border border-border bg-muted/30 p-4">
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Industry
          <input
            className="h-10 rounded-md border border-border bg-card px-3 text-sm font-normal normal-case text-foreground"
            placeholder="e.g. fintech, beauty"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
          />
        </label>
        {categories.length > 0 ? (
          <label className="flex min-w-[10rem] flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Category
            <select
              className="h-10 rounded-md border border-border bg-card px-3 text-sm font-normal normal-case text-foreground"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="all">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="flex h-10 items-center gap-2 pb-0.5 text-sm text-foreground">
          <input
            type="checkbox"
            checked={verifiedOnly}
            onChange={(e) => setVerifiedOnly(e.target.checked)}
          />
          Verified only
        </label>
      </div>
      {rows === null ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : loadError ? (
        <EmptyState
          title="Could not load sponsor directory"
          description="Check that the API is running and sponsor profile migrations are applied (through 20260723_0139). For local demo brands, run scripts.seed_sponsor_demo_data after seed_demo_data."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No public sponsor profiles yet"
          description="Sponsor profiles appear here after admin verification."
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {filtered.map((s) => (
            <SponsorDirectoryCardView key={s.id} sponsor={s} />
          ))}
        </ul>
      )}
    </section>
  );
}
