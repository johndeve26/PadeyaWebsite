"use client";

import { Button } from "@/components/ui";

import type { BlogInternalLinkSuggestion } from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function BlogInternalLinksPanel({
  suggestions,
  busy,
  onRun,
  onInsert,
  onDismiss,
}: {
  suggestions: BlogInternalLinkSuggestion[];
  busy?: boolean;
  onRun: () => void;
  onInsert: (suggestion: BlogInternalLinkSuggestion) => void;
  onDismiss: (suggestion: BlogInternalLinkSuggestion) => void;
}) {
  const visible = suggestions.filter((s) => !s.dismissed);

  return (
    <StudioPanel
      title="Internal links"
      description="Suggestions use real Pàdéyá routes and published posts only."
      actions={
        <Button size="sm" variant="secondary" disabled={busy} onClick={onRun}>
          {busy ? "Finding…" : "Suggest links"}
        </Button>
      }
    >
      {visible.length === 0 ? (
        <p className="text-xs text-muted-foreground">No suggestions yet.</p>
      ) : (
        <ul className="space-y-2">
          {visible.map((s) => (
            <li
              key={`${s.target_url}-${s.suggested_anchor || ""}`}
              className="rounded-[var(--radius-sm)] border border-border px-2 py-1.5 text-xs"
            >
              <p className="font-semibold text-foreground">
                {s.target_title || s.target_url}
              </p>
              <p className="text-muted-foreground">{s.target_url}</p>
              {s.suggested_anchor ? (
                <p className="mt-1">
                  Anchor:{" "}
                  <span className="font-medium">{s.suggested_anchor}</span>
                </p>
              ) : null}
              {s.relevance_reason ? (
                <p className="mt-1 text-muted-foreground">{s.relevance_reason}</p>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-1">
                <Button size="sm" onClick={() => onInsert(s)}>
                  Insert
                </Button>
                <Button size="sm" variant="ghost" onClick={() => onDismiss(s)}>
                  Dismiss
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </StudioPanel>
  );
}
