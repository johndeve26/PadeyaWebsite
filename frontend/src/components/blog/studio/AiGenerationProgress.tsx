"use client";

import { Button } from "@/components/ui";

import type { GenerationStage } from "./types";
import { StudioPanel } from "./BlogStudioShell";

const STAGE_LABELS: Record<GenerationStage, string> = {
  idle: "Idle",
  preparing: "Preparing brief",
  seo_brief: "Generating SEO brief",
  titles: "Generating titles",
  outline: "Building outline",
  section: "Writing section",
  draft: "Writing draft",
  rewrite: "Rewriting selection",
  faqs: "Generating FAQs",
  review: "Reviewing article",
  image: "Creating image prompt",
  links: "Finding internal links",
  facts: "Reviewing claims",
  seo_score: "Scoring SEO",
  finalizing: "Finalizing draft",
};

export function AiGenerationProgress({
  stage,
  message,
  busy,
  onCancel,
}: {
  stage: GenerationStage;
  message?: string | null;
  busy: boolean;
  onCancel: () => void;
}) {
  if (!busy && stage === "idle") return null;

  return (
    <StudioPanel title="AI generation">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">
            {STAGE_LABELS[stage] || "Working…"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {message ||
              (busy
                ? "Waiting for the backend — progress is not marked complete until the request succeeds."
                : "Complete")}
          </p>
          {busy ? (
            <div
              className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-muted"
              aria-hidden
            >
              <div className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
            </div>
          ) : null}
        </div>
        {busy ? (
          <Button size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </StudioPanel>
  );
}
