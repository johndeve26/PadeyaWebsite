import Link from "next/link";

import { Button } from "@/components/ui";
import type { RoadmapItem } from "@/lib/host-roadmap";
import { roadmapCtaLabel } from "@/lib/host-roadmap";

import { RoadmapStatusBadge } from "./RoadmapStatusBadge";

export function RoadmapStepRow({
  item,
  index,
}: {
  item: RoadmapItem;
  index: number;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
      <div className="flex min-w-0 flex-1 gap-4">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-extrabold text-foreground"
          aria-hidden
        >
          {index}
        </span>
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-extrabold text-foreground">
              {item.label}
            </h3>
            <RoadmapStatusBadge status={item.status} />
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {item.why}
          </p>
          <p className="text-xs text-muted-foreground">
            Route:{" "}
            <Link
              href={item.href}
              className="font-medium text-accent underline-offset-2 hover:underline"
            >
              {item.href}
            </Link>
          </p>
        </div>
      </div>
      <Link href={item.href} className="shrink-0">
        <Button
          size="sm"
          variant={item.status === "done" ? "secondary" : "primary"}
        >
          {roadmapCtaLabel(item.status)}
        </Button>
      </Link>
    </div>
  );
}
