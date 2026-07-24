"use client";

import { cn } from "@/lib/cn";

import {
  VAULT_CREATOR_STEPS,
  type VaultCreatorStepId,
} from "./types";

export function VaultCreatorStepper({
  current,
  completed,
  onSelect,
}: {
  current: VaultCreatorStepId;
  completed: Record<VaultCreatorStepId, boolean>;
  onSelect: (id: VaultCreatorStepId) => void;
}) {
  const currentIndex = VAULT_CREATOR_STEPS.findIndex((s) => s.id === current);
  const doneCount = VAULT_CREATOR_STEPS.filter((s) => completed[s.id]).length;

  return (
    <nav
      aria-label="Vault creator steps"
      className="rounded-[var(--radius-xl)] border border-border bg-card p-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
    >
      <div className="mb-3 border-b border-border px-1 pb-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
          Creator steps
        </p>
        <p className="mt-1 text-sm font-semibold text-foreground">
          {doneCount} of {VAULT_CREATOR_STEPS.length} ready
        </p>
      </div>
      <ol className="flex flex-col gap-1.5">
        {VAULT_CREATOR_STEPS.map((step, index) => {
          const active = step.id === current;
          const done = completed[step.id];
          const past = index < currentIndex;
          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "group w-full rounded-[var(--radius-md)] border px-3 py-2.5 text-left transition-all duration-200",
                  active
                    ? "border-primary bg-[color-mix(in_srgb,var(--primary)_14%,transparent)] shadow-[var(--shadow-soft)]"
                    : done || past
                      ? "border-border bg-card hover:border-border-strong/25 dark:bg-surface-elevated"
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
                  <span className="min-w-0">
                    <span className="block text-sm font-extrabold text-foreground">
                      {step.label}
                    </span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {step.description}
                    </span>
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
