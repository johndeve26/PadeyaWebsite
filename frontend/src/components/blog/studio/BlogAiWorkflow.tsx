"use client";

import { cn } from "@/lib/cn";

import {
  BLOG_WORKFLOW_STEPS,
  type BlogWorkflowStepId,
} from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function BlogAiWorkflow({
  current,
  onSelect,
  completed,
}: {
  current: BlogWorkflowStepId;
  onSelect: (id: BlogWorkflowStepId) => void;
  completed?: Partial<Record<BlogWorkflowStepId, boolean>>;
}) {
  const currentIndex = BLOG_WORKFLOW_STEPS.findIndex((s) => s.id === current);

  return (
    <StudioPanel
      title="AI workflow"
      description="Brief → SEO brief → Titles → Outline → Draft → Review → Publish"
    >
      <ol className="space-y-1">
        {BLOG_WORKFLOW_STEPS.map((step, i) => {
          const done = Boolean(completed?.[step.id]) || i < currentIndex;
          const active = step.id === current;
          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                className={cn(
                  "flex w-full items-start gap-2 rounded-[var(--radius-sm)] px-2 py-1.5 text-left transition",
                  active
                    ? "bg-primary/10 text-foreground"
                    : "hover:bg-surface-muted text-muted-foreground",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                    active
                      ? "bg-primary text-primary-foreground"
                      : done
                        ? "bg-primary/20 text-primary"
                        : "bg-surface-muted text-muted-foreground",
                  )}
                >
                  {done && !active ? "✓" : i + 1}
                </span>
                <span>
                  <span className="block text-xs font-semibold text-foreground">
                    {step.label}
                  </span>
                  <span className="block text-[11px] text-muted-foreground">
                    {step.description}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </StudioPanel>
  );
}
