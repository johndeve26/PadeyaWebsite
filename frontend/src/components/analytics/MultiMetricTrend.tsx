import { Card, EmptyState, SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";
import type { TimeseriesPoint } from "@/lib/types/analytics";

const METRICS = [
  { key: "impressions", label: "Impressions", color: "bg-chart-1" },
  { key: "views", label: "Views", color: "bg-chart-2" },
  { key: "checkout_starts", label: "Checkout", color: "bg-chart-3" },
  { key: "purchases", label: "Purchases", color: "bg-chart-4" },
] as const;

const REVENUE_COLOR = "bg-chart-4";

type MetricKey = (typeof METRICS)[number]["key"];

function valueOf(point: TimeseriesPoint, key: MetricKey): number {
  return Number(point[key] ?? 0);
}

/** Multi-metric time series using proportional bars from real API values only. */
export function MultiMetricTrend({
  points,
  granularity,
  className = "",
}: {
  points: TimeseriesPoint[];
  granularity: string;
  className?: string;
}) {
  const maxCount = Math.max(
    0,
    ...points.flatMap((p) => METRICS.map((m) => valueOf(p, m.key))),
  );
  const maxRevenue = Math.max(0, ...points.map((p) => Number(p.revenue ?? 0)));
  const hasData = points.length > 0 && (maxCount > 0 || maxRevenue > 0);

  return (
    <Card className={cn("space-y-5", className)}>
      <SectionHeader
        title="Activity over time"
        description={`By ${granularity} · impressions, views, checkout starts, purchases, and revenue`}
      />
      <div className="flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {METRICS.map((m) => (
          <span key={m.key} className="inline-flex items-center gap-1.5">
            <span
              className={cn(
                "h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-border/60",
                m.color,
              )}
            />
            {m.label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span
            className={cn(
              "h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-border/60",
              REVENUE_COLOR,
            )}
          />
          Revenue
        </span>
      </div>
      {!hasData ? (
        <EmptyState
          title="No time-series yet"
          description="Traffic and sales will chart here once guests start engaging."
        />
      ) : (
        <ul className="space-y-4">
          {points.map((point) => {
            const rev = Number(point.revenue ?? 0);
            const revWidth =
              maxRevenue > 0 ? Math.max(4, Math.round((rev / maxRevenue) * 100)) : 0;
            return (
              <li key={point.bucket} className="space-y-2">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="font-semibold text-heading">{point.bucket}</span>
                  <span className="tabular-nums font-medium text-muted-foreground">
                    {formatNgn(rev)}
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-1.5">
                  {METRICS.map((m) => {
                    const v = valueOf(point, m.key);
                    const h =
                      maxCount > 0 ? Math.max(6, Math.round((v / maxCount) * 100)) : 6;
                    return (
                      <div
                        key={m.key}
                        className="flex h-16 flex-col justify-end rounded-[var(--radius-sm)] bg-surface-inset px-1 pb-1 ring-1 ring-border/50"
                        title={`${m.label}: ${v}`}
                      >
                        <div
                          className={cn("w-full rounded-sm transition-all", m.color)}
                          style={{ height: `${h}%` }}
                        />
                      </div>
                    );
                  })}
                </div>
                {maxRevenue > 0 ? (
                  <div className="h-1.5 overflow-hidden rounded-full bg-chart-muted/50">
                    <div
                      className={cn("h-full rounded-full", REVENUE_COLOR)}
                      style={{ width: `${revWidth}%` }}
                    />
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
