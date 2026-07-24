"use client";

import { cn } from "@/lib/cn";

import { STUDIO_STEPS, type StudioStepId } from "./types";

export function EventStudioStepper({
  current,
  completed,
  onSelect,
  orientation = "vertical",
}: {
  current: StudioStepId;
  completed: Partial<Record<StudioStepId, boolean>>;
  onSelect: (id: StudioStepId) => void;
  orientation?: "vertical" | "horizontal";
}) {
  const currentIndex = STUDIO_STEPS.findIndex((s) => s.id === current);
  const vertical = orientation === "vertical";
  const doneCount = STUDIO_STEPS.filter((s) => completed[s.id]).length;

  return (
    <nav
      aria-label="Event Studio steps"
      className={cn(
        vertical
          ? "rounded-[var(--radius-xl)] border border-border bg-card p-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
          : "overflow-x-auto pb-1",
      )}
    >
      {vertical ? (
        <div className="mb-3 border-b border-border px-1 pb-3">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            Steps
          </p>
          <p className="mt-1 text-sm font-semibold text-foreground">
            {doneCount} of {STUDIO_STEPS.length} ready
          </p>
        </div>
      ) : null}
      <ol
        className={cn(
          vertical ? "flex flex-col gap-1.5" : "flex min-w-max gap-2",
        )}
      >
        {STUDIO_STEPS.map((step, index) => {
          const active = step.id === current;
          const done = Boolean(completed[step.id]);
          const past = index < currentIndex;
          return (
            <li
              key={step.id}
              className={cn(vertical ? "w-full" : "min-w-[152px] shrink-0")}
            >
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "group w-full rounded-[var(--radius-md)] border px-3 py-2.5 text-left transition-all duration-200",
                  active
                    ? "border-primary bg-[color-mix(in_srgb,var(--primary)_14%,transparent)] shadow-[var(--shadow-soft)]"
                    : done || past
                      ? "border-border bg-card hover:border-border-strong/25 hover:shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
                      : "border-border bg-muted/40 hover:bg-surface-elevated",
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-extrabold",
                      active
                        ? "bg-ink text-primary"
                        : done
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground",
                    )}
                  >
                    {done && !active ? "✓" : String(index + 1)}
                  </span>
                  <p className="text-sm font-bold leading-snug text-foreground">
                    {step.label}
                  </p>
                </div>
                {vertical ? (
                  <p className="mt-1.5 pl-8 text-xs leading-snug text-muted-foreground">
                    {step.description}
                  </p>
                ) : (
                  <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                    {done ? "Ready" : active ? "Current" : "Next"}
                  </p>
                )}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
