import { Card, EmptyState, SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";

export type TrendPoint = {
  label: string;
  value: number;
  display: string;
};

/** Non-misleading visual: proportional bars from real series values only. */
export function TrendPanel({
  title,
  description,
  points,
  emptyTitle = "No data in this range",
  emptyDescription,
  className = "",
}: {
  title: string;
  description?: string;
  points: TrendPoint[];
  emptyTitle?: string;
  emptyDescription?: string;
  className?: string;
}) {
  const max = Math.max(...points.map((p) => p.value), 0);

  return (
    <Card className={cn("space-y-4", className)}>
      <SectionHeader title={title} description={description} />
      {points.length === 0 || max <= 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <ul className="space-y-3">
          {points.map((point) => {
            const width = Math.max(4, Math.round((point.value / max) * 100));
            return (
              <li key={point.label} className="space-y-1.5">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="font-medium text-heading">{point.label}</span>
                  <span className="shrink-0 font-bold tabular-nums text-heading">
                    {point.display}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-chart-muted/50 ring-1 ring-border/40">
                  <div
                    className="h-full rounded-full bg-chart-4 transition-all duration-300"
                    style={{ width: `${width}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
