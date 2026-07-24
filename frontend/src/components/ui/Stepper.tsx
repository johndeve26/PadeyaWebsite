import { cn } from "@/lib/cn";

export type Step = {
  id: string;
  label: string;
  description?: string;
};

export function Stepper({
  steps,
  current,
  className = "",
}: {
  steps: Step[];
  /** When omitted, all steps render as equal informational cards */
  current?: string;
  className?: string;
}) {
  const index =
    current == null ? -1 : Math.max(0, steps.findIndex((s) => s.id === current));

  return (
    <ol className={cn("grid gap-3 sm:grid-cols-3", className)}>
      {steps.map((step, i) => {
        const informational = current == null;
        const done = !informational && i < index;
        const active = !informational && i === index;
        return (
          <li
            key={step.id}
            className={cn(
              "rounded-[var(--radius-md)] border px-4 py-4 transition-colors",
              informational
                ? "border-border bg-card shadow-[var(--shadow-soft)]"
                : active
                  ? "border-primary bg-[color-mix(in_srgb,var(--primary)_10%,transparent)]"
                  : done
                    ? "border-ink/20 bg-card"
                    : "border-border bg-muted/50",
            )}
          >
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
              {informational ? `0${i + 1}` : `Step ${i + 1}`}
            </p>
            <p className="mt-1.5 text-base font-bold text-foreground">{step.label}</p>
            {step.description ? (
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
