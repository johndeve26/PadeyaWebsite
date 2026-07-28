"use client";

import { Button } from "@/components/ui";

import type { AiSuggestionState } from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function AiSuggestionDiff({
  suggestion,
  onApply,
  onInsertBelow,
  onReplace,
  onDiscard,
}: {
  suggestion: AiSuggestionState;
  onApply: () => void;
  onInsertBelow: () => void;
  onReplace: () => void;
  onDiscard: () => void;
}) {
  if (!suggestion) return null;

  return (
    <StudioPanel
      title="AI suggestion"
      description="Review before changing the editor. Nothing is applied until you choose an action."
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Selected
          </p>
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-[var(--radius-sm)] border border-border bg-surface-muted p-2 text-xs">
            {suggestion.original}
          </pre>
        </div>
        <div>
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Proposed ({suggestion.action})
          </p>
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded-[var(--radius-sm)] border border-primary/30 bg-primary/5 p-2 text-xs">
            {suggestion.proposed}
          </pre>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" onClick={onApply}>
          Apply
        </Button>
        <Button size="sm" variant="secondary" onClick={onInsertBelow}>
          Insert below
        </Button>
        <Button size="sm" variant="secondary" onClick={onReplace}>
          Replace
        </Button>
        <Button size="sm" variant="ghost" onClick={onDiscard}>
          Discard
        </Button>
      </div>
    </StudioPanel>
  );
}
