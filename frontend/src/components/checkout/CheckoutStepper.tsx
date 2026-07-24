"use client";

import { CHECKOUT_STEPS, type CheckoutStepId } from "@/components/checkout/types";

type Props = {
  current: CheckoutStepId;
  onSelect?: (id: CheckoutStepId) => void;
  completed?: Set<CheckoutStepId>;
};

export function CheckoutStepper({ current, onSelect, completed }: Props) {
  const currentIdx = CHECKOUT_STEPS.findIndex((s) => s.id === current);

  return (
    <nav aria-label="Checkout progress" className="w-full">
      <ol className="flex items-center gap-1 sm:gap-2">
        {CHECKOUT_STEPS.map((step, idx) => {
          const isCurrent = step.id === current;
          const isDone =
            (completed?.has(step.id) ?? false) || idx < currentIdx;
          const clickable = Boolean(onSelect) && (isDone || isCurrent);
          return (
            <li key={step.id} className="flex min-w-0 flex-1 items-center gap-1 sm:gap-2">
              <button
                type="button"
                disabled={!clickable}
                onClick={() => onSelect?.(step.id)}
                className={[
                  "flex min-h-11 w-full min-w-0 items-center gap-2 rounded-[var(--radius-md)] px-2 py-2 text-left transition sm:px-3",
                  isCurrent
                    ? "bg-primary/15 text-foreground"
                    : isDone
                      ? "text-foreground hover:bg-muted"
                      : "text-muted-foreground",
                ].join(" ")}
              >
                <span
                  className={[
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                    isCurrent
                      ? "bg-primary text-primary-foreground"
                      : isDone
                        ? "bg-foreground text-background"
                        : "bg-muted text-muted-foreground",
                  ].join(" ")}
                >
                  {idx + 1}
                </span>
                <span className="truncate text-xs font-semibold sm:text-sm">
                  {step.label}
                </span>
              </button>
              {idx < CHECKOUT_STEPS.length - 1 ? (
                <span
                  aria-hidden
                  className={[
                    "hidden h-px w-3 shrink-0 sm:block",
                    isDone ? "bg-foreground/40" : "bg-border",
                  ].join(" ")}
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
