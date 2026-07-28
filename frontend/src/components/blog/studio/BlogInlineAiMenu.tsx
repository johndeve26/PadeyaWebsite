"use client";

import { Button } from "@/components/ui";

import type { RewriteAction } from "./types";

const ACTIONS: Array<{ id: RewriteAction; label: string }> = [
  { id: "rewrite", label: "Rewrite" },
  { id: "clarity", label: "Improve clarity" },
  { id: "shorter", label: "Make shorter" },
  { id: "expand", label: "Expand" },
  { id: "tone", label: "Change tone" },
  { id: "grammar", label: "Fix grammar" },
  { id: "engaging", label: "More engaging" },
  { id: "simplify", label: "Simplify" },
  { id: "examples", label: "Add examples" },
  { id: "transition", label: "Add transition" },
  { id: "to_bullets", label: "To bullets" },
  { id: "to_prose", label: "Bullets to prose" },
  { id: "heading", label: "Generate heading" },
  { id: "continue", label: "Continue writing" },
  { id: "summarize", label: "Summarize" },
];

export function BlogInlineAiMenu({
  visible,
  busy,
  onAction,
}: {
  visible: boolean;
  busy?: boolean;
  onAction: (action: RewriteAction) => void;
}) {
  if (!visible) return null;

  return (
    <div className="rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 shadow-[var(--shadow-soft)]">
      <p className="mb-2 text-xs font-semibold text-foreground">
        Inline AI — selected text
      </p>
      <div className="flex flex-wrap gap-1">
        {ACTIONS.map((a) => (
          <Button
            key={a.id}
            size="sm"
            variant="ghost"
            disabled={busy}
            onClick={() => onAction(a.id)}
          >
            {a.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
