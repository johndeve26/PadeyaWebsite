import { Card, EmptyState, SectionHeader } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatPercent } from "@/lib/format";
import type { EventAnalyticsFunnel } from "@/lib/types/analytics";

type FunnelStep = {
  key: string;
  label: string;
  count: number;
};

function stepsFromFunnel(funnel: EventAnalyticsFunnel): FunnelStep[] {
  return [
    { key: "impressions", label: "Impression", count: funnel.impressions },
    { key: "card_clicks", label: "Click", count: funnel.card_clicks },
    { key: "detail_views", label: "View", count: funnel.detail_views },
    {
      key: "ticket_selections",
      label: "Ticket select",
      count: funnel.ticket_selections,
    },
    { key: "checkout_starts", label: "Checkout", count: funnel.checkout_starts },
    { key: "purchases", label: "Purchase", count: funnel.purchases },
    { key: "check_ins", label: "Check-in", count: funnel.check_ins },
    { key: "reviews", label: "Review", count: funnel.reviews },
  ];
}

function rate(n: number, d: number): number | null {
  if (d <= 0) return null;
  return (n / d) * 100;
}

/** Visual conversion funnel with drop-off and step conversion rates. */
export function AnalyticsFunnel({
  funnel,
  className = "",
}: {
  funnel: EventAnalyticsFunnel;
  className?: string;
}) {
  const steps = stepsFromFunnel(funnel);
  const max = Math.max(...steps.map((s) => s.count), 0);
  const hasData = max > 0;

  return (
    <Card className={cn("space-y-5", className)}>
      <SectionHeader
        title="Conversion funnel"
        description="Impression → click → view → ticket → checkout → purchase → check-in → review"
      />
      {!hasData ? (
        <EmptyState
          title="No funnel activity yet"
          description="Counts appear as guests discover and book this event."
        />
      ) : (
        <ol className="space-y-3">
          {steps.map((step, index) => {
            const prev = index === 0 ? step.count : steps[index - 1].count;
            const width = Math.max(8, Math.round((step.count / max) * 100));
            const stepRate = index === 0 ? 100 : rate(step.count, prev);
            const drop = index === 0 ? 0 : Math.max(0, prev - step.count);
            const dropPct = index === 0 ? null : rate(drop, prev);
            return (
              <li key={step.key} className="space-y-1.5">
                <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                  <span className="font-bold text-heading">
                    {index + 1}. {step.label}
                  </span>
                  <span className="tabular-nums text-muted-foreground">
                    <span className="font-extrabold text-heading">
                      {step.count.toLocaleString("en-NG")}
                    </span>
                    {stepRate != null ? (
                      <>
                        {" · "}
                        <span className="font-semibold text-foreground">
                          {formatPercent(stepRate)}
                        </span>
                        <span> of prior</span>
                      </>
                    ) : null}
                    {dropPct != null && drop > 0 ? (
                      <span className="font-semibold text-danger">
                        {" · −"}
                        {formatPercent(dropPct)} drop
                      </span>
                    ) : null}
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-chart-muted/50 ring-1 ring-border/40">
                  <div
                    className="h-full rounded-full bg-chart-4 transition-all duration-500"
                    style={{ width: `${width}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
