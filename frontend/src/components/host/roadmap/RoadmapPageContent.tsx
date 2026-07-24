"use client";

import { useEffect, useMemo, useState } from "react";

import { Alert, Button, Card, SkeletonLoader } from "@/components/ui";
import { isDeskFocusedStaff } from "@/lib/host-access";
import {
  filterRoadmapForDeskStaff,
  roadmapProgress,
  type RoadmapCategory,
  type RoadmapItem,
} from "@/lib/host-roadmap";
import { loadHostRoadmapItems } from "@/lib/load-host-roadmap";
import type { HostWorkspace } from "@/lib/types/host-workspace";

import { RoadmapStepRow } from "./RoadmapStepRow";

const FILTERS: { id: "all" | RoadmapCategory; label: string }[] = [
  { id: "all", label: "All" },
  { id: "launch", label: "Launch" },
  { id: "operate", label: "Operate" },
  { id: "grow", label: "Grow" },
];

export function RoadmapPageContent({
  workspace,
}: {
  workspace: HostWorkspace | null;
}) {
  const [items, setItems] = useState<RoadmapItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | RoadmapCategory>("all");

  useEffect(() => {
    let active = true;
    void loadHostRoadmapItems()
      .then((rows) => {
        if (active) setItems(rows);
      })
      .catch(() => {
        if (active) {
          setError("Unable to load launch checklist.");
          setItems([]);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleItems = useMemo(() => {
    const base = items ?? [];
    const scoped =
      workspace && isDeskFocusedStaff(workspace)
        ? filterRoadmapForDeskStaff(base)
        : base;
    if (filter === "all") return scoped;
    return scoped.filter((item) => item.category === filter);
  }, [items, filter, workspace]);

  const progress = useMemo(
    () => roadmapProgress(visibleItems),
    [visibleItems],
  );

  const pct =
    progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <div className="space-y-6">
      {error ? (
        <Alert tone="danger" title="Checklist unavailable">
          {error}
        </Alert>
      ) : null}

      <Card className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              Progress
            </p>
            <p className="text-xl font-bold tabular-nums text-foreground">
              {items === null ? "—" : `${progress.done} / ${progress.total}`}
            </p>
            <p className="text-sm text-muted-foreground">
              {items === null
                ? "Loading checklist…"
                : `${pct}% complete — inferred from your host profile, events, and workspace data.`}
            </p>
          </div>
        </div>
        <div
          className="h-2 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Launch checklist progress"
        >
          <div
            className="h-full rounded-full bg-accent transition-[width]"
            style={{ width: `${pct}%` }}
          />
        </div>
      </Card>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((entry) => (
          <Button
            key={entry.id}
            size="sm"
            variant={filter === entry.id ? "primary" : "secondary"}
            onClick={() => setFilter(entry.id)}
          >
            {entry.label}
          </Button>
        ))}
      </div>

      {items === null ? (
        <SkeletonLoader lines={8} />
      ) : visibleItems.length === 0 ? (
        <Card className="py-6 text-center">
          <p className="text-sm text-muted-foreground">
            No checklist items in this filter for your role.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {visibleItems.map((item, index) => (
            <RoadmapStepRow key={item.id} item={item} index={index + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
