import { cn } from "@/lib/cn";
import {
  merchOrderTimeline,
  type TimelineStep,
} from "@/lib/merch/buyer-merch-wallet";
import type { MerchFulfillment } from "@/lib/types/merch";

function TimelineList({ steps }: { steps: TimelineStep[] }) {
  return (
    <ol className="m-0 flex list-none flex-wrap gap-x-4 gap-y-2 p-0">
      {steps.map((step, i) => (
        <li key={step.id} className="flex items-center gap-2 text-xs">
          <span
            className={cn(
              "flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold",
              step.done
                ? "bg-foreground text-background"
                : "bg-muted text-muted-foreground ring-1 ring-border",
              step.current && !step.done && "ring-primary/50",
              step.current && step.done && "bg-primary text-primary-foreground",
            )}
            aria-hidden
          >
            {step.done ? "✓" : i + 1}
          </span>
          <span
            className={cn(
              "font-semibold",
              step.current ? "text-foreground" : "text-muted-foreground",
            )}
          >
            {step.label}
          </span>
        </li>
      ))}
    </ol>
  );
}

export function MerchOrderTimeline({ row }: { row: MerchFulfillment }) {
  const steps = merchOrderTimeline(row);
  return (
    <div className="space-y-2">
      <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
        Status
      </p>
      <TimelineList steps={steps} />
    </div>
  );
}
