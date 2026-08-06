"use client";

import { getWelcomePrompts } from "@/lib/assistant/welcome-prompts";
import type { AssistantSuggestedPrompt } from "@/lib/types/assistant";

export function AssistantWelcome({
  role,
  onSelect,
}: {
  role: string | null;
  productTitle?: string;
  subtitle?: string;
  onSelect: (prompt: AssistantSuggestedPrompt) => void;
}) {
  const prompts = getWelcomePrompts(role);

  return (
    <div className="flex flex-col gap-3 px-1 py-1">
      <p className="text-sm text-muted-foreground">
        Pick a prompt or type your question below.
      </p>
      <ul className="grid gap-2">
        {prompts.map((p) => (
          <li key={p.id}>
            <button
              type="button"
              onClick={() => onSelect(p)}
              className="w-full rounded-[var(--radius-md)] border border-border bg-surface-elevated px-3.5 py-2.5 text-left text-sm font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
            >
              {p.label}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
